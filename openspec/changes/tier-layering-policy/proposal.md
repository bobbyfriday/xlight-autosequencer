# Proposal: tier-layering policy

## Why

Investigation traced from a real-render review of the Cher fixture
(`Cher-DJ_Play_a_Christmas_Song`, 2026-05-06) showed that of the eight
tiers the generator synthesises into the layout XML, **only tiers 5–8
ever receive effect placements**. Tiers 1 BASE, 2 GEO, 3 TYPE, and 4
BEAT are written to disk and then ignored.

The gate is two small hardcoded policies in shared modules:

1. [`src/generator/rotation.py:107`](../../../src/generator/rotation.py#L107)
   maps only tiers 5–8 to a `tier_affinity` value
   (`{5: "mid", 6: "mid", 7: "foreground", 8: "hero"}`). When tiers
   1–4 are scored the affinity context is `None`, so the variant
   scorer cannot bias toward background-tagged variants.

2. [`src/generator/effect_placer.py:1980`](../../../src/generator/effect_placer.py#L1980)
   `_compute_active_tiers` returns at most one of `{2, 4, 6}` plus
   `{8}` per section, never including 1, 3, 5, or 7. The function's
   docstring justifies this with a "silent overwrite" claim — that
   activating multiple partition tiers makes the higher one clobber
   the lower on shared props. Empirical check (Rob, 2026-05-06) found
   this isn't true: xLights composes layers correctly. The actual past
   incident was tier 1 BASE running bold effects (e.g. `Color Wash`)
   that *visually* overwhelmed the upper tiers — the symptom was
   misdiagnosed as structural overwrite.

The pieces to fix this are already in place:

- The variant library has **75 variants tagged `"background"`** across
  20 base effects (`Plasma×10, Bars×9, Color Wash×8, Liquid×4,
  Spirals×4, Twinkle×5, …`).
- The scorer applies tier_affinity as a soft 0.20-weighted bias with
  adjacency relaxation — not a hard filter — so background-leaning
  selection coexists with the other scoring axes.
- All 22 themes already use `Normal` + `Additive` blend modes per
  layer; the layer-composition discipline is already tuned.

What's missing is the *policy* that turns tiers 1–4 on and routes the
right affinity context to the scorer when they are.

## What Changes

- Extend the `tier_map` in `rotation.py` to cover tiers 1–4.
- Extend `_compute_active_tiers` in `effect_placer.py` so each mood
  branch returns a richer set that layers BASE (tier 1) under the
  partition tier, with optional GEO and BEAT layering above.
- Add an inter-tier *layer-and-blend policy* helper that decides which
  xLights layer index and blend mode each tier's effects use when
  multiple tiers fire on the same prop. Today this is implicit per-theme
  and per-layer-index; making it tier-aware is the missing piece.
- Update the four `_compute_active_tiers` unit tests that assert exact
  frozenset values (`tests/unit/test_generator/test_effect_placer.py:541,
  548, 556, 576`) to match the new policy.

## What Does NOT Change

- The variant library's `tier_affinity` tags. Already correct.
- The scorer's `_score_tier` function. Already correct.
- The theme JSON files. Already correct.
- Tiers 3 (TYPE) and 5 (TEX). Currently unused; staying unused for
  this change, scoped out as future work.
- The layout-XML group synthesis (`017-xlights-layout-grouping`).
  Untouched.

## Validation

This change is grounded in a **render-watch-tweak iteration loop on
real sequences**, not unit tests alone. See the iteration plan in
[design.md](./design.md#iteration-plan). Microscope panel coverage
(metric: `tier_placement_breakdown`) will track tiers 1, 2, 4
appearing in placements as a regression guard, but the truth source
is what the render looks like in xLights.
