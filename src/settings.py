"""Installation-wide settings stored at ~/.xlight/settings.json."""
from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH: Path = Path.home() / ".xlight" / "settings.json"


def load_settings() -> dict:
    """Read ~/.xlight/settings.json and return its contents as a dict.

    Returns an empty dict if the file is missing or contains invalid JSON.
    """
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_settings(updates: dict) -> None:
    """Merge *updates* into ~/.xlight/settings.json, creating the file if needed."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_settings()
    existing.update(updates)
    SETTINGS_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def get_layout_path() -> Path | None:
    """Return the configured layout path, or None if not set."""
    value = load_settings().get("layout_path")
    if not value:
        return None
    return Path(value)
