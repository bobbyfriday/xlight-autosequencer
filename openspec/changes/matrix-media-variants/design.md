# Design: Matrix Media Variants

## Layer 1 — Variant additions (no shared-module gate)

Each existing variant file (`Plasma.json`, `Fire.json`, `Pinwheel.json`, `Color Wash.json`) gains 2-3 new entries tuned for matrix output:

- **Plasma** — high `Line_Density` (5-7) + `Speed` 25-50 + `Pattern` 2/6/7. Tier `foreground`/`hero`, energy `medium`/`high`, sections `chorus/build/drop`.
- **Fire** — `GrowWithMusic=1`, `Height` 90-95, `HueShift` 0/40 (red and cool variants). Tier `foreground`/`hero`, energy `high`.
- **Pinwheel** — `Arms` 5-8, `Speed` 25-40, centered XC/YC, `Twist` 35-45 with `Sweep`/`3D` depth for asymmetry. Tier `foreground`/`hero`, energy `medium`/`high`.
- **Color Wash** — `Cycles` 3-4, `Shimmer=1`, both `HFade=1` and `VFade=1` to add 2D motion. Tier `foreground`/`hero`, energy `medium`/`high`.

Naming: `<Effect> Matrix <Adjective>` (e.g., `Plasma Matrix Storm`). Identity keys unique (parameter sets differ from existing entries).

## Layer 2 — `_build_effect_pool` matrix filter

```python
# src/generator/effect_placer.py around line 353-380

# Effects whose visual pattern doesn't exploit 2D matrix resolution.
_MATRIX_LOW_VALUE_EFFECTS: frozenset[str] = frozenset({
    "Single Strand", "Bars", "Strobe", "Curtain",
})

def _build_effect_pool(effect_library, exclude=None, prop_type=None):
    exclude = exclude or set()
    pool = []
    for name in _PROP_EFFECT_POOL:
        if name in exclude:
            continue
        edef = effect_library.effects.get(name)
        if edef is None:
            continue
        if prop_type is not None:
            rating = edef.prop_suitability.get(prop_type, "possible")
            if rating == "not_recommended":
                continue
            # NEW: matrix prop_type rejects 1D-oriented effects so the
            # 2D-rich pool wins by default.
            if prop_type == "matrix" and name in _MATRIX_LOW_VALUE_EFFECTS:
                continue
        pool.append(edef)
    if not pool and prop_type is not None:
        return _build_effect_pool(effect_library, exclude=exclude, prop_type=None)
    return pool
```

The relaxation fallback (re-call without `prop_type`) is unchanged — a degenerate pool still gets relaxed.

## Why not also touch `rotation.py`?

`RotationEngine` already weighs `prop_type` at 0.30 in `WEIGHTS` (highest dimension) via `_score_prop_type`, which reads `effect_def.prop_suitability[prop_type]`. The matrix-rich effects are already rated `ideal` for matrix in `builtin_effects.json`, so they already win on that dimension — what they were losing on was `tier_affinity` (only background-tagged variants existed). Adding hero/foreground-tagged variants fixes the tier signal without touching rotation scoring math. Less surface area, fewer regressions.

## Test additions

- `tests/unit/test_effect_placer.py::TestMatrixPoolFilter` (3 cases): assert matrix prop_type filter excludes 1D-oriented effects; assert non-matrix prop_types keep them; assert relaxation fallback still works when every effect is `not_recommended`.

## Rollback

Each layer is independently revertible:
- Revert variant JSON: motion variants disappear, scoring picks background-tagged variants again (current behaviour).
- Revert `_build_effect_pool`: matrix props rotate the full pool (current behaviour).
