"""T022: Tests for Vamp onset algorithms — skipped if plugins not installed."""
from __future__ import annotations

import pytest
from tests.conftest import vamp_plugin_available
from src.analyzer.audio import load

qm_onset_available = pytest.mark.skipif(
    not vamp_plugin_available("qm-vamp-plugins:qm-onsetdetector"),
    reason="QM onset Vamp plugin not installed",
)


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


@qm_onset_available
def test_complex_produces_marks(beat_audio):
    from src.analyzer.algorithms.vamp_onsets import QMOnsetComplexAlgorithm
    audio, sr = beat_audio
    track = QMOnsetComplexAlgorithm().run(audio, sr)
    assert track is not None
    assert track.mark_count > 0


@qm_onset_available
def test_hfc_produces_marks(beat_audio):
    from src.analyzer.algorithms.vamp_onsets import QMOnsetHFCAlgorithm
    audio, sr = beat_audio
    track = QMOnsetHFCAlgorithm().run(audio, sr)
    assert track is not None
    assert track.mark_count > 0


@qm_onset_available
def test_phase_produces_marks(beat_audio):
    from src.analyzer.algorithms.vamp_onsets import QMOnsetPhaseAlgorithm
    audio, sr = beat_audio
    track = QMOnsetPhaseAlgorithm().run(audio, sr)
    assert track is not None
    assert track.mark_count > 0
