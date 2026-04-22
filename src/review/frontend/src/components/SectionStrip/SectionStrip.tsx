import React from 'react';
import styles from './SectionStrip.module.css';

interface Section {
  index: number;
  start_ms: number;
  end_ms: number;
  kind: string;
  label: string;
}

interface Assignment {
  section_index: number;
  theme_id: string | null;
  overrides: Record<string, number>;
  user_confirmed: boolean;
}

interface SectionStripProps {
  sections: Section[];
  assignments: Assignment[];
  durationMs: number;
  selectedIndex?: number;
  onSelect?: (index: number) => void;
}

// Accent colors per theme_id
const THEME_ACCENTS: Record<string, string> = {
  'shimmer-wash': '#4ade80',
  'driving-pulse': '#d97757',
  'peak-flash': '#facc15',
  'solo-chase': '#38bdf8',
  'bridge-burn': '#f97316',
  'neutral-glow': '#e2e8f0',
};

export function SectionStrip({
  sections,
  assignments,
  durationMs,
  selectedIndex,
  onSelect,
}: SectionStripProps) {
  const assignmentByIndex = Object.fromEntries(
    assignments.map((a) => [a.section_index, a])
  );

  return (
    <div className={styles.strip}>
      {sections.map((sec) => {
        const duration = sec.end_ms - sec.start_ms;
        const widthPct = durationMs > 0 ? (duration / durationMs) * 100 : 0;
        const assignment = assignmentByIndex[sec.index];
        const accent = assignment?.theme_id
          ? (THEME_ACCENTS[assignment.theme_id] ?? '#555')
          : '#555';
        const isSelected = selectedIndex === sec.index;

        return (
          <button
            key={sec.index}
            data-testid="section-chip"
            data-selected={isSelected ? 'true' : 'false'}
            className={`${styles.chip} ${isSelected ? styles.selected : ''}`}
            style={{
              width: `${widthPct}%`,
              borderColor: accent,
            }}
            onClick={() => onSelect?.(sec.index)}
            title={sec.label}
          >
            <span className={styles.chipLabel}>{sec.label}</span>
          </button>
        );
      })}
    </div>
  );
}
