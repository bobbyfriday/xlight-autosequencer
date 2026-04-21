import React from 'react';
import styles from './Transport.module.css';

interface TransportProps {
  playing: boolean;
  timeMs: number;
  durationMs: number;
  onPlay?: () => void;
  onPause?: () => void;
  onPrevSection?: () => void;
  onNextSection?: () => void;
}

function formatTimecode(ms: number): string {
  const totalSecs = Math.floor(ms / 1000);
  const m = Math.floor(totalSecs / 60);
  const s = totalSecs % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function Transport({
  playing,
  timeMs,
  durationMs,
  onPlay,
  onPause,
  onPrevSection,
  onNextSection,
}: TransportProps) {
  return (
    <div className={styles.root}>
      <button
        className={styles.btn}
        aria-label="Previous section"
        onClick={onPrevSection}
      >
        ⏮
      </button>

      {playing ? (
        <button
          className={`${styles.btn} ${styles.playPause}`}
          aria-label="Pause"
          onClick={onPause}
        >
          ⏸
        </button>
      ) : (
        <button
          className={`${styles.btn} ${styles.playPause}`}
          aria-label="Play"
          onClick={onPlay}
        >
          ▶
        </button>
      )}

      <button
        className={styles.btn}
        aria-label="Next section"
        onClick={onNextSection}
      >
        ⏭
      </button>

      <span className={styles.timecode}>
        {formatTimecode(timeMs)}
      </span>
      <span className={styles.separator}>/</span>
      <span className={styles.duration}>{formatTimecode(durationMs)}</span>
    </div>
  );
}
