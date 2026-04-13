# Upload Contract: In-Browser MP3 Upload and Analysis

**Feature**: 007-upload-and-analyze
**Date**: 2026-03-22

This document defines the new Flask HTTP endpoints added in upload mode, the SSE event format, and the upload page interaction contract.

---

## New HTTP Endpoints (upload mode only)

These routes are registered only when `create_app()` is called with no `analysis_path` (upload mode). They are NOT present in review mode.

### `GET /`
Returns the upload page (`upload.html`).

**Response**: `200 text/html`

---

### `POST /upload`
Accepts an MP3 file and algorithm toggles, saves the file, and starts background analysis.

**Request**: `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mp3` | file | Yes | The MP3 file to analyze |
| `vamp` | string `"true"/"false"` | No | Include Vamp algorithms (default: `"true"`) |
| `madmom` | string `"true"/"false"` | No | Include madmom algorithms (default: `"true"`) |

**Responses**:

| Status | Condition | Body |
|--------|-----------|------|
| `202` | Job started | `{"status": "started", "filename": "song.mp3", "total": 18}` |
| `400` | No file, wrong type, or empty filename | `{"error": "..."}` |
| `409` | Analysis already in progress | `{"error": "Analysis already running. Please wait."}` |
| `500` | Failed to save file or start thread | `{"error": "..."}` |

---

### `GET /progress`
Server-Sent Events stream of analysis progress. The client connects and receives one event per algorithm completion, followed by a terminal event.

**Response**: `200 text/event-stream`

**Event format**:
```
data: <json>\n\n
```

**Progress event** (one per algorithm):
```json
{"idx": 3, "total": 18, "name": "librosa_beats", "mark_count": 142, "ok": true}
```

**Error event** (for an individual algorithm failure — analysis continues):
```json
{"idx": 5, "total": 18, "name": "qm_onsets_complex", "mark_count": 0, "ok": false}
```

**Terminal — success** (sent once at the end):
```json
{"done": true, "result_path": "/abs/path/to/song_analysis.json"}
```

**Terminal — failure** (zero tracks or write error):
```json
{"error": "All algorithms failed — no tracks produced"}
```

**Behaviour**:
- The stream stays open until a terminal event is sent.
- If the client connects after analysis has already completed, all buffered events are replayed from the beginning (the `events` list is iterated from index 0).
- The generator polls `AnalysisJob.events` every 0.2 seconds while waiting for new events.

---

### `GET /job-status`
Returns the current job state as JSON. Used by the client for reconnection after tab reload.

**Response**: `200 application/json`

```json
{
  "status": "running",
  "events_count": 7,
  "total": 18,
  "result_path": null,
  "error": null
}
```

When `status == "done"`:
```json
{
  "status": "done",
  "events_count": 18,
  "total": 18,
  "result_path": "/abs/path/to/song_analysis.json",
  "error": null
}
```

When no job exists:
```json
{"status": "idle"}
```

---

## Upload Page Interaction Contract

### Upload Form View

Shown on first load (when no job is running or complete).

| Element | Behaviour |
|---------|-----------|
| Drop zone | Accepts `.mp3` drag-and-drop; highlights on `dragover`; rejects non-MP3 with inline message |
| File picker button | Opens system file picker filtered to `.mp3` |
| Selected file display | Shows filename once selected |
| Vamp toggle (checkbox) | Checked by default. Label: "Vamp plugins (~14 tracks)" |
| madmom toggle (checkbox) | Checked by default. Label: "madmom (~2 tracks)" |
| Analyze button | Disabled until an MP3 is selected; submits `POST /upload` via `fetch` |

### Progress View

Shown after `POST /upload` returns `202`. The form is hidden; the progress list is shown.

| Element | Behaviour |
|---------|-----------|
| Progress bar | `completed / total * 100%` width, updated on each SSE event |
| Algorithm list | Appends one row per SSE event: `[✓/✗] algorithm_name (N marks)` |
| Status message | Shows "Analyzing… (N / total)" while running; "Done!" on terminal success |
| Auto-navigation | On terminal `done` event: `window.location.href = '/'` after 500ms delay |
| Error display | On terminal `error` event: shows error message; offers "Try again" button to reload |

### Reconnection Behaviour

On page load, the client calls `GET /job-status`:
- `"running"`: skip upload form, show progress view, reconnect to `GET /progress`
- `"done"`: navigate directly to `'/'`
- `"idle"`: show upload form normally

---

## Modified CLI Contract

The `review` command's `analysis_json` argument becomes optional:

```
xlight-analyze review [analysis_json]
```

| Invocation | Behaviour |
|-----------|-----------|
| `xlight-analyze review song.json` | Existing behaviour — validate file, open timeline at `/` |
| `xlight-analyze review` | New — start server in upload mode, open browser at `/` (upload page) |

Exit codes remain the same for the existing invocation. The no-argument invocation exits `0` on clean shutdown (Ctrl-C) or `5` if port 5173 is busy.
