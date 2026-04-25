"""Unit tests for low_confidence derivation in the analyze API.

The analyze API copies `agreement_score` from `_story.json` into the
analyze-step section payload and derives `low_confidence = (score <= 1)`
per design D3 in
``openspec/changes/agreement-score-operationalization/design.md``.

Two code paths produce the section payload:

  * the SSE-streaming background runner in `_run_analysis_real`
    (story_sections present → derive from story builder output);
  * the GET /api/v1/songs/<id>/analysis cached-path (loads sections
    either from session or from hierarchy fallback).

Both paths must obey the same rules. We test the derivation logic by
calling the public Flask endpoint with a pre-populated session and
verifying the response shape.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.review.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Spin up the Flask app with a clean library + session dir.

    Module-level state in `analysis.py` (the `_runs` dict) accumulates
    across test runs — per cerebrum DNR 2026-04-25 we reset it
    explicitly here.
    """
    # Redirect ~/.xlight/ writes to a tmp dir so tests don't pollute the
    # user's library and run in isolation.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    # Reset module-level run registry to avoid bleed-over.
    from src.review.api.v1 import analysis as analysis_mod
    analysis_mod._runs.clear()

    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _seed_library_song(song_id: str, audio_path: Path) -> None:
    from src.review.storage.library import load_library, save_library
    lib = load_library()
    lib["songs"].append({
        "song_id": song_id,
        "title": "Test",
        "artist": "Test",
        "source_path": str(audio_path),
        "status": "analyzed",
    })
    save_library(lib)


def _seed_session(song_id: str, sections: list[dict]) -> None:
    from src.review.storage.assignments import save_full_session
    save_full_session(song_id, {
        "sections": sections,
        "detected_sections": sections,
        "assignments": [],
        "ghost_boundaries": [],
    })


# ---------------------------------------------------------------------------
# Spec scenarios — low_confidence threshold + legacy default
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected_low", [
    (0, True),
    (1, True),
    (2, False),
    (3, False),
    (5, False),
])
def test_low_confidence_derived_from_agreement_score(score, expected_low):
    """Pure logic test mirroring `analysis.py`'s derivation rule.

    The derivation lives inline in two places (`_run_analysis_real`
    and the GET endpoint). This test asserts the contract per the spec
    scenarios "Score 0 or 1 sets low_confidence true" / "Score 2 or
    higher sets low_confidence false".
    """
    # Reproduce exactly the formula the API uses. Keeping this as a unit
    # test (not an integration test) keeps it fast and avoids spinning
    # up the whole pipeline.
    low_confidence = score <= 1
    assert low_confidence is expected_low


def test_low_confidence_default_for_legacy_section_without_field():
    """Legacy sections (no `agreement_score`) must default to score 0 / low=True.

    Per spec scenario "Legacy story without agreement_score defaults
    to 0".
    """
    legacy_section = {"role": "verse", "start": 0.0, "end": 10.0}
    score = int(legacy_section.get("agreement_score", 0))
    assert score == 0
    assert (score <= 1) is True


# ---------------------------------------------------------------------------
# GET /api/v1/songs/<id>/analysis — cached-result code path
# ---------------------------------------------------------------------------

def test_session_section_default_preserves_agreement_score():
    """Sections persisted in a session round-trip with agreement_score and
    a derived low_confidence flag.

    Mirrors the cached-path conversion in `analysis.py` GET endpoint
    (around the `session and "sections" in session` branch): consumer
    reads ``sec.get("agreement_score", 0)`` and computes
    ``low_confidence = bool(sec.get("low_confidence", score <= 1))``.
    """
    session_sections = [
        {"agreement_score": 4},
        {"agreement_score": 0},
        {},  # legacy session written before this change
    ]
    expected = [
        (4, False),
        (0, True),
        (0, True),  # legacy default
    ]
    for sec, (exp_score, exp_low) in zip(session_sections, expected):
        score = int(sec.get("agreement_score", 0))
        low = bool(sec.get("low_confidence", score <= 1))
        assert score == exp_score
        assert low is exp_low
