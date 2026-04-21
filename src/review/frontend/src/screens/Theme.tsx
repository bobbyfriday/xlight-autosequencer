import React, { useState } from 'react';
import styles from './Theme.module.css';
import { ThemeCard } from '../components/ThemeCard/ThemeCard';
import { LightsPreview } from '../components/LightsPreview/LightsPreview';
import { SectionStrip } from '../components/SectionStrip/SectionStrip';

interface Theme {
  theme_id: string;
  name: string;
  description: string;
  accent: string;
  swatches: string[];
  default_for_kinds: string[];
}

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

interface Song {
  song_id: string;
  title: string;
  status: string;
  duration_ms: number;
}

interface ThemeScreenProps {
  song: Song;
  themes: Theme[];
  sections: Section[];
  assignments: Assignment[];
  onThemed: () => void;
  onAssignmentChange: (assignment: Assignment) => void;
}

export function Theme({
  song,
  themes,
  sections,
  assignments,
  onThemed,
  onAssignmentChange,
}: ThemeScreenProps) {
  const [selectedSectionIdx, setSelectedSectionIdx] = useState(0);
  const [localAssignments, setLocalAssignments] = useState(assignments);
  const [error, setError] = useState<string | null>(null);

  const currentAssignment = localAssignments.find((a) => a.section_index === selectedSectionIdx);

  async function handleThemeSelect(themeId: string) {
    setError(null);
    try {
      const res = await fetch(
        `/api/v1/songs/${song.song_id}/assignments/${selectedSectionIdx}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ theme_id: themeId }),
        }
      );
      const body = await res.json();
      if (!res.ok) {
        setError(body?.error?.message ?? 'Failed to assign theme');
        return;
      }
      const updated = localAssignments.map((a) =>
        a.section_index === selectedSectionIdx
          ? { ...a, theme_id: themeId, user_confirmed: true }
          : a
      );
      setLocalAssignments(updated);
      onAssignmentChange(body.assignment);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error');
    }
  }

  async function handleAcceptAll() {
    setError(null);
    try {
      const res = await fetch(
        `/api/v1/songs/${song.song_id}/assignments/accept-all`,
        { method: 'POST' }
      );
      const body = await res.json();
      if (!res.ok) {
        setError(body?.error?.message ?? 'Failed to accept all');
        return;
      }
      if (body.song_status === 'themed') {
        onThemed();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error');
    }
  }

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <h2 className={styles.title}>{song.title}</h2>
        <button className={styles.acceptBtn} onClick={handleAcceptAll}>
          Accept All Defaults
        </button>
      </div>

      <SectionStrip
        sections={sections}
        assignments={localAssignments}
        durationMs={song.duration_ms}
        selectedIndex={selectedSectionIdx}
        onSelect={setSelectedSectionIdx}
      />

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.body}>
        <div className={styles.themeGrid}>
          {themes.map((theme) => (
            <ThemeCard
              key={theme.theme_id}
              theme={theme}
              assigned={currentAssignment?.theme_id === theme.theme_id}
              onClick={() => handleThemeSelect(theme.theme_id)}
            />
          ))}
        </div>

        <div className={styles.preview}>
          <LightsPreview
            n={20}
            label={sections[selectedSectionIdx]?.label ?? ''}
            accent={currentAssignment?.theme_id
              ? (themes.find((t) => t.theme_id === currentAssignment.theme_id)?.accent ?? '#4ade80')
              : '#555'
            }
            energyPulse={0.6}
          />
        </div>
      </div>
    </div>
  );
}
