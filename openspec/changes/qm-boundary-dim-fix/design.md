# Design: restore ethereal active tiers to {1, 8}

## Goal

Ethereal-mood sections render with a dim wash across all props (Tier 1 BASE_All + heroes) instead of HERO-only. Empirically lifts 63% of Baby Shark from ~5% brightness to ~40% brightness.

## Approach

In `src/generator/effect_placer.py:_compute_active_tiers`, change the ethereal branch:

```python
# Before (current):
if section.mood_tier == "ethereal":
    return frozenset({8})

# After:
if section.mood_tier == "ethereal":
    return frozenset({1, 8})
```

The `_TIER_BRIGHTNESS` table already has `{1: 0.40}` so Tier 1 effects auto-render at 40% brightness on every prop. Tier 8 keeps the hero highlights at full brightness. Net effect: ethereal sections look like a dim wash with a few bright heroes, instead of a black canvas with a few bright heroes.

**Alternative considered:** add `{1, 8}` only when section.energy_score > 0. Rejected — the energy score already gates which sections are classified ethereal in the first place; adding a second-level gate is redundant and gives identical results on every realistic audio input.

**Alternative considered:** carry the surrounding section's mood for `qm_boundary` labels. Rejected for reasons in proposal.md (the issue isn't qm-boundary-specific; section 5 of Baby Shark is a labeled `A` section that's also ethereal-and-dim).

## Files touched

- **MODIFY** `src/generator/effect_placer.py:1788` — change `frozenset({8})` → `frozenset({1, 8})` and update the comment to reflect the new rationale (citing #77 as the prior decision being revisited)
- **ADD** `tests/unit/test_active_tiers_ethereal.py` — covers ethereal returns {1, 8}, structural unchanged, aggressive unchanged
- **ADD** `tests/golden/baseline.json` — generator-baseline metrics will shift; accept-and-resnapshot is part of the verification step (not committed in this PR; user runs `xlight-evaluate snapshot-analyzer` after merge if metrics improve)

## Regression surface

Public symbols changed:

- `_compute_active_tiers` is module-private (underscore prefix) and called from exactly one place: `_populate_assignment_decisions` in `src/generator/plan.py:312`. No external callers.

Files importing `_compute_active_tiers`:

```bash
$ grep -rn "_compute_active_tiers" src/ tests/
src/generator/effect_placer.py:1765:def _compute_active_tiers(  # definition
src/generator/effect_placer.py:583:  # comment ref only
src/generator/effect_placer.py:776:  # comment ref only
src/generator/effect_placer.py:796:  # comment ref only
src/generator/plan.py:16:    _compute_active_tiers,  # import
src/generator/plan.py:312:    assignment.active_tiers = _compute_active_tiers(...)  # call site
```

Single call site, single definition, no test imports. Behavior change is intentional and contained.

Effects on other parts of the system:

- `tests/golden/baseline.json` — placement counts will increase for ethereal sections (more tier-1 placements). Already expected to shift after every generator-behavior change; user re-snapshots after acceptance review.
- `tests/integration/test_generate_integration.py` — happy-path test, asserts sequence generation completes; not sensitive to placement count. Should remain green.
- Any `test_generate_with_curves.py` — value-curve tests; orthogonal to tier selection. Should remain green.

## Historical echoes

`.wolf/buglog.json` and `.wolf/cerebrum.md` Do-Not-Repeat: scanned for entries matching `tier`, `ethereal`, `silent`, `BASE`, `HERO`, `dim`. **No matches** — this isn't a re-litigation of a prior bug.

PR history: PR #77 (commit 9d6a2c48) was the one that removed Tier 1 from ethereal. Its commit message was "fix: theme override pipeline — overrides reach the generator, palettes honor the theme" — the tier-set change was a side-modification with the comment "drove tier_utilization to ~100% even in silent moments." This PR is an acknowledged revert of that side-modification, with the new rationale that user-visible darkness on a song with constant audio is worse than a tier-utilization metric being high.

## Verification

After this PR merges and PR-A's verification framework lands, run:

```bash
python -m tools.verify_suggestion.run \
  --suggestion 21 \
  --slug ethereal-tier-1-restored \
  --what-changed "Restore Tier 1 BASE_All to ethereal active_tiers" \
  --why "63% of Baby Shark was rendering at <5% brightness because ethereal sections fired only Tier 8 (heroes)"
```

Expected metric deltas:
- `lit_mean` ↑ significantly (probably 5-10× for songs with ethereal sections)
- `upper_third_pct`, `middle_third_pct`, `lower_third_pct` all ↑
- `motion_mean` may go either way (more lit pixels = more places motion can happen, but Tier 1 BASE effects are typically smooth washes)
- `distinct_colors_mean` ≈ unchanged (palette doesn't change, just whether more props render it)
