"""T017: Failing tests for librosa beat algorithms."""
from __future__ import annotations

from pathlib import Path

import pytest
from src.analyzer.algorithms.librosa_beats import LibrosaBeatAlgorithm, LibrosaBarAlgorithm
from src.analyzer.audio import load


@pytest.fixture(scope="module")
def beat_audio(beat_fixture_path):
    audio, sr, _ = load(str(beat_fixture_path))
    return audio, sr


class TestLibrosaBeatAlgorithm:
    def test_produces_timing_track(self, beat_audio):
        audio, sr = beat_audio
        algo = LibrosaBeatAlgorithm()
        track = algo.run(audio, sr)
        assert track is not None
        assert track.name == "librosa_beats"
        assert track.element_type == "beat"

    def test_mark_count_approx_20_for_120bpm_10s(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaBeatAlgorithm().run(audio, sr)
        # 120 BPM × 10s = 20 beats ± 3 tolerance
        assert 15 <= track.mark_count <= 25

    def test_all_time_ms_are_ints(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaBeatAlgorithm().run(audio, sr)
        for m in track.marks:
            assert isinstance(m.time_ms, int)

    def test_marks_sorted_ascending(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaBeatAlgorithm().run(audio, sr)
        times = [m.time_ms for m in track.marks]
        assert times == sorted(times)

    def test_deterministic(self, beat_audio):
        audio, sr = beat_audio
        t1 = LibrosaBeatAlgorithm().run(audio, sr)
        t2 = LibrosaBeatAlgorithm().run(audio, sr)
        assert [m.time_ms for m in t1.marks] == [m.time_ms for m in t2.marks]

    def test_avg_interval_near_500ms(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaBeatAlgorithm().run(audio, sr)
        # 120 BPM = 500ms per beat
        assert 400 <= track.avg_interval_ms <= 600


class TestLibrosaBarAlgorithm:
    def test_produces_timing_track(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaBarAlgorithm().run(audio, sr)
        assert track is not None
        assert track.name == "librosa_bars"
        assert track.element_type == "bar"

    def test_fewer_marks_than_beats(self, beat_audio):
        audio, sr = beat_audio
        beats = LibrosaBeatAlgorithm().run(audio, sr)
        bars = LibrosaBarAlgorithm().run(audio, sr)
        assert bars.mark_count < beats.mark_count

    def test_mark_count_approx_5_for_120bpm_10s(self, beat_audio):
        audio, sr = beat_audio
        track = LibrosaBarAlgorithm().run(audio, sr)
        # 120 BPM, 4/4 → 5 bars in 10s ± 3
        assert 2 <= track.mark_count <= 8
