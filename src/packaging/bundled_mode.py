"""Detect whether the backend is running inside a packaged .app.

Single source of truth for the `XLIGHT_PACKAGED=1` env-var check and for
reading the packaging manifest that Tauri bundles into Contents/Resources/.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def is_bundled() -> bool:
    """True when launched as a Tauri sidecar inside a packaged .app."""
    return os.environ.get("XLIGHT_PACKAGED") == "1"


def _resource_dir() -> Path | None:
    """Return the Contents/Resources directory, or None in dev mode.

    Inside a PyInstaller onedir bundle `sys._MEIPASS` points at the
    extracted frozen bundle root. Tauri copies packaging-manifest.json into
    the .app's Resources directory, which PyInstaller then surfaces via
    `sys._MEIPASS` at runtime.
    """
    if not is_bundled():
        return None
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is None:
        return None
    return Path(meipass)


def get_manifest() -> dict | None:
    """Load packaging-manifest.json from the bundle, or return None in dev."""
    base = _resource_dir()
    if base is None:
        return None
    candidate = base / "packaging-manifest.json"
    if not candidate.is_file():
        return None
    try:
        return json.loads(candidate.read_text())
    except (OSError, json.JSONDecodeError):
        return None
