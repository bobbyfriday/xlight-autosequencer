"""Placement coverage metric.

``placement_coverage_pct`` reports the fraction of layout-defined models that
received at least one placement. Surfaces the failure mode hit by the
matrix-heavy panel (PR #151): a layout-defined prop that the placer never
reaches is invisible to every other metric, since they all derive from
placements.

The metric requires layout context — ``SequenceSummary.layout_model_names``
is populated by ``parse(..., layout_path=...)``. Synthetic summaries built
by tests (and production legacy callers that don't pass a layout) leave it
empty, in which case this metric reports ``reliability="no_layout"`` rather
than synthesizing a meaningless 1.0.
"""
from __future__ import annotations

from src.evaluation.metrics import (
    DEFAULT_TOLERANCE,
    MetricDefinition,
    MetricKind,
    register,
)
from src.evaluation.models import MetricValue, SequenceSummary


def placement_coverage_pct(summary: SequenceSummary) -> MetricValue:
    """Fraction of layout-defined models that received a placement.

    Each name in ``summary.model_names`` is a placement target — either a
    layout model name OR a synthetic group name (e.g. ``08_HERO_MegaTree``,
    ``02_GEO_Left``). Group names are expanded to their underlying members
    via ``layout_group_members`` before the layout-universe intersection.
    """
    layout_universe = set(summary.layout_model_names)
    if not layout_universe:
        return MetricValue(
            name="placement_coverage_pct",
            kind=MetricKind.SCALAR.value,
            value=None,
            payload=None,
            reliability="no_layout",
        )
    covered: set[str] = set()
    for target in set(summary.model_names):
        if target in layout_universe:
            covered.add(target)
        members = summary.layout_group_members.get(target)
        if members:
            covered.update(members)
    covered &= layout_universe
    return MetricValue(
        name="placement_coverage_pct",
        kind=MetricKind.SCALAR.value,
        value=len(covered) / len(layout_universe),
        payload=None,
        reliability="ok",
    )


register(
    MetricDefinition(
        name="placement_coverage_pct",
        kind=MetricKind.SCALAR,
        gated=False,
        tolerance=DEFAULT_TOLERANCE,
        compute=placement_coverage_pct,
        pro_comparable=False,
        higher_is_better=True,
    )
)
