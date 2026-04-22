import React, { useState } from 'react';
import styles from './Timeline.module.css';
import { Transport } from '../components/Transport/Transport';
import { Waveform } from '../components/Waveform/Waveform';
import { Ruler } from '../components/Ruler/Ruler';
import { SectionStrip } from '../components/SectionStrip/SectionStrip';
import { LightsPreview } from '../components/LightsPreview/LightsPreview';
import { usePlaybackStore } from '../store/playback';

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

interface Analysis {
  song_id: string;
  detected_sections: Section[];
  peaks: number[];
  beats: { t_ms: number; bar: number; beat: number }[];
  detectors: { name: string; library: string; status: string; confidence: number | null; error: string | null }[];
  completed_at: string;
  [key: string]: unknown;
}

interface Song {
  song_id: string;
  title: string;
  status: string;
  duration_ms: number;
  source_paths: string[];
  [key: string]: unknown;
}

interface TimelineProps {
  song: Song;
  analysis: Analysis;
  assignments: Assignment[];
  onNavigateTheme?: () => void;
}

export function Timeline({ song, analysis, assignments, onNavigateTheme }: TimelineProps) {
  const { playing, timeMs, play, pause, seekMs } = usePlaybackStore();
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const sections = analysis.detected_sections;

  function handlePrevSection() {
    const idx = Math.max(0, selectedIndex - 1);
    setSelectedIndex(idx);
    seekMs(sections[idx]?.start_ms ?? 0);
  }

  function handleNextSection() {
    const idx = Math.min(sections.length - 1, selectedIndex + 1);
    setSelectedIndex(idx);
    seekMs(sections[idx]?.start_ms ?? 0);
  }

  const currentAssignment = assignments.find((a) => a.section_index === selectedIndex);

  return (
    <div className={styles.root}>
      <Transport
        playing={playing}
        timeMs={timeMs}
        durationMs={song.duration_ms}
        onPlay={play}
        onPause={pause}
        onPrevSection={handlePrevSection}
        onNextSection={handleNextSection}
      />

      <div className={styles.waveformArea}>
        <Waveform
          peaks={analysis.peaks}
          playheadMs={timeMs}
          durationMs={song.duration_ms}
          sections={sections}
          accent="#4ade80"
        />
        <Ruler
          durationMs={song.duration_ms}
          playheadMs={timeMs}
          onSeek={seekMs}
        />
      </div>

      <SectionStrip
        sections={sections}
        assignments={assignments}
        durationMs={song.duration_ms}
        selectedIndex={selectedIndex}
        onSelect={setSelectedIndex}
      />

      <div className={styles.previewRow}>
        <LightsPreview
          n={16}
          label={sections[selectedIndex]?.label ?? ''}
          energyPulse={0.5}
          accent={currentAssignment?.theme_id ? '#4ade80' : '#555'}
        />
      </div>

      {onNavigateTheme && (
        <button className={styles.themeBtn} onClick={onNavigateTheme}>
          Go to Theme →
        </button>
      )}
    </div>
  );
}
