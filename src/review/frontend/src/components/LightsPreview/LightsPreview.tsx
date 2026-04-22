import React from 'react';
import styles from './LightsPreview.module.css';

interface LightsPreviewProps {
  n?: number;
  label?: string;
  compact?: boolean;
  energyPulse?: number;
  playhead?: number;
  accent?: string;
}

export function LightsPreview({
  n = 12,
  label,
  compact = false,
  energyPulse = 0,
  playhead = 0,
  accent = '#4ade80',
}: LightsPreviewProps) {
  const intensity = Math.max(0.15, energyPulse);

  return (
    <div className={styles.root}>
      <div className={styles.cells}>
        {Array.from({ length: n }, (_, i) => {
          const active = playhead > 0 && i / n < playhead;
          const brightness = active ? intensity : 0.15;
          return (
            <div
              key={i}
              data-testid="light-cell"
              className={styles.cell}
              style={{
                backgroundColor: accent,
                opacity: brightness,
              }}
            />
          );
        })}
      </div>
      {!compact && label && <span className={styles.label}>{label}</span>}
    </div>
  );
}
