"""Flask blueprint for per-song Creative Brief persistence (spec 047).

Provides GET/PUT endpoints for ``/brief/<source_hash>``. The Brief JSON is
stored alongside the audio file as ``<audio_stem>_brief.json``.

See ``specs/047-creative-brief/`` for schema and behavior.
"""
from __future__ import annotations

# TODO(047): implement brief_bp blueprint.  Skeleton — filled out in Phase 5.
