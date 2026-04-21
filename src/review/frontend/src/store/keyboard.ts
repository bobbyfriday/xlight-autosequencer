import { create } from 'zustand';

export type KeyHandler = () => void;

export interface KeyBinding {
  key: string;
  handler: KeyHandler;
  scope: string;
}

interface KeyboardState {
  bindings: KeyBinding[];
  suspended: boolean;

  register: (binding: KeyBinding) => () => void;
  suspend: () => void;
  resume: () => void;
  dispatch: (key: string, scope: string) => boolean;
}

export const useKeyboardStore = create<KeyboardState>((set, get) => ({
  bindings: [],
  suspended: false,

  register: (binding) => {
    set((s) => ({ bindings: [...s.bindings, binding] }));
    return () => {
      set((s) => ({ bindings: s.bindings.filter((b) => b !== binding) }));
    };
  },

  suspend: () => set({ suspended: true }),
  resume: () => set({ suspended: false }),

  dispatch: (key, scope) => {
    const { bindings, suspended } = get();
    if (suspended) return false;
    const match = bindings.find(
      (b) => b.key === key && (b.scope === scope || b.scope === 'global'),
    );
    if (match) {
      match.handler();
      return true;
    }
    return false;
  },
}));
