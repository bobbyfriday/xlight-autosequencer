import { create } from 'zustand';

export interface Section {
  index: number;
  start_ms: number;
  end_ms: number;
  kind: 'intro' | 'verse' | 'pre_chorus' | 'chorus' | 'solo' | 'bridge' | 'outro' | 'unknown';
  label: string;
}

export interface Boundary {
  at_ms: number;
  kind: 'real' | 'ghost';
  confidence: number;
  promoted_by_user: boolean;
}

interface SectionsState {
  sections: Section[];
  boundaries: Boundary[];
  editMode: boolean;
  selectedIndex: number | null;

  setSections: (sections: Section[]) => void;
  setBoundaries: (boundaries: Boundary[]) => void;
  setEditMode: (on: boolean) => void;
  setSelectedIndex: (idx: number | null) => void;
}

export const useSectionsStore = create<SectionsState>((set) => ({
  sections: [],
  boundaries: [],
  editMode: false,
  selectedIndex: null,

  setSections: (sections) => set({ sections }),
  setBoundaries: (boundaries) => set({ boundaries }),
  setEditMode: (editMode) => set({ editMode }),
  setSelectedIndex: (selectedIndex) => set({ selectedIndex }),
}));
