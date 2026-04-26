"""Integration tests for orchestrator SSM (self-similarity) wiring.

The orchestrator's full pipeline pulls in vamp/madmom/demucs and is too
heavy to invoke here. Instead we exercise the SSM wrapper logic in
isolation, mirroring the pattern in test_orchestrator_energy_smoothing.py
and test_orchestrator_beat_confidence.py.

Protects the spec contract for ``HierarchyResult.repetition_groups``:
- success → field populated with the returned list
- error → field None + warning appended
- empty result → field is empty list (not None)
"""
from __future__ import annotations

import sys
import types

import numpy as np

from src.analyzer.result import HierarchyResult, RepetitionGroup


def _ssm_wrapper(audio, sr, compute_fn) -> tuple[list | None, list[str]]:
    """Reproduce the orchestrator's SSM try/except block.

    Mirrors src/analyzer/orchestrator.py around line 676. compute_fn is
    injected so we can stub success / error / empty paths without
    running the real librosa-based SSM.
    """
    warnings: list[str] = []
    repetition_groups = None
    try:
        repetition_groups = compute_fn(audio, sr)
    except Exception as exc:
        warnings.append(f"SSM (self-similarity matrix) failed: {exc}")
        repetition_groups = None
    return repetition_groups, warnings


def _make_group(gid: int, members: list[tuple[int, int]]) -> RepetitionGroup:
    return RepetitionGroup(id=gid, members=members)


class TestSSMWrapper:
    def test_success_populates_repetition_groups(self):
        """Per spec: when compute_repetition_groups returns groups,
        HierarchyResult.repetition_groups holds the same list."""
        audio = np.zeros(22050, dtype=np.float32)
        groups = [_make_group(0, [(0, 8000), (32000, 40000)])]
        result, warnings = _ssm_wrapper(audio, 22050, lambda a, sr: groups)
        assert result == groups
        assert warnings == []

    def test_empty_result_is_preserved(self):
        """Per spec scenario "SSM produces zero groups → empty list":
        empty list ≠ None. Consumers (story builder, frontend) need
        to distinguish "ran but found nothing" from "didn't run"."""
        audio = np.zeros(22050, dtype=np.float32)
        result, warnings = _ssm_wrapper(audio, 22050, lambda a, sr: [])
        assert result == []
        assert result is not None
        assert warnings == []

    def test_exception_yields_none_and_warning(self):
        """Per spec scenario "SSM unavailable or errored → None plus
        warning": exceptions don't propagate; the analyzer continues."""
        audio = np.zeros(22050, dtype=np.float32)

        def boom(a, sr):
            raise RuntimeError("librosa unavailable")

        result, warnings = _ssm_wrapper(audio, 22050, boom)
        assert result is None
        assert len(warnings) == 1
        assert "SSM (self-similarity matrix) failed" in warnings[0]
        assert "librosa unavailable" in warnings[0]

    def test_typeerror_during_compute_is_caught(self):
        """Defensive: even programming errors don't kill the analyzer."""
        audio = np.zeros(22050, dtype=np.float32)

        def buggy(a, sr):
            return None.foo  # type: ignore[union-attr]

        result, warnings = _ssm_wrapper(audio, 22050, buggy)
        assert result is None
        assert len(warnings) == 1


class TestHierarchyResultPopulation:
    """End-to-end (synthetic): construct a HierarchyResult with
    repetition_groups and confirm it round-trips through to_dict."""

    def test_repetition_groups_round_trip(self):
        groups = [
            _make_group(0, [(0, 8000), (40000, 48000)]),
            _make_group(1, [(20000, 28000), (60000, 68000)]),
        ]
        h = HierarchyResult(
            schema_version="2.0.0",
            source_file="/tmp/synth.mp3",
            source_hash="deadbeef",
            duration_ms=120_000,
            estimated_bpm=120.0,
            repetition_groups=groups,
        )
        d = h.to_dict()
        assert "repetition_groups" in d
        assert len(d["repetition_groups"]) == 2

        h2 = HierarchyResult.from_dict(d)
        assert h2.repetition_groups is not None
        assert len(h2.repetition_groups) == 2
        assert h2.repetition_groups[0].members == groups[0].members

    def test_repetition_groups_none_round_trip(self):
        """SSM unavailable → None preserves through serialization."""
        h = HierarchyResult(
            schema_version="2.0.0",
            source_file="/tmp/synth.mp3",
            source_hash="deadbeef",
            duration_ms=120_000,
            estimated_bpm=120.0,
            repetition_groups=None,
        )
        d = h.to_dict()
        h2 = HierarchyResult.from_dict(d)
        assert h2.repetition_groups is None

    def test_repetition_groups_empty_round_trip(self):
        """SSM ran but found no repetition → empty list preserves."""
        h = HierarchyResult(
            schema_version="2.0.0",
            source_file="/tmp/synth.mp3",
            source_hash="deadbeef",
            duration_ms=120_000,
            estimated_bpm=120.0,
            repetition_groups=[],
        )
        d = h.to_dict()
        h2 = HierarchyResult.from_dict(d)
        assert h2.repetition_groups == []
        assert h2.repetition_groups is not None
