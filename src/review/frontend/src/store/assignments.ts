import { create } from 'zustand';

export interface ParameterOverrides {
  brightness?: number;
  hit_strength?: number;
  dwell_time?: number;
  color_shift?: number;
}

export interface Assignment {
  section_index: number;
  theme_id: string | null;
  overrides: ParameterOverrides;
}

interface AssignmentsState {
  assignments: Assignment[];

  setAssignments: (assignments: Assignment[]) => void;
  updateAssignment: (index: number, patch: Partial<Assignment>) => void;
}

export const useAssignmentsStore = create<AssignmentsState>((set) => ({
  assignments: [],

  setAssignments: (assignments) => set({ assignments }),
  updateAssignment: (index, patch) =>
    set((s) => {
      const next = [...s.assignments];
      next[index] = { ...next[index], ...patch };
      return { assignments: next };
    }),
}));
