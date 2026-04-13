# Implementation Plan: Genius Lyric Segment Timing

**Branch**: `013-genius-lyric-segments` | **Date**: 2026-03-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-genius-lyric-segments/spec.md`
**Constitution**: v1.0.0

## Summary

Add an opt-in `--genius` flag to `xlight-analyze analyze` that reads Artist/Title from the
MP3's ID3 tags (via mutagen), fetches verified lyrics from the Genius API, parses bracketed
section headers (`[Chorus]`, `[Verse 1]`, etc.) as segment markers, and force-aligns each
section's lyric text to the vocals stem (or full mix) using the existing WhisperX
infrastructure. The resulting `(label, start_ms, end_ms)` records are written into
`AnalysisResult.song_structure` in the same shape as the existing librosa structure analyser,
so the review UI renders them without code changes. Results are stored in the MD5-keyed
analysis JSON cache; repeat runs return instantly.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `lyricsgenius` (new optional dep), `mutagen` (new lightweight dep),
`whisperx` (existing), `librosa` (existing), `click 8+` (existing)
**Storage**: JSON files — existing MD5-keyed `_analysis.json` cache; `song_structure` field
already present in `AnalysisResult`
**Testing**: pytest
**Target Platform**: macOS / Linux desktop CLI
**Project Type**: CLI extension — new module `src/analyzer/genius_segments.py` + new `--genius`
flag on existing `analyze` command
**Performance Goals**: Genius fetch + parse + alignment ≤ 60 seconds on CPU for a 4-minute
song (FR spec SC-002)
**Constraints**: All non-Genius analysis remains fully offline; Genius API call is gated
behind `--genius` flag (opt-in)
**Scale/Scope**: Single-user CLI; first-run network + alignment; cached subsequent runs (zero
additional time per SC-004)

## Constitution Check

*Constitution v1.0.0 | GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | ✅ PASS | Genius headers are text anchors only; all timestamps derive from WhisperX forced-alignment against the audio file. |
| II. xLights Compatibility | ✅ PASS | Segments are written to `song_structure.segments` as `{label, start_ms, end_ms}` — identical shape to the existing librosa-source structure. Review UI and `.xtiming` export need zero changes. |
| III. Modular Pipeline | ✅ PASS | New module `genius_segments.py` is fully self-contained and communicates via `LyricSegment`, `SegmentBoundary`, `GeniusMatch` data contracts. No changes to other stages. |
| IV. Test-First Development | ✅ REQUIRED | Unit tests must cover: ID3 reading, title sanitisation, lyric parsing, segment alignment, and all graceful-fallback paths. |
| V. Simplicity First | ✅ PASS | Two new optional deps (`lyricsgenius`, `mutagen`) justified by direct feature need. No speculative abstractions. |
| Technical Constraint (Offline) | ⚠️ JUSTIFIED VIOLATION | Genius API is a cloud call. Gated behind `--genius` (opt-in); all other analysis remains fully offline. See Complexity Tracking. |

## Project Structure

### Documentation (this feature)

```text
specs/013-genius-lyric-segments/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-genius-flag.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── analyzer/
│   ├── genius_segments.py   # NEW: ID3 reading, Genius fetch, lyric parse, alignment
│   └── ...                  # existing unchanged
tests/
└── unit/
    └── test_genius_segments.py  # NEW: unit tests for all components
```

**Structure Decision**: Single-module addition to `src/analyzer/`. The new module encapsulates
all Genius-specific logic. The only changes to existing files are: (1) `src/cli.py` — add
`--genius` flag and call the new module after the existing analysis steps, (2) `src/cache.py`
— no changes needed (existing cache stores `song_structure` already).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Cloud API call (Genius API) | Song section labels (Chorus, Verse, Bridge) cannot be reliably extracted from audio alone without a large trained segmentation model | A local lyrics file input would require manual authoring for every song, defeating the automation goal |
