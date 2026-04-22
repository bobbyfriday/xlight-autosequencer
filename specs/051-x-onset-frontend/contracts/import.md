# Contract: Import

Accepts a user-dropped audio file, computes its content hash, dedups against the library, and returns the resulting Song. Traceable to FR-006, FR-007, FR-008, FR-001a.

## POST `/api/v1/import`

**Request**: `multipart/form-data` with fields:

| Field | Type | Notes |
| --- | --- | --- |
| `audio` | file | MP3 / WAV / FLAC / AIFF. Required. |
| `source_path` | string | Absolute path on the user's machine where the file originates. Optional but recommended — used for the Song's `source_paths` list and subsequent audio streaming. If omitted, the backend copies the uploaded bytes to its own managed location. |
| `folder_id` | string | Target folder. Optional; defaults to `unfiled`. |

**Response 201** — new song created
```json
{
  "created": true,
  "song": {
    "song_id": "a1b2c3d4e5f6a7b8",
    "title": "Baby Shark",
    "artist": "Pinkfong",
    "duration_ms": 145000,
    "status": "draft",
    "folder_id": "unfiled",
    "source_paths": ["/Users/bob/Music/BabyShark.mp3"],
    "imported_at": "2026-04-21T18:02:00Z"
  }
}
```

**Response 200** — song already exists (dedup)
```json
{
  "created": false,
  "song": { /* existing Song */ },
  "source_path_added": true
}
```

`source_path_added` is `true` when the incoming `source_path` differed from any previously-seen path for the same `song_id`; the backend appended it to `source_paths` (FR-001a). Existing analysis, sections, and theme assignments are preserved — that's the entire point of content-hash dedup.

**Errors**
- `400 unsupported_format` — extension or sniffed magic-bytes aren't in the allowed set (FR-007).
- `400 audio_decode_failed` — extension looks supported but librosa couldn't load it.
- `413 audio_too_large` — arbitrary cap (default 200 MB; configurable).
- `400 missing_file` — no `audio` field.

**Notes**
- The backend MUST decode the audio enough to read `duration_ms` and compute the content hash before returning. This is fast (~100ms for a 4-minute MP3).
- No analysis runs automatically on import — the frontend navigates to ANALYZE and calls `POST /songs/<id>/analyze` explicitly (FR-008).
- The content-hash computation SHOULD run on the bytes as-delivered, before any normalization, so the same file always produces the same hash regardless of metadata edits downstream.
