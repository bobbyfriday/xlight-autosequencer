# Tasks: Timing Track Review UI

**Input**: Design documents from `/specs/002-track-review-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui.md

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Exact file paths included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add Flask dependency and create the `src/review/` package skeleton

- [X] T001 Add `flask>=3.0` to `[project.dependencies]` in `pyproject.toml`
- [X] T002 Create `src/review/` package: `src/review/__init__.py` (empty), `src/review/server.py` (stub), `src/review/static/` directory with empty `index.html`, `app.js`, `style.css`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Flask app factory and CLI entry point — everything US1–US4 builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement Flask app factory `create_app(analysis_path: str, audio_path: str) -> Flask` in `src/review/server.py`: stores paths in `app.config`, registers a blueprint placeholder, returns the app instance
- [X] T004 Add `review` subcommand to `src/cli.py`: accepts `<analysis_json>` argument, validates the file exists and is valid JSON (exit 4 if not), resolves `song_path` from the JSON and checks it exists (exit 3 if not), calls `create_app()`, opens browser via `threading.Timer(0.5, webbrowser.open, args=['http://localhost:5173/'])`, and starts Flask on `host='127.0.0.1', port=5173` with `use_reloader=False`

**Checkpoint**: `xlight-analyze review song_analysis.json` starts Flask and opens a browser tab (404 until US1 routes are wired, but server is live)

---

## Phase 3: User Story 1 — Visualise Timing Tracks Against Audio (Priority: P1) MVP

**Goal**: Load an analysis JSON, render all tracks as horizontal canvas lanes with marks at correct proportional positions along a time axis. No audio required.

**Independent Test**: Load a known analysis JSON. Without playing audio, the page renders all tracks with the correct number of named lanes, marks visible at proportional positions, and a quality score beside each name.

### Implementation for User Story 1

- [X] T005 [P] [US1] Add `GET /analysis` route to `src/review/server.py`: returns `flask.jsonify` of the full analysis JSON loaded from `app.config['ANALYSIS_PATH']`
- [X] T006 [P] [US1] Add `GET /` route to `src/review/server.py`: returns `flask.send_from_directory(app.static_folder, 'index.html')`; configure `static_folder` to point to `src/review/static/`
- [X] T007 [US1] Write `src/review/static/index.html`: two-canvas overlay container (background canvas id `bg-canvas`, foreground canvas id `fg-canvas` stacked via `position: absolute`), left panel column (200px) containing per-lane name/score/type/Solo/checkbox controls rendered by JS, play/pause button, time display, export button
- [X] T008 [P] [US1] Write `src/review/static/style.css`: flex layout with fixed-height track list, 200px left panel, canvas container filling remaining width; lane row height 60px; scrollable track list; muted color scheme
- [X] T009 [US1] Implement background canvas renderer in `src/review/static/app.js`: on page load fetch `GET /analysis`, build `TrackLane` objects sorted by `quality_score` descending, draw time axis (mm:ss ticks every 10 s) and one lane per track (marks as 1px vertical lines at `time_ms / duration_ms * canvasWidth`); high-density tracks (`quality_score == 0` or `avg_interval_ms < 200`) draw marks in `#e44` red
- [X] T010 [P] [US1] Write server-side test for `GET /analysis` in `tests/unit/test_review_server.py`: create Flask test client with a fixture analysis JSON path, assert `200`, `Content-Type: application/json`, and that `tracks` array length matches fixture

**Checkpoint**: `xlight-analyze review song_analysis.json` shows all tracks rendered with names, quality scores, and marks on the timeline — no audio needed

---

## Phase 4: User Story 2 — Synchronised Audio Playback (Priority: P2)

**Goal**: Play the MP3; a playhead moves left-to-right in sync with audio. Click timeline to seek. Pause and resume.

**Independent Test**: Play a 10-second test clip. The playhead travels from start to end within 10 ± 0.5 seconds. Clicking the 50% mark scrubs audio to approximately the halfway point.

### Implementation for User Story 2

