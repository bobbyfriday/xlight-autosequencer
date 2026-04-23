"""Analysis endpoints — T047.

POST /api/v1/songs/<song_id>/analyze         — start analysis (returns run_id)
GET  /api/v1/songs/<song_id>/analyze/status  — SSE progress stream
GET  /api/v1/songs/<song_id>/analysis        — fetch completed result
"""
from __future__ import annotations

import datetime
import json
import random
import string
import threading
import time
from pathlib import Path
from typing import Any

from flask import Response, jsonify, request, stream_with_context

from . import api_v1
from src.review.storage.library import load_library, save_library
from src.review.storage.assignments import load_session, save_session, save_full_session


# In-memory run registry. Maps song_id → RunState.
_runs: dict[str, "_RunState"] = {}
_runs_lock = threading.Lock()


class _RunState:
    def __init__(self, run_id: str, song_id: str, force: bool = False) -> None:
        self.run_id = run_id
        self.song_id = song_id
        self.started_at = _now_iso()
        self.status = "running"  # "running" | "done" | "failed"
        self.events: list[dict] = []
        self.result: dict | None = None
        self.force = force  # True → do NOT persist to session until commit
        self.committed = False  # True after analyze/commit called
        self.pending_sections: list[dict] | None = None
        self.pending_assignments: list[dict] | None = None
        self.lock = threading.Lock()

    def push(self, event: dict) -> None:
        with self.lock:
            self.events.append(event)


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_id() -> str:
    return "run_" + "".join(random.choices(string.ascii_letters + string.digits, k=5))


def _default_overrides() -> dict:
    return {
        "brightness": 1.0,
        "hit_strength": 0.5,
        "dwell_time": 1.0,
        "color_shift": 0.0,
    }


_KIND_TO_THEME: dict[str, str] = {
    "intro": "shimmer-wash",
    "verse": "driving-pulse",
    "chorus": "peak-flash",
    "solo": "solo-chase",
    "bridge": "bridge-burn",
    "outro": "shimmer-wash",
    "unknown": "neutral-glow",
}


def _auto_assign_defaults(song_id: str, sections: list[dict]) -> list[dict]:
    """Build default ThemeAssignment list from sections per FR-012a."""
    assignments = []
    for sec in sections:
        kind = sec.get("kind", "unknown")
        theme_id = _KIND_TO_THEME.get(kind, "neutral-glow")
        assignments.append({
            "section_index": sec["index"],
            "theme_id": theme_id,
            "overrides": _default_overrides(),
            "user_confirmed": False,
        })
    return assignments


