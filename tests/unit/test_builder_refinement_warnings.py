"""Unit tests for §7 — Step 15c capability-skip warnings.

OpenSpec change ``lyric-anchored-boundary-refinement`` §7 requires
``build_song_story`` to emit one warning per skipped boundary-refinement
fix per song into ``story["refinement_warnings"]`` (which the analyze-step
API merges into ``HierarchyResult.warnings``). Per-section non-fires
(a section that simply doesn't match a fix's preconditions) SHALL NOT
produce warnings — those are silent.

These tests exercise the builder's Step 15c warning emission directly
by mocking ``_try_genius_sections`` to vary capability availability
(chorus body, free word marks).
"""
from __future__ import annotations

import re

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
    sections=None,
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


# ── Field always present ────────────────────────────────────────────────────────

def test_story_always_has_refinement_warnings_field(hierarchy, monkeypatch):
    """``refinement_warnings`` is always present in the story dict.

    With no Genius data and no free words, Fix 2 and Fix 2/3 emit their
    capability-skip warnings (since 2026-04-28 the refinement step is
    always-on; no flag).
    """
    monkeypatch.setattr(
        builder_mod, "_try_genius_sections",
        _stub_genius_sections_factory(),
    )
    story = build_song_story(hierarchy, AUDIO_PATH)
    assert "refinement_warnings" in story
    # No chorus body → Fix 2 skip; no free words → Fix 2/3 skip.
    assert any("Fix 2" in w for w in story["refinement_warnings"])


def test_story_full_capabilities_emits_no_skip_warnings(hierarchy, monkeypatch):
    """Full capabilities (chorus body + free words): no skip warnings."""
    free_words = [{"label": "HELLO", "start_ms": 1000, "end_ms": 1400}]
    monkeypatch.setattr(
        builder_mod, "_try_genius_sections",
        _stub_genius_sections_factory(
            chorus_body="DJ play a Christmas song",
            free_words=free_words,
        ),
    )
    story = build_song_story(hierarchy, AUDIO_PATH)
    assert story["refinement_warnings"] == []


# ── Skip-warning emission ───────────────────────────────────────────────────────

def test_no_chorus_body_emits_fix2_skip_warning(hierarchy, monkeypatch):
    """When Genius produced no chorus body but free words exist → Fix 2 skipped."""
    free_words = [{"label": "HELLO", "start_ms": 1000, "end_ms": 1400}]
    monkeypatch.setattr(
        builder_mod, "_try_genius_sections",
        _stub_genius_sections_factory(
            chorus_body=None,
            free_words=free_words,
        ),
    )
    story = build_song_story(hierarchy, AUDIO_PATH)
    warnings = story["refinement_warnings"]

    # Exactly one Fix-2 skip warning, matching the spec's regex.
    fix2_warnings = [w for w in warnings if re.search(
        r"boundary refinement skipped: Fix 2.*no chorus body from Genius", w
    )]
    assert len(fix2_warnings) == 1, (
        f"expected exactly one Fix-2 'no chorus body' warning, got {warnings}"
    )


def test_no_free_words_emits_fix23_skip_warning(hierarchy, monkeypatch):
    """When free word marks are empty → Fix 2/3 skipped."""
    monkeypatch.setattr(
        builder_mod, "_try_genius_sections",
        _stub_genius_sections_factory(
            chorus_body="DJ play a Christmas song",
            free_words=[],
        ),
    )
    story = build_song_story(hierarchy, AUDIO_PATH)
    warnings = story["refinement_warnings"]
    fix23_warnings = [
        w for w in warnings if "Fix 2/3" in w and "no free-transcription" in w
    ]
    assert len(fix23_warnings) == 1, (
        f"expected one Fix-2/3 'no free-transcription' warning, got {warnings}"
    )


