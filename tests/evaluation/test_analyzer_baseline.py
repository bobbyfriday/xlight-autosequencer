"""Tests for src/evaluation/analyzer_baseline.py.

Pure-data tests — no audio required. Tests the snapshot / check /
round-trip contract directly on synthetic TrackSnapshots.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.analyzer_baseline import (
    AnalyzerBaseline,
    FixtureSnapshot,
    TrackSnapshot,
    Violation,
    BaselineMissingError,
    check_fixture,
    check_track,
    load,
    save,
    tolerance_for,
)


def _snap(
    algo: str,
    times: list[int],
    labels: list[str | None] | None = None,
    tolerance: dict | None = None,
) -> TrackSnapshot:
    if labels is None:
        labels = [None] * len(times)
    return TrackSnapshot(
        algorithm_name=algo,
        event_times_ms=times,
        event_labels=labels,
        tolerance=tolerance or tolerance_for(algo),
    )


# ---------- load / save round-trip ----------

def test_roundtrip_preserves_shape(tmp_path: Path) -> None:
    baseline = AnalyzerBaseline(
        fixtures={
            "maple_leaf_rag": FixtureSnapshot(
                fixture_slug="maple_leaf_rag",
                algorithms={
                    "librosa_beats": _snap("librosa_beats", [500, 1000, 1500, 2000]),
                    "chordino": _snap(
                        "chordino", [0, 2000], labels=["C", "G"]
                    ),
                },
            ),
        },
    )
    path = tmp_path / "baseline.json"
    save(baseline, path)

    assert path.exists()
    loaded = load(path)
    assert loaded.schema_version == baseline.schema_version
    assert set(loaded.fixtures.keys()) == {"maple_leaf_rag"}
    fixture = loaded.fixtures["maple_leaf_rag"]
    assert set(fixture.algorithms.keys()) == {"librosa_beats", "chordino"}
    assert fixture.algorithms["librosa_beats"].event_times_ms == [500, 1000, 1500, 2000]
    assert fixture.algorithms["chordino"].event_labels == ["C", "G"]


def test_load_missing_raises() -> None:
    with pytest.raises(BaselineMissingError):
        load(Path("/nonexistent/path/baseline.json"))


def test_load_schema_mismatch_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": 999, "fixtures": {}}))
    with pytest.raises(ValueError, match="schema mismatch"):
        load(path)


# ---------- count tolerance at boundaries ----------

def test_count_within_tolerance_passes() -> None:
    # qm_onset_detector has 10% count tolerance.
    base = _snap("qm_onset_detector", list(range(0, 100, 10)))  # 10 events
    curr = _snap("qm_onset_detector", list(range(0, 99, 11)))  # 9 events = 10% drift
    violations = check_track(base, curr, "fixture")
    # 10% drift is at the exact boundary — should pass (tolerance is "<=").
    count_viols = [v for v in violations if v.kind == "count"]
    assert not count_viols


def test_count_beyond_tolerance_fails() -> None:
    # 2 extra events on a 10-event baseline = 20% drift, tolerance is 10%.
    base = _snap("qm_onset_detector", list(range(0, 100, 10)))  # 10 events
    curr = _snap("qm_onset_detector", list(range(0, 120, 10)))  # 12 events
    violations = check_track(base, curr, "fixture")
    count_viols = [v for v in violations if v.kind == "count"]
    assert len(count_viols) == 1
    assert "20.0%" in count_viols[0].detail


def test_count_mismatch_short_circuits_timing_check() -> None:
    """If count mismatches, we should NOT report per-event timing violations too."""
    base = _snap("librosa_beats", [100, 200, 300, 400])
    curr = _snap("librosa_beats", [999])  # wildly different count
    violations = check_track(base, curr, "fixture")
    assert all(v.kind == "count" for v in violations)


def test_empty_baseline_current_also_empty_passes() -> None:
    base = _snap("qm_onset_detector", [])
    curr = _snap("qm_onset_detector", [])
    assert check_track(base, curr, "fixture") == []


def test_empty_baseline_current_has_events_fails() -> None:
    base = _snap("qm_onset_detector", [])
    curr = _snap("qm_onset_detector", [100, 200])
    violations = check_track(base, curr, "fixture")
    assert len(violations) == 1
    assert violations[0].kind == "count"


# ---------- timing tolerance at boundaries ----------

def test_timing_within_tolerance_passes() -> None:
    # librosa_beats has 30ms timing tolerance.
    base = _snap("librosa_beats", [100, 200, 300])
    curr = _snap("librosa_beats", [130, 230, 330])  # exactly at boundary
    violations = check_track(base, curr, "fixture")
    timing_viols = [v for v in violations if v.kind == "timing"]
    assert not timing_viols


def test_timing_beyond_tolerance_fails() -> None:
    base = _snap("librosa_beats", [100, 200, 300])
    curr = _snap("librosa_beats", [100, 235, 300])  # middle event +35ms (tolerance 30)
    violations = check_track(base, curr, "fixture")
    timing_viols = [v for v in violations if v.kind == "timing"]
    assert len(timing_viols) == 1
    assert "event #1" in timing_viols[0].detail
    assert "35ms" in timing_viols[0].detail


def test_multiple_timing_violations_reported() -> None:
    base = _snap("librosa_beats", [100, 200, 300])
    curr = _snap("librosa_beats", [160, 200, 360])  # events 0 and 2 both exceed 30ms
    violations = check_track(base, curr, "fixture")
    timing_viols = [v for v in violations if v.kind == "timing"]
    assert len(timing_viols) == 2


# ---------- algorithm-specific rules ----------

def test_enharmonic_equivalents_pass_for_chordino() -> None:
    # chordino has enharmonic_equivalents: True.
    base = _snap("chordino", [0, 2000, 4000], labels=["F#m", "Gb", "C"])
    curr = _snap("chordino", [0, 2000, 4000], labels=["Gbm", "F#", "C"])
    violations = check_track(base, curr, "fixture")
    label_viols = [v for v in violations if v.kind == "label"]
    assert not label_viols, f"enharmonic equivalents should match: {label_viols}"


def test_enharmonic_equivalents_off_by_default() -> None:
    # Make up an algorithm that has no enharmonic flex.
    base = _snap("some_label_algo", [0], labels=["F#m"], tolerance={
        "count_tolerance_pct": 5.0, "timing_tolerance_ms": 50,
    })
    curr = _snap("some_label_algo", [0], labels=["Gbm"])
    # Need matching tolerance keys — use baseline's tolerance for both.
    curr.tolerance = base.tolerance
    violations = check_track(base, curr, "fixture")
    label_viols = [v for v in violations if v.kind == "label"]
    assert len(label_viols) == 1


def test_section_merge_window_collapses_close_boundaries() -> None:
    # qm_segmenter has merge_window_ms=2000. Events 100ms apart get merged to one.
    base = _snap("qm_segmenter", [0, 10000, 20000])  # clean baseline
    curr = _snap("qm_segmenter", [0, 100, 10000, 20000])  # extra boundary 100ms after 0 merges away
    violations = check_track(base, curr, "fixture")
    count_viols = [v for v in violations if v.kind == "count"]
    assert not count_viols, "merge_window should have collapsed the duplicate"


# ---------- fixture-level check ----------

def test_missing_fixture_slug_reports_violation() -> None:
    baseline = AnalyzerBaseline()
    current = FixtureSnapshot(fixture_slug="new_fixture", algorithms={})
    violations = check_fixture(baseline, "new_fixture", current)
    assert len(violations) == 1
    assert violations[0].kind == "missing"


def test_new_algorithm_in_current_does_not_fail() -> None:
    """Per spec: a new algorithm without baseline entry warns but doesn't fail."""
    baseline = AnalyzerBaseline(
        fixtures={
            "f": FixtureSnapshot(
                fixture_slug="f",
                algorithms={"librosa_beats": _snap("librosa_beats", [100, 200])},
            ),
        },
    )
    current = FixtureSnapshot(
        fixture_slug="f",
        algorithms={
            "librosa_beats": _snap("librosa_beats", [100, 200]),
            "brand_new_algo": _snap("brand_new_algo", [500]),
        },
    )
    violations = check_fixture(baseline, "f", current)
    assert violations == [], "brand_new_algo without baseline should not be a violation"


# ---------- tolerance_for defaults ----------

def test_tolerance_for_known_algorithm() -> None:
    tol = tolerance_for("librosa_beats")
    assert tol["count_tolerance_pct"] == 2.0
    assert tol["timing_tolerance_ms"] == 30


def test_tolerance_for_unknown_algorithm_uses_defaults() -> None:
    tol = tolerance_for("made_up_algorithm")
    assert tol["count_tolerance_pct"] == 5.0
    assert tol["timing_tolerance_ms"] == 50


def test_tolerance_for_chordino_has_enharmonic_flag() -> None:
    tol = tolerance_for("chordino")
    assert tol.get("enharmonic_equivalents") is True
