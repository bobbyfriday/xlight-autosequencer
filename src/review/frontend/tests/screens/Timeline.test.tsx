import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Timeline } from '../../src/screens/Timeline';

const song = {
  song_id: 'abc123',
  title: 'Test Song',
  status: 'analyzed',
  duration_ms: 60000,
  folder_id: 'unfiled',
  imported_at: '2026-01-01T00:00:00Z',
  source_paths: ['/tmp/test.mp3'],
};

const analysis = {
  song_id: 'abc123',
  detected_sections: [
    { index: 0, start_ms: 0, end_ms: 30000, kind: 'intro', label: 'Intro' },
    { index: 1, start_ms: 30000, end_ms: 60000, kind: 'verse', label: 'Verse 1' },
  ],
  alt_boundaries: [],
  beats: [],
  bars: [],
  impacts: [],
  drops: [],
  peaks: Array.from({ length: 50 }, (_, i) => Math.sin(i * 0.2) * 0.5 + 0.5),
  detectors: [],
  completed_at: '2026-01-01T00:00:01Z',
  pipeline_version: 'test',
};

const assignments = [
  { section_index: 0, theme_id: 'shimmer-wash', overrides: {}, user_confirmed: false },
  { section_index: 1, theme_id: 'driving-pulse', overrides: {}, user_confirmed: false },
];

describe('Timeline screen', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <Timeline
        song={song}
        analysis={analysis}
        assignments={assignments}
        onNavigateTheme={() => {}}
      />
    );
    expect(container.firstChild).toBeTruthy();
  });

  it('renders the Transport component', () => {
    render(
      <Timeline
        song={song}
        analysis={analysis}
        assignments={assignments}
        onNavigateTheme={() => {}}
      />
    );
    expect(screen.getByRole('button', { name: /play/i })).toBeTruthy();
  });

  it('renders the Waveform component', () => {
    const { container } = render(
      <Timeline
        song={song}
        analysis={analysis}
        assignments={assignments}
        onNavigateTheme={() => {}}
      />
    );
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('renders SectionStrip chips', () => {
    render(
      <Timeline
        song={song}
        analysis={analysis}
        assignments={assignments}
        onNavigateTheme={() => {}}
      />
    );
    const chips = screen.getAllByRole('button');
    // Should have at least the section chips + transport buttons
    expect(chips.length).toBeGreaterThan(2);
  });
});
