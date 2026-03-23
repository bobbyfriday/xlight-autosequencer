"""T019: Failing tests for librosa HPSS algorithms."""
from __future__ import annotations

import pytest
from src.analyzer.algorithms.librosa_hpss import LibrosaDrumsAlgorithm, LibrosaHarmonicAlgorithm
from src.analyzer.audio import load


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


class TestLibrosaDrumsAlgorithm:
    def test_produces_timing_track(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaDrumsAlgorithm().run(audio, sr)
        assert track is not None
        assert track.name == "drums"
        assert track.element_type == "percussion"

    def test_has_marks(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaDrumsAlgorithm().run(audio, sr)
        assert track.mark_count > 0

    def test_marks_sorted_ascending(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaDrumsAlgorithm().run(audio, sr)
        times = [m.time_ms for m in track.marks]
        assert times == sorted(times)


class TestLibrosaHarmonicAlgorithm:
    def test_produces_timing_track(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaHarmonicAlgorithm().run(audio, sr)
        assert track is not None
        assert track.name == "harmonic_peaks"
        assert track.element_type == "harmonic"

    def test_drums_has_more_marks_than_harmonic_for_beat_fixture(self, beat_audio):
        """A kick drum fixture should have more percussive marks than harmonic."""
        audio, sr = beat_audio
        drums = LibrosaDrumsAlgorithm().run(audio, sr)
        harmonic = LibrosaHarmonicAlgorithm().run(audio, sr)
        assert drums.mark_count >= harmonic.mark_count
