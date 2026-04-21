import React, { useEffect, useCallback, useRef } from 'react';
import './theme/tokens.module.css';
import './theme/typography.css';
import { useKeyboard } from 'src/hooks/useKeyboard';
import { useKeyboardStore } from 'src/store/keyboard';
import { usePlaybackStore } from 'src/store/playback';
import { useAppStore, Screen } from 'src/store/app';
import { Chrome } from 'src/components/Chrome/Chrome';
import { Drop } from 'src/screens/Drop';
import { Analyze } from 'src/screens/Analyze';
import { Timeline } from 'src/screens/Timeline';
import { Theme } from 'src/screens/Theme';
import { Export } from 'src/screens/Export';
import { debounce } from 'src/hooks/usePersist';

// ── shared types ─────────────────────────────────────────────────────────────

interface Song {
  song_id: string;
  title: string;
  status: string;
  duration_ms: number;
  folder_id: string;
  imported_at: string;
  source_paths: string[];
}

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

interface Assignment {
  section_index: number;
  theme_id: string | null;
  overrides: Record<string, number>;
  user_confirmed: boolean;
}

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
  await fetch(`/api/v1/songs/${songId}/assignments`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assignments }),
  });
}

// ── main app ──────────────────────────────────────────────────────────────────

export default function App() {
  const screen = useAppStore((s) => s.screen);
  const setScreen = useAppStore((s) => s.setScreen);

  // cross-screen data lives here — screens receive it as props
  const [data, setData] = React.useState<AppData>({
    song: null,
    themes: [],
    analysis: null,
    assignments: [],
    layoutId: null,
  });

  // load themes catalog once on mount
  useEffect(() => {
    fetch('/api/v1/themes')
      .then((r) => r.json())
      .then((body) => {
        if (body.themes) setData((d) => ({ ...d, themes: body.themes }));
      })
      .catch(() => {});
  }, []);

  // load layout preference on mount
  useEffect(() => {
    fetch('/api/v1/layout')
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
    setScreen('analyze');
  }, [setScreen]);

  // T087: ANALYZE → TIMELINE
  const handleAnalyzeComplete = useCallback(async () => {
    const song = data.song;
    if (!song) return;
    try {
      const [analysisRes, assignmentsRes] = await Promise.all([
        fetch(`/api/v1/songs/${song.song_id}/analysis`),
        fetch(`/api/v1/songs/${song.song_id}/assignments`),
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
      setData((d) => ({
        ...d,
        song: d.song ? { ...d.song, status: 'themed' } : d.song,
      }));
    }
    setScreen('export');
  }, [data.song, setScreen]);

  // render active screen content
  function renderScreen() {
    const { song, themes, analysis, assignments, layoutId } = data;

    switch (screen) {
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
              // stay on export screen; outputPath shown in Export component
              void outputPath;
            }}
          />
        );

      case 'library':
      default:
        return <LibraryPlaceholder onDrop={() => setScreen('drop')} />;
    }
  }

  return (
    <div id="app-root" data-testid="app-root">
      <GlobalKeyboardListener />
      <Chrome activeScreen={screen} onNavigate={setScreen}>
        {renderScreen()}
      </Chrome>
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

function LibraryPlaceholder({ onDrop }: { onDrop: () => void }) {
  return (
    <div style={{ padding: 32, color: 'var(--color-text, #f5f5f0)' }}>
      <h2 style={{ marginBottom: 16 }}>Library</h2>
      <p style={{ color: 'var(--color-text-muted, #888)', marginBottom: 24 }}>
        Your imported songs will appear here.
      </p>
      <button
        onClick={onDrop}
        style={{
          padding: '10px 24px',
          background: 'var(--color-accent, #4ade80)',
          color: '#000',
          border: 'none',
          borderRadius: 6,
          cursor: 'pointer',
          fontWeight: 600,
          fontSize: 14,
        }}
      >
        Import a song →
      </button>
    </div>
  );
}
