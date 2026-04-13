# Tasks: In-Browser MP3 Upload and Analysis

**Input**: Design documents from `/specs/007-upload-and-analyze/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/upload.md

**Organization**: Tasks grouped by user story. Each phase is independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Exact file paths included in every description

---

## Phase 1: Setup

**Purpose**: Create new static files needed before any routes are implemented

- [x] T001 Create empty `src/review/static/upload.html` and `src/review/static/upload.js` placeholder files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend `create_app()` and the `review` CLI command to support upload mode — everything US1–US3 builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Add `AnalysisJob` class to `src/review/server.py`: fields `mp3_path`, `include_vamp`, `include_madmom`, `status` (str: `"running"/"done"/"error"`), `events: list[dict]`, `total: int`, `result_path: str | None`, `error_message: str | None`, `lock: threading.Lock`; method `record_progress(self, idx: int, total: int, name: str, mark_count: int) -> None` appends `{"idx": idx, "total": total, "name": name, "mark_count": mark_count}` to `self.events` under `self.lock`
- [x] T003 Extend `create_app()` signature in `src/review/server.py` to `create_app(analysis_path: str | None = None, audio_path: str | None = None) -> Flask`: when both are `None` register upload-mode routes (stubs returning 501 for now) and serve `upload.html` at `GET /`; when both provided retain existing timeline behaviour unchanged; store a module-level `_current_job: AnalysisJob | None = None` variable
- [x] T004 Modify `review` CLI command in `src/cli.py`: change `analysis_json` argument to `@click.argument("analysis_json", required=False, default=None)`; add `if analysis_json is None:` branch that calls `create_app()` (no arguments) and starts Flask on port 5173 — skip all file/audio validation in this branch

**Checkpoint**: `xlight-analyze review` (no args) starts Flask and opens browser showing a blank upload page; `xlight-analyze review song.json` still works as before

---

## Phase 3: User Story 1 — Upload MP3 and Start Analysis (Priority: P1) MVP

**Goal**: User selects or drags an MP3, clicks Analyze, analysis runs in the background, browser auto-navigates to timeline when done.

**Independent Test**: Run `xlight-analyze review` with no args. Drag a valid MP3 onto the upload page and click Analyze. Confirm the browser transitions to the progress view and then automatically navigates to `http://127.0.0.1:5173/` (the timeline) when analysis completes. Verify `<filename>_analysis.json` was written to the working directory.

### Implementation for User Story 1

- [x] T005 [P] [US1] Implement `POST /upload` route in `src/review/server.py`: accept `multipart/form-data` with field `mp3` (file) and form fields `vamp` and `madmom` (strings `"true"/"false"`, default `"true"`); validate `.mp3` extension (return `400 {"error": "..."}` if invalid); check `_current_job` is None (return `409 {"error": "Analysis already running"}` if busy); save file to `os.path.join(os.getcwd(), secure_filename(file.filename))`; create `AnalysisJob`, set as `_current_job`; start `threading.Thread(target=_run_analysis, args=(app, job), daemon=True)`; return `202 {"status": "started", "filename": ..., "total": len(algo_list)}`
- [x] T006 [P] [US1] Implement `_run_analysis(app, job: AnalysisJob)` function in `src/review/server.py`: inside `with app.app_context()`: build `algo_list` from `default_algorithms(include_vamp=job.include_vamp, include_madmom=job.include_madmom)`; set `job.total = len(algo_list)`; call `AnalysisRunner(algo_list).run(job.mp3_path, progress_callback=job.record_progress)`; if zero tracks set `job.status = "error"` and `job.error_message`; else call `export.write(result, out_path)`, set `job.result_path` and `job.status = "done"`; on any exception set `job.status = "error"`
- [x] T007 [US1] Write `src/review/static/upload.html`: dark-themed page with a drop zone div (`id="drop-zone"`), a file input (`id="file-input"`, `accept=".mp3"`), a "Browse" button, a selected filename display (`id="file-name"`), Vamp checkbox (`id="chk-vamp"`, checked by default, label "Vamp plugins (~14 tracks)"), madmom checkbox (`id="chk-madmom"`, checked by default, label "madmom (~2 tracks)"), an Analyze button (`id="btn-analyze"`, disabled until file selected); a progress section (`id="progress-section"`, hidden initially) containing a progress bar (`id="progress-bar"`), a status line (`id="status-line"`), and an algorithm list (`id="algo-list"`); link to `upload.js`
- [x] T008 [US1] Write `src/review/static/upload.js`: drag-and-drop handlers on `#drop-zone` (`dragover` preventDefault + highlight, `dragleave` unhighlight, `drop` extract file + validate `.mp3`); `#file-input` `change` handler; `#btn-analyze` `click` handler: POST `FormData` to `/upload`, on `202` hide upload form, show `#progress-section`, call `startProgressStream()`; `startProgressStream()` creates `new EventSource('/progress')`, on each `message` event parses JSON and either appends algorithm row to `#algo-list` + updates progress bar, or (on `done`) sets `window.location.href = '/'` after 500ms delay, or (on `error`) shows error message with a "Try again" reload button
- [x] T009 [P] [US1] Write `POST /upload` tests in `tests/unit/test_review_upload.py`: test `202` with valid MP3 bytes + `filename="song.mp3"`; test `400` with a non-MP3 filename; test `409` when a job is already running; test that `_current_job` is set after a successful upload (check via `GET /job-status`)

