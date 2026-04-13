# Data Model: Intelligent Stem Analysis and Automated Light Sequencing Pipeline

**Feature**: 012-intelligent-stem-sweep
**Date**: 2026-03-23

## Existing Entities (Extended)

### StemMetrics (existing — `src/analyzer/stem_inspector.py`)

Already defined. No changes needed.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Stem name (drums, bass, vocals, guitar, piano, other) |
| `rms` | `float` | Root-mean-square energy |
| `peak` | `float` | Peak absolute sample value |
| `crest_db` | `float` | 20*log10(peak/rms) — higher = more transient |
| `coverage` | `float` | Fraction of frames above noise floor (0-1) |
| `spectral_centroid_hz` | `float` | Mean spectral centroid |
| `verdict` | `str` | "keep" / "review" / "skip" |
| `reason` | `str` | Human-readable explanation |

**Derived properties**: `rms_db`, `is_rhythmic`, `is_tonal` (already exist).

---

### TimingTrack (existing — `src/analyzer/result.py`)

No changes needed. Leader track transitions and handoff events are exported as TimingTrack instances with appropriate `element_type` values.

---

### AnalysisResult (existing — `src/analyzer/result.py`)

Extended with an optional `interaction_result` field.

| New Field | Type | Description |
|-----------|------|-------------|
| `interaction_result` | `Optional[InteractionResult]` | Cross-stem interaction analysis output |

---

## New Entities

### StemSelection

Captures the user's final selection of which stems to analyze, after viewing verdicts and optionally overriding them.

| Field | Type | Description |
|-------|------|-------------|
| `stems` | `dict[str, str]` | Map of stem name → final verdict ("keep" / "skip") |
| `overrides` | `list[str]` | List of stem names where the user overrode the automatic verdict |
| `fallback_to_mix` | `bool` | True if all stems were skipped and full mix is used |

**Validation**: At least one stem must be "keep" OR `fallback_to_mix` must be True.

**Serialization**: `to_dict() / from_dict()` for JSON persistence.

---

### InteractionResult

Top-level container for all cross-stem interaction analysis outputs.

| Field | Type | Description |
|-------|------|-------------|
| `leader_track` | `LeaderTrack` | Frame-by-frame dominant stem assignment |
| `tightness` | `Optional[TightnessResult]` | Kick-bass rhythmic tightness (None if drums or bass not available) |
| `sidechained_curves` | `list[SidechainedCurve]` | Sidechained vocal/melodic curves |
| `handoffs` | `list[HandoffEvent]` | Stem handoff events |
| `other_stem_class` | `Optional[str]` | Classification of "other" stem: "spatial", "timing", "ambiguous", or None |

**Serialization**: `to_dict() / from_dict()`.

---

### LeaderTrack

Frame-by-frame record of which stem is dominant.

| Field | Type | Description |
|-------|------|-------------|
| `fps` | `int` | Frame rate of the leader data |
| `frames` | `list[str]` | One stem name per frame (e.g., ["drums", "drums", "vocals", ...]) |
| `transitions` | `list[LeaderTransition]` | Computed from frames — only the change points |

**Derived property**: `duration_ms` = `len(frames) * (1000 / fps)`

---

### LeaderTransition

A single point where the dominant stem changes.

| Field | Type | Description |
|-------|------|-------------|
| `time_ms` | `int` | Timestamp of the transition |
| `from_stem` | `str` | Previous leader |
| `to_stem` | `str` | New leader |

---

### TightnessResult

Windowed kick-bass rhythmic tightness analysis.

| Field | Type | Description |
|-------|------|-------------|
| `windows` | `list[TightnessWindow]` | Per-window tightness scores |

---

### TightnessWindow

A single analysis window for kick-bass tightness.

| Field | Type | Description |
|-------|------|-------------|
| `start_ms` | `int` | Window start time |
| `end_ms` | `int` | Window end time |
| `score` | `float` | Tightness score 0.0-1.0 |
| `label` | `str` | "unison" (>0.7), "independent" (<0.3), or "mixed" |

---

### SidechainedCurve

