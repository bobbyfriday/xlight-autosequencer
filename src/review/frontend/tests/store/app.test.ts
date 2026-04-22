import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from 'src/store/app';
import { act } from '@testing-library/react';

function getStore() {
  return useAppStore.getState();
}

describe('app store', () => {
  beforeEach(() => {
    useAppStore.setState({
      screen: 'library',
      selectedSongId: null,
      inspectorOpen: true,
      tweaksOpen: false,
    });
  });

  it('switches screen', () => {
    act(() => getStore().setScreen('analyze'));
    expect(getStore().screen).toBe('analyze');
  });

  it('sets selected song', () => {
    act(() => getStore().setSelectedSongId('abc123'));
    expect(getStore().selectedSongId).toBe('abc123');
  });

  it('toggles inspector', () => {
    act(() => getStore().toggleInspector());
    expect(getStore().inspectorOpen).toBe(false);
    act(() => getStore().toggleInspector());
    expect(getStore().inspectorOpen).toBe(true);
  });

  it('toggles tweaks panel', () => {
    act(() => getStore().toggleTweaks());
    expect(getStore().tweaksOpen).toBe(true);
  });
});
