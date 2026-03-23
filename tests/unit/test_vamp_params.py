"""005: Tests for VampParamDiscovery."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.vamp_params import (
    ParameterDescriptor,
    PluginNotFoundError,
    VampParamDiscovery,
)

# ---------------------------------------------------------------------------
# Fake descriptor helpers
# ---------------------------------------------------------------------------

def _make_raw_descriptor(
    identifier: str,
    name: str,
    description: str = "",
    unit: str = "",
    min_value: float = 0.0,
    max_value: float = 100.0,
    default_value: float = 50.0,
    is_quantized: bool = False,
    quantize_step: float = 1.0,
    value_names: list[str] | None = None,
) -> MagicMock:
    d = MagicMock()
    d.identifier = identifier
    d.name = name
    d.description = description
    d.unit = unit
    d.min_value = min_value
    d.max_value = max_value
    d.default_value = default_value
    d.is_quantized = is_quantized
    d.quantize_step = quantize_step
    d.value_names = value_names or []
    return d


def _make_plugin(descriptors: list) -> MagicMock:
    plugin = MagicMock()
    plugin.get_parameter_descriptors.return_value = descriptors
    return plugin


SENSITIVITY_DESC = _make_raw_descriptor(
    "sensitivity", "Sensitivity", min_value=0.0, max_value=100.0, default_value=50.0
)
DFTYPE_DESC = _make_raw_descriptor(
    "dftype", "Detection Function Type",
    min_value=0.0, max_value=3.0, default_value=3.0,
    is_quantized=True, quantize_step=1.0,
    value_names=["HFC", "Spectral", "Phase", "Complex"],
)


# ---------------------------------------------------------------------------
# list_params
# ---------------------------------------------------------------------------

class TestListParams:
    def test_returns_parameter_descriptor_list(self):
        plugin = _make_plugin([SENSITIVITY_DESC, DFTYPE_DESC])
        discovery = VampParamDiscovery()
        with patch.object(discovery, "_load_plugin", return_value=plugin):
            result = discovery.list_params("qm-vamp-plugins:qm-onsetdetector")
        assert len(result) == 2
        assert isinstance(result[0], ParameterDescriptor)
        assert result[0].identifier == "sensitivity"
        assert result[0].min_value == 0.0
        assert result[0].max_value == 100.0
        assert result[0].default_value == 50.0

    def test_maps_enum_parameter_correctly(self):
        plugin = _make_plugin([DFTYPE_DESC])
        discovery = VampParamDiscovery()
        with patch.object(discovery, "_load_plugin", return_value=plugin):
            result = discovery.list_params("qm-vamp-plugins:qm-onsetdetector")
        desc = result[0]
        assert desc.is_quantized is True
        assert desc.value_names == ["HFC", "Spectral", "Phase", "Complex"]

    def test_raises_plugin_not_found_when_load_fails(self):
        discovery = VampParamDiscovery()
        with patch.object(discovery, "_load_plugin", side_effect=PluginNotFoundError("not found")):
            with pytest.raises(PluginNotFoundError):
                discovery.list_params("nonexistent:plugin")

    def test_empty_parameter_list(self):
        plugin = _make_plugin([])
        discovery = VampParamDiscovery()
        with patch.object(discovery, "_load_plugin", return_value=plugin):
            result = discovery.list_params("beatroot-vamp:beatroot")
        assert result == []


# ---------------------------------------------------------------------------
# suggest_values
# ---------------------------------------------------------------------------

class TestSuggestValues:
    def _desc(self) -> ParameterDescriptor:
        return ParameterDescriptor(
            identifier="sensitivity", name="Sensitivity", description="",
            unit="", min_value=0.0, max_value=100.0, default_value=50.0,
            is_quantized=False, quantize_step=1.0, value_names=[],
        )

    def test_returns_correct_count(self):
        desc = self._desc()
        values = VampParamDiscovery().suggest_values(desc, steps=5)
        assert len(values) == 5

    def test_includes_min_and_max(self):
        desc = self._desc()
        values = VampParamDiscovery().suggest_values(desc, steps=5)
        assert values[0] == pytest.approx(0.0)
        assert values[-1] == pytest.approx(100.0)

    def test_evenly_spaced(self):
        desc = self._desc()
        values = VampParamDiscovery().suggest_values(desc, steps=5)
        assert values == pytest.approx([0.0, 25.0, 50.0, 75.0, 100.0])

    def test_single_step_returns_midpoint(self):
        desc = self._desc()
        values = VampParamDiscovery().suggest_values(desc, steps=1)
        assert len(values) == 1
        assert values[0] == pytest.approx(50.0)  # midpoint of [0, 100]

    def test_raises_for_pure_enum(self):
        desc = ParameterDescriptor(
            identifier="dftype", name="Type", description="",
            unit="", min_value=0.0, max_value=3.0, default_value=3.0,
            is_quantized=True, quantize_step=1.0,
            value_names=["HFC", "Spectral", "Phase", "Complex"],
        )
        with pytest.raises(ValueError, match="enum"):
            VampParamDiscovery().suggest_values(desc, steps=5)


# ---------------------------------------------------------------------------
# validate_params
# ---------------------------------------------------------------------------

class TestValidateParams:
    def _discovery_with(self, descriptors: list) -> VampParamDiscovery:
        plugin = _make_plugin(descriptors)
        discovery = VampParamDiscovery()
        discovery._load_plugin = MagicMock(return_value=plugin)
        return discovery

    def test_valid_params_returns_empty_list(self):
        discovery = self._discovery_with([SENSITIVITY_DESC, DFTYPE_DESC])
        errors = discovery.validate_params(
            "qm-vamp-plugins:qm-onsetdetector",
            {"sensitivity": 50.0, "dftype": 3},
        )
        assert errors == []

    def test_unknown_param_key_is_an_error(self):
        discovery = self._discovery_with([SENSITIVITY_DESC])
        errors = discovery.validate_params(
            "qm-vamp-plugins:qm-onsetdetector",
            {"nonexistent": 1.0},
        )
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_out_of_range_value_is_an_error(self):
        discovery = self._discovery_with([SENSITIVITY_DESC])
        errors = discovery.validate_params(
            "qm-vamp-plugins:qm-onsetdetector",
            {"sensitivity": 150.0},
        )
        assert len(errors) == 1
        assert "sensitivity" in errors[0]

    def test_quantized_param_invalid_step_is_an_error(self):
        discovery = self._discovery_with([DFTYPE_DESC])
        errors = discovery.validate_params(
            "qm-vamp-plugins:qm-onsetdetector",
            {"dftype": 1.5},
        )
        assert len(errors) == 1
        assert "dftype" in errors[0]

    def test_quantized_param_valid_step_passes(self):
        discovery = self._discovery_with([DFTYPE_DESC])
        errors = discovery.validate_params(
            "qm-vamp-plugins:qm-onsetdetector",
            {"dftype": 2.0},
        )
        assert errors == []

    def test_plugin_not_found_raises(self):
        discovery = VampParamDiscovery()
        discovery._load_plugin = MagicMock(side_effect=PluginNotFoundError("bad"))
        with pytest.raises(PluginNotFoundError):
            discovery.validate_params("bad:plugin", {"x": 1})
