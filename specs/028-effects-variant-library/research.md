# Research: Effects Variant Library

**Feature**: 028-effects-variant-library
**Date**: 2026-04-01

## R1: Variant Data Model — Relationship to Existing Effects

**Decision**: Effect variants are a new entity type stored in a separate module (`src/variants/`), not embedded within the existing `EffectDefinition`. A variant holds a reference to a base effect by name, parameter overrides, and variant-specific tags.

**Rationale**: The existing `EffectDefinition` in `src/effects/models.py` represents the canonical xLights effect with its full parameter schema, prop suitability, and analysis mappings. Variants are *configurations* of those definitions — they don't add parameters or change suitability ratings. Keeping them separate avoids bloating the effect catalog and follows the same separation pattern as effects vs. themes.

**Alternatives considered**:
- Embedding variants as a list inside `EffectDefinition` — rejected because it couples the effect schema to variant metadata and makes the builtin_effects.json file unwieldy.
- Storing variants in the theme files — rejected because variants are reusable across themes and should have their own lifecycle.

## R2: Variant Storage Format

**Decision**: Single bundled `builtin_variants.json` for built-in catalog, per-file `~/.xlight/custom_variants/*.json` for custom variants. Follows the same convention as effects and themes.

**Rationale**: The project has an established pattern:
- `src/effects/builtin_effects.json` + `~/.xlight/custom_effects/*.json`
- `src/themes/builtin_themes.json` + `~/.xlight/custom_themes/*.json`

Using the same pattern for variants means the same loading/merging code patterns apply, and users have a consistent mental model.

**Alternatives considered**:
- SQLite database for faster querying — rejected per constitution (file-based, offline, simple).
- Single monolithic file for all custom variants — rejected because per-file makes git-friendliness and individual variant sharing easier.

## R3: .xsq Import Strategy

**Decision**: Use the existing `parse_xsq()` function in `src/generator/xsq_writer.py` to extract `EffectPlacement` objects, then convert each unique (effect_name, parameters) combination into a draft variant. Auto-generate names from effect name + distinguishing parameter values. Tags are left blank for manual categorization.

**Rationale**: `parse_xsq()` already handles the XML parsing and produces `EffectPlacement` objects with resolved parameters. The importer only needs to:
1. Call `parse_xsq()` to get all placements
2. Group by (effect_name, sorted parameter dict) for deduplication
3. Create draft `EffectVariant` objects with auto-generated names
4. Let the user review, rename, and tag them

**Alternatives considered**:
- Raw XML parsing in the importer — rejected because `parse_xsq()` already handles the complexity.
- Automatic tag inference from placement context (which model it was on, timing position) — deferred to future work. Initial import produces untagged variants.

## R4: Variant-to-Theme Integration

**Decision**: Add an optional `variant_ref: str | None` field to `EffectLayer` in `src/themes/models.py`. When present, the generator resolves the variant from `VariantLibrary`, merging its parameters over the base effect defaults. The existing `parameter_overrides` field on `EffectLayer` can still further override variant parameters (theme-level tweaks on top of variant).

**Rationale**: This is backward-compatible — existing themes without `variant_ref` work exactly as before. The resolution chain is: base effect defaults → variant parameter overrides → theme layer parameter_overrides. This gives maximum flexibility.

**Alternatives considered**:
- Replace `effect` + `parameter_overrides` entirely with `variant_ref` — rejected because it breaks backward compatibility and removes the ability to do theme-level tweaks.
- Separate variant references from the layer model — rejected because the layer is the natural place where an effect choice is made.

## R5: Composite Suitability Scoring

**Decision**: Multi-dimensional scoring with weighted dimensions. When querying variants for a context, each matching variant receives a score:
- Prop suitability (inherited from base effect): ideal=1.0, good=0.7, possible=0.4, not_recommended=0.1
- Energy match: exact=1.0, adjacent=0.5, mismatch=0.0
- Tier affinity match: exact=1.0, adjacent=0.5, mismatch=0.2
- Section role match: present in list=1.0, absent=0.3
- Scope match: exact=1.0, mismatch=0.5
- Genre match: exact=1.0, "any"=0.8, mismatch=0.3

Final score = weighted average. Weights: prop suitability (0.3), energy (0.25), tier (0.2), section role (0.15), scope (0.05), genre (0.05).

**Rationale**: Prop suitability and energy are the highest-impact dimensions (wrong prop type = unusable, wrong energy = jarring). Tier and section role matter but have more graceful degradation. Scope and genre are soft preferences.

**Alternatives considered**:
- Boolean filtering only (match/no-match) — rejected because it's too restrictive and produces empty results frequently.
- Unweighted average — rejected because all dimensions are not equally important.

## R6: Fallback Strategy for Empty Query Results

**Decision**: Progressive constraint relaxation in this order: (1) drop section role filter, (2) drop genre filter, (3) widen energy to adjacent levels, (4) widen tier affinity to adjacent, (5) drop scope filter. If still empty, return all variants for the base effect sorted by prop suitability alone.

**Rationale**: The relaxation order matches the weighted scoring — least important constraints drop first. The final fallback ensures the generator always has at least one variant to work with.

## R7: Built-in Catalog Population — Phase 1 Seed

**Decision**: Hand-curate the initial ~30-40 core variants by extracting configurations from:
1. The 21 existing themes in `builtin_themes.json` — each theme layer's `parameter_overrides` becomes a variant
2. The `_PROP_EFFECT_POOL` rotation in `effect_placer.py` — each effect with its forced parameters and alternating directions becomes 2-4 directional variants
3. The `_XLIGHTS_EFFECT_DEFAULTS` in `xsq_writer.py` — the "default" configuration of each effect becomes a baseline variant

Then import from a single .xsq sequence to validate the importer and assess yield before expanding.

**Rationale**: This uses configurations already proven to work in the pipeline, requires no external data, and establishes the variant format before bulk import.
