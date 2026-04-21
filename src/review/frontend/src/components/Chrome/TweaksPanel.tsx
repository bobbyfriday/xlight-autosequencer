import React from 'react';
import { usePreferencesStore } from 'src/store/preferences';
import styles from './TweaksPanel.module.css';

export function TweaksPanel() {
  const { mode, density, inspector_open, setPreferences } = usePreferencesStore();

  return (
    <aside className={styles.panel}>
      <div className={styles.row}>
        <span className={styles.label}>Mode</span>
        <div className={styles.segmented}>
          <button
            data-active={String(mode === 'dark')}
            onClick={() => setPreferences({ mode: 'dark' })}
          >
            Dark
          </button>
          <button
            data-active={String(mode === 'light')}
            onClick={() => setPreferences({ mode: 'light' })}
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
            onClick={() => setPreferences({ density: 'comfortable' })}
          >
            Comfortable
          </button>
          <button
            data-active={String(density === 'compact')}
            onClick={() => setPreferences({ density: 'compact' })}
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
            onClick={() => setPreferences({ inspector_open: !inspector_open })}
          >
            {inspector_open ? 'Visible' : 'Hidden'}
          </button>
        </div>
      </div>
    </aside>
  );
}
