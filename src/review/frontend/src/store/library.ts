import { create } from 'zustand';

export interface Song {
  song_id: string;
  title: string;
  artist: string | null;
  duration_ms: number;
  bpm: number | null;
  key: string | null;
  time_signature: [number, number] | null;
  status: 'draft' | 'analyzed' | 'themed' | 'source_missing';
  source_paths: string[];
  folder_id: string;
  imported_at: string;
  last_opened_at: string | null;
}

export interface Folder {
  id: string;
  name: string;
  created_at: string;
}

type FilterStatus = 'all' | 'draft' | 'analyzed' | 'themed';

interface LibraryState {
  songs: Song[];
  folders: Folder[];
  filterStatus: FilterStatus;

  setSongs: (songs: Song[]) => void;
  setFolders: (folders: Folder[]) => void;
  setFilterStatus: (f: FilterStatus) => void;
  upsertSong: (song: Song) => void;
}

export const useLibraryStore = create<LibraryState>((set) => ({
  songs: [],
  folders: [],
  filterStatus: 'all',

  setSongs: (songs) => set({ songs }),
  setFolders: (folders) => set({ folders }),
  setFilterStatus: (filterStatus) => set({ filterStatus }),
  upsertSong: (song) =>
    set((s) => {
      const idx = s.songs.findIndex((x) => x.song_id === song.song_id);
      if (idx >= 0) {
        const next = [...s.songs];
        next[idx] = song;
        return { songs: next };
      }
      return { songs: [...s.songs, song] };
    }),
}));
