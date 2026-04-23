import React, { useEffect, useRef, useState } from 'react';
import styles from './ParameterSliders.module.css';
import { apiFetch } from 'src/lib/apiClient';

export interface ParameterOverrides {
  brightness: number;
  hit_strength: number;
  dwell_time: number;
  color_shift: number;
}

interface ParameterSlidersProps {
  songId: string;
  sectionIdx: number;
  themeId: string;
  overrides: ParameterOverrides;
  onOverridesChange: (overrides: ParameterOverrides) => void;
}

const SLIDER_DEFS = [
  { field: 'brightness' as const,   label: 'Brightness',  min: 0, max: 2, step: 0.05 },
  { field: 'hit_strength' as const, label: 'Hit Strength', min: 0, max: 2, step: 0.05 },
  { field: 'dwell_time' as const,   label: 'Dwell Time',  min: 0, max: 2, step: 0.05 },
  { field: 'color_shift' as const,  label: 'Color Shift', min: 0, max: 1, step: 0.05 },
] as const;

export function ParameterSliders({
  songId,
  sectionIdx,
  themeId,
  overrides,
  onOverridesChange,
}: ParameterSlidersProps) {
  const [local, setLocal] = useState<ParameterOverrides>(overrides);
  const prevThemeIdRef = useRef(themeId);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Track whether a change was triggered by a themeId change (suppress PUT)
  const suppressNextPutRef = useRef(false);

  // Sync local state when overrides prop changes (e.g. after theme change resets on server)
  useEffect(() => {
    const themeChanged = prevThemeIdRef.current !== themeId;
    prevThemeIdRef.current = themeId;
    if (themeChanged) {
      // Cancel any pending debounced PUT from before the theme change
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      suppressNextPutRef.current = true;
    }
    setLocal(overrides);
  }, [overrides, themeId]);

  function handleChange(field: keyof ParameterOverrides, value: number) {
    const updated = { ...local, [field]: value };
    setLocal(updated);
    onOverridesChange(updated);
    schedulePut(updated);
  }

  function schedulePut(updated: ParameterOverrides) {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    if (suppressNextPutRef.current) {
      suppressNextPutRef.current = false;
      return;
    }
    debounceTimerRef.current = setTimeout(() => {
      debounceTimerRef.current = null;
      apiFetch(`/api/v1/songs/${songId}/assignments/${sectionIdx}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ overrides: updated }),
      });
    }, 300);
  }

  return (
    <div className={styles.root}>
      {SLIDER_DEFS.map(({ field, label, min, max, step }) => (
        <div key={field} className={styles.row}>
          <label className={styles.label} htmlFor={`slider-${field}`}>
            {label}
          </label>
          <input
            id={`slider-${field}`}
            type="range"
            min={min}
            max={max}
            step={step}
            value={local[field]}
            onChange={(e) => handleChange(field, parseFloat(e.target.value))}
            className={styles.slider}
          />
          <span className={styles.value}>
            {parseFloat(local[field].toFixed(2))}
          </span>
        </div>
      ))}
    </div>
  );
}
