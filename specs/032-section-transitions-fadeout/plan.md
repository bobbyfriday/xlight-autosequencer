# Implementation Plan: Section Transitions & End-of-Song Fade Out

**Branch**: `032-section-transitions-fadeout` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/032-section-transitions-fadeout/spec.md`

## Summary

Add smooth crossfades at section boundaries and a progressive fade-out at end-of-song. Crossfades use the existing `fade_in_ms`/`fade_out_ms` fields on EffectPlacement (already plumbed to XSQ output as `E_TEXTCTRL_Fadein`/`E_TEXTCTRL_Fadeout` but currently always zero). Section boundary snap precision is improved. Three transition modes (none/subtle/dramatic) give users and theme authors control. The end-of-song fade-out progressively dims tiers following the energy curve.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click 8+ (CLI), Flask 3+ (web), existing effect_placer, xsq_writer, section_classifier
**Storage**: JSON files — existing builtin_themes.json (extended with transition_mode), analysis hierarchy
**Testing**: pytest
**Target Platform**: Linux/macOS (local CLI + web dashboard)
**Project Type**: CLI tool + local web application
**Performance Goals**: No measurable impact on generation time; crossfade calculations are O(sections × groups)
**Constraints**: Backward compatible via "none" mode; fade fields must survive xLights import (test empirically)
**Scale/Scope**: Typical: 10-30 sections per song, 8-30 groups, ~100-300 effect placements

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | PASS | Crossfade durations derived from tempo/beats. Fade-out follows energy curves. All timing from audio analysis. |
| II. xLights Compatibility | PASS | Uses existing E_TEXTCTRL_Fadein/Fadeout fields. Empirical test needed to confirm xLights preserves values. |
| III. Modular Pipeline | PASS | New transition module in `src/generator/transitions.py`. Snap logic enhances existing analyzer function. |
| IV. Test-First Development | PASS | Tests before implementation for each user story. |
| V. Simplicity First | PASS | Uses existing fade fields — no new abstraction layers. Three modes via simple enum. |

No violations.

## Project Structure

### Documentation (this feature)

```text
specs/032-section-transitions-fadeout/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── generator/
│   ├── transitions.py       # NEW: TransitionConfig, CrossfadeRegion, FadeOutPlan, apply_crossfades(), apply_fadeout()
│   ├── effect_placer.py     # MODIFIED: update _calculate_fades() to accept transition config
│   ├── plan.py              # MODIFIED: integrate transitions into build_plan pipeline
│   └── models.py            # (unchanged)
├── analyzer/
│   └── orchestrator.py      # MODIFIED: improve _snap_sections_to_bars (boundary merge prevention)
├── themes/
│   └── models.py            # MODIFIED: add optional transition_mode field to Theme
└── cli.py                   # MODIFIED: add --transition-mode option to generate command

tests/
├── unit/
│   └── test_transitions.py      # NEW: crossfade, fadeout, snap unit tests
├── integration/
│   └── test_transitions_integration.py  # NEW: end-to-end transition tests
└── fixtures/
    └── (use existing hierarchy fixtures)
```

**Structure Decision**: Single new module `transitions.py` in the generator package. No new packages.
