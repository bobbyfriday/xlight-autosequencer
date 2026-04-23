import React, { useRef, useState, useCallback } from 'react';
import styles from './Drop.module.css';

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
  /**
   * Called after a successful /api/v1/import response.
   *
   * `created` is the server's "this is a new library entry" flag. When
   * `created: false` the user dropped a file that's already in the library
   * (deduplicated by SHA-256) and the returned song is the existing record,
   * typically with status='analyzed'. Callers can use this to decide whether
   * to force a re-analysis rather than just showing the cached result.
   */
  onSongImported: (song: Song, created: boolean) => void;
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

      const res = await fetch('/api/v1/import', {
        method: 'POST',
        body: formData,
      });

      const body = await res.json();
      if (!res.ok) {
        setError(body?.error?.message ?? 'Import failed');
        return;
      }

      // `created` is truthy only when this is a fresh library entry.
      // Dropping a file that's already imported returns created: false.
      onSongImported(body.song, Boolean(body?.created));
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

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  return (
    <div className={styles.root}>
      <div
        data-testid="drop-target"
        className={styles.dropZone}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => inputRef.current?.click()}
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
