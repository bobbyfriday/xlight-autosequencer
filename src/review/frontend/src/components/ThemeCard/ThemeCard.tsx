import React from 'react';
import styles from './ThemeCard.module.css';

interface Theme {
  theme_id: string;
  name: string;
  description: string;
  accent: string;
  swatches: string[];
  default_for_kinds: string[];
}

interface ThemeCardProps {
  theme: Theme;
  assigned?: boolean;
  onClick?: () => void;
}

export function ThemeCard({ theme, assigned = false, onClick }: ThemeCardProps) {
  return (
    <div
      data-testid="theme-card"
      data-assigned={String(assigned)}
      className={`${styles.card} ${assigned ? styles.assigned : ''}`}
      style={{ borderColor: assigned ? theme.accent : 'transparent' }}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
    >
      {/* Swatches row */}
      <div className={styles.swatchRow}>
        {theme.swatches.map((color, i) => (
          <div
            key={i}
            data-testid="swatch"
            className={styles.swatch}
            style={{ backgroundColor: color }}
          />
        ))}
      </div>

      {/* Name + ASSIGNED pill */}
      <div className={styles.nameRow}>
        <span className={styles.name}>{theme.name}</span>
        {assigned && (
          <span className={styles.assignedPill}>Assigned</span>
        )}
      </div>

      {/* Description */}
      <p className={styles.description}>{theme.description}</p>
    </div>
  );
}
