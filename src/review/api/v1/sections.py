"""GET /api/v1/songs/<song_id>/sections — section list endpoint (T049)."""
from __future__ import annotations

from flask import jsonify

from . import api_v1
from src.review.storage.library import load_library
from src.review.storage.assignments import load_session


@api_v1.route("/songs/<song_id>/sections", methods=["GET"])
def get_sections(song_id: str):
    lib = load_library()
    song = next((s for s in lib["songs"] if s["song_id"] == song_id), None)
    if song is None:
        return jsonify({"error": {"code": "song_not_found",
                                   "message": "Song not found"}}), 404

    if song.get("status") == "draft":
        return jsonify({"error": {"code": "not_analyzed",
                                   "message": "Song has not been analyzed yet"}}), 409

    session = load_session(song_id)
    if session is None:
        return jsonify({"error": {"code": "not_analyzed",
                                   "message": "No analysis result available"}}), 409

    sections = session.get("sections", [])
    return jsonify({
        "sections": sections,
        "ghost_boundaries": [],  # populated by full analysis pipeline
    }), 200
