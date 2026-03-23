"""T012: Unit tests for quality scorer in src/analyzer/scorer.py — RED before T011."""
from __future__ import annotations

import pytest
from src.analyzer.result import TimingMark, TimingTrack
from src.analyzer.scorer import score_track


def _make_track_with_interval(avg_interval_ms: int, n_marks: int = 20) -> TimingTrack:
    """Create a perfectly regular track with the given average interval."""
    marks = [TimingMark(i * avg_interval_ms, None) for i in range(n_marks)]
    return TimingTrack(
        name="test", algorithm_name="test", element_type="beat",
        marks=marks, quality_score=0.0  # will be overwritten by scorer
    )


class TestDensityScore:
    def test_ideal_range_500ms_scores_near_1(self):
        track = _make_track_with_interval(500)
        score = score_track(track)
        assert score >= 0.85

    def test_very_dense_under_100ms_scores_near_0(self):
        track = _make_track_with_interval(50)
        score = score_track(track)
        assert score <= 0.15

    def test_sparse_above_5000ms_scores_around_half(self):
        track = _make_track_with_interval(6000, n_marks=5)
        score = score_track(track)
        assert 0.3 <= score <= 0.7

    def test_250ms_scores_above_threshold(self):
        track = _make_track_with_interval(250)
        score = score_track(track)
        assert score >= 0.7

    def test_1000ms_scores_high(self):
        track = _make_track_with_interval(1000)
        score = score_track(track)
        assert score >= 0.8


class TestRegularityScore:
    def test_perfectly_regular_beat_higher_than_erratic_onset(self):
        regular = _make_track_with_interval(500, n_marks=20)
        # Erratic: random intervals between 50ms and 950ms, avg ~500ms
        rng = [50, 950, 100, 900, 200, 800, 150, 850, 300, 700,
               250, 750, 400, 600, 350, 650, 450, 550, 500, 500]
        marks = []
        t = 0
        for interval in rng:
            marks.append(TimingMark(t, None))
            t += interval
        erratic = TimingTrack("e", "e", "onset", marks, 0.0)

        reg_score = score_track(regular)
        err_score = score_track(erratic)
        assert reg_score > err_score


class TestEdgeCases:
    def test_empty_track_returns_zero(self):
        track = TimingTrack("empty", "x", "beat", [], 0.0)
        score = score_track(track)
        assert score == pytest.approx(0.0)

    def test_single_mark_returns_zero(self):
        track = TimingTrack("one", "x", "beat", [TimingMark(500, None)], 0.0)
        score = score_track(track)
        assert score == pytest.approx(0.0)

    def test_score_in_range_0_to_1(self):
        for interval in [50, 100, 250, 500, 1000, 2000, 5000]:
            track = _make_track_with_interval(interval)
            score = score_track(track)
            assert 0.0 <= score <= 1.0, f"Score out of range for interval={interval}: {score}"
