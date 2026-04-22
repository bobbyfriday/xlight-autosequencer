import React, { useState } from 'react';
import styles from './Export.module.css';
import { apiFetch } from 'src/lib/apiClient';

interface Song {
  song_id: string;
  title: string;
  status: string;
  duration_ms: number;
}

interface ExportProps {
  song: Song;
  layoutId: string | null;
  onExportComplete?: (outputPath: string) => void;
}

export function Export({ song, layoutId, onExportComplete }: ExportProps) {
  const [exporting, setExporting] = useState(false);
  const [outputPath, setOutputPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isThemed = song.status === 'themed';
  const hasLayout = layoutId != null;

  async function handleRender() {
    setError(null);
    setExporting(true);
    try {
      const res = await apiFetch(`/api/v1/songs/${song.song_id}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format: 'xsq' }),
      });
      const body = await res.json();
      if (!res.ok) {
        setError(body?.error?.message ?? 'Export failed');
        return;
      }
      // Poll SSE for completion
      const es = new EventSource(`/api/v1/songs/${song.song_id}/export/status`);
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.stage === 'done') {
            setOutputPath(data.output_path);
            onExportComplete?.(data.output_path);
            es.close();
          } else if (data.stage === 'failed') {
            setError(data.error ?? 'Export failed');
            es.close();
          }
        } catch {}
      };
      es.onerror = () => {
        es.close();
        setExporting(false);
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  }

  const isSourceMissing = song.status === 'source_missing';

  if (isSourceMissing) {
    return (
      <div data-testid="source-missing-block" className={styles.block}>
        <h3>Audio File Missing</h3>
        <p>The audio file for <strong>{song.title}</strong> can no longer be found.</p>
        <p>Use "Locate file" to point to the audio file on your disk.</p>
      </div>
    );
  }

  if (!hasLayout) {
    return (
      <div data-testid="layout-required" className={styles.block}>
        <h3>Layout Required</h3>
        <p>Import your <code>xlights_rgbeffects.xml</code> to continue.</p>
      </div>
    );
  }

  if (!isThemed) {
    return (
      <div data-testid="incomplete-theming" className={styles.block}>
        <h3>Theming Incomplete</h3>
        <p>All sections must be themed before exporting.</p>
      </div>
    );
  }

  return (
    <div data-testid="export-form" className={styles.root}>
      <h2 className={styles.title}>Export: {song.title}</h2>

      {error && <p className={styles.error}>{error}</p>}

      {outputPath ? (
        <div className={styles.success}>
          <p>Export complete!</p>
          <code className={styles.path}>{outputPath}</code>
        </div>
      ) : (
        <button
          className={styles.renderBtn}
          onClick={handleRender}
          disabled={exporting}
        >
          {exporting ? 'Rendering…' : 'Render Sequence'}
        </button>
      )}
    </div>
  );
}
