"""T040: Tests for the 'export' CLI subcommand."""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from src.cli import cli
from src.analyzer.result import AnalysisResult, TimingTrack, TimingMark, AnalysisAlgorithm
from src import export


@pytest.fixture()
def analysis_json(tmp_path):
    marks_slow = [TimingMark(time_ms=i * 500, confidence=None) for i in range(20)]
    marks_fast = [TimingMark(time_ms=i * 100, confidence=None) for i in range(20)]

    tracks = [
        TimingTrack(
            name="librosa_beats", algorithm_name="librosa_beats", element_type="beat",
            marks=marks_slow, quality_score=0.85,
        ),
        TimingTrack(
            name="drums", algorithm_name="drums", element_type="percussion",
            marks=marks_slow[:8], quality_score=0.70,
        ),
        TimingTrack(
            name="librosa_onsets", algorithm_name="librosa_onsets", element_type="onset",
            marks=marks_fast, quality_score=0.30,
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


def test_export_select_produces_correct_tracks(analysis_json, tmp_path):
    out = str(tmp_path / "out.json")
    runner = CliRunner()
    result = runner.invoke(cli, ["export", analysis_json, "--select", "librosa_beats,drums", "--output", out])
    assert result.exit_code == 0
    with open(out) as fh:
        data = json.load(fh)
    assert len(data["timing_tracks"]) == 2
    names = {t["name"] for t in data["timing_tracks"]}
    assert names == {"librosa_beats", "drums"}


def test_export_top_n_selects_highest_scored(analysis_json, tmp_path):
    out = str(tmp_path / "out.json")
    runner = CliRunner()
    result = runner.invoke(cli, ["export", analysis_json, "--top", "2", "--output", out])
    assert result.exit_code == 0
    with open(out) as fh:
        data = json.load(fh)
    assert len(data["timing_tracks"]) == 2
    names = {t["name"] for t in data["timing_tracks"]}
    # Top 2 by quality: librosa_beats (0.85) and drums (0.70)
    assert names == {"librosa_beats", "drums"}


def test_export_unknown_track_exits_4(analysis_json, tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["export", analysis_json, "--select", "nonexistent_track"])
    assert result.exit_code == 4


def test_export_missing_both_select_and_top_exits_5(analysis_json):
    runner = CliRunner()
    result = runner.invoke(cli, ["export", analysis_json])
    assert result.exit_code == 5


def test_export_source_json_unchanged(analysis_json, tmp_path):
    """Export must not modify the source JSON."""
    import hashlib
    with open(analysis_json, "rb") as fh:
        original_hash = hashlib.md5(fh.read()).hexdigest()

    out = str(tmp_path / "out.json")
    runner = CliRunner()
    runner.invoke(cli, ["export", analysis_json, "--top", "1", "--output", out])

    with open(analysis_json, "rb") as fh:
        after_hash = hashlib.md5(fh.read()).hexdigest()
    assert original_hash == after_hash
