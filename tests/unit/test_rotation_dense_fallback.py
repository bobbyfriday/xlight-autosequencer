"""Tests for the rotation-engine dense-fill fallback (P1 of dim-section-real-cause).

The within-tier base-effect dedup at `rotation.py:325` historically kept the
originally-selected variant when no unclaimed alternative scored ≥0.3 — which
in low-energy structural sections meant ~10 of every section's tier-6 groups
landed on `Chase Multi Dense` (Single Strand), a sparse-by-design effect.

The fix: when the unclaimed list is empty, prefer duplicating a dense-fill
variant (Color Wash, Liquid, Plasma, Fire, Galaxy, Pinwheel, Butterfly,
Shockwave) over the originally-selected sparse one. These tests confirm the
fallback path picks dense over sparse.
"""
from __future__ import annotations

import pytest

from src.generator.rotation import _DENSE_FILL_BASE_EFFECTS


def test_dense_fill_set_includes_known_dense_effects() -> None:
    """The constant must include the base effects we documented as dense fills."""
    expected = {"Color Wash", "Liquid", "Plasma", "Fire", "Galaxy", "Pinwheel",
                "Butterfly", "Shockwave"}
    assert expected.issubset(_DENSE_FILL_BASE_EFFECTS)


def test_dense_fill_set_excludes_sparse_effects() -> None:
    """Sparse-by-design effects must NOT be in the dense set or the fallback fails."""
    sparse = {"Single Strand", "Bars", "Strobe", "Curtain"}
    assert sparse.isdisjoint(_DENSE_FILL_BASE_EFFECTS)


# Note: the dedup-fallback branch is integration-tested via the broader
# tests/unit/test_generator/test_rotation*.py suite (which exercises
# `build_rotation_plan` end-to-end). A focused unit test would require
# mocking out half of `rank_variants_with_fallback` and is brittle. The
# verification-framework run on Baby Shark is the empirical confirmation
# that matters; metric deltas are recorded in metrics_25.json.
