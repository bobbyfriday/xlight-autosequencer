# Quickstart: x-onset Frontend Redo

End-to-end walkthrough for a developer (install → dev loop → first-run user flow) and for a hobbyist user (install → first light show).

---

## For developers

### 1. Prerequisites

- Python 3.11+
- Node 20+ (dev-time only; end-users do not need Node)
- ffmpeg (for MP3 decode, existing requirement)
- An xLights install (or just an `xlights_rgbeffects.xml` from one) for end-to-end export testing

### 2. Install

```bash
# from repo root
pip install -e .
cd src/review/frontend
npm install
```

### 3. Dev loop — two processes

Terminal 1 — Flask on `:5000`:
```bash
# from repo root
xlight review --dev
# or equivalently:
FLASK_APP=src.review.server flask run --port 5000
```

Terminal 2 — Vite on `:5173` (HMR, proxies `/api/*` and `/audio/*` to Flask):
```bash
cd src/review/frontend
npm run dev
```

Open `http://localhost:5173`.

### 4. Building for release

```bash
cd src/review/frontend
npm run build      # outputs to src/review/frontend/dist/
```

Commit the resulting `dist/` changes to git. End-users running `pip install -e .` or an installed wheel get the pre-built SPA; Flask serves it from `dist/index.html` at `/`.

### 5. Running tests

```bash
# Backend API tests
pytest tests/review/ -v

# Frontend unit + component tests
cd src/review/frontend
npm test

# End-to-end happy-path (requires both dev servers running)
cd src/review/frontend
npm run e2e
```

---

## For hobbyist users

### 1. Install

```bash
pip install xlight-autosequencer
```

Requires Python 3.11+ and ffmpeg on the PATH. No Node required — the UI ships pre-built.

### 2. Start

```bash
xlight review
```

A browser tab opens to `http://localhost:5000`. If the browser doesn't open automatically, navigate there manually.

### 3. First-run flow

On the first-ever launch the LIBRARY screen shows a centered drop target:

> **Drop an MP3 to start**
> or click to browse

(Per FR-005c — no setup wizard; layout configuration is deferred.)

### 4. Import your first song

Drop an MP3 onto the drop target (or use DROP tab for keyboard-only flow: press `2`). The app:

1. Hashes the audio bytes (`song_id`).
2. Dedupes against the library.
3. Creates a library entry with status `"draft"`.
4. Auto-advances to the ANALYZE screen.

### 5. Watch analysis run

The ANALYZE screen shows:
- Overall progress percentage + ETA.
- Per-detector status (beats, onsets, impacts, drops, chords, ...) with a confidence score.
- A live log pane.

When every detector completes, a `review timeline →` button becomes active (or press `4`).

### 6. Review the timeline

The TIMELINE screen shows:
- A transport bar with play/pause, skip, and jump-section buttons.
- A waveform with the detected sections tinted underneath.
- An editable section strip — chips colored by the auto-assigned default theme (FR-012a).
- Raw detector tracks below (toggle-able).

Press `space` to play. Scrub by clicking the ruler or the waveform. Click a section chip to jump there.

If you want to edit sections: click the section-strip's edit toggle (or press the appropriate tool-strip button). Now `S` splits at the playhead, `M` merges with the follower, `Del` deletes, `R` renames. Click "reset to detected" to undo all edits.

### 7. Assign themes

Navigate to THEME (press `5`). Each section has its analyzer-suggested default theme already assigned — you'll see a meaningful first-pass light show in the live preview.

The theme grid shows all built-in themes. Click a theme card to assign it to the currently-selected section (click a section chip at the top to select). Adjust per-section parameter sliders in the right inspector (brightness, hit strength, dwell time, color shift) — tweaks are immediate and reflected in the live preview.

**Status flip to `themed`**: either click "accept all defaults" (bulk-confirms every section's assignment) or walk each section and assign individually. The song's library status flips from `"analyzed"` to `"themed"` only after explicit confirmation (FR-029a).

### 8. First-time export — layout import

Navigate to EXPORT (press `6`). On first-ever visit to this screen the app blocks with:

> **Import your xLights layout to continue**
> [Click to pick `xlights_rgbeffects.xml`]

Point to your xLights setup's `xlights_rgbeffects.xml` (typically under `Documents/xLights/`). The app parses it, extracts every model + pixel range, and the export screen becomes fully available.

### 9. Export

On the EXPORT screen:
- Pick a format: `.xsq`, `.fseq`, or xLights project.
- Review the per-prop mapping table (prop name, LED count, pixel range, theme-driven colors).
- Click `render ⌘R` (primary button).

Progress streams live. When done the output file's path is shown and a "reveal in finder" action appears.

### 10. Next session

Close the app. Re-open — the LIBRARY shows every imported song with its status chip. Click a song:
- If `draft`, goes to ANALYZE.
- If `analyzed`, goes to TIMELINE.
- If `themed`, goes to THEME (the screen where the user spends the most time — they usually want to tweak rather than re-review the timeline).

The last-active song, screen, and playhead position are restored (SC-004).

---

## Simulated regression (for maintainers)

Useful for sanity-checking the CI path:

1. Theme and export a reference song. Note the output file size and bytes 0–256.
2. Tweak one theme's parameters in a built-in theme file.
3. Re-run the export on the same song (do NOT re-theme).
4. The new export bytes should differ — if they don't, the generator isn't picking up the theme change.

This is not a formal test (we don't commit binary xsq fixtures for this), but it's the fastest sniff-test when you touch the generator side.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Browser opens to a blank page, dev tools show 404 on `/assets/*` | Running against `pip install -e .` but `src/review/frontend/dist/` is empty. | Run `npm run build` in `src/review/frontend/`. |
| `/audio/<song_id>` returns 404 | Source MP3 was moved or deleted after import. | Use the "locate file" action on the LIBRARY entry (FR-001a). |
| Analysis screen never advances from "queued" | Another song is analyzing (single-concurrency). | Wait, or cancel the other run. |
| Export is blocked with `layout_required` | No xLights layout imported yet. | Import your `xlights_rgbeffects.xml` via EXPORT → layout prompt or TWEAKS → settings. |
| After restart, a song shows "source file missing" | Audio path is unreachable. | Click the song's "locate file" action and point it to the current path. Existing analysis and themes preserved (FR-001a). |
| Dark/light toggle doesn't persist | `/api/v1/preferences` PUT is failing. | Check the browser network tab; ensure Flask is reachable. |
