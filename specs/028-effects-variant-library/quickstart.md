# Quickstart: Effects Variant Library

**Feature**: 028-effects-variant-library
**Date**: 2026-04-01

## What This Feature Does

The effects variant library adds a layer between base xLights effects and themes. Instead of themes specifying raw parameter overrides for each effect, they can reference named **variants** — proven, described, and categorized configurations of effects. The sequence generator can then intelligently select the best variant for each placement based on prop type, energy level, song section, and more.

## Key Concepts

- **Effect Variant**: A named set of parameter overrides for a base xLights effect, plus categorization tags (tier affinity, energy, speed, direction, section roles, scope, genre).
- **Variant Catalog**: Built-in (100+ shipped) + custom user variants. Queried by the generator for automated selection.
- **Variant Reference**: A theme layer can point to a variant by name instead of inline parameter overrides.
- **Variant Import**: Mine .xsq sequence files for proven effect configurations.

## Architecture

```
EffectDefinition (base)
       │
       ▼
EffectVariant (configuration + tags)
       │
       ▼
Theme.EffectLayer.variant_ref ──→ resolved at generation time
       │
       ▼
EffectPlacement (in sequence plan)
```

**Resolution chain**: base effect defaults → variant parameter_overrides → theme layer parameter_overrides

## New Module: `src/variants/`

| File | Purpose |
|------|---------|
| `models.py` | `EffectVariant` and `VariantTags` dataclasses |
| `library.py` | `VariantLibrary` class — load, query, CRUD |
| `validator.py` | `validate_variant()` — cross-validates against EffectLibrary |
| `importer.py` | `extract_variants_from_xsq()` — .xsq mining |
| `scorer.py` | `rank_variants()` — weighted multi-dimensional scoring |
| `builtin_variants.json` | 100+ built-in variant catalog |

## Modified Files

| File | Change |
|------|--------|
| `src/themes/models.py` | Add `variant_ref: str \| None` to `EffectLayer` |
| `src/themes/validator.py` | Validate `variant_ref` against `VariantLibrary` |
| `src/themes/library.py` | Pass `VariantLibrary` for validation |
| `src/generator/effect_placer.py` | Resolve variant parameters during placement |
| `src/review/server.py` | Add variant CRUD + browse + import endpoints |
| `src/cli.py` | Add `variant` subcommand group |

## How to Use

### CLI

```bash
# Browse variants
xlight-analyze variant list --effect Meteors --energy high

# Show details
xlight-analyze variant show "Meteors Storm Burst"

# Import from sequence
xlight-analyze variant import my_show.xsq --dry-run

# Create custom variant
xlight-analyze variant create --effect Bars --name "Bars Slow Breathe"

# Check coverage
xlight-analyze variant coverage
```

### Web Dashboard

- Browse/filter variants at `/variants` endpoint
- Create/edit/delete via REST API
- Import .xsq via file upload

### In Themes

```json
{
  "effect": "Meteors",
  "blend_mode": "Additive",
  "variant_ref": "Meteors Storm Burst",
  "parameter_overrides": {}
}
```

## Implementation Order

1. **Models + Validator** — EffectVariant, VariantTags, validate_variant()
2. **Library + Storage** — VariantLibrary, load/save/delete, JSON catalog
3. **CLI commands** — variant list/show/create/edit/delete/coverage
4. **XSQ Importer** — extract_variants_from_xsq(), dedup, CLI command
5. **Scorer** — rank_variants(), composite scoring, fallback logic
6. **Theme Integration** — variant_ref on EffectLayer, generator resolution
7. **Web Dashboard** — REST endpoints, browse/CRUD UI
8. **Built-in Catalog** — curate 30-40 core + import from .xsq to reach 100+
