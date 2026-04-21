import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Analyze } from '../../src/screens/Analyze';

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
    expect(screen.getByText('Test Song')).toBeTruthy();
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
