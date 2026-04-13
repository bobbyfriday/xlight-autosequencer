# Data Model: Focused Effect Vocabulary + Embrace Repetition

## Entities

### WorkingSet

A weighted list of effects derived from a theme's layer structure at generation time.

| Field | Type | Description |
|-------|------|-------------|
| effects | list[WorkingSetEntry] | Ordered by weight descending |
| theme_name | str | Source theme name (for debugging/logging) |

### WorkingSetEntry

A single effect in the working set with its selection weight.

| Field | Type | Description |
|-------|------|-------------|
| effect_name | str | Base effect name (e.g., "Butterfly") |
| variant_name | str | Specific variant name (e.g., "Butterfly Medium Fast") |
| weight | float | Selection probability weight (0.0-1.0, all entries sum to 1.0) |
| source | str | "layer_0", "layer_1", "effect_pool", "alternate" |

### RepetitionPolicy

Controls how the rotation engine handles repeated variant selections.

| Field | Type | Description |
|-------|------|-------------|
| allow_intra_section_reuse | bool | If True, same variant can repeat within a section without penalty (default: True) |
| cross_section_penalty | float | Multiplier for same-label cross-section reuse (default: 0.85, was 0.5) |

## Derivation Rules

### WorkingSet from Theme

Given a Theme with N layers:

1. **Layer weights**: Layer 0 gets weight 0.40, layer 1 gets 0.20, layer 2 gets 0.10, etc.
   (each layer = previous / 2). Minimum layer weight = 0.05.

2. **Effect pool expansion**: If a layer has an `effect_pool` list, the layer's weight is
   split evenly across the pool variants. The layer's own variant is included in the split.

3. **Alternate layers**: Each alternate set contributes its variants at weight 0.05 each.

4. **Normalization**: All weights are normalized to sum to 1.0.

5. **Deduplication**: If the same base effect appears in multiple layers (different variants),
   their weights are summed under the highest-weighted variant.

### Example: "Stellar Wind" (3 layers + 2 alternates)

| Entry | Effect | Variant | Raw Weight | Normalized |
|-------|--------|---------|------------|------------|
| 1 | Butterfly | Butterfly Medium Fast | 0.40 | 0.40 |
| 2 | Shockwave | Shockwave Medium Thin | 0.20 | 0.20 |
| 3 | Ripple | Ripple Fast Medium | 0.033 | 0.033 |
| 4 | Ripple | Ripple Circle | 0.033 | 0.033 |
| 5 | Spirals | Spirals 3D Slow Spin | 0.033 | 0.033 |
| 6 | Wave | Wave Dual Medium | 0.05 | 0.05 |
| 7 | Spirals | Spirals Directed Medium | 0.05 | 0.05 |

After normalization and Spirals dedup: Butterfly 0.40, Shockwave 0.20, Spirals 0.08,
Ripple 0.07, Wave 0.05. Remaining distributed to maintain sum = 1.0.

Top-5 effects account for 100% (only 5 unique effects). Target met.

## State Transitions

### WorkingSet Lifecycle

```
Theme loaded → WorkingSet derived (once per theme per generation)
                    ↓
           Used for all sections assigned to this theme
                    ↓
           Discarded at end of generation
```

WorkingSets are stateless — derived fresh each generation run. No persistence needed.

## Relationships

```
Theme (1) ──derives──→ WorkingSet (1)
WorkingSet (1) ──contains──→ WorkingSetEntry (4-8)
WorkingSetEntry (1) ──references──→ EffectVariant (1) ──references──→ EffectDefinition (1)
RepetitionPolicy (1) ──applied to──→ RotationEngine (1)
```
