"""005: Tests for SavedConfig."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analyzer.sweep import PermutationResult, SavedConfig, SweepReport
from src.analyzer.result import TimingMark, TimingTrack


def _make_track() -> TimingTrack:
    marks = [TimingMark(time_ms=i * 500, confidence=None) for i in range(10)]
    return TimingTrack(
        name="qm_onsets_complex", algorithm_name="qm_onsets_complex",
        element_type="onset", marks=marks, quality_score=0.75,
    )


def _make_report() -> SweepReport:
    track = _make_track()
    results = [
        PermutationResult(rank=1, stem="drums", parameters={"sensitivity": 50, "dftype": 3},
                          quality_score=0.75, mark_count=10, avg_interval_ms=500, track=track),
        PermutationResult(rank=2, stem="full_mix", parameters={"sensitivity": 20, "dftype": 3},
                          quality_score=0.60, mark_count=8, avg_interval_ms=600, track=track),
    ]
    return SweepReport(
        schema_version="1.0",
        audio_file="/tmp/song.wav",
        algorithm="qm_onsets_complex",
        plugin_key="qm-vamp-plugins:qm-onsetdetector",
        stems_tested=["drums", "full_mix"],
        sweep_params={"sensitivity": [20, 50]},
        fixed_params={"dftype": 3},
        permutation_count=2,
        generated_at="2026-03-22T00:00:00Z",
        results=results,
    )


class TestSavedConfig:
    def test_save_writes_correct_json(self, tmp_path):
        report = _make_report()
        cfg = SavedConfig.from_report(report, rank=1, name="tight-onsets")
        cfg.save(config_dir=tmp_path)

        saved_path = tmp_path / "tight-onsets.json"
        assert saved_path.exists()
        data = json.loads(saved_path.read_text())
        assert data["name"] == "tight-onsets"
        assert data["algorithm"] == "qm_onsets_complex"
        assert data["stem"] == "drums"
        assert data["parameters"] == {"sensitivity": 50, "dftype": 3}

    def test_load_round_trips_all_fields(self, tmp_path):
        report = _make_report()
        cfg = SavedConfig.from_report(report, rank=1, name="tight-onsets")
        cfg.save(config_dir=tmp_path)

        loaded = SavedConfig.load("tight-onsets", config_dir=tmp_path)
        assert loaded.name == "tight-onsets"
        assert loaded.algorithm == "qm_onsets_complex"
        assert loaded.stem == "drums"
        assert loaded.parameters == {"sensitivity": 50, "dftype": 3}

    def test_save_rank_2_captures_second_result(self, tmp_path):
        report = _make_report()
        cfg = SavedConfig.from_report(report, rank=2, name="loose-onsets")
        cfg.save(config_dir=tmp_path)

        loaded = SavedConfig.load("loose-onsets", config_dir=tmp_path)
        assert loaded.stem == "full_mix"
        assert loaded.parameters == {"sensitivity": 20, "dftype": 3}

    def test_save_overwrites_existing_config(self, tmp_path):
        report = _make_report()
        cfg1 = SavedConfig.from_report(report, rank=1, name="my-config")
        cfg1.save(config_dir=tmp_path)

        cfg2 = SavedConfig.from_report(report, rank=2, name="my-config")
        cfg2.save(config_dir=tmp_path)  # overwrite

        loaded = SavedConfig.load("my-config", config_dir=tmp_path)
        assert loaded.stem == "full_mix"  # rank 2

    def test_from_report_invalid_rank_raises(self):
        report = _make_report()
        with pytest.raises((IndexError, ValueError)):
            SavedConfig.from_report(report, rank=99, name="bad")

    def test_save_creates_directory_if_absent(self, tmp_path):
        new_dir = tmp_path / "nonexistent" / "subdir"
        report = _make_report()
        cfg = SavedConfig.from_report(report, rank=1, name="test")
        cfg.save(config_dir=new_dir)
        assert (new_dir / "test.json").exists()
