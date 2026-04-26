# Proposal: fix the real cause of low-energy structural sections rendering dim

## Problem

Empirical FSEQ analysis of `01 - Baby Shark with Jaws Intro` shows ~63% of song duration renders at ≤15/255 channel brightness with only 3-6% of channels active. Every Baby Shark section classifies as `mood_tier="structural"` (energy 46-59), so the previously-suspected ethereal branch was never the cause (PR #122 was a verified no-op).

The actual root cause is a **3-way interaction** in the structural code path:

1. `plan.py:357-358` — `energy_score <= 50` produces `group_density = 0.40`. With 41 tier-6 PROP groups, only the first 16 survive the cull.
2. `rotation.py:325-329` — within-tier base-effect dedup keeps each variant's *originally-selected* candidate when no unclaimed alternative scores ≥0.3. For low-energy structural sections the originally-selected fallback is consistently `Single Strand "Chase Multi Dense"`. ~10 of those 16 surviving groups land on it.
3. `Single Strand "Chase Multi Dense"` is sparse-by-design (`Number_Chases=6, Rotations=12, Fade_Type=None`) — lights ~10-15% of pixels per frame.

Net: 16 of 41 prop groups render at 5-15% pixel density → 3-6% total channel activation.

The smoking gun is N2 (60-67s, energy=49, **bright**) vs section 8 (67-95s, energy=50, **dim**). Same energy, both structural, identical placement count. The only difference is which variants survived dedup — N2's first 16 got Color Wash / Liquid / Plasma (dense fills); section 8's got mostly Single Strand.

## Goal

Lift dim-band channel activation from 3-6% to ≥20% and brightness from ≤15/255 to ≥80/255 by ensuring the rotation engine's dedup fallback prefers dense-fill variants over sparse ones, and by reducing how aggressively `group_density` culls low-energy sections.

## Scope

- **In scope:**
  - `src/generator/rotation.py` — the within-tier base-effect dedup at line 325-329. When the unclaimed-with-score-≥0.3 list is empty, prefer variants whose base_effect is in a dense-fill set over the current "keep originally-selected" fallback.
  - `src/generator/plan.py` — `group_density` brackets at line 357-362. Shift the lower threshold so songs whose energy sits in the 47-50 range (a wide swath of mid-tempo pop) drop into the 0.70 bucket instead of 0.40.
- **Out of scope:**
  - Per-variant `coverage_class` schema tagging (cleaner long-term but requires touching every variant JSON file). Use a hard-coded `_DENSE_FILL_BASE_EFFECTS` set in rotation.py for this PR; refactor to per-variant tags as a follow-up if validated.
  - Activating Tier 7 (COMP) for low-energy structural sections — the comment at `effect_placer.py:1772-1776` warns about partition-tier overrides. Investigation suggested it as a possible future change but it's not in this PR's scope.

## Why this approach over the alternative

**Considered:** add a `coverage_class` field to every `EffectVariant` and let the dedup fallback prefer high-coverage variants. Rejected for *this* PR because it requires editing every JSON in `src/variants/builtins/`, bumping the variant schema version, and migrating consumer code. The hard-coded base-effect set in rotation.py is a minimal lever that hits the same outcome with one new constant; if it works empirically we can refactor to per-variant tags later without affecting the show-improvement metrics.

**Considered:** raise the `group_density` threshold to keep more groups when energy ≤ 50. Adopted as P2, complementary to P1. Density alone isn't sufficient — without P1 the extra groups still render Single Strand sparse fills. Density *with* P1 lifts more groups AND ensures they render dense.

## Verification expectation

Apples-to-apples comparison via `tools/verify_suggestion/`:
- `lit_mean` ↑ significantly (predicted 2-5×, vs the +209% PR #124 produced by adding new placement targets)
- `motion_mean` ↑ moderately (denser variants animate more pixels)
- `distinct_colors_mean` ↑ moderately
- Third-band activations all ↑

If the verifier shows <10% lit_mean improvement, this PR was misdiagnosed and gets reverted.