**Checkpoint**: Full end-to-end: upload MP3 in browser → progress appears → browser navigates to timeline. Run `pytest tests/unit/test_review_upload.py -v` — all pass.

---

## Phase 4: User Story 2 — Live Analysis Progress (Priority: P2)

**Goal**: Browser receives per-algorithm progress events in real time as analysis runs. Individual algorithm failures are shown but do not abort the run.

**Independent Test**: Start an analysis. Verify the `#algo-list` grows with one row per algorithm as each completes. Verify the progress bar reaches 100% before navigation. Verify that a known-failing algorithm (e.g. with Vamp disabled) does not prevent the rest from running and showing in the list.

### Implementation for User Story 2

- [x] T010 [P] [US2] Implement `GET /progress` SSE route in `src/review/server.py`: return `Response(stream_with_context(_progress_generator()), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`; `_progress_generator()` iterates `_current_job.events` from index 0, sleeping `0.2s` when caught up; yields `f"data: {json.dumps(event)}\n\n"` per event; when `_current_job.status != "running"` and all events yielded, sends terminal event: `data: {"done": true, "result_path": "..."}` or `data: {"error": "..."}` then returns; if `_current_job` is None yields `data: {"error": "No active job"}\n\n` and returns
- [x] T011 [P] [US2] Implement `GET /job-status` route in `src/review/server.py`: if `_current_job` is None return `{"status": "idle"}`; else return `{"status": job.status, "events_count": len(job.events), "total": job.total, "result_path": job.result_path, "error": job.error_message}`
- [x] T012 [US2] Add reconnection logic to `src/review/static/upload.js`: on page load call `fetch('/job-status')`; if `status == "running"` hide upload form, show progress section, call `startProgressStream()` (reconnects EventSource from current index); if `status == "done"` immediately redirect to `'/'`; if `status == "idle"` show upload form normally
- [x] T013 [P] [US2] Write `GET /progress` and `GET /job-status` tests in `tests/unit/test_review_upload.py`: test `/job-status` returns `{"status": "idle"}` when no job; test `/job-status` returns `"running"` fields when a mock job is set; test `/progress` with a pre-populated completed job returns all events plus terminal `done` event in the streamed body

**Checkpoint**: Progress bar fills in real time during analysis; algorithm rows appear as each completes; page auto-navigates on completion

---

## Phase 5: User Story 3 — Algorithm Coverage Controls (Priority: P3)

**Goal**: Vamp and madmom toggles on the upload page pass through to the analysis thread, controlling which algorithm families run.

**Independent Test**: Uncheck both Vamp and madmom on the upload page, upload an MP3, complete analysis. Open the resulting `_analysis.json` — confirm zero tracks with `library == "vamp"` or `library == "madmom"`.

### Implementation for User Story 3

