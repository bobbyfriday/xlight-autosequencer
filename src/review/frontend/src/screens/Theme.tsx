import React, { useState } from 'react';
import styles from './Theme.module.css';
import { ThemeCard } from '../components/ThemeCard/ThemeCard';
import { LightsPreview } from '../components/LightsPreview/LightsPreview';
import { SectionStrip } from '../components/SectionStrip/SectionStrip';
import { Inspector } from '../components/Inspector/Inspector';
import { ParameterSliders, ParameterOverrides } from '../components/ParameterSliders/ParameterSliders';

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

const DEFAULT_OVERRIDES: ParameterOverrides = {
  brightness: 1.0,
  hit_strength: 1.0,
  dwell_time: 1.0,
  color_shift: 0.0,
};

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
  // Live override state for immediate preview — no round-trip needed
  const [liveOverrides, setLiveOverrides] = useState<ParameterOverrides>(DEFAULT_OVERRIDES);

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
          ? { ...body.assignment }
          : a
      );
      setLocalAssignments(updated);
      // Reset live overrides to defaults on theme change (FR-032a)
      setLiveOverrides(body.assignment.overrides ?? DEFAULT_OVERRIDES);
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
        onSelect={(idx) => {
          setSelectedSectionIdx(idx);
          const a = localAssignments.find((a) => a.section_index === idx);
          setLiveOverrides(
            a?.overrides && Object.keys(a.overrides).length > 0
              ? (a.overrides as ParameterOverrides)
              : DEFAULT_OVERRIDES
          );
        }}
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
            energyPulse={0.6 * liveOverrides.brightness}
          />
        </div>

        <Inspector title="Section Parameters">
          {currentAssignment?.theme_id && (
            <ParameterSliders
              songId={song.song_id}
              sectionIdx={selectedSectionIdx}
              themeId={currentAssignment.theme_id}
              overrides={
                currentAssignment.overrides && Object.keys(currentAssignment.overrides).length > 0
                  ? (currentAssignment.overrides as ParameterOverrides)
                  : DEFAULT_OVERRIDES
              }
              onOverridesChange={(updated) => {
                setLiveOverrides(updated);
                // Update local assignment overrides for persistence on next theme action
                const next = localAssignments.map((a) =>
                  a.section_index === selectedSectionIdx
                    ? { ...a, overrides: updated }
                    : a
                );
                setLocalAssignments(next);
              }}
            />
          )}
        </Inspector>
      </div>
    </div>
  );
}
