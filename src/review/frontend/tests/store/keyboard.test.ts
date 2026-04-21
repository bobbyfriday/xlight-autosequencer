import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useKeyboardStore } from 'src/store/keyboard';

describe('keyboard store', () => {
  beforeEach(() => {
    useKeyboardStore.setState({ bindings: [], suspended: false });
  });

  it('registers and dispatches a binding', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'Space', scope: 'global', handler });
    const handled = useKeyboardStore.getState().dispatch('Space', 'timeline');
    expect(handled).toBe(true);
    expect(handler).toHaveBeenCalledOnce();
  });

  it('unregister removes the binding', () => {
    const handler = vi.fn();
    const unregister = useKeyboardStore
      .getState()
      .register({ key: 'Space', scope: 'global', handler });
    unregister();
    const handled = useKeyboardStore.getState().dispatch('Space', 'timeline');
    expect(handled).toBe(false);
  });

  it('scope-scoped binding does not fire in other scope', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 's', scope: 'timeline', handler });
    const handled = useKeyboardStore.getState().dispatch('s', 'theme');
    expect(handled).toBe(false);
  });

  it('suspended store does not fire handlers', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'Space', scope: 'global', handler });
    useKeyboardStore.getState().suspend();
    useKeyboardStore.getState().dispatch('Space', 'global');
    expect(handler).not.toHaveBeenCalled();
  });

  it('resumes after suspend', () => {
    const handler = vi.fn();
    useKeyboardStore.getState().register({ key: 'Space', scope: 'global', handler });
    useKeyboardStore.getState().suspend();
    useKeyboardStore.getState().resume();
    useKeyboardStore.getState().dispatch('Space', 'global');
    expect(handler).toHaveBeenCalledOnce();
  });
});
