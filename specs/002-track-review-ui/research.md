# Research: Timing Track Review UI

**Feature**: 002-track-review-ui
**Date**: 2026-03-22
**Status**: Complete — all decisions resolved

---

## Decision 1: Local Web Server Framework

**Decision**: Flask
**Rationale**: This is a single-user local tool that needs to serve static files, stream an MP3 with Range request support, and handle one POST endpoint for export. Flask's synchronous, minimal model is the right fit — no async, no schema validation, no auto-generated docs needed. FastAPI's overhead is unjustified here.
**Alternatives considered**:
- FastAPI: Async-first, OpenAPI docs, Pydantic validation — all valuable for APIs with multiple consumers, but over-engineered for a local single-user tool.
- aiohttp: Async HTTP server — same over-engineering concern, plus harder to serve static files simply.
- http.server (stdlib): No Range request support out of the box; fragile for production-style file serving.

---

## Decision 2: Timeline Rendering Technology

**Decision**: Canvas 2D API
**Rationale**: A song analysis can produce 20 tracks × hundreds of marks = thousands of DOM elements if SVG is used. Canvas batches all rendering into a single element and redraws on each animation frame, which keeps scrolling and playhead animation smooth regardless of mark density. The timeline is read-only (no per-mark interactivity), so the lack of individual DOM nodes per mark is not a drawback.
**Alternatives considered**:
- SVG: Each mark would be a `<line>` element; 20 tracks × 300 marks = 6,000 DOM nodes. Smooth 60fps playhead updates would be expensive.
- CSS + absolute-positioned divs: Similar DOM explosion; complex to manage layout.

---

## Decision 3: Audio Playback

**Decision**: HTML `<audio>` element + `audio.currentTime` polled via `requestAnimationFrame`
**Rationale**: The `<audio>` element's `currentTime` is a `double` with sub-millisecond resolution, updated by the browser's internal media clock. Polling it at 60fps via `requestAnimationFrame` gives one-frame precision (~16ms), which is imperceptible for a visual playhead. The browser handles MP3 decoding natively and issues HTTP Range requests automatically for seeking — Flask's `send_file()` handles those correctly. This is the simplest approach: no JS decoding, no buffer management.
**Alternatives considered**:
- `AudioContext.decodeAudioData`: Loads the entire file into memory as a decoded PCM buffer. More complex: seeking requires stopping and restarting an `AudioBufferSourceNode` with an offset. Overkill for a UI that just needs accurate playhead sync.
- Streaming from server on each seek: Adds latency; unnecessary for a local file.

**MP3 Loading**: Flask `/audio` endpoint returns the MP3 via `send_file()` with `Accept-Ranges: bytes`. The browser requests byte ranges automatically when seeking. `audio.src = '/audio'` is all the JS needs.

---

## Decision 4: Frontend Architecture

**Decision**: Vanilla JS, single HTML page, no framework
**Rationale**: The UI has one screen, one data source (the analysis JSON loaded at startup), and straightforward state: playback position, focus index, selection map. A framework like React or Vue would add build tooling and conceptual overhead for what is a ~500-line JS file.
**Alternatives considered**:
- React/Vue: Component model is valuable when UI state is complex or shared across many components. For a single-screen tool with a canvas timeline, it adds more ceremony than value.
- Preact/Alpine.js: Lighter than React/Vue but still a dependency and abstraction layer that is not needed.

---

## Decision 5: Export Mechanism

**Decision**: POST to Flask `/export` endpoint — server writes the file
**Rationale**: The export file must land on the local filesystem alongside the source analysis file (per FR-011: default path `<input_basename>_selected.json`). The Flask server already knows the source path, so writing server-side is the natural choice. A browser download blob would deposit the file in the user's Downloads folder, not alongside the source, which breaks the pipeline.
**Alternatives considered**:
- Browser `Blob` download: File lands in Downloads, not alongside the analysis JSON. Breaks FR-011.
- Electron/Tauri: Desktop wrapper would give native file dialogs, but is a massive dependency just for file path control.

---

## Decision 6: Track Focus vs. Selection — Visual Distinction

**Decision**: Two independent visual states rendered on the canvas per track lane:
- **Selected** (checkbox): Track lane has full opacity tick marks; checkbox is checked.
- **Deselected** (checkbox): Track lane marks are dimmed (30% opacity); lane has a "deselected" indicator.
- **Focused** (solo/Next/Prev): Track lane has a highlighted border + full-brightness marks; all other lanes are dimmed to 25% opacity. Focus state does not change checkbox state.

**Rationale**: FR-017 requires focused tracks to be prominent with others dimmed. FR-009 requires selection state (checkbox). The spec explicitly states focus is a viewing aid that does not affect export. Rendering both states on a canvas is straightforward by checking each track's `selected` and `focused` flags when drawing each lane.

---

## Decision 7: Keyboard Shortcut Assignments

| Action | Key | Rationale |
|--------|-----|-----------|
| Play/Pause | Space | Universal media player convention |
| Next track focus | ArrowRight or `n` | Arrow for discoverability; `n` for touch-typers |
| Prev track focus | ArrowLeft or `p` | Arrow for discoverability; `p` for touch-typers |
| Clear focus | Escape | Universal "cancel/dismiss" key |
| Click timeline | Mouse click | Seek to position |

Space must not trigger button click (use `preventDefault` on keydown for Space when focus is on buttons).

---

## Decision 8: Port and Launch UX

**Decision**: Flask binds to `localhost:5173` (fixed port). If the port is busy, fail with a clear error message suggesting the user kill the conflicting process.
**Rationale**: A fixed port makes the tool predictable. Auto-incrementing ports add complexity and make bookmarks/shortcuts unreliable. Port 5173 is chosen to avoid the common 5000 (Flask default, conflicts with macOS AirPlay Receiver on Ventura+) and 8000/8080 (often used by other dev tools).
**Alternatives considered**:
- Random available port: Unpredictable, harder to test.
- Port 5000: Conflicts with macOS AirPlay Receiver since macOS Ventura.

---

## Summary Table

| Area | Decision |
|------|----------|
| Server | Flask |
| Timeline | Canvas 2D |
| Audio | Web Audio API (full buffer, in-memory) |
| Frontend | Vanilla JS, single HTML page |
| Export | POST → Flask writes file server-side |
| Focus vs Selection | Two independent visual states on canvas |
| Keyboard shortcuts | Space/ArrowRight/ArrowLeft/Escape |
| Port | localhost:5173 |