- [X] T011 [P] [US2] Add `GET /audio` route to `src/review/server.py`: serves the MP3 via `flask.send_file(app.config['AUDIO_PATH'], mimetype='audio/mpeg', conditional=True)` — `conditional=True` enables Range request support (206 Partial Content) via Werkzeug
- [X] T012 [P] [US2] Write server-side test for `GET /audio` in `tests/unit/test_review_server.py`: assert `200`, `Content-Type: audio/mpeg`, `Accept-Ranges: bytes` response header present
- [X] T013 [US2] Add `<audio id="player" src="/audio" preload="auto">` to `src/review/static/index.html`; wire play/pause button click handler and `timeupdate` event in `src/review/static/app.js`; implement `requestAnimationFrame` loop that reads `player.currentTime` and redraws the foreground canvas with the playhead line at `x = (player.currentTime / player.duration) * canvasWidth`
- [X] T014 [US2] Implement timeline click-to-seek in `src/review/static/app.js`: on `mousedown` on the canvas container, compute `seekTime = (offsetX / canvasWidth) * player.duration`, set `player.currentTime = seekTime`, update playhead position immediately; handle `player.ended` event to stop rAF loop and reset play button label

**Checkpoint**: Play button starts audio and playhead moves in sync; clicking timeline scrubs; pause/resume works

---

## Phase 5: User Story 3 — Quick Track Switching and Focus Mode (Priority: P3)

**Goal**: Next/Prev buttons (+ keyboard shortcuts) cycle focus through tracks. Focused track is highlighted; others are dimmed. Solo button directly focuses any track. Clear focus restores equal visibility.

**Independent Test**: Load 10 tracks. Press Next 5 times — 6th track is highlighted, others dimmed. Press Prev once — 5th track is highlighted. Audio playback (if running) is uninterrupted throughout.

### Implementation for User Story 3

- [X] T015 [P] [US3] Add Next, Prev, and Clear Focus buttons to the toolbar in `src/review/static/index.html`; add a Solo `[S]` button to each lane row in the left panel (rendered by JS alongside track name/score)
- [X] T016 [US3] Implement focus state in `src/review/static/app.js`: `focusIndex` variable (int or null); `setFocus(i)` sets `focusIndex`, redraws foreground overlay (semi-transparent black rect over all lanes except focused; focused lane gets 2px blue border); `clearFocus()` sets `focusIndex = null`, clears overlay; `focusNext()` / `focusPrev()` increment/decrement with wraparound
- [X] T017 [US3] Implement keyboard shortcut handler in `src/review/static/app.js`: attach `keydown` listener to `document`; Space → toggle play/pause + `preventDefault`; `ArrowRight` or `n` → `focusNext()`; `ArrowLeft` or `p` → `focusPrev()`; `Escape` → `clearFocus()`; `preventDefault` on Space and arrow keys to suppress browser scroll
- [X] T018 [US3] Wire Solo button per lane in `src/review/static/app.js`: clicking Solo on the currently focused track calls `clearFocus()`; clicking Solo on any other track calls `setFocus(i)`; Next/Prev/Clear Focus buttons call `focusNext()`, `focusPrev()`, `clearFocus()` respectively

**Checkpoint**: Next/Prev/Solo focus navigation works with keyboard and buttons; focus overlay renders correctly; audio continues playing when switching focus

---

## Phase 6: User Story 4 — Track Selection and Export (Priority: P4)

**Goal**: Each track has a checkbox. Export Selection writes a filtered analysis JSON to disk containing only selected tracks.

**Independent Test**: Load 8 tracks, deselect 3, click Export. The resulting file contains exactly 5 tracks matching the selected names, with all mark data intact.

### Implementation for User Story 4

- [X] T019 [P] [US4] Implement `POST /export` route in `src/review/server.py`: receives `{"selected_track_names": [...]}` (and optional `"overwrite": true`); loads source analysis JSON; filters to selected tracks; computes output path as `source_basename_selected.json` (replace `_analysis.json` → `_selected.json` if present, otherwise append `_selected`); returns `409 {"warning": "File exists", "path": "..."}` if output exists and `overwrite` not set; writes filtered JSON and returns `200 {"path": "..."}` on success; returns `400 {"error": "No tracks selected"}` if `selected_track_names` is empty
- [X] T020 [P] [US4] Write server-side tests for `POST /export` in `tests/unit/test_review_server.py`: test success (5 of 8 tracks), test empty selection returns 400, test overwrite returns 409 without flag and succeeds with `"overwrite": true`
- [X] T021 [US4] Add selection checkboxes to lane rows in `src/review/static/app.js` (checked by default); maintain `track.selected` boolean per lane; deselected lanes render at 40% opacity on background canvas (trigger background canvas redraw on checkbox toggle)
- [X] T022 [US4] Implement Export Selection button in `src/review/static/app.js`: collect all `track.selected == true` names; if zero, show inline warning and abort; POST to `/export`; on `409` show overwrite confirmation dialog and re-POST with `"overwrite": true` on confirm; on `200` show success message with the returned `path`; disable Export button when zero tracks are selected

