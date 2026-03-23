# Research: In-Browser MP3 Upload and Analysis

**Feature**: 007-upload-and-analyze
**Date**: 2026-03-22
**Status**: Complete

---

## Decision 1: Progress Streaming — SSE vs WebSockets

**Decision**: Server-Sent Events (SSE) via Flask `Response` with `stream_with_context`
**Rationale**: SSE is a one-directional server-push mechanism — exactly what progress reporting needs. Flask supports it natively: a generator function yields `data: ...\n\n` strings and Flask wraps it in a streaming response. No extra dependencies, no handshake protocol, automatic browser reconnection built-in. WebSockets require `flask-socketio` or `websockets`, add async complexity, and are bidirectional — overkill for one-way progress events.
**Alternatives considered**:
- WebSockets: Bidirectional, requires `flask-socketio`. Unnecessary complexity for a one-way push channel.
- Client polling (`GET /job-status` every second): Works but adds latency and unnecessary requests. SSE is lower-overhead and simpler on the client side.

---

## Decision 2: Background Analysis Thread Coordination

**Decision**: `threading.Thread` + a module-level `AnalysisJob` state object protected by a `threading.Lock`
**Rationale**: The analysis pipeline is CPU/IO-bound and takes 1–3 minutes. It must run in a background thread so Flask can still serve the SSE stream and status endpoint during analysis. A shared mutable state object (holding progress events, status, and result path) is the simplest coordination mechanism for a single-user local tool. The lock prevents race conditions between the writer thread (analysis runner) and reader threads (SSE subscribers). No queue, no Redis, no Celery — YAGNI.
**Alternatives considered**:
- `multiprocessing.Process`: Heavier; IPC adds complexity. Unnecessary since GIL is not a bottleneck for I/O-bound Vamp/librosa calls.
- `asyncio` + `async def`: Would require rewriting the entire Flask app as async (Quart or FastAPI). Massive scope increase for no benefit.

---

## Decision 3: SSE Delivery — Generator vs Queue

**Decision**: The analysis thread appends `ProgressEvent` dicts to a list on the `AnalysisJob`. The SSE generator iterates over a growing index into this list, sleeping briefly between polls.
**Rationale**: This is the simplest SSE pattern for Flask. The generator does not need to be a thread — it runs in Flask's request thread and polls the shared list. A `queue.Queue` would also work but requires the SSE generator to block on `queue.get(timeout=...)`, which is slightly more complex. The list-with-index pattern is easier to reason about and supports reconnecting clients (they can skip to the current index).
**Alternative considered**:
- `queue.Queue` per subscriber: Correct for multi-subscriber scenarios. Unnecessary here since only one browser tab is expected. List polling is simpler.

---

## Decision 4: File Upload Handling

**Decision**: `flask.request.files['mp3']` → save directly to `os.getcwd()/<original_filename>`. Analysis then runs on that saved path, producing `<stem>_analysis.json` in the same directory.
**Rationale**: The spec requires the analysis result to be saved alongside the MP3 (FR-011). Saving to the working directory mirrors the behavior of `xlight-analyze analyze` run from that directory. No temp directory needed — the file is the permanent input, not a throwaway.
**MP3 validation**: Check `filename.endswith('.mp3')` and `file.content_type == 'audio/mpeg'` before saving. If invalid, return 400 immediately without saving anything.
**Alternatives considered**:
- Temp directory + move on success: More robust for concurrent multi-user scenarios, but adds complexity and is unnecessary for a single-user local tool.
- Stream directly to analysis without saving: Would require a complete rewrite of the audio loader. Not worth it.

---

## Decision 5: Single vs Multi-Page Upload Flow

**Decision**: One new page (`upload.html`) with two JS-managed views: an upload form view and a progress view. When analysis completes, `window.location.href = '/'` navigates to the existing timeline.
**Rationale**: No page reload needed between upload and progress — JS hides the form and shows the progress list in-place. This avoids a flash of a blank page and keeps state (selected file, toggles) visible during transition. The final navigation to `'/'` reloads the full timeline app cleanly.
**Alternatives considered**:
- Separate `/progress` HTML page with redirect after upload: Adds a page load; requires passing state (job ID) via URL or session. More complex for no UX benefit.
- Integrate upload into the existing `index.html`: The timeline and upload flows have nothing in common. Keeping them in separate HTML files keeps both simpler.

---

## Decision 6: App Factory Mode — Upload vs Review

**Decision**: Extend `create_app()` signature to `create_app(analysis_path=None, audio_path=None)`. When both are `None`, the app starts in **upload mode** (serves `upload.html` at `/`, registers upload/progress routes). When both are provided, it starts in **review mode** (existing behavior, timeline at `/`).
**Rationale**: A single factory with a mode flag is cleaner than two separate factory functions. The shared infrastructure (Flask instance, static file serving) stays DRY.
**New routes (upload mode only)**:
- `POST /upload` — receives MP3 + toggles, saves file, starts analysis thread
- `GET /progress` — SSE stream of `ProgressEvent` dicts
- `GET /job-status` — returns current `AnalysisJob` state as JSON (for reconnecting clients)

---

## Decision 7: Concurrency Guard

**Decision**: A module-level `_current_job: AnalysisJob | None` variable. `POST /upload` checks if `_current_job` is running; if so, returns `409 Conflict`. Reset to `None` when analysis completes or fails.
**Rationale**: FR-014 requires exactly this. A simple None-check with a lock is sufficient. No queue, no retry — just a clear error telling the user to wait.

---

## Summary Table

| Area | Decision |
|------|----------|
| Progress streaming | SSE via Flask streaming response |
| Background thread | `threading.Thread` + shared `AnalysisJob` state with `Lock` |
| SSE delivery | Generator polls growing list on `AnalysisJob` |
| File upload storage | Save to `os.getcwd()/<filename>.mp3` |
| Page structure | Single `upload.html`, two JS views, navigate to `/` on complete |
| App factory | Extend `create_app()` with optional args; `None` = upload mode |
| Concurrency guard | Module-level job reference; 409 if busy |
