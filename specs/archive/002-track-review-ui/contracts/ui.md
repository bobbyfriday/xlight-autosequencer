# UI Contract: Timing Track Review UI

**Feature**: 002-track-review-ui
**Date**: 2026-03-22

This document defines the Flask HTTP endpoints and the client-side interaction contract (keyboard shortcuts, component behaviour, canvas layout) that the implementation MUST conform to.

---

## HTTP Endpoints

### `GET /`
Returns the single-page review UI (`index.html`).

### `GET /analysis`
Returns the loaded analysis JSON as-is.

**Response**: `200 application/json` — the full `AnalysisResult` object.

### `GET /audio`
Returns the MP3 audio file.

**Response**: `200 audio/mpeg` — file bytes with Range request support.
**Note**: Must include `Accept-Ranges: bytes` header. The browser issues Range requests automatically when the user seeks; Flask `send_file()` handles `206 Partial Content` responses correctly.

### `POST /export`
Writes a filtered `AnalysisResult` JSON to disk.

**Request body** (`application/json`):
```json
{
  "selected_track_names": ["qm_beats", "librosa_drums"]
}
```

**Responses**:

| Status | Condition | Body |
|--------|-----------|------|
| `200` | File written successfully | `{"path": "/abs/path/to/song_selected.json"}` |
| `400` | `selected_track_names` is empty or missing | `{"error": "No tracks selected"}` |
| `409` | Output file already exists | `{"warning": "File exists", "path": "..."}` — client must confirm, then re-POST with `"overwrite": true` |
| `500` | Write error | `{"error": "..."}` |

**Overwrite confirmation request body**:
```json
{
  "selected_track_names": ["qm_beats"],
  "overwrite": true
}
```

---

## Canvas Timeline Layout

```
+----------------------------------------------------------+
| Track name   Score  [S]  [ ]  ||||  |  |||| ||| |||||   |
| Track name   Score  [S]  [X]  |  | ||  | ||  |  |  ||   |
| ...                                                       |
+----------------------------------------------------------+
^                              ^
Time axis (mm:ss)           Playhead (vertical red line)
```

- **Left column** (~200px): track name, quality score badge, element type tag, Solo button `[S]`, selection checkbox `[ ]`
- **Right area**: canvas lane — marks drawn as `1px` vertical lines spanning full lane height
- **Time axis**: drawn at top of canvas, ticks every 10 seconds labelled `mm:ss`
- **Playhead**: 1px wide red vertical line spanning full canvas height, positioned at `(position_ms / duration_ms) × canvas_width`

### Lane Heights and Colours

| State | Opacity | Border |
|-------|---------|--------|
| Normal (selected, no focus) | 100% | none |
| Deselected (checkbox off) | 40% | none |
| Focused | 100% | 2px solid `#4af` (blue) |
| Unfocused (when any focus active) | 25% | none |
| High-density (flagged) | marks drawn in `#e44` (red) | none |

---

## Keyboard Shortcuts

All shortcuts are active when the page has keyboard focus (the `document` handles `keydown`).

| Key | Action | Notes |
|-----|--------|-------|
| `Space` | Toggle play/pause | `preventDefault` to avoid button focus side-effects |
| `ArrowRight` or `n` | Focus next track | Wraps: last → first |
| `ArrowLeft` or `p` | Focus previous track | Wraps: first → last |
| `Escape` | Clear focus (all tracks equal) | Only if a track is currently focused |

---

## Component Behaviour Contract

### Play/Pause Button
- Label alternates between "Play" and "Pause" based on `is_playing` state
- Clicking while playing: pauses audio, freezes playhead
- Clicking while paused: resumes from current `position_ms`

### Timeline Seek (Click)
- Clicking anywhere on the canvas computes `click_x / canvas_width × duration_ms`
- Seeks audio to that position (stop + restart with offset)
- Updates playhead immediately (does not wait for audio to restart)

### Solo Button `[S]` on a Track Lane
- If the track is NOT currently focused: sets `focus_index` to this track's index
- If the track IS currently focused: clears focus (`focus_index = None`)
- Equivalent to Next/Prev cycling to that track

### Selection Checkbox
- Checked by default for all tracks on load
- Toggling does NOT affect `focus_index`
- Dimmed tracks (unchecked) still appear in the timeline at reduced opacity

### Export Selection Button
- Disabled (greyed out) when zero tracks are selected
- Clicking sends `POST /export` with all currently checked track names
- On `409` (file exists): shows inline warning and confirmation dialog; re-sends with `"overwrite": true` on confirm
- On `200`: shows success message with the output path
- On `400` or `500`: shows inline error message

### Audio Playhead Animation
- Uses `requestAnimationFrame` while `is_playing == true`
- Reads `audio.currentTime` each frame (sub-ms precision `double`)
- Redraws the foreground canvas only: clear + optional focus overlay + playhead line
- Background canvas (track marks) is not redrawn per frame — only on load, resize, or selection change

### End of Track
- When `AudioBufferSourceNode` fires `onended`:
  - `is_playing` → `false`
  - Playhead remains at `duration_ms` (right edge)
  - Play button label resets to "Play"

---

## CLI Launch Contract

The review UI is launched via:

```
xlight-analyze review <analysis_json>
```

Behaviour:
1. Validates that `<analysis_json>` exists and is a valid `AnalysisResult` JSON
2. Resolves the audio path from `analysis_json.song_path`; if not found, prints a clear error and exits with code 3
3. Starts Flask on `localhost:5173`
4. Opens the default browser to `http://localhost:5173/`
5. Blocks until the user sends `Ctrl-C`; then shuts down cleanly

Exit codes:
| Code | Condition |
|------|-----------|
| `0` | Clean shutdown (Ctrl-C) |
| `3` | Audio file not found at path in JSON |
| `4` | Analysis JSON file not found or unreadable |
| `5` | Port 5173 already in use |
