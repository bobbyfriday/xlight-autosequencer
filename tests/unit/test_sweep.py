"""005: Tests for SweepConfig, SweepRunner, SweepReport."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.analyzer.result import TimingMark, TimingTrack
from src.analyzer.sweep import (
    PermutationResult,
    SweepConfig,
    SweepReport,
    SweepRunner,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_track(mark_count: int, interval_ms: int = 500) -> TimingTrack:
    marks = [TimingMark(time_ms=i * interval_ms, confidence=None) for i in range(mark_count)]
    return TimingTrack(
        name="test_algo",
        algorithm_name="test_algo",
        element_type="beat",
        marks=marks,
        quality_score=0.0,
    )


def _write_sweep_config(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# SweepConfig
# ---------------------------------------------------------------------------

class TestSweepConfig:
    def test_from_file_valid(self, tmp_path):
        cfg_path = tmp_path / "sweep.json"
        _write_sweep_config(cfg_path, {
            "algorithm": "qm_onsets_complex",
            "stems": ["full_mix", "drums"],
            "sweep": {"sensitivity": [20, 50, 80]},
            "fixed": {"dftype": 3},
        })
        cfg = SweepConfig.from_file(str(cfg_path))
        assert cfg.algorithm == "qm_onsets_complex"
        assert cfg.stems == ["full_mix", "drums"]
        assert cfg.sweep_params == {"sensitivity": [20, 50, 80]}
        assert cfg.fixed_params == {"dftype": 3}

    def test_from_file_missing_algorithm_raises(self, tmp_path):
        cfg_path = tmp_path / "sweep.json"
        _write_sweep_config(cfg_path, {"sweep": {"sensitivity": [20]}})
        with pytest.raises((KeyError, ValueError)):
            SweepConfig.from_file(str(cfg_path))

    def test_from_file_key_in_both_sweep_and_fixed_raises(self, tmp_path):
        cfg_path = tmp_path / "sweep.json"
        _write_sweep_config(cfg_path, {
            "algorithm": "qm_onsets_complex",
            "sweep": {"dftype": [0, 3]},
            "fixed": {"dftype": 3},
        })
        with pytest.raises(ValueError, match="dftype"):
            SweepConfig.from_file(str(cfg_path))

    def test_permutations_no_stems(self):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=[],
            sweep_params={"sensitivity": [20, 50, 80]},
            fixed_params={"dftype": 3},
        )
        perms = list(cfg.permutations(default_stem="drums"))
        # 3 sensitivity values, no stem sweep
        assert len(perms) == 3
        stems_seen = {stem for stem, _ in perms}
        assert stems_seen == {"drums"}
        params_seen = [params for _, params in perms]
        assert {"sensitivity": 20, "dftype": 3} in params_seen
        assert {"sensitivity": 80, "dftype": 3} in params_seen

    def test_permutations_with_stems(self):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=["full_mix", "drums"],
            sweep_params={"sensitivity": [20, 50, 80]},
            fixed_params={},
        )
        perms = list(cfg.permutations(default_stem="drums"))
        # 2 stems × 3 sensitivity = 6
        assert len(perms) == 6
        stems_seen = {stem for stem, _ in perms}
        assert stems_seen == {"full_mix", "drums"}

    def test_permutation_count_with_stems(self):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=["full_mix", "drums"],
            sweep_params={"sensitivity": [20, 50, 80], "whiten": [0, 1]},
            fixed_params={},
        )
        assert cfg.permutation_count(default_stem="drums") == 2 * 3 * 2  # 12

    def test_permutation_count_no_stems(self):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=[],
            sweep_params={"sensitivity": [20, 50, 80]},
            fixed_params={},
        )
        assert cfg.permutation_count(default_stem="drums") == 3

    def test_validate_invalid_stem_name(self):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=["invalid_stem"],
            sweep_params={"sensitivity": [50]},
            fixed_params={},
        )
        mock_discovery = MagicMock()
        mock_discovery.validate_params.return_value = []
        errors = cfg.validate("qm-vamp-plugins:qm-onsetdetector", mock_discovery)
        assert any("invalid_stem" in e for e in errors)

    def test_validate_invalid_param_value(self):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=[],
            sweep_params={"sensitivity": [999]},  # out of range
            fixed_params={},
        )
        mock_discovery = MagicMock()
        mock_discovery.validate_params.return_value = ["sensitivity out of range"]
        errors = cfg.validate("qm-vamp-plugins:qm-onsetdetector", mock_discovery)
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# SweepReport serialisation
# ---------------------------------------------------------------------------

class TestSweepReport:
    def _make_report(self) -> SweepReport:
        track = _make_track(10)
        results = [
            PermutationResult(rank=1, stem="drums", parameters={"sensitivity": 50},
                              quality_score=0.8, mark_count=10, avg_interval_ms=500, track=track),
            PermutationResult(rank=2, stem="full_mix", parameters={"sensitivity": 20},
                              quality_score=0.5, mark_count=8, avg_interval_ms=600, track=track),
        ]
        return SweepReport(
            schema_version="1.0",
            audio_file="/tmp/song.wav",
            algorithm="qm_onsets_complex",
            plugin_key="qm-vamp-plugins:qm-onsetdetector",
            stems_tested=["drums", "full_mix"],
            sweep_params={"sensitivity": [20, 50]},
            fixed_params={},
            permutation_count=2,
            generated_at="2026-03-22T00:00:00Z",
            results=results,
        )

    def test_to_dict_includes_stems_tested(self):
        report = self._make_report()
        d = report.to_dict()
        assert d["stems_tested"] == ["drums", "full_mix"]

    def test_to_dict_includes_stem_on_each_result(self):
        report = self._make_report()
        d = report.to_dict()
        assert d["results"][0]["stem"] == "drums"
        assert d["results"][1]["stem"] == "full_mix"

    def test_round_trip(self, tmp_path):
        report = self._make_report()
        out = tmp_path / "report.json"
        report.write(str(out))
        loaded = SweepReport.read(str(out))
        assert loaded.algorithm == "qm_onsets_complex"
        assert loaded.stems_tested == ["drums", "full_mix"]
        assert len(loaded.results) == 2
        assert loaded.results[0].stem == "drums"
        assert loaded.results[0].quality_score == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# SweepRunner
# ---------------------------------------------------------------------------

class TestSweepRunner:
    def _make_stem_set(self) -> MagicMock:
        stem_set = MagicMock()
        stem_set.sample_rate = 22050
        drums_arr = np.zeros(22050, dtype=np.float32)
        full_mix_arr = np.ones(22050, dtype=np.float32) * 0.5
        stem_set.get.side_effect = lambda name: (
            drums_arr if name == "drums" else full_mix_arr if name == "full_mix" else None
        )
        return stem_set

    def test_results_sorted_by_quality_score_descending(self, tmp_path):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=["drums"],
            sweep_params={"sensitivity": [20, 80]},
            fixed_params={"dftype": 3},
        )

        call_count = [0]

        def fake_run(audio, sr):
            call_count[0] += 1
            # Return more marks for sensitivity=80 → higher quality score
            marks_n = 20 if call_count[0] == 1 else 5
            return _make_track(marks_n, interval_ms=500)

        mock_algo_cls = MagicMock()
        mock_algo_cls.return_value.run = fake_run
        mock_algo_cls.return_value.preferred_stem = "drums"

        registry = {"qm_onsets_complex": mock_algo_cls}
        runner = SweepRunner(registry)

        stem_set = self._make_stem_set()
        audio = np.zeros(22050, dtype=np.float32)

        with patch("src.analyzer.sweep.load") as mock_load:
            mock_load.return_value = (audio, 22050, MagicMock(path="/tmp/song.wav",
                                                               filename="song.wav",
                                                               duration_ms=1000))
            report = runner.run("/tmp/song.wav", cfg, stem_set)

        assert len(report.results) == 2
        assert report.results[0].quality_score >= report.results[1].quality_score
        assert report.results[0].rank == 1
        assert report.results[1].rank == 2

    def test_each_result_has_correct_stem(self, tmp_path):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=["drums", "full_mix"],
            sweep_params={"sensitivity": [50]},
            fixed_params={},
        )

        mock_algo_cls = MagicMock()
        mock_algo_cls.return_value.run.return_value = _make_track(10)
        mock_algo_cls.return_value.preferred_stem = "drums"

        registry = {"qm_onsets_complex": mock_algo_cls}
        runner = SweepRunner(registry)
        stem_set = self._make_stem_set()
        audio = np.zeros(22050, dtype=np.float32)

        with patch("src.analyzer.sweep.load") as mock_load:
            mock_load.return_value = (audio, 22050, MagicMock(path="/tmp/song.wav",
                                                               filename="song.wav",
                                                               duration_ms=1000))
            report = runner.run("/tmp/song.wav", cfg, stem_set)

        stems_in_results = {r.stem for r in report.results}
        assert stems_in_results == {"drums", "full_mix"}

    def test_stems_tested_recorded_in_report(self):
        cfg = SweepConfig(
            algorithm="qm_onsets_complex",
            stems=["drums", "full_mix"],
            sweep_params={"sensitivity": [50]},
            fixed_params={},
        )
        mock_algo_cls = MagicMock()
        mock_algo_cls.return_value.run.return_value = _make_track(10)
        mock_algo_cls.return_value.preferred_stem = "drums"

        registry = {"qm_onsets_complex": mock_algo_cls}
        runner = SweepRunner(registry)
        stem_set = self._make_stem_set()
        audio = np.zeros(22050, dtype=np.float32)

        with patch("src.analyzer.sweep.load") as mock_load:
            mock_load.return_value = (audio, 22050, MagicMock(path="/tmp/song.wav",
                                                               filename="song.wav",
                                                               duration_ms=1000))
            report = runner.run("/tmp/song.wav", cfg, stem_set)

        assert set(report.stems_tested) == {"drums", "full_mix"}
