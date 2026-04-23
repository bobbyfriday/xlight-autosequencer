# Contract: Library & Folders

Covers the library rail, folder CRUD, song removal, and cache purge. Traceable to FR-001 through FR-005c.

## GET `/api/v1/library`

List every imported song plus the folder tree. Used by the LIBRARY screen on load and after any mutation.

**Response 200**
```json
{
  "schema_version": 1,
  "songs": [
    {
      "song_id": "a1b2c3d4e5f6a7b8",
      "title": "Baby Shark",
      "artist": "Pinkfong",
      "duration_ms": 145000,
      "status": "themed",
      "folder_id": "folder_xmas26",
      "bpm": 115.0,
      "key": "G major",
      "source_exists": true,
      "imported_at": "2026-04-21T18:02:00Z",
      "last_opened_at": "2026-04-21T18:20:41Z"
    }
  ],
  "folders": [
    { "folder_id": "unfiled", "name": "Unfiled", "collapsed": false, "order": 0 },
    { "folder_id": "folder_xmas26", "name": "Christmas 2026", "collapsed": false, "order": 1 }
  ]
}
```

**Notes**
- `source_exists` is computed per-request from disk; `false` ⇒ the frontend renders the "source file missing" affordance.
- Songs are returned in import order; the frontend sorts / filters client-side (SC-007).

## POST `/api/v1/folders`

Create a new folder.

**Request**
```json
{ "name": "Halloween 2026" }
```

**Response 201**
```json
{ "folder_id": "folder_kY7qZ0", "name": "Halloween 2026", "collapsed": false, "order": 2 }
```

**Errors**
- `400 invalid_name` — empty, whitespace-only, or longer than 64 chars.
- `409 folder_name_taken` — case-insensitive duplicate.

## PATCH `/api/v1/folders/<folder_id>`

Rename, reorder, or collapse.

**Request** (any subset)
```json
{ "name": "X 2026", "collapsed": true, "order": 3 }
```

**Response 200**: updated Folder.

**Errors**
- `404 folder_not_found`
- `400 reserved_folder` — cannot rename the `unfiled` folder.

## DELETE `/api/v1/folders/<folder_id>`

Delete a folder. Moves its songs to `unfiled`. The `unfiled` folder cannot be deleted.

**Response 204**: empty body.

**Errors**
- `404 folder_not_found`
- `400 reserved_folder` — cannot delete `unfiled`.

## PATCH `/api/v1/songs/<song_id>/folder`

Move a song between folders.

**Request**
```json
{ "folder_id": "folder_xmas26" }
```

**Response 200**: updated Song (same shape as in `GET /library`).

**Errors**
- `404 song_not_found`
- `404 folder_not_found`

## DELETE `/api/v1/songs/<song_id>`

Step 1 of song deletion per FR-005a: drop the app state for this song (Session, Assignments, folder membership, preferences' last-playhead entry). Does NOT touch the audio file on disk. Does NOT touch the analysis cache or stems.

**Response 200**
```json
{
  "song_id": "a1b2c3d4e5f6a7b8",
  "cache_purge_available": true,
  "cache_size_bytes": 412339200
}
```

`cache_purge_available` is true when there's still an analysis cache + stems on disk for this song_id that the user can now choose to purge via `POST /songs/<id>/purge`. The frontend shows the confirmation dialog immediately after this response.

**Errors**
- `404 song_not_found`
- `409 song_is_analyzing` — an analysis run is active for this song; the user must cancel it first.

## POST `/api/v1/songs/<song_id>/purge`

Step 2 of song deletion per FR-005b: purge the analysis cache and stems for a previously-removed song.

**Request** (body optional; defaults to purging both)
```json
{ "analysis": true, "stems": true }
```

**Response 200**
```json
{ "freed_bytes": 412339200 }
```

**Errors**
- `404 cache_not_found` — nothing to purge.
- `409 song_still_imported` — the song is still in the library; call `DELETE /songs/<song_id>` first.
