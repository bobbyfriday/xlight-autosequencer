"""GET /api/v1/themes — built-in theme catalog for the x-onset frontend (T041)."""
from __future__ import annotations

from flask import jsonify

from . import api_v1

# Built-in theme catalog shaped per contracts/themes.md.
# Each Section kind ("intro", "verse", "chorus", "solo", "bridge", "outro", "unknown")
# must appear in at least one theme's default_for_kinds (FR-012a).
_BUILTIN_THEMES: list[dict] = [
    {
        "theme_id": "shimmer-wash",
        "name": "Shimmer Wash",
        "description": "Slow color drift with micro-sparkle. Floats gently — great for intros and outros.",
        "accent": "#4ade80",
        "swatches": ["#4ade80", "#7eebd1", "#f5f5f0", "#1a1a20"],
        "default_for_kinds": ["intro", "outro"],
    },
    {
        "theme_id": "driving-pulse",
        "name": "Driving Pulse",
        "description": "Warm strobe with beat-tight color shifts. Locks to the kick drum. Great for verses.",
        "accent": "#d97757",
        "swatches": ["#d97757", "#f5a623", "#f5f5f0", "#111114"],
        "default_for_kinds": ["verse"],
    },
    {
        "theme_id": "peak-flash",
        "name": "Peak Flash",
        "description": "High-contrast whiteout hits on every impact. Built for choruses and drops.",
        "accent": "#facc15",
        "swatches": ["#facc15", "#fb923c", "#f5f5f0", "#0d0d10"],
        "default_for_kinds": ["chorus"],
    },
    {
        "theme_id": "solo-chase",
        "name": "Solo Chase",
        "description": "Single-color ribbon chase that follows note onsets. Ideal for instrument solos.",
        "accent": "#38bdf8",
        "swatches": ["#38bdf8", "#818cf8", "#f5f5f0", "#0d1020"],
        "default_for_kinds": ["solo"],
    },
    {
        "theme_id": "bridge-burn",
        "name": "Bridge Burn",
        "description": "Slow build through warm oranges and reds. Tension for bridges and transitions.",
        "accent": "#f97316",
        "swatches": ["#f97316", "#ef4444", "#fde68a", "#14040a"],
        "default_for_kinds": ["bridge"],
    },
    {
        "theme_id": "neutral-glow",
        "name": "Neutral Glow",
        "description": "Soft white warm glow with gentle pulse. Works everywhere — the safe default.",
        "accent": "#e2e8f0",
        "swatches": ["#e2e8f0", "#cbd5e1", "#f8fafc", "#0f172a"],
        "default_for_kinds": ["unknown"],
    },
]

_SCHEMA_VERSION = 1


@api_v1.route("/themes", methods=["GET"])
def get_themes():
    return jsonify({
        "schema_version": _SCHEMA_VERSION,
        "themes": _BUILTIN_THEMES,
    }), 200
