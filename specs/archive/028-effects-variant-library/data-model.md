# Data Model: Effects Variant Library

**Feature**: 028-effects-variant-library
**Date**: 2026-04-01

## Entities

### EffectVariant

The core entity — a named, reusable parameter configuration of a base xLights effect.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | yes | — | Human-readable display name (e.g., "Meteors Gentle Rain") |
| `base_effect` | `str` | yes | — | Name of the parent effect from EffectDefinition (e.g., "Meteors") |
| `description` | `str` | yes | — | Visual description of what this variant looks like |
| `parameter_overrides` | `dict[str, int\|float\|bool\|str]` | yes | — | Parameter storage_name → value overrides |
| `tags` | `VariantTags` | yes | — | Variant-specific categorization metadata |

**Identity**: Two variants are considered duplicates when `base_effect` + sorted `parameter_overrides` are identical. `name` is a display label, not an identity key.

**Inheritance**: The following fields are NOT stored on the variant — they are inherited from the parent `EffectDefinition` at query time:
- `category` (color_wash, pattern, nature, movement, audio_reactive, media, utility)
- `layer_role` (standalone, modifier, either)
- `duration_type` (section, bar, beat, trigger)
- `prop_suitability` (dict of prop type → rating)
- `parameters` (full parameter schema with min/max/defaults)
- `analysis_mappings` (audio-reactive bindings)

**Excluded by design**: Color palette (theme-owned), blend mode (theme-layer-owned).

### VariantTags

Variant-specific categorization metadata. All fields are optional to support incremental tagging (e.g., imported variants start untagged).

| Field | Type | Required | Default | Valid Values |
|-------|------|----------|---------|--------------|
| `tier_affinity` | `str \| None` | no | `None` | `"background"`, `"mid"`, `"foreground"`, `"hero"` |
| `energy_level` | `str \| None` | no | `None` | `"low"`, `"medium"`, `"high"` |
| `speed_feel` | `str \| None` | no | `None` | `"slow"`, `"moderate"`, `"fast"` |
| `direction` | `str \| None` | no | `None` | Freeform (e.g., `"sweep-left"`, `"rain-down"`, `"expand-out"`, `"clockwise"`) |
| `section_roles` | `list[str]` | no | `[]` | `"verse"`, `"chorus"`, `"bridge"`, `"intro"`, `"outro"`, `"build"`, `"drop"` |
| `scope` | `str \| None` | no | `None` | `"single-prop"`, `"group"` |
| `genre_affinity` | `str` | no | `"any"` | `"any"`, `"rock"`, `"pop"`, `"classical"`, `"electronic"`, etc. |

### VariantCatalog (JSON root)

The top-level container for the builtin_variants.json file.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | `str` | yes | Semantic version (e.g., "1.0.0") |
| `variants` | `list[dict]` | yes | Array of serialized EffectVariant objects |

### VariantLibrary (runtime)

In-memory collection of all loaded variants (built-in + custom merged).

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `str` | From builtin catalog |
| `variants` | `dict[str, EffectVariant]` | name → variant (custom overrides built-in) |

## Relationships

```text
EffectDefinition (1) ←── references ──→ (many) EffectVariant
    base_effect field points to EffectDefinition.name

Theme.EffectLayer (1) ←── optionally references ──→ (0..1) EffectVariant
    variant_ref field points to EffectVariant.name
    When present: variant parameters merge over base effect defaults
    When absent: existing parameter_overrides behavior unchanged

Resolution chain (generator):
    base effect defaults → variant parameter_overrides → theme layer parameter_overrides
```

## Modified Existing Entity: EffectLayer

One new optional field added to `src/themes/models.py`:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `variant_ref` | `str \| None` | no | `None` | Name of an EffectVariant to use. When set, the variant's parameter_overrides are applied before the layer's own parameter_overrides. |

**Backward compatibility**: Existing themes without `variant_ref` work identically to today. The field defaults to `None`.

## Validation Rules

### Variant Validation (validate_variant)
1. `name` must be non-empty string
2. `base_effect` must exist in `EffectLibrary`
3. All keys in `parameter_overrides` must be valid `storage_name` values from the base effect's parameter list
4. All values in `parameter_overrides` must be within the min/max range defined by the corresponding parameter
5. `tags.tier_affinity` must be one of the valid enum values or None
6. `tags.energy_level` must be one of the valid enum values or None
7. `tags.speed_feel` must be one of the valid enum values or None
8. `tags.section_roles` items must all be valid section role values
9. `tags.scope` must be one of the valid enum values or None

### Theme Validation (extended)
1. If `variant_ref` is set on a layer, it must resolve to an existing variant in `VariantLibrary`
2. If `variant_ref` is set, the variant's `base_effect` must match the layer's `effect` field
3. If variant not found, warn (not error) and fall back to base effect defaults (FR-008)

### Import Deduplication
1. Two variants are duplicates when `base_effect` is identical AND `parameter_overrides` (sorted by key) are identical
2. During import, duplicates are flagged for user decision: skip, merge (keep existing name/tags), or create as new

## JSON Schema (variant file)

```json
{
  "name": "Meteors Gentle Rain",
  "base_effect": "Meteors",
  "description": "Soft falling meteors with long trails and slow speed, ideal for ambient verse sections",
  "parameter_overrides": {
    "E_SLIDER_Meteors_Count": 5,
    "E_SLIDER_Meteors_Length": 40,
    "E_SLIDER_Meteors_Speed": 8,
    "E_CHOICE_Meteors_Effect": "Down"
  },
  "tags": {
    "tier_affinity": "background",
    "energy_level": "low",
    "speed_feel": "slow",
    "direction": "rain-down",
    "section_roles": ["verse", "intro", "outro"],
    "scope": "single-prop",
    "genre_affinity": "any"
  }
}
```

## Scoring Model

When ranking variants for automated selection, each dimension contributes a weighted score:

| Dimension | Weight | Scoring |
|-----------|--------|---------|
| Prop suitability (inherited) | 0.30 | ideal=1.0, good=0.7, possible=0.4, not_recommended=0.1 |
| Energy match | 0.25 | exact=1.0, adjacent=0.5, mismatch=0.0 |
| Tier affinity match | 0.20 | exact=1.0, adjacent=0.5, mismatch=0.2 |
| Section role match | 0.15 | present=1.0, absent=0.3 |
| Scope match | 0.05 | exact=1.0, mismatch=0.5 |
| Genre match | 0.05 | exact=1.0, "any"=0.8, mismatch=0.3 |

**Fallback order** when no results: drop section role → drop genre → widen energy → widen tier → drop scope → return all for base effect by prop suitability.
