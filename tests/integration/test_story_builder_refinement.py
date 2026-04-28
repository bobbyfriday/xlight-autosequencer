"""Integration tests for boundary-refinement wiring in build_song_story.

Exercises Step 15c of ``src/story/builder.py``: the call into
``src.story.boundary_refinement.refine_section_boundaries`` and the
plumbing that surfaces forced/free word marks + chorus body across the
Genius subprocess boundary.

The Genius subprocess is mocked via monkey-patching ``_try_genius_sections``
so the test runs without ``.venv-vamp`` / WhisperX / a real audio fixture.
The point of this test is the wiring, not the algorithm — algorithm
correctness is covered by ``tests/unit/test_boundary_refinement.py``.
"""
from __future__ import annotations

import pytest

from src.story import builder as builder_mod
from src.story.builder import build_song_story
from tests.fixtures.story_fixture import make_hierarchy_dict


AUDIO_PATH = "/tmp/fixture_song.mp3"


@pytest.fixture()
def hierarchy():
    return make_hierarchy_dict()


def _stub_genius_sections_factory(
    *,
    sections,
    free_words: list[dict] | None = None,
    forced_words: list[dict] | None = None,
    chorus_body: str | None = None,
    match_info: dict | None = None,
):
    """Build a stub for ``_try_genius_sections`` returning the supplied tuple."""
    def _stub(audio_path, duration_ms, *, override_artist=None, override_title=None):
        return (
            sections,
            match_info,
            free_words or [],
            forced_words or [],
            chorus_body,
        )
    return _stub


def test_flag_off_emits_empty_boundary_refinements_field(hierarchy, monkeypatch):
    """Default-off: every section gets boundary_refinements: [], no fix runs."""
    monkeypatch.setattr(builder_mod, "_try_genius_sections", _stub_genius_sections_factory(
        sections=None,
        free_words=[],
        forced_words=[],
        chorus_body=None,
    ))

    story = build_song_story(hierarchy, AUDIO_PATH)
    assert story["schema_version"] == "1.1.0"
    for sec in story["sections"]:
        assert "boundary_refinements" in sec
        assert sec["boundary_refinements"] == []


def test_flag_on_no_genius_data_still_emits_empty_field(hierarchy, monkeypatch):
    """Flag on but Genius returned nothing — every section still gets []."""
    monkeypatch.setattr(builder_mod, "_try_genius_sections", _stub_genius_sections_factory(
        sections=None,
        free_words=[],
        forced_words=[],
        chorus_body=None,
    ))

    story = build_song_story(hierarchy, AUDIO_PATH)
    for sec in story["sections"]:
        assert sec["boundary_refinements"] == []


def test_flag_on_fix3_fires_for_late_vocal_entry(hierarchy, monkeypatch):
    """Flag on with synthetic free_words showing a vocal section starts late.

    The fixture hierarchy contains multiple sections; we feed free_words
    consistent with one of them having its first transcribed word > 5 s
    after the section start. Fix 3 should split it.
    """

    # First, build with flag off to discover what sections the fixture
    # produces. Then we know which one to target with synthetic free_words.
    monkeypatch.setattr(builder_mod, "_try_genius_sections", _stub_genius_sections_factory(
        sections=None,
    ))

    baseline = build_song_story(hierarchy, AUDIO_PATH)

    # Pick a vocal section ≥ 10 s long so we can simulate a late entry.
    vocal_target = next(
        (
            s for s in baseline["sections"]
            if s["role"] in {"verse", "chorus", "pre_chorus", "post_chorus", "bridge"}
            and (s["end"] - s["start"]) >= 10.0
            and "instrumental" not in s["role"]
            and "break" not in s["role"]
        ),
        None,
    )
    if vocal_target is None:
        pytest.skip("fixture has no vocal section ≥ 10s — Fix 3 untriggerable")

    # First transcribed word lands 7 s after the section start.
    word_start_ms = int(round(vocal_target["start"] * 1000)) + 7000
    free_words = [
        {"label": "HELLO", "start_ms": word_start_ms, "end_ms": word_start_ms + 400},
        {"label": "WORLD", "start_ms": word_start_ms + 600, "end_ms": word_start_ms + 1000},
    ]

    monkeypatch.setattr(builder_mod, "_try_genius_sections", _stub_genius_sections_factory(
        sections=None,
        free_words=free_words,
        forced_words=[],
        chorus_body=None,
    ))
    refined = build_song_story(hierarchy, AUDIO_PATH)

    # Fix 3 should produce a new instrumental section preceding the vocal one.
    refinement_notes = [
        n
        for sec in refined["sections"]
        for n in sec.get("boundary_refinements", [])
    ]
    assert any(
        "first transcribed word" in n or "pre-vocal gap split off" in n
        for n in refinement_notes
    ), (
        f"expected Fix 3 note in refinements; got: {refinement_notes}"
    )

    # And there is at least one section with role=='instrumental' adjacent
    # to (or within) the original target span.
    has_synth_instrumental = any(
        s["role"] == "instrumental" for s in refined["sections"]
    )
    assert has_synth_instrumental, "expected a synthetic instrumental section after Fix 3"


def test_legacy_story_dict_section_from_dict_handles_missing_field(hierarchy, monkeypatch):
    """Section.from_dict tolerates legacy section dicts lacking the field."""
    from src.story.models import Section

    # Build a real story (flag off → no refinement notes added beyond []).
    monkeypatch.setattr(builder_mod, "_try_genius_sections", _stub_genius_sections_factory(
        sections=None,
    ))
    story = build_song_story(hierarchy, AUDIO_PATH)
    legacy_dict = dict(story["sections"][0])
    # Simulate a legacy story that predates the field.
    legacy_dict.pop("boundary_refinements", None)

    section = Section.from_dict(legacy_dict)
    assert section.boundary_refinements == []
    assert section.to_dict()["boundary_refinements"] == []
