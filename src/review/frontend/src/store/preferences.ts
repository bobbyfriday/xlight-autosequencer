import { create } from 'zustand';

export interface Preferences {
  mode: 'dark' | 'light';
  density: 'comfortable' | 'compact';
  inspector_open: boolean;
  tweaks_open: boolean;
  last_song_id: string | null;
  last_screen: string;
  last_playhead_ms_by_song: Record<string, number>;
  layout_id: string | null;
  library_state_version: number;
}

interface PreferencesState extends Preferences {
  setPreferences: (prefs: Partial<Preferences>) => void;
}

const DEFAULTS: Preferences = {
  mode: 'dark',
  density: 'comfortable',
  inspector_open: true,
  tweaks_open: false,
  last_song_id: null,
  last_screen: 'library',
  last_playhead_ms_by_song: {},
  layout_id: null,
  library_state_version: 0,
};

export const usePreferencesStore = create<PreferencesState>((set) => ({
  ...DEFAULTS,
  setPreferences: (prefs) => set((s) => ({ ...s, ...prefs })),
}));
