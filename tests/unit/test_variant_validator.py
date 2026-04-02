"""Tests for src/variants/validator.py — validate_variant()."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.effects.library import load_effect_library
from src.variants.validator import validate_variant

FIXTURES = Path(__file__).parent.parent / "fixtures"
EFFECTS_FIXTURES = FIXTURES / "effects"


@pytest.fixture
def effect_lib():
    return load_effect_library(builtin_path=EFFECTS_FIXTURES / "minimal_library_with_meteors.json")


def _valid_data() -> dict:
    return {
        "name": "Fire Blaze High",
        "base_effect": "Fire",
        "description": "Tall intense fire",
        "parameter_overrides": {
            "E_SLIDER_Fire_Height": 80,
        },
        "tags": {
            "tier_affinity": "foreground",
            "energy_level": "high",
        },
    }


class TestValidateVariant:
    def test_valid_variant_no_errors(self, effect_lib):
        errors = validate_variant(_valid_data(), effect_lib)
        assert errors == []

    def test_empty_overrides_valid(self, effect_lib):
        data = _valid_data()
        data["parameter_overrides"] = {}
        errors = validate_variant(data, effect_lib)
        assert errors == []

    def test_all_tags_none_valid(self, effect_lib):
        data = _valid_data()
        data["tags"] = {}
        errors = validate_variant(data, effect_lib)
        assert errors == []

    def test_missing_name(self, effect_lib):
        data = _valid_data()
        del data["name"]
        errors = validate_variant(data, effect_lib)
        assert any("name" in e.lower() for e in errors)

    def test_empty_name(self, effect_lib):
        data = _valid_data()
        data["name"] = ""
        errors = validate_variant(data, effect_lib)
        assert any("name" in e.lower() for e in errors)

    def test_missing_base_effect(self, effect_lib):
        data = _valid_data()
        del data["base_effect"]
        errors = validate_variant(data, effect_lib)
        assert any("base_effect" in e.lower() or "base effect" in e.lower() for e in errors)

    def test_unknown_base_effect(self, effect_lib):
        data = _valid_data()
        data["base_effect"] = "NonExistentEffect"
        errors = validate_variant(data, effect_lib)
        assert any("NonExistentEffect" in e or "base_effect" in e.lower() for e in errors)

    def test_missing_description(self, effect_lib):
        data = _valid_data()
        del data["description"]
        errors = validate_variant(data, effect_lib)
        assert any("description" in e.lower() for e in errors)

    def test_unknown_parameter_storage_name(self, effect_lib):
        data = _valid_data()
        data["parameter_overrides"]["E_SLIDER_Fire_NonExistent"] = 50
        errors = validate_variant(data, effect_lib)
        assert any("E_SLIDER_Fire_NonExistent" in e for e in errors)

    def test_parameter_value_above_max(self, effect_lib):
        data = _valid_data()
        data["parameter_overrides"]["E_SLIDER_Fire_Height"] = 999  # max is 100
        errors = validate_variant(data, effect_lib)
        assert any("range" in e.lower() or "max" in e.lower() or "999" in e for e in errors)

    def test_parameter_value_below_min(self, effect_lib):
        data = _valid_data()
        data["parameter_overrides"]["E_SLIDER_Fire_Height"] = -5  # min is 1
        errors = validate_variant(data, effect_lib)
        assert any("range" in e.lower() or "min" in e.lower() or "-5" in e for e in errors)

    def test_invalid_tier_affinity(self, effect_lib):
        data = _valid_data()
        data["tags"]["tier_affinity"] = "ultra-background"
        errors = validate_variant(data, effect_lib)
        assert any("tier_affinity" in e.lower() or "tier" in e.lower() for e in errors)

    def test_invalid_energy_level(self, effect_lib):
        data = _valid_data()
        data["tags"]["energy_level"] = "extreme"
        errors = validate_variant(data, effect_lib)
        assert any("energy" in e.lower() for e in errors)

    def test_invalid_speed_feel(self, effect_lib):
        data = _valid_data()
        data["tags"]["speed_feel"] = "ultra-fast"
        errors = validate_variant(data, effect_lib)
        assert any("speed" in e.lower() for e in errors)

    def test_invalid_section_role(self, effect_lib):
        data = _valid_data()
        data["tags"]["section_roles"] = ["verse", "unknown_section"]
        errors = validate_variant(data, effect_lib)
        assert any("section" in e.lower() or "unknown_section" in e for e in errors)

    def test_invalid_scope(self, effect_lib):
        data = _valid_data()
        data["tags"]["scope"] = "whole-house"
        errors = validate_variant(data, effect_lib)
        assert any("scope" in e.lower() for e in errors)

    def test_valid_none_tag_values(self, effect_lib):
        data = _valid_data()
        data["tags"] = {
            "tier_affinity": None,
            "energy_level": None,
            "speed_feel": None,
            "direction": None,
            "section_roles": [],
            "scope": None,
            "genre_affinity": "any",
        }
        errors = validate_variant(data, effect_lib)
        assert errors == []

    def test_returns_all_errors_at_once(self, effect_lib):
        """Validator should collect all errors, not fail-fast."""
        data = {
            "name": "",
            "base_effect": "NonExistent",
            "description": "",
            "parameter_overrides": {},
            "tags": {"energy_level": "extreme"},
        }
        errors = validate_variant(data, effect_lib)
        assert len(errors) >= 3  # name, base_effect, energy_level

    def test_name_none_is_rejected(self, effect_lib):
        """None is not a valid name value — must be a string."""
        data = _valid_data()
        data["name"] = None
        errors = validate_variant(data, effect_lib)
        assert any("name" in e.lower() for e in errors)

    def test_direction_cycle_invalid_param_name(self, effect_lib):
        """direction_cycle.param must reference a known parameter for the base effect."""
        data = _valid_data()
        data["direction_cycle"] = {
            "param": "E_CHOICE_Fire_NonExistent",
            "values": ["Left", "Right"],
            "mode": "alternate",
        }
        errors = validate_variant(data, effect_lib)
        assert any("direction_cycle param" in e and "not a known parameter" in e for e in errors)

    def test_direction_cycle_param_in_overrides_rejected(self, effect_lib):
        """direction_cycle.param must not also appear in parameter_overrides."""
        data = _valid_data()
        data["parameter_overrides"]["E_CHOICE_Fire_Location"] = "Top"
        data["direction_cycle"] = {
            "param": "E_CHOICE_Fire_Location",
            "values": ["Top", "Bottom"],
            "mode": "alternate",
        }
        errors = validate_variant(data, effect_lib)
        assert any("should not also appear in parameter_overrides" in e for e in errors)

    def test_wrong_type_parameter_value_returns_error_not_exception(self, effect_lib):
        """A string value for a numeric slider must return an error, not raise TypeError."""
        data = _valid_data()
        data["parameter_overrides"]["E_SLIDER_Fire_Height"] = "banana"
        errors = validate_variant(data, effect_lib)
        assert any("E_SLIDER_Fire_Height" in e for e in errors)
