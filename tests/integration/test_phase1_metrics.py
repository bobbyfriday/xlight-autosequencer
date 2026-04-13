"""Integration tests for Phase 1 metric targets.

Tests validate that the generated sequences achieve the desired
effect vocabulary and repetition characteristics after Phase 1 changes.

T008: focused_vocabulary=True → top-5 effects >= 80% with single theme
T023: All 21 themes produce top1 >= 0.25 and top2 >= 0.45 in their WorkingSet
T029: Both toggles=False restores pre-Phase-1 behavior (no regressions)

Note: The 80% top-5 target applies to SINGLE-THEME sequences, matching community
      hand-sequenced files. Multi-theme sequences naturally have more vocabulary
      diversity, so we test multi-theme improvement separately.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from src.effects.library import load_effect_library
from src.generator.plan import build_plan
from src.themes.library import load_theme_library
from src.validation.scenarios import ALL_SCENARIOS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_and_collect_effects(scenario_name: str, tmp_path: Path, **config_kwargs) -> Counter:
    """Run a scenario and count effect placements by effect name."""
    scenario = ALL_SCENARIOS[scenario_name]()
    effect_lib = load_effect_library()
    from src.variants.library import load_variant_library
    variant_lib = load_variant_library(effect_library=effect_lib)
    theme_lib = load_theme_library(effect_library=effect_lib, variant_library=variant_lib)

    config = scenario.make_config(tmp_path)
    # Apply overrides
    for k, v in config_kwargs.items():
        setattr(config, k, v)

    plan = build_plan(
        config, scenario.hierarchy,
        scenario.props, scenario.groups,
        effect_lib, theme_lib,
    )

    counter: Counter = Counter()
    for assignment in plan.sections:
        for group_name, placements in assignment.group_effects.items():
            for p in placements:
                counter[p.effect_name] += 1

    return counter


# ---------------------------------------------------------------------------
# T008: single-theme scenario achieves top-5 >= 80% and top-1 >= 25%
# ---------------------------------------------------------------------------

class TestFocusedVocabularyMetrics:
    def test_single_theme_top5_above_80_percent(self, tmp_path: Path):
        """With focused_vocabulary=True and single theme, top-5 >= 80% of placements.

        The 80% target matches community hand-sequenced files that use one
        consistent visual theme. Multi-theme sequences have inherently more
        vocabulary diversity.
        """
        scenario_name = next(iter(ALL_SCENARIOS.keys()))
        # Force a single theme so we measure focused vocabulary in isolation
        counter = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=True,
            embrace_repetition=True,
            theme_overrides={i: "Stellar Wind" for i in range(20)},
        )

        if not counter:
            pytest.skip("No effects generated for this scenario")

        total = sum(counter.values())
        top5_count = sum(count for _, count in counter.most_common(5))
        top5_pct = top5_count / total

        assert top5_pct >= 0.80, (
            f"Single-theme top-5 is {top5_pct:.1%} (expected >= 80%). "
            f"Top effects: {counter.most_common(7)}"
        )

    def test_single_theme_top1_above_25_percent(self, tmp_path: Path):
        """With focused_vocabulary=True and single theme, top effect >= 25%."""
        scenario_name = next(iter(ALL_SCENARIOS.keys()))
        counter = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=True,
            embrace_repetition=True,
            theme_overrides={i: "Stellar Wind" for i in range(20)},
        )

        if not counter:
            pytest.skip("No effects generated for this scenario")

        total = sum(counter.values())
        top1_pct = counter.most_common(1)[0][1] / total

        assert top1_pct >= 0.25, (
            f"Single-theme top effect is {top1_pct:.1%} (expected >= 25%). "
            f"Top effects: {counter.most_common(3)}"
        )

    def test_focused_reduces_effect_count_vs_baseline(self, tmp_path: Path):
        """focused_vocabulary=True should use fewer distinct effects than False (single theme)."""
        scenario_name = next(iter(ALL_SCENARIOS.keys()))
        overrides = {i: "Stellar Wind" for i in range(20)}

        counter_on = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=True, embrace_repetition=True,
            theme_overrides=overrides,
        )
        counter_off = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=False, embrace_repetition=False,
            theme_overrides=overrides,
        )

        if not counter_on or not counter_off:
            pytest.skip("No effects generated")

        # WorkingSet constraint should reduce distinct effect count
        assert len(counter_on) <= len(counter_off), (
            f"focused_vocabulary=True should use <= distinct effects than False: "
            f"on={len(counter_on)}, off={len(counter_off)}"
        )


# ---------------------------------------------------------------------------
# T023: All themes produce steep WorkingSet weight distribution
# ---------------------------------------------------------------------------

class TestThemeWeightDistribution:
    def test_all_themes_have_steep_distribution(self):
        """All 21 themes should produce top1 >= 0.25 and top2 >= 0.45."""
        from src.variants.library import load_variant_library
        from src.generator.effect_placer import derive_working_set

        el = load_effect_library()
        vl = load_variant_library(effect_library=el)
        tl = load_theme_library(effect_library=el, variant_library=vl)

        failures = []
        for name, theme in tl.themes.items():
            ws = derive_working_set(theme, vl)
            if not ws.effects:
                failures.append(f"{name}: empty working set")
                continue
            top1 = ws.effects[0].weight
            top2 = sum(e.weight for e in ws.effects[:2])
            if top1 < 0.25:
                failures.append(f"{name}: top1={top1:.3f} < 0.25")
            if top2 < 0.45:
                failures.append(f"{name}: top2={top2:.3f} < 0.45")

        assert not failures, (
            f"Themes with flat distributions:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )

    def test_two_themes_single_theme_integration_targets(self, tmp_path: Path):
        """Single-theme sequences for 2 different themes pass top-1 >= 25%."""
        scenario_name = next(iter(ALL_SCENARIOS.keys()))
        test_themes = ["Stellar Wind", "Tracer Fire"]
        failures = []

        for theme_name in test_themes:
            counter = _run_and_collect_effects(
                scenario_name, tmp_path,
                focused_vocabulary=True,
                embrace_repetition=True,
                theme_overrides={i: theme_name for i in range(20)},
            )
            if not counter:
                continue
            total = sum(counter.values())
            top1_pct = counter.most_common(1)[0][1] / total
            if top1_pct < 0.25:
                failures.append(f"{theme_name}: top effect = {top1_pct:.1%} < 25%")

        assert not failures, "Integration targets not met:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# T029: Both toggles=False restores pre-Phase-1 behavior (no regressions)
# ---------------------------------------------------------------------------

class TestTogglesOffRestoresBehavior:
    def test_toggles_off_generates_valid_sequence(self, tmp_path: Path):
        """With both toggles=False, generation still produces a valid sequence."""
        scenario_name = next(iter(ALL_SCENARIOS.keys()))
        counter = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=False,
            embrace_repetition=False,
        )
        assert sum(counter.values()) > 0, (
            "With both toggles=False, generation should still produce effects"
        )

    def test_both_toggles_false_is_deterministic(self, tmp_path: Path):
        """With both toggles=False, two runs produce identical results."""
        scenario_name = next(iter(ALL_SCENARIOS.keys()))

        counter1 = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=False,
            embrace_repetition=False,
        )
        counter2 = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=False,
            embrace_repetition=False,
        )

        assert counter1 == counter2, (
            "With both toggles=False, two runs should be deterministic"
        )

    def test_focused_vocabulary_constrains_rotation_variants(self, tmp_path: Path):
        """focused_vocabulary=True uses fewer distinct effects for single-theme sequences."""
        scenario_name = next(iter(ALL_SCENARIOS.keys()))
        overrides = {i: "Stellar Wind" for i in range(20)}

        counter_on = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=True,
            theme_overrides=overrides,
        )
        counter_off = _run_and_collect_effects(
            scenario_name, tmp_path,
            focused_vocabulary=False,
            theme_overrides=overrides,
        )

        assert len(counter_on) <= len(counter_off), (
            f"focused_vocabulary=True should not increase distinct effects: "
            f"on={len(counter_on)}, off={len(counter_off)}"
        )
