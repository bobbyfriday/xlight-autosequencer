# Data Structures

[< Back to Index](README.md) | See also: [Pipeline](pipeline.md) · [Export Formats](export-formats.md)

This document describes the core data models that flow through the system.

---

## Relationship Diagram

```
AnalysisResult (schema 1.0)          HierarchyResult (schema 2.0.0)
┌─────────────────────────┐          ┌──────────────────────────────┐
│ source_file              │          │ source_file                  │
│ source_hash              │          │ source_hash                  │
│ duration_ms              │          │ duration_ms                  │
│ estimated_tempo_bpm      │          │ estimated_bpm                │
│ algorithms[]             │          │ capabilities                 │
│   └─ AnalysisAlgorithm   │          │ stems_available[]            │
│ timing_tracks[]          │          │                              │
│   └─ TimingTrack ────────┼──┐       │ energy_impacts[] ──┐         │
│ phoneme_result           │  │       │ energy_drops[]     ├─ L0     │
│ song_structure           │  │       │ gaps[]        ─────┘         │
└─────────────────────────┘  │       │                              │
                              │       │ sections[] ────── L1         │
                              │       │                              │
┌─────────────────────────┐  │       │ bars ────────────── L2       │
│ TimingTrack              │◄─┘       │ beats ───────────── L3       │
│ ┌─────────────────────┐ │          │ events{stem: ...} ─ L4       │
│ │ name                 │ │          │ interaction ──────── L5       │
│ │ algorithm_name       │ │          │ chords ──────────── L6       │
│ │ element_type         │ │          │ key_changes ─────── L6       │
│ │ quality_score        │ │          └──────────────────────────────┘
│ │ stem_source          │ │                      │
│ │ marks[] ──────────┐  │ │                      │ (levels reference
│ │ value_curve ────┐ │  │ │                       │  TimingTrack and
│ │ score_breakdown │ │  │ │                       │  TimingMark too)
│ └────────────────┼─┼──┘ │
│                  │ │     │
│   ┌──────────────┘ │     │
│   ▼                ▼     │
│ ValueCurve   TimingMark  │
└──────────────────────────┘
```

---

## TimingMark

The atomic unit of timing data — a single point in time.

```python
@dataclass
class TimingMark:
    time_ms: int                    # Timestamp in milliseconds (always int)
    confidence: Optional[float]     # 0.0–1.0 confidence from algorithm
    label: Optional[str]            # e.g., "C maj", "verse", beat position
    duration_ms: Optional[int]      # For segments/notes with extent
```

**Rules:**
- `time_ms` is always an integer — never a float. This avoids floating-point comparison issues when aligning marks across tracks.
- `confidence` is set by algorithms that produce it (e.g., vamp plugins); None for algorithms that don't.
- `label` is used by chord detectors ("C", "Am"), structure detectors ("verse", "chorus"), and beat trackers (beat number within bar).
- `duration_ms` is set by segment detectors and note transcription algorithms.

**JSON representation:**
```json
{"time_ms": 15230, "confidence": 0.92, "label": "C", "duration_ms": null}
```

---

## TimingTrack

A collection of marks from a single algorithm run.

```python
@dataclass
class TimingTrack:
    name: str                               # Algorithm name (e.g., "madmom_beats")
    algorithm_name: str                     # Same as name (backward compat)
    element_type: str                       # "beat", "onset", "bar", "harmonic", etc.
    marks: list[TimingMark]                 # Sorted by time_ms ascending
    quality_score: float                    # 0.0–1.0 overall score
    stem_source: str                        # "drums", "vocals", "full_mix", etc.
    score_breakdown: Optional[ScoreBreakdown]  # Detailed per-criterion scores
    value_curve: Optional[ValueCurve]       # Attached curve (for energy algorithms)
```

**Key behaviors:**
- Marks are always sorted by `time_ms` ascending
- `element_type` determines which scoring category is used
- `stem_source` records which audio stem was analyzed
- `value_curve` is only populated for value_curve-type algorithms (bbc_energy, etc.)

---

## ValueCurve

Continuous time-series data sampled at a fixed frame rate.

```python
@dataclass
class ValueCurve:
    name: str                   # Curve name (e.g., "bbc_energy")
    stem_source: str            # Which stem was analyzed
    fps: int                    # Frames per second (typically 20)
    values: list[int]           # 0–100 normalized per frame
```

**Structure:**
```
Frame:   0    1    2    3    4    5    6    7    8    9   ...
Value:   12   15   23   45   67   82   79   65   43   28  ...
Time:    0ms  50ms 100ms 150ms 200ms ...  (at 20 fps = 50ms per frame)
```

Values are integers in the range [0, 100]. This normalization means all curves are comparable regardless of the underlying measurement (RMS energy, spectral flux, amplitude, etc.).

**Frame rate:** Typically 20 fps (50ms per frame), configurable via `--fps` in the pipeline command.

---

## ScoreBreakdown

Detailed quality scoring information for a single track.

```python
@dataclass
class ScoreBreakdown:
    track_name: str
    algorithm_name: str
    category: str                       # "beats", "onsets", "segments", etc.
    overall_score: float                # Weighted average of criteria
    criteria: list[CriterionResult]     # 5 scoring criteria
    passed_thresholds: bool
    threshold_failures: list[str]
    skipped_as_duplicate: bool
    duplicate_of: Optional[str]         # Name of the track this duplicates
```

