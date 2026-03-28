"""Tests for value curve generation."""
from __future__ import annotations

import pytest

from src.effects.models import AnalysisMapping, EffectDefinition, EffectParameter
from src.analyzer.result import HierarchyResult, ValueCurve
from src.generator.models import EffectPlacement
from src.generator.value_curves import generate_value_curves


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_parameter(
    name: str = "brightness",
    supports_value_curve: bool = True,
    min_val: int = 0,
    max_val: int = 100,
) -> EffectParameter:
    return EffectParameter(
        name=name,
        storage_name=f"E_{name}",
        widget_type="slider",
        value_type="int",
        default=50,
        description=f"{name} parameter",
        min=min_val,
        max=max_val,
        supports_value_curve=supports_value_curve,
    )


def _make_mapping(
    parameter: str = "brightness",
    mapping_type: str = "direct",
    curve_shape: str = "linear",
    input_min: float = 0.0,
    input_max: float = 100.0,
    output_min: float | None = None,
    output_max: float | None = None,
    threshold: float | None = None,
) -> AnalysisMapping:
    return AnalysisMapping(
        parameter=parameter,
        analysis_level="L5",
        analysis_field="full_mix",
        mapping_type=mapping_type,
        description="test mapping",
        input_min=input_min,
        input_max=input_max,
        output_min=output_min,
        output_max=output_max,
        curve_shape=curve_shape,
        threshold=threshold,
    )


def _make_effect_def(
    parameters: list[EffectParameter] | None = None,
    mappings: list[AnalysisMapping] | None = None,
) -> EffectDefinition:
    return EffectDefinition(
        name="Color Wash",
        xlights_id="E_VALUECURVE_ColorWash",
        category="color_wash",
        description="A color wash effect",
        intent="Fill with color",
        parameters=parameters or [],
        prop_suitability={"matrix": "ideal"},
        analysis_mappings=mappings or [],
    )


def _make_placement(start_ms: int = 0, end_ms: int = 5000) -> EffectPlacement:
    return EffectPlacement(
        effect_name="Color Wash",
        xlights_id="E_VALUECURVE_ColorWash",
        model_or_group="AllModels",
        start_ms=start_ms,
        end_ms=end_ms,
    )


