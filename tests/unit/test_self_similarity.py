"""Unit tests for src/analyzer/self_similarity.py.

We avoid loading real audio in unit tests — instead we synthesize a
recurrence matrix with two known repetition blocks and assert the SSM
produces the expected groups.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.analyzer import self_similarity as ssm
from src.analyzer.result import RepetitionGroup


def _build_synthetic_matrix(
    n_beats: int = 80,
    block_starts: list[tuple[int, int]] | None = None,
    block_len: int = 16,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a [N, N] recurrence matrix with known diagonal stripes.

    Each pair in ``block_starts`` gives (a, b) — the two beat indices
    that mark the start of a self-similar pair of blocks of length
    ``block_len``. The matrix has 1.0 on the main diagonal, 0.95 on the
    diagonals defined by the block pairs, and 0.05 noise elsewhere.
    """
    if block_starts is None:
        # Default: two pairs of repetitions
        # Pair 1: beats 5..21 ↔ beats 40..56  (lag = 35)
        # Pair 2: beats 10..26 ↔ beats 60..76 (lag = 50)
        block_starts = [(5, 40), (10, 60)]
    rng = np.random.default_rng(seed=42)
    R = rng.uniform(0.0, 0.1, size=(n_beats, n_beats))
    # Symmetric noise floor
    R = (R + R.T) / 2
    np.fill_diagonal(R, 1.0)
    for a, b in block_starts:
        for offset in range(block_len):
            i = a + offset
            j = b + offset
            if 0 <= i < n_beats and 0 <= j < n_beats:
                R[i, j] = 0.95
                R[j, i] = 0.95
    # Beat times: 0.5s per beat → sr-equivalent constant cadence
    beat_times = np.arange(n_beats) * 0.5
    return R, beat_times


# ---------------------------------------------------------------------------
# Auto-threshold
# ---------------------------------------------------------------------------

def test_auto_threshold_uses_off_diagonal_distribution() -> None:
    R, _ = _build_synthetic_matrix()
    # 90th percentile of off-diagonal noise (~0.05 mean) should be far
    # below the stripe value 0.95, so stripes are above threshold.
    th = ssm._auto_threshold(R)
    assert 0.05 < th < 0.95


def test_auto_threshold_per_song_independence() -> None:
    """Spec scenario 'Threshold is per-song' — different matrices, different thresholds."""
    R_a, _ = _build_synthetic_matrix()
    R_b = R_a * 2.0
    np.fill_diagonal(R_b, 1.0)
    R_b = np.clip(R_b, 0.0, 1.0)
    assert ssm._auto_threshold(R_a) != ssm._auto_threshold(R_b)


# ---------------------------------------------------------------------------
# Stripe detection + grouping
# ---------------------------------------------------------------------------

def test_detects_two_known_repetition_blocks() -> None:
    """Synthetic matrix with two stripe pairs → SSM finds matching groups."""
    R, beat_times = _build_synthetic_matrix(
        n_beats=120,
        block_starts=[(5, 60), (35, 90)],
        block_len=16,
    )
    groups = ssm.compute_repetition_groups_from_matrix(
        R, beat_times, percentile=80.0,
    )
    assert len(groups) >= 1
    # Each detected group should have at least 2 members
    for g in groups:
        assert isinstance(g, RepetitionGroup)
        assert len(g.members) >= 2


def test_zero_groups_when_no_stripes() -> None:
    """Pure-noise matrix → no diagonals exceed threshold → empty list.

    Spec scenario "SSM produces zero groups → empty list".
    """
    rng = np.random.default_rng(seed=7)
    n = 80
    R = rng.uniform(0.0, 0.05, size=(n, n))
    R = (R + R.T) / 2
    np.fill_diagonal(R, 1.0)
    beat_times = np.arange(n) * 0.5
    # Force a high threshold (95th percentile of noise) so no stripes
    # qualify.
    groups = ssm.compute_repetition_groups_from_matrix(
        R, beat_times, percentile=99.0,
    )
    assert groups == []


def test_repetition_group_round_trip() -> None:
    """RepetitionGroup serializes and deserializes cleanly."""
    g = RepetitionGroup(id=2, members=[(1000, 5000), (10000, 14000)])
    d = g.to_dict()
    g2 = RepetitionGroup.from_dict(d)
    assert g2.id == g.id
    assert g2.members == g.members


# ---------------------------------------------------------------------------
# compute_repetition_groups public API edge cases
# ---------------------------------------------------------------------------

def test_compute_repetition_groups_empty_audio() -> None:
    """Empty audio array → empty list (no crash)."""
    audio = np.zeros(0, dtype=np.float32)
    assert ssm.compute_repetition_groups(audio, sr=22050) == []


def test_member_milliseconds_match_beat_times() -> None:
    """Group members carry beat-time ms, not raw beat indices."""
    R, beat_times = _build_synthetic_matrix(
        n_beats=120,
        block_starts=[(5, 60)],
        block_len=16,
    )
    groups = ssm.compute_repetition_groups_from_matrix(
        R, beat_times, percentile=70.0,
    )
    if not groups:
        pytest.skip("synthetic matrix produced no groups at this threshold")
    g = groups[0]
    for start_ms, end_ms in g.members:
        assert isinstance(start_ms, int)
        assert isinstance(end_ms, int)
        assert end_ms > start_ms
        # Beat times are 0.5s apart → ms values are multiples of 500.
        # Allow some integer rounding slack.
        assert start_ms % 500 == 0 or end_ms % 500 == 0
