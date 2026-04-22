# Contract: Sections

Covers section CRUD: get/put the current section list, split/merge/promote/reset. Traceable to FR-020 through FR-027.

## GET `/api/v1/songs/<song_id>/sections`

Return the user's current section list (the edited one, which is the analyzer's detected list for a fresh song and diverges from there).

**Response 200**
```json
{
  "sections": [
    { "index": 0, "start_ms": 0, "end_ms": 12500, "kind": "intro", "label": "Intro" },
    { "index": 1, "start_ms": 12500, "end_ms": 34000, "kind": "verse", "label": "Verse 1" }
  ],
  "ghost_boundaries": [
    { "at_ms": 19000, "confidence": 0.62 }
  ]
}
```

**Errors**
- `404 song_not_found`
- `409 not_analyzed` — no detected sections exist yet.

## POST `/api/v1/songs/<song_id>/sections/split`

Split a section at a playhead time. Per FR-021: rejected if within 500ms of an existing boundary. Per clarify: both halves inherit the original's theme + overrides.

**Request**
```json
{ "at_ms": 23500 }
```

**Response 200**: updated sections + assignments (same shape as `GET /sections` plus the assignments of the two new sections).

**Errors**
- `422 section_too_short` — would create a sub-500ms section.
- `422 split_at_boundary` — already a boundary there.
- `404 song_not_found`
- `409 source_file_missing` — audio required for playhead-based edit.

## POST `/api/v1/songs/<song_id>/sections/merge`

Merge a section with its adjacent follower. Per clarify: the merged result keeps the first section's theme + overrides.

**Request**
```json
{ "section_index": 2 }
```

Merges section 2 with section 3.

**Response 200**: updated sections.

**Errors**
- `422 no_follower` — trying to merge the last section.
- `404 section_not_found`

## POST `/api/v1/songs/<song_id>/sections/promote-ghost`

Promote an analyzer-detected ghost boundary into a real boundary. Both resulting sections inherit the original's theme + overrides.

**Request**
```json
{ "at_ms": 19000 }
```

**Response 200**: updated sections.

**Errors**
- `404 ghost_not_found`
- `422 section_too_short`

## PATCH `/api/v1/songs/<song_id>/sections/<section_index>`

Rename. Currently the only mutation on a specific section by index.

**Request**
```json
{ "label": "The Bridge" }
```

**Response 200**: updated section.

**Errors**
- `400 invalid_label` — empty, whitespace, or > 64 chars.
- `404 section_not_found`

## DELETE `/api/v1/songs/<song_id>/sections/<section_index>`

Delete a section. Its time range collapses into the adjacent section (previous if it exists, else next). Theme assignment is discarded.

**Response 200**: updated sections.

**Errors**
- `422 last_section_required` — FR-023.
- `404 section_not_found`

## POST `/api/v1/songs/<song_id>/sections/reset`

Reset all user edits back to the analyzer's original section list per FR-026. Theme assignments are re-derived from the analyzer's default-theme suggestions per FR-012a.

**Response 200**
```json
{
  "sections": [/* original detected_sections */],
  "ghost_boundaries": [/* original alt_boundaries */],
  "assignments": [/* auto-populated defaults per FR-012a */],
  "user_confirmed": false
}
```

**Errors**
- `404 song_not_found`
- `409 not_analyzed`

**Notes**
- All section mutations durably persist before 200 returns (FR-049a).
- All mutations are blocked when the song is `source_missing` for playhead-dependent ops (split, promote-ghost); label edits, merge, delete, and reset remain allowed per FR-001a.
