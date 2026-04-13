# Implementation Plan: In-Browser MP3 Upload and Analysis

**Branch**: `007-upload-and-analyze` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/007-upload-and-analyze/spec.md`
**Constitution**: v1.0.0

## Summary

Extend the existing `xlight-analyze review` command so it works without a pre-existing analysis JSON. When run with no arguments, Flask starts in **upload mode**: the browser shows an upload page where the user can drag-and-drop an MP3, toggle Vamp/madmom coverage, and click Analyze. The server runs the analysis pipeline in a background thread and streams per-algorithm progress to the browser via Server-Sent Events. When analysis completes the browser auto-navigates to the existing timeline review UI. The `review <analysis_json>` form is unchanged.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Flask 3+ (existing), click 8+ (existing), threading (stdlib), existing AnalysisRunner
**New capabilities**: `threading.Thread` + shared `AnalysisJob` state, SSE via Flask streaming response, multipart/form-data file upload
**Frontend**: Vanilla JS + SSE `EventSource` API — no new dependencies
**Storage**: JSON files on local filesystem (unchanged)
**Testing**: pytest + Flask test client (existing pattern)
**Target Platform**: macOS (primary); Linux compatible
**Project Type**: Extension of existing CLI tool + local web app
**Performance Goals**: Progress event delivered to browser within 5 seconds of each algorithm completing
**Constraints**: Single analysis job at a time; fully offline; port 5173 (unchanged)
**Scale/Scope**: One upload per session; same analysis scale as existing feature (up to 22 algorithms)

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | PASS | Upload triggers the existing audio analysis pipeline unchanged; no timing data invented or altered |
| II. xLights Compatibility | PASS | Output format identical to `xlight-analyze analyze` — same AnalysisResult JSON schema |
| III. Modular Pipeline | PASS | Upload/progress routes isolated in server.py; AnalysisRunner called via its existing interface unchanged |
| IV. Test-First | PARTIAL | Flask upload and SSE endpoints testable via test client. SSE streaming in a real browser cannot be unit-tested; manual test criteria defined in spec. Same accepted pattern as 002. |
| V. Simplicity First | PASS | threading.Thread + list polling for SSE; no Celery, no Redis, no async rewrite. Vanilla JS EventSource. Single new HTML file. |

All gates pass. No complexity justification required.

## Project Structure

### Documentation (this feature)

```text
specs/007-upload-and-analyze/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── checklists/
│   └── requirements.md
└── contracts/
    └── upload.md
```

### Source Code changes

```text
src/
├── cli.py                    # Modify: make analysis_json optional; add upload-mode branch
└── review/
    ├── server.py             # Modify: extend create_app() for upload mode; add /upload, /progress, /job-status routes
    └── static/
        ├── upload.html       # New: upload form + progress view (JS-toggled)
        └── upload.js         # New: drag-drop, fetch POST /upload, EventSource /progress, auto-navigate

tests/
└── unit/
    └── test_review_upload.py  # New: upload endpoint + job-status + SSE contract tests
```

No new directories. No changes to AnalysisRunner, TimingTrack, AnalysisResult, export.py, or existing static files.

## Technology Decisions (from research.md)

| Area | Choice | Why |
|------|--------|-----|
| Progress streaming | SSE (text/event-stream) | One-directional push; Flask native; no extra deps |
| Background thread | threading.Thread | Simple; analysis is I/O-bound |
| SSE delivery | Generator polls AnalysisJob.events list | Supports reconnecting clients; simpler than queue |
| File upload storage | Save to os.getcwd() | Mirrors xlight-analyze analyze behaviour |
| Page structure | Single upload.html, two JS views | No page reload needed during transition |
| App factory mode | create_app(analysis_path=None, audio_path=None) | None = upload mode; backwards-compatible |
| Concurrency guard | Module-level job ref; 409 if busy | Simplest correct solution for FR-014 |

## Key Implementation Notes

1. **`create_app()` signature**: Change to `create_app(analysis_path=None, audio_path=None)`. When both are `None`, register upload routes and serve `upload.html` at `/`. When both provided, existing timeline behaviour unchanged.

2. **`AnalysisJob` class**: Added to `server.py`. Holds `mp3_path`, `include_vamp`, `include_madmom`, `status` (`"running"/"done"/"error"`), `events: list[dict]`, `total: int`, `result_path`, `error_message`, `lock: threading.Lock`. Method `record_progress(idx, total, name, mark_count)` appends event dict under lock.

3. **Analysis thread**: Calls `AnalysisRunner(algo_list).run(mp3_path, progress_callback=job.record_progress)`, writes result via `export.write()`, sets `job.result_path` and `job.status = "done"`. On exception or zero tracks: `job.status = "error"`.

4. **SSE generator**: `Response(generate(), mimetype='text/event-stream')` with `Cache-Control: no-cache`. The `generate()` function iterates `job.events` from index 0, sleeping 0.2s when caught up. Sends terminal `done` or `error` event after all events emitted and job no longer running.

5. **`review` CLI command**: Change `analysis_json` argument to `required=False, default=None`. When `None`, call `create_app()` (no args) and start Flask — skip audio/JSON validation entirely.

6. **MP3 validation**: Check `filename.lower().endswith('.mp3')` in `POST /upload`. Extension check is primary (browser MIME type is unreliable). Return 400 on failure without saving.

7. **Output path**: `os.path.join(os.getcwd(), Path(filename).stem + "_analysis.json")`. Overwrite silently if exists.

8. **Reconnection**: On `upload.html` load, fetch `GET /job-status`. If `running` → show progress and reconnect EventSource. If `done` → redirect to `/` immediately. If `idle` → show upload form.