A continuous feature curve that has been modified by drum onset positions.

| Field | Type | Description |
|-------|------|-------------|
| `source_stem` | `str` | The stem being sidechained (e.g., "vocals") |
| `feature` | `str` | Feature name (e.g., "brightness", "energy") |
| `fps` | `int` | Frame rate |
| `values` | `list[int]` | Conditioned values 0-100, one per frame |
| `boost_values` | `list[int]` | Secondary dimension boost 0-100, one per frame |

---

### HandoffEvent

A detected melodic handoff between stems.

| Field | Type | Description |
|-------|------|-------------|
| `time_ms` | `int` | Timestamp of the handoff midpoint |
| `from_stem` | `str` | Stem ending the phrase |
| `to_stem` | `str` | Stem continuing the phrase |
| `confidence` | `float` | 0.0-1.0 based on gap duration and structural alignment |

---

### ConditionedCurve

A feature curve that has been downsampled, smoothed, and normalized.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Descriptive name (e.g., "vocals_energy", "drums_onset_strength") |
| `stem` | `str` | Source stem |
| `feature` | `str` | Feature type (energy, spectral_centroid, onset_strength, pitch_salience) |
| `fps` | `int` | Target frame rate |
| `values` | `list[int]` | Normalized integers 0-100 |
| `is_flat` | `bool` | True if the curve had negligible dynamic range |

**Validation**: All values in [0, 100]. Length = ceil(duration_ms / (1000/fps)).

---

### ValueCurveExport

Metadata for an exported `.xvc` file.

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `str` | Output file path |
| `curve_name` | `str` | xLights display name (stem + feature) |
| `curve_type` | `str` | "macro" (full song, reduced resolution) or "segment" (per-effect) |
| `segment_label` | `Optional[str]` | Song structure label if segment export |
| `start_ms` | `int` | Segment start time |
| `end_ms` | `int` | Segment end time |
| `point_count` | `int` | Number of data points in the curve |

---

### TimingTrackExport

Metadata for an exported `.xtiming` file.

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `str` | Output file path |
| `track_name` | `str` | xLights display name |
| `source_stem` | `str` | Which stem the data came from |
| `element_type` | `str` | beat, onset, segment, handoff, leader_change |
| `mark_count` | `int` | Number of timing marks |

---

### ExportManifest

Summary of all exported files for a song.

| Field | Type | Description |
|-------|------|-------------|
| `song_file` | `str` | Source audio file path |
| `export_dir` | `str` | Output directory |
| `exported_at` | `str` | ISO timestamp |
| `stems_used` | `list[str]` | Which stems were included |
| `timing_tracks` | `list[TimingTrackExport]` | All exported timing tracks |
| `value_curves` | `list[ValueCurveExport]` | All exported value curves |
| `interactions_detected` | `dict` | Summary: leader_transitions, tightness_windows, handoff_count, sidechain_applied |
| `warnings` | `list[str]` | Any issues encountered (flat curves, missing stems, etc.) |

**Serialization**: Written as `export_manifest.json` in the export directory.

---

## Entity Relationships

```
StemMetrics[] ──→ StemSelection ──→ SweepConfig[] (existing)
                                  ──→ InteractionResult
                                        ├── LeaderTrack → LeaderTransition[]
                                        ├── TightnessResult → TightnessWindow[]
                                        ├── SidechainedCurve[]
                                        └── HandoffEvent[]

TimingTrack[] (from sweep) ──→ ConditionedCurve[] ──→ ValueCurveExport[]
                           ──→ TimingTrackExport[]

SongStructure ──→ segment boundaries for per-segment .xvc export

ExportManifest ──→ aggregates all TimingTrackExport + ValueCurveExport
```

## State Transitions

### Stem Verdict Flow

```
inspect_stems()     →  KEEP / REVIEW / SKIP  (automatic)
interactive_review() →  KEEP / SKIP           (user-confirmed)
```

### Pipeline Flow

```
Inspection → Selection → Parameter Init → Sweep → Interaction → Conditioning → Export
```

Each stage produces its own output and passes it to the next. Stages are independently executable per Constitution Principle III.
