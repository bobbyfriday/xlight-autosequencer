"""T026: Integration test — full pipeline from audio file to JSON output."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from src.analyzer.runner import AnalysisRunner, default_algorithms
from src import export


def test_full_pipeline_produces_valid_result(beat_fixture_path, tmp_path):
    """Run the full analysis pipeline and validate JSON output structure."""
    algorithms = default_algorithms(include_vamp=False, include_madmom=False)
    runner = AnalysisRunner(algorithms)
    result = runner.run(str(beat_fixture_path))

    # Validate result structure
    assert result.schema_version == "1.0"
    assert result.filename == beat_fixture_path.name
    assert result.duration_ms > 0
    assert result.sample_rate > 0
    assert result.estimated_tempo_bpm > 0

    # At least the librosa tracks should be present
    assert len(result.timing_tracks) >= 7

    # All tracks have marks as sorted ints
    for track in result.timing_tracks:
        times = [m.time_ms for m in track.marks]
        assert times == sorted(times)
        for t in times:
            assert isinstance(t, int)


def test_full_pipeline_writes_valid_json(beat_fixture_path, tmp_path):
    """Pipeline output can be serialised to JSON and read back."""
    algorithms = default_algorithms(include_vamp=False, include_madmom=False)
    runner = AnalysisRunner(algorithms)
    result = runner.run(str(beat_fixture_path))

    out_path = str(tmp_path / "test_output.json")
    export.write(result, out_path)

    # Verify file is valid JSON
    with open(out_path) as fh:
        data = json.load(fh)

    assert data["schema_version"] == "1.0"
    assert len(data["timing_tracks"]) == len(result.timing_tracks)


def test_full_pipeline_is_deterministic(beat_fixture_path, tmp_path):
    """Same input with same algorithms produces identical output."""
    algorithms1 = default_algorithms(include_vamp=False, include_madmom=False)
    algorithms2 = default_algorithms(include_vamp=False, include_madmom=False)
    runner1 = AnalysisRunner(algorithms1)
    runner2 = AnalysisRunner(algorithms2)

    result1 = runner1.run(str(beat_fixture_path))
    result2 = runner2.run(str(beat_fixture_path))

    # Compare timing marks (timestamps should be identical)
    assert len(result1.timing_tracks) == len(result2.timing_tracks)
    for t1, t2 in zip(result1.timing_tracks, result2.timing_tracks):
        assert t1.name == t2.name
        marks1 = [m.time_ms for m in t1.marks]
        marks2 = [m.time_ms for m in t2.marks]
        assert marks1 == marks2, f"Track {t1.name} not deterministic"


def test_all_tracks_have_quality_score(beat_fixture_path):
    """Every generated track has a quality_score in [0, 1]."""
    algorithms = default_algorithms(include_vamp=False, include_madmom=False)
    runner = AnalysisRunner(algorithms)
    result = runner.run(str(beat_fixture_path))

    for track in result.timing_tracks:
        assert 0.0 <= track.quality_score <= 1.0, (
            f"Track {track.name} quality_score={track.quality_score} out of range"
        )
