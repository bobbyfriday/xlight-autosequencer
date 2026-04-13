# Implementation Plan: Timing Track Review UI

**Branch**: `002-track-review-ui` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-track-review-ui/spec.md`
**Constitution**: v1.0.0

## Summary

Add a local web-based review UI to the `xlight-analyze` CLI. Given an `_analysis.json` file
produced by `xlight-analyze analyze`, the user runs `xlight-analyze review song_analysis.json`
which starts a Flask server on `localhost:5173` and opens a browser. The UI shows all timing
tracks as horizontal canvas lanes with marks positioned proportionally to song duration, plays
the MP3 in sync with a moving playhead, supports Next/Prev/Solo keyboard navigation to focus
individual tracks, and exports a filtered analysis JSON containing only the selected tracks.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Flask 3+ (local web server), click 8+ (CLI integration)
**Frontend**: Vanilla JS + Web Audio API + Canvas 2D — no build step, no npm
**Storage**: JSON files on local filesystem (same `AnalysisResult` schema as existing pipeline)
**Testing**: pytest (server endpoint tests via Flask test client); manual browser testing for canvas/audio
**Target Platform**: macOS (primary); Linux compatible
**Project Type**: CLI tool extension + local single-page web app
**Performance Goals**: 20 tracks rendered on page load within 3 seconds; playhead sync within 100ms
**Constraints**: Fully offline; no network calls; single song per session; port 5173 (fixed)
**Scale/Scope**: One analysis JSON + one MP3 per session; up to ~20 tracks, ~300 marks per track

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | PASS | UI reads analysis JSON produced by the audio pipeline; does not alter or re-run analysis |
| II. xLights Compatibility | PASS | Exported selection JSON uses the same `AnalysisResult` schema; downstream steps unchanged |
| III. Modular Pipeline | PASS | Review UI is an independent pipeline stage: reads analysis JSON, produces filtered JSON. Flask server is isolated in `src/review/`; no coupling to analyzer internals |
| IV. Test-First | PARTIAL | Flask endpoints are tested with pytest + Flask test client. Canvas rendering and Web Audio playback are browser-only and cannot be unit-tested; this is acceptable and noted |
| V. Simplicity First | PASS | Vanilla JS with no React, no npm, no build step. Flask with no async, no auth, no database. Fixed port, single page, single session |

**IV note**: Canvas/audio cannot be pytest-tested. Each user story has an independent manual test defined in the spec. This is the accepted verification path for browser-rendered behaviour.

All gates pass. No complexity justification required.

## Project Structure

### Documentation (this feature)

```text
specs/002-track-review-ui/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── checklists/
│   └── requirements.md
└── contracts/
    └── ui.md
```

### Source Code (repository root)

```text
src/
├── analyzer/            # existing — unchanged
├── cli.py               # existing — add `review` subcommand
├── export.py            # existing — unchanged
└── review/
    ├── __init__.py      # package marker
    ├── server.py        # Flask app: routes /, /analysis, /audio, /export
    └── static/
        ├── index.html   # single-page UI shell
        ├── app.js       # timeline canvas, audio playback, keyboard nav, export
        └── style.css    # layout and lane styling

tests/
└── unit/
    └── test_review_server.py   # Flask test client: endpoint contract tests
```

**Structure Decision**: Single project layout extending the existing `src/` tree. The review module is self-contained under `src/review/`. No separate frontend project or build step.

## Technology Decisions (from research.md)

| Area | Choice | Why |
|------|--------|-----|
| Server | Flask 3+ | Minimal, synchronous, sufficient for local single-user tool |
| Timeline | Canvas 2D | Handles 20 tracks x 300+ marks without DOM explosion |
| Audio | `<audio>` element + rAF | Simplest; `currentTime` sub-ms precision; browser handles MP3 + Range seeks |
| Frontend | Vanilla JS | No build step; single screen; ~500 LOC |
| Export | POST to Flask writes file | File must land alongside source analysis JSON (FR-011) |
| Port | localhost:5173 | Avoids macOS AirPlay (5000), common dev ports (8000/8080) |

## Key Implementation Notes

1. **MP3 serving**: Flask `/audio` endpoint returns the file via `send_file()` with `Accept-Ranges: bytes`. `<audio src="/audio">` in the HTML; the browser issues Range requests automatically for seeking. No client-side decoding needed.

2. **Playhead sync**: `requestAnimationFrame` loop reads `audio.currentTime` (sub-ms `double`) each frame and converts to canvas x-position: `x = (audio.currentTime / audio.duration) * canvasWidth`. Redraws the playhead line on every frame.

3. **Canvas rendering**: Two stacked canvases (CSS `position: absolute`):
   - **Background canvas**: draws time axis + all track lanes (marks). Redrawn only on load, resize, or selection change.
   - **Foreground canvas**: redrawn on focus change and each rAF tick. Draws a semi-transparent overlay over non-focused lanes, then the playhead. Keeps focus transitions instant without redrawing all marks.

4. **Track lane layout**: Fixed 80px height per lane. Left panel (200px) contains metadata + controls. Right canvas area renders marks. Both scroll together vertically via a flex layout.

5. **Focus vs Selection independence**: `focusIndex` (int | null) and `track.selected` (bool) are independent state. Changing focus never changes selection checkboxes.

6. **Export path**: Flask server holds the `analysis_path`. On POST `/export`, the server computes the output path by replacing `_analysis.json` with `_selected.json` (or appending `_selected` if not matching that pattern). Returns 409 if file exists without `overwrite: true`.

7. **Audio file resolution**: If `analysis_json.song_path` does not exist, the CLI exits with code 3 before starting Flask. No browser-side file picker needed.

8. **Browser launch**: Use `threading.Timer(0.5, webbrowser.open, args=['http://localhost:5173/'])` to open the browser half a second after Flask binds, ensuring the server is ready.