def _make_hierarchy(num_frames: int = 200, fps: int = 40) -> HierarchyResult:
    """Build a minimal HierarchyResult with a full_mix energy curve.

    Default: 200 frames at 40 fps = 5 seconds of audio.
    Values ramp linearly from 0 to 100.
    """
    values = [int(i * 100 / max(num_frames - 1, 1)) for i in range(num_frames)]
    curve = ValueCurve(
        name="full_mix",
        stem_source="full_mix",
        fps=fps,
        values=values,
    )
    return HierarchyResult(
        schema_version="2.0.0",
        source_file="test.mp3",
        source_hash="abc123",
        duration_ms=int(num_frames * 1000 / fps),
        estimated_bpm=120.0,
        energy_curves={"full_mix": curve},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateValueCurves:
    """Tests for generate_value_curves()."""

    def test_no_mappings_returns_empty(self) -> None:
        """Effect with no analysis_mappings returns an empty dict."""
        effect_def = _make_effect_def(parameters=[], mappings=[])
        placement = _make_placement()
        hierarchy = _make_hierarchy()

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert result == {}

    def test_parameter_without_value_curve_support_skipped(self) -> None:
        """Mapping exists but parameter has supports_value_curve=False."""
        param = _make_parameter(name="brightness", supports_value_curve=False)
        mapping = _make_mapping(parameter="brightness")
        effect_def = _make_effect_def(parameters=[param], mappings=[mapping])
        placement = _make_placement()
        hierarchy = _make_hierarchy()

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert "brightness" not in result

    def test_linear_curve_shape(self) -> None:
        """Linear mapping from input range to output range produces correct points."""
        param = _make_parameter(name="brightness", supports_value_curve=True)
        mapping = _make_mapping(
            parameter="brightness",
            curve_shape="linear",
            input_min=0.0,
            input_max=100.0,
            output_min=0.0,
            output_max=100.0,
        )
        effect_def = _make_effect_def(parameters=[param], mappings=[mapping])
        placement = _make_placement(start_ms=0, end_ms=5000)
        hierarchy = _make_hierarchy(num_frames=200, fps=40)

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert "brightness" in result
        points = result["brightness"]
        assert len(points) > 0
        # Linear mapping: output should track input proportionally.
        # First point should map near 0, last point should map near 100.
        _x_first, y_first = points[0]
        _x_last, y_last = points[-1]
        assert y_first == pytest.approx(0.0, abs=2.0)
        assert y_last == pytest.approx(100.0, abs=2.0)

    def test_logarithmic_curve_shape(self) -> None:
        """Logarithmic mapping produces logarithmically scaled output."""
        param = _make_parameter(name="brightness", supports_value_curve=True)
        mapping = _make_mapping(
            parameter="brightness",
            curve_shape="logarithmic",
            input_min=0.0,
            input_max=100.0,
            output_min=0.0,
            output_max=100.0,
        )
        effect_def = _make_effect_def(parameters=[param], mappings=[mapping])
        placement = _make_placement(start_ms=0, end_ms=5000)
        hierarchy = _make_hierarchy(num_frames=200, fps=40)

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert "brightness" in result
        points = result["brightness"]
        # Log curve: midpoint input (50) should map above linear midpoint (50).
        mid_idx = len(points) // 2
        _x_mid, y_mid = points[mid_idx]
        assert y_mid > 50.0, (
            f"Logarithmic midpoint {y_mid} should be above linear midpoint 50"
        )

    def test_exponential_curve_shape(self) -> None:
        """Exponential mapping produces exponentially scaled output."""
        param = _make_parameter(name="brightness", supports_value_curve=True)
        mapping = _make_mapping(
            parameter="brightness",
            curve_shape="exponential",
            input_min=0.0,
            input_max=100.0,
            output_min=0.0,
            output_max=100.0,
        )
        effect_def = _make_effect_def(parameters=[param], mappings=[mapping])
        placement = _make_placement(start_ms=0, end_ms=5000)
        hierarchy = _make_hierarchy(num_frames=200, fps=40)

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert "brightness" in result
        points = result["brightness"]
        # Exp curve: midpoint input (50) should map below linear midpoint (50).
        mid_idx = len(points) // 2
        _x_mid, y_mid = points[mid_idx]
        assert y_mid < 50.0, (
            f"Exponential midpoint {y_mid} should be below linear midpoint 50"
        )

    def test_step_curve_shape(self) -> None:
        """Step mapping with threshold produces binary output."""
        param = _make_parameter(name="brightness", supports_value_curve=True)
        mapping = _make_mapping(
            parameter="brightness",
            curve_shape="step",
            mapping_type="threshold_trigger",
            input_min=0.0,
            input_max=100.0,
            output_min=0.0,
            output_max=100.0,
            threshold=50.0,
        )
        effect_def = _make_effect_def(parameters=[param], mappings=[mapping])
        placement = _make_placement(start_ms=0, end_ms=5000)
        hierarchy = _make_hierarchy(num_frames=200, fps=40)

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert "brightness" in result
        points = result["brightness"]
        # Step/threshold: every y value should be either output_min or output_max.
        y_values = {y for _x, y in points}
        assert y_values <= {0.0, 100.0}, (
            f"Step curve should produce only 0.0 or 100.0, got {y_values}"
        )

    def test_range_mapping(self) -> None:
        """Input range [0, 100] maps to output range [10, 90] correctly."""
        param = _make_parameter(name="brightness", supports_value_curve=True, min_val=0, max_val=100)
        mapping = _make_mapping(
            parameter="brightness",
            curve_shape="linear",
            input_min=0.0,
            input_max=100.0,
            output_min=10.0,
            output_max=90.0,
        )
        effect_def = _make_effect_def(parameters=[param], mappings=[mapping])
        placement = _make_placement(start_ms=0, end_ms=5000)
        hierarchy = _make_hierarchy(num_frames=200, fps=40)

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert "brightness" in result
        points = result["brightness"]
        y_values = [y for _x, y in points]
        assert min(y_values) >= 10.0 - 1.0, (
            f"Output minimum {min(y_values)} should be >= ~10.0"
        )
        assert max(y_values) <= 90.0 + 1.0, (
            f"Output maximum {max(y_values)} should be <= ~90.0"
        )

    def test_downsampling_to_100_points(self) -> None:
        """Input with 500 frames downsamples to at most 100 control points."""
        param = _make_parameter(name="brightness", supports_value_curve=True)
        mapping = _make_mapping(parameter="brightness")
        effect_def = _make_effect_def(parameters=[param], mappings=[mapping])
        placement = _make_placement(start_ms=0, end_ms=12500)
        hierarchy = _make_hierarchy(num_frames=500, fps=40)

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert "brightness" in result
        points = result["brightness"]
        assert len(points) <= 100, (
            f"Expected at most 100 control points, got {len(points)}"
        )

    def test_normalized_x_positions(self) -> None:
        """X values range from 0.0 to 1.0 within the effect span."""
        param = _make_parameter(name="brightness", supports_value_curve=True)
        mapping = _make_mapping(parameter="brightness")
        effect_def = _make_effect_def(parameters=[param], mappings=[mapping])
        placement = _make_placement(start_ms=1000, end_ms=4000)
        hierarchy = _make_hierarchy(num_frames=200, fps=40)

        result = generate_value_curves(placement, effect_def, hierarchy)

        assert "brightness" in result
        points = result["brightness"]
        x_values = [x for x, _y in points]
        assert min(x_values) == pytest.approx(0.0, abs=0.01)
        assert max(x_values) == pytest.approx(1.0, abs=0.01)
        # X values should be monotonically non-decreasing.
        for i in range(1, len(x_values)):
            assert x_values[i] >= x_values[i - 1], (
                f"X values not monotonic at index {i}: {x_values[i]} < {x_values[i-1]}"
            )
