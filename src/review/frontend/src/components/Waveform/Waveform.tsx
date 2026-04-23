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
  playheadMs?: number;
  durationMs?: number;
  sections?: Section[];
  width?: number;
  height?: number;
  accent?: string;
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

function buildPath(peaks: number[], width: number, height: number): string {
  if (!peaks.length) return '';
  const midY = height / 2;
  const step = width / peaks.length;
  const points: string[] = [];

  // Top half
  for (let i = 0; i < peaks.length; i++) {
    const x = i * step;
    const y = midY - peaks[i] * midY * 0.9;
    points.push(`${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  // Bottom half (mirrored)
  for (let i = peaks.length - 1; i >= 0; i--) {
    const x = i * step;
    const y = midY + peaks[i] * midY * 0.9;
    points.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  points.push('Z');
  return points.join(' ');
}

export function Waveform({
  peaks,
  playheadMs = 0,
  durationMs = 0,
  sections,
  width = 600,
  height = 80,
  accent = '#4ade80',
}: WaveformProps) {
  const playheadX = durationMs > 0 ? (playheadMs / durationMs) * width : 0;
  const d = buildPath(peaks, width, height);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
    >
      {/* Section tint rects */}
      {sections?.map((sec) => {
        if (!durationMs) return null;
        const x = (sec.start_ms / durationMs) * width;
        const w = ((sec.end_ms - sec.start_ms) / durationMs) * width;
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

      {/* Waveform path */}
      {d && <path d={d} fill={accent} fillOpacity={0.7} />}

      {/* Playhead */}
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
    </svg>
  );
}
