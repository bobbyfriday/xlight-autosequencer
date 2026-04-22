import React, { useEffect, useCallback, useRef, useState } from 'react';
import './theme/tokens.module.css';
import './theme/typography.css';
import { useKeyboard } from 'src/hooks/useKeyboard';
import { useKeyboardStore } from 'src/store/keyboard';
import { usePlaybackStore } from 'src/store/playback';
import { useAppStore, Screen } from 'src/store/app';
import { useLibraryStore } from 'src/store/library';
import type { Song, Folder } from 'src/store/library';
import type { Assignment as StoreAssignment } from 'src/store/assignments';
import { usePreferencesStore } from 'src/store/preferences';
import { Chrome } from 'src/components/Chrome/Chrome';
import { Drop } from 'src/screens/Drop';
import { Analyze } from 'src/screens/Analyze';
import { Timeline } from 'src/screens/Timeline';
import { Theme } from 'src/screens/Theme';
import { Export } from 'src/screens/Export';
import { Library } from 'src/screens/Library';
import { debounce } from 'src/hooks/usePersist';
import { apiFetch } from 'src/lib/apiClient';
import { WeightsDownload } from 'src/components/WeightsDownload/WeightsDownload';

// ── shared types ─────────────────────────────────────────────────────────────

interface ThemeDef {
  theme_id: string;
  name: string;
  description: string;
  accent: string;
  swatches: string[];
  default_for_kinds: string[];
}

interface Section {
  index: number;
  start_ms: number;
  end_ms: number;
  kind: string;
  label: string;
}

// Use the store's canonical Assignment type.
type Assignment = StoreAssignment;

interface Analysis {
  song_id: string;
  detected_sections: Section[];
  peaks: number[];
  beats: { t_ms: number; bar: number; beat: number }[];
  detectors: { name: string; library: string; status: string; confidence: number | null; error: string | null }[];
  completed_at: string;
  [key: string]: unknown;
}

// ── cross-screen state ────────────────────────────────────────────────────────

interface AppData {
  song: Song | null;
  themes: ThemeDef[];
  analysis: Analysis | null;
  assignments: Assignment[];
  layoutId: string | null;
}

const SCREENS: Screen[] = ['library', 'drop', 'analyze', 'timeline', 'theme', 'export'];

// ── cache purge dialog ────────────────────────────────────────────────────────

interface PurgeDialogState {
  songId: string;
  cacheSizeBytes: number;
}

// ── keyboard shortcuts ────────────────────────────────────────────────────────

function useGlobalShortcuts() {
  const register = useKeyboardStore((s) => s.register);

  useEffect(() => {
    const unregister: Array<() => void> = [];

    unregister.push(
      register({
        key: 'Space',
        scope: 'global',
        handler: () => {
          if (usePlaybackStore.getState().playing) {
            usePlaybackStore.getState().pause();
          } else {
            usePlaybackStore.getState().play();
          }
        },
      }),
    );

    unregister.push(
      register({
        key: 'ArrowLeft',
        scope: 'global',
        handler: () => {
          const { timeMs: t, seekMs: seek } = usePlaybackStore.getState();
          seek(t - 1000);
        },
      }),
    );

    unregister.push(
      register({
        key: 'ArrowRight',
        scope: 'global',
        handler: () => {
          const { timeMs: t, seekMs: seek } = usePlaybackStore.getState();
          seek(t + 1000);
        },
      }),
    );

    unregister.push(
      register({
        key: 'Shift+ArrowLeft',
        scope: 'global',
        handler: () => {
          const { timeMs: t, seekMs: seek } = usePlaybackStore.getState();
          seek(t - 5000);
        },
      }),
    );

    unregister.push(
      register({
        key: 'Shift+ArrowRight',
        scope: 'global',
        handler: () => {
          const { timeMs: t, seekMs: seek } = usePlaybackStore.getState();
          seek(t + 5000);
        },
      }),
    );

    SCREENS.forEach((screen, idx) => {
      unregister.push(
        register({
          key: String(idx + 1),
          scope: 'global',
          handler: () => {
            useAppStore.getState().setScreen(screen);
          },
        }),
      );
    });

    return () => unregister.forEach((fn) => fn());
  }, [register]);
}

