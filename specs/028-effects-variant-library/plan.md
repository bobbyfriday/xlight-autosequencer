# Implementation Plan: Effects Variant Library

**Branch**: `028-effects-variant-library` | **Date**: 2026-04-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/028-effects-variant-library/spec.md`

## Summary

Build a variant library system that extends the existing effect catalog with named, reusable parameter configurations. Each variant wraps a base xLights effect with specific parameter overrides and rich categorization metadata (tier affinity, energy level, speed feel, direction, section roles, scope, genre affinity). The library supports CLI and web dashboard CRUD, .xsq import for mining proven configurations, theme integration via variant references, and ranked multi-dimensional querying for automated selection by the sequence generator.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click 8+ (CLI), Flask 3+ (web dashboard), xml.etree.ElementTree (stdlib, .xsq parsing), json/pathlib (stdlib)
**Storage**: JSON files — `src/variants/builtin_variants.json` (built-in catalog), `~/.xlight/custom_variants/*.json` (custom, per-file)
**Testing**: pytest
**Target Platform**: Linux/macOS (local tool, offline-only)
**Project Type**: CLI + web dashboard (extends existing pipeline)
**Performance Goals**: Library load <500ms for 500+ variants; query response <50ms
**Constraints**: Fully offline; no new external dependencies; must not break existing theme/effect loading
**Scale/Scope**: Initial 100+ built-in variants, unbounded custom variants; 7 variant-specific tag dimensions + inherited base effect dimensions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Audio-First Pipeline** | PASS | Variants are parameter configurations — they don't alter audio analysis. Variant tags (energy, section roles) derive from audio analysis context at query time. |
| **II. xLights Compatibility** | PASS | Variants resolve to standard xLights effect parameters. No change to .xsq output format. Theme→variant→parameter resolution produces identical xLights XML. |
| **III. Modular Pipeline** | PASS | New `src/variants/` module with well-defined data contracts. Communicates with effects library (read-only) and themes (variant references). No shared mutable state. |
| **IV. Test-First Development** | PASS | Unit tests for variant model/validator/library, integration tests for .xsq import and theme resolution, fixture-based test data. |
| **V. Simplicity First** | PASS | Follows existing patterns (dataclass models, JSON storage, load_library pattern, validate_ functions). No new abstractions beyond what EffectLibrary/ThemeLibrary already establish. |
| **Offline Operation** | PASS | All file-based, no network calls. |

**Gate result: ALL PASS — no violations to justify.**

## Project Structure

### Documentation (this feature)

```text
specs/028-effects-variant-library/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── cli-commands.md
│   └── api-endpoints.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── variants/                    # NEW — variant library module
│   ├── __init__.py
│   ├── models.py                # EffectVariant dataclass, VariantTags dataclass
│   ├── library.py               # VariantLibrary class, load_variant_library(), save/delete
│   ├── validator.py             # validate_variant() with effect_library dependency
│   ├── importer.py              # extract_variants_from_xsq() — .xsq mining
│   ├── scorer.py                # rank_variants() — composite suitability scoring
│   └── builtin_variants.json    # Built-in catalog (100+ variants)
├── effects/                     # EXISTING — no structural changes
│   ├── models.py                # (unchanged)
│   ├── library.py               # (unchanged)
│   └── validator.py             # (unchanged)
├── themes/                      # EXISTING — minor extension
│   ├── models.py                # EffectLayer gains optional variant_ref field
│   ├── library.py               # load resolves variant references
│   └── validator.py             # validates variant_ref against VariantLibrary
├── generator/
│   └── effect_placer.py         # Updated to resolve variants during placement
├── review/
│   └── server.py                # New variant CRUD + browse endpoints
└── cli.py                       # New variant subcommands

tests/
├── unit/
│   ├── test_variant_models.py
│   ├── test_variant_library.py
│   ├── test_variant_validator.py
│   ├── test_variant_importer.py
│   └── test_variant_scorer.py
├── integration/
│   └── test_variant_theme_integration.py
└── fixtures/
    ├── variants/
    │   ├── valid_custom_variant.json
    │   └── builtin_variants_minimal.json
    └── xsq/
        └── sample_sequence.xsq    # Minimal .xsq for import testing
```

**Structure Decision**: New `src/variants/` module follows the exact pattern of `src/effects/` and `src/themes/` — dataclass models, JSON library loader, validation function, CRUD helpers. This is consistent with the existing modular pipeline architecture.

## Complexity Tracking

> No violations to justify — all constitution gates pass.
