---

description: "Task list for x-onset Frontend Redo"
---

# Tasks: x-onset Frontend Redo

**Input**: Design documents from `/workspace/specs/051-x-onset-frontend/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Tests**: REQUIRED — constitution Principle IV (Test-First Development) mandates failing tests before implementation. Backend contract tests via pytest; frontend unit/component tests via Vitest + React Testing Library; one end-to-end happy-path via Playwright.

**Organization**: Tasks grouped by user story per spec.md priorities (P1 → P3). Within each story: tests before implementation; storage before services; services before UI components; components before screens.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3, US4, US5)
- File paths are absolute project-relative (`src/…`, `tests/…`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the new frontend project + backend test harness without touching the existing UI. Legacy deletion happens at cutover in Polish.

- [X] T001 Create frontend project skeleton at `src/review/frontend/` with `package.json` (name `xonset-frontend`, `"private": true`, scripts: `dev`, `build`, `test`, `e2e`), `tsconfig.json` (strict, target ES2022, module ESNext, jsx react-jsx, paths to `src/*`), `vite.config.ts` (dev proxy: `/api` and `/audio` → `http://127.0.0.1:5000`), `index.html` (loads `src/main.tsx`), and `src/main.tsx` + `src/App.tsx` stubs
- [X] T002 [P] Install frontend dependencies: `react@18`, `react-dom@18`, `zustand@4`, `vite@5`, `typescript@5`, `@vitejs/plugin-react`, `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`, `@playwright/test`
- [X] T003 [P] Configure Vitest at `src/review/frontend/vitest.config.ts` (environment jsdom, setup file loads `@testing-library/jest-dom`)
- [X] T004 [P] Configure Playwright at `src/review/frontend/playwright.config.ts` (webServer spawns `npm run dev` + Flask; baseURL `http://localhost:5173`)
- [X] T005 [P] Create `src/review/frontend/dist/.gitkeep` + `src/review/frontend/dist/README.md` documenting that `dist/` is committed so `pip install` works without Node
- [X] T006 [P] Register `xlight review` console script entry in `pyproject.toml` under `[project.scripts]` pointing at a new `src.review.cli:main` (CLI will be written in T073)
- [X] T007 [P] Create pytest fixtures for API tests at `tests/review/conftest.py` — Flask test client, temp library dir fixture (patches `~/.xlight/library/` via monkeypatch), sample Song fixture
- [X] T008 [P] Create pytest fixtures for storage tests at `tests/review_storage/conftest.py` — temp dir + monkeypatched paths
- [X] T009 Create `src/review/api/__init__.py` and `src/review/api/v1/__init__.py` empty package files (Flask Blueprint added in Foundational phase)
- [X] T01- [X] T010 Create `src/review/storage/__init__.py` empty package file

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure every user story depends on — storage layer, API error handling, design tokens, Zustand store scaffolding, API client, Chrome shell, keyboard registry.

**⚠️ CRITICAL**: No user story work begins until every task in this phase is complete.

### Storage layer (test-first)

- [X] T01- [X] T011 [P] Write failing tests in `tests/review_storage/test_paths.py` covering: `library_root()` returns `~/.xlight/library/`, `song_session_path(song_id)` returns the per-song sidecar path, honors `XLIGHT_STATE_HOME` env override
- [X] T01- [X] T012 Implement `src/review/storage/paths.py` per data-model.md §Library and §Session paths; T011 passes
- [X] T01- [X] T013 [P] Write failing tests in `tests/review_storage/test_library_json.py` covering: create-new, round-trip read/write, atomic write (temp + rename), schema_version preserved, corrupt file raises clean error
- [X] T01- [X] T014 Implement `src/review/storage/library.py` — read/write `library.json` with Library entity shape (per data-model.md); T013 passes
- [X] T01- [X] T015 [P] Write failing tests in `tests/review_storage/test_assignments_json.py` for per-song `session.json` read/write + the invariant `sections.length == assignments.length`
- [X] T01- [X] T016 Implement `src/review/storage/assignments.py` — read/write per-song `session.json`; T015 passes
- [X] T01- [X] T017 [P] Write failing tests in `tests/review_storage/test_bundle_roundtrip.py` — pack library + sessions into a zip, unpack, assert byte-stable round-trip, detect schema version mismatch
- [X] T01- [X] T018 Implement `src/review/storage/bundle.py` — pack/unpack `.xonset-bundle` per FR-049c; T017 passes

### API scaffolding

- [X] T01- [X] T019 [P] Write failing tests in `tests/review/test_api_base.py` — unknown route 404, error-response shape `{"error": {"code": ..., "message": ...}}`, JSON content-type on errors
- [X] T020 Implement `src/review/api/v1/__init__.py` — Flask Blueprint at `/api/v1`, global error handlers producing the documented error shape; T019 passes
- [X] T021 Register the Blueprint in `src/review/server.py` alongside existing routes (do NOT delete existing routes yet — cutover happens in Polish)

### Frontend design system

- [X] T022 [P] Port design tokens from `design_handoff_xonset/prototype/state.jsx` (`PALETTE.dark` + `PALETTE.light`) to `src/review/frontend/src/theme/tokens.module.css` as CSS custom properties on `:root` and `[data-mode="light"]`
- [X] T023 [P] Write `src/review/frontend/src/theme/typography.css` — loads Inter + JetBrains Mono from Google Fonts, sets `font-variant-numeric: tabular-nums` on `.mono`, type scale per handoff README
- [X] T024 [P] Export TS design tokens at `src/review/frontend/src/theme/palette.ts` for runtime-only code (e.g., canvas fill colors) — mirrors `tokens.module.css` values
- [X] T025 Wire design tokens + typography into `App.tsx`; verify dark/light swap by toggling `data-mode` on `<body>`

### Frontend state + API client

- [X] T026 [P] Write failing tests in `src/review/frontend/tests/store/app.test.ts` for the `app` store slice — screen switch, selected song, inspector/tweaks toggles
- [X] T027 Implement `src/review/frontend/src/store/app.ts` (Zustand slice); T026 passes
- [X] T028 [P] Write failing tests in `src/review/frontend/tests/store/playback.test.ts` for playback slice — play/pause, time, derived `curBeat`, `energyPulse` decay
- [X] T029 Implement `src/review/frontend/src/store/playback.ts`; T028 passes
- [X] T030 [P] Scaffold remaining store slices at `src/review/frontend/src/store/library.ts`, `sections.ts`, `assignments.ts`, `preferences.ts`, `keyboard.ts` with empty shape matching data-model.md entities — tests land per user story later
- [X] T031 [P] Implement `src/review/frontend/src/api/client.ts` — typed fetch wrapper, SSE helper (wraps EventSource with typed events), error unwrapping matching the API error envelope. Co-located tests at `src/review/frontend/tests/api/client.test.ts`
- [X] T032 [P] Implement `src/review/frontend/src/hooks/useDesignTokens.ts` — subscribes to `preferences.mode` and sets `data-mode` attribute on `<body>`

### Frontend Chrome (shell that hosts every screen)

- [X] T033 [P] Write failing tests in `src/review/frontend/tests/components/Chrome.test.tsx` — header renders wordmark + traffic lights, tool strip highlights active tab with 2px accent underline, status bar shows playing state
- [X] T034 Implement `src/review/frontend/src/components/Chrome/Chrome.tsx` + children (`Header.tsx`, `ToolStrip.tsx`, `LibraryRail.tsx` shell — actual song list lands in US2, `StatusBar.tsx`, `TweaksPanel.tsx`) per handoff §App Chrome; T033 passes
- [X] T035 Implement `src/review/frontend/src/components/Chrome/TweaksPanel.tsx` body with segmented controls for dark/light, compact/comfortable, inspector visible/hidden; driven by preferences store (preferences endpoint comes in US5)

### Keyboard shortcut registry

- [X] T036 [P] Write failing tests in `src/review/frontend/tests/store/keyboard.test.ts` — register/unregister bindings, screen-scoped bindings, suspend-on-input-focus behavior
- [X] T037 Implement `src/review/frontend/src/store/keyboard.ts` + `src/review/frontend/src/hooks/useKeyboard.ts` — global `keydown` listener routed through the store, active-input suppression; T036 passes

### Persistence hook

- [X] T038 [P] Write failing tests in `src/review/frontend/tests/hooks/usePersist.test.ts` — meaningful-change writes fire immediately (FR-049a), high-frequency writes debounce to 1s (FR-049b)
- [X] T039 Implement `src/review/frontend/src/hooks/usePersist.ts` per FR-049a/b; T038 passes

**Checkpoint**: Foundational complete — storage, API scaffold, design system, store + client, Chrome shell, keyboard, and persistence are ready. User-story work begins.

---

## Phase 3: User Story 1 — First-Song Happy Path (Priority: P1) 🎯 MVP

**Goal**: A fresh-install user can drop an MP3 and reach a finished `.xsq` export — drop → analyze → timeline → theme → export — in a single session. Everything else is strictly additive.

**Independent Test**: Reset the library dir, launch the app, drop `tests/fixtures/highway.mp3`, watch ANALYZE complete, scrub on TIMELINE, visit THEME and click "accept all defaults", import an `xlights_rgbeffects.xml` when prompted on EXPORT, click render, confirm a `.xsq` file is produced on disk.

### API endpoints for US1 (test-first)

- [X] T04- [X] T040 [P] [US1] Write failing tests in `tests/review/test_api_themes.py` for `GET /api/v1/themes` — returns `schema_version`, every Section kind has at least one theme with that kind in `default_for_kinds` (FR-012a requirement)
- [X] T04- [X] T041 [P] [US1] Implement `src/review/api/v1/themes.py` reading the built-in theme catalog from `src/themes/builtin_themes.json` and transforming to API shape; T040 passes
- [X] T04- [X] T042 [P] [US1] Write failing tests in `tests/review/test_api_import.py` per `contracts/import.md` — accepts multipart MP3, computes content hash, dedups on same hash, rejects unsupported format, returns 201 on new + 200 on dedup
- [X] T04- [X] T043 [US1] Implement `src/review/api/v1/import_.py` — multipart upload, SHA-256 hash first 16 hex, library lookup/create, ID3-tag parse for title/artist; T042 passes
- [X] T04- [X] T044 [P] [US1] Write failing tests in `tests/review/test_api_library.py` for `GET /api/v1/library` (single-song case only for US1) — returns songs[], folders[] (at least "unfiled"), `source_exists` computed from disk
- [X] T04- [X] T045 [US1] Implement `GET /api/v1/library` in `src/review/api/v1/library.py`; T044 passes
- [X] T04- [X] T046 [P] [US1] Write failing tests in `tests/review/test_api_analysis.py` covering `POST /api/v1/songs/<id>/analyze` (202 + run_id), `GET .../analysis` (200 with full AnalysisResult after completion, 409 `not_analyzed` before), and SSE stream basic shape (first event received within 2s, terminates with `overall.done`)
- [X] T04- [X] T047 [US1] Implement `src/review/api/v1/analysis.py` — wraps the existing `src/analyzer/runner.py`, streams per-detector progress via SSE, auto-populates section assignments with default-theme on completion (FR-012a); T046 passes
- [X] T04- [X] T048 [P] [US1] Write failing tests in `tests/review/test_api_sections.py` for `GET /api/v1/songs/<id>/sections` (split/merge/etc. live in US3)
- [X] T04- [X] T049 [US1] Implement `GET /api/v1/songs/<id>/sections` in `src/review/api/v1/sections.py`; T048 passes
- [X] T050 [P] [US1] Write failing tests in `tests/review/test_api_assignments.py` for `GET /api/v1/songs/<id>/assignments`, `PUT .../assignments/<idx>` (FR-032a override reset on theme change), and `POST .../assignments/accept-all` (FR-029a status transition to "themed")
- [X] T051 [US1] Implement `src/review/api/v1/assignments.py`; T050 passes
- [X] T052 [P] [US1] Write failing tests in `tests/review/test_api_layout.py` for `POST /api/v1/layout` (parses `xlights_rgbeffects.xml`, rejects invalid XML, returns `replaced_prior` flag per FR-036c) and `GET /api/v1/layout`
- [X] T053 [US1] Implement `src/review/api/v1/layout.py` (reuses existing layout-parsing from `src/layout/`); T052 passes
- [X] T054 [P] [US1] Write failing tests in `tests/review/test_api_export.py` covering `POST /api/v1/songs/<id>/export` (202 + export_id), SSE progress, 409 `incomplete_theming` with `missing_sections`, 409 `layout_required`, 409 `source_file_missing`
- [X] T055 [US1] Implement `src/review/api/v1/export.py` — wraps existing `src/generator/` pipeline, streams progress via SSE; T054 passes
- [X] T056 [P] [US1] Write failing tests in `tests/review/test_audio_stream.py` for `GET /audio/<song_id>` — streams bytes with `Accept-Ranges: bytes`, supports partial-content 206, returns 404 `source_file_missing` when path not found
- [X] T057 [US1] Implement the audio-stream route in `src/review/server.py`; T056 passes

### Frontend shared components for US1 (test-first)

- [X] T058 [P] [US1] Write failing tests in `src/review/frontend/tests/components/LightsPreview.test.tsx` — renders N cells, reacts to `playhead`/`energyPulse` props, compact flag hides label
- [X] T059 [P] [US1] Implement `src/review/frontend/src/components/LightsPreview/LightsPreview.tsx`; T058 passes
- [X] T060 [P] [US1] Write failing tests in `src/review/frontend/tests/components/MiniLights.test.tsx` — deterministic animation keyed on `themeId` + `kind`
- [X] T061 [P] [US1] Implement `src/review/frontend/src/components/MiniLights/MiniLights.tsx`; T060 passes
- [X] T062 [P] [US1] Write failing tests in `src/review/frontend/tests/components/Waveform.test.tsx` — renders SVG path from `peaks[]`, playhead line at correct x, per-section tint rects
- [X] T063 [P] [US1] Implement `src/review/frontend/src/components/Waveform/Waveform.tsx` per research §5 (inline SVG); T062 passes
- [X] T064 [P] [US1] Write failing tests in `src/review/frontend/tests/components/Ruler.test.tsx` — tick every 20s, click scrubs
- [X] T065 [P] [US1] Implement `src/review/frontend/src/components/Ruler/Ruler.tsx`; T064 passes
- [X] T066 [P] [US1] Write failing tests in `src/review/frontend/tests/components/Transport.test.tsx` — play/pause toggles, jump prev/next section, big timecode tabular
- [X] T067 [P] [US1] Implement `src/review/frontend/src/components/Transport/Transport.tsx`; T066 passes
- [X] T068 [P] [US1] Write failing tests in `src/review/frontend/tests/components/SectionStrip.test.tsx` — chips width proportional to duration, selected chip outlined, colored by assigned theme.accent
- [X] T069 [US1] Implement `src/review/frontend/src/components/SectionStrip/SectionStrip.tsx`; T068 passes
- [X] T069b [P] [US1] Write failing tests in `src/review/frontend/tests/components/DetectorTracks.test.tsx` — FR-017: toggle-able detector event tracks render below waveform, each track lane labeled by detector name, events positioned by `t_ms`, lanes hidden by default, visible after toggle
- [X] T069c [US1] Implement `src/review/frontend/src/components/DetectorTracks/DetectorTracks.tsx`; T069b passes
- [X] T070 [P] [US1] Write failing tests in `src/review/frontend/tests/components/ThemeCard.test.tsx` — renders swatches, `ASSIGNED` pill when active, double-stroke border on assigned state
- [X] T071 [P] [US1] Implement `src/review/frontend/src/components/ThemeCard/ThemeCard.tsx`; T070 passes
- [X] T072 [P] [US1] Implement `src/review/frontend/src/components/Inspector/Inspector.tsx` — generic right-rail container (per-screen inspector content slots via children). Tests co-located.

### CLI + audio hook

- [X] T073 [US1] Implement `src/review/cli.py` — `xlight review` command that starts Flask, opens `http://127.0.0.1:5000` in the default browser, reads `--dev` flag to skip auto-open
- [X] T074 [P] [US1] Write failing tests in `src/review/frontend/tests/hooks/useAudio.test.ts` — single `<audio>` element ref survives re-render, RAF-driven `time` updates fire at ~60Hz while playing, seek clamps to [0, duration]
- [X] T075 [US1] Implement `src/review/frontend/src/hooks/useAudio.ts` per research §6; T074 passes

### Screens for US1

- [X] T076 [P] [US1] Write failing tests in `src/review/frontend/tests/screens/Drop.test.tsx` — drop target accepts a file and calls the import API, rejects unsupported extensions pre-flight, auto-advances to analyze on success (FR-008)
- [X] T077 [US1] Implement `src/review/frontend/src/screens/Drop.tsx`; T076 passes
- [X] T078 [P] [US1] Write failing tests in `src/review/frontend/tests/screens/Analyze.test.tsx` — consumes SSE stream, renders per-detector rows (FR-009), overall progress (FR-010), enables `review timeline →` on completion (FR-012)
- [X] T079 [US1] Implement `src/review/frontend/src/screens/Analyze.tsx`; T078 passes
- [X] T080 [P] [US1] Write failing tests in `src/review/frontend/tests/screens/Timeline.test.tsx` — Transport + Ruler + SectionStrip + Waveform + LightsPreview composed correctly, playback continues across screen switches (FR-038)
- [X] T081 [US1] Implement `src/review/frontend/src/screens/Timeline.tsx`; T080 passes
- [X] T082 [P] [US1] Write failing tests in `src/review/frontend/tests/screens/Theme.test.tsx` — theme grid renders, clicking a card calls `PUT /assignments/<idx>` (T051), "accept all defaults" button flips song status to "themed" via `POST /assignments/accept-all` (FR-029a), live LightsPreview reflects current assignment
- [X] T083 [US1] Implement `src/review/frontend/src/screens/Theme.tsx`; T082 passes
- [X] T084 [P] [US1] Write failing tests in `src/review/frontend/tests/screens/Export.test.tsx` — shows layout-required block when `preferences.layout_id == null` (FR-036b), shows `incomplete_theming` block when applicable (FR-035), mapping table renders from `GET /export/mapping`, render button fires SSE-driven progress
- [X] T085 [US1] Implement `src/review/frontend/src/screens/Export.tsx`; T084 passes

### US1 wiring + navigation

- [X] T086 [US1] Wire `App.tsx` router keyed on `store.app.screen`; mounts each screen inside `<Chrome>`
- [X] T087 [US1] Wire auto-advance from DROP to ANALYZE on successful import; wire `review timeline →` button to advance to TIMELINE; wire TIMELINE → THEME via tool strip or implicit on themed-transition
- [X] T088 [US1] Wire the persistence hook (T039) so library, sections, assignments, and preferences writes fire on every meaningful state change (FR-049a)

**Checkpoint**: US1 MVP shippable — a hobbyist can go from empty-app to exported `.xsq` on a single song. SC-001 (≤15 min end-to-end), SC-002 (60fps scrub), SC-005 (design-token fidelity) verifiable here.

---

## Phase 4: User Story 2 — Multi-Song Library Management (Priority: P2)

**Goal**: A returning user sees every imported song, filters by status, and jumps directly to the screen matching each song's state.

**Independent Test**: Import three songs (analyze one, theme one, leave one as draft). Close and reopen the app. Library shows all three with correct status chips. Clicking the `analyzed` filter pill shows only that one. Clicking the themed song opens THEME directly; clicking the draft opens ANALYZE.

### API (test-first)

- [X] T089 [P] [US2] Extend tests in `tests/review/test_api_library.py` for the multi-song case, `GET /library` ordering, folder listing
- [X] T090 [US2] Extend `GET /api/v1/library` to return full multi-song + folder-tree response; T089 passes
- [X] T091 [P] [US2] Write failing tests in `tests/review/test_api_folders.py` for `POST /api/v1/folders`, `PATCH /api/v1/folders/<id>`, `DELETE /api/v1/folders/<id>` (moves songs to `unfiled`, can't delete reserved `unfiled`), `PATCH /api/v1/songs/<id>/folder`
- [X] T092 [US2] Implement folder CRUD endpoints in `src/review/api/v1/library.py`; T091 passes
- [X] T093 [P] [US2] Write failing tests in `tests/review/test_api_song_delete.py` for `DELETE /api/v1/songs/<id>` (drops Session + returns `cache_purge_available`) and `POST /api/v1/songs/<id>/purge` (purges analysis cache + stems, FR-005a/b)
- [X] T094 [US2] Implement song delete + cache purge endpoints; T093 passes

### Frontend

- [X] T095 [P] [US2] Write failing tests in `src/review/frontend/tests/screens/Library.test.tsx` — song grid/list, filter pills (all/themed/analyzed/draft) update view in < 200ms keystroke → render (SC-007), folder sections collapsible, clicking a song routes by status (FR-003)
- [X] T096 [US2] Implement `src/review/frontend/src/screens/Library.tsx` using the existing Chrome.LibraryRail shell from T034; T095 passes
- [X] T097 [P] [US2] Extend LibraryRail in Chrome (from T034) to render the folder tree + per-song status chips + active-song highlight; unit tests under `src/review/frontend/tests/components/Chrome.test.tsx`
- [X] T098 [US2] Wire drag-and-drop of a song between folders (calls `PATCH /songs/<id>/folder`) in the rail
- [X] T099 [US2] Wire the "remove from library" action on a library entry (calls `DELETE /songs/<id>` then presents the cache-purge dialog; purge calls `POST /songs/<id>/purge`)
- [X] T100 [US2] Wire `preferences.last_song_id` + `last_screen` restore on app boot — SC-004 (< 2 s to first paint)

**Checkpoint**: US2 complete — multi-song library with folders, status routing, and deletion; SC-004, SC-007 verifiable.

---

## Phase 5: User Story 3 — Section Boundary Editing (Priority: P2)

**Goal**: User enters sections edit mode on TIMELINE and can split/merge/promote/rename/delete sections, with theme inheritance matching clarifications (split inherits both, merge first-wins, promote inherits both), and reset to detected. Re-analysis review dialog handles theme mapping before commit.

**Independent Test**: On a themed song, enter sections edit mode. Split a section — both halves retain the theme. Merge — result keeps first theme. Promote a ghost boundary — both sides inherit. Delete (not last). Rename. Reset. Force a re-analysis and verify the review dialog surfaces moved/dropped/needs-theme rows.

### API (test-first)

- [X] T101 [P] [US3] Write failing tests in `tests/review/test_api_sections_edit.py` per [contracts/sections.md](contracts/sections.md): split (FR-021, sub-500ms rejected, theme inherit both), merge (FR-022, first-wins), promote-ghost (FR-025, inherit), delete (FR-023, last-section guard), rename (FR-024), reset (FR-026, restores detected + re-derives default themes per FR-012a)
- [X] T102 [US3] Implement the five section edit endpoints in `src/review/api/v1/sections.py`; T101 passes
- [X] T103 [P] [US3] Extend `POST /api/v1/songs/<id>/analyze` tests in `tests/review/test_api_analysis.py` to cover the `force: true` flag on analyzed/themed songs (does NOT overwrite session yet) and `POST .../analyze/commit` endpoint with `assignment_mapping` body per FR-013a
- [X] T104 [US3] Implement `force` flag + `POST .../analyze/commit` endpoint in `src/review/api/v1/analysis.py`; T103 passes
- [X] T105 [P] [US3] Write failing tests in `tests/review/test_overlap_mapping.py` for the max-overlap algorithm (research §10): 0.3 threshold, orphan detection, new-sections-need-theme detection
- [X] T106 [US3] Implement overlap-mapping utility in `src/review/api/v1/analysis.py` (or a helper module); T105 passes

### Frontend

- [X] T107 [P] [US3] Write failing tests in `src/review/frontend/tests/util/overlap.test.ts` — mirror of T105 at the client (the review dialog also computes the proposed mapping client-side for instant UI)
- [X] T108 [US3] Implement `src/review/frontend/src/util/overlap.ts`; T107 passes
- [X] T109 [P] [US3] Write failing tests in `src/review/frontend/tests/components/SectionsEditMode.test.tsx` — mode toggle, `S`/`M`/`Del`/`R` keyboard shortcuts (FR-042), ghost-boundary UI on the timeline, section-rename inline edit
- [X] T110 [US3] Implement `src/review/frontend/src/components/SectionsEditMode/*` + wire into Timeline screen; T109 passes
- [X] T111 [P] [US3] Write failing tests in `src/review/frontend/tests/components/ReanalysisDialog.test.tsx` — lists carry-over / shifted / dropped / needs-theme rows, confirm calls `POST .../analyze/commit`, cancel keeps prior analysis intact
- [X] T112 [US3] Implement `src/review/frontend/src/components/ReanalysisDialog/ReanalysisDialog.tsx`; T111 passes

**Checkpoint**: US3 complete — all section edits work with correct theme inheritance; re-analysis is safe and reviewable.

---

## Phase 6: User Story 4 — Per-Section Theme Parameter Tuning (Priority: P3)

**Goal**: On the THEME screen inspector, four sliders (brightness, hit strength, dwell time, color shift) adjust a theme's behavior on the selected section. Changes preview live. Overrides reset on theme change (FR-032a).

**Independent Test**: Theme a song. Select section A, slide brightness to 0.5 — live preview dims. Change theme on A — sliders reset. Switch to section B — B shows default values. Export — rendered output applies overrides per section.

- [X] T113 [P] [US4] Write failing tests in `src/review/frontend/tests/components/ParameterSliders.test.tsx` — each slider bound to `assignments.overrides.<field>`, values persist via `PUT /assignments/<idx>`, theme change wipes values to new theme defaults (FR-032a)
- [X] T114 [US4] Implement `src/review/frontend/src/components/ParameterSliders/ParameterSliders.tsx` and mount in the Theme-screen Inspector; T113 passes
- [X] T115 [US4] Verify `PUT /api/v1/songs/<id>/assignments/<idx>` correctly handles partial `overrides` bodies + theme-change-triggered reset (tests already in T050; add regression cases if missing)
- [X] T116 [US4] Wire ParameterSliders into the LightsPreview on the Theme screen so slider drags produce immediate visual feedback (no round-trip required for preview — server only hears the final value via the normal persistence flow)
- [X] T117 [US4] Confirm the Export pipeline (T055) picks up `overrides` per section — add an end-to-end test at `tests/review/test_api_export.py` that asserts a song with non-default overrides produces different output bytes than the same song with defaults

**Checkpoint**: US4 complete — per-section tuning works end-to-end.

---

## Phase 7: User Story 5 — Visual Preferences & Keyboard-First (Priority: P3)

**Goal**: Dark/light, density, inspector visibility take effect immediately and persist. Every screen reachable and operable by keyboard alone per SC-006.

**Independent Test**: Open tweaks, toggle each preference — UI updates instantly. Close and reopen the app — preferences restored. Without using the mouse, complete the US1 chain from drop to export.

### API

- [X] T118 [P] [US5] Write failing tests in `tests/review/test_api_preferences.py` for `GET` and `PUT /api/v1/preferences` (partial updates, validation rejects unknown `mode` value)
- [X] T119 [US5] Implement `src/review/api/v1/preferences.py`; T118 passes

### Frontend

- [X] T120 [P] [US5] Write failing tests in `src/review/frontend/tests/store/preferences.test.ts` for the preferences store slice — reducer + derivation to `data-mode`
- [X] T121 [US5] Implement `src/review/frontend/src/store/preferences.ts` per T030 scaffold; T120 passes
- [X] T122 [P] [US5] Wire TweaksPanel (T035) segmented controls to `store.preferences` and back to `PUT /api/v1/preferences` via the persistence hook
- [X] T123 [P] [US5] Write failing tests in `src/review/frontend/tests/hooks/useKeyboard.integration.test.tsx` — each FR-041 global shortcut (`space`, `←`/`→`, `Shift+←`/`Shift+→`, `1`–`6`) fires the right store action, input-focus suppresses shortcuts
- [X] T124 [US5] Register global shortcuts in `src/review/frontend/src/App.tsx` using the registry from T037; T123 passes
- [X] T125 [US5] Register TIMELINE-sections-edit-mode shortcuts (FR-042: `S`/`M`/`Del`/`R`) inside the SectionsEditMode component (T110); they unregister when the mode exits
- [X] T126 [US5] Implement the `inspector_open` toggle + density compact/comfortable CSS (CSS custom property switches `:root { --density: ... }`)

**Checkpoint**: US5 complete — all preferences persist, keyboard-only US1 passes SC-006.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Library portability, source-missing UX, first-run empty-library polish, legacy cutover, build pipeline, end-to-end smoke, performance verification.

### Library portability (FR-049c)

- [ ] T127 [P] Write failing tests in `tests/review/test_api_library_portability.py` for `POST /api/v1/library/export` (produces valid zip, includes library.json + per-song session.json, excludes audio) and `POST /api/v1/library/import` (merge + replace modes, `source_missing_songs` populated when audio isn't found)
- [ ] T128 Implement library export/import endpoints in `src/review/api/v1/preferences.py` using the bundle utility from T018; T127 passes
- [ ] T129 [P] Implement the "Export library" and "Import library" actions in the TweaksPanel (T035) with the replace-mode double-confirm

### Source-file-missing experience

- [ ] T130 [P] Write failing tests in `src/review/frontend/tests/integration/source_missing.test.tsx` — a song whose audio path returns 404 on `/audio/<id>` enters `source_missing` state; library rail shows the affordance; playback/preview/export blocked; section/theme edits still allowed (FR-001a)
- [ ] T131 Implement the `source_missing` state handling across screens: library rail badge, "locate file" action that calls a (new) `POST /api/v1/songs/<id>/relocate` endpoint, blocked-button affordances on TIMELINE / THEME / EXPORT
- [ ] T132 [P] Write failing tests in `tests/review/test_api_relocate.py` for `POST /api/v1/songs/<id>/relocate` — user provides a new absolute path, backend verifies the file at that path hashes to the song's `song_id`, appends to `source_paths`, returns updated Song
- [ ] T133 Implement relocate endpoint; T132 passes

### First-run polish

- [ ] T134 Implement the empty-library first-run centered drop target per FR-005c in `src/review/frontend/src/screens/Library.tsx`
- [ ] T135 Implement the "import your xLights layout to continue" export-screen block per FR-036b

### Cutover (destructive — do last, single commit)

- [ ] T136 Delete every file under `src/review/static/` (the old vanilla-JS frontend)
- [ ] T137 Delete the legacy route modules: `src/review/brief_routes.py`, `generate_routes.py`, `grouper.py`, `preview_routes.py`, `story_routes.py`, `theme_routes.py`, `variant_routes.py`
- [ ] T138 Rewrite `src/review/server.py` — Flask app that serves `src/review/frontend/dist/index.html` at `/`, `dist/assets/*` at `/assets/*`, audio at `/audio/<id>` (T057), and mounts `/api/v1/*` blueprint (T020). Remove the old route imports. Existing tests in `tests/review/` must still pass.
- [ ] T139 Search-and-destroy any remaining references to the deleted route modules across the codebase (CLI, integration tests, docs) and update or remove them

### Build pipeline & distribution

- [ ] T140 Run `npm run build` in `src/review/frontend/`, commit the resulting `dist/` assets
- [ ] T141 Add a `Makefile` target or `scripts/build-frontend.sh` that runs the build step and stages `dist/` for commit — documented in `specs/051-x-onset-frontend/quickstart.md`
- [ ] T142 Update the top-level `README.md` (or `CLAUDE.md` quick-reference) with the new `xlight review` command

### End-to-end smoke + performance

- [ ] T143 Implement `src/review/frontend/tests/e2e/happy-path.spec.ts` — Playwright walk of US1 against a real Flask + dev server: drop the fixture MP3, wait for ANALYZE to complete, click `review timeline →`, scrub, switch to THEME, click "accept all defaults", visit EXPORT, provide a test `xlights_rgbeffects.xml`, click render, assert the output file exists
- [ ] T144 [P] Benchmark SC-002 (60fps during scrub) with Playwright frame-timing capture on a 4-minute song; record result in a comment in the e2e spec
- [ ] T145 [P] Benchmark SC-004 (< 2 s restore after restart) — close the app programmatically in the e2e test, re-open, assert time from first paint to restored-state-visible
- [ ] T146 [P] Benchmark SC-007 (< 200 ms filter keystroke → render) — unit test with 100 synthetic songs in the library store
- [ ] T147 [P] Benchmark SC-008 (< 1 s to show analysis on a previously-analyzed song) — API-side test that `GET /api/v1/songs/<id>/analysis` returns within budget when the cache is warm

### Visual QA

- [ ] T148 Run `openwolf designqc` via Bash, capture screenshots of every screen in both dark and light modes, compare side-by-side to [design_handoff_xonset/Prototype.html](design_handoff_xonset/Prototype.html), file diffs as follow-up issues if any. Verify all FR-047 visual-identity requirements (color tokens, typography, spacing grid, sharp corners, tabular numerals, unicode glyphs).

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no prerequisites
- **Foundational (Phase 2)**: depends on Setup; BLOCKS every user story
- **US1 (Phase 3)**: depends on Foundational; independent of US2–US5
- **US2 (Phase 4)**: depends on US1 (shares Chrome.LibraryRail, Library screen shell)
- **US3 (Phase 5)**: depends on US1 (extends Timeline + sections endpoints)
- **US4 (Phase 6)**: depends on US1 (extends Theme screen Inspector + assignments endpoint)
- **US5 (Phase 7)**: depends on Foundational; independent of US1–US4 functionally, but Library first-run polish in Polish depends on US2 UI being present
- **Polish (Phase 8)**: depends on US1 + US2 at minimum; cutover (T136–T139) depends on every user story being functionally complete in the new UI

### Within each user story

Tests MUST be written and confirmed failing before the matching implementation task. Task IDs are ordered so a top-down execution satisfies this naturally.

### Parallel opportunities

- **Phase 1**: T002–T008 all run independently after T001
- **Phase 2**: T011/T013/T015/T017 are [P] storage tests; T019 is [P] (API base); T022/T023/T024 are [P] design tokens; T026/T028 are [P] store tests; T031/T032 are [P] client utilities; T033/T036/T038 are [P] component/hook tests
- **Phase 3 (US1)**: every endpoint's test-then-implementation pair (T040/T041 ... T056/T057) is independent of other pairs — six backend pipelines can land in parallel. Every shared component pair (T058/T059 ... T070/T071) is independent of the others — six components can land in parallel. Screen pairs (T076/T077 ... T084/T085) depend only on their shared components being done
- **Phase 4 (US2)**: T089/T091/T093 tests and impls can be three parallel tracks (library list, folders, song delete)
- **Phase 5 (US3)**: T101 section edits and T103 re-analysis are parallel backend tracks; T107 overlap and T109 SectionsEditMode are parallel frontend tracks
- **Phase 8**: T144–T148 polish tasks all run in parallel

### Parallel team strategy

After Foundational:
- **Developer A** drives US1 end-to-end (the deepest phase)
- **Developer B** picks up US3 section editing once US1 Timeline lands
- **Developer C** picks up US5 preferences + keyboard in parallel with US1 (minimal cross-dependency)

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Setup (T001–T010)
2. Foundational (T011–T039) — critical, blocks everything
3. US1 (T040–T088) — ship with a single-song flow; the full product value in its simplest form
4. **Stop, validate, consider shipping.** Every downstream phase is strictly additive.

### Incremental delivery

Each phase checkpoint is a coherent increment:
- After US1 → hobbyist can produce a themed `.xsq` from a single song
- After US2 → multi-song library + deletion
- After US3 → section editing + re-analysis safety
- After US4 → per-section tuning sliders
- After US5 → keyboard-only + visual preferences
- After Polish → library portability, source-missing UX, cutover complete, build pipeline in place, e2e smoke passing

---

## Notes

- Every test task MUST be run and observed failing before the matching implementation task begins (constitution IV).
- `src/review/frontend/dist/` is committed — refresh it (T140) before every release; forgetting leaves end-users with stale UI after `pip install`.
- Legacy cutover (T136–T139) is destructive and must land in a single commit so main never ships in a half-cutover state.
- Per [memory/no-xlights-in-tests](../../../home/node/.claude/projects/-workspace/memory/feedback_no_xlights_in_tests.md), `xlights-check` / `xlights-render` MUST NOT run in any automated test; they are manual verification tools only. The Playwright happy-path test produces a `.xsq` file and asserts its existence on disk, but does NOT invoke xLights to render it.
- Commit after each completed task or coherent task group; do not batch unrelated changes (constitution).
