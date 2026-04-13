# Implementation Plan: Stem Separation

**Branch**: `008-stem-separation` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-stem-separation/spec.md`

## Summary

Add opt-in audio stem separation (`--stems` flag) as a preprocessing step before timing analysis. The source MP3 is split into six stems (drums, bass, vocals, guitar, piano, other) using Demucs v4 (`htdemucs_6s`). Each algorithm is routed to its best-fit stem via a `preferred_stem` class attribute, improving beat, pitch, and harmony track quality. Stems are MD5-cached adjacent to the source file and reused on re-runs. A new `stem_source` field is added to each `TimingTrack` and surfaced in the summary CLI and review UI.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: demucs `htdemucs_6s` (new), vamp, librosa, madmom, click, Flask
**Storage**: JSON files (local filesystem); WAV stem files in `.stems/<md5>/`
**Testing**: pytest with fixture audio files
**Target Platform**: macOS (darwin), local machine
**Project Type**: CLI tool
**Performance Goals**: Stem separation completes within 3× the runtime of a non-stem analysis on a 4-minute song; cache hit completes in under 2 seconds
**Constraints**: Fully offline — no cloud API calls; Demucs runs on CPU (GPU optional)
**Scale/Scope**: Single user, local machine; typical songs 3–6 minutes

## Constitution Check

*Constitution version 1.0.0 — ratified 2026-03-22*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | ✅ Pass | Stems are derived from audio; all timing decisions remain audio-grounded |
| II. xLights Compatibility | ✅ Pass | No change to output format; `stem_source` is additive metadata |
| III. Modular Pipeline | ✅ Pass | Stem separation is a new independent stage; communicates via `StemSet` data contract; replacing Demucs requires changes only in `stems.py` |
| IV. Test-First Development | ✅ Pass | Tests written before implementation; fixture WAV files used for deterministic stem routing tests |
| V. Simplicity First | ✅ Pass | No speculative features; 4 stems, 1 new module, minimal changes to existing modules |

**Complexity Tracking**: No violations. No additional justification needed.

## Project Structure

### Documentation (this feature)

```text
specs/008-stem-separation/
├── plan.md              # This file
├── research.md          # Phase 0 output — library, cache, routing decisions
├── data-model.md        # Phase 1 output — StemSet, StemCache, TimingTrack extension
├── quickstart.md        # Phase 1 output — developer onboarding
├── contracts/
│   └── cli.md           # CLI schema: --stems flag, summary output, JSON schema
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── analyzer/
│   ├── audio.py              # unchanged
│   ├── result.py             # +stem_source field on TimingTrack
│   ├── runner.py             # +stems: StemSet | None param; routes algorithms
│   ├── scorer.py             # unchanged
│   ├── stems.py              # NEW: StemSeparator, StemSet, StemCache
│   └── algorithms/
│       ├── base.py           # +preferred_stem class attribute (default: "full_mix")
│       ├── vamp_beats.py     # +preferred_stem = "drums"
│       ├── vamp_onsets.py    # +preferred_stem = "drums"
│       ├── vamp_structure.py # unchanged (full_mix)
│       ├── vamp_pitch.py     # +preferred_stem = "vocals"
│       ├── vamp_harmony.py   # +preferred_stem = "other"
│       ├── librosa_beats.py  # +preferred_stem = "drums"
│       ├── librosa_bands.py  # unchanged (full_mix)
│       ├── librosa_hpss.py   # unchanged (full_mix — does own source separation)
│       └── madmom_beat.py    # +preferred_stem = "drums"
├── cli.py                    # +--stems flag; pass StemSet to runner
└── export.py                 # +stem_source in serialization/deserialization

tests/
├── fixtures/
│   └── 10s_drums_bass.wav    # NEW: short fixture for stem routing tests
├── unit/
│   └── test_stems.py         # NEW: StemSeparator, StemCache, StemSet unit tests
└── integration/
    └── test_stem_pipeline.py # NEW: end-to-end --stems analysis test

src/review/
└── static/                   # +stem source label on each track in timeline UI
```

**Structure Decision**: Single-project layout (Option 1). All new code is within the existing `src/analyzer/` module boundary. The only new file is `stems.py`; all other changes are additive to existing files.
