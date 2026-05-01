# Matrix Media Variants (Suggestion #6)

## Goal

Make `DisplayAs="Matrix"` props render rich pattern effects (Plasma, Fire, Pinwheel, Color Wash with motion) instead of the flat or 1D-oriented effects (Bars, Single Strand, Strobe) the rotation currently picks for them.

## Context

In Pinkfong's "Baby Shark with Jaws Intro" baseline render, the two `Vert Matrix` props (12×48, 576 px each) light as flat color blocks — the highest-density elements in the layout effectively wasted. Two causes:

1. The tier-6/7 PROP rotation cycles `_PROP_EFFECT_POOL` (`Meteors, Single Strand, Ripple, Spirals, Bars, Curtain, Shockwave, Fire, Strobe, Galaxy`) by group index modulo, with no per-prop-type bias. `_build_effect_pool` only excludes `not_recommended` ratings; everything rated "ideal" or "possible" competes equally.
2. The new variants for Plasma/Fire/Pinwheel/Color Wash are mostly tagged `tier_affinity="background"`, so when a foreground/hero matrix group is being scored by `RotationEngine`, these motion-rich variants score lower than tier-matched alternatives.

## Approach

Two coordinated changes:

1. **Add tier-up variants** for Plasma, Fire, Pinwheel, Color Wash — tagged `tier_affinity="foreground"` or `"hero"`, `energy_level="high"` or `"medium"`, with parameters tuned for matrix output (saturated colors, motion, no flat-fill overrides). These slot into the existing JSON files; no schema changes.
2. **Tighten `_build_effect_pool` for matrix prop_type**: when `prop_type == "matrix"`, exclude effects whose visual pattern doesn't exploit 2D resolution (Single Strand, Bars, Strobe, Curtain). Keep the empty-pool relaxation fallback already in place.

## Files Touched

- `src/variants/builtins/Plasma.json` (modified — add hero/foreground variants)
- `src/variants/builtins/Fire.json` (modified — add)
- `src/variants/builtins/Pinwheel.json` (modified — add)
- `src/variants/builtins/Color Wash.json` (modified — add)
- `src/generator/effect_placer.py` (modified — `_build_effect_pool` matrix filter)

## Alternatives Considered

- **Variant-only fix.** Add hero-tagged variants, leave the pool alone. Rejected: tier-6/7 rotation uses `gi % len(pool)` (positional, no scoring), so even a perfect variant doesn't help when the pool index lands on `Bars`. Both layers must change.
- **Reorder `_PROP_EFFECT_POOL` globally.** Move Plasma/Pinwheel earlier in the constant. Rejected: list order is shared across all prop types; non-matrix props (arches, candy canes) still benefit from Bars/Single Strand.
- **Add a new `_MATRIX_EFFECT_POOL` constant.** Rejected: duplicates the existing list and creates two places to keep in sync. Filtering the existing pool on prop_type is simpler.

## Regression Surface

- `_build_effect_pool` is called at exactly one site: `effect_placer.py:733` (tier-6/7 PROP rotation), passing `prop_type=group.prop_type`. Direct tests exist for the function in `tests/unit/test_effect_placer.py` (covered below).
- Variant additions are purely additive — no existing variant is renamed or removed. Identity keys are unique because parameter sets differ.
- Per-tier dedup logic in `RotationEngine` (`used_effects_per_tier`) already prevents the new variants from monopolizing a tier.

## Historical Echoes

Searched `.wolf/buglog.json` and `.wolf/cerebrum.md` for "matrix", "prop_pool", "effect_pool", "rotation" — no matches.

## Test Plan

- `pytest tests/unit/ -k variant` — variant validator + library + scorer remain green.
- New unit tests in `tests/unit/test_effect_placer.py::TestMatrixPoolFilter` — assert Bars/Single Strand/Strobe/Curtain are filtered, Plasma/Fire/Pinwheel/Spirals are kept.
- Visual confirmation deferred to verify_suggestion framework (run by orchestrator).
