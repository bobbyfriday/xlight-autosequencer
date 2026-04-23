import React, { useEffect, useState, useRef } from 'react';
import styles from './Analyze.module.css';

interface Song {
  song_id: string;
  title: string;
  status: string;
  duration_ms: number;
  folder_id: string;
  imported_at: string;
  source_paths: string[];
}

interface DetectorRow {
  detector: string;
  library: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  progress?: number;
  confidence?: number;
  error?: string;
}

interface AnalyzeProps {
  song: Song;
  /**
   * When true, run analysis on mount even if the song is already marked
   * 'analyzed'. Set by the App on re-drop of an existing library file.
   */
  forceOnMount?: boolean;
  /**
   * Notify the parent when the analysis state changes so it can refresh the
   * library rail status chip. Called with the latest song shape.
   */
  onAnalysisComplete?: (song: Song) => void;
  onComplete: () => void;
}

export function Analyze({ song, forceOnMount = false, onAnalysisComplete, onComplete }: AnalyzeProps) {
  const [detectors, setDetectors] = useState<DetectorRow[]>([]);
  const [overall, setOverall] = useState<{ status: string; progress: number } | null>(null);
  // Already analyzed AND not being forced re-analyzed → skip straight to the
  // "done" view. Otherwise we'll POST /analyze and stream status.
  const [analysisComplete, setAnalysisComplete] = useState(
    !forceOnMount && (song.status === 'analyzed' || song.status === 'themed')
  );
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (analysisComplete) return;

    async function startAnalysis() {
      try {
        const res = await fetch(`/api/v1/songs/${song.song_id}/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ force: forceOnMount }),
        });
        if (!res.ok) return;

        // Open SSE stream
        const es = new EventSource(`/api/v1/songs/${song.song_id}/analyze/status`);
        esRef.current = es;

        es.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            if (data.overall) {
              setOverall(data.overall);
              if (data.overall.status === 'done') {
                setAnalysisComplete(true);
                // Update the parent so the library rail status chip turns
                // green without needing a library re-fetch.
                onAnalysisComplete?.({ ...song, status: 'analyzed' });
                es.close();
              }
            } else if (data.detector) {
              setDetectors((prev) => {
                const existing = prev.findIndex((d) => d.detector === data.detector);
                const row: DetectorRow = {
                  detector: data.detector,
                  library: data.library ?? '',
                  status: data.status,
                  progress: data.progress,
                  confidence: data.confidence,
                  error: data.error,
                };
                if (existing >= 0) {
                  const next = [...prev];
                  next[existing] = row;
                  return next;
                }
                return [...prev, row];
              });
            }
          } catch {}
        };

        es.onerror = () => {
          // Connection closed — check if analysis completed
          es.close();
          setAnalysisComplete(true);
        };
      } catch {}
    }

    startAnalysis();

    return () => {
      esRef.current?.close();
    };
  }, [song.song_id, analysisComplete]);

  return (
    <div data-testid="analyze-screen" className={styles.root}>
      <h2 className={styles.title}>{song.title}</h2>

      {overall && (
        <div className={styles.overall}>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${(overall.progress ?? 0) * 100}%` }}
            />
          </div>
          <span className={styles.statusText}>{overall.status}</span>
        </div>
      )}

      {detectors.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Detector</th>
              <th>Library</th>
              <th>Status</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {detectors.map((d) => (
              <tr key={d.detector}>
                <td>{d.detector}</td>
                <td>{d.library}</td>
                <td>{d.status}</td>
                <td>{d.confidence != null ? `${(d.confidence * 100).toFixed(0)}%` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {analysisComplete && (
        <button
          className={styles.reviewBtn}
          onClick={onComplete}
        >
          Review Timeline →
        </button>
      )}
    </div>
  );
}
