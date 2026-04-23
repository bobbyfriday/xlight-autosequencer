# Contract: First-Use Model Weights Download

**Feature**: 052-tauri-desktop-packaging
**Status**: Stable contract for v1

The packaged app does not bundle demucs stem-separation model weights. On the first stem-separation request, the backend detects missing weights, the frontend prompts the user, and on confirmation the backend downloads weights with progress streamed via SSE.

## Applies to

- Model: `htdemucs_6s` (facebookresearch/demucs, CC BY-NC 4.0 weights)
- Location: `~/Library/Application Support/XLight/models/torch-hub/checkpoints/`
- Env var: `TORCH_HOME` set by sidecar launcher to the `models/torch-hub/` parent directory so demucs finds weights without further config.

## Protocol

### Step 1 — Frontend requests stem separation

```
POST /api/v1/analysis/<song_id>/separate-stems
Content-Type: application/json

{ "model": "htdemucs_6s" }
```

### Step 2a — Weights present: normal 200 response

Backend proceeds with separation as today. Protocol identical to the existing stem-separation flow (`src/analyzer/stems.py`).

### Step 2b — Weights missing: 409 Conflict

```
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "needs_download": true,
  "model": "htdemucs_6s",
  "size_bytes": 178257920,
  "shards": [
    { "url": "https://dl.fbaipublicfiles.com/demucs/...", "sha256": "...", "size_bytes": 44500000 },
    ...
  ],
  "license": "CC BY-NC 4.0",
  "license_note": "For non-commercial use. A commercial license from Meta is required for commercial distribution of stem separation outputs."
}
```

The frontend MUST surface the license note in the download confirmation dialog.

### Step 3 — User confirms download

```
POST /api/v1/models/download
Content-Type: application/json
Accept: text/event-stream

{ "name": "htdemucs_6s" }
```

Backend response is an SSE stream:

```
event: progress
data: {"model": "htdemucs_6s", "shard_index": 0, "bytes_downloaded": 1048576, "bytes_total": 44500000, "overall_bytes": 1048576, "overall_total": 178257920}

event: progress
data: {...}

event: shard_complete
data: {"model": "htdemucs_6s", "shard_index": 0, "sha256_verified": true}

event: progress
data: {...}

...

event: complete
data: {"model": "htdemucs_6s", "path": "/Users/.../models/torch-hub/checkpoints/..."}
```

Error events:

```
event: error
data: {"code": "network", "shard_index": 1, "bytes_downloaded": 5000000, "message": "Connection reset"}
```

Errors do NOT close the stream — the backend retries each shard up to 3 times with exponential backoff, resuming from `bytes_downloaded`. Only after all retries fail does the backend emit a terminal error and close the stream.

### Step 4 — Resume after interruption

If the user closes the app or the network dies mid-download, `.download-state.json` in the cache directory records per-shard `bytes_downloaded` and the partial file path. On the next `POST /api/v1/models/download`:

- Backend reads `.download-state.json`.
- For each shard not yet `completed`, sends `Range: bytes=<bytes_downloaded>-` to resume.
- For each completed shard, skips download but verifies SHA256 before marking final.
- Partial files that fail SHA256 verification are deleted and re-downloaded from zero.

### Step 5 — Retry stem separation

After `complete` event, frontend re-issues the original `POST /api/v1/analysis/<song_id>/separate-stems`. Backend now finds the weights and proceeds normally.

## Contract properties

- **User-visible**: the download never happens without an explicit user confirmation.
- **Resumable**: interrupted downloads resume from the last verified byte; no full re-download after a crash.
- **Verified**: every shard is SHA256-verified against hashes delivered in the 409 response. The hashes themselves come from a bundled `download_model_manifest.json` in the `.app`, updatable via a new installer.
- **License-surfaced**: the non-commercial license note is shown to the user before the first download.
- **Cache-reusing**: once downloaded, weights live in the standard torch hub path. Re-installs of the app reuse the existing cache.
- **Non-blocking for non-stem flow**: if a user never requests stem separation, no download ever happens; the rest of the app is fully offline.

## Testing

- **Unit (Python)**:
  - Download resume: partially-written shard file with matching `.download-state.json` resumes correctly.
  - SHA256 mismatch: corrupted shard is deleted and re-downloaded.
  - Retry/backoff: injected network failure triggers retries without progress duplication.
- **Integration**: mock `dl.fbaipublicfiles.com` with a local HTTP server that serves shards and can simulate connection drops; end-to-end the full download+verify+place flow.
- **Manual**: at least one real download to confirm URL validity and file sizes match the bundled manifest.

## Not in scope for v1

- Supporting other demucs models (only `htdemucs_6s` is currently used by `src/analyzer/stems.py:190`).
- Pre-downloading weights at install time via a separate installer component.
- Delta updates to newer weight versions (would require version metadata in the cache).
- Bundling weights in the `.app` (requires Meta commercial licensing — see R6 in research.md).
