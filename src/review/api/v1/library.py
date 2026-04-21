"""GET /api/v1/library — song library endpoint (T045)."""
from __future__ import annotations

from pathlib import Path

from flask import jsonify

from . import api_v1
from src.review.storage.library import load_library


def _song_with_source_exists(song: dict) -> dict:
    """Add computed source_exists field to a song dict."""
    paths = song.get("source_paths") or []
    source_exists = any(Path(p).exists() for p in paths)
    return {**song, "source_exists": source_exists}


def _normalize_folder(folder: dict) -> dict:
    """Normalize folder dict to use folder_id instead of id."""
    if "folder_id" not in folder and "id" in folder:
        folder = {**folder, "folder_id": folder["id"]}
    return folder


@api_v1.route("/library", methods=["GET"])
def get_library():
    lib = load_library()
    songs = [_song_with_source_exists(s) for s in lib.get("songs", [])]
    folders = [_normalize_folder(f) for f in lib.get("folders", [])]
    return jsonify({"songs": songs, "folders": folders}), 200
