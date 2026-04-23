import React from 'react';

interface Section {
  index: number;
  start_ms: number;
  end_ms: number;
  kind: string;
  label: string;
}

interface WaveformProps {
  peaks: number[];
  /** When true, `peaks` already covers exactly the visible window — don't slice. */
  peaksArePrescaled?: boolean;
  playheadMs?: number;
  durationMs?: number;
  viewStartMs?: number;
  viewEndMs?: number;
  sections?: Section[];
  width?: number;
  height?: number;
  accent?: string;
  onSeek?: (ms: number) => void;
}

const KIND_COLORS: Record<string, string> = {
  intro: '#4ade8020',
  verse: '#38bdf820',
  chorus: '#facc1530',
  solo: '#818cf820',
  bridge: '#f9731620',
  outro: '#4ade8020',
  unknown: '#94a3b820',
};

/**
 * Builds a vertical-bar waveform path: one M/V segment per sample from
 * -peak to +peak around the centre line. This preserves transient sharpness
 * at all zoom levels — unlike a smoothed polygon outline.
 */
function buildPath(peaks: number[], width: number, height: number): string {
  if (!peaks.length) return '';
  const midY = height / 2;
  const step = width / peaks.length;
  const parts: string[] = [];

  for (let i = 0; i < peaks.length; i++) {
    const x = (i * step + step / 2).toFixed(2);
    const amplitude = peaks[i] * midY * 0.9;
    const y1 = (midY - amplitude).toFixed(2);
    const y2 = (midY + amplitude).toFixed(2);
    parts.push(`M${x},${y1}V${y2}`);
  }
  return parts.join('');
}

export function Waveform({
  peaks,
  peaksArePrescaled = false,
  playheadMs = 0,
  durationMs = 0,
  viewStartMs,
  viewEndMs,
  sections,
  width = 1000,
  height = 80,
  accent = '#4ade80',
  onSeek,
}: WaveformProps) {
  const start = viewStartMs ?? 0;
  const end = viewEndMs ?? durationMs;
  const windowMs = end - start || durationMs;

  // Slice peaks to the visible window (skip if the caller already sliced)
  const visiblePeaks = (() => {
    if (peaksArePrescaled) return peaks;
    if (!viewStartMs && !viewEndMs) return peaks;
    const startFrac = start / durationMs;
    const endFrac = end / durationMs;
    const lo = Math.floor(startFrac * peaks.length);
    const hi = Math.ceil(endFrac * peaks.length);
    return peaks.slice(lo, hi);
  })();

  const playheadX = windowMs > 0 ? ((playheadMs - start) / windowMs) * width : 0;
  const d = buildPath(visiblePeaks, width, height);

  // ms → x within the visible window
  function msToX(ms: number): number {
    return ((ms - start) / windowMs) * width;
  }

  function handleClick(e: React.MouseEvent<SVGSVGElement>) {
    if (!onSeek) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const ms = start + ratio * windowMs;
    onSeek(Math.max(0, Math.min(durationMs || ms, ms)));
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      onClick={onSeek ? handleClick : undefined}
      style={onSeek ? { cursor: 'pointer' } : undefined}
    >
      {/* Section tint rects */}
      {sections?.map((sec) => {
        if (!durationMs) return null;
        const secStart = Math.max(sec.start_ms, start);
        const secEnd = Math.min(sec.end_ms, end);
        if (secEnd <= secStart) return null;
        const x = msToX(secStart);
        const w = msToX(secEnd) - x;
        return (
          <rect
            key={sec.index}
            data-testid="section-tint"
            x={x}
            y={0}
            width={w}
            height={height}
            fill={KIND_COLORS[sec.kind] ?? '#94a3b820'}
          />
        );
      })}

      {/* Waveform bars — stroked vertical lines, one per sample */}
      {d && (
        <path
          d={d}
          fill="none"
          stroke={accent}
          strokeOpacity={0.85}
          strokeWidth={Math.max(0.8, (width / Math.max(visiblePeaks.length, 1)) * 0.7)}
          vectorEffect="non-scaling-stroke"
        />
      )}

      {/* Playhead — only render when inside visible window */}
      {playheadMs >= start && playheadMs <= end && (
        <line
          data-testid="playhead"
          x1={playheadX}
          y1={0}
          x2={playheadX}
          y2={height}
          stroke="white"
          strokeWidth={1.5}
          strokeOpacity={0.9}
        />
      )}
    </svg>
  );
}
