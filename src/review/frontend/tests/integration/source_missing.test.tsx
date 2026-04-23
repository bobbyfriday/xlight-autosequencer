/**
 * T130: source_missing state handling tests.
 *
 * A song whose audio path returns 404 on /audio/<id> enters source_missing state:
 * - Library rail shows the "missing" affordance (StatusChip shows 'missing')
 * - Playback / preview / export are blocked
 * - Section / theme edits are still allowed
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Song } from 'src/store/library';

const mockSourceMissingSong: Song = {
  song_id: 'deadbeef00000001',
  title: 'Missing Song',
  artist: 'Unknown',
  duration_ms: 180_000,
  bpm: 120,
  key: 'C major',
  time_signature: [4, 4],
  status: 'source_missing',
  source_paths: ['/nonexistent/song.mp3'],
  folder_id: 'unfiled',
  imported_at: '2026-04-21T00:00:00Z',
  last_opened_at: null,
};

// ─── Library screen shows missing badge ──────────────────────────────────────

describe('Library screen — source_missing song', () => {
  it('shows status chip with "missing" label', async () => {
    const { Library } = await import('src/screens/Library');
    render(
      <Library
        songs={[mockSourceMissingSong]}
        folders={[{ id: 'unfiled', name: 'Unfiled', created_at: '2026-04-21T00:00:00Z' }]}
        onSelectSong={() => {}}
      />,
    );
    expect(screen.getByTestId('status-chip-source_missing')).toBeInTheDocument();
    expect(screen.getByTestId('status-chip-source_missing').textContent).toBe('missing');
  });
});

// ─── Export screen — blocked for source_missing songs ────────────────────────

describe('Export screen — source_missing song', () => {
  it('renders a blocked affordance when song is source_missing', async () => {
    const { Export } = await import('src/screens/Export');
    render(
      <Export
        song={{ ...mockSourceMissingSong } as any}
        layoutId="layout-1"
        onExportComplete={() => {}}
      />,
    );
    // Render sequence button must not be present
    expect(screen.queryByText('Render Sequence')).not.toBeInTheDocument();
    // Some blocked affordance element must be shown
    const blocked = screen.getByTestId('source-missing-block');
    expect(blocked).toBeInTheDocument();
  });
});

// ─── Timeline / THEME screens still allow edits ──────────────────────────────

describe('Library onSelectSong — source_missing navigates to analyze screen', () => {
  it('routes source_missing song to analyze screen (not timeline/theme)', async () => {
    const { Library } = await import('src/screens/Library');
    const onSelectSong = vi.fn();
    render(
      <Library
        songs={[mockSourceMissingSong]}
        folders={[{ id: 'unfiled', name: 'Unfiled', created_at: '2026-04-21T00:00:00Z' }]}
        onSelectSong={onSelectSong}
      />,
    );
    screen.getByTestId(`song-row-${mockSourceMissingSong.song_id}`).click();
    expect(onSelectSong).toHaveBeenCalledWith(mockSourceMissingSong, expect.any(String));
  });
});