**Checkpoint**: Checking/unchecking tracks visually dims them; Export writes the correct filtered file next to the source analysis JSON

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, UX refinements, and validation across all stories

- [X] T023 [P] Add port-in-use handling to `src/cli.py`: wrap `app.run()` in a try/except for `OSError` (errno `EADDRINUSE`); print clear error message and exit with code 5
- [X] T024 [P] Add "N selected / N total" counter near the Export button in `src/review/static/index.html` + `src/review/static/app.js`, updated on every checkbox toggle
- [X] T025 Verify all Flask routes return correct status codes and headers by running `pytest tests/unit/test_review_server.py -v` and confirming all tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — blocks all user stories
- **US1 (Phase 3)**: Depends on Foundational — first story, no story dependencies
- **US2 (Phase 4)**: Depends on Foundational + US1 HTML structure (adds `<audio>` to existing page)
- **US3 (Phase 5)**: Depends on US1 (canvas and lane list must exist before focus overlay)
- **US4 (Phase 6)**: Depends on US1 (lane list must exist before adding checkboxes)
- **Polish (Phase 7)**: Depends on all user story phases

### User Story Dependencies

- **US1 (P1)**: Independent — start after Foundational
- **US2 (P2)**: Depends on US1 HTML skeleton (`index.html` must exist for `<audio>` addition)
- **US3 (P3)**: Depends on US1 canvas and lane rendering being in place
- **US4 (P4)**: Depends on US1 lane list being in place for checkbox injection

### Within Each User Story

- Server-side routes and client-side rendering tasks marked `[P]` can run in parallel
- Client-side tasks that modify the same file (`app.js`) must run sequentially
- Test tasks for a story can be written in parallel with implementation

### Parallel Opportunities

- T005, T006 (US1 routes) can run in parallel
- T008 (style.css) can run in parallel with T005, T006
- T010 (server test) can run in parallel with T007, T009 (client-side tasks)
- T011, T012 (US2 audio route + test) run in parallel
- T015, T016 can start in parallel (different concerns: HTML vs JS state)
- T019, T020 (US4 server + test) run in parallel

---

## Parallel Example: User Story 1

```text
Parallel group A (server-side):
  T005  GET /analysis route in server.py
  T006  GET / route in server.py
  T010  Server test in test_review_server.py

Parallel group B (client-side static):
  T008  style.css layout

Sequential (client-side, shared app.js):
  T007  index.html shell
  T009  Background canvas renderer in app.js
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T010)
4. **STOP and VALIDATE**: Load a real analysis JSON, confirm all tracks appear with names, scores, and marks. Run `pytest tests/unit/test_review_server.py -v`.
5. Ready for US2

### Incremental Delivery

1. Setup + Foundational → server starts and opens browser
2. US1 → timeline renders (MVP: static visualisation)
3. US2 → add audio playback and playhead sync
4. US3 → add focus/solo keyboard navigation
5. US4 → add selection checkboxes and export

### Single Developer

Work the phases in order (Phase 1 → 7). Within each phase, use `[P]` markers to batch server-side and client-side work in a single message to the LLM.

---

## Notes

- `[P]` tasks touch different files — safe to implement in the same LLM turn
- Flask test client in `tests/unit/test_review_server.py` uses `create_app()` with fixture paths — no live server needed for tests
- Canvas rendering tasks (`app.js`) are sequential because they all modify the same file
- `conditional=True` in `send_file()` is the key to Range request support — do not omit it
- `focusIndex` and `track.selected` are independent state — verify they never interfere
- Commit after each completed phase checkpoint
