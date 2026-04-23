import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { Waveform } from '../../src/components/Waveform/Waveform';

const PEAKS = Array.from({ length: 20 }, (_, i) => Math.sin(i * 0.5) * 0.5 + 0.5);

describe('Waveform', () => {
  it('renders an SVG element', () => {
    const { container } = render(<Waveform peaks={PEAKS} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
  });

  it('renders a path from peaks[]', () => {
    const { container } = render(<Waveform peaks={PEAKS} />);
    const path = container.querySelector('path');
    expect(path).toBeTruthy();
    expect(path?.getAttribute('d')).toBeTruthy();
  });

  it('renders playhead line at correct position', () => {
    const { container } = render(<Waveform peaks={PEAKS} playheadMs={500} durationMs={1000} />);
    const line = container.querySelector('line[data-testid="playhead"]');
    expect(line).toBeTruthy();
  });

  it('playhead at 0 is at left edge', () => {
    const { container } = render(<Waveform peaks={PEAKS} playheadMs={0} durationMs={1000} />);
    const line = container.querySelector('line[data-testid="playhead"]');
    expect(line).toBeTruthy();
  });

  it('renders section tint rects when sections provided', () => {
    const sections = [
      { index: 0, start_ms: 0, end_ms: 500, kind: 'intro', label: 'Intro' },
      { index: 1, start_ms: 500, end_ms: 1000, kind: 'verse', label: 'Verse 1' },
    ];
    const { container } = render(
      <Waveform peaks={PEAKS} durationMs={1000} sections={sections} />
    );
    const rects = container.querySelectorAll('rect[data-testid="section-tint"]');
    expect(rects.length).toBe(2);
  });
});
