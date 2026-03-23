"""005: Vamp plugin parameter discovery and validation."""
from __future__ import annotations

import math
from dataclasses import dataclass, field


class PluginNotFoundError(Exception):
    """Raised when a Vamp plugin cannot be loaded."""


@dataclass
class ParameterDescriptor:
    """Metadata about a single tunable Vamp plugin parameter."""

    identifier: str
    name: str
    description: str
    unit: str
    min_value: float
    max_value: float
    default_value: float
    is_quantized: bool
    quantize_step: float
    value_names: list[str] = field(default_factory=list)


class VampParamDiscovery:
    """
    Runtime discovery and validation of Vamp plugin parameters.

    Uses vamp.vampyhost to load plugins and inspect their parameter
    descriptors without running any audio analysis.
    """

    def list_params(
        self,
        plugin_key: str,
        sample_rate: int = 44100,
    ) -> list[ParameterDescriptor]:
        """
        Return all tunable parameters for *plugin_key*.

        Raises PluginNotFoundError if the plugin cannot be loaded.
        """
        plugin = self._load_plugin(plugin_key, sample_rate)
        raw = plugin.get_parameter_descriptors()
        return [self._map_descriptor(d) for d in raw]

    def suggest_values(
        self,
        descriptor: ParameterDescriptor,
        steps: int,
    ) -> list[float]:
        """
        Return *steps* evenly-spaced candidate values across the parameter range.

        For a pure enum parameter (value_names non-empty and range equals
        0..len-1), raises ValueError — list the allowed indices explicitly instead.

        When steps == 1 returns the midpoint of the range.
        """
        if descriptor.value_names and descriptor.is_quantized:
            n = len(descriptor.value_names)
            expected_max = float(n - 1)
            if (
                math.isclose(descriptor.min_value, 0.0)
                and math.isclose(descriptor.max_value, expected_max)
            ):
                raise ValueError(
                    f"Parameter '{descriptor.identifier}' is a pure enum — "
                    f"choose from indices 0..{n - 1} ({', '.join(descriptor.value_names)})"
                )

        lo, hi = descriptor.min_value, descriptor.max_value
        if steps == 1:
            return [(lo + hi) / 2.0]
        return [lo + (hi - lo) * i / (steps - 1) for i in range(steps)]

    def validate_params(
        self,
        plugin_key: str,
        params: dict[str, float],
        sample_rate: int = 44100,
    ) -> list[str]:
        """
        Validate *params* against *plugin_key*'s parameter schema.

        Returns a list of error strings; empty list means all params are valid.
        Raises PluginNotFoundError if the plugin cannot be loaded.
        """
        descriptors = {d.identifier: d for d in self.list_params(plugin_key, sample_rate)}
        errors: list[str] = []

        for key, value in params.items():
            if key not in descriptors:
                errors.append(
                    f"Unknown parameter '{key}' for plugin '{plugin_key}'. "
                    f"Valid keys: {sorted(descriptors)}"
                )
                continue

            desc = descriptors[key]
            if value < desc.min_value or value > desc.max_value:
                errors.append(
                    f"Parameter '{key}' value {value} is out of range "
                    f"[{desc.min_value}, {desc.max_value}]"
                )
                continue

            if desc.is_quantized and desc.quantize_step > 0:
                remainder = (value - desc.min_value) % desc.quantize_step
                # Allow a small floating-point tolerance
                if remainder > 1e-6 and (desc.quantize_step - remainder) > 1e-6:
                    errors.append(
                        f"Parameter '{key}' value {value} does not align to "
                        f"quantize step {desc.quantize_step} "
                        f"(min={desc.min_value})"
                    )

        return errors

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_plugin(self, plugin_key: str, sample_rate: int = 44100):
        """Load and return the raw vamp plugin object."""
        try:
            import vamp.vampyhost as _vh
            return _vh.load_plugin(plugin_key, sample_rate)
        except Exception as exc:
            raise PluginNotFoundError(
                f"Cannot load Vamp plugin '{plugin_key}': {exc}"
            ) from exc

    @staticmethod
    def _map_descriptor(raw) -> ParameterDescriptor:
        return ParameterDescriptor(
            identifier=raw.identifier,
            name=raw.name,
            description=getattr(raw, "description", ""),
            unit=getattr(raw, "unit", ""),
            min_value=float(raw.min_value),
            max_value=float(raw.max_value),
            default_value=float(raw.default_value),
            is_quantized=bool(raw.is_quantized),
            quantize_step=float(getattr(raw, "quantize_step", 1.0)),
            value_names=list(getattr(raw, "value_names", []) or []),
        )
