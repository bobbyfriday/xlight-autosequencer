import React from 'react';
import styles from './DetectorTracks.module.css';

interface Detector {
  name: string;
  library: string;
  status: string;
  confidence: number | null;
  error: string | null;
}

interface Beat {
  t_ms: number;
  bar: number;
  beat: number;
}

interface DetectorTracksProps {
  detectors: Detector[];
  beats: Beat[];
  durationMs: number;
  visible?: boolean;
  onToggleVisible?: () => void;
}

export function DetectorTracks({
  detectors,
  beats,
  durationMs,
  visible = false,
  onToggleVisible,
}: DetectorTracksProps) {
  return (
    <div data-testid="detector-tracks" data-visible={String(visible)}>
      <button
        aria-label="Toggle detector tracks"
        className={styles.toggleBtn}
        onClick={onToggleVisible}
      >
        Detector Tracks
      </button>

      {visible && (
        <div className={styles.lanes}>
          {detectors.map((det) => (
            <div key={det.name} className={styles.lane}>
              <div className={styles.laneLabel}>{det.name}</div>
              <div className={styles.laneTrack} style={{ position: 'relative' }}>
                {det.name === 'beats' &&
                  beats.map((b, i) => {
                    const pct = durationMs > 0 ? (b.t_ms / durationMs) * 100 : 0;
                    return (
                      <div
                        key={i}
                        data-testid="beat-event"
                        className={styles.event}
                        style={{ left: `${pct}%` }}
                      />
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
