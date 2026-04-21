import React from 'react';
import { usePreferencesStore, Preferences } from 'src/store/preferences';
import { api } from 'src/api/client';
import styles from './TweaksPanel.module.css';

function persistPrefs(patch: Partial<Preferences>): void {
  api.put('/preferences', patch).catch(() => {
    // Network failure is non-fatal; local state already updated.
  });
}

export function TweaksPanel() {
  const { mode, density, inspector_open, setMode, setDensity, setPreferences } =
    usePreferencesStore();

  function handleMode(value: Preferences['mode']) {
    setMode(value);
    persistPrefs({ mode: value });
  }

  function handleDensity(value: Preferences['density']) {
    setDensity(value);
    persistPrefs({ density: value });
  }

  function handleInspectorToggle() {
    const next = !inspector_open;
    setPreferences({ inspector_open: next });
    persistPrefs({ inspector_open: next });
  }

  return (
    <aside className={styles.panel}>
      <div className={styles.row}>
        <span className={styles.label}>Mode</span>
        <div className={styles.segmented}>
          <button
            data-active={String(mode === 'dark')}
            onClick={() => handleMode('dark')}
          >
            Dark
          </button>
          <button
            data-active={String(mode === 'light')}
            onClick={() => handleMode('light')}
          >
            Light
          </button>
        </div>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Density</span>
        <div className={styles.segmented}>
          <button
            data-active={String(density === 'comfortable')}
            onClick={() => handleDensity('comfortable')}
          >
            Comfortable
          </button>
          <button
            data-active={String(density === 'compact')}
            onClick={() => handleDensity('compact')}
          >
            Compact
          </button>
        </div>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>Inspector</span>
        <div className={styles.segmented}>
          <button
            data-active={String(inspector_open)}
            onClick={handleInspectorToggle}
          >
            {inspector_open ? 'Visible' : 'Hidden'}
          </button>
        </div>
      </div>
    </aside>
  );
}
