"""T018: Failing tests for librosa frequency band algorithms."""
from __future__ import annotations

import pytest
from src.analyzer.algorithms.librosa_bands import (
    LibrosaBassAlgorithm,
    LibrosaMidAlgorithm,
    LibrosaTrebleAlgorithm,
)
from src.analyzer.audio import load


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


class TestLibrosaBandAlgorithms:
    @pytest.mark.parametrize("AlgoClass,name,element_type", [
        (LibrosaBassAlgorithm, "bass", "frequency"),
        (LibrosaMidAlgorithm, "mid", "frequency"),
        (LibrosaTrebleAlgorithm, "treble", "frequency"),
    ])
    def test_produces_track_with_marks(self, beat_audio, AlgoClass, name, element_type):
        audio, sr = beat_audio
        track = AlgoClass().run(audio, sr)
        assert track is not None
        assert track.name == name
        assert track.element_type == element_type
        assert track.mark_count > 0

    @pytest.mark.parametrize("AlgoClass", [
        LibrosaBassAlgorithm, LibrosaMidAlgorithm, LibrosaTrebleAlgorithm
    ])
    def test_all_time_ms_are_ints(self, beat_audio, AlgoClass):
        audio, sr = beat_audio
        track = AlgoClass().run(audio, sr)
        for m in track.marks:
            assert isinstance(m.time_ms, int)

    @pytest.mark.parametrize("AlgoClass", [
        LibrosaBassAlgorithm, LibrosaMidAlgorithm, LibrosaTrebleAlgorithm
    ])
    def test_marks_sorted_ascending(self, beat_audio, AlgoClass):
        audio, sr = beat_audio
        track = AlgoClass().run(audio, sr)
        times = [m.time_ms for m in track.marks]
        assert times == sorted(times)

    def test_treble_has_more_marks_than_bass(self, beat_audio):
        """Treble fires more often than bass on a synthetic kick drum fixture."""
        audio, sr = beat_audio
        bass = LibrosaBassAlgorithm().run(audio, sr)
        treble = LibrosaTrebleAlgorithm().run(audio, sr)
        # Treble typically has shorter avg interval (higher density)
        assert treble.avg_interval_ms <= bass.avg_interval_ms