function GlobalKeyboardListener() {
  useKeyboard('global');
  useGlobalShortcuts();
  return null;
}

// ── persistence helpers (T088) ────────────────────────────────────────────────

async function saveAssignments(songId: string, assignments: Assignment[]) {
  await apiFetch(`/api/v1/songs/${songId}/assignments`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assignments }),
  });
}

// ── main app ──────────────────────────────────────────────────────────────────

export default function App() {
  const screen = useAppStore((s) => s.screen);
  const setScreen = useAppStore((s) => s.setScreen);
  const selectedSongId = useAppStore((s) => s.selectedSongId);
  const setSelectedSongId = useAppStore((s) => s.setSelectedSongId);

  const songs = useLibraryStore((s) => s.songs);
  const folders = useLibraryStore((s) => s.folders);
  const setSongs = useLibraryStore((s) => s.setSongs);
  const setFolders = useLibraryStore((s) => s.setFolders);
  const upsertSong = useLibraryStore((s) => s.upsertSong);

  const setPreferences = usePreferencesStore((s) => s.setPreferences);
  const lastSongId = usePreferencesStore((s) => s.last_song_id);
  const lastScreen = usePreferencesStore((s) => s.last_screen);

  // cross-screen data lives here — screens receive it as props
  const [data, setData] = React.useState<AppData>({
    song: null,
    themes: [],
    analysis: null,
    assignments: [],
    layoutId: null,
  });

  // Cache purge dialog state (T099)
  const [purgeDialog, setPurgeDialog] = useState<PurgeDialogState | null>(null);

  // T100: Load preferences + library on mount, then restore last session
  const bootDone = useRef(false);
  useEffect(() => {
    if (bootDone.current) return;
    bootDone.current = true;

    // Load preferences first
    apiFetch('/api/v1/preferences')
      .then((r) => (r.ok ? r.json() : null))
      .then((prefs) => {
        if (prefs) {
          setPreferences(prefs);
        }
      })
      .catch(() => {});

    // Load library
    apiFetch('/api/v1/library')
      .then((r) => r.json())
      .then((body) => {
        if (body.songs) setSongs(body.songs);
        if (body.folders) setFolders(body.folders);

        // T100: restore last session after library is loaded
        const prefs = usePreferencesStore.getState();
        const lastId = prefs.last_song_id;
        const lastScr = prefs.last_screen as Screen;
        if (lastId && body.songs) {
          const song = body.songs.find((s: Song) => s.song_id === lastId);
          if (song) {
            setData((d) => ({ ...d, song }));
            setSelectedSongId(lastId);
            if (lastScr && lastScr !== 'library') {
              setScreen(lastScr);
            }
          }
        }
      })
      .catch(() => {});
  }, []);

  // load themes catalog once on mount
  useEffect(() => {
    apiFetch('/api/v1/themes')
      .then((r) => r.json())
      .then((body) => {
        if (body.themes) setData((d) => ({ ...d, themes: body.themes }));
      })
      .catch(() => {});
  }, []);

  // load layout preference on mount
  useEffect(() => {
    apiFetch('/api/v1/layout')
      .then((r) => {
        if (!r.ok) return null;
        return r.json();
      })
      .then((body) => {
        if (body?.layout_id) setData((d) => ({ ...d, layoutId: body.layout_id }));
      })
      .catch(() => {});
  }, []);

  // debounced assignment persistence (T088 — FR-049a)
  const debouncedSave = useRef(
    debounce((songId: string, assignments: Assignment[]) => {
      saveAssignments(songId, assignments).catch(() => {});
    }, 500),
  );

  function handleAssignmentChange(updated: Assignment) {
    setData((d) => {
      const next = d.assignments.map((a) =>
        a.section_index === updated.section_index ? updated : a,
      );
      if (d.song) debouncedSave.current(d.song.song_id, next);
      return { ...d, assignments: next };
    });
  }

  // ── screen handlers ──

  // T087: DROP → ANALYZE
  const handleSongImported = useCallback((song: Song) => {
    setData((d) => ({ ...d, song, analysis: null, assignments: [] }));
    setSelectedSongId(song.song_id);
    upsertSong(song);
    setScreen('analyze');
  }, [setScreen, setSelectedSongId, upsertSong]);

  // T087: ANALYZE → TIMELINE
  const handleAnalyzeComplete = useCallback(async () => {
    const song = data.song;
    if (!song) return;
    try {
      const [analysisRes, assignmentsRes] = await Promise.all([
        apiFetch(`/api/v1/songs/${song.song_id}/analysis`),
        apiFetch(`/api/v1/songs/${song.song_id}/assignments`),
      ]);
      const analysisBody = analysisRes.ok ? await analysisRes.json() : null;
      const assignmentsBody = assignmentsRes.ok ? await assignmentsRes.json() : null;
      setData((d) => ({
        ...d,
        analysis: analysisBody,
        assignments: assignmentsBody?.assignments ?? [],
      }));
    } catch {}
    setScreen('timeline');
  }, [data.song, setScreen]);

  // T087: TIMELINE → THEME
  const handleNavigateTheme = useCallback(() => {
    setScreen('theme');
  }, [setScreen]);

  // THEME → EXPORT
  const handleThemed = useCallback(() => {
    if (data.song) {
      const updatedSong = { ...data.song, status: 'themed' as const };
      setData((d) => ({ ...d, song: updatedSong }));
      upsertSong(updatedSong);
    }
    setScreen('export');
  }, [data.song, setScreen, upsertSong]);

  // Library: selecting a song (FR-003 — route by status)
  const handleSelectSong = useCallback((song: Song, targetScreen: string) => {
    setData((d) => ({ ...d, song, analysis: null, assignments: [] }));
    setSelectedSongId(song.song_id);

    // Persist last_song_id in preferences
    setPreferences({ last_song_id: song.song_id, last_screen: targetScreen });
    apiFetch('/api/v1/preferences', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ last_song_id: song.song_id, last_screen: targetScreen }),
    }).catch(() => {});

    setScreen(targetScreen as Screen);
  }, [setScreen, setSelectedSongId, setPreferences]);

  // T098: drag-and-drop folder move
  const handleSongMoved = useCallback((songId: string, targetFolderId: string) => {
    apiFetch(`/api/v1/songs/${songId}/folder`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_id: targetFolderId }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((updated) => {
        if (updated) upsertSong(updated);
      })
      .catch(() => {});
  }, [upsertSong]);

  // T099: remove from library → cache purge dialog
  const handleRemoveSong = useCallback((song: Song) => {
    apiFetch(`/api/v1/songs/${song.song_id}`, { method: 'DELETE' })
      .then((r) => (r.ok ? r.json() : null))
      .then((result) => {
        if (!result) return;
        // Remove from local store
        setSongs(songs.filter((s) => s.song_id !== song.song_id));
        if (result.cache_purge_available) {
          setPurgeDialog({ songId: song.song_id, cacheSizeBytes: result.cache_size_bytes });
        }
      })
      .catch(() => {});
  }, [songs, setSongs]);

  const handlePurgeCache = useCallback((songId: string) => {
    apiFetch(`/api/v1/songs/${songId}/purge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis: true, stems: true }),
    }).catch(() => {});
    setPurgeDialog(null);
  }, []);

  // render active screen content
  function renderScreen() {
    const { song, themes, analysis, assignments, layoutId } = data;

    switch (screen) {
      case 'library':
        return (
          <Library
            songs={songs}
            folders={folders}
            onSelectSong={handleSelectSong}
          />
        );

      case 'drop':
        return <Drop onSongImported={handleSongImported} />;

      case 'analyze':
        if (!song) return <PlaceholderScreen label="Drop a song first" onDrop={() => setScreen('drop')} />;
        return <Analyze song={song} onComplete={handleAnalyzeComplete} />;

      case 'timeline':
        if (!song || !analysis)
          return <PlaceholderScreen label="Analysis required" onDrop={() => setScreen('analyze')} />;
        return (
          <Timeline
            song={song}
            analysis={analysis}
            assignments={assignments}
            onNavigateTheme={handleNavigateTheme}
          />
        );

      case 'theme':
        if (!song || !analysis)
          return <PlaceholderScreen label="Analysis required" onDrop={() => setScreen('analyze')} />;
        return (
          <Theme
            song={song}
            themes={themes}
            sections={analysis.detected_sections}
            assignments={assignments}
            onThemed={handleThemed}
            onAssignmentChange={handleAssignmentChange}
          />
        );

      case 'export':
        if (!song)
          return <PlaceholderScreen label="Drop a song first" onDrop={() => setScreen('drop')} />;
        return (
          <Export
            song={song}
            layoutId={layoutId}
            onExportComplete={(outputPath) => {
              void outputPath;
            }}
          />
        );

      default:
        return <PlaceholderScreen label="Unknown screen" onDrop={() => setScreen('library')} />;
    }
  }

  return (
    <div id="app-root" data-testid="app-root">
      <GlobalKeyboardListener />
      <Chrome
        activeScreen={screen}
        onNavigate={setScreen}
        songs={songs}
        folders={folders}
        activeSongId={selectedSongId}
        onSelectSong={handleSelectSong}
        onSongMoved={handleSongMoved}
        onRemoveSong={handleRemoveSong}
      >
        {renderScreen()}
      </Chrome>

      {/* 052 US2: first-use demucs-weights download modal.
          Self-managed visibility via useWeightsDownloadStore.phase. */}
      <WeightsDownload />

      {/* T099: cache purge confirmation dialog */}
      {purgeDialog && (
        <PurgeDialog
          songId={purgeDialog.songId}
          cacheSizeBytes={purgeDialog.cacheSizeBytes}
          onPurge={() => handlePurgeCache(purgeDialog.songId)}
          onDismiss={() => setPurgeDialog(null)}
        />
      )}
    </div>
  );
}

// ── Purge dialog ──────────────────────────────────────────────────────────────

function PurgeDialog({
  songId,
  cacheSizeBytes,
  onPurge,
  onDismiss,
}: {
  songId: string;
  cacheSizeBytes: number;
  onPurge: () => void;
  onDismiss: () => void;
}) {
  const mb = (cacheSizeBytes / 1024 / 1024).toFixed(1);
  return (
    <div
      data-testid="purge-dialog"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: 'var(--color-surface, #1a1a1a)',
          border: '1px solid var(--color-border, #444)',
          borderRadius: 10,
          padding: 28,
          maxWidth: 360,
          width: '90%',
        }}
      >
        <h3 style={{ marginBottom: 12, color: 'var(--color-text, #f5f5f0)' }}>
          Remove analysis cache?
        </h3>
        <p style={{ color: 'var(--color-text-muted, #888)', marginBottom: 20, fontSize: 14 }}>
          The song was removed from your library. Its analysis cache
          {cacheSizeBytes > 0 ? ` (${mb} MB)` : ''} can be deleted to free disk space.
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button
            onClick={onDismiss}
            style={{
              padding: '7px 16px',
              background: 'transparent',
              border: '1px solid var(--color-border, #444)',
              borderRadius: 6,
              cursor: 'pointer',
              color: 'var(--color-text, #f5f5f0)',
              fontSize: 13,
            }}
          >
            Keep cache
          </button>
          <button
            data-testid="purge-confirm-button"
            onClick={onPurge}
            style={{
              padding: '7px 16px',
              background: 'var(--color-accent, #4ade80)',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              color: '#000',
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            Delete cache
          </button>
        </div>
      </div>
    </div>
  );
}

// ── minimal placeholder screens ───────────────────────────────────────────────

function PlaceholderScreen({ label, onDrop }: { label: string; onDrop: () => void }) {
  return (
    <div style={{ padding: 32, color: 'var(--color-text-muted, #888)', textAlign: 'center' }}>
      <p>{label}</p>
      <button
        onClick={onDrop}
        style={{
          marginTop: 16,
          padding: '8px 20px',
          background: 'var(--color-accent, #4ade80)',
          color: '#000',
          border: 'none',
          borderRadius: 6,
          cursor: 'pointer',
          fontWeight: 600,
        }}
      >
        Go
      </button>
    </div>
  );
}
