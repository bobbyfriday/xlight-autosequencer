"""Integration tests for variant resolution in the sequence generator."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.analyzer.result import HierarchyResult, TimingMark, TimingTrack
from src.effects.library import load_effect_library
from src.generator.effect_placer import place_effects
from src.generator.models import SectionAssignment, SectionEnergy
from src.grouper.grouper import PowerGroup
from src.themes.models import EffectLayer, Theme
from src.variants.library import load_variant_library
from src.variants.models import EffectVariant, VariantTags

EFFECTS_FIXTURE = Path(__file__).parent.parent / "fixtures" / "effects" / "minimal_library_with_meteors.json"
VARIANTS_FIXTURE = Path(__file__).parent.parent / "fixtures" / "variants" / "variants_with_variant_refs.json"


# ── Test helpers ──────────────────────────────────────────────────────────────


def _make_hierarchy(duration_ms: int = 10000) -> HierarchyResult:
    beats = TimingTrack(
        name="beats", algorithm_name="librosa_beats", element_type="beat",
        marks=[TimingMark(time_ms=i * 500, confidence=1.0) for i in range(duration_ms // 500)],
        quality_score=0.9,
    )
    bars = TimingTrack(
        name="bars", algorithm_name="librosa_beats", element_type="bar",
        marks=[TimingMark(time_ms=i * 2000, confidence=1.0) for i in range(duration_ms // 2000)],
        quality_score=0.9,
    )
    return HierarchyResult(
        schema_version="2.0.0",
        source_file="test.mp3",
        source_hash="abc123",
        duration_ms=duration_ms,
        estimated_bpm=120.0,
        sections=[TimingMark(time_ms=0, confidence=1.0, label="verse", duration_ms=duration_ms)],
        beats=beats,
        bars=bars,
        energy_curves={},
        energy_impacts=[],
    )


def _make_section_energy(start_ms: int = 0, end_ms: int = 10000) -> SectionEnergy:
    return SectionEnergy(
        label="verse",
        start_ms=start_ms,
        end_ms=end_ms,
        energy_score=60,
        mood_tier="mid",
        impact_count=0,
    )


def _make_groups() -> list[PowerGroup]:
    return [
        PowerGroup(name="01_BASE_All", tier=1, members=["Arch1"]),
        PowerGroup(name="08_HERO_Main", tier=8, members=["Matrix1"]),
    ]


def _make_theme_with_variant(effect_name: str, variant_ref: str | None) -> Theme:
    layer = EffectLayer(
        effect=effect_name,
        blend_mode="Normal",
        parameter_overrides={},
        variant_ref=variant_ref,
    )
    return Theme(
        name="Test Theme",
        mood="ethereal",
        occasion="general",
        genre="any",
        intent="Testing",
        layers=[layer],
        palette=["#FF0000", "#00FF00", "#0000FF"],
    )


def _make_assignment(theme: Theme, section: SectionEnergy) -> SectionAssignment:
    return SectionAssignment(
        section=section,
        theme=theme,
        variation_seed=0,
        group_effects={},
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestVariantResolutionInPlacer:
    """Verify that variant parameter_overrides flow through to EffectPlacement."""

    def test_variant_params_appear_in_placement(self):
        """Variant overrides appear in the generated placement parameters."""
        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
        variant_lib = load_variant_library(builtin_path=VARIANTS_FIXTURE)

        # bars-triple sets E_SLIDER_Bars_BarCount = 3
        theme = _make_theme_with_variant("Bars", "bars-triple")
        section = _make_section_energy()
        assignment = _make_assignment(theme, section)
        groups = _make_groups()
        hierarchy = _make_hierarchy()

        result = place_effects(
            assignment, groups, effect_lib, hierarchy,
            variant_library=variant_lib,
        )

        all_placements = [p for placements in result.values() for p in placements]
        assert len(all_placements) > 0

        found = any(
            p.parameters.get("E_SLIDER_Bars_BarCount") == 3
            for p in all_placements
        )
        assert found, (
            f"Expected E_SLIDER_Bars_BarCount=3 from variant, "
            f"got params: {[p.parameters for p in all_placements]}"
        )

    def test_layer_overrides_take_precedence_over_variant(self):
        """Layer parameter_overrides override variant overrides."""
        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
        variant_lib = load_variant_library(builtin_path=VARIANTS_FIXTURE)

        # Variant bars-triple sets BarCount=3, layer overrides to 7
        layer = EffectLayer(
            effect="Bars",
            blend_mode="Normal",
            parameter_overrides={"E_SLIDER_Bars_BarCount": 7},
            variant_ref="bars-triple",
        )
        theme = Theme(
            name="Test Theme",
            mood="ethereal",
            occasion="general",
            genre="any",
            intent="Testing",
            layers=[layer],
            palette=["#FF0000", "#00FF00", "#0000FF"],
        )
        section = _make_section_energy()
        assignment = _make_assignment(theme, section)
        groups = _make_groups()
        hierarchy = _make_hierarchy()

        result = place_effects(
            assignment, groups, effect_lib, hierarchy,
            variant_library=variant_lib,
        )

        all_placements = [p for placements in result.values() for p in placements]
        assert len(all_placements) > 0

        found = any(p.parameters.get("E_SLIDER_Bars_BarCount") == 7 for p in all_placements)
        assert found, (
            f"Expected layer override E_SLIDER_Bars_BarCount=7 to win over variant's 3, "
            f"got: {[p.parameters for p in all_placements]}"
        )

    def test_nonexistent_variant_ref_falls_back_gracefully(self, caplog):
        """Nonexistent variant_ref does not crash — falls back to base defaults."""
        import logging
        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
        variant_lib = load_variant_library(builtin_path=VARIANTS_FIXTURE)

        theme = _make_theme_with_variant("Fire", "does-not-exist")
        section = _make_section_energy()
        assignment = _make_assignment(theme, section)
        groups = _make_groups()
        hierarchy = _make_hierarchy()

        with caplog.at_level(logging.WARNING):
            result = place_effects(
                assignment, groups, effect_lib, hierarchy,
                variant_library=variant_lib,
            )

        all_placements = [p for placements in result.values() for p in placements]
        assert len(all_placements) > 0
        assert any("does-not-exist" in r.message for r in caplog.records)

    def test_none_variant_ref_uses_base_defaults(self):
        """variant_ref=None uses only base defaults + layer overrides (no variant)."""
        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
        variant_lib = load_variant_library(builtin_path=VARIANTS_FIXTURE)

        layer = EffectLayer(
            effect="Bars",
            blend_mode="Normal",
            parameter_overrides={"E_SLIDER_Bars_BarCount": 5},
            variant_ref=None,
        )
        theme = Theme(
            name="Test Theme",
            mood="ethereal",
            occasion="general",
            genre="any",
            intent="Testing",
            layers=[layer],
            palette=["#FF0000", "#00FF00", "#0000FF"],
        )
        section = _make_section_energy()
        assignment = _make_assignment(theme, section)
        groups = _make_groups()
        hierarchy = _make_hierarchy()

        result = place_effects(
            assignment, groups, effect_lib, hierarchy,
            variant_library=variant_lib,
        )

        all_placements = [p for placements in result.values() for p in placements]
        assert len(all_placements) > 0

        found = any(p.parameters.get("E_SLIDER_Bars_BarCount") == 5 for p in all_placements)
        assert found, f"Expected E_SLIDER_Bars_BarCount=5 from layer override"

    def test_no_variant_library_behavior_unchanged(self):
        """Without variant_library, behavior is identical to pre-feature code."""
        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)

        layer = EffectLayer(
            effect="Bars",
            blend_mode="Normal",
            parameter_overrides={"E_SLIDER_Bars_BarCount": 4},
            variant_ref="bars-triple",  # will be ignored since no variant_library
        )
        theme = Theme(
            name="Test Theme",
            mood="ethereal",
            occasion="general",
            genre="any",
            intent="Testing",
            layers=[layer],
            palette=["#FF0000", "#00FF00", "#0000FF"],
        )
        section = _make_section_energy()
        assignment = _make_assignment(theme, section)
        groups = _make_groups()
        hierarchy = _make_hierarchy()

        result = place_effects(
            assignment, groups, effect_lib, hierarchy,
        )

        all_placements = [p for placements in result.values() for p in placements]
        assert len(all_placements) > 0

        found = any(p.parameters.get("E_SLIDER_Bars_BarCount") == 4 for p in all_placements)
        assert found, f"Expected E_SLIDER_Bars_BarCount=4 from layer override only"

    def test_variant_params_are_base_for_layer_override_chain(self):
        """Variant provides additional params that layer doesn't touch."""
        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
        variant_lib = load_variant_library(builtin_path=VARIANTS_FIXTURE)

        # fire-low-flicker sets Height=20 and HueShift=10
        # Layer only overrides Height=50, leaving HueShift from variant
        layer = EffectLayer(
            effect="Fire",
            blend_mode="Normal",
            parameter_overrides={"E_SLIDER_Fire_Height": 50},
            variant_ref="fire-low-flicker",
        )
        theme = Theme(
            name="Test Theme",
            mood="ethereal",
            occasion="general",
            genre="any",
            intent="Testing",
            layers=[layer],
            palette=["#FF0000", "#00FF00", "#0000FF"],
        )
        section = _make_section_energy()
        assignment = _make_assignment(theme, section)
        groups = _make_groups()
        hierarchy = _make_hierarchy()

        result = place_effects(
            assignment, groups, effect_lib, hierarchy,
            variant_library=variant_lib,
        )

        all_placements = [p for placements in result.values() for p in placements]
        assert len(all_placements) > 0

        height_ok = any(p.parameters.get("E_SLIDER_Fire_Height") == 50 for p in all_placements)
        hue_ok = any(p.parameters.get("E_SLIDER_Fire_HueShift") == 10 for p in all_placements)

        assert height_ok, "Expected layer override Height=50"
        assert hue_ok, "Expected variant HueShift=10 to survive (layer doesn't override it)"

    def test_direction_cycle_applied_to_placement(self):
        """Variant with direction_cycle sets the direction param on placement."""
        from src.variants.library import VariantLibrary

        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)

        # Create a variant with direction_cycle (no direction in parameter_overrides)
        variant = EffectVariant(
            name="bars-cycle-test",
            base_effect="Bars",
            description="test",
            parameter_overrides={"E_SLIDER_Bars_BarCount": 2},
            tags=VariantTags(),
            direction_cycle={
                "param": "E_CHOICE_Bars_Direction",
                "values": ["left", "right"],
                "mode": "alternate",
            },
        )
        variant_lib = VariantLibrary(
            schema_version="1.0.0",
            variants={"bars-cycle-test": variant},
            builtin_names=set(),
        )

        layer = EffectLayer(
            effect="Bars",
            blend_mode="Normal",
            parameter_overrides={},
            variant_ref="bars-cycle-test",
        )
        theme = Theme(
            name="Test Theme",
            mood="ethereal",
            occasion="general",
            genre="any",
            intent="Testing",
            layers=[layer],
            palette=["#FF0000", "#00FF00", "#0000FF"],
        )
        section = _make_section_energy()
        assignment = _make_assignment(theme, section)
        groups = _make_groups()
        hierarchy = _make_hierarchy()

        result = place_effects(
            assignment, groups, effect_lib, hierarchy,
            variant_library=variant_lib,
        )

        all_placements = [p for placements in result.values() for p in placements]
        assert len(all_placements) >= 1

        # Direction cycle should inject the param (instance_index=0 → "left")
        directions = [
            p.parameters.get("E_CHOICE_Bars_Direction")
            for p in all_placements
            if "E_CHOICE_Bars_Direction" in p.parameters
        ]
        assert len(directions) >= 1, (
            f"Expected direction_cycle to inject E_CHOICE_Bars_Direction, "
            f"got params: {[p.parameters for p in all_placements]}"
        )
        assert directions[0] == "left", (
            f"Expected 'left' for instance_index=0, got: {directions[0]}"
        )

    def test_direction_cycle_alternates_with_multiple_instances(self):
        """direction_cycle alternates values across multiple placements (unit test of _make_placement)."""
        from src.generator.effect_placer import _make_placement

        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
        bars_def = effect_lib.get("Bars")

        dc = {"param": "E_CHOICE_Bars_Direction", "values": ["up", "down"], "mode": "alternate"}
        params = {"E_SLIDER_Bars_BarCount": 3}

        p0 = _make_placement(bars_def, "G1", 0, 2000, params, ["#FF0000"], "Normal", "bar",
                             instance_index=0, direction_cycle=dc)
        p1 = _make_placement(bars_def, "G1", 2000, 4000, params, ["#FF0000"], "Normal", "bar",
                             instance_index=1, direction_cycle=dc)
        p2 = _make_placement(bars_def, "G1", 4000, 6000, params, ["#FF0000"], "Normal", "bar",
                             instance_index=2, direction_cycle=dc)

        assert p0.parameters["E_CHOICE_Bars_Direction"] == "up"
        assert p1.parameters["E_CHOICE_Bars_Direction"] == "down"
        assert p2.parameters["E_CHOICE_Bars_Direction"] == "up"

    def test_no_direction_cycle_uses_hardcoded_fallback(self):
        """Without direction_cycle, hardcoded _ALTERNATING_DIRECTIONS still works."""
        from src.generator.effect_placer import _make_placement

        effect_lib = load_effect_library(builtin_path=EFFECTS_FIXTURE)
        bars_def = effect_lib.get("Bars")

        # Include a direction param in overrides — hardcoded alternation should cycle it
        params = {"E_SLIDER_Bars_BarCount": 2, "E_CHOICE_Bars_Direction": "Left"}

        p0 = _make_placement(bars_def, "G1", 0, 2000, params, ["#FF0000"], "Normal", "bar",
                             instance_index=0)
        p1 = _make_placement(bars_def, "G1", 2000, 4000, params, ["#FF0000"], "Normal", "bar",
                             instance_index=1)

        # Hardcoded _ALTERNATING_DIRECTIONS for Bars_Direction is ["Left", "Right", "expand", "compress"]
        assert p0.parameters["E_CHOICE_Bars_Direction"] == "Left"
        assert p1.parameters["E_CHOICE_Bars_Direction"] == "Right"
