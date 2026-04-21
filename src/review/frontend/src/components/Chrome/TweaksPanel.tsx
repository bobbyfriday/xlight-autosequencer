import React, { useRef, useState } from 'react';
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

  // Replace-mode double-confirm state
  const [replaceConfirmPending, setReplaceConfirmPending] = useState(false);
  const importInputRef = useRef<HTMLInputElement>(null);

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

  async function handleExport() {
    const resp = await fetch('/api/v1/library/export', { method: 'POST' });
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'library.xonset';
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleImportClick() {
    importInputRef.current?.click();
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    const formData = new FormData();
    formData.append('bundle', file);
    formData.append('mode', 'merge');
    await fetch('/api/v1/library/import', { method: 'POST', body: formData });
    // Reload the page to refresh library state
    window.location.reload();
  }

  function handleReplaceClick() {
    if (!replaceConfirmPending) {
      setReplaceConfirmPending(true);
      // Auto-cancel confirm after 5s
      setTimeout(() => setReplaceConfirmPending(false), 5000);
      return;
    }
    // Second click: proceed with replace
    setReplaceConfirmPending(false);
    importInputRef.current?.setAttribute('data-mode', 'replace');
    importInputRef.current?.click();
  }

  async function handleImportFileReplace(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    const formData = new FormData();
    formData.append('bundle', file);
    formData.append('mode', 'replace');
    await fetch('/api/v1/library/import', { method: 'POST', body: formData });
    window.location.reload();
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

      {/* Library portability */}
      <div className={styles.row}>
        <span className={styles.label}>Library</span>
        <button
          data-testid="export-library-btn"
          className={styles.actionBtn}
          onClick={handleExport}
        >
          Export library
        </button>
        <button
          data-testid="import-library-btn"
          className={styles.actionBtn}
          onClick={handleImportClick}
        >
          Import (merge)
        </button>
        <button
          data-testid="replace-library-btn"
          className={styles.actionBtn}
          data-danger={String(replaceConfirmPending)}
          onClick={handleReplaceClick}
        >
          {replaceConfirmPending ? 'Confirm replace?' : 'Import (replace)'}
        </button>
      </div>

      {/* Hidden file inputs */}
      <input
        ref={importInputRef}
        type="file"
        accept=".xonset,.zip"
        style={{ display: 'none' }}
        onChange={handleImportFile}
        data-testid="import-file-input"
      />
      <input
        type="file"
        accept=".xonset,.zip"
        style={{ display: 'none' }}
        onChange={handleImportFileReplace}
        data-testid="replace-file-input"
      />
    </aside>
  );
}
