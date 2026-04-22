import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useKeyboard } from 'src/hooks/useKeyboard';
import { useKeyboardStore } from 'src/store/keyboard';
import { usePlaybackStore } from 'src/store/playback';
import { useAppStore } from 'src/store/app';

// Helper: fire a keydown event on the window
function fireKey(key: string, options: { shiftKey?: boolean } = {}) {
  const event = new KeyboardEvent('keydown', {
    key,
    shiftKey: options.shiftKey ?? false,
    bubbles: true,
    cancelable: true,
  });
  window.dispatchEvent(event);
}

describe('useKeyboard integration — FR-041 global shortcuts', () => {
  beforeEach(() => {
    // Reset stores
    useKeyboardStore.setState({ bindings: [], suspended: false });
    usePlaybackStore.setState({
      playing: false,
      timeMs: 5000,
      durationMs: 180000,
      energyPulse: 0,
      songId: null,
    });
    useAppStore.setState({
      screen: 'library',
      selectedSongId: null,
      inspectorOpen: true,
      tweaksOpen: false,
    });
  });

  it('Space toggles play/pause via store action', () => {
    const playHandler = vi.fn();
    const pauseHandler = vi.fn();
    useKeyboardStore.getState().register({ key: 'Space', scope: 'global', handler: playHandler });

    const { unmount } = renderHook(() => useKeyboard('global'));
    fireKey(' ');
    expect(playHandler).toHaveBeenCalledOnce();
    unmount();
  });

  it('ArrowLeft fires the ArrowLeft binding', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'ArrowLeft', scope: 'global', handler });

    const { unmount } = renderHook(() => useKeyboard('global'));
    fireKey('ArrowLeft');
    expect(handler).toHaveBeenCalledOnce();
    unmount();
  });

  it('ArrowRight fires the ArrowRight binding', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'ArrowRight', scope: 'global', handler });

    const { unmount } = renderHook(() => useKeyboard('global'));
    fireKey('ArrowRight');
    expect(handler).toHaveBeenCalledOnce();
    unmount();
  });

  it('Shift+ArrowLeft fires the Shift+ArrowLeft binding', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'Shift+ArrowLeft', scope: 'global', handler });

    const { unmount } = renderHook(() => useKeyboard('global'));
    fireKey('ArrowLeft', { shiftKey: true });
    expect(handler).toHaveBeenCalledOnce();
    unmount();
  });

  it('Shift+ArrowRight fires the Shift+ArrowRight binding', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'Shift+ArrowRight', scope: 'global', handler });

    const { unmount } = renderHook(() => useKeyboard('global'));
    fireKey('ArrowRight', { shiftKey: true });
    expect(handler).toHaveBeenCalledOnce();
    unmount();
  });

  it('key 1 fires screen switch binding', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: '1', scope: 'global', handler });

    const { unmount } = renderHook(() => useKeyboard('global'));
    fireKey('1');
    expect(handler).toHaveBeenCalledOnce();
    unmount();
  });

  it('key 6 fires screen switch binding', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: '6', scope: 'global', handler });

    const { unmount } = renderHook(() => useKeyboard('global'));
    fireKey('6');
    expect(handler).toHaveBeenCalledOnce();
    unmount();
  });

  it('input focus suppresses shortcuts', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'Space', scope: 'global', handler });

    const { unmount } = renderHook(() => useKeyboard('global'));

    // Simulate focus on an input by triggering suspend through focusin
    const input = document.createElement('input');
    document.body.appendChild(input);
    input.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));

    fireKey(' ');
    expect(handler).not.toHaveBeenCalled();

    // Clean up
    input.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
    document.body.removeChild(input);
    unmount();
  });

  it('shortcuts resume after input loses focus', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'Space', scope: 'global', handler });

    const { unmount } = renderHook(() => useKeyboard('global'));

    const input = document.createElement('input');
    document.body.appendChild(input);
    input.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    input.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));

    fireKey(' ');
    expect(handler).toHaveBeenCalledOnce();

    document.body.removeChild(input);
    unmount();
  });
});
