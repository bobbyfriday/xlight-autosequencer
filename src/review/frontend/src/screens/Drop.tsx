import React, { useEffect, useRef, useState, useCallback } from 'react';
import styles from './Drop.module.css';
import { apiFetch } from 'src/lib/apiClient';
import { importByPath, onDrop as onTauriDrop, openAudio } from 'src/lib/nativeDialog';

interface Song {
  song_id: string;
  title: string;
  status: string;
  duration_ms: number;
  folder_id: string;
  imported_at: string;
  source_paths: string[];
}

interface DropProps {
  onSongImported: (song: Song) => void;
}

const ALLOWED_EXTS = new Set(['.mp3', '.wav', '.flac', '.aiff', '.aif']);

function getExt(filename: string): string {
  const i = filename.lastIndexOf('.');
  return i >= 0 ? filename.slice(i).toLowerCase() : '';
}

export function Drop({ onSongImported }: DropProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleFile(file: File) {
    const ext = getExt(file.name);
    if (!ALLOWED_EXTS.has(ext)) {
      setError(`Unsupported file type: ${ext}. Supported: ${[...ALLOWED_EXTS].join(', ')}`);
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('audio', file);

      const res = await apiFetch('/api/v1/import', {
        method: 'POST',
        body: formData,
      });

      const body = await res.json();
      if (!res.ok) {
        setError(body?.error?.message ?? 'Import failed');
        return;
      }

      onSongImported(body.song);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setLoading(false);
    }
  }

  // 052 US3: in the packaged Tauri app we receive absolute file paths and
  // import them via /api/v1/import/by-path — no multipart upload. Dev mode
  // still uses the browser input → handleFile path below.
  async function handlePath(absolutePath: string) {
    const ext = getExt(absolutePath);
    if (!ALLOWED_EXTS.has(ext)) {
      setError(`Unsupported file type: ${ext}. Supported: ${[...ALLOWED_EXTS].join(', ')}`);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const body = (await importByPath(absolutePath)) as { song?: Song };
      if (body.song) onSongImported(body.song);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setLoading(false);
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  async function handleClickToBrowse() {
    // Prefer the native Open dialog in Tauri mode — returns absolute
    // paths that avoid the multi-MB multipart upload round-trip.
    const result = await openAudio({ multiple: false });
    if (result.usable) {
      if (result.paths[0]) void handlePath(result.paths[0]);
      return;
    }
    // Dev fallback: fire the hidden <input type=file>.
    inputRef.current?.click();
  }

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  // 052 US3: listen for files dropped on the Tauri window (Finder drag-drop).
  // In dev this is a no-op; the browser drop handler on dropZone already works.
  useEffect(() => {
    let cancelled = false;
    let unsubscribe: (() => void) | null = null;
    onTauriDrop((paths) => {
      if (!cancelled && paths[0]) void handlePath(paths[0]);
    }).then((fn) => {
      if (cancelled) fn();
      else unsubscribe = fn;
    });
    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  }, []);

  return (
    <div className={styles.root}>
      <div
        data-testid="drop-target"
        className={styles.dropZone}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={handleClickToBrowse}
      >
        <input
          data-testid="file-input"
          ref={inputRef}
          type="file"
          accept=".mp3,.wav,.flac,.aiff,.aif"
          style={{ display: 'none' }}
          onChange={handleChange}
        />
        {loading ? (
          <p>Importing…</p>
        ) : (
          <>
            <p className={styles.hint}>Drop an MP3 here or click to browse</p>
            <p className={styles.sub}>Supports MP3, WAV, FLAC, AIFF</p>
          </>
        )}
      </div>
      {error && (
        <p data-testid="error-message" className={styles.error}>{error}</p>
      )}
    </div>
  );
}
