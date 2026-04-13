# Tasks: Unified Dashboard

**Input**: Design documents from `/specs/027-unified-dashboard/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/routes.md

**Tests**: Not explicitly requested in the specification. Test tasks included only for backend route changes.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create new files and shared infrastructure needed by all stories

- [x] T001 [P] Create shared navbar component in src/review/static/navbar.js — renders nav bar with links to Homepage (/), Theme Editor (/themes/editor), Layout Grouping (/grouper); highlights active section based on window.location.pathname; auto-injects `<nav>` at top of `<body>` on DOMContentLoaded
- [x] T002 [P] Create shared navbar styles in src/review/static/navbar.css — dark theme (#1a1a1a bg, #4a9eff accent), horizontal bar, active indicator, responsive layout; include breadcrumb area for song-specific tool pages

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Inject navbar into all existing pages and unify server modes — MUST complete before user stories

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Add navbar script/CSS includes to src/review/static/index.html — add `<link rel="stylesheet" href="/static/navbar.css">` and `<script src="/static/navbar.js"></script>`; adjust body padding to account for fixed navbar
- [x] T004 [P] Add navbar script/CSS includes to src/review/static/story-review.html — same includes; replace existing back button with navbar navigation
- [x] T005 [P] Add navbar script/CSS includes to src/review/static/phonemes.html — same includes; replace existing Library/Timeline nav buttons with navbar
- [x] T006 [P] Add navbar script/CSS includes to src/review/static/grouper.html — same includes; add padding for navbar
- [x] T007 Unify server modes in src/review/server.py — modify create_app() to always register dashboard routes (library, upload, progress, job-status) and theme blueprint regardless of whether analysis_path is provided; when analysis_path is provided, also register review-mode routes; change GET `/` to always serve dashboard.html; add redirect from `/library-view` to `/`; add redirect from old upload page to `/`

**Checkpoint**: Foundation ready — all pages have navbar, server serves dashboard in all modes. User story implementation can now begin.

---

## Phase 3: User Story 1 — Song Library Homepage (Priority: P1) MVP

**Goal**: Homepage displays all analyzed songs with metadata in a sortable, filterable table

**Independent Test**: Launch app, verify song list renders with correct metadata, sorting works, clicking a song navigates to timeline

### Implementation for User Story 1

- [x] T008 [US1] Extend GET `/library` endpoint in src/review/server.py — enrich each LibraryEntry with computed fields: title (from ID3 tags via mutagen or Genius cache in analysis JSON, fallback to filename), artist (same sources, fallback to "Unknown"), quality_score (from analysis JSON overall_quality), has_story (os.path.exists check), has_phonemes (os.path.exists check), file_exists (os.path.exists on source_file), analysis_exists (os.path.exists on analysis_path)
- [x] T009 [P] [US1] Create dashboard page in src/review/static/dashboard.html — page structure with: navbar includes, search/filter input bar, sortable table (columns: title, artist, duration, BPM, quality score, stems badge, analysis date), upload section (collapsible), empty state for zero songs
- [x] T010 [P] [US1] Create dashboard styles in src/review/static/dashboard.css — dark theme consistent with existing pages; table styles with hover row highlight; sort indicator arrows on column headers; quality score color bar (green/orange/red); stem/phoneme badge styles; empty state styling; search input styling
- [x] T011 [US1] Create dashboard logic in src/review/static/dashboard.js — fetch GET /library on load; render song table rows from JSON; implement client-side sorting (click column header to toggle asc/desc); implement client-side text filtering (search input filters title and artist); show "missing" indicator for entries where file_exists or analysis_exists is false; click song row navigates to /timeline?hash={source_hash}; show empty welcome state when entries array is empty with prominent upload prompt
- [x] T012 [US1] Wire dashboard as homepage in src/review/server.py — add route GET `/` serving dashboard.html (ensure this replaces upload.html in all modes per T007)

**Checkpoint**: Homepage works — shows song library, sorts, filters, navigates to timeline. Independently functional MVP.

---

## Phase 4: User Story 2 — Upload and Analyze from Homepage (Priority: P1)

**Goal**: Users can upload MP3 directly from the dashboard with real-time progress, no page navigation needed

**Independent Test**: Upload an MP3 from the dashboard, verify progress updates display, song appears in list on completion

### Implementation for User Story 2

- [x] T013 [US2] Add upload section to dashboard in src/review/static/dashboard.html — collapsible upload area at top of page with drag-and-drop zone, file browse button, analysis option checkboxes (Vamp, madmom, stems, phonemes, structure, story), analyze button
- [x] T014 [US2] Add upload styles to src/review/static/dashboard.css — drop zone styling (dashed border, hover highlight), progress bar, algorithm step list, collapsible animation, Genius prompt styling
- [x] T015 [US2] Implement upload logic in src/review/static/dashboard.js — drag-and-drop file handling; POST to /upload; SSE listener on /progress for real-time progress display (reuse existing event format: progress, warning, stage, genius_prompt, done); on completion, re-fetch /library and update table without page reload; on error, show error message with retry option; handle Genius artist/title prompt via POST /genius-retry; detect duplicate upload by checking source_hash against existing entries before uploading

**Checkpoint**: Upload works end-to-end from dashboard. Song list auto-refreshes after analysis completes.

---

## Phase 5: User Story 3 — Navigation Hub to All Tools (Priority: P1)

**Goal**: Persistent navigation across all pages lets users move between tools fluidly

**Independent Test**: Navigate from homepage to each tool and back; verify active state indicator and breadcrumbs work

### Implementation for User Story 3

- [x] T016 [US3] Enhance navbar with song context in src/review/static/navbar.js — when on song-specific tool pages (/timeline, /story-review, /phonemes-view), show breadcrumb: "Song Library > [Song Title] > [Tool Name]"; extract song title from page context or query parameter; highlight parent "Song Library" nav item for song tool pages
- [x] T017 [US3] Preserve dashboard state across navigation in src/review/static/dashboard.js — before navigating away, save current sort column, sort direction, and filter text to sessionStorage; on dashboard load, restore from sessionStorage if present

**Checkpoint**: Full navigation works. User can move between homepage, theme editor, grouper, and song tools without losing context.

---

## Phase 6: User Story 4 — Theme Management (Priority: P2)

**Goal**: Browse, create, edit, duplicate, and delete themes from a visual theme editor page

**Independent Test**: Navigate to theme editor, browse built-in themes, create a custom theme with palette, save it, verify it persists after page reload

### Implementation for User Story 4

- [x] T018 [US4] Add save_custom_theme() and delete_custom_theme() methods to src/themes/library.py — save_custom_theme(theme: Theme) writes JSON to ~/.xlight/custom_themes/{slugified_name}.json using existing theme schema; delete_custom_theme(name: str) removes the file; add slug generation helper (lowercase, hyphens, strip special chars)
- [x] T019 [US4] Create theme routes blueprint in src/review/theme_routes.py — Flask Blueprint at /themes; GET /themes/list returns all themes with is_builtin flag; POST /themes/create validates and saves new custom theme (409 if name exists); PUT /themes/<name> updates custom theme (403 if built-in); DELETE /themes/<name> deletes custom theme (403 if built-in); POST /themes/duplicate copies source theme to new custom theme name
- [x] T020 [US4] Register theme blueprint in src/review/server.py — import and register theme_routes Blueprint in create_app(); add GET /themes/editor route serving theme-editor.html
- [x] T021 [P] [US4] Create theme editor page in src/review/static/theme-editor.html — navbar includes; theme list panel (left side) with built-in and custom sections; detail/edit panel (right side) with form fields; visual palette preview area
- [x] T022 [P] [US4] Create theme editor styles in src/review/static/theme-editor.css — two-column layout (list + detail); theme card styling with palette color swatches; form styling for create/edit mode; read-only styling for built-in themes; color input styling; layer configuration display
- [x] T023 [US4] Create theme editor logic in src/review/static/theme-editor.js — fetch GET /themes/list on load; render theme list with name, mood badge, and palette color swatches; click theme shows detail panel with all fields; for custom themes: enable edit fields, save button calls PUT /themes/<name>; "Create Theme" button shows empty form, save calls POST /themes/create; "Duplicate" button on any theme calls POST /themes/duplicate; "Delete" button on custom themes calls DELETE /themes/<name> with confirmation; color palette input using native HTML color inputs for each swatch; layer configuration display (effect name, blend mode); form validation (name required, at least one palette color)

**Checkpoint**: Theme editor fully functional. Users can browse, create, edit, duplicate, and delete themes.

---

## Phase 7: User Story 5 — Song Management Actions (Priority: P2)

**Goal**: Delete songs, re-analyze with different settings, and view analysis details from the dashboard

**Independent Test**: Select a song, view its details, delete it (verify removal), re-analyze another song with different options

### Implementation for User Story 5

- [x] T024 [US5] Add remove_entry() and delete_files_for_entry() to src/library.py — remove_entry(source_hash) removes entry from library JSON and saves; delete_files_for_entry(entry, delete_files=False) optionally removes analysis JSON, hierarchy JSON, story JSON, and .stems/<hash>/ directory from disk
- [x] T025 [US5] Add DELETE /library/<source_hash> route in src/review/server.py — accepts query param delete_files (default false); calls Library.remove_entry() and optionally delete_files_for_entry(); returns JSON with status and files_deleted flag; 404 if entry not found
- [x] T026 [US5] Add song detail panel to dashboard in src/review/static/dashboard.js — clicking a song's detail/expand button shows inline detail panel with: quality score breakdown (if available from analysis JSON), track list count, available stems list, analysis date, file paths; action buttons: "Review Timeline" → /timeline?hash=, "Story Review" → /story-review?path=, "Phonemes" → /phonemes-view?hash=, "Re-analyze" (opens upload area pre-filled with source file path and analysis options), "Delete" (confirmation dialog with optional "Also delete files from disk" checkbox, calls DELETE /library/<hash>)
- [x] T027 [US5] Add detail panel and delete dialog styles to src/review/static/dashboard.css — expandable detail panel below song row; action button styling; confirmation dialog overlay; checkbox styling for delete-files option

**Checkpoint**: Song management works. Users can view details, delete entries, and initiate re-analysis from the dashboard.

---

## Phase 8: User Story 6 — Layout Grouping Access (Priority: P2)

**Goal**: Layout grouping editor is accessible as a first-class navigation item

**Independent Test**: Click "Layout Grouping" in nav, verify grouper loads and existing drag-drop functionality works

### Implementation for User Story 6

- [x] T028 [US6] Verify grouper route is available in all server modes in src/review/server.py — ensure GET /grouper and all /grouper/* API routes are registered regardless of server mode (part of T007 unification, verify here)
- [x] T029 [US6] Verify navbar "Layout Grouping" link works in src/review/static/navbar.js — ensure /grouper link is present and highlights correctly when active; test that grouper.html loads with navbar and existing functionality (drag-drop, tier tabs, save/reset/export) is unaffected by the navbar addition

**Checkpoint**: Grouper is accessible from nav. All existing grouper functionality preserved.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Quality improvements that affect multiple stories

- [x] T030 [P] Add pytest tests for enriched /library endpoint in tests/unit/test_dashboard_routes.py — test that enriched fields (title, artist, quality_score, has_story, has_phonemes, file_exists, analysis_exists) are present in response; test empty library returns empty array
- [x] T031 [P] Add pytest tests for DELETE /library/<hash> in tests/unit/test_library_delete.py — test successful deletion returns 200; test missing hash returns 404; test delete_files=true removes files; test delete_files=false keeps files
- [x] T032 [P] Add pytest tests for theme CRUD routes in tests/unit/test_dashboard_routes.py — test GET /themes/list returns built-in + custom; test POST create/PUT update/DELETE for custom themes; test 403 on edit/delete of built-in themes; test 409 on duplicate name creation
- [x] T033 Backward compatibility: ensure old bookmarked URLs still work in src/review/server.py — verify /library-view redirects to /; verify old upload.html URL redirects to /; verify /timeline?hash= works for deep links to specific songs
- [x] T034 Run quickstart.md validation — launch server, walk through the architecture overview flow: verify GET / shows dashboard, navigate to /themes/editor, navigate to /grouper, open a song for timeline review, verify navbar on all pages

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (navbar must exist before injecting)
- **Phase 3-5 (US1, US2, US3)**: All depend on Phase 2. US2 depends on US1 (upload extends dashboard). US3 depends on US1 (enhances navbar on dashboard pages).
- **Phase 6 (US4 — Themes)**: Depends on Phase 2 only. Can run in parallel with US1-US3.
- **Phase 7 (US5 — Song Management)**: Depends on US1 (extends dashboard).
- **Phase 8 (US6 — Grouping)**: Depends on Phase 2 only. Can run in parallel with other stories.
- **Phase 9 (Polish)**: Depends on all user stories being complete.

### User Story Dependencies

- **US1 (Song Library Homepage)**: Depends on Foundational only — MVP story
- **US2 (Upload from Homepage)**: Depends on US1 (adds upload to existing dashboard page)
- **US3 (Navigation Hub)**: Depends on US1 (enhances dashboard state preservation)
- **US4 (Theme Management)**: Independent of US1-3 — can start after Foundational
- **US5 (Song Management)**: Depends on US1 (extends dashboard with detail panel)
- **US6 (Grouping Access)**: Independent — verification task only, can start after Foundational

### Within Each User Story

- HTML structure before CSS before JS logic
- Backend routes before frontend consumption
- Core rendering before interactive features

### Parallel Opportunities

- T001 + T002 (navbar JS and CSS) — different files
- T003 + T004 + T005 + T006 (navbar injection into 4 pages) — different files
- T009 + T010 (dashboard HTML and CSS) — different files
- T021 + T022 (theme editor HTML and CSS) — different files
- T030 + T031 + T032 (all test files) — different files
- US4 (themes) can run in parallel with US1 → US2 → US3 pipeline
- US6 (grouping) can run in parallel with everything after Phase 2

---

## Parallel Example: Phase 2

```bash
# All navbar injections can run in parallel (different HTML files):
Task: T003 — inject navbar into index.html
Task: T004 — inject navbar into story-review.html
Task: T005 — inject navbar into phonemes.html
Task: T006 — inject navbar into grouper.html
```

## Parallel Example: User Story 1

```bash
# HTML and CSS can be created in parallel:
Task: T009 — dashboard.html structure
Task: T010 — dashboard.css styles
# Then JS depends on both:
Task: T011 — dashboard.js logic
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (navbar component)
2. Complete Phase 2: Foundational (inject navbar, unify server)
3. Complete Phase 3: User Story 1 (song library homepage)
4. **STOP and VALIDATE**: Launch app, verify homepage shows songs, sorting and filtering works, navigation via navbar works
5. This is a usable product — users see their library and navigate between tools

### Incremental Delivery

1. Setup + Foundational → All pages have navbar, server unified
2. US1 (Homepage) → Song library is the landing page (MVP!)
3. US2 (Upload) → Upload integrated into homepage
4. US3 (Navigation) → Breadcrumbs and state preservation
5. US4 (Themes) → Theme editor accessible from nav
6. US5 (Song Management) → Delete, re-analyze, detail view
7. US6 (Grouping) → Verification only
8. Polish → Tests, backward compat, validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Existing pages (upload.html, library.html) are preserved but redirect to dashboard — no deletions