- [x] T014 [US3] Verify `POST /upload` handler in `src/review/server.py` correctly reads `request.form.get('vamp', 'true') == 'true'` and `request.form.get('madmom', 'true') == 'true'`, stores results as `job.include_vamp` and `job.include_madmom`, and passes them to `default_algorithms(include_vamp=..., include_madmom=...)` in `_run_analysis()`; add `tests/unit/test_review_upload.py` test: POST with `vamp=false` and `madmom=false`, check returned `total` matches librosa-only algorithm count
- [x] T015 [US3] Update `src/review/static/upload.js` to include Vamp and madmom checkbox values in the `FormData` sent to `POST /upload`: `formData.append('vamp', chkVamp.checked ? 'true' : 'false')` and same for madmom; update `#status-line` during analysis to show which algorithm families are active (e.g. "Running librosa only…" if both disabled)

**Checkpoint**: Disabling Vamp + madmom produces a librosa-only result JSON significantly faster than a full-coverage run

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, edge cases, and UX refinements

- [x] T016 [P] Handle non-MP3 upload error in `src/review/static/upload.js`: display inline error message below drop zone when a non-`.mp3` file is dropped or selected; clear error when a valid file is selected
- [x] T017 [P] Handle zero-track analysis failure in `src/review/server.py` `_run_analysis()`: if `result.timing_tracks` is empty, set `job.status = "error"` and `job.error_message = "All algorithms failed — no tracks produced"` before returning; the SSE stream will send the terminal error event
- [x] T018 Handle analysis write error in `src/review/server.py` `_run_analysis()`: wrap `export.write()` in try/except OSError; on failure set `job.status = "error"` and `job.error_message = f"Failed to write result: {exc}"`
- [x] T019 [P] Run full test suite to confirm no regressions: `pytest tests/unit/test_review_server.py tests/unit/test_review_upload.py -v`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — blocks all user stories
- **US1 (Phase 3)**: Depends on Foundational — core upload + analysis thread + UI
- **US2 (Phase 4)**: Depends on US1 (SSE route reads `_current_job` set by US1's `/upload`)
- **US3 (Phase 5)**: Depends on US1 (toggle values flow through the upload handler built in US1)
- **Polish (Phase 6)**: Depends on all user story phases

### User Story Dependencies

- **US1 (P1)**: Core — must complete before US2 or US3
- **US2 (P2)**: SSE + reconnection; depends on `_current_job` and `AnalysisJob.events` from US1
- **US3 (P3)**: Toggle wiring; depends on `POST /upload` and `_run_analysis()` from US1

### Within Each User Story

- Server-side tasks `[P]` and test tasks `[P]` can be written in the same LLM turn
- `upload.js` tasks are sequential (single file)
- `server.py` tasks within a phase can be written together (no intra-phase file conflicts)

### Parallel Opportunities

- T005, T006 (server-side US1) can be written together
- T007 (HTML) can be written in parallel with T005/T006
- T009 (US1 tests) can be written in parallel with T007/T008
- T010, T011 (US2 server routes) can be written together
- T013 (US2 tests) can be written in parallel with T010/T011

---

## Parallel Example: User Story 1

```text
Parallel group A (server-side):
  T005  POST /upload route in server.py
  T006  _run_analysis() function in server.py
  T009  Upload endpoint tests in test_review_upload.py

Sequential (client-side, shared upload.js):
  T007  upload.html shell
  T008  upload.js drag-drop + fetch + EventSource
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T004)
3. Complete Phase 3: User Story 1 (T005–T009)
4. **STOP and VALIDATE**: Upload a real MP3 in the browser, confirm analysis runs and browser navigates to timeline. Run `pytest tests/unit/test_review_upload.py`.
5. Ready for US2 (progress streaming)

### Incremental Delivery

1. Setup + Foundational → `xlight-analyze review` (no args) opens blank upload page
2. US1 → upload, analyze, auto-navigate (full flow works end-to-end)
3. US2 → add live progress stream + reconnection
4. US3 → add Vamp/madmom toggles
5. Polish → error cases hardened

---

## Notes

- `[P]` tasks touch different files or are independent concerns — safe to implement in one LLM turn
- `_current_job` is a module-level variable in `server.py`; the Flask test client can inspect it directly
- `stream_with_context` is required for SSE in Flask so the app context is available inside the generator
- `daemon=True` on the analysis thread ensures it does not block server shutdown on Ctrl-C
- The existing `test_review_server.py` tests must still pass after modifying `create_app()` — they call `create_app(analysis_file, audio_file)` which must still work
- `werkzeug.utils.secure_filename` should be used when saving the uploaded file to prevent path traversal
