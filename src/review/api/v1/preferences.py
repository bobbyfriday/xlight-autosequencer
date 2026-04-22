"""Preferences endpoints: GET/PUT /api/v1/preferences."""
from __future__ import annotations

from flask import jsonify, request

from . import api_v1
from src.review.storage.library import load_library, save_library

_VALID_MODES = {"dark", "light"}
_VALID_DENSITIES = {"comfortable", "compact"}


@api_v1.route("/preferences", methods=["GET"])
def get_preferences():
    lib = load_library()
    return jsonify(lib["preferences"]), 200


@api_v1.route("/preferences", methods=["PUT"])
def put_preferences():
    body = request.get_json(silent=True) or {}

    mode = body.get("mode")
    if mode is not None and mode not in _VALID_MODES:
        return (
            jsonify({"error": {"code": "invalid_preferences", "message": f"Invalid mode: {mode!r}"}}),
            400,
        )

    density = body.get("density")
    if density is not None and density not in _VALID_DENSITIES:
        return (
            jsonify({"error": {"code": "invalid_preferences", "message": f"Invalid density: {density!r}"}}),
            400,
        )

    lib = load_library()
    prefs = lib["preferences"]
    prefs.update(body)
    lib["preferences"] = prefs
    save_library(lib)
    return jsonify(prefs), 200
