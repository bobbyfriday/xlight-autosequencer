import { create } from 'zustand';

interface PlaybackState {
  playing: boolean;
  timeMs: number;
  durationMs: number;
  energyPulse: number;
  songId: string | null;

  play: () => void;
  pause: () => void;
  setTimeMs: (ms: number) => void;
  setDurationMs: (ms: number) => void;
  seekMs: (ms: number) => void;
  setEnergyPulse: (v: number) => void;
  tickDecay: (dt: number) => void;
  setSongId: (id: string | null) => void;
}

const DECAY_RATE = 4.0;

export const usePlaybackStore = create<PlaybackState>((set, get) => ({
  playing: false,
  timeMs: 0,
  durationMs: 0,
  energyPulse: 0,
  songId: null,

  play: () => set({ playing: true }),
  pause: () => set({ playing: false }),
  setTimeMs: (ms) => set({ timeMs: ms }),
  setDurationMs: (ms) => set({ durationMs: ms }),
  seekMs: (ms) => set((s) => ({ timeMs: Math.max(0, Math.min(ms, s.durationMs)) })),
  setEnergyPulse: (v) => set({ energyPulse: Math.max(0, Math.min(1, v)) }),
  tickDecay: (dt) =>
    set((s) => ({ energyPulse: Math.max(0, s.energyPulse - DECAY_RATE * dt) })),
  setSongId: (id) => set({ songId: id }),
}));
