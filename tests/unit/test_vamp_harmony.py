"""T025: Tests for Vamp harmony algorithms — skipped if plugins not installed."""
from __future__ import annotations

import pytest
from tests.conftest import vamp_plugin_available
from src.analyzer.audio import load

nnls_available = pytest.mark.skipif(
    not vamp_plugin_available("nnls-chroma:chordino"),
    reason="NNLS Chroma / Chordino Vamp plugin not installed",
)


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


@nnls_available
def test_chord_changes_produces_track(beat_audio):
    from src.analyzer.algorithms.vamp_harmony import ChordinoAlgorithm
    audio, sr = beat_audio
    track = ChordinoAlgorithm().run(audio, sr)
    assert track is not None
    assert track.element_type == "harmonic"


@nnls_available
def test_chroma_peaks_more_marks_than_chords(beat_audio):
    from src.analyzer.algorithms.vamp_harmony import ChordinoAlgorithm, NNLSChromaAlgorithm
    audio, sr = beat_audio
    chords = ChordinoAlgorithm().run(audio, sr)
    chroma = NNLSChromaAlgorithm().run(audio, sr)
    assert chroma.mark_count >= chords.mark_count
