# Implementation Plan: Unified Dashboard

**Branch**: `027-unified-dashboard` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/027-unified-dashboard/spec.md`

## Summary

Replace the current disconnected upload/library pages with a unified dashboard homepage that serves as the central hub for the application. The dashboard provides a song library with sort/filter/search, integrated upload with real-time progress, a theme editor for browsing and creating themes, and persistent navigation across all existing tool pages (timeline, story, phonemes, grouper). All pages get a shared nav bar. The server's dual-mode architecture (upload vs review) is unified so the dashboard is always reachable.

## Technical Context

**Language/Version**: Python 3.11+ (backend), Vanilla JavaScript ES2020+ (frontend)
**Primary Dependencies**: Flask 3+ (web server), click 8+ (CLI), mutagen (ID3 tags), existing analysis pipeline
**Storage**: JSON files — `~/.xlight/library.json` (song library), `~/.xlight/custom_themes/*.json` (custom themes), `src/themes/builtin_themes.json` (built-in themes, read-only)
**Testing**: pytest (backend), manual browser testing (frontend)
**Target Platform**: Local desktop browser (localhost), macOS/Linux
**Project Type**: Web application (local Flask server + vanilla JS frontend)
**Performance Goals**: Homepage renders song list in <500ms for 100 songs; navigation between pages in <200ms
**Constraints**: No frontend framework (vanilla JS only); single-user local tool; no authentication
**Scale/Scope**: Single user, up to ~200 analyzed songs, ~21 built-in themes + custom themes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | PASS | Dashboard does not alter analysis pipeline; it reads existing analysis results |
| II. xLights Compatibility | PASS | No changes to sequence output; dashboard is a management UI layer |
| III. Modular Pipeline | PASS | Dashboard is a new UI module; existing stages remain independent and unchanged |
| IV. Test-First Development | PASS | Backend routes will have pytest tests; frontend pages tested manually |
| V. Simplicity First | PASS | Vanilla JS, no new framework; reuses existing library/theme data structures |

**Offline operation**: PASS — Dashboard is entirely local, no cloud calls.
**Performance baseline**: N/A — Dashboard is UI, not audio processing.

## Project Structure

### Documentation (this feature)

```text
specs/027-unified-dashboard/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── routes.md        # HTTP route contracts
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── review/
│   ├── server.py                  # Modified: unified mode, new routes for themes/delete/re-analyze
│   ├── theme_routes.py            # New: Flask blueprint for theme CRUD endpoints
│   └── static/
│       ├── dashboard.html         # New: unified homepage (song library + upload + navigation)
│       ├── dashboard.js           # New: song list rendering, sort/filter, upload integration
│       ├── dashboard.css          # New: dashboard-specific styles
│       ├── theme-editor.html      # New: theme browser/editor page
│       ├── theme-editor.js        # New: theme CRUD, palette preview, form handling
│       ├── theme-editor.css       # New: theme editor styles
│       ├── navbar.js              # New: shared nav bar component (injected into all pages)
│       ├── navbar.css             # New: shared nav bar styles
│       ├── index.html             # Modified: add navbar include
│       ├── story-review.html      # Modified: add navbar include
│       ├── phonemes.html          # Modified: add navbar include
│       ├── grouper.html           # Modified: add navbar include
│       ├── upload.html            # Preserved but deprecated (redirect to dashboard)
│       ├── library.html           # Preserved but deprecated (redirect to dashboard)
│       └── [existing files unchanged]
├── themes/
│   ├── library.py                 # Modified: add save_custom_theme(), delete_custom_theme()
│   └── builtin_themes.json        # Unchanged (read-only)
└── library.py                     # Modified: add remove_entry(), delete_files_for_entry()

tests/
└── unit/
    ├── test_dashboard_routes.py   # New: dashboard and theme API route tests
    └── test_library_delete.py     # New: library entry deletion tests
```

**Structure Decision**: Extends existing `src/review/` web module. Theme routes split into a new Blueprint (`theme_routes.py`) to keep `server.py` manageable. Shared navbar is a standalone JS module loaded by all pages. No new top-level directories needed.

## Complexity Tracking

No constitution violations to justify.

## Design Decisions

### D1: Shared Navigation Bar Approach

The navbar is a standalone JS module (`navbar.js`) that each HTML page loads via a `<script>` tag. On DOMContentLoaded, it injects a `<nav>` element at the top of `<body>`. This avoids server-side templating (keeping the existing static file approach) and ensures every page gets consistent navigation with minimal changes.

The navbar highlights the active section based on the current URL path. Song-specific tool pages show a breadcrumb-style indicator (e.g., "Song Library > Mad Russian's Christmas > Timeline").

### D2: Unified Server Mode

Currently `create_app()` registers different route sets based on whether `analysis_path` is provided. The change: always register the dashboard and library routes regardless of mode. When launched with a specific file, the server opens that file's tool page but the dashboard routes are still accessible. The `/` route serves `dashboard.html` in all modes; the old `upload.html` redirects to `/`.

### D3: Theme Editor Backend

Theme CRUD is a new Flask Blueprint (`theme_routes.py`) mounted at `/themes`. It reuses the existing `ThemeLibrary` and `Theme` dataclass from `src/themes/`. New methods on the library: `save_custom_theme(theme)` writes to `~/.xlight/custom_themes/{name}.json`, and `delete_custom_theme(name)` removes the file. Built-in themes are served read-only.

### D4: Song Deletion

Library deletion adds a `remove_entry(source_hash)` method to the `Library` class. Optional file cleanup uses a new `delete_files_for_entry(entry, delete_files=False)` that removes the `_analysis.json`, `_hierarchy.json`, `_story.json`, and `.stems/` directory if the flag is set.

### D5: Dashboard Song List

The song list is rendered client-side from the `/library` JSON endpoint (already exists). The dashboard JS adds sorting (click column headers), filtering (text input searches title/artist), and metadata display. The existing library endpoint returns all entries; the dashboard adds client-side processing.

### D6: Upload Integration

The dashboard embeds the upload flow inline (collapsible section at the top). It reuses the existing `/upload` endpoint and SSE `/progress` stream. When analysis completes, the dashboard refreshes the song list from `/library` without a page reload.
