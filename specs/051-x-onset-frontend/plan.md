# Implementation Plan: x-onset Frontend Redo

**Branch**: `051-x-onset-frontend` | **Date**: 2026-04-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/workspace/specs/051-x-onset-frontend/spec.md`

## Summary

Replace the existing ~21K-line vanilla-JS Flask-rendered UI at [src/review/](../../src/review/) with a clean-slate SPA built to the [x-onset design handoff](../../design_handoff_xonset/README.md) — a six-screen DAW-style flow (LIBRARY → DROP → ANALYZE → TIMELINE → THEME → EXPORT). Pair the SPA with a new versioned JSON API (`/api/v1/*`) whose shape is designed for these screens, and delete every old route + static asset in the same change. No parallel operation period.

Technical approach: Vite + React 18 + TypeScript SPA, Zustand for shared state, CSS Modules driven by design-token custom properties, served as a built `dist/` by the existing Flask backend. Backend remains Python 3.11+ (Flask 3), analysis pipeline (librosa, vamp, madmom, demucs, existing generator) is untouched — only the HTTP layer exposing it is rewritten.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5+ / ES2022 (frontend)
**Primary Dependencies**: Flask 3+ (backend web server, existing); React 18+, Zustand 4+, Vite 5+, TypeScript 5+ (frontend). No UI framework (no Tailwind, no shadcn/ui, no Chakra) — design tokens ported directly from [design_handoff_xonset/prototype/state.jsx](../../design_handoff_xonset/prototype/state.jsx) as CSS custom properties consumed by CSS Modules.
**Storage**: JSON files on local disk under the user's state directory (`~/.xlight/library/` — library, sections, assignments, preferences, layout), and the existing hash-keyed analysis + stems caches under `.stems/<hash>/` and `_analysis.json` files.
**Testing**: pytest (backend API), Vitest + React Testing Library (frontend components and stores), Playwright (one end-to-end happy-path smoke test covering the US1 chain).
**Target Platform**: Local developer workstation (Linux / macOS / Windows). Delivered as a Python package; user runs a CLI command that boots Flask and auto-opens the browser at the localhost URL.
**Project Type**: Web application — separate frontend (TypeScript SPA) and backend (Python Flask + existing pipeline) within the same repo.
**Performance Goals**: 60 fps playhead animation during playback (no visible frame drops per SC-002); filter keystroke → library update < 200 ms (SC-007); cold-start analysis restore < 1 s (SC-008); app-restart → last-position restore < 2 s (SC-004).
**Constraints**: All operation is local-only (no network egress beyond localhost); single concurrent analysis; cutover migration (no parallel operation with old UI); state is durably written on every meaningful edit (FR-049a); frontend architected to allow a future Tauri shell wrap without UI rewrite.
**Scale/Scope**: ~6 screens, ~30 React components, ~12 API endpoints, ~15 store slices. Expected user library size up to 100 songs (SC-007). No multi-user / multi-tenant concerns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
| --- | --- | --- |
| I. Audio-First Pipeline | ✅ Pass | This feature does not alter audio analysis. The new UI consumes analysis results produced by the unchanged pipeline and respects the existing hash-keyed cache. Analysis remains deterministic per input. |
| II. xLights Compatibility | ✅ Pass | Export flows through the existing generator (`src/generator/`). The new UI adds a `/api/v1/export` entry point but does not alter output format. The prop layout is imported once and reused (FR-036a–c), matching the generator's existing expectation of an `xlights_rgbeffects.xml`. |
| III. Modular Pipeline | ✅ Pass | The new `src/review/frontend/` and `src/review/api/v1/` are independent modules communicating with the existing `src/analyzer/`, `src/generator/`, `src/themes/`, `src/effects/` via their current Python interfaces — no reach-through, no shared mutable state with the pipeline. |
| IV. Test-First Development | ✅ Pass | All API endpoints get pytest contract tests written before implementation. Frontend stores and screens get Vitest unit tests before implementation. One Playwright smoke test covers the US1 end-to-end chain. Tests fixture-driven where possible. |
| V. Simplicity First | ⚠ Tracked | Introducing a React/TS/Vite/Zustand toolchain adds real complexity vs. the current vanilla-JS stack. Justification recorded in Complexity Tracking below. |

**Result**: No hard violations. One tracked complexity entry for the framework stack.

## Project Structure

### Documentation (this feature)

```text
specs/051-x-onset-frontend/
├── plan.md                  # This file
├── spec.md                  # Feature specification (13 clarifications)
├── research.md              # Phase 0 output — resolved decisions
├── data-model.md            # Phase 1 output — entities & schemas
├── contracts/               # Phase 1 output — API contracts
│   ├── README.md            # Index + conventions
│   ├── library.md           # library, folder, song endpoints
│   ├── import.md            # file import + hash-based dedup
│   ├── analysis.md          # analysis start/status/result + SSE progress
│   ├── sections.md          # section CRUD + split/merge/reset
│   ├── themes.md            # theme catalog
│   ├── assignments.md       # theme assignment + parameter overrides
│   ├── export.md            # export trigger + status
│   ├── layout.md            # xLights layout import
│   └── preferences.md       # preferences, library export/import bundle
├── quickstart.md            # Phase 1 output — dev and first-run walkthrough
└── checklists/
    └── requirements.md      # Spec quality checklist (from /speckit.specify)
```

### Source Code (repository root)

```text
src/
├── review/
│   ├── __init__.py
│   ├── server.py                        # REWRITTEN — Flask app: mounts /api/v1/* + serves built SPA at /
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py              # Blueprint + error handlers
│   │       ├── library.py               # GET /api/v1/library, POST /api/v1/folders, PATCH /api/v1/songs/<hash>/folder, DELETE /api/v1/songs/<hash>
│   │       ├── import_.py               # POST /api/v1/import (multipart) → computes hash, dedups, returns song
│   │       ├── analysis.py              # POST /api/v1/songs/<hash>/analyze (start), GET .../analyze/status (SSE progress), GET .../analysis (result)
│   │       ├── sections.py              # GET/PUT /api/v1/songs/<hash>/sections, POST .../sections/split|merge|promote, POST .../sections/reset
│   │       ├── themes.py                # GET /api/v1/themes — built-in theme catalog
│   │       ├── assignments.py           # GET/PUT /api/v1/songs/<hash>/assignments — theme + parameter overrides per section
│   │       ├── export.py                # POST /api/v1/songs/<hash>/export, GET .../export/status
│   │       ├── layout.py                # POST /api/v1/layout (upload xlights_rgbeffects.xml), GET /api/v1/layout
│   │       └── preferences.py           # GET/PUT /api/v1/preferences, POST /api/v1/library/export, POST /api/v1/library/import
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── paths.py                     # resolves ~/.xlight/library/, .stems/<hash>/, etc.
│   │   ├── library.py                   # read/write library.json (songs, folders, preferences)
│   │   ├── assignments.py               # read/write per-song assignments + sections
│   │   └── bundle.py                    # library export/import bundle pack/unpack
│   └── frontend/
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts               # dev server on :5173, proxies /api → :5000 (Flask)
│       ├── index.html
│       ├── src/
│       │   ├── main.tsx
│       │   ├── App.tsx                  # router keyed on store.screen
│       │   ├── api/
│       │   │   └── client.ts            # fetch wrapper, SSE helper, typed endpoints
│       │   ├── store/
│       │   │   ├── app.ts               # screen, current song, inspector, tweaks
│       │   │   ├── library.ts           # songs[], folders[], filter
│       │   │   ├── playback.ts          # time, playing, curBeat, energyPulse
│       │   │   ├── sections.ts          # sections, ghost boundaries, edit mode
│       │   │   ├── assignments.ts       # sectionThemesById, parameter overrides
│       │   │   ├── preferences.ts       # mode, density, inspectorOpen, tweaksOpen
│       │   │   └── keyboard.ts          # global keyboard shortcut registry
│       │   ├── theme/
│       │   │   ├── tokens.module.css    # :root { --bg0: #111114; ... } — dark + light palettes
│       │   │   ├── palette.ts           # TS tokens (re-export for runtime use)
│       │   │   └── typography.css       # Inter + JetBrains Mono, tabular-nums
│       │   ├── components/
│       │   │   ├── Chrome/              # header, tool strip, library rail, status bar, tweaks panel
│       │   │   ├── LightsPreview/       # parametric strip, used on timeline & theme
│       │   │   ├── MiniLights/          # small non-interactive preview for theme cards + section chips
│       │   │   ├── Waveform/            # SVG waveform + playhead + per-section tint
│       │   │   ├── Ruler/               # time ruler with clickable scrubbing
│       │   │   ├── SectionStrip/        # editable section chips (timeline + theme contexts)
│       │   │   ├── AlgoTrack/           # raw detector event lanes (timeline)
│       │   │   ├── Transport/           # play/pause/nudge/jump buttons, timecode
│       │   │   ├── ThemeCard/           # theme grid card with swatches + animated preview
│       │   │   └── Inspector/           # right rail (varies per screen)
│       │   ├── screens/
│       │   │   ├── Library.tsx
│       │   │   ├── Drop.tsx
│       │   │   ├── Analyze.tsx          # SSE-driven progress + per-detector status
│       │   │   ├── Timeline.tsx
│       │   │   ├── Theme.tsx            # north-star screen
│       │   │   └── Export.tsx
│       │   ├── hooks/
│       │   │   ├── useAudio.ts          # single-Audio-element ref, RAF loop for time updates
│       │   │   ├── useKeyboard.ts       # bind store keyboard registry
│       │   │   ├── usePersist.ts        # PUT to /api/v1/preferences and /api/v1/songs/<hash>/* on store changes
│       │   │   └── useDesignTokens.ts   # switch dark/light by setting data-mode on <body>
│       │   └── util/
│       │       ├── format.ts            # timecode, numeric formatters
│       │       ├── overlap.ts           # section overlap math (for re-analysis mapping, FR-013a)
│       │       └── themeDefaults.ts     # analyzer-suggested default-theme resolution (FR-012a)
│       ├── dist/                        # Vite build output (COMMITTED so `pip install` works without npm)
│       └── tests/
│           ├── store/*.test.ts          # Vitest unit tests for store slices
│           ├── components/*.test.tsx    # Vitest + RTL for components
│           ├── util/*.test.ts           # overlap math, format helpers
│           └── e2e/
│               └── happy-path.spec.ts   # Playwright — US1 end-to-end smoke
│   # DELETED in this change:
│   #   src/review/static/**              (entire old vanilla-JS frontend — ~40 files, ~21k LOC)
│   #   src/review/brief_routes.py, generate_routes.py, grouper.py,
│   #   preview_routes.py, story_routes.py, theme_routes.py, variant_routes.py

tests/
├── review/                              # Python API tests (new, mirror /api/v1 structure)
│   ├── conftest.py                      # Flask test client, temp library dir fixture
│   ├── test_api_library.py
│   ├── test_api_import.py
│   ├── test_api_analysis.py
│   ├── test_api_sections.py
│   ├── test_api_themes.py
│   ├── test_api_assignments.py
│   ├── test_api_export.py
│   ├── test_api_layout.py
│   └── test_api_preferences.py
└── review_storage/                      # Storage-layer tests
    ├── test_library_json.py
    ├── test_assignments_json.py
    └── test_bundle_roundtrip.py
```

**Structure Decision**: Web-application layout with frontend and backend colocated under the existing `src/review/` tree. The new frontend lives in `src/review/frontend/` (self-contained Node project with its own `package.json`), and the new API lives in `src/review/api/v1/`. This keeps the full UI stack inside the existing Python package so `pip install -e .` remains the single install command, and the built SPA (`src/review/frontend/dist/`) is served by the same Flask process that handles the API — no dual-server deployment.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| New build toolchain (Vite, npm, Node at dev time) | The design handoff is a React/JSX reference whose visual and interaction demands (60fps waveform + playhead, stateful 6-screen flow with cross-screen playback, dark/light palette swap, dense DAW-style chrome) exceed what the current vanilla-JS stack can maintain without becoming the slow-growing 21K-line tangle it already is. | **Vanilla JS / Web Components**: would require re-authoring the handoff prototype by hand and reinventing state management — more LOC, worse correctness, no hiring pool. **Preact / Alpine.js**: still requires a build toolchain; shallow ecosystem for waveform + audio libs. Net: ship the framework once, retire ~21K lines of custom plumbing. |
| TypeScript | State shape carries Section, Beat, Boundary, ParameterOverride, and store slices — correctness matters. Runtime-only typing in vanilla JS has been a source of bugs in the existing code. | **Plain JS + JSDoc**: tooling support is strictly inferior; refactor safety is the main value we want. |
| Committed `dist/` build artifacts | Users `pip install` without needing Node on their machines (FR — hobbyist audience). Matches how many Python packages ship with pre-built assets. | **Build at install time**: requires Node on the user's box; rejected because it raises the onboarding bar for non-engineers. **Build in CI + package as wheel**: future polish; for v0 we commit `dist/` and refresh it before releases. |

## Phase 0: Outline & Research

See [research.md](./research.md). All `NEEDS CLARIFICATION` markers resolved — Technical Context has no unknowns. Research covered:

- Stack selection rationale and alternatives rejected (React vs Svelte vs Solid vs vanilla; Vite vs Next.js; Zustand vs Redux Toolkit vs Jotai vs useContext; CSS Modules vs Tailwind vs CSS-in-JS).
- Waveform rendering strategy (inline SVG vs WaveSurfer.js vs Canvas 2D — decision: inline SVG with server-computed peaks, simpler than WaveSurfer and zero JS dependency cost).
- Analysis progress transport (SSE vs WebSocket vs polling — decision: SSE, one-way server-push is exactly the shape needed).
- Library persistence format (single JSON vs SQLite vs IndexedDB — decision: two JSON files per library root; one index, one per-song sidecar).
- MP3 delivery to the browser (stream from disk vs upload to server — decision: backend streams from on-disk source path keyed by content hash; no re-upload).
- Keyboard shortcut architecture (library choice and focus-management rules).
- Library export/import bundle format.
- Re-analysis section-mapping algorithm (FR-013a maximum-overlap approach).

## Phase 1: Design & Contracts

### Data model

See [data-model.md](./data-model.md). Defines:

- **Entities**: Song, Section, Boundary (real + ghost), Theme, ThemeAssignment, ParameterOverride, AnalysisResult, Layout, Preferences, Folder, Bundle.
- **Identity**: `song_id = sha256(audio_bytes)[:16]` as a hex string.
- **Validation**: field-level rules derived from FR-001 through FR-051.
- **State transitions**: draft → analyzed → themed, plus the reverse path from re-analysis and the `source_file_missing` branch.
- **JSON schemas**: for every entity as it crosses the `/api/v1` boundary.

### Contracts

See [contracts/](./contracts/). One markdown file per endpoint group, each specifying method, path, request shape, response shape, error codes, and acceptance behaviors cited back to FRs. Key shape conventions:

- Song identity in URLs: `/api/v1/songs/<song_id>` where `song_id` is the 16-hex content hash.
- Error responses: `{ "error": { "code": "string", "message": "string" } }` with stable codes.
- Time values in JSON are **milliseconds** as integers, not seconds as floats — matches the existing backend invariant (CLAUDE.md: "Timestamps are always stored as integers (milliseconds) — never floats").
- All endpoints return JSON except `/` (serves `dist/index.html`) and `/assets/*` (serves SPA assets) and `/audio/<song_id>` (streams audio bytes).

### Quickstart

See [quickstart.md](./quickstart.md). End-to-end walkthrough:

1. Install — `pip install -e .` + (dev only) `cd src/review/frontend && npm install && npm run dev`.
2. Start — `xlight review` boots Flask on `:5000`, opens browser to `http://localhost:5000`.
3. First-run experience — empty LIBRARY with drop target.
4. Drop an MP3, watch ANALYZE, land on TIMELINE.
5. Assign themes (or accept defaults), export as `.xsq`.
6. Simulated regression: change a theme, re-export, diff the output.

### Agent context

Will run `.specify/scripts/bash/update-agent-context.sh claude` during Phase 1 to add this feature's tech additions (React, TS, Zustand, Vite) to [CLAUDE.md](../../CLAUDE.md).

### Constitution re-check (post-design)

No new violations introduced by the design. The Complexity Tracking entries above cover the full delta.

## Implementation phasing (to be expanded in `/speckit.tasks`)

Suggested top-down sequencing the tasks command will refine:

1. **Setup** — scaffold `src/review/frontend/`, install deps, configure Vite dev proxy to Flask, delete legacy static/ and old route modules in their own commit.
2. **Storage foundation** — `src/review/storage/*.py`, tests for library/assignments/bundle round-trip.
3. **API v1 foundation** — `src/review/api/v1/__init__.py` blueprint + error handlers + pytest fixtures.
4. **Backend endpoints** — one commit per contract file (library, import, analysis, sections, themes, assignments, layout, export, preferences), test-first.
5. **Frontend foundation** — design tokens, typography, Chrome skeleton, store setup, API client, keyboard registry.
6. **Shared components** — LightsPreview, MiniLights, Waveform, SectionStrip, Transport, ThemeCard, Inspector.
7. **Screens in the critical-path order recommended by the handoff**: TIMELINE → THEME → ANALYZE → LIBRARY → DROP → EXPORT.
8. **Integration wiring** — persistence hooks (FR-049a/b), keyboard shortcuts (FR-041/042), re-analysis review dialog (FR-013a), theme inheritance on split/merge (FR-021/022/025).
9. **Library export/import** (FR-049c).
10. **Cutover migration** — delete old UI + route modules in a single squash-ready commit; rewrite `src/review/server.py`.
11. **Build & package** — configure Vite output, commit initial `dist/`, verify `pip install` works without Node.
12. **End-to-end smoke** — Playwright happy-path covering US1, plus SC-001 through SC-008 verification pass.
