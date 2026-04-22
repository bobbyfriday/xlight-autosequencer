# Contract: Analysis

Three endpoints cover the ANALYZE screen: start an analysis, stream per-detector progress via SSE, and fetch the completed result. Traceable to FR-009 through FR-013a and FR-011a.

## POST `/api/v1/songs/<song_id>/analyze`

Start an analysis run. Idempotent — if a run is already in progress for this `song_id`, returns the same run id.

**Request** (body optional)
```json
{ "force": false }
```

`force: true` triggers a re-analysis per FR-013a; only allowed when `song.status` is `analyzed` or `themed`. For a `themed` song, the re-analysis does NOT overwrite the stored session until the frontend calls `POST /songs/<id>/analyze/commit` with the user's confirmed section mapping.

**Response 202**
```json
{ "run_id": "run_Xa71Q", "started_at": "2026-04-21T18:02:30Z" }
```

**Errors**
- `404 song_not_found`
- `409 analysis_in_progress` — another song is analyzing (single-concurrency per assumption "Single-song analysis concurrency"). Details include the currently-running `song_id`.
- `409 source_file_missing` — audio source not found on disk (FR-001a).

## GET `/api/v1/songs/<song_id>/analyze/status`

**Server-Sent Events** stream of per-detector progress. Connection stays open until the run terminates.

**Response**: `text/event-stream`

Each event is:
```
data: {"detector":"beats","library":"madmom","status":"running","progress":0.42}

data: {"detector":"beats","library":"madmom","status":"done","confidence":0.93}

...

data: {"overall":{"status":"done","elapsed_ms":112340}}
```

**Event types**
- Per-detector: `{"detector": str, "library": str, "status": "queued"|"running"|"done"|"failed", "progress": 0..1?, "confidence": 0..1?, "error": str?}`.
- Overall: `{"overall": {"status": "running"|"done"|"failed", "progress": 0..1, "eta_ms": int, "elapsed_ms": int}}`.
- Log line: `{"log": {"at_ms": int, "level": "info"|"warn"|"error", "message": str}}` — drives the ANALYZE screen's live log pane (FR-009).

**Errors**
- `404 run_not_found`

**FR-011a behavior**: if the server process dies mid-run, the in-progress `AnalysisResult` is discarded. On reconnect with the same `song_id`, the song shows `status: "draft"` again and the SSE stream ends with a `{"overall": {"status": "interrupted"}}` event (when possible) or closes unexpectedly (when not).

## POST `/api/v1/songs/<song_id>/analyze/retry`

Retry a single failed detector within a completed run. Corresponds to FR-011.

**Request**
```json
{ "detector": "chords" }
```

**Response 202**
```json
{ "run_id": "run_Xa71Q" }
```

The detector re-runs; the SSE stream resumes with new events for that detector only.

**Errors**
- `404 detector_not_found`
- `409 detector_already_running`
- `409 detector_succeeded` — that detector did not fail; nothing to retry.

## GET `/api/v1/songs/<song_id>/analysis`

Return the full completed `AnalysisResult` for a song. Used by TIMELINE and THEME on song load (FR-013, SC-008).

**Response 200**
```json
{
  "song_id": "a1b2c3d4e5f6a7b8",
  "detected_sections": [
    { "index": 0, "start_ms": 0, "end_ms": 12500, "kind": "intro", "label": "Intro" },
    { "index": 1, "start_ms": 12500, "end_ms": 34000, "kind": "verse", "label": "Verse 1" }
  ],
  "alt_boundaries": [
    { "at_ms": 19000, "kind": "ghost", "confidence": 0.62, "promoted_by_user": false }
  ],
  "beats": [{ "t_ms": 300, "bar": 1, "beat": 1 }],
  "bars": [300, 2400, 4500],
  "impacts": [{ "t_ms": 12500, "conf": 0.88 }],
  "drops": [{ "t_ms": 98000, "conf": 0.91 }],
  "peaks": [0.12, 0.34, 0.67],
  "detectors": [
    { "name": "beats", "library": "madmom", "status": "done", "confidence": 0.93 }
  ],
  "completed_at": "2026-04-21T18:04:25Z",
  "pipeline_version": "333c68b"
}
```

**Errors**
- `404 song_not_found`
- `409 not_analyzed` — song is still `status: "draft"`.

## POST `/api/v1/songs/<song_id>/analyze/commit`

Apply a pending re-analysis result (produced by `analyze` with `force: true` on a themed song) after the user has confirmed the section-mapping review dialog (FR-013a).

**Request**
```json
{
  "run_id": "run_Xa71Q",
  "assignment_mapping": [
    { "new_section_index": 0, "inherited_from_old_index": 0, "action": "kept" },
    { "new_section_index": 1, "inherited_from_old_index": 0, "action": "shifted", "shift_ms": 180 },
    { "new_section_index": 2, "inherited_from_old_index": null, "action": "needs_theme" }
  ]
}
```

The frontend computes this mapping by max-overlap (research §10), shows it to the user, and sends the confirmed version. `action: "dropped"` on the old side lists orphans.

**Response 200**: new AnalysisResult replaces the old; Song Session updated with preserved assignments where `action == "kept"` or `"shifted"`.

**Errors**
- `404 run_not_found`
- `409 already_committed`
- `400 mapping_invalid` — indexes don't match the pending run's new section list.