```python
@dataclass
class CriterionResult:
    name: str                   # "density", "regularity", etc.
    raw_value: float            # Measured value
    score: float                # 0.0–1.0 after range evaluation
    weight: float               # Criterion weight (0.15–0.25)
    target_range: tuple         # (min, max) expected range
```

See [Quality Scoring](quality-scoring.md) for how scores are computed.

---

## AnalysisResult (Schema 1.0)

The original flat analysis format — all tracks in a single list.

```python
@dataclass
class AnalysisResult:
    schema_version: str                 # "1.0"
    source_file: str                    # Absolute path to source MP3
    source_hash: Optional[str]          # MD5 hex digest
    filename: str                       # Basename
    duration_ms: int
    sample_rate: int
    estimated_tempo_bpm: float
    run_timestamp: str                  # ISO 8601 UTC

    algorithms: list[AnalysisAlgorithm] # Algorithm metadata
    timing_tracks: list[TimingTrack]    # All tracks (flat list)

    stem_separation: bool               # Whether stems were used
    stem_cache: Optional[str]           # Path to .stems/ directory

    phoneme_result: Optional[PhonemeResult]
    song_structure: Optional[SongStructure]
    interaction_result: Optional[...]
    pipeline_stats: Optional[dict]
```

This format is still used by the sweep system and older commands. The `_analysis.json` files in the cache use this schema.

---

## HierarchyResult (Schema 2.0.0)

The newer structured format with levels.

```python
@dataclass
class HierarchyResult:
    schema_version: str = "2.0.0"
    source_file: str
    source_hash: str
    filename: str
    duration_ms: int
    estimated_bpm: float
    capabilities: dict                  # {"vamp": True, "madmom": True, "demucs": True}
    stems_available: list[str]          # ["drums", "bass", "vocals", ...]

    # L0 - Derived
    energy_impacts: list[TimingMark]
    energy_drops: list[TimingMark]
    gaps: list[TimingMark]

    # L1 - Sections
    sections: list[StructureSegment]

    # L2 - Bars (best-of)
    bars: Optional[TimingTrack]

    # L3 - Beats (best-of)
    beats: Optional[TimingTrack]

    # L4 - Events (per-stem)
    events: dict[str, TimingTrack]      # {"full_mix": ..., "drums": ...}

    # L5 - Interaction/Dynamics
    interaction: Optional[InteractionResult]

    # L6 - Harmony
    chords: Optional[TimingTrack]
    key_changes: Optional[TimingTrack]
```

The `_hierarchy.json` files use this schema. The review UI's `_adapt_hierarchy_for_ui()` function flattens this back into a timing_tracks list for the Canvas timeline.

---

## StructureSegment

A labeled time span within the song.

```python
@dataclass
class StructureSegment:
    label: str          # "intro", "verse", "chorus", "bridge", "outro"
    start_ms: int
    end_ms: int
```

---

## PhonemeResult

Word-level and phoneme-level timing from WhisperX + CMUdict.

```python
@dataclass
class PhonemeResult:
    source_file: str
    lyrics_block: LyricsBlock           # Full transcribed text
    word_track: WordTrack               # Word-level timing
    phoneme_track: PhonemeTrack         # Phoneme-level timing
    song_structure: Optional[SongStructure]
    genius_segments: Optional[list[GeniusSegment]]
```

```python
@dataclass
class WordMark:
    label: str          # "HOLIDAY" (uppercased)
    start_ms: int
    end_ms: int

@dataclass
class PhonemeMark:
    label: str          # "AI", "E", "O", "WQ", "L", "MBP", "FV", etc.
    start_ms: int       # (Papagayo phoneme alphabet)
    end_ms: int
```

---

## AudioFile

Metadata about the source audio.

```python
@dataclass
class AudioFile:
    path: str           # Absolute path
    filename: str       # Basename
    duration_ms: int    # Computed from sample count / sample rate
    sample_rate: int    # Native SR (not resampled)
    channels: int       # Always 1 (mono after loading)
```

---

## AnalysisAlgorithm

Metadata about an algorithm (not its results — just its identity).

```python
@dataclass
class AnalysisAlgorithm:
    name: str
    element_type: str
    library: str            # "librosa", "vamp", "madmom"
    plugin_key: Optional[str]
    parameters: dict
    preferred_stem: str
```

---

## Serialization

All dataclasses implement `to_dict()` and `from_dict()` for JSON round-tripping.

```python
# Write
result_dict = analysis_result.to_dict()
json.dump(result_dict, file, indent=2)

# Read
data = json.load(file)
result = AnalysisResult.from_dict(data)
```

The `src/export.py` module provides convenience functions:
```python
export.write(result, "song_analysis.json")
result = export.read("song_analysis.json")
```

---

## Related Docs

- [Pipeline](pipeline.md) — How data flows through the system
- [Export Formats](export-formats.md) — JSON, .xtiming, .xvc output formats
- [Hierarchy Levels](hierarchy.md) — How levels use these structures
