import React, { useEffect, useState, useRef, useCallback } from 'react';
import styles from './Analyze.module.css';
import { MetadataBanner } from './MetadataBanner';

interface Song {
  song_id: string;
  title: string;
  artist?: string | null;
  override_artist?: string | null;
  override_title?: string | null;
  status: string;
  duration_ms: number;
  folder_id: string;
  imported_at: string;
  source_paths: string[];
}

interface GeniusLookup {
  section_source: string | null;
  match: { url: string; artist: string; title: string; genius_id?: number } | null;
  reject_reason: string | null;
}

interface DetectorRow {
  detector: string;
  library: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  progress?: number;
  confidence?: number;
  marks?: number;
  error?: string;
}

interface LogLine {
  text: string;
  kind: 'info' | 'ok' | 'err' | 'warn' | 'meta' | 'progress';
}

interface Section {
  label: string;
  kind: string;
  start_ms: number;
  end_ms: number;
}

interface Findings {
  beats: number;
  bars: number;
  sections: Section[];
  waveformDecoded: boolean;
  themesAssigned: boolean;
}

interface OverallState {
  status: string;
  progress: number;
  elapsed_ms?: number;
  eta_ms?: number;
}

interface AnalyzeProps {
  song: Song;
  /**
   * When true, run analysis on mount even if the song is already marked
   * 'analyzed'. Set by the App on re-drop of an existing library file.
   */
  forceOnMount?: boolean;
  /**
   * Notify the parent when the analysis state changes so it can refresh the
   * library rail status chip. Called with the latest song shape.
   */
  onAnalysisComplete?: (song: Song) => void;
  onComplete: () => void;
}

// 7 logical phases derived from SSE events
const PHASES = [
  { id: 'decode',    label: 'loading audio' },
  { id: 'stems',     label: 'separating stems' },
  { id: 'beats',     label: 'tracking beats' },
  { id: 'bars',      label: 'finding bars' },
  { id: 'structure', label: 'segmenting structure' },
  { id: 'story',     label: 'song story' },
  { id: 'themes',    label: 'assigning themes' },
];

// Map a detector name to a phase index
function detectorToPhaseIdx(detector: string, library: string): number {
  const d = detector.toLowerCase();
  const lib = (library ?? '').toLowerCase();
  if (d.includes('demucs') || d.includes('stems') || lib.includes('demucs')) return 1;
  if (d.includes('bar') || d.includes('downbeat') || lib.includes('qm_bars')) return 3;
  if (
    d.includes('madmom') ||
    d.includes('beat') ||
    d.includes('beatroot') ||
    lib.includes('madmom') ||
    lib.includes('librosa_beats')
  ) return 2;
  if (
    d.includes('qm_') ||
    d.includes('segmentino') ||
    d.includes('bbc_') ||
    d.includes('segment') ||
    lib.includes('segmentino') ||
    lib.includes('qm')
  ) return 4;
  if (d.includes('story') || d.includes('song story')) return 5;
  return 0;
}

const KIND_COLORS: Record<string, string> = {
  intro:   '#4aa8ff',
  verse:   '#4ade80',
  chorus:  '#f5a623',
  bridge:  '#d97757',
  outro:   '#888',
  drop:    '#d43a2f',
  build:   '#c084fc',
  solo:    '#facc15',
  default: '#a8a8b0',
};

function kindColor(kind: string): string {
  if (!kind) return KIND_COLORS.default;
  const k = kind.toLowerCase();
  for (const key of Object.keys(KIND_COLORS)) {
    if (k.includes(key)) return KIND_COLORS[key];
  }
  return KIND_COLORS.default;
}

