import React, { useEffect, useState } from 'react';
import styles from './StemWaveforms.module.css';

interface StemWaveformsProps {
  songId: string;
  durationMs: number;
  playheadMs: number;
  viewStartMs?: number;
  viewEndMs?: number;
  onSeek?: (ms: number) => void;
}

const STEM_COLORS: Record<string, string> = {
  drums:  '#f97316',
  bass:   '#38bdf8',
  vocals: '#a78bfa',
  guitar: '#4ade80',
  piano:  '#facc15',
  other:  '#94a3b8',
};

const STEM_ORDER = ['drums', 'bass', 'vocals', 'guitar', 'piano', 'other'];

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

export function StemWaveforms({ songId, durationMs, playheadMs, viewStartMs, viewEndMs, onSeek }: StemWaveformsProps) {
  const [open, setOpen] = useState(false);
  const [stems, setStems] = useState<Record<string, number[]>>({});
  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  useEffect(() => {
    if (!open || fetched) return;
    setLoading(true);
    fetch(`/api/v1/songs/${songId}/stem-peaks`)
      .then(r => r.json())
      .then(data => {
        setStems(data.stems ?? {});
        setFetched(true);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [open, songId, fetched]);

  const start = viewStartMs ?? 0;
  const end = viewEndMs ?? durationMs;
  const windowMs = end - start || durationMs;

  function handleSeek(e: React.MouseEvent<SVGSVGElement>) {
    if (!onSeek) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const ms = start + ratio * windowMs;
    onSeek(Math.max(0, Math.min(durationMs, ms)));
  }

  const availableStems = STEM_ORDER.filter(name => stems[name]?.length > 0);
  const hasStemData = availableStems.length > 0;

  return (
    <div className={styles.root}>
      <button className={styles.header} onClick={() => setOpen(o => !o)}>
        <span className={styles.arrow}>{open ? '▾' : '▸'}</span>
        <span className={styles.title}>STEM WAVEFORMS</span>
        {!open && hasStemData && (
          <span className={styles.badge}>{availableStems.length} stems</span>
        )}
        {!open && !fetched && (
          <span className={styles.hint}>click to load</span>
        )}
      </button>

      {open && (
        <div className={styles.body}>
          {loading && <div className={styles.loading}>Loading stems…</div>}
          {!loading && !hasStemData && fetched && (
            <div className={styles.empty}>No stem cache found — re-analyze with Demucs enabled to generate stems.</div>
          )}
          {availableStems.map(name => {
            const allPeaks = stems[name];
            // Slice to visible window
            const startFrac = start / durationMs;
            const endFrac = end / durationMs;
            const lo = Math.floor(startFrac * allPeaks.length);
            const hi = Math.ceil(endFrac * allPeaks.length);
            const visiblePeaks = (viewStartMs !== undefined) ? allPeaks.slice(lo, hi) : allPeaks;

            const playheadPct = windowMs > 0 ? ((playheadMs - start) / windowMs) * 100 : 0;
            const playheadVisible = playheadMs >= start && playheadMs <= end;
            const color = STEM_COLORS[name] ?? '#94a3b8';
            const d = buildPath(visiblePeaks, 1000, 40);

            return (
              <div key={name} className={styles.stemRow}>
                <div className={styles.stemLabel} style={{ color }}>
                  {name}
                </div>
                <div className={styles.stemTrack}>
                  <svg
                    viewBox="0 0 1000 40"
                    width="100%"
                    height="40"
                    preserveAspectRatio="none"
                    onClick={onSeek ? handleSeek : undefined}
                    style={onSeek ? { cursor: 'pointer' } : undefined}
                  >
                    {d && (
                      <path
                        d={d}
                        fill="none"
                        stroke={color}
                        strokeOpacity={0.8}
                        strokeWidth={Math.max(0.8, (1000 / Math.max(visiblePeaks.length, 1)) * 0.7)}
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                    {playheadVisible && (
                      <line x1={playheadPct * 10} y1={0} x2={playheadPct * 10} y2={40}
                        stroke="white" strokeWidth={1.5} strokeOpacity={0.8} />
                    )}
                  </svg>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
