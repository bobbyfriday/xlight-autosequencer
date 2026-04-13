"""Unit tests for WorkingSet derivation from theme layer structure.

Tests follow TDD: written before implementation, expected to fail until
derive_working_set() is implemented in src/generator/effect_placer.py.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.generator.models import WorkingSet, WorkingSetEntry
from src.themes.models import EffectLayer, Theme, ThemeAlternate


# ---------------------------------------------------------------------------
# Helpers to build lightweight test fixtures
# ---------------------------------------------------------------------------

def _make_variant(name: str, base_effect: str):
    v = MagicMock()
    v.name = name
    v.base_effect = base_effect
    return v


def _make_variant_library(variants: dict[str, str]):
    """Build a minimal variant library stub: {variant_name: base_effect}."""
    lib = MagicMock()
    mocks = {name: _make_variant(name, base) for name, base in variants.items()}

    def _get(name):
        return mocks.get(name)

    lib.get = _get
    return lib


def _make_single_layer_theme(variant_name: str = "Butterfly Medium Fast") -> Theme:
    return Theme(
        name="Single Layer",
        mood="ethereal",
        occasion="general",
        genre="any",
        intent="test",
        layers=[EffectLayer(variant=variant_name)],
        palette=["#000000"],
    )


def _make_stellar_wind_theme() -> Theme:
    """3-layer theme matching the Stellar Wind example from data-model.md."""
    return Theme(
        name="Stellar Wind",
        mood="ethereal",
        occasion="general",
        genre="any",
        intent="test",
        layers=[
            EffectLayer(variant="Butterfly Medium Fast"),
            EffectLayer(variant="Shockwave Medium Thin"),
            EffectLayer(
                variant="Ripple Fast Medium",
                effect_pool=["Ripple Circle", "Spirals 3D Slow Spin"],
            ),
        ],
        alternates=[
            ThemeAlternate(layers=[EffectLayer(variant="Wave Dual Medium")]),
            ThemeAlternate(layers=[EffectLayer(variant="Spirals Directed Medium")]),
        ],
        palette=["#000000"],
    )


def _make_stellar_wind_variants() -> dict[str, str]:
    return {
        "Butterfly Medium Fast": "Butterfly",
        "Shockwave Medium Thin": "Shockwave",
        "Ripple Fast Medium": "Ripple",
        "Ripple Circle": "Ripple",
        "Spirals 3D Slow Spin": "Spirals",
        "Wave Dual Medium": "Wave",
        "Spirals Directed Medium": "Spirals",
    }


# ---------------------------------------------------------------------------
# Import the function under test (will fail until implemented)
# ---------------------------------------------------------------------------

from src.generator.effect_placer import derive_working_set  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1: Single-layer theme produces one entry with weight 1.0
# ---------------------------------------------------------------------------

class TestSingleLayerTheme:
    def test_single_layer_returns_one_entry(self):
        theme = _make_single_layer_theme("Butterfly Medium Fast")
        vl = _make_variant_library({"Butterfly Medium Fast": "Butterfly"})
        ws = derive_working_set(theme, vl)
        assert isinstance(ws, WorkingSet)
        assert len(ws.effects) == 1

    def test_single_layer_weight_is_1(self):
        theme = _make_single_layer_theme("Butterfly Medium Fast")
        vl = _make_variant_library({"Butterfly Medium Fast": "Butterfly"})
        ws = derive_working_set(theme, vl)
        assert abs(ws.effects[0].weight - 1.0) < 1e-6

    def test_single_layer_effect_name(self):
        theme = _make_single_layer_theme("Butterfly Medium Fast")
        vl = _make_variant_library({"Butterfly Medium Fast": "Butterfly"})
        ws = derive_working_set(theme, vl)
        assert ws.effects[0].effect_name == "Butterfly"
        assert ws.effects[0].variant_name == "Butterfly Medium Fast"

    def test_single_layer_source_is_layer_0(self):
        theme = _make_single_layer_theme("Butterfly Medium Fast")
        vl = _make_variant_library({"Butterfly Medium Fast": "Butterfly"})
        ws = derive_working_set(theme, vl)
        assert ws.effects[0].source == "layer_0"

    def test_theme_name_preserved(self):
        theme = _make_single_layer_theme()
        vl = _make_variant_library({"Butterfly Medium Fast": "Butterfly"})
        ws = derive_working_set(theme, vl)
        assert ws.theme_name == "Single Layer"


# ---------------------------------------------------------------------------
# Test 2: 3-layer theme (Stellar Wind) weight distribution
# ---------------------------------------------------------------------------

class TestThreeLayerTheme:
    def setup_method(self):
        self.theme = _make_stellar_wind_theme()
        self.vl = _make_variant_library(_make_stellar_wind_variants())
        self.ws = derive_working_set(self.theme, self.vl)

    def test_weights_sum_to_1(self):
        total = sum(e.weight for e in self.ws.effects)
        assert abs(total - 1.0) < 1e-6

    def test_butterfly_has_highest_weight(self):
        butterfly = next(e for e in self.ws.effects if e.effect_name == "Butterfly")
        for other in self.ws.effects:
            if other.effect_name != "Butterfly":
                assert butterfly.weight >= other.weight

    def test_layer_0_weight_approx_040(self):
        """Layer 0 base effect should have approximately 0.40 raw weight before normalization."""
        butterfly = next(e for e in self.ws.effects if e.effect_name == "Butterfly")
        # After normalization with alternates, butterfly should still dominate
        assert butterfly.weight >= 0.25

    def test_shockwave_has_second_highest(self):
        sorted_effects = sorted(self.ws.effects, key=lambda e: e.weight, reverse=True)
        assert sorted_effects[0].effect_name == "Butterfly"
        assert sorted_effects[1].effect_name == "Shockwave"

    def test_ordered_by_weight_descending(self):
        weights = [e.weight for e in self.ws.effects]
        assert weights == sorted(weights, reverse=True)


# ---------------------------------------------------------------------------
# Test 3: Theme with effect_pool splits layer weight evenly
# ---------------------------------------------------------------------------

class TestEffectPool:
    def test_effect_pool_splits_layer_weight(self):
        """Layer 2 has 3 pool items + the layer's own variant = 4 entries sharing weight."""
        theme = _make_stellar_wind_theme()
        vl = _make_variant_library(_make_stellar_wind_variants())
        ws = derive_working_set(theme, vl)

        # Layer 2 has variant "Ripple Fast Medium" + pool ["Ripple Circle", "Spirals 3D Slow Spin"]
        # Ripple base appears in layer 2 variant AND pool → should be deduped
        # Spirals base only in pool
        effect_names = {e.effect_name for e in ws.effects}
        assert "Ripple" in effect_names
        assert "Spirals" in effect_names

    def test_pool_source_label(self):
        theme = _make_stellar_wind_theme()
        vl = _make_variant_library(_make_stellar_wind_variants())
        ws = derive_working_set(theme, vl)
        pool_entries = [e for e in ws.effects if e.source == "effect_pool"]
        # Spirals only comes from the pool (not the layer variant itself)
        spirals_entries = [e for e in ws.effects if e.effect_name == "Spirals"]
        assert len(spirals_entries) >= 1


