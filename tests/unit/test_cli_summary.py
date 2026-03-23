"""T039: Tests for the 'summary' CLI subcommand."""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from src.cli import cli
from src.analyzer.result import AnalysisResult, TimingTrack, TimingMark, AnalysisAlgorithm
from src import export


@pytest.fixture()
def analysis_json(tmp_path):
    """Write a minimal analysis JSON fixture and return its path."""
    marks_fast = [TimingMark(time_ms=i * 100, confidence=None) for i in range(20)]
    marks_slow = [TimingMark(time_ms=i * 500, confidence=None) for i in range(20)]

    tracks = [
        TimingTrack(
            name="librosa_beats", algorithm_name="librosa_beats", element_type="beat",
            marks=marks_slow, quality_score=0.85,
        ),
        TimingTrack(
            name="librosa_onsets", algorithm_name="librosa_onsets", element_type="onset",
            marks=marks_fast, quality_score=0.30,
        ),
        TimingTrack(
            name="drums", algorithm_name="drums", element_type="percussion",
            marks=marks_slow[:8], quality_score=0.70,
        ),
    ]
    result = AnalysisResult(
        schema_version="1.0",
        source_file=str(tmp_path / "song.wav"),
        filename="song.wav",
        duration_ms=10000,
        sample_rate=22050,
        estimated_tempo_bpm=120.0,
        run_timestamp="2026-03-22T10:00:00+00:00",
        algorithms=[
            AnalysisAlgorithm(name=t.name, element_type=t.element_type,
                              library="librosa", plugin_key=None, parameters={})
            for t in tracks
        ],
        timing_tracks=tracks,
    )
    out = str(tmp_path / "song_analysis.json")
    export.write(result, out)
    return out


def test_summary_prints_header(analysis_json):
    runner = CliRunner()
    result = runner.invoke(cli, ["summary", analysis_json])
    assert result.exit_code == 0
    assert "song.wav" in result.output
    assert "120.0" in result.output
    assert "3 tracks" in result.output


def test_summary_table_sorted_by_score_descending(analysis_json):
    runner = CliRunner()
    result = runner.invoke(cli, ["summary", analysis_json])
    assert result.exit_code == 0
    lines = result.output.splitlines()
    # Find data rows (those with a score float at start of the score column)
    score_lines = [l for l in lines if "librosa_beats" in l or "drums" in l or "librosa_onsets" in l]
    scores = []
    for line in score_lines:
        parts = line.split()
        scores.append(float(parts[0]))
    assert scores == sorted(scores, reverse=True)


def test_summary_high_density_flag(analysis_json):
    runner = CliRunner()
    result = runner.invoke(cli, ["summary", analysis_json])
    assert result.exit_code == 0
    # librosa_onsets has avg_interval_ms=100ms → HIGH DENSITY
    assert "HIGH DENSITY" in result.output


def test_summary_top_n_limits_rows(analysis_json):
    runner = CliRunner()
    result = runner.invoke(cli, ["summary", analysis_json, "--top", "2"])
    assert result.exit_code == 0
    # Only 2 data rows shown
    lines = result.output.splitlines()
    data_lines = [l for l in lines if any(name in l for name in
                                          ["librosa_beats", "librosa_onsets", "drums"])]
    assert len(data_lines) == 2


def test_summary_missing_file_exits_1(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["summary", str(tmp_path / "nonexistent.json")])
    assert result.exit_code != 0
