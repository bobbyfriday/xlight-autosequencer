import React, { useRef } from 'react';
import styles from './Ruler.module.css';

interface RulerProps {
  durationMs: number;
  playheadMs?: number;
  onSeek?: (ms: number) => void;
  tickIntervalMs?: number;
}

function formatTime(ms: number): string {
  const totalSecs = Math.floor(ms / 1000);
  const m = Math.floor(totalSecs / 60);
  const s = totalSecs % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function Ruler({ durationMs, playheadMs = 0, onSeek, tickIntervalMs = 20000 }: RulerProps) {
  const rulerRef = useRef<HTMLDivElement>(null);

  function handleClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!onSeek || !rulerRef.current) return;
    const rect = rulerRef.current.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    onSeek(Math.max(0, Math.min(durationMs, ratio * durationMs)));
  }

  const ticks: number[] = [];
  for (let t = 0; t <= durationMs; t += tickIntervalMs) {
    ticks.push(t);
  }

  return (
    <div
      data-testid="ruler"
      ref={rulerRef}
      className={styles.ruler}
      onClick={handleClick}
      style={{ position: 'relative', overflow: 'hidden' }}
    >
      {ticks.map((t) => {
        const pct = durationMs > 0 ? (t / durationMs) * 100 : 0;
        return (
          <div
            key={t}
            data-testid="ruler-tick"
            className={styles.tick}
            style={{ left: `${pct}%` }}
          >
            <span className={styles.label}>{formatTime(t)}</span>
          </div>
        );
      })}
      {durationMs > 0 && (
        <div
          data-testid="ruler-playhead"
          className={styles.playhead}
          style={{ left: `${(playheadMs / durationMs) * 100}%` }}
        />
      )}
    </div>
  );
}
