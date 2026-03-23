"""T024: Tests for Vamp pYIN pitch algorithms — skipped if plugin not installed."""
from __future__ import annotations

import pytest
from tests.conftest import vamp_plugin_available
from src.analyzer.audio import load

pyin_available = pytest.mark.skipif(
    not vamp_plugin_available("pyin:pyin"),
    reason="pYIN Vamp plugin not installed",
)


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


@pyin_available
def test_pyin_notes_produces_track(beat_audio):
    from src.analyzer.algorithms.vamp_pitch import PYINNotesAlgorithm
    audio, sr = beat_audio
    track = PYINNotesAlgorithm().run(audio, sr)
    assert track is not None
    assert track.element_type == "melody"
    assert track.mark_count >= 0  # May be 0 for a beat-only fixture


@pyin_available
def test_pyin_pitch_changes_produces_track(beat_audio):
    from src.analyzer.algorithms.vamp_pitch import PYINPitchChangesAlgorithm
    audio, sr = beat_audio
    track = PYINPitchChangesAlgorithm().run(audio, sr)
    assert track is not None
    assert track.element_type == "melody"
