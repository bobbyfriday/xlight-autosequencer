import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { debounce, persist } from 'src/hooks/usePersist';

describe('persist helpers', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('persist calls the writer immediately (FR-049a)', async () => {
    const writer = vi.fn().mockResolvedValue(undefined);
    await persist(writer);
    expect(writer).toHaveBeenCalledOnce();
  });

  it('debounce delays execution by the given ms (FR-049b)', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 1000);

    debounced();
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(999);
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(fn).toHaveBeenCalledOnce();
  });

  it('debounce resets timer on repeated calls (FR-049b)', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 1000);

    debounced();
    vi.advanceTimersByTime(500);
    debounced();
    vi.advanceTimersByTime(500);
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(500);
    expect(fn).toHaveBeenCalledOnce();
  });

  it('rapid calls (5s) produce at most 6 invocations via debounce', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 1000);

    for (let i = 0; i < 50; i++) {
      debounced();
      vi.advanceTimersByTime(100);
    }
    vi.advanceTimersByTime(1000);

    expect(fn.mock.calls.length).toBeLessThanOrEqual(6);
  });
});
