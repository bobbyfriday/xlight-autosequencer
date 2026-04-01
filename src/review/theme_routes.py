"""Flask blueprint for theme CRUD endpoints."""
from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory

theme_bp = Blueprint("themes", __name__)


def _theme_to_dict(theme, is_builtin: bool) -> dict:
    """Serialize a Theme to a JSON-safe dict with is_builtin flag."""
    from dataclasses import asdict
    d = asdict(theme)
    d["is_builtin"] = is_builtin
    return d


@theme_bp.route("/editor")
def theme_editor():
    static_dir = str(Path(__file__).parent / "static")
    return send_from_directory(static_dir, "theme-editor.html")


@theme_bp.route("/list")
def theme_list():
    from src.themes.library import load_theme_library, _BUILTIN_PATH, _DEFAULT_CUSTOM_DIR

    lib = load_theme_library()
    # Determine which are built-in vs custom
    builtin_names: set[str] = set()
    try:
        with open(_BUILTIN_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        builtin_names = set(raw.get("themes", {}).keys())
    except Exception:
        pass

    themes = []
    for name, theme in lib.themes.items():
        themes.append(_theme_to_dict(theme, name in builtin_names))

    return jsonify({"themes": themes})


@theme_bp.route("/create", methods=["POST"])
def theme_create():
    from src.themes.library import load_theme_library, save_custom_theme
    from src.themes.models import Theme

    data = request.get_json(force=True)
    if not data.get("name"):
        return jsonify({"error": "Theme name is required"}), 400

    # Check for duplicate name
    lib = load_theme_library()
    if lib.get(data["name"]) is not None:
        return jsonify({"error": "Theme name already exists", "name": data["name"]}), 409

    try:
        theme = Theme.from_dict(data)
        save_custom_theme(theme)
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid theme data: {exc}"}), 400

    return jsonify({"status": "created", "name": theme.name}), 201


@theme_bp.route("/<name>", methods=["PUT"])
def theme_update(name):
    from src.themes.library import load_theme_library, save_custom_theme, _BUILTIN_PATH

    # Check if built-in — fail closed if we can't read the builtin file
    try:
        with open(_BUILTIN_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if name in raw.get("themes", {}):
            return jsonify({"error": "Cannot edit built-in theme", "name": name}), 403
    except Exception:
        return jsonify({"error": "Cannot verify theme status"}), 500

    data = request.get_json(force=True)
    data["name"] = name  # Ensure name matches URL

    from src.themes.models import Theme
    try:
        theme = Theme.from_dict(data)
        save_custom_theme(theme)
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid theme data: {exc}"}), 400

    return jsonify({"status": "updated", "name": name})


@theme_bp.route("/<name>", methods=["DELETE"])
def theme_delete(name):
    from src.themes.library import _BUILTIN_PATH, delete_custom_theme

    # Check if built-in — fail closed if we can't read the builtin file
    try:
        with open(_BUILTIN_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if name in raw.get("themes", {}):
            return jsonify({"error": "Cannot delete built-in theme"}), 403
    except Exception:
        return jsonify({"error": "Cannot verify theme status"}), 500

    try:
        delete_custom_theme(name)
    except FileNotFoundError:
        return jsonify({"error": "Custom theme not found", "name": name}), 404

    return jsonify({"status": "deleted", "name": name})


@theme_bp.route("/duplicate", methods=["POST"])
def theme_duplicate():
    from src.themes.library import load_theme_library, save_custom_theme
    from src.themes.models import Theme
    from dataclasses import asdict

    data = request.get_json(force=True)
    source_name = data.get("source_name", "")
    new_name = data.get("new_name", "")

    if not source_name or not new_name:
        return jsonify({"error": "source_name and new_name are required"}), 400

    lib = load_theme_library()
    source = lib.get(source_name)
    if source is None:
        return jsonify({"error": f"Source theme not found: {source_name}"}), 404

    # Check new name doesn't exist
    if lib.get(new_name) is not None:
        return jsonify({"error": "Theme name already exists", "name": new_name}), 409

    # Clone the theme with new name
    theme_dict = asdict(source)
    theme_dict["name"] = new_name
    new_theme = Theme.from_dict(theme_dict)
    save_custom_theme(new_theme)

    return jsonify({"status": "created", "name": new_name}), 201
