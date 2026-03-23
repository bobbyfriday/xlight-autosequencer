"""T023: Tests for Vamp structure algorithms — skipped if plugins not installed."""
from __future__ import annotations

import pytest
from tests.conftest import vamp_plugin_available
from src.analyzer.audio import load

qm_seg_available = pytest.mark.skipif(
    not vamp_plugin_available("qm-vamp-plugins:qm-segmenter"),
    reason="QM segmenter Vamp plugin not installed",
)
qm_tempo_available = pytest.mark.skipif(
    not vamp_plugin_available("qm-vamp-plugins:qm-tempotracker"),
    reason="QM tempo Vamp plugin not installed",
)


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


@qm_seg_available
def test_qm_segments_produces_track(beat_audio):
    from src.analyzer.algorithms.vamp_structure import QMSegmenterAlgorithm
    audio, sr = beat_audio
    track = QMSegmenterAlgorithm().run(audio, sr)
    assert track is not None
    assert track.element_type == "structure"
    assert 1 <= track.mark_count <= 20


@qm_tempo_available
def test_qm_tempo_produces_track(beat_audio):
    from src.analyzer.algorithms.vamp_structure import QMTempoAlgorithm
    audio, sr = beat_audio
    track = QMTempoAlgorithm().run(audio, sr)
    assert track is not None
    assert track.element_type == "tempo"
