"""T009: Unit tests for data classes in src/analyzer/result.py — RED before T008."""
from __future__ import annotations

import pytest
from src.analyzer.result import (
    AnalysisAlgorithm,
    AnalysisResult,
    TimingMark,
    TimingTrack,
)


class TestTimingMark:
    def test_create_with_confidence(self):
        m = TimingMark(time_ms=500, confidence=0.9)
        assert m.time_ms == 500
        assert m.confidence == pytest.approx(0.9)

    def test_create_without_confidence(self):
        m = TimingMark(time_ms=1000, confidence=None)
        assert m.time_ms == 1000
        assert m.confidence is None

    def test_time_ms_is_int(self):
        m = TimingMark(time_ms=250, confidence=None)
        assert isinstance(m.time_ms, int)

    def test_equality(self):
        assert TimingMark(500, 0.9) == TimingMark(500, 0.9)
        assert TimingMark(500, 0.9) != TimingMark(501, 0.9)


class TestTimingTrack:
    def _make_track(self, marks=None, quality_score=0.75):
        if marks is None:
            marks = [TimingMark(100, None), TimingMark(600, None), TimingMark(1100, None)]
        return TimingTrack(
            name="test_beats",
            algorithm_name="librosa_beats",
            element_type="beat",
            marks=marks,
            quality_score=quality_score,
        )

    def test_basic_fields(self):
        track = self._make_track()
        assert track.name == "test_beats"
        assert track.algorithm_name == "librosa_beats"
        assert track.element_type == "beat"
        assert track.quality_score == pytest.approx(0.75)

    def test_mark_count_derived(self):
        track = self._make_track()
        assert track.mark_count == 3

    def test_avg_interval_ms_derived(self):
        # marks at 100, 600, 1100 → intervals 500, 500 → avg 500
        track = self._make_track()
        assert track.avg_interval_ms == 500

    def test_avg_interval_ms_single_mark(self):
        track = self._make_track(marks=[TimingMark(500, None)])
        assert track.avg_interval_ms == 0

    def test_avg_interval_ms_empty(self):
        track = self._make_track(marks=[])
        assert track.avg_interval_ms == 0
        assert track.mark_count == 0

    def test_marks_sorted_ascending(self):
        unsorted = [TimingMark(600, None), TimingMark(100, None), TimingMark(300, None)]
        track = TimingTrack(
            name="t", algorithm_name="a", element_type="beat",
            marks=unsorted, quality_score=0.5
        )
        times = [m.time_ms for m in track.marks]
        assert times == sorted(times)


class TestAnalysisAlgorithm:
    def test_create(self):
        algo = AnalysisAlgorithm(
            name="librosa_beats",
            element_type="beat",
            library="librosa 0.10.1",
            plugin_key=None,
            parameters={"hop_length": 512},
        )
        assert algo.name == "librosa_beats"
        assert algo.plugin_key is None
        assert algo.parameters["hop_length"] == 512

    def test_vamp_plugin_key(self):
        algo = AnalysisAlgorithm(
            name="qm_beats",
            element_type="beat",
            library="vamp + qm-vamp-plugins",
            plugin_key="qm-vamp-plugins:qm-barbeattracker:beats",
            parameters={},
        )
        assert algo.plugin_key == "qm-vamp-plugins:qm-barbeattracker:beats"


class TestAnalysisResult:
    def test_create(self):
        algo = AnalysisAlgorithm("a", "beat", "librosa 0.10", None, {})
        mark = TimingMark(500, None)
        track = TimingTrack("beats", "a", "beat", [mark], 0.9)
        result = AnalysisResult(
            schema_version="1.0",
            source_file="/path/to/song.wav",
            filename="song.wav",
            duration_ms=10000,
            sample_rate=22050,
            estimated_tempo_bpm=120.0,
            run_timestamp="2026-03-22T10:00:00Z",
            algorithms=[algo],
            timing_tracks=[track],
        )
        assert result.schema_version == "1.0"
        assert len(result.timing_tracks) == 1
        assert result.timing_tracks[0].name == "beats"
