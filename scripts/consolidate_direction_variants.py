#!/usr/bin/env python3
"""Consolidate directional variant pairs into single variants with direction_cycle.

This script processes all builtin variant JSON files and merges variants that
are identical except for their direction parameter value into a single variant
with a direction_cycle field.

Run from project root:
    python3 scripts/consolidate_direction_variants.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BUILTINS_DIR = Path(__file__).parent.parent / "src" / "variants" / "builtins"

# Direction value → mode classification
HORIZONTAL_VALUES = {"left", "right", "Left", "Right", "Left to Right", "Right to Left"}
VERTICAL_VALUES = {"up", "down", "Up", "Down"}
RADIAL_VALUES = {
    "compress", "expand", "Compress", "Expand",
    "H-compress", "H-expand", "V-compress", "V-expand",
    "In", "Out", "in", "out",
}
FIXED_VALUES = {"Normal", "normal", "None"}

# Cycle value pairs per mode per direction param
CYCLES: dict[str, dict[str, list[str]]] = {
    "horizontal": {
        "E_CHOICE_Bars_Direction": ["left", "right"],
        "E_CHOICE_Wave_Direction": ["Left to Right", "Right to Left"],
        "E_CHOICE_Fill_Direction": ["Left", "Right"],
        "E_CHOICE_Pictures_Direction": ["left", "right"],
        "E_CHOICE_Skips_Direction": ["Left", "Right"],
    },
    "vertical": {
        "E_CHOICE_Bars_Direction": ["up", "down"],
        "E_CHOICE_Fill_Direction": ["Up", "Down"],
        "E_CHOICE_Pictures_Direction": ["up", "down"],
    },
    "radial": {
        "E_CHOICE_Bars_Direction": ["expand", "compress"],
    },
}

# Words to strip from names when consolidating
DIRECTION_WORDS = re.compile(
    r"\b(Left|Right|Up|Down|left|right|up|down)\b",
    re.IGNORECASE,
)


def classify_direction_value(value: str) -> str | None:
    """Return mode label for a direction param value, or None if unknown."""
    if value in HORIZONTAL_VALUES:
        return "horizontal"
    if value in VERTICAL_VALUES:
        return "vertical"
    if value in RADIAL_VALUES:
        return "radial"
    if value in FIXED_VALUES:
        return "fixed"
    return None


def find_direction_param(overrides: dict) -> tuple[str, str] | None:
    """Find the direction parameter key and value in overrides, if any."""
    for key, val in overrides.items():
        if "_Direction" in key and isinstance(val, str):
            return key, val
    return None


def make_group_key(variant: dict, dir_param: str) -> str:
    """Create a grouping key from overrides minus the direction param."""
    overrides = dict(variant["parameter_overrides"])
    overrides.pop(dir_param, None)
    return json.dumps(
        {"base_effect": variant["base_effect"], "params": overrides},
        sort_keys=True,
    )


def clean_name(name: str, mode: str) -> str:
    """Remove direction words from name and append mode label."""
    cleaned = DIRECTION_WORDS.sub("", name)
    # Clean up extra spaces and trailing letters like " A", " B" that were suffixes
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Remove trailing single-letter suffixes that were disambiguation (e.g. "A", "B")
    cleaned = re.sub(r"\s+[A-Z]$", "", cleaned)
    # Append mode
    if not cleaned.endswith(mode.capitalize()):
        cleaned = f"{cleaned} {mode.capitalize()}"
    # Clean double spaces again
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def consolidate_file(filepath: Path) -> bool:
    """Process one effect JSON file. Returns True if changes were made."""
    with open(filepath) as f:
        data = json.load(f)

    variants = data.get("variants", [])
    if not variants:
        return False

    # Separate variants by whether they have a direction param
    has_direction: list[tuple[int, str, str, str]] = []  # (idx, dir_param, dir_value, mode)
    no_direction_indices: list[int] = []
    fixed_updated = False

    for i, v in enumerate(variants):
        dp = find_direction_param(v["parameter_overrides"])
        if dp is None:
            no_direction_indices.append(i)
            continue
        dir_param, dir_value = dp
        mode = classify_direction_value(dir_value)
        if mode is None:
            # Unknown direction value (e.g. "down-left") — leave unchanged
            no_direction_indices.append(i)
            continue
        if mode == "fixed":
            # Fixed direction — leave as-is, just update tags
            if v["tags"].get("direction") != "fixed":
                v["tags"]["direction"] = "fixed"
                fixed_updated = True
            no_direction_indices.append(i)
            continue
        has_direction.append((i, dir_param, dir_value, mode))

    if not has_direction:
        if fixed_updated:
            data["variants"] = variants
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            print(f"  {filepath.name}: updated {len(variants)} variants (fixed direction tags)")
            return True
        return False

    # Group direction variants by (group_key, mode)
    groups: dict[tuple[str, str, str], list[int]] = {}
    for idx, dir_param, dir_value, mode in has_direction:
        gkey = make_group_key(variants[idx], dir_param)
        key = (gkey, mode, dir_param)
        groups.setdefault(key, []).append(idx)

    new_variants = []
    consumed_indices: set[int] = set()

    for (gkey, mode, dir_param), indices in groups.items():
        if len(indices) >= 2:
            # True pair/group — merge them
            canonical = dict(variants[indices[0]])  # deep-ish copy
            canonical["parameter_overrides"] = dict(canonical["parameter_overrides"])
            canonical["parameter_overrides"].pop(dir_param, None)
            canonical["tags"] = dict(canonical["tags"])
            canonical["tags"]["direction"] = mode

            # Get cycle values
            if mode in CYCLES and dir_param in CYCLES[mode]:
                cycle_values = CYCLES[mode][dir_param]
            else:
                # Collect actual values from the group
                cycle_values = []
                for idx in indices:
                    dp = find_direction_param(variants[idx]["parameter_overrides"])
                    if dp and dp[1] not in cycle_values:
                        cycle_values.append(dp[1])

            canonical["direction_cycle"] = {
                "param": dir_param,
                "values": cycle_values,
                "mode": "alternate",
            }
            canonical["name"] = clean_name(canonical["name"], mode)
            new_variants.append(canonical)
            consumed_indices.update(indices)
        else:
            # Singleton with direction — still add cycle with known pair
            idx = indices[0]
            canonical = dict(variants[idx])
            canonical["parameter_overrides"] = dict(canonical["parameter_overrides"])
            canonical["parameter_overrides"].pop(dir_param, None)
            canonical["tags"] = dict(canonical["tags"])
            canonical["tags"]["direction"] = mode

            if mode in CYCLES and dir_param in CYCLES[mode]:
                cycle_values = CYCLES[mode][dir_param]
            else:
                # Only have one value, use it alone (shouldn't normally happen)
                dp = find_direction_param(variants[idx]["parameter_overrides"])
                cycle_values = [dp[1]] if dp else []

            canonical["direction_cycle"] = {
                "param": dir_param,
                "values": cycle_values,
                "mode": "alternate",
            }
            canonical["name"] = clean_name(canonical["name"], mode)
            new_variants.append(canonical)
            consumed_indices.add(idx)

    # Add unchanged variants
    for i in no_direction_indices:
        if i not in consumed_indices:
            new_variants.append(variants[i])

    # Check for name conflicts
    names_seen: dict[str, int] = {}
    for v in new_variants:
        name = v["name"]
        if name in names_seen:
            names_seen[name] += 1
            v["name"] = f"{name} {chr(64 + names_seen[name])}"  # A, B, C...
        else:
            names_seen[name] = 0

    data["variants"] = new_variants

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"  {filepath.name}: {len(variants)} → {len(new_variants)} variants")
    return True


def main():
    print("Consolidating direction variants...")
    changed = 0
    for filepath in sorted(BUILTINS_DIR.glob("*.json")):
        if filepath.name.startswith("_"):
            continue
        if consolidate_file(filepath):
            changed += 1
    print(f"\nDone. {changed} files updated.")


if __name__ == "__main__":
    main()
