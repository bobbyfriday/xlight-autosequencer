# Implementation Plan: Effect & Variant Library UI Wiring

**Branch**: `031-effect-variant-ui-wiring` | **Date**: 2026-04-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/031-effect-variant-ui-wiring/spec.md`

## Summary

Wire the existing effect variant library (123+ curated variants with scoring/filtering API) into the web UI. The theme editor gains an inline variant picker per layer, the variant library gets a standalone browser page, and the navbar links to it. No new backend endpoints needed — all API infrastructure exists.

## Technical Context

**Language/Version**: Python 3.11+ (backend), Vanilla JavaScript ES2020+ (frontend)
**Primary Dependencies**: Flask 3+ (web server), existing EffectLibrary, VariantLibrary, ThemeLibrary
**Storage**: JSON files (variant definitions in `src/variants/builtins/`, custom variants in `~/.xlight/custom_variants/`)
**Testing**: pytest (integration tests for API endpoints)
**Target Platform**: Local web app (Flask dev server, localhost)
**Project Type**: Web application (Flask backend + vanilla JS frontend, no build step)
**Performance Goals**: Variant picker loads in <1 second; filter results update instantly
**Constraints**: No new backend endpoints needed — use existing `/variants`, `/variants/query`, `/variants/coverage`; no build tooling; no external JS dependencies
**Scale/Scope**: 123+ variants across 34 effects; 3 UI surfaces (theme editor picker, variant browser page, navbar)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | N/A | This feature is UI-only; no audio analysis changes |
| II. xLights Compatibility | Pass | `variant_ref` on EffectLayer already resolves correctly in effect_placer.py; no output format changes |
| III. Modular Pipeline | Pass | UI consumes existing library modules via existing API endpoints; no coupling introduced |
| IV. Test-First Development | Pass | Will add integration tests for variant picker API calls and variant browser page |
| V. Simplicity First | Pass | Reuses existing API endpoints, extends existing UI components, no new abstractions |

**Gate result**: PASS — no violations, no complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/031-effect-variant-ui-wiring/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (frontend ↔ API contracts)
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/review/
├── server.py                      # Flask app factory (existing — no changes expected)
├── theme_routes.py                # Theme API (existing — minor addition: proxy variant query)
├── variant_routes.py              # Variant API (existing — add page-serve route)
└── static/
    ├── navbar.js                  # Shared nav (existing — add Variant Library link)
    ├── theme-editor.html          # Theme editor page (existing — no changes)
    ├── theme-editor.js            # Theme editor logic (existing — add variant picker)
    ├── theme-editor.css           # Theme editor styles (existing — add variant picker styles)
    ├── variant-library.html       # Variant browser page (NEW)
    ├── variant-library.js         # Variant browser logic (NEW)
    └── variant-library.css        # Variant browser styles (NEW)

tests/integration/
├── test_variant_api_browse.py     # Existing variant API tests (extend)
└── test_theme_variant_picker.py   # New: variant picker integration tests
```

**Structure Decision**: Extends existing Flask + vanilla JS frontend in `src/review/static/`. New variant browser page follows the same single-HTML-file + JS + CSS pattern used by theme-editor and dashboard. No new backend modules needed.
