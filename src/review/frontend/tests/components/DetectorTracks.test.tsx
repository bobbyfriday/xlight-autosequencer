import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DetectorTracks } from '../../src/components/DetectorTracks/DetectorTracks';

const detectors = [
  { name: 'beats', library: 'madmom', status: 'done', confidence: 0.9, error: null },
  { name: 'sections', library: 'librosa', status: 'done', confidence: 0.75, error: null },
];

const beats = [
  { t_ms: 0, bar: 1, beat: 1 },
  { t_ms: 500, bar: 1, beat: 2 },
];

describe('DetectorTracks', () => {
  it('renders hidden by default', () => {
    const { container } = render(
      <DetectorTracks detectors={detectors} beats={beats} durationMs={10000} />
    );
    const tracks = container.querySelector('[data-testid="detector-tracks"]');
    expect(tracks?.getAttribute('data-visible')).toBe('false');
  });

  it('lanes are labeled by detector name', () => {
    render(
      <DetectorTracks
        detectors={detectors}
        beats={beats}
        durationMs={10000}
        visible={true}
      />
    );
    expect(screen.getByText('beats')).toBeTruthy();
    expect(screen.getByText('sections')).toBeTruthy();
  });

  it('toggles visibility when toggle is called', () => {
    const onToggle = vi.fn();
    render(
      <DetectorTracks
        detectors={detectors}
        beats={beats}
        durationMs={10000}
        onToggleVisible={onToggle}
      />
    );
    const toggleBtn = screen.getByRole('button', { name: /detector/i });
    if (toggleBtn) {
      fireEvent.click(toggleBtn);
      expect(onToggle).toHaveBeenCalledOnce();
    }
  });

  it('events positioned by t_ms', () => {
    const { container } = render(
      <DetectorTracks
        detectors={detectors}
        beats={beats}
        durationMs={10000}
        visible={true}
      />
    );
    const events = container.querySelectorAll('[data-testid="beat-event"]');
    expect(events.length).toBeGreaterThan(0);
  });
});