function fmtDuration(ms: number): string {
  const s = Math.round(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, '0')}`;
}

export function Analyze({ song, forceOnMount = false, onAnalysisComplete, onComplete }: AnalyzeProps) {
  const [detectors, setDetectors] = useState<DetectorRow[]>([]);
  const [overall, setOverall] = useState<OverallState | null>(null);
  // If the song is already analyzed AND we weren't asked to re-analyze,
  // we render the compact "already analyzed" summary and skip the pipeline
  // entirely. `alreadyAnalyzedAtMount` is a sticky marker — we use it to
  // pick a cleaner summary layout instead of the live-analysis layout with
  // empty phase strips and a "waiting for detectors" message.
  const alreadyAnalyzedAtMount = useRef(
    !forceOnMount && (song.status === 'analyzed' || song.status === 'themed')
  ).current;
  const [analysisComplete, setAnalysisComplete] = useState(alreadyAnalyzedAtMount);
  const [error, setError] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  // Genius provenance: populated either by the `genius_lookup` SSE event
  // during an in-flight run, or by fetching /analysis for an already-completed
  // one. Null means "we haven't heard yet" (not "Genius didn't run").
  const [geniusLookup, setGeniusLookup] = useState<GeniusLookup | null>(null);
  // Local copy of the song's override fields so MetadataBanner updates
  // feel instantaneous without requiring a parent-level library re-fetch.
  const [localOverrideArtist, setLocalOverrideArtist] = useState<string | null>(
    song.override_artist ?? null,
  );
  const [localOverrideTitle, setLocalOverrideTitle] = useState<string | null>(
    song.override_title ?? null,
  );
  const [findings, setFindings] = useState<Findings>({
    beats: 0,
    bars: 0,
    sections: [],
    waveformDecoded: false,
    themesAssigned: false,
  });
  const [elapsedMs, setElapsedMs] = useState(0);

  const esRef = useRef<EventSource | null>(null);
  // Seed forceRef with forceOnMount so the initial POST /analyze carries
  // force=true when the parent asked for a re-run (set on re-drop).
  const forceRef = useRef(forceOnMount);
  const startTimeRef = useRef<number | null>(null);
  const elapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const logRef = useRef<HTMLDivElement | null>(null);

  function handleReanalyze() {
    esRef.current?.close();
    if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    forceRef.current = true;
    setDetectors([]);
    setOverall(null);
    setError(null);
    setAnalysisComplete(false);
    setLogLines([]);
    setFindings({ beats: 0, bars: 0, sections: [], waveformDecoded: false, themesAssigned: false });
    setElapsedMs(0);
    startTimeRef.current = null;
  }

  // Fetch sections on complete
  const fetchSections = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/songs/${song.song_id}/analysis`);
      if (!res.ok) return;
      const data = await res.json();
      const secs: Section[] = (data?.sections ?? data?.song_story?.sections ?? []).map(
        (s: { label?: string; kind?: string; start_ms?: number; end_ms?: number; start?: number; end?: number }) => ({
          label: s.label ?? s.kind ?? 'section',
          kind: s.kind ?? '',
          start_ms: s.start_ms ?? (s.start ? s.start * 1000 : 0),
          end_ms: s.end_ms ?? (s.end ? s.end * 1000 : 0),
        })
      );
      if (secs.length > 0) {
        setFindings((prev) => ({ ...prev, sections: secs, themesAssigned: true }));
      }
      // Genius provenance — populated for completed runs; SSE stream delivered
      // it live for in-flight runs. Either path ends up here.
      if (data?.section_source !== undefined
          || data?.genius_match !== undefined
          || data?.section_source_reject_reason !== undefined) {
        setGeniusLookup({
          section_source: data?.section_source ?? null,
          match: data?.genius_match ?? null,
          reject_reason: data?.section_source_reject_reason ?? null,
        });
      }
    } catch {}
  }, [song.song_id]);

  useEffect(() => {
    if (analysisComplete) {
      if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
      fetchSections();
      return;
    }

    async function startAnalysis() {
      try {
        const res = await fetch(`/api/v1/songs/${song.song_id}/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ force: forceRef.current }),
        });
        forceRef.current = false;
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          setError(body?.error?.message ?? `Analysis failed (${res.status})`);
          return;
        }

        startTimeRef.current = Date.now();
        elapsedTimerRef.current = setInterval(() => {
          if (startTimeRef.current != null) {
            setElapsedMs(Date.now() - startTimeRef.current);
          }
        }, 250);

        // Open SSE stream
        const es = new EventSource(`/api/v1/songs/${song.song_id}/analyze/status`);
        esRef.current = es;

        es.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);

            if (data.overall) {
              const ov: OverallState = {
                status: data.overall.status,
                progress: data.overall.progress ?? 0,
                elapsed_ms: data.overall.elapsed_ms,
                eta_ms: data.overall.eta_ms,
              };
              setOverall(ov);
              if (data.overall.elapsed_ms != null) {
                setElapsedMs(data.overall.elapsed_ms);
              }
              const pct = Math.round((ov.progress ?? 0) * 100);
              setLogLines((prev) => [
                ...prev,
                { text: `  ${pct}% · ${Math.round((ov.elapsed_ms ?? 0) / 1000)}s`, kind: 'progress' },
              ]);
              if (data.overall.status === 'done') {
                setAnalysisComplete(true);
                setFindings((prev) => ({ ...prev, waveformDecoded: true, themesAssigned: true }));
                // Update the parent so the library rail status chip turns
                // green without needing a library re-fetch.
                onAnalysisComplete?.({ ...song, status: 'analyzed' });
                if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
                es.close();
              } else if (data.overall.status === 'failed') {
                setError(data.overall.error ?? 'Analysis failed');
                if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
                es.close();
              }
            } else if (data.detector) {
              const det: DetectorRow = {
                detector: data.detector,
                library: data.library ?? '',
                status: data.status,
                progress: data.progress,
                confidence: data.confidence,
                marks: data.marks,
                error: data.error,
              };

              setDetectors((prev) => {
                const existing = prev.findIndex((d) => d.detector === data.detector);
                if (existing >= 0) {
                  const next = [...prev];
                  next[existing] = det;
                  return next;
                }
                return [...prev, det];
              });

              // Derive findings
              if (data.status === 'done' && data.marks != null) {
                const d = data.detector.toLowerCase();
                if (d.includes('beat') || d.includes('madmom')) {
                  setFindings((prev) => ({ ...prev, beats: Math.max(prev.beats, data.marks as number), waveformDecoded: true }));
                } else if (d.includes('bar') || d.includes('downbeat')) {
                  setFindings((prev) => ({ ...prev, bars: Math.max(prev.bars, data.marks as number) }));
                }
              }
              if (data.status === 'running' && data.detector.toLowerCase() === 'decode') {
                setFindings((prev) => ({ ...prev, waveformDecoded: false }));
              }

              // Build log line
              if (data.status === 'running') {
                setLogLines((prev) => [...prev, { text: `› ${data.detector}: running…`, kind: 'info' }]);
              } else if (data.status === 'done') {
                const marksStr = data.marks != null ? ` · ${data.marks} marks` : '';
                setLogLines((prev) => [...prev, { text: `✓ ${data.detector}${marksStr}`, kind: 'ok' }]);
              } else if (data.status === 'failed') {
                setLogLines((prev) => [
                  ...prev,
                  { text: `✗ ${data.detector}: ${data.error ?? 'failed'}`, kind: 'err' },
                ]);
              }
            } else if (data.genius_lookup) {
              setGeniusLookup({
                section_source: data.genius_lookup.section_source ?? null,
                match: data.genius_lookup.match ?? null,
                reject_reason: data.genius_lookup.reject_reason ?? null,
              });
            } else if (data.log) {
              const kind = data.log.level === 'error' ? 'err'
                : data.log.level === 'warn' ? 'warn'
                : 'info';
              setLogLines((prev) => [...prev, { text: data.log.message, kind: kind as LogLine['kind'] }]);
            }
          } catch {}
        };

        es.onerror = () => {
          es.close();
        };
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Network error');
      }
    }

    startAnalysis();

    return () => {
      esRef.current?.close();
      if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    };
  }, [song.song_id, analysisComplete, fetchSections]);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logLines.length]);

  const progress = overall?.progress ?? 0;
  const elapsedSec = Math.round(elapsedMs / 1000);
  const etaSec = overall?.eta_ms != null ? Math.round(overall.eta_ms / 1000) : null;
  const pct = Math.round(progress * 100);
  const canSkip = progress >= 0.4 || analysisComplete;

  // Compute active phase from detectors
  const activePhaseIdx = React.useMemo(() => {
    if (analysisComplete) return PHASES.length - 1;
    const running = detectors.find((d) => d.status === 'running');
    if (running) return detectorToPhaseIdx(running.detector, running.library);
    const lastDone = [...detectors].reverse().find((d) => d.status === 'done');
    if (lastDone) {
      const idx = detectorToPhaseIdx(lastDone.detector, lastDone.library);
      return Math.min(idx + 1, PHASES.length - 1);
    }
    return 0;
  }, [detectors, analysisComplete]);

  const doneCount = detectors.filter((d) => d.status === 'done').length;

  // Compact "already analyzed" view: when the user lands on Analyze for a
  // song that was analyzed in a previous session, the live-analysis layout
  // (phase strip, detector panel, findings inspector) has no fresh data to
  // show — the SSE stream was never opened — and it renders empty bars and
  // a "waiting for detectors…" message which reads as "stuck halfway". We
  // bypass all of that and show a summary card instead.
  if (alreadyAnalyzedAtMount && !error) {
    return (
      <div data-testid="analyze-screen" className={styles.root}>
        <div className={styles.header}>
          <div className={styles.headerTitle}>Analysis complete</div>
          <div className={styles.headerMeta}>
            {song.title} · {fmtDuration(song.duration_ms)}
          </div>
          <div className={styles.spacer} />
          <button className={styles.reviewBtn} onClick={onComplete}>
            ▶ review timeline →
          </button>
        </div>
        <MetadataBanner
          songId={song.song_id}
          id3Title={song.title}
          id3Artist={song.artist ?? ''}
          overrideArtist={localOverrideArtist}
          overrideTitle={localOverrideTitle}
          genius={geniusLookup}
          onSaved={(next) => {
            setLocalOverrideArtist(next.override_artist);
            setLocalOverrideTitle(next.override_title);
          }}
        />

        <div style={{
          padding: '24px 32px',
          color: 'var(--color-text-muted, #888)',
          fontSize: 14,
          lineHeight: 1.6,
        }}>
          This song was analyzed in a previous session. Open the timeline to review it,
          or re-analyze to run the pipeline again.
          {findings.sections.length > 0 && (
            <>
              <div style={{ marginTop: 16, fontWeight: 600, color: 'var(--color-text, #f5f5f0)' }}>
                {findings.sections.length} sections detected
              </div>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 6,
                marginTop: 8,
              }}>
                {findings.sections.map((s, i) => (
                  <span key={i} style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: 'rgba(255,255,255,0.05)',
                    border: `1px solid ${kindColor(s.kind)}`,
                    color: 'var(--color-text, #f5f5f0)',
                    fontSize: 12,
                  }}>
                    {s.label}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>

        <div className={styles.reanalyzeRow}>
          <button className={styles.reanalyzeBtn} onClick={handleReanalyze}>
            Re-analyze
          </button>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="analyze-screen" className={styles.root}>
      {/* Header row */}
      <div className={styles.header}>
        <div className={styles.headerTitle}>
          {analysisComplete ? 'Analysis complete' : 'Analyzing…'}
        </div>
        <div className={styles.headerMeta}>
          {song.title} · {fmtDuration(song.duration_ms)}
        </div>
        <div className={styles.spacer} />
        {!analysisComplete && (
          <>
            <div className={styles.elapsedText}>
              {elapsedSec}s{etaSec != null ? ` / ~${etaSec}s` : ''}
            </div>
            <button
              className={styles.skipBtn}
              disabled={!canSkip}
              onClick={onComplete}
              title={canSkip ? 'skip to review timeline' : 'wait for sections to detect'}
            >
              skip to timeline →
            </button>
          </>
        )}
        {analysisComplete && (
          <button className={styles.reviewBtn} onClick={onComplete}>
            ▶ review timeline →
          </button>
        )}
      </div>

      <MetadataBanner
        songId={song.song_id}
        id3Title={song.title}
        id3Artist={song.artist ?? ''}
        overrideArtist={localOverrideArtist}
        overrideTitle={localOverrideTitle}
        genius={geniusLookup}
        onSaved={(next) => {
          setLocalOverrideArtist(next.override_artist);
          setLocalOverrideTitle(next.override_title);
        }}
      />

      {error && (
        <div className={styles.errorBox}>
          <span className={styles.errorText}>{error}</span>
          <button className={styles.reanalyzeBtn} onClick={handleReanalyze}>
            Try Again
          </button>
        </div>
      )}

      {/* Phase timeline strip */}
      <div className={styles.phaseStrip}>
        {PHASES.map((phase, i) => {
          const isDone = analysisComplete || i < activePhaseIdx;
          const isActive = !analysisComplete && i === activePhaseIdx;
          const isPending = !isDone && !isActive;
          const fillPct = isDone ? 100 : isActive ? pct : 0;
          return (
            <div
              key={phase.id}
              className={[
                styles.phaseCard,
                isDone ? styles.phaseCardDone : '',
                isActive ? styles.phaseCardActive : '',
                isPending ? styles.phaseCardPending : '',
              ].join(' ')}
            >
              <div className={styles.phaseCardInner}>
                <span className={[styles.phaseGlyph, isDone ? styles.phaseGlyphDone : isActive ? styles.phaseGlyphActive : styles.phaseGlyphPending].join(' ')}>
                  {isDone ? '✓' : isActive ? '●' : String(i + 1).padStart(2, '0')}
                </span>
                <span className={[styles.phaseLabel, isActive ? styles.phaseLabelActive : ''].join(' ')}>
                  {phase.label}
                </span>
              </div>
              <div className={styles.phaseBar}>
                <i
                  className={styles.phaseBarFill}
                  style={{
                    width: `${fillPct}%`,
                    background: isDone ? 'var(--ok, #4ade80)' : 'var(--accent, #4ade80)',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Three-column body */}
      <div className={styles.body}>
        {/* Left: detector list */}
        <div className={styles.detectorPanel}>
          <div className={styles.panelHeader}>
            DETECTORS · {doneCount} / {detectors.length} done
          </div>
          <div className={styles.detectorList}>
            {detectors.length === 0 && (
              <div className={styles.emptyNote}>waiting for detectors…</div>
            )}
            {detectors.map((d) => {
              const isDone = d.status === 'done';
              const isRunning = d.status === 'running';
              const glyph = isDone ? '✓' : isRunning ? '●' : '○';
              const fillPct = isDone ? 100 : isRunning ? ((d.progress ?? 0) * 100) : 0;
              return (
                <div
                  key={d.detector}
                  className={[
                    styles.detectorRow,
                    isDone ? styles.detectorDone : '',
                    isRunning ? styles.detectorRunning : '',
                    d.status === 'queued' ? styles.detectorQueued : '',
                  ].join(' ')}
                >
                  <div className={styles.detectorRowTop}>
                    <span className={[styles.detectorGlyph, isDone ? styles.glyphDone : isRunning ? styles.glyphRunning : styles.glyphPending].join(' ')}>
                      {glyph}
                    </span>
                    <span className={styles.detectorName}>{d.detector}</span>
                    {d.library && (
                      <span className={styles.detectorLib}>{d.library}</span>
                    )}
                    <span className={styles.detectorMarks}>
                      {d.marks != null ? d.marks : isRunning ? '…' : '—'}
                    </span>
                  </div>
                  <div className={styles.detectorBarTrack}>
                    <i
                      className={styles.detectorBarFill}
                      style={{
                        width: `${fillPct}%`,
                        background: isDone ? 'var(--ok, #4ade80)' : 'var(--accent, #4ade80)',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Center: console log */}
        <div className={styles.consolePanel}>
          <div className={styles.panelHeader}>
            STREAM · {logLines.length} lines
          </div>
          <div className={styles.consoleBody} ref={logRef}>
            {logLines.map((line, i) => (
              <div
                key={i}
                className={[
                  styles.logLine,
                  line.kind === 'ok' ? styles.logOk : '',
                  line.kind === 'err' ? styles.logErr : '',
                  line.kind === 'warn' ? styles.logWarn : '',
                  line.kind === 'meta' ? styles.logMeta : '',
                  line.kind === 'progress' ? styles.logProgress : '',
                ].join(' ')}
              >
                {line.text}
              </div>
            ))}
            <div className={styles.cursor}>▋</div>
          </div>
        </div>

        {/* Right: findings inspector */}
        <div className={styles.inspector}>
          <div className={styles.inspectorHeader}>
            <span>FINDINGS</span>
            <span className={analysisComplete ? styles.statusDone : styles.statusLive}>
              {analysisComplete ? '✓ DONE' : '● LIVE'}
            </span>
          </div>

          {/* Big % + progress */}
          <div className={styles.inspectorProgress}>
            <div className={styles.inspectorPctRow}>
              <span
                className={styles.inspectorPct}
                style={{ color: analysisComplete ? 'var(--ok, #4ade80)' : 'var(--accent, #4ade80)' }}
              >
                {pct}%
              </span>
              <span className={styles.inspectorTime}>
                {elapsedSec}s{etaSec != null ? ` / ~${etaSec}s` : ''}
              </span>
            </div>
            <div className={styles.inspectorBar}>
              <i
                className={styles.inspectorBarFill}
                style={{
                  width: `${pct}%`,
                  background: analysisComplete ? 'var(--ok, #4ade80)' : 'var(--accent, #4ade80)',
                }}
              />
            </div>
            <div className={styles.inspectorPhaseLabel}>
              {analysisComplete ? 'all detectors complete' : PHASES[activePhaseIdx]?.label ?? ''}
            </div>
          </div>

          {/* Detected checklist */}
          <div className={styles.inspectorSection}>
            <div className={styles.inspectorSectionHeader}>DETECTED</div>
            {(
              [
                ['waveform', findings.waveformDecoded ? '✓' : '—', findings.waveformDecoded],
                ['beats', findings.beats > 0 ? String(findings.beats) : '—', findings.beats > 0],
                ['bars', findings.bars > 0 ? String(findings.bars) : '—', findings.bars > 0],
                ['sections', findings.sections.length > 0 ? String(findings.sections.length) : '—', findings.sections.length > 0],
                ['themes', findings.themesAssigned ? '✓' : '—', findings.themesAssigned],
              ] as [string, string, boolean][]
            ).map(([key, val, has]) => (
              <div key={key} className={styles.detectedRow}>
                <span className={has ? styles.detectedGlyphHas : styles.detectedGlyphNot}>
                  {has ? '✓' : '·'}
                </span>
                <span className={has ? styles.detectedKey : styles.detectedKeyDim}>{key}</span>
                <span className={has ? styles.detectedVal : styles.detectedValDim}>{val}</span>
              </div>
            ))}
          </div>

          {/* Sections list */}
          <div className={styles.inspectorSectionsWrap}>
            <div className={styles.inspectorSectionHeader}>
              SECTIONS · {findings.sections.length}
            </div>
            {findings.sections.length === 0 && (
              <div className={styles.emptyNote}>waiting for structure…</div>
            )}
            {findings.sections.map((s, i) => (
              <div key={i} className={styles.sectionRow}>
                <i
                  className={styles.sectionDot}
                  style={{ background: kindColor(s.kind) }}
                />
                <span className={styles.sectionIdx}>{String(i + 1).padStart(2, '0')}</span>
                <span className={styles.sectionLabel}>{s.label}</span>
                <span className={styles.sectionDur}>
                  {Math.round((s.end_ms - s.start_ms) / 1000)}s
                </span>
              </div>
            ))}
          </div>

          {/* Bottom button */}
          <div className={styles.inspectorFooter}>
            <button
              className={[styles.inspectorBtn, canSkip ? styles.inspectorBtnActive : styles.inspectorBtnDisabled].join(' ')}
              disabled={!canSkip}
              onClick={onComplete}
            >
              {analysisComplete ? '▶ REVIEW TIMELINE →' : canSkip ? 'SKIP TO TIMELINE →' : 'WAITING…'}
            </button>
          </div>
        </div>
      </div>

      {/* Re-analyze action (shown when complete) */}
      {analysisComplete && (
        <div className={styles.reanalyzeRow}>
          <button className={styles.reanalyzeBtn} onClick={handleReanalyze}>
            Re-analyze
          </button>
        </div>
      )}
    </div>
  );
}