def test_both_capabilities_missing_emits_two_warnings(hierarchy, monkeypatch):
    """Chorus body missing AND free words missing → two distinct skip warnings."""
    monkeypatch.setattr(
        builder_mod, "_try_genius_sections",
        _stub_genius_sections_factory(
            chorus_body=None,
            free_words=[],
        ),
    )
    story = build_song_story(hierarchy, AUDIO_PATH)
    warnings = story["refinement_warnings"]
    assert len(warnings) == 2, (
        f"expected exactly two skip warnings (one per missing capability), got {warnings}"
    )
    assert any("Fix 2" in w and "no chorus body" in w for w in warnings)
    assert any("Fix 2/3" in w and "no free-transcription" in w for w in warnings)


# ── One-warning-per-skipped-fix-per-song (NOT per section) ──────────────────────

def test_warnings_are_per_song_not_per_section(hierarchy, monkeypatch):
    """The fixture has 4 sections; the warning list still has exactly one
    Fix-2 entry — proving emission is per song, not per section."""
    free_words = [{"label": "HELLO", "start_ms": 1000, "end_ms": 1400}]
    monkeypatch.setattr(
        builder_mod, "_try_genius_sections",
        _stub_genius_sections_factory(
            chorus_body=None,
            free_words=free_words,
        ),
    )
    story = build_song_story(hierarchy, AUDIO_PATH)

    # The fixture must produce > 1 section for this assertion to be meaningful.
    assert len(story["sections"]) > 1
    # Only one warning total even though many sections exist.
    assert len(story["refinement_warnings"]) == 1


# ── Per-section non-fires are silent ────────────────────────────────────────────

def test_per_section_non_fires_do_not_emit_warnings(hierarchy, monkeypatch):
    """A section whose preconditions for a fix simply don't apply (e.g., a
    bridge whose transcribed words don't match the chorus hook) is a normal
    no-op — no warning. This is distinct from a capability skip."""
    # Provide a chorus body and free words. The fixture's bridges (if any)
    # won't contain the hook "DJ play christmas song" — that's a per-section
    # non-fire, which must NOT produce a warning.
    chorus_body = "DJ play a Christmas song wanna start dancing"
    free_words = [
        {"label": "completely", "start_ms": 1000, "end_ms": 1400},
        {"label": "different", "start_ms": 1500, "end_ms": 1900},
        {"label": "lyrics", "start_ms": 2000, "end_ms": 2400},
    ]
    monkeypatch.setattr(
        builder_mod, "_try_genius_sections",
        _stub_genius_sections_factory(
            chorus_body=chorus_body,
            free_words=free_words,
        ),
    )
    story = build_song_story(hierarchy, AUDIO_PATH)
    # No skip warnings — capabilities were available; the fixes simply
    # didn't fire on any section.
    assert story["refinement_warnings"] == [], (
        f"expected no skip warnings when capabilities are present "
        f"(per-section non-fires are silent); got {story['refinement_warnings']}"
    )


# ── refine_section_boundaries (the function) is silent on chorus_body=None ──────

def test_refine_function_with_no_chorus_body_does_not_raise() -> None:
    """The function itself does NOT emit warnings — it returns notes that
    describe what fired. The CALLER (builder.py Step 15c) is responsible
    for emitting capability-skip warnings to the song-level list. This test
    locks in that contract: passing chorus_body=None is a normal call that
    just causes Fix 2 to skip per-section."""
    from src.story.boundary_refinement import refine_section_boundaries

    bridge = {
        "id": "s0", "role": "bridge", "label": "Bridge",
        "start": 100.0, "end": 130.0, "start_ms": 100_000, "end_ms": 130_000,
    }
    out, notes = refine_section_boundaries(
        [bridge], forced_words=[], free_words=[], chorus_body=None
    )
    # Section list unchanged, no relabel notes.
    assert out[0]["role"] == "bridge"
    assert not any("relabel" in n for n in notes)
    # The boundary_refinements field is always present (per §2).
    assert out[0]["boundary_refinements"] == []
