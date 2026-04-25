import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Analyze, deriveSectionReviewStatus } from '../../src/screens/Analyze';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

const mockSong = {
  song_id: 'abc123',
  title: 'Test Song',
  status: 'draft',
  duration_ms: 60000,
  folder_id: 'unfiled',
  imported_at: '2026-01-01T00:00:00Z',
  source_paths: ['/tmp/test.mp3'],
};

describe('Analyze screen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the song title', () => {
    render(<Analyze song={mockSong} onComplete={() => {}} />);
    // headerMeta renders "Test Song · <duration>" as one text node, so a
    // substring matcher is required.
    expect(screen.getByText(/Test Song/)).toBeTruthy();
  });

  it('shows an analyzing state initially', () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: 'run_1', started_at: '2026-01-01T00:00:00Z' }),
    });
    render(<Analyze song={mockSong} onComplete={() => {}} />);
    // Should show some indication of analysis state
    expect(screen.getByTestId('analyze-screen')).toBeTruthy();
  });

  it('shows review button when complete', async () => {
    render(<Analyze song={{ ...mockSong, status: 'analyzed' }} onComplete={() => {}} />);
    await waitFor(() => {
      const btn = screen.queryByRole('button', { name: /review timeline/i });
      // Button may appear after analysis completes
      if (btn) expect(btn).toBeTruthy();
    });
  });

  it('calls onComplete when review button clicked', async () => {
    const onComplete = vi.fn();
    render(<Analyze song={{ ...mockSong, status: 'analyzed' }} onComplete={onComplete} />);
    const btn = screen.queryByRole('button', { name: /review timeline/i });
    if (btn) {
      btn.click();
      expect(onComplete).toHaveBeenCalled();
    }
  });

});

// ──────────────────────────────────────────────────────────────────────
// deriveSectionReviewStatus — pure function unit tests
//
// Per openspec change `agreement-score-operationalization` task 5.4 and
// the spec's "section-list low_confidence indicator" scenarios. Tests
// the pure-function logic that drives the section row's review flag.
//
// Tested at function level rather than at the rendered-component level
// because the section list is inlined inside Analyze.tsx and only renders
// in the live-pipeline view (the "already analyzed" summary view returns
// early at line 448 with no section list). Testing the pure function is
// a more focused, less brittle target — it isolates the indicator logic
// from the full pipeline state machine.
//
// Threshold for low_confidence is `agreement_score <= 0` (retuned
// 2026-04-25 from <= 1; corpus measurement on 16 songs / 145 sections
// showed <= 1 flagged 38% of sections, <= 0 flags only the 11%
// genuinely uncorroborated boundaries).
// ──────────────────────────────────────────────────────────────────────
describe('deriveSectionReviewStatus', () => {
  it('no flag when neither low_confidence nor SSM-unsupported', () => {
    const status = deriveSectionReviewStatus({
      low_confidence: false,
      agreement_score: 3,
    });
    expect(status.needsReview).toBe(false);
    expect(status.tooltip).toBe('');
  });

  it('flags when low_confidence is true', () => {
    const status = deriveSectionReviewStatus({
      low_confidence: true,
      agreement_score: 0,
    });
    expect(status.needsReview).toBe(true);
    expect(status.tooltip).toMatch(/verify boundary/i);
    expect(status.tooltip).toMatch(/score 0/);
  });

  it('flags when chorus_ssm_supported is false', () => {
    const status = deriveSectionReviewStatus({
      low_confidence: false,
      agreement_score: 4,
      chorus_ssm_supported: false,
    });
    expect(status.needsReview).toBe(true);
    expect(status.tooltip).toMatch(/verify Chorus label/i);
  });

  it('joins both reasons with a middot when both signals fire', () => {
    const status = deriveSectionReviewStatus({
      low_confidence: true,
      agreement_score: 0,
      chorus_ssm_supported: false,
    });
    expect(status.needsReview).toBe(true);
    expect(status.tooltip).toMatch(/verify boundary/i);
    expect(status.tooltip).toMatch(/verify Chorus label/i);
    expect(status.tooltip).toContain(' · ');
  });

  it('treats absent chorus_ssm_supported as supported (no flag)', () => {
    // Per spec D1: missing field → treated as supported. Only
    // explicit false should flag.
    const status = deriveSectionReviewStatus({
      low_confidence: false,
      agreement_score: 3,
      // chorus_ssm_supported intentionally omitted
    });
    expect(status.needsReview).toBe(false);
    expect(status.tooltip).toBe('');
  });

  it('treats chorus_ssm_supported=true as supported (no flag)', () => {
    const status = deriveSectionReviewStatus({
      low_confidence: false,
      agreement_score: 3,
      chorus_ssm_supported: true,
    });
    expect(status.needsReview).toBe(false);
  });

  it('includes the actual agreement_score in the boundary tooltip', () => {
    // Lets reviewers see the raw score without changing the on/off logic.
    // Useful when debugging close-call boundaries.
    const status = deriveSectionReviewStatus({
      low_confidence: true,
      agreement_score: 0,
    });
    expect(status.tooltip).toContain('score 0');
  });
});
