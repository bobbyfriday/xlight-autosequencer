import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Transport } from '../../src/components/Transport/Transport';

describe('Transport', () => {
  it('renders play button when paused', () => {
    render(<Transport playing={false} timeMs={0} durationMs={60000} />);
    expect(screen.getByRole('button', { name: /play/i })).toBeTruthy();
  });

  it('renders pause button when playing', () => {
    render(<Transport playing={true} timeMs={5000} durationMs={60000} />);
    expect(screen.getByRole('button', { name: /pause/i })).toBeTruthy();
  });

  it('calls onPlay when play clicked', () => {
    const onPlay = vi.fn();
    render(<Transport playing={false} timeMs={0} durationMs={60000} onPlay={onPlay} />);
    fireEvent.click(screen.getByRole('button', { name: /play/i }));
    expect(onPlay).toHaveBeenCalledOnce();
  });

  it('calls onPause when pause clicked', () => {
    const onPause = vi.fn();
    render(<Transport playing={true} timeMs={0} durationMs={60000} onPause={onPause} />);
    fireEvent.click(screen.getByRole('button', { name: /pause/i }));
    expect(onPause).toHaveBeenCalledOnce();
  });

  it('shows timecode in tabular format', () => {
    render(<Transport playing={false} timeMs={65000} durationMs={120000} />);
    // Should show "1:05" somewhere
    expect(screen.getByText(/1:05/)).toBeTruthy();
  });

  it('renders prev and next section buttons', () => {
    render(<Transport playing={false} timeMs={0} durationMs={60000} />);
    expect(screen.getByRole('button', { name: /prev/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /next/i })).toBeTruthy();
  });
});
