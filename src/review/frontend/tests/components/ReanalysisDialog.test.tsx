/**
 * T111: Failing tests for ReanalysisDialog component (US3).
 *
 * Covers: carry-over / shifted / dropped / needs-theme rows,
 * confirm calls POST .../analyze/commit, cancel keeps prior analysis intact.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReanalysisDialog } from '../../src/components/ReanalysisDialog/ReanalysisDialog';
import type { MappingEntry, DroppedEntry } from '../../src/util/overlap';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SONG_ID = 'aabbccddeeff0011';
const RUN_ID = 'run_Xa71Q';

function keptEntry(newIdx: number, oldIdx: number): MappingEntry {
  return {
    new_section_index: newIdx,
    action: 'kept',
    inherited_theme_id: 'shimmer-wash',
    inherited_from_old_index: oldIdx,
    overlap_ratio: 1.0,
  };
}

function shiftedEntry(newIdx: number, oldIdx: number): MappingEntry {
  return {
    new_section_index: newIdx,
    action: 'shifted',
    inherited_theme_id: 'driving-pulse',
    inherited_from_old_index: oldIdx,
    overlap_ratio: 0.85,
  };
}

function needsThemeEntry(newIdx: number): MappingEntry {
  return {
    new_section_index: newIdx,
    action: 'needs_theme',
    inherited_theme_id: null,
    inherited_from_old_index: null,
    overlap_ratio: 0.1,
  };
}

function droppedEntry(oldIdx: number): DroppedEntry {
  return {
    old_section_index: oldIdx,
    theme_id: 'peak-flash',
  };
}

const NEW_SECTIONS = [
  { index: 0, start_ms: 0, end_ms: 10000, kind: 'intro', label: 'Intro' },
  { index: 1, start_ms: 10000, end_ms: 25000, kind: 'verse', label: 'Verse 1' },
  { index: 2, start_ms: 25000, end_ms: 40000, kind: 'chorus', label: 'Chorus 1' },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ReanalysisDialog', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders the dialog', () => {
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[keptEntry(0, 0)]}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 1)}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByRole('dialog')).toBeTruthy();
  });

  it('shows carry-over rows for kept sections', () => {
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[keptEntry(0, 0)]}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 1)}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('row-kept-0')).toBeTruthy();
  });

  it('shows shifted rows', () => {
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[shiftedEntry(0, 0)]}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 1)}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('row-shifted-0')).toBeTruthy();
  });

  it('shows needs-theme rows', () => {
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[needsThemeEntry(2)]}
        dropped={[]}
        newSections={[NEW_SECTIONS[2]]}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('row-needs-theme-2')).toBeTruthy();
  });

  it('shows dropped rows', () => {
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[]}
        dropped={[droppedEntry(1)]}
        newSections={[]}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('row-dropped-1')).toBeTruthy();
  });

  it('renders Confirm and Cancel buttons', () => {
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[keptEntry(0, 0)]}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 1)}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByTestId('btn-confirm')).toBeTruthy();
    expect(screen.getByTestId('btn-cancel')).toBeTruthy();
  });

  it('calls onCancel when Cancel button is clicked', () => {
    const onCancel = vi.fn();
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[keptEntry(0, 0)]}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 1)}
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    );
    fireEvent.click(screen.getByTestId('btn-cancel'));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('calls POST .../analyze/commit when Confirm is clicked', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sections: [], assignments: [] }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const onConfirm = vi.fn();
    const mapping = [keptEntry(0, 0), shiftedEntry(1, 1)];
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={mapping}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 2)}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('btn-confirm'));

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toContain(`/songs/${SONG_ID}/analyze/commit`);
    expect(JSON.parse(opts.body)).toMatchObject({
      run_id: RUN_ID,
    });
  });

  it('calls onConfirm after successful commit', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sections: [], assignments: [] }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const onConfirm = vi.fn();
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[keptEntry(0, 0)]}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 1)}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('btn-confirm'));
    await waitFor(() => expect(onConfirm).toHaveBeenCalled());
  });

  it('does NOT call onConfirm when Cancel is clicked', async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={[keptEntry(0, 0)]}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 1)}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );
    fireEvent.click(screen.getByTestId('btn-cancel'));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('includes assignment_mapping in the commit request body', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sections: [], assignments: [] }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const mapping: MappingEntry[] = [
      keptEntry(0, 0),
      needsThemeEntry(1),
    ];

    render(
      <ReanalysisDialog
        songId={SONG_ID}
        runId={RUN_ID}
        mapping={mapping}
        dropped={[]}
        newSections={NEW_SECTIONS.slice(0, 2)}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('btn-confirm'));
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(Array.isArray(body.assignment_mapping)).toBe(true);
    expect(body.assignment_mapping.length).toBe(2);
  });
});
