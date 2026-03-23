# Implementation Plan: Audio Analysis and Timing Track Generation

**Branch**: `001-audio-timing-tracks` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-audio-timing-tracks/spec.md`
**Constitution**: v1.0.0

## Summary

Build the audio analysis pipeline stage for xlight-autosequencer. Given an MP3 file,
run 22 audio analysis algorithms across Vamp plugins, librosa, and madmom to generate
named timing tracks covering beats, bars, onsets (3 methods), frequency bands, drums,
melody, chords, and structural segments. Score each track for lighting usefulness.
Output the full result as a structured JSON file. Provide a CLI summary view, `--top N`
automatic selection, and manual track selection/export so the user can pick the 3–6
tracks that best suit a given song.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: vamp (Python host), librosa 0.10+, madmom 0.16+, click, pytest
**System Dependencies**: ffmpeg, Vamp plugin packs (QM, BeatRoot, pYIN, NNLS Chroma, Silvet)
**Storage**: JSON files on local filesystem (no database)
**Testing**: pytest with royalty-free audio fixtures
**Target Platform**: macOS (primary); Linux compatible
**Project Type**: CLI tool / library
**Performance Goals**: 3-minute MP3 analyzed (all 22 algorithms) in < 120 seconds on modern laptop
**Constraints**: Fully offline; no network calls; deterministic output per input+config; graceful
degradation if Vamp plugins not installed
**Scale/Scope**: Single MP3 file per invocation for this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | PASS | Feature is exclusively audio analysis; all timing marks derived from audio signal |
| II. xLights Compatibility | PASS | JSON output is an intermediate format; xLights export deferred to later feature. JSON schema designed for clean conversion to xLights timing XML |
| III. Modular Pipeline | PASS | Audio ingest, per-algorithm analysis, result assembly, and JSON export are separate, independently testable units |
| IV. Test-First | PASS | Tests written first with short audio fixtures; each algorithm tested against known-good timing ground truth |
| V. Simplicity First | PASS | MP4 deferred; no plugin system; no GUI; CLI only; no config file format for this feature |

All gates pass. No complexity justification required.

## Project Structure

### Documentation (this feature)

```text
specs/001-audio-timing-tracks/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md
└── contracts/
    └── cli.md
```

### Source Code (repository root)

```text
src/
├── analyzer/
│   ├── __init__.py
│   ├── audio.py              # MP3 loading and AudioFile metadata
│   ├── result.py             # AnalysisResult, TimingTrack, TimingMark data classes
│   ├── runner.py             # Orchestrates all 22 algorithm runs for a file
│   ├── scorer.py             # Quality scoring (density + regularity → quality_score)
│   └── algorithms/
│       ├── __init__.py
│       ├── base.py           # Abstract Algorithm interface
│       ├── vamp_beats.py     # QM bar-beat tracker + BeatRoot (Vamp)
│       ├── vamp_onsets.py    # QM onset detector x3 methods (Vamp)
│       ├── vamp_structure.py # QM segmenter + tempo tracker (Vamp)
│       ├── vamp_pitch.py     # pYIN note events + pitch changes (Vamp)
│       ├── vamp_harmony.py   # Chordino chord changes + NNLS chroma peaks (Vamp)
│       ├── librosa_beats.py  # librosa beat tracking + bar grouping
│       ├── librosa_bands.py  # librosa frequency band energy peaks (bass/mid/treble)
│       ├── librosa_hpss.py   # librosa HPSS drums + harmonic peaks
│       └── madmom_beat.py    # madmom RNN+DBN beat + downbeat tracking
├── cli.py                    # Click CLI entry point
└── export.py                 # JSON serialization / deserialization

tests/
├── fixtures/
│   ├── README.md             # License info for fixture files
│   ├── beat_120bpm_10s.mp3   # Synthetic 10s, 120 BPM, clear beat
│   └── ambient_10s.mp3       # No-beat edge case
├── unit/
│   ├── test_audio.py
│   ├── test_scorer.py
│   ├── test_librosa_beats.py
│   ├── test_librosa_bands.py
│   ├── test_librosa_hpss.py
│   ├── test_madmom_beat.py
│   ├── test_vamp_beats.py    # skipped if Vamp plugins not installed
│   ├── test_vamp_onsets.py
│   ├── test_vamp_structure.py
│   ├── test_vamp_pitch.py
│   └── test_vamp_harmony.py
└── integration/
    └── test_full_pipeline.py
```

**Structure Decision**: Single project layout. No frontend, no API server. `src/`
contains library code; `cli.py` is the thin CLI wrapper. This separation means the
analysis engine can be imported directly in future features without going through the CLI.

## Complexity Tracking

> No constitution violations — table not required.