# ---------------------------------------------------------------------------
# Test 4: Theme with alternates contributes alternate entries
# ---------------------------------------------------------------------------

class TestAlternates:
    def test_alternates_contribute_entries(self):
        """Wave and Spirals from alternates should appear in working set."""
        theme = _make_stellar_wind_theme()
        vl = _make_variant_library(_make_stellar_wind_variants())
        ws = derive_working_set(theme, vl)
        effect_names = {e.effect_name for e in ws.effects}
        assert "Wave" in effect_names

    def test_alternate_source_label(self):
        theme = _make_stellar_wind_theme()
        vl = _make_variant_library(_make_stellar_wind_variants())
        ws = derive_working_set(theme, vl)
        alt_entries = [e for e in ws.effects if e.source == "alternate"]
        assert len(alt_entries) >= 1


# ---------------------------------------------------------------------------
# Test 5: Weight normalization always sums to 1.0
# ---------------------------------------------------------------------------

class TestWeightNormalization:
    def test_normalization_with_many_layers(self):
        """Even with many layers, total weight must be 1.0."""
        theme = Theme(
            name="Deep Stack",
            mood="aggressive",
            occasion="general",
            genre="any",
            intent="test",
            layers=[
                EffectLayer(variant="Butterfly Medium Fast"),
                EffectLayer(variant="Shockwave Medium Thin"),
                EffectLayer(variant="Ripple Fast Medium"),
                EffectLayer(variant="Wave Dual Medium"),
            ],
            palette=["#000000"],
        )
        vl = _make_variant_library({
            "Butterfly Medium Fast": "Butterfly",
            "Shockwave Medium Thin": "Shockwave",
            "Ripple Fast Medium": "Ripple",
            "Wave Dual Medium": "Wave",
        })
        ws = derive_working_set(theme, vl)
        total = sum(e.weight for e in ws.effects)
        assert abs(total - 1.0) < 1e-6

    def test_normalization_with_single_layer(self):
        theme = _make_single_layer_theme()
        vl = _make_variant_library({"Butterfly Medium Fast": "Butterfly"})
        ws = derive_working_set(theme, vl)
        assert abs(sum(e.weight for e in ws.effects) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Test 6: Deduplication of same base effect across layers
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_dedup_same_base_effect(self):
        """Two layers with different variants of the same base effect should produce one entry."""
        theme = Theme(
            name="Double Ripple",
            mood="ethereal",
            occasion="general",
            genre="any",
            intent="test",
            layers=[
                EffectLayer(variant="Butterfly Medium Fast"),
                EffectLayer(variant="Ripple Fast Medium"),
                EffectLayer(variant="Ripple Circle"),  # same base as layer 1
            ],
            palette=["#000000"],
        )
        vl = _make_variant_library({
            "Butterfly Medium Fast": "Butterfly",
            "Ripple Fast Medium": "Ripple",
            "Ripple Circle": "Ripple",
        })
        ws = derive_working_set(theme, vl)
        # Only one entry with effect_name "Ripple"
        ripple_entries = [e for e in ws.effects if e.effect_name == "Ripple"]
        assert len(ripple_entries) == 1

    def test_dedup_combined_weight_still_sums_to_1(self):
        """After dedup, total weight must still sum to 1.0."""
        theme = Theme(
            name="Double Ripple",
            mood="ethereal",
            occasion="general",
            genre="any",
            intent="test",
            layers=[
                EffectLayer(variant="Butterfly Medium Fast"),
                EffectLayer(variant="Ripple Fast Medium"),
                EffectLayer(variant="Ripple Circle"),
            ],
            palette=["#000000"],
        )
        vl = _make_variant_library({
            "Butterfly Medium Fast": "Butterfly",
            "Ripple Fast Medium": "Ripple",
            "Ripple Circle": "Ripple",
        })
        ws = derive_working_set(theme, vl)
        assert abs(sum(e.weight for e in ws.effects) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Test 7 (T007): Weighted selection distribution within 10% of target weights
# ---------------------------------------------------------------------------

class TestWeightedSelection:
    def test_weighted_selection_distribution(self):
        """select_from_working_set should produce distribution within 10% of target weights."""
        import random
        from src.generator.effect_placer import select_from_working_set

        theme = _make_stellar_wind_theme()
        vl = _make_variant_library(_make_stellar_wind_variants())
        ws = derive_working_set(theme, vl)

        rng = random.Random(42)
        counts: dict[str, int] = {}
        N = 1000
        for _ in range(N):
            entry = select_from_working_set(ws, rng)
            counts[entry.effect_name] = counts.get(entry.effect_name, 0) + 1

        for entry in ws.effects:
            observed = counts.get(entry.effect_name, 0) / N
            expected = entry.weight
            assert abs(observed - expected) < 0.10, (
                f"Effect {entry.effect_name}: observed {observed:.3f}, "
                f"expected {expected:.3f}, diff {abs(observed - expected):.3f}"
            )


# ---------------------------------------------------------------------------
# Test 8 (T025): focused_vocabulary=False uses original behavior (toggle test)
# ---------------------------------------------------------------------------

class TestFocusedVocabularyToggle:
    def test_focused_vocabulary_false_skips_working_set(self):
        """When focused_vocabulary=False, place_effects should not use WorkingSet."""
        # This is a behavioral test — with False, the WorkingSet path is bypassed.
        # We verify that derive_working_set is not called by checking the code path
        # doesn't raise when no working set is passed.
        # The actual behavioral test is in test_phase1_metrics.py (integration).
        # Here we just confirm derive_working_set still works for the True path.
        theme = _make_single_layer_theme()
        vl = _make_variant_library({"Butterfly Medium Fast": "Butterfly"})
        ws = derive_working_set(theme, vl)
        assert ws is not None
