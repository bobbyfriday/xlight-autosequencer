import React from 'react';
import styles from './AlgoTrack.module.css';

export interface AlgoTrackProps {
  name: string;
  library: string;
  events: number[];
  markCount: number;
  durationMs: number;
  timeMs: number;
  visible: boolean;
  onToggle: () => void;
  color: string;
  rowIdx: number;
  viewStartMs?: number;
  viewEndMs?: number;
  onSeek?: (ms: number) => void;
  /** When provided, renders a value curve line chart instead of tick marks. */
  curve?: { fps: number; values: number[] };
}

export function AlgoTrack({
  name,
  events,
  markCount,
  durationMs,
  timeMs,
  visible,
  onToggle,
  color,
  rowIdx,
  viewStartMs,
  viewEndMs,
  onSeek,
  curve,
}: AlgoTrackProps) {
  const displayCount = curve
    ? curve.values.length
    : (events.length > 0 ? events.length : markCount);

  const start = viewStartMs ?? 0;
  const end = viewEndMs ?? durationMs;
  const windowMs = end - start || durationMs;
  const visibleEvents = events.filter(t => t >= start && t <= end);

  // Build curve path — line chart of normalized values over the visible window
  const curvePath = (() => {
    if (!curve) return '';
    const msPerSample = 1000 / curve.fps;
    const startIdx = Math.max(0, Math.floor(start / msPerSample));
    const endIdx = Math.min(curve.values.length, Math.ceil(end / msPerSample));
    const max = curve.values.length ? Math.max(...curve.values, 1) : 1;
    const parts: string[] = [];
    // Only sample ~1000 points for rendering even if the window has more
    const sliceLen = Math.max(1, endIdx - startIdx);
    const stride = Math.max(1, Math.floor(sliceLen / 1000));
    for (let i = startIdx; i < endIdx; i += stride) {
      const t_ms = i * msPerSample;
      const x = ((t_ms - start) / windowMs) * 1000;
      const y = 26 - (curve.values[i] / max) * 22;
      parts.push(`${parts.length === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return parts.join(' ');
  })();

  function handleClick(e: React.MouseEvent<SVGSVGElement>) {
    if (!onSeek) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const targetMs = start + ratio * windowMs;
    // Snap to nearest event if one is within 30px of the click
    const snapWindowMs = (windowMs * 30) / rect.width;
    const nearest = visibleEvents.reduce<{ ms: number; dist: number } | null>((best, ev) => {
      const d = Math.abs(ev - targetMs);
      if (d > snapWindowMs) return best;
      if (!best || d < best.dist) return { ms: ev, dist: d };
      return best;
    }, null);
    onSeek(nearest ? nearest.ms : Math.max(0, Math.min(durationMs, targetMs)));
  }

  return (
    <div className={`${styles.row} ${rowIdx % 2 === 0 ? styles.rowEven : styles.rowOdd}`} style={{ opacity: visible ? 1 : 0.4 }}>
      <div className={styles.sidebar}>
        <button
          className={styles.toggleBtn}
          onClick={onToggle}
          aria-label={visible ? `Hide ${name}` : `Show ${name}`}
          style={{ color: visible ? '#e2e8f0' : '#64748b' }}
        >
          {visible ? '●' : '○'}
        </button>
        <i className={styles.colorDot} style={{ background: color }} />
        <span className={styles.detectorName} style={{ color: visible ? '#e2e8f0' : '#64748b' }}>
          {name}
        </span>
        <span className={styles.markCount}>{displayCount}</span>
      </div>

      <div className={styles.trackArea} style={{ background: rowIdx % 2 === 0 ? 'var(--bg0, #0a0a0a)' : 'rgba(255,255,255,0.015)' }}>
        <svg
          width="100%"
          height="28"
          viewBox="0 0 1000 28"
          preserveAspectRatio="none"
          onClick={onSeek ? handleClick : undefined}
          style={{ display: 'block', cursor: onSeek ? 'pointer' : undefined }}
        >
          {curve ? (
            curvePath && (
              <path
                d={curvePath}
                fill="none"
                stroke={color}
                strokeWidth={1.2}
                strokeOpacity={0.9}
                vectorEffect="non-scaling-stroke"
              />
            )
          ) : (
            visibleEvents.map((t_ms, i) => {
              const x = ((t_ms - start) / windowMs) * 1000;
              const near = Math.abs(t_ms - timeMs) < 150;
              return (
                <line
                  key={i}
                  x1={x}
                  x2={x}
                  y1={5}
                  y2={23}
                  stroke={near ? '#ffffff' : color}
                  strokeWidth={near ? 1.5 : 1}
                  opacity={near ? 1 : 0.35}
                />
              );
            })
          )}

          {/* Playhead — subtle dashed line so position is visible away from marks */}
          {timeMs >= start && timeMs <= end && (
            <line
              x1={((timeMs - start) / windowMs) * 1000}
              x2={((timeMs - start) / windowMs) * 1000}
              y1={0}
              y2={28}
              stroke="#a8a8b0"
              strokeWidth={0.8}
              strokeDasharray="2 3"
              strokeOpacity={0.6}
              vectorEffect="non-scaling-stroke"
              pointerEvents="none"
            />
          )}
        </svg>
      </div>
    </div>
  );
}
