# Data Model: Effect & Variant Library UI Wiring

**Feature**: 031-effect-variant-ui-wiring
**Date**: 2026-04-01

## Entities

This feature introduces no new data entities. It wires existing entities into the UI. The relevant entities and their relationships are documented here for reference.

### EffectVariant (existing — src/variants/models.py)

A pre-tuned parameter configuration for a specific xLights effect.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Unique variant name (e.g. "Bars Single 3D Half-Cycle") |
| base_effect | str | The xLights effect this variant applies to (e.g. "Bars") |
| description | str | Human-readable description of the visual |
| parameter_overrides | dict[str, int\|float\|bool\|str] | Parameter values that differ from effect defaults |
| tags | VariantTags | Metadata for filtering and scoring |
| direction_cycle | dict \| None | Optional directional parameter rotation config |

### VariantTags (existing — src/variants/models.py)

Metadata tags used for filtering and scoring variant suggestions.

| Field | Type | Description |
|-------|------|-------------|
| tier_affinity | str \| None | background / mid / foreground / hero |
| energy_level | str \| None | low / medium / high |
| speed_feel | str \| None | slow / moderate / fast |
| direction | str \| None | Directional hint for the visual |
| section_roles | list[str] | verse / chorus / bridge / intro / outro / build / drop |
| scope | str \| None | single-prop / group |
| genre_affinity | str | "any" or specific genre |

### EffectLayer (existing — src/themes/models.py)

A single layer in a theme's layer stack.

| Field | Type | Description |
|-------|------|-------------|
| effect | str | Effect name (required) |
| blend_mode | str | Blend mode (default "Normal") |
| parameter_overrides | dict | Manual parameter tweaks |
| variant_ref | str \| None | **Reference to an EffectVariant by name** — currently unused in UI |

### Parameter Resolution Chain (existing — src/generator/effect_placer.py)

When `variant_ref` is set on an EffectLayer:
1. Start with empty params dict
2. Apply variant's `parameter_overrides`
3. Apply layer's `parameter_overrides` on top (layer wins on conflict)
4. Inherit `direction_cycle` from variant if layer doesn't specify one

## Relationships

```
EffectDefinition (1) ←── base_effect ──→ (N) EffectVariant
                                               ↑
Theme → EffectLayer ── variant_ref ────────────┘
```

- One EffectDefinition has zero or more EffectVariants (via `base_effect` field)
- One EffectLayer optionally references one EffectVariant (via `variant_ref` field)
- A Theme contains multiple EffectLayers in its `layers` list
- A Theme also contains "alternates" (formerly "theme variants") — alternate layer sets with their own EffectLayers

## UI State Model (new — frontend only)

The theme editor JS maintains in-memory state. This feature extends it:

| State Field | Type | Description |
|-------------|------|-------------|
| state.effects | array | Already loaded from `/themes/api/effects` |
| state.variantCache | dict | **New**: Maps effect name → variant list (fetched lazily from `/variants?effect=X`) |

The variant browser page has its own independent state:

| State Field | Type | Description |
|-------------|------|-------------|
| state.variants | array | All variants loaded from `/variants` |
| state.filters | dict | Active filter selections (effect, energy, tier, section, scope) |
| state.coverage | dict | Coverage stats from `/variants/coverage` |
| state.selectedVariant | object \| null | Currently selected variant for detail view |
