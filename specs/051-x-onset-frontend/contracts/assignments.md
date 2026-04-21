# Contract: Theme Assignments

Per-section theme assignment and parameter overrides, plus the status-transition gate to "themed". Traceable to FR-028 through FR-033, FR-029a, FR-032a.

## GET `/api/v1/songs/<song_id>/assignments`

Return the full per-section assignment list for a song.

**Response 200**
```json
{
  "assignments": [
    {
      "section_index": 0,
      "theme_id": "shimmer-wash",
      "overrides": { "brightness": 1.0, "hit_strength": 0.5, "dwell_time": 1.0, "color_shift": 0.0 },
      "user_confirmed": false
    }
  ],
  "song_status": "analyzed"
}
```

**Errors**
- `404 song_not_found`
- `409 not_analyzed`

## PUT `/api/v1/songs/<song_id>/assignments/<section_index>`

Assign a theme (and optionally overrides) to a specific section.

**Request**
```json
{ "theme_id": "driving-pulse", "overrides": { "brightness": 0.8 } }
```

`overrides` is a partial object; unspecified fields stay at their current value. If `theme_id` differs from the current value, `overrides` resets to the new theme's defaults **first**, then any explicit fields in this request are applied (FR-032a).

Setting `theme_id` also flips `user_confirmed: true` for that assignment (the user made an explicit choice).

**Response 200**: updated ThemeAssignment + new `song_status` (may flip `analyzed → themed` if this was the final unconfirmed section).

**Errors**
- `404 theme_not_found`
- `404 section_not_found`
- `400 invalid_override` — override value out of range (see [data-model.md](../data-model.md) ParameterOverride).

## POST `/api/v1/songs/<song_id>/assignments/accept-all`

The "accept all defaults" action described in FR-029a. Marks every auto-populated assignment as `user_confirmed: true` without changing the theme assignments themselves. Flips song status to `"themed"` if all sections have a `theme_id`.

**Response 200**
```json
{ "song_status": "themed", "confirmed_count": 8 }
```

**Errors**
- `409 incomplete_assignments` — some section has `theme_id == null`; the user must assign them individually before using accept-all.

## DELETE `/api/v1/songs/<song_id>/assignments/<section_index>`

Clear a specific section's theme assignment. Used rarely (there's no direct "un-theme" button in the handoff), but supports the case of re-analysis orphan handling. Flips song status back to `"analyzed"` if this was the only themed section.

**Response 200**: updated assignment (`theme_id: null`, `user_confirmed: false`) + new `song_status`.

## Notes

- All assignment writes durably persist before 200 returns (FR-049a).
- Assignments may be edited when `song.status == "source_missing"` (FR-001a: read-only review + theme edits are allowed without audio). However, `user_confirmed: true` MUST still be reachable from that state so the user can progress to `themed`.
