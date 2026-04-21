import React, { useEffect } from 'react';
import './theme/tokens.module.css';
import './theme/typography.css';
import { useKeyboard } from 'src/hooks/useKeyboard';
import { useKeyboardStore } from 'src/store/keyboard';
import { usePlaybackStore } from 'src/store/playback';
import { useAppStore, Screen } from 'src/store/app';

const SCREENS: Screen[] = ['library', 'drop', 'analyze', 'timeline', 'theme', 'export'];

function useGlobalShortcuts() {
  const register = useKeyboardStore((s) => s.register);
  const play = usePlaybackStore((s) => s.play);
  const pause = usePlaybackStore((s) => s.pause);
  const playing = usePlaybackStore((s) => s.playing);
  const seekMs = usePlaybackStore((s) => s.seekMs);
  const timeMs = usePlaybackStore((s) => s.timeMs);
  const setScreen = useAppStore((s) => s.setScreen);

  useEffect(() => {
    const unregister: Array<() => void> = [];

    // Space — play/pause
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

    // ArrowLeft — nudge -1s
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

    // ArrowRight — nudge +1s
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

    // Shift+ArrowLeft — jump to prev section (stub: nudge -5s until sections store wired)
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

    // Shift+ArrowRight — jump to next section (stub: nudge +5s until sections store wired)
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

    // 1–6 — switch screens
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

// Activate the global keydown listener
function GlobalKeyboardListener() {
  useKeyboard('global');
  useGlobalShortcuts();
  return null;
}

// Stub — screens wired in T086; Chrome wired in T034
export default function App() {
  return (
    <div id="app-root" data-testid="app-root">
      <GlobalKeyboardListener />
    </div>
  );
}
