"""Value curve generation — modulates effect parameters from analysis data."""
from __future__ import annotations

import math

from src.analyzer.result import HierarchyResult, ValueCurve
from src.effects.models import AnalysisMapping, EffectDefinition, EffectParameter
from src.generator.energy import slice_curve
from src.generator.models import EffectPlacement


MAX_CONTROL_POINTS = 100


def generate_value_curves(
    placement: EffectPlacement,
    effect_def: EffectDefinition,
    hierarchy: HierarchyResult,
) -> dict[str, list[tuple[float, float]]]:
    """Generate parameter modulation curves from analysis mappings.

    For each AnalysisMapping where the target parameter supports value curves:
    1. Extract analysis data for the effect's time range
    2. Apply curve_shape transform (linear, log, exp, step)
    3. Map input_min/max -> output_min/max
    4. Downsample to ≤100 control points
    5. Return as (x, y) tuples where x is normalized position [0.0-1.0]
    """
    if not effect_def.analysis_mappings:
        return {}

    # Build parameter lookup
    param_map: dict[str, EffectParameter] = {
        p.name: p for p in effect_def.parameters
    }

    result: dict[str, list[tuple[float, float]]] = {}

    for mapping in effect_def.analysis_mappings:
        param = param_map.get(mapping.parameter)
        if param is None or not param.supports_value_curve:
            continue

        curve_data = _extract_analysis_data(
            mapping, hierarchy, placement.start_ms, placement.end_ms
        )
        if not curve_data:
            continue

        points = _map_to_output(curve_data, mapping)
        points = _downsample(points, MAX_CONTROL_POINTS)
        result[mapping.parameter] = points

    return result


def _extract_analysis_data(
    mapping: AnalysisMapping,
    hierarchy: HierarchyResult,
    start_ms: int,
    end_ms: int,
) -> list[float]:
    """Extract raw analysis values for the effect's time range."""
    if mapping.analysis_level == "L5":
        curve = hierarchy.energy_curves.get(mapping.analysis_field)
        if curve is None:
            curve = hierarchy.energy_curves.get("full_mix")
        return [float(v) for v in slice_curve(curve, start_ms, end_ms)]

    return []


def _map_to_output(
    raw_values: list[float],
    mapping: AnalysisMapping,
) -> list[tuple[float, float]]:
    """Apply curve shape and range mapping to produce (x, y) control points."""
    n = len(raw_values)
    if n == 0:
        return []

    in_min = mapping.input_min
    in_max = mapping.input_max
    out_min = mapping.output_min if mapping.output_min is not None else in_min
    out_max = mapping.output_max if mapping.output_max is not None else in_max
    in_range = in_max - in_min if in_max != in_min else 1.0

    points: list[tuple[float, float]] = []
    for i, raw in enumerate(raw_values):
        x = i / max(n - 1, 1)

        # Normalize to 0-1
        normalized = max(0.0, min(1.0, (raw - in_min) / in_range))

        # Apply curve shape
        shaped = _apply_curve_shape(normalized, mapping.curve_shape, mapping.threshold)

        # Invert if mapping type is inverted
        if mapping.mapping_type == "inverted":
            shaped = 1.0 - shaped

        # Map to output range
        y = out_min + shaped * (out_max - out_min)
        points.append((round(x, 4), round(y, 2)))

    return points


def _apply_curve_shape(
    normalized: float, shape: str, threshold: float | None
) -> float:
    """Apply a curve shape transform to a normalized 0-1 value."""
    if shape == "linear":
        return normalized

    elif shape == "logarithmic":
        # Log curve: fast rise, slow finish
        return math.log1p(normalized * 9) / math.log(10)

    elif shape == "exponential":
        # Exponential curve: slow start, fast finish
        return (math.pow(10, normalized) - 1) / 9

    elif shape == "step":
        # Binary output based on threshold
        thresh = threshold if threshold is not None else 0.5
        return 1.0 if normalized >= thresh else 0.0

    return normalized


def _downsample(
    points: list[tuple[float, float]], max_points: int
) -> list[tuple[float, float]]:
    """Downsample control points to at most max_points."""
    if len(points) <= max_points:
        return points

    step = len(points) / max_points
    result = [points[int(i * step)] for i in range(max_points - 1)]
    result.append(points[-1])  # Always include last point
    return result
