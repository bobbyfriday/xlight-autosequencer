import React from 'react';
import styles from './MiniLights.module.css';

interface MiniLightsProps {
  themeId: string;
  kind: string;
  swatches?: string[];
}

// Deterministic color selection keyed on themeId + kind
function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

const DEFAULT_SWATCHES = ['#4ade80', '#38bdf8', '#facc15', '#f97316'];
const N_CELLS = 8;

export function MiniLights({ themeId, kind, swatches }: MiniLightsProps) {
  const palette = swatches ?? DEFAULT_SWATCHES;
  const seed = hashCode(`${themeId}:${kind}`);

  return (
    <div className={styles.root}>
      {Array.from({ length: N_CELLS }, (_, i) => {
        const colorIdx = (seed + i * 3) % palette.length;
        const opacity = 0.4 + (((seed + i * 7) % 60) / 100);
        return (
          <div
            key={i}
            data-testid="mini-light"
            className={styles.dot}
            style={{ backgroundColor: palette[colorIdx], opacity }}
          />
        );
      })}
    </div>
  );
}
