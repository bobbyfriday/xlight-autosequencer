import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { usePlaybackStore } from 'src/store/playback';
import { act } from '@testing-library/react';

describe('playback store', () => {
  beforeEach(() => {
    usePlaybackStore.setState({
      playing: false,
      timeMs: 0,
      durationMs: 0,
      energyPulse: 0,
      songId: null,
    });
  });

  it('toggles play/pause', () => {
    act(() => usePlaybackStore.getState().play());
    expect(usePlaybackStore.getState().playing).toBe(true);
    act(() => usePlaybackStore.getState().pause());
    expect(usePlaybackStore.getState().playing).toBe(false);
  });

  it('sets time', () => {
    act(() => usePlaybackStore.getState().setTimeMs(45000));
    expect(usePlaybackStore.getState().timeMs).toBe(45000);
  });

  it('seek clamps to [0, duration]', () => {
    act(() => {
      usePlaybackStore.getState().setDurationMs(120000);
      usePlaybackStore.getState().seekMs(-100);
    });
    expect(usePlaybackStore.getState().timeMs).toBe(0);

    act(() => usePlaybackStore.getState().seekMs(200000));
    expect(usePlaybackStore.getState().timeMs).toBe(120000);
  });

  it('energyPulse decays toward 0', () => {
    act(() => usePlaybackStore.getState().setEnergyPulse(1.0));
    expect(usePlaybackStore.getState().energyPulse).toBe(1.0);
    act(() => usePlaybackStore.getState().tickDecay(0.1));
    expect(usePlaybackStore.getState().energyPulse).toBeLessThan(1.0);
    expect(usePlaybackStore.getState().energyPulse).toBeGreaterThanOrEqual(0);
  });
});
