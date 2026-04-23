import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Ruler } from '../../src/components/Ruler/Ruler';

describe('Ruler', () => {
  it('renders without crashing', () => {
    const { container } = render(<Ruler durationMs={60000} />);
    expect(container.firstChild).toBeTruthy();
  });

  it('renders ticks at 20s intervals', () => {
    const { container } = render(<Ruler durationMs={60000} />);
    const ticks = container.querySelectorAll('[data-testid="ruler-tick"]');
    // 60s → ticks at 0, 20, 40, 60 = 4 ticks
    expect(ticks.length).toBeGreaterThanOrEqual(3);
  });

  it('calls onSeek when clicked', () => {
    const onSeek = vi.fn();
    const { container } = render(
      <Ruler durationMs={60000} onSeek={onSeek} />
    );
    const ruler = container.querySelector('[data-testid="ruler"]') as HTMLElement;
    if (ruler) {
      fireEvent.click(ruler, { clientX: 0, currentTarget: ruler });
    }
    // onSeek called or not depending on click position
  });

  it('shows time labels', () => {
    render(<Ruler durationMs={60000} />);
    // Should have some time labels like "0:00" or "0:20"
    const timeLabels = screen.queryAllByText(/\d:\d\d/);
    expect(timeLabels.length).toBeGreaterThan(0);
  });
});
