# Contract: Themes

Read-only catalog of the built-in theme set. No v0 endpoints for user-authored themes (scope-excluded). Traceable to FR-028.

## GET `/api/v1/themes`

Return every built-in theme available to the user. Results are stable within a release.

**Response 200**
```json
{
  "schema_version": 1,
  "themes": [
    {
      "theme_id": "driving-pulse",
      "name": "Driving Pulse",
      "description": "Warm strobe with beat-tight color shifts. Great for verses.",
      "accent": "#d97757",
      "swatches": ["#d97757", "#f5a623", "#f5f5f0", "#111114"],
      "default_for_kinds": ["verse"]
    },
    {
      "theme_id": "shimmer-wash",
      "name": "Shimmer Wash",
      "description": "Slow color drift with micro-sparkle. Great for intros.",
      "accent": "#4ade80",
      "swatches": ["#4ade80", "#7eebd1", "#f5f5f0", "#1a1a20"],
      "default_for_kinds": ["intro", "outro"]
    }
  ]
}
```

**Invariants**
- Every Section kind in `"intro" | "verse" | "chorus" | "solo" | "bridge" | "outro" | "unknown"` MUST have at least one theme with that kind in `default_for_kinds` (required by FR-012a).
- `theme_id` values never change across v0 releases (assumption: "built-in theme set is stable for v0").

**No errors under normal operation.**
