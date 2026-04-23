"""Model-weights download endpoints.

Per contracts/weights-download.md. Exposes:
  - GET /api/v1/models/<name>/status      -> { present: bool, license, size }
  - POST /api/v1/models/<name>/download   -> SSE stream of progress events

These are only used by the packaged app for the first-stem-separation
weights download. In dev mode the endpoints are still reachable but the
frontend typically doesn't call them (torch.hub downloads on demand).
"""
from __future__ import annotations

import json
from typing import Iterator

from flask import Response, jsonify, request, stream_with_context

from src.packaging import weights_downloader
from src.review.api.v1 import api_v1


@api_v1.get("/models/<model_name>/status")
def model_status(model_name: str):
    try:
        manifest = weights_downloader.load_manifest()
    except Exception as exc:  # manifest shouldn't be missing, but surface it
        return jsonify({"error": {"code": "manifest_unreadable", "message": str(exc)}}), 500

    if model_name not in manifest:
        return jsonify({"error": {"code": "unknown_model", "message": model_name}}), 404

    spec = manifest[model_name]
    return jsonify({
        "name": model_name,
        "present": weights_downloader.is_model_present(model_name),
        "size_bytes": spec.total_size_bytes,
        "license": spec.license,
        "license_note": spec.license_note,
        "shard_count": len(spec.shards),
    })


@api_v1.post("/models/<model_name>/download")
def model_download(model_name: str):
    try:
        manifest = weights_downloader.load_manifest()
    except Exception as exc:
        return jsonify({"error": {"code": "manifest_unreadable", "message": str(exc)}}), 500

    if model_name not in manifest:
        return jsonify({"error": {"code": "unknown_model", "message": model_name}}), 404

    def stream() -> Iterator[bytes]:
        queue: list[dict] = []

        def on_progress(evt: weights_downloader.ProgressEvent) -> None:
            queue.append({
                "event": "progress",
                "data": {
                    "model": evt.model,
                    "shard_index": evt.shard_index,
                    "shard_name": evt.shard_name,
                    "bytes_downloaded": evt.bytes_downloaded,
                    "shard_size_bytes": evt.shard_size_bytes,
                    "overall_bytes": evt.overall_bytes,
                    "overall_total": evt.overall_total,
                },
            })

        # Download runs synchronously in this request thread — SSE chunks
        # are flushed as the callback enqueues them. This is fine for
        # local sidecar use where we're the only client.
        try:
            dest = weights_downloader.download_model(model_name, on_progress=on_progress)
            # Drain any pending progress events that arrived during the
            # final write+rename.
            while queue:
                evt = queue.pop(0)
                yield _sse(evt["event"], evt["data"])
            yield _sse("complete", {"model": model_name, "path": str(dest)})
        except Exception as exc:
            while queue:
                evt = queue.pop(0)
                yield _sse(evt["event"], evt["data"])
            yield _sse("error", {
                "code": type(exc).__name__,
                "message": str(exc),
            })

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: dict) -> bytes:
    return (f"event: {event}\ndata: {json.dumps(data)}\n\n").encode("utf-8")
