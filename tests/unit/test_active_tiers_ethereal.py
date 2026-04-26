"""Tests for `_compute_active_tiers` after PR #21 restored Tier 1 to ethereal.

These cover all three mood branches; the ethereal branch is the one that
changed (was {8}, now {1, 8}). Structural and aggressive branches are kept
in the test for regression-protection.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.generator.effect_placer import _compute_active_tiers
from src.generator.models import SectionEnergy


def _section(mood: str, *, energy_score: int = 50) -> SectionEnergy:
    """Build a minimal SectionEnergy for the tier-selection check."""
    return SectionEnergy(
        label="A",
        start_ms=0, end_ms=10_000,
        energy_score=energy_score,
        mood_tier=mood,
        impact_count=0,
    )


def test_ethereal_returns_base_plus_hero() -> None:
    """Ethereal sections fire Tier 1 (BASE_All wash) + Tier 8 (heroes).

    Tier 1's 0.40 brightness multiplier keeps the wash dim relative to
    structural sections so the dynamic-range hierarchy survives.
    """
    section = _section("ethereal", energy_score=15)
    hierarchy = MagicMock()
    assert _compute_active_tiers(section, 0, hierarchy) == frozenset({1, 8})


def test_structural_returns_partition_plus_hero() -> None:
    """Structural sections without strong phrase structure fire Tier 6 + Tier 8."""
    section = _section("structural", energy_score=50)
    hierarchy = MagicMock()
    # Force the phrase-structure check to return False for the simple branch
    from src.generator import effect_placer
    saved = effect_placer._has_strong_phrase_structure
    effect_placer._has_strong_phrase_structure = lambda *a, **k: False
    try:
        assert _compute_active_tiers(section, 0, hierarchy) == frozenset({6, 8})
    finally:
        effect_placer._has_strong_phrase_structure = saved


def test_structural_with_phrase_structure_returns_geo_plus_hero() -> None:
    """Structural sections with strong phrase structure fire Tier 2 (GEO call-response) + Tier 8."""
    section = _section("structural", energy_score=50)
    hierarchy = MagicMock()
    from src.generator import effect_placer
    saved = effect_placer._has_strong_phrase_structure
    effect_placer._has_strong_phrase_structure = lambda *a, **k: True
    try:
        assert _compute_active_tiers(section, 0, hierarchy) == frozenset({2, 8})
    finally:
        effect_placer._has_strong_phrase_structure = saved


def test_aggressive_returns_beat_plus_hero() -> None:
    """Aggressive sections fire Tier 4 (beat chase) + Tier 8."""
    section = _section("aggressive", energy_score=85)
    hierarchy = MagicMock()
    assert _compute_active_tiers(section, 0, hierarchy) == frozenset({4, 8})


def test_ethereal_does_not_include_overlapping_partition_tiers() -> None:
    """Tier 1 (BASE_All) is the only background-wash tier; partition tiers
    2/4/6/7 must NOT be in the ethereal set since they'd silently overwrite it."""
    section = _section("ethereal", energy_score=10)
    hierarchy = MagicMock()
    tiers = _compute_active_tiers(section, 0, hierarchy)
    assert tiers.isdisjoint({2, 3, 4, 5, 6, 7}), (
        f"ethereal must not include partition tiers; got {tiers}"
    )
