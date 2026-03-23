"""T021: Tests for Vamp beat algorithms — skipped if plugins not installed."""
from __future__ import annotations

import pytest
from tests.conftest import vamp_plugin_available
from src.analyzer.audio import load

qm_available = pytest.mark.skipif(
    not vamp_plugin_available("qm-vamp-plugins:qm-barbeattracker"),
    reason="QM Vamp plugins not installed",
)
beatroot_available = pytest.mark.skipif(
    not vamp_plugin_available("beatroot-vamp:beatroot"),
    reason="BeatRoot Vamp plugin not installed",
)


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


@qm_available
def test_qm_beats_mark_count(beat_audio):
    from src.analyzer.algorithms.vamp_beats import QMBeatAlgorithm
    audio, sr = beat_audio
    track = QMBeatAlgorithm().run(audio, sr)
    assert track is not None
    assert 15 <= track.mark_count <= 25


@qm_available
def test_qm_bars_fewer_than_beats(beat_audio):
    from src.analyzer.algorithms.vamp_beats import QMBeatAlgorithm, QMBarAlgorithm
    audio, sr = beat_audio
    beats = QMBeatAlgorithm().run(audio, sr)
    bars = QMBarAlgorithm().run(audio, sr)
    assert bars.mark_count < beats.mark_count


@beatroot_available
def test_beatroot_mark_count(beat_audio):
    from src.analyzer.algorithms.vamp_beats import BeatRootAlgorithm
    audio, sr = beat_audio
    track = BeatRootAlgorithm().run(audio, sr)
    assert track is not None
    assert 15 <= track.mark_count <= 25
