# Implementation Plan: Intelligent Stem Analysis and Automated Light Sequencing Pipeline

**Branch**: `012-intelligent-stem-sweep` | **Date**: 2026-03-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-intelligent-stem-sweep/spec.md`

## Summary

Build a complete automated pipeline from stem inspection through xLights export. The pipeline evaluates stem quality (KEEP/REVIEW/SKIP), lets users confirm selections interactively, derives intelligent sweep parameters from audio properties, runs cross-stem interaction analysis (leader tracking, kick-bass tightness, visual sidechaining, call-and-response handoffs), conditions all feature data for hardware compatibility (downsampling, smoothing, normalization to 0-100 integers), and exports finished timing tracks (`.xtiming`) and value curves (`.xvc`) for xLights.

The codebase already has stem inspection (`stem_inspector.py`), sweep infrastructure (`sweep.py`), `.xtiming` export (`xtiming.py`), and quality scoring (`scorer.py`). This feature extends stem inspection with interactive selection, adds the interaction analysis layer, builds the data conditioning pipeline, adds `.xvc` value curve export, and wires everything into a single `pipeline` CLI command.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: numpy (signal processing, cross-correlation), librosa 0.10+ (audio features, onset detection), vamp (plugin host), click 8+ (CLI), xml.etree.ElementTree (stdlib, xLights XML export)
**Storage**: JSON files (analysis output), XML files (`.xtiming`, `.xvc` exports), WAV stem files in `.stems/<md5>/`
**Testing**: pytest
**Target Platform**: macOS (primary), Linux
**Project Type**: CLI tool
**Performance Goals**: Full pipeline on a 3-minute song in under 5 minutes (per SC-001); 60s for analysis per constitution
**Constraints**: Fully offline; all output values integers 0-100; default 20 FPS (50ms) frame rate; xLights-importable without modification
**Scale/Scope**: Single-user CLI; processes one song at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Audio-First Pipeline** | PASS | All timing/feature data derives from audio analysis. Interaction features (leader track, tightness, sidechaining) are computed from stem audio. No arbitrary defaults. |
| **II. xLights Compatibility** | PASS | Exports `.xtiming` (already proven format) and `.xvc` (standard xLights value curve XML). All output validated against xLights import requirements. |
| **III. Modular Pipeline** | PASS | Each stage (inspection, selection, parameter init, sweep, interaction, conditioning, export) is independently executable and testable. Stages communicate via data classes, not shared state. |
| **IV. Test-First Development** | PASS | Each new module will have unit tests with fixture data. Integration test covers full pipeline end-to-end. |
| **V. Simplicity First** | PASS | Builds on existing infrastructure (stem_inspector, sweep, xtiming). New modules are focused: interaction.py, conditioning.py, xvc_export.py. No speculative abstraction. |

**Constitution version**: 1.0.0 — All gates pass. No violations to track.

### Post-Phase 1 Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Audio-First Pipeline** | PASS | All data model entities (LeaderTrack, TightnessResult, SidechainedCurve, HandoffEvent, ConditionedCurve) derive from audio analysis. No manual/arbitrary inputs. |
| **II. xLights Compatibility** | PASS | `.xvc` format confirmed from xLights source code (ValueCurve.cpp). Per-segment export strategy resolves the 200-point X-axis resolution limit. `.xtiming` format already proven. |
| **III. Modular Pipeline** | PASS | Each stage has its own module (stem_inspector, interaction, conditioning, xvc_export, xtiming). Data flows through well-defined dataclasses. CLI exposes each stage independently. |
| **IV. Test-First Development** | PASS | Test plan covers all new modules with fixture-based unit tests. |
| **V. Simplicity First** | PASS | No new dependencies (scipy.signal.savgol_filter is in scipy, already available via librosa's dependency chain). Three focused new modules. No abstraction layers. |

## Project Structure

### Documentation (this feature)

```text
specs/012-intelligent-stem-sweep/
├── plan.md              # This file
├── research.md          # Phase 0: unknowns resolution
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: developer quickstart
├── contracts/           # Phase 1: CLI contract
└── tasks.md             # Phase 2: implementation tasks
```

### Source Code (repository root)

```text
src/
├── analyzer/
│   ├── stem_inspector.py      # EXTEND: add interactive selection mode
│   ├── interaction.py         # NEW: cross-stem interaction analysis
│   ├── conditioning.py        # NEW: downsample, smooth, normalize to 0-100
│   ├── xvc_export.py          # NEW: .xvc value curve XML export
│   ├── xtiming.py             # EXTEND: support beat/onset timing tracks (not just phonemes)
│   ├── sweep.py               # EXISTING: sweep infrastructure (no changes expected)
│   ├── result.py              # EXTEND: add interaction result types
│   └── algorithms/            # EXISTING: no changes
├── cli.py                     # EXTEND: add pipeline command, interactive stem review
└── export.py                  # EXISTING: JSON serialization (no changes expected)

tests/
├── unit/
│   ├── test_stem_inspector.py # EXTEND: interactive selection tests
│   ├── test_interaction.py    # NEW: interaction analysis tests
│   ├── test_conditioning.py   # NEW: conditioning pipeline tests
│   ├── test_xvc_export.py     # NEW: value curve export tests
│   └── test_xtiming.py        # EXTEND: beat/onset timing track tests
└── fixtures/                  # Short audio fixtures for deterministic tests
```

**Structure Decision**: Single project, extending the existing `src/analyzer/` module structure. Three new focused modules (`interaction.py`, `conditioning.py`, `xvc_export.py`) plus extensions to existing modules (`stem_inspector.py`, `xtiming.py`, `result.py`, `cli.py`).

## Complexity Tracking

No constitution violations — table not needed.
