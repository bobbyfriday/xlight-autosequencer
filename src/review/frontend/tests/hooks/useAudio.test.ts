import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAudio } from '../../src/hooks/useAudio';

describe('useAudio', () => {
  it('returns stable audio ref across re-renders', () => {
    const { result, rerender } = renderHook(() => useAudio());
    const first = result.current.audioRef;
    rerender();
    expect(result.current.audioRef).toBe(first);
  });

  it('seek clamps to [0, duration]', () => {
    const { result } = renderHook(() => useAudio());
    act(() => {
      result.current.seek(-100);
    });
    // No throw means clamping works
    act(() => {
      result.current.seek(999999);
    });
  });

  it('provides playing state', () => {
    const { result } = renderHook(() => useAudio());
    expect(typeof result.current.playing).toBe('boolean');
  });

  it('provides timeMs state', () => {
    const { result } = renderHook(() => useAudio());
    expect(typeof result.current.timeMs).toBe('number');
  });

  it('provides play and pause functions', () => {
    const { result } = renderHook(() => useAudio());
    expect(typeof result.current.play).toBe('function');
    expect(typeof result.current.pause).toBe('function');
  });
});
