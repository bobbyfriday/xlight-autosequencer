"""Validate effect variant definitions."""
from __future__ import annotations

from src.effects.library import EffectLibrary
from src.variants.models import (
    VALID_ENERGY_LEVELS,
    VALID_SCOPES,
    VALID_SECTION_ROLES,
    VALID_SPEED_FEELS,
    VALID_TIER_AFFINITIES,
)

_REQUIRED_FIELDS = ("name", "base_effect", "description")


def validate_variant(data: dict, effect_library: EffectLibrary) -> list[str]:
    """Validate a parsed variant dict against the effect library.

    Returns a list of error messages (empty list = valid). Collects all errors
    rather than failing on the first one.
    """
    errors: list[str] = []

    # Required top-level fields — must be present, string-typed, and non-empty
    for f in _REQUIRED_FIELDS:
        if f not in data:
            errors.append(f"Missing required field: {f}")
        elif not isinstance(data[f], str):
            errors.append(f"Field '{f}' must be a string, got {type(data[f]).__name__}")
        elif not data[f].strip():
            errors.append(f"Field '{f}' must not be empty")

    # base_effect must reference a known effect
    base_effect = data.get("base_effect", "")
    effect_defn = None
    if isinstance(base_effect, str) and base_effect:
        effect_defn = effect_library.get(base_effect)
        if effect_defn is None:
            errors.append(
                f"Unknown base_effect '{base_effect}' — not found in effect library"
            )

    # parameter_overrides: each key must be a known storage_name for the base effect
    overrides = data.get("parameter_overrides", {})
    if effect_defn is not None and isinstance(overrides, dict):
        known_params = {p.storage_name: p for p in effect_defn.parameters}
        for storage_name, value in overrides.items():
            if storage_name not in known_params:
                errors.append(
                    f"Unknown parameter override '{storage_name}' for effect '{base_effect}'"
                )
                continue
            param = known_params[storage_name]
            try:
                if param.min is not None and value < param.min:
                    errors.append(
                        f"Parameter '{storage_name}' value {value} is below min {param.min}"
                    )
                if param.max is not None and value > param.max:
                    errors.append(
                        f"Parameter '{storage_name}' value {value} exceeds max {param.max}"
                    )
            except TypeError:
                errors.append(
                    f"Parameter '{storage_name}' value {value!r} has wrong type"
                    f" (expected numeric, got {type(value).__name__})"
                )

    # tags validation
    tags = data.get("tags", {})
    if isinstance(tags, dict):
        tier = tags.get("tier_affinity")
        if tier is not None and tier not in VALID_TIER_AFFINITIES:
            errors.append(
                f"Invalid tier_affinity '{tier}' — must be one of {list(VALID_TIER_AFFINITIES)}"
            )

        energy = tags.get("energy_level")
        if energy is not None and energy not in VALID_ENERGY_LEVELS:
            errors.append(
                f"Invalid energy_level '{energy}' — must be one of {list(VALID_ENERGY_LEVELS)}"
            )

        speed = tags.get("speed_feel")
        if speed is not None and speed not in VALID_SPEED_FEELS:
            errors.append(
                f"Invalid speed_feel '{speed}' — must be one of {list(VALID_SPEED_FEELS)}"
            )

        scope = tags.get("scope")
        if scope is not None and scope not in VALID_SCOPES:
            errors.append(
                f"Invalid scope '{scope}' — must be one of {list(VALID_SCOPES)}"
            )

        section_roles = tags.get("section_roles", [])
        if isinstance(section_roles, list):
            for role in section_roles:
                if role not in VALID_SECTION_ROLES:
                    errors.append(
                        f"Invalid section_role '{role}' — must be one of {list(VALID_SECTION_ROLES)}"
                    )

    return errors
