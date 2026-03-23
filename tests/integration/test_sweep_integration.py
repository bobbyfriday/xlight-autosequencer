"""005: Integration tests for the end-to-end parameter sweep pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.analyzer.result import TimingMark, TimingTrack
from src.analyzer.sweep import SweepConfig, SweepRunner, SweepReport


def _make_track(mark_count: int, interval_ms: int = 500) -> TimingTrack:
    marks = [TimingMark(time_ms=i * interval_ms, confidence=None) for i in range(mark_count)]
    return TimingTrack(
        name="qm_onsets_complex",
        algorithm_name="qm_onsets_complex",
        element_type="onset",
        marks=marks,
        quality_score=0.0,
    )


def _make_stem_set() -> MagicMock:
    stem_set = MagicMock()
    stem_set.sample_rate = 22050
    drums_arr = np.zeros(22050, dtype=np.float32)
    full_mix_arr = np.ones(22050, dtype=np.float32) * 0.5
    stem_set.get.side_effect = lambda name: (
        drums_arr if name == "drums" else full_mix_arr if name == "full_mix" else None
    )
    return stem_set


class TestSweepEndToEnd:
    def test_four_permutation_sweep_produces_ranked_report(self, tmp_path, beat_fixture_path):
        """2 stems × 2 sensitivity values = 4 permutations, end-to-end."""
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=["full_mix", "drums"],
            sweep_params={"sensitivity": [20, 80]},
            fixed_params={"dftype": 3},
        )

        call_count = [0]

        def fake_run(audio, sr):
            call_count[0] += 1
            n = [10, 15, 8, 20][min(call_count[0] - 1, 3)]
            return _make_track(n, interval_ms=500)

        mock_algo_cls = MagicMock()
        mock_algo_cls.return_value.run = fake_run
        mock_algo_cls.return_value.preferred_stem = "drums"
        mock_algo_cls.plugin_key = "qm-vamp-plugins:qm-onsetdetector"
        mock_algo_cls.preferred_stem = "drums"

        registry = {"qm_onsets_complex": mock_algo_cls}
        runner = SweepRunner(registry)
        stem_set = _make_stem_set()

        report = runner.run(str(beat_fixture_path), cfg, stem_set)

        # 4 results
        assert len(report.results) == 4

        # All have stem field
        for r in report.results:
            assert r.stem in {"full_mix", "drums"}

        # Ranked correctly
        scores = [r.quality_score for r in report.results]
        assert scores == sorted(scores, reverse=True)
        assert report.results[0].rank == 1
        assert report.results[-1].rank == 4

        # stems_tested matches config
        assert set(report.stems_tested) == {"full_mix", "drums"}

        # All quality scores are non-negative
        assert all(r.quality_score >= 0.0 for r in report.results)

    def test_json_round_trip(self, tmp_path, beat_fixture_path):
        """Report written to disk and loaded back is identical."""
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=["drums"],
            sweep_params={"sensitivity": [30, 70]},
            fixed_params={},
        )

        mock_algo_cls = MagicMock()
        mock_algo_cls.return_value.run.return_value = _make_track(12)
        mock_algo_cls.return_value.preferred_stem = "drums"
        mock_algo_cls.plugin_key = "qm-vamp-plugins:qm-onsetdetector"
        mock_algo_cls.preferred_stem = "drums"

        runner = SweepRunner({"qm_onsets_complex": mock_algo_cls})
        stem_set = _make_stem_set()
        report = runner.run(str(beat_fixture_path), cfg, stem_set)

        out_path = tmp_path / "report.json"
        report.write(str(out_path))
        loaded = SweepReport.read(str(out_path))

        assert loaded.algorithm == report.algorithm
        assert loaded.stems_tested == report.stems_tested
        assert len(loaded.results) == len(report.results)
        for orig, reloaded in zip(report.results, loaded.results):
            assert reloaded.stem == orig.stem
            assert reloaded.quality_score == pytest.approx(orig.quality_score, abs=1e-4)
            assert reloaded.mark_count == orig.mark_count
