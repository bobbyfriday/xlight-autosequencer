# Contract: xLights Layout

One-time import of the user's xLights prop layout, reused for every song's export. Traceable to FR-036a, FR-036b, FR-036c.

## GET `/api/v1/layout`

Return the currently-imported layout, or null.

**Response 200**
```json
{
  "layout_id": "layout_b3f01a",
  "display_name": "Front Yard 2026",
  "imported_at": "2026-04-21T17:00:00Z",
  "props": [
    { "name": "Arch 1", "display_type": "SingleLine", "pixel_count": 50, "pixel_range": [0, 49] }
  ],
  "total_pixels": 2400
}
```

**Response 200** (no layout)
```json
{ "layout": null }
```

## POST `/api/v1/layout`

Import a new `xlights_rgbeffects.xml`. Replaces the prior layout entirely (FR-036c: only one layout active at a time).

**Request**: `multipart/form-data`

| Field | Type | Notes |
| --- | --- | --- |
| `layout_xml` | file | The `xlights_rgbeffects.xml` from the user's xLights install. Required. |
| `display_name` | string | Optional override for the layout display name. |

**Response 201**
```json
{
  "layout": { /* same shape as GET /layout */ },
  "replaced_prior": true,
  "warning": "Re-exporting any prior song against the new layout may produce different output."
}
```

`replaced_prior: true` ⇒ frontend shows the FR-036c warning about prior exports.

**Errors**
- `400 invalid_xml` — file is not valid XML.
- `400 not_xlights_rgbeffects` — XML does not match the expected xLights schema shape.
- `400 no_props_found` — XML parses but contains zero usable models/groups.
- `413 file_too_large` — arbitrary cap (default 20 MB).

## Notes

- The backend stores the parsed layout in `Preferences.layout_id` plus the full `Layout` entity inside `library.json` (per [data-model.md](../data-model.md)).
- No update-in-place: every import is a full replacement. This is the simplest model and avoids prop-identity-tracking across edits.