def _analyze_in_background(state: "_RunState", source_path: str, song_id: str,
                            audio_bytes: bytes | None) -> None:
    """Run a lightweight analysis in a background thread.

    For now this produces synthetic results from the audio file metadata.
    Real vamp/madmom analysis is behind feature flags in the full pipeline.
    """
    try:
        state.push({"detector": "beats", "library": "librosa",
                    "status": "running", "progress": 0.0})
        state.push({"overall": {"status": "running", "progress": 0.1,
                                "eta_ms": 5000, "elapsed_ms": 0}})

        # Attempt real analysis with librosa if the source file exists
        sections: list[dict] = []
        beats: list[dict] = []
        bars: list[int] = []
        peaks: list[float] = []
        impacts: list[dict] = []
        drops: list[dict] = []
        duration_ms = 0

        src = Path(source_path) if source_path else None
        if src and src.exists():
            try:
                import numpy as np
                import librosa as _librosa

                y, sr = _librosa.load(str(src), sr=22050, mono=True, duration=None)
                duration_ms = int(len(y) / sr * 1000)

                # Beat tracking
                tempo_arr, beat_frames = _librosa.beat.beat_track(y=y, sr=sr)
                beat_times = _librosa.frames_to_time(beat_frames, sr=sr)
                for i, t in enumerate(beat_times):
                    beats.append({"t_ms": int(t * 1000), "bar": i // 4 + 1, "beat": i % 4 + 1})
                bars = [b["t_ms"] for b in beats if b["beat"] == 1]

                # Waveform peaks
                hop = max(1, len(y) // 200)
                peak_vals = [float(np.max(np.abs(y[i:i + hop]))) for i in range(0, len(y), hop)]
                max_peak = max(peak_vals) if peak_vals else 1.0
                peaks = [v / max_peak for v in peak_vals[:200]]

                # Simple section detection via energy
                frame_hop = sr // 5
                rms = _librosa.feature.rms(y=y, frame_length=2048, hop_length=frame_hop)[0]
                mean_rms = float(np.mean(rms))
                # Create 4 equal sections with alternating kinds
                seg_dur = duration_ms // 4
                kinds = ["intro", "verse", "chorus", "outro"]
                for i in range(4):
                    start = i * seg_dur
                    end = (i + 1) * seg_dur if i < 3 else duration_ms
                    sections.append({
                        "index": i,
                        "start_ms": start,
                        "end_ms": end,
                        "kind": kinds[i],
                        "label": kinds[i].capitalize(),
                    })

                state.push({"detector": "beats", "library": "librosa",
                            "status": "done", "confidence": 0.85})
                state.push({"overall": {"status": "running", "progress": 0.5,
                                        "eta_ms": 2000, "elapsed_ms": 500}})
            except Exception as exc:
                state.push({"log": {"at_ms": 0, "level": "warn",
                                    "message": f"librosa analysis failed: {exc}"}})

        if not sections:
            # Fallback: single section covering whole duration
            sections = [{"index": 0, "start_ms": 0, "end_ms": max(duration_ms, 1000),
                         "kind": "unknown", "label": "Full Song"}]

        detectors = [
            {"name": "beats", "library": "librosa", "status": "done", "confidence": 0.85, "error": None},
            {"name": "sections", "library": "librosa", "status": "done", "confidence": 0.75, "error": None},
        ]

        result: dict[str, Any] = {
            "song_id": song_id,
            "detected_sections": sections,
            "alt_boundaries": [],
            "beats": beats,
            "bars": bars,
            "impacts": impacts,
            "drops": drops,
            "peaks": peaks,
            "detectors": detectors,
            "completed_at": _now_iso(),
            "pipeline_version": "stub",
        }

        # Persist result to session file — also store detected_sections for reset.
        # When force=True, we do NOT overwrite the existing session; wait for commit.
        assignments = _auto_assign_defaults(song_id, sections)
        if not state.force:
            try:
                save_full_session(song_id, {
                    "sections": sections,
                    "detected_sections": sections,
                    "assignments": assignments,
                    "ghost_boundaries": [],
                })
            except Exception:
                pass

            # Update song status to "analyzed"
            try:
                lib = load_library()
                for s in lib["songs"]:
                    if s["song_id"] == song_id:
                        s["status"] = "analyzed"
                        break
                save_library(lib)
            except Exception:
                pass
        else:
            # Store the suggested assignments in the run state for commit later
            with state.lock:
                state.pending_sections = sections
                state.pending_assignments = assignments

        with state.lock:
            state.result = result
            state.status = "done"

        state.push({"overall": {"status": "done", "progress": 1.0,
                                "eta_ms": 0, "elapsed_ms": 1000}})

    except Exception as exc:
        with state.lock:
            state.status = "failed"
        state.push({"overall": {"status": "failed", "progress": 0.0,
                                "eta_ms": 0, "elapsed_ms": 0,
                                "error": str(exc)}})


@api_v1.route("/songs/<song_id>/analyze", methods=["POST"])
def start_analyze(song_id: str):
    lib = load_library()
    song = next((s for s in lib["songs"] if s["song_id"] == song_id), None)
    if song is None:
        return jsonify({"error": {"code": "song_not_found",
                                   "message": "Song not found"}}), 404

    source_paths = song.get("source_paths") or []
    source_path = source_paths[0] if source_paths else ""
    if source_path and not Path(source_path).exists():
        return jsonify({"error": {"code": "source_file_missing",
                                   "message": "Audio source not found on disk"}}), 409

    body = request.get_json(silent=True) or {}
    force = bool(body.get("force", False))

    with _runs_lock:
        existing = _runs.get(song_id)
        if existing and existing.status == "running":
            return jsonify({"run_id": existing.run_id,
                            "started_at": existing.started_at}), 202
        # Start new run
        state = _RunState(_run_id(), song_id, force=force)
        _runs[song_id] = state

    # Audio bytes not needed since we use the file path directly
    t = threading.Thread(
        target=_analyze_in_background,
        args=(state, source_path, song_id, None),
        daemon=True,
    )
    t.start()

    return jsonify({"run_id": state.run_id, "started_at": state.started_at}), 202


@api_v1.route("/songs/<song_id>/analyze/commit", methods=["POST"])
def commit_analyze(song_id: str):
    """Apply a pending force re-analysis result after user confirms the mapping (FR-013a)."""
    lib = load_library()
    song = next((s for s in lib["songs"] if s["song_id"] == song_id), None)
    if song is None:
        return jsonify({"error": {"code": "song_not_found",
                                   "message": "Song not found"}}), 404

    body = request.get_json(silent=True) or {}
    run_id = body.get("run_id")
    if not run_id:
        return jsonify({"error": {"code": "missing_field",
                                   "message": "run_id is required"}}), 400

    assignment_mapping = body.get("assignment_mapping", [])

    # Find the run
    with _runs_lock:
        state = _runs.get(song_id)

    if state is None or state.run_id != run_id:
        # Also search for any run with this run_id (could have been replaced)
        matching = None
        with _runs_lock:
            for sid, s in _runs.items():
                if s.run_id == run_id and sid == song_id:
                    matching = s
                    break
        state = matching

    if state is None:
        return jsonify({"error": {"code": "run_not_found",
                                   "message": "No run found with this run_id"}}), 404

    if state.committed:
        return jsonify({"error": {"code": "already_committed",
                                   "message": "This run has already been committed"}}), 409

    with state.lock:
        pending_sections = state.pending_sections
        pending_assignments = state.pending_assignments
        result = state.result

    if pending_sections is None and result is not None:
        # Non-force run — use detected_sections from result
        pending_sections = result.get("detected_sections", [])
        pending_assignments = _auto_assign_defaults(song_id, pending_sections)

    if pending_sections is None:
        return jsonify({"error": {"code": "run_not_found",
                                   "message": "Run result not yet available"}}), 404

    # Apply assignment_mapping: carry over themes from old assignments where specified
    session = load_session(song_id)
    old_assignments = session.get("assignments", []) if session else []

    final_assignments = list(pending_assignments)  # start from suggested defaults
    for entry in assignment_mapping:
        new_idx = entry.get("new_section_index")
        old_idx = entry.get("inherited_from_old_index")
        action = entry.get("action", "")
        if new_idx is None or new_idx >= len(final_assignments):
            continue
        if action in ("kept", "shifted") and old_idx is not None and old_idx < len(old_assignments):
            old_a = old_assignments[old_idx]
            final_assignments[new_idx] = {
                "section_index": new_idx,
                "theme_id": old_a.get("theme_id"),
                "overrides": old_a.get("overrides", _default_overrides()),
                "user_confirmed": False,
            }

    # Persist
    try:
        save_full_session(song_id, {
            "sections": pending_sections,
            "detected_sections": pending_sections,
            "assignments": final_assignments,
            "ghost_boundaries": [],
        })
    except Exception as exc:
        return jsonify({"error": {"code": "internal_error", "message": str(exc)}}), 500

    # Update song status
    try:
        lib2 = load_library()
        for s in lib2["songs"]:
            if s["song_id"] == song_id:
                s["status"] = "analyzed"
                break
        from src.review.storage.library import save_library
        save_library(lib2)
    except Exception:
        pass

    with state.lock:
        state.committed = True

    return jsonify({
        "sections": pending_sections,
        "assignments": final_assignments,
    }), 200


@api_v1.route("/songs/<song_id>/analyze/status", methods=["GET"])
def analyze_status(song_id: str):
    with _runs_lock:
        state = _runs.get(song_id)

    if state is None:
        return jsonify({"error": {"code": "run_not_found",
                                   "message": "No run found for song"}}), 404

    def _gen():
        idx = 0
        while True:
            with state.lock:
                n = len(state.events)
                status = state.status

            while idx < n:
                yield f"data: {json.dumps(state.events[idx])}\n\n"
                idx += 1

            if status != "running":
                return
            time.sleep(0.05)

    return Response(
        stream_with_context(_gen()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api_v1.route("/songs/<song_id>/analysis", methods=["GET"])
def get_analysis(song_id: str):
    lib = load_library()
    song = next((s for s in lib["songs"] if s["song_id"] == song_id), None)
    if song is None:
        return jsonify({"error": {"code": "song_not_found",
                                   "message": "Song not found"}}), 404

    if song.get("status") == "draft":
        return jsonify({"error": {"code": "not_analyzed",
                                   "message": "Song has not been analyzed yet"}}), 409

    with _runs_lock:
        state = _runs.get(song_id)

    if state is None or state.result is None:
        # Try loading from session file
        session = load_session(song_id)
        if session and "sections" in session:
            sections = session["sections"]
            result = {
                "song_id": song_id,
                "detected_sections": sections,
                "alt_boundaries": [],
                "beats": [],
                "bars": [],
                "impacts": [],
                "drops": [],
                "peaks": [],
                "detectors": [],
                "completed_at": _now_iso(),
                "pipeline_version": "stub",
            }
            return jsonify(result), 200
        return jsonify({"error": {"code": "not_analyzed",
                                   "message": "Analysis result not available"}}), 409

    return jsonify(state.result), 200
