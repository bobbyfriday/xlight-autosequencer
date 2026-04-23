import React, { useRef } from 'react';
import styles from './Ruler.module.css';

interface RulerProps {
  durationMs: number;
  playheadMs?: number;
  onSeek?: (ms: number) => void;
  tickIntervalMs?: number;
  viewStartMs?: number;
  viewEndMs?: number;
}

function formatTime(ms: number): string {
  const totalSecs = Math.floor(ms / 1000);
  const m = Math.floor(totalSecs / 60);
  const s = totalSecs % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function Ruler({ durationMs, playheadMs = 0, onSeek, tickIntervalMs, viewStartMs, viewEndMs }: RulerProps) {
  const rulerRef = useRef<HTMLDivElement>(null);

  const start = viewStartMs ?? 0;
  const end = viewEndMs ?? durationMs;
  const windowMs = end - start || durationMs;

  // Auto-scale tick interval based on visible window
  const resolvedTickInterval = tickIntervalMs ?? (() => {
    if (windowMs <= 10000) return 1000;
    if (windowMs <= 30000) return 2000;
    if (windowMs <= 60000) return 5000;
    if (windowMs <= 120000) return 10000;
    if (windowMs <= 300000) return 20000;
    return 60000;
  })();

  function handleClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!onSeek || !rulerRef.current) return;
    const rect = rulerRef.current.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const ms = start + ratio * windowMs;
    onSeek(Math.max(0, Math.min(durationMs, ms)));
  }

  const ticks: number[] = [];
  // Start at the first tick at or after viewStart
  const firstTick = Math.ceil(start / resolvedTickInterval) * resolvedTickInterval;
  for (let t = firstTick; t <= end; t += resolvedTickInterval) {
    ticks.push(t);
  }

  const playheadPct = windowMs > 0 ? ((playheadMs - start) / windowMs) * 100 : 0;
  const playheadVisible = playheadMs >= start && playheadMs <= end;

  return (
    <div
      data-testid="ruler"
      ref={rulerRef}
      className={styles.ruler}
      onClick={handleClick}
      style={{ position: 'relative', overflow: 'hidden' }}
    >
      {ticks.map((t) => {
        const pct = ((t - start) / windowMs) * 100;
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
      {durationMs > 0 && playheadVisible && (
        <div
          data-testid="ruler-playhead"
          className={styles.playhead}
          style={{ left: `${playheadPct}%` }}
        />
      )}
    </div>
  );
}
