"""Tests for ``placement_coverage_pct`` (OpenSpec change
``microscope-placement-coverage`` §3).

Six scenarios from the spec: full coverage = 1.0; partial coverage; no
layout context → no_layout; empty layout (defensive) → no_layout; metric
registry registration; round-trip through ``MetricValue.to_dict``.
"""
from __future__ import annotations

import json

# Import for side effect — registers the metric.
import src.evaluation.metrics.coverage as _coverage  # noqa: F401
from src.evaluation.metrics import get_registry
from src.evaluation.metrics.coverage import placement_coverage_pct
from src.evaluation.models import Placement, SequenceSummary


def _summary(
    layout: tuple[str, ...],
    placement_models: tuple[str, ...],
    group_members: dict[str, tuple[str, ...]] | None = None,
) -> SequenceSummary:
    """Build a synthetic summary with one placement per ``placement_models``
    entry. The placements themselves don't matter for coverage — the metric
    looks at ``model_names``, ``layout_model_names``, and
    ``layout_group_members``."""
    placements = tuple(
        Placement(
            start_ms=i * 1000,
            end_ms=(i + 1) * 1000,
            effect_type="Plasma",
            model_name=name,
            palette_colors=("#FF0000",),
            layer_index=0,
        )
        for i, name in enumerate(placement_models)
    )
    return SequenceSummary(
        song_id="t",
        source_label="ours",
        duration_ms=10_000,
        placements=placements,
        model_names=placement_models,
        inferred_prop_types={n: "Unknown" for n in placement_models},
        layout_model_names=layout,
        layout_group_members=group_members or {},
    )


def test_full_coverage_returns_one():
    s = _summary(layout=("A", "B", "C"), placement_models=("A", "B", "C"))
    mv = placement_coverage_pct(s)
    assert mv.value == 1.0
    assert mv.reliability == "ok"


def test_partial_coverage_returns_fraction():
    s = _summary(layout=("A", "B", "C", "D"), placement_models=("A", "B"))
    mv = placement_coverage_pct(s)
    assert mv.value == 0.5
    assert mv.reliability == "ok"


def test_no_layout_yields_none_value():
    s = _summary(layout=(), placement_models=("A",))
    mv = placement_coverage_pct(s)
    assert mv.value is None
    assert mv.reliability == "no_layout"


def test_placement_on_unmapped_group_is_ignored():
    """If a placement targets a group name that isn't in
    ``layout_group_members`` and isn't in the layout, it doesn't inflate
    coverage."""
    s = _summary(
        layout=("A", "B", "C"),
        placement_models=("A", "02_GEO_Bot"),  # only A counts
    )
    mv = placement_coverage_pct(s)
    assert mv.value == 1 / 3
    assert mv.reliability == "ok"


def test_group_placement_expands_to_members():
    """Spec scenario: a placement on a group target counts every layout
    model the group expands to."""
    s = _summary(
        layout=("A", "B", "C", "D"),
        placement_models=("HERO_GroupOne",),
        group_members={"HERO_GroupOne": ("A", "B")},
    )
    mv = placement_coverage_pct(s)
    assert mv.value == 0.5
    assert mv.reliability == "ok"


def test_group_expansion_ignores_non_layout_members():
    """Spec scenario: members the group claims that aren't in the layout
    universe (e.g. ``Parent/SubModel`` sub-model addresses) don't count."""
    s = _summary(
        layout=("A", "B"),
        placement_models=("HERO_GroupOne",),
        group_members={
            "HERO_GroupOne": ("A", "Parent/SubModel", "NotInLayout"),
        },
    )
    mv = placement_coverage_pct(s)
    # Only A is in layout; Parent/SubModel and NotInLayout don't count.
    assert mv.value == 0.5


def test_direct_and_group_placements_combine():
    """A direct-model placement plus a group placement should union without
    double-counting."""
    s = _summary(
        layout=("A", "B", "C", "D"),
        placement_models=("A", "HERO_Group"),
        group_members={"HERO_Group": ("B", "C")},
    )
    mv = placement_coverage_pct(s)
    # Covered: A (direct), B + C (via group). 3 of 4 = 0.75
    assert mv.value == 0.75


def test_metric_is_registered():
    registry = get_registry()
    assert "placement_coverage_pct" in registry
    defn = registry["placement_coverage_pct"]
    assert defn.higher_is_better is True
    assert defn.gated is False


def test_metric_value_roundtrips_through_json():
    s = _summary(layout=("A", "B"), placement_models=("A",))
    mv = placement_coverage_pct(s)
    d = mv.to_dict() if hasattr(mv, "to_dict") else {
        "value": mv.value,
        "kind": mv.kind,
        "reliability": mv.reliability,
    }
    encoded = json.dumps(d)
    decoded = json.loads(encoded)
    assert decoded["value"] == 0.5
    assert decoded["reliability"] == "ok"
