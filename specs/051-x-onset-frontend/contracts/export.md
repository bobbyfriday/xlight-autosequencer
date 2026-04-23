# Contract: Export

Emit the final light show file. Traceable to FR-034 through FR-037, FR-035a.

## POST `/api/v1/songs/<song_id>/export`

Start an export render. Asynchronous — returns immediately with an `export_id` the client polls or streams via SSE.

**Request**
```json
{ "format": "xsq", "destination_name": "baby-shark-2026.xsq" }
```

`format` is one of `"xsq" | "fseq" | "xlights_project"` (FR-034). `destination_name` is a suggested filename; the frontend prompts the user for the save location, but v0 always writes to a standard output dir and exposes the full path in the response.

**Response 202**
```json
{ "export_id": "exp_L9v2k", "started_at": "2026-04-21T18:22:10Z" }
```

**Errors**
- `404 song_not_found`
- `409 incomplete_theming` — some section lacks a theme or is not user-confirmed (FR-035, FR-029a).
  ```json
  {
    "error": {
      "code": "incomplete_theming",
      "message": "3 sections still need a theme.",
      "details": { "missing_sections": [1, 4, 5] }
    }
  }
  ```
- `409 layout_required` — no xLights layout has been imported (FR-036b).
- `409 source_file_missing` — export requires audio (FR-035a).

## GET `/api/v1/songs/<song_id>/export/status`

**Server-Sent Events** stream of export progress. Same pattern as analysis progress — events are one-way server→client.

**Response**: `text/event-stream`

```
data: {"stage":"building_plan","progress":0.1}

data: {"stage":"placing_effects","progress":0.4}

data: {"stage":"writing_xml","progress":0.9}

data: {"stage":"done","output_path":"/Users/bob/xlight/exports/baby-shark-2026.xsq","bytes":472381}
```

## GET `/api/v1/songs/<song_id>/export/mapping`

Return the per-prop mapping that the frontend renders in the EXPORT screen's mapping table (FR-036). Derived from Song + Assignments + Layout.

**Response 200**
```json
{
  "props": [
    {
      "name": "Arch 1",
      "display_type": "SingleLine",
      "pixel_count": 50,
      "pixel_range": [0, 49],
      "theme_colors_by_section": [
        { "section_index": 0, "theme_id": "shimmer-wash", "colors": ["#4ade80", "#7eebd1"] }
      ]
    }
  ]
}
```

**Errors**
- `409 layout_required` (FR-036b)
- `409 incomplete_theming`

## GET `/api/v1/songs/<song_id>/export/preview`

Return the data needed to animate the EXPORT screen's scrubbable render preview (FR-037). This is an in-memory simulation, not a real xLights render (per scope exclusion "Rendering real xLights output video inside the app").

**Response 200**
```json
{
  "duration_ms": 145000,
  "frames_per_second": 20,
  "frames": [
    { "t_ms": 0, "props": [ { "name": "Arch 1", "pixels": ["#000", "#000", ...] } ] }
  ]
}
```

Frame rate is reduced from xLights's native 50fps to 20fps for preview (lower bandwidth). This is a "visual approximation" per the scope-exclusion note.
