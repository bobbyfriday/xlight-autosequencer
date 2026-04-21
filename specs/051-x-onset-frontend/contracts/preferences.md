# Contract: Preferences & Library Portability

Per-machine user preferences plus the library export / import bundle endpoints. Traceable to FR-043 through FR-049c.

## GET `/api/v1/preferences`

**Response 200**
```json
{
  "mode": "dark",
  "density": "comfortable",
  "inspector_open": true,
  "tweaks_open": false,
  "last_song_id": "a1b2c3d4e5f6a7b8",
  "last_screen": "theme",
  "last_playhead_ms_by_song": { "a1b2c3d4e5f6a7b8": 45200 },
  "layout_id": "layout_b3f01a",
  "library_state_version": 42
}
```

## PUT `/api/v1/preferences`

Partial update. Any subset of the preference fields may be provided.

**Request**
```json
{ "mode": "light" }
```

**Response 200**: updated Preferences.

**Errors**
- `400 invalid_preferences` — e.g., `mode: "neon"`.

**Notes**
- Frontend calls this on every toggle / setting change (FR-049a).
- `last_playhead_ms_by_song` writes may be debounced up to 1 second on the client (FR-049b); server accepts them as normal PUTs.

## POST `/api/v1/library/export`

Produce a portable library bundle (FR-049c). Zip format, `.xonset-bundle` extension.

**Request** (optional; default exports everything)
```json
{ "include_folder_ids": ["folder_xmas26"] }
```

If `include_folder_ids` is present, only songs in those folders are included in the bundle; otherwise every song is included.

**Response 200**: `application/zip` body, `Content-Disposition: attachment; filename="xonset-library-2026-04-21.xonset-bundle"`.

Bundle contents (see [data-model.md](../data-model.md) Bundle):
```
xonset-library-2026-04-21.xonset-bundle  (zip)
├── library.json           # Bundle metadata + songs + folders + preferences + layout
└── songs/
    └── <song_id>/
        └── session.json   # Sections, assignments, overrides for that song
```

**Notes**: audio files are NOT included per FR-049c.

## POST `/api/v1/library/import`

Consume a bundle produced by `POST /library/export`.

**Request**: `multipart/form-data`

| Field | Type | Notes |
| --- | --- | --- |
| `bundle` | file | `.xonset-bundle` (zip). Required. |
| `mode` | string | `"merge"` or `"replace"`. Default `"merge"`. |

- **merge**: add the bundle's songs/folders to the current library. On `song_id` collision, the bundle's Session wins if its `library_state_version` is higher than the local version (research §12); otherwise the local version wins.
- **replace**: wipe the existing library and install the bundle's contents. Destructive — frontend MUST double-confirm.

**Response 200**
```json
{
  "imported_songs": 12,
  "merged_songs": 3,
  "skipped_songs": 0,
  "source_missing_songs": ["c9d8e7f6a5b4c3d2", "e1f2a3b4c5d6e7f8"]
}
```

`source_missing_songs` lists `song_id` values whose audio was not found on this machine's disk — they land in the library with `status: "source_missing"` (FR-001a).

**Errors**
- `400 invalid_bundle` — zip is malformed, missing `library.json`, or schema version mismatch.
- `400 unsupported_schema_version` — bundle was produced by a newer version of the app.
