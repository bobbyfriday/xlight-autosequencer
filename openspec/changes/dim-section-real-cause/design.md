# Design: rotation dedup + density bracket fix

## P1 — `rotation.py`: dense-fill preference in dedup fallback

### Current code (lines 320-330)

```python
# T008/T010 (FR-001, FR-006): within-tier base-effect dedup for tiers 5-8.
if group.tier >= 5 and variant.base_effect in used_effects_per_tier[group.tier]:
    unclaimed = [
        (v, s, b) for v, s, b in results
        if v.base_effect not in used_effects_per_tier[group.tier] and s >= 0.3
    ]
    if unclaimed:
        variant, score, breakdown = unclaimed[0]
    # else: no suitable alternative — keep current selection (allow duplication)
```

### Problem

When `unclaimed` is empty (every other base_effect is either already used or scores <0.3), the engine falls back to `variant` — which was set on line 318 to `results[0]`, i.e. *the highest-scoring variant overall*. For Tier 6 in low-energy structural sections that is consistently `Chase Multi Dense` (Single Strand). So as the loop walks the 16-30 surviving groups in tier order, each one inherits that same Single Strand fallback and renders the same sparse 6-chase pattern.

### Fix

Add a `_DENSE_FILL_BASE_EFFECTS` constant near the top of `rotation.py`. Before keeping `variant` as the fallback, look one more time for a variant whose base_effect is in that set, regardless of whether it's already used in the tier — duplicating a dense fill across props is far less visually noticeable than every prop chasing six pixels back and forth.

```python
_DENSE_FILL_BASE_EFFECTS: frozenset[str] = frozenset({
    "Color Wash", "Liquid", "Plasma", "Fire", "Galaxy", "Pinwheel",
    "Butterfly", "Shockwave",
})
# Rationale: each of these base effects lights >50% of a prop's pixels at any
# frame, vs Single Strand / Bars / Wave which animate sparse subsets. When the
# rotation engine has exhausted unclaimed candidates with score >= 0.3, prefer
# duplicating a dense fill rather than recycling a sparse one — visual
# repetition of a wash reads as "subtle" while repetition of a chase reads as
# "the show is broken."
```

```python
if group.tier >= 5 and variant.base_effect in used_effects_per_tier[group.tier]:
    unclaimed = [
        (v, s, b) for v, s, b in results
        if v.base_effect not in used_effects_per_tier[group.tier] and s >= 0.3
    ]
    if unclaimed:
        variant, score, breakdown = unclaimed[0]
    else:
        # Prefer recycling a dense fill over the originally-selected sparse one.
        # Drop the score threshold and the no-duplication constraint — duplicating
        # a wash across props is much less visible than every prop chasing.
        dense_fallback = [
            (v, s, b) for v, s, b in results
            if v.base_effect in _DENSE_FILL_BASE_EFFECTS
        ]
        if dense_fallback:
            variant, score, breakdown = dense_fallback[0]
        # else: no dense fill available — keep current (rare; only happens when
        # every dense effect already failed the variant-library lookup, which
        # would itself be a pipeline bug worth surfacing).
```

## P2 — `plan.py`: shift density threshold

### Current code (lines 356-362)

```python
energy = section.energy_score
if energy <= 50:
    assignment.group_density = 0.40
elif energy <= 75:
    assignment.group_density = 0.70
else:
    assignment.group_density = 1.0
```

### Problem

The `≤ 50` cutoff lumps the entire 0-50 energy range into the same 0.40 density. Baby Shark's structural sections sit at 46-59, with several at exactly 50. Those land on 0.40 (cull 60% of groups) when their energy is within rounding distance of the 0.70 boundary — that's a step-function cliff hidden inside the data.

### Fix

```python
energy = section.energy_score
if energy <= 35:
    assignment.group_density = 0.40
elif energy <= 70:
    assignment.group_density = 0.70
else:
    assignment.group_density = 1.0
```

Rationale: 0.40 is "very quiet sections only" — narrow it to the bottom third of the energy range. The middle ⅔ (energy 36-70, where most pop / kid / mid-tempo songs sit) gets 0.70 density, lighting 70% of tier-6 groups. The top range stays unchanged.

## Files touched

- **MODIFY** `src/generator/rotation.py` — add `_DENSE_FILL_BASE_EFFECTS` constant, modify the dedup fallback (lines 325-330)
- **MODIFY** `src/generator/plan.py` — shift density brackets (line 357-359)
- **ADD** `tests/unit/test_rotation_dense_fallback.py` — verify dense fills picked over sparse when dedup runs out
- **MODIFY** `tests/unit/test_plan.py` (or wherever density logic is tested) — update for new bracket boundaries

## Regression surface

`rotation.py` `_rank_for_group` and `build_rotation_plan` are public. Single caller path: `build_plan` in `plan.py`. The dedup fallback only changes behaviour when `unclaimed` is empty AND a dense-fill variant exists in `results` — so songs that already produce dense rotations (high-energy structural and aggressive sections) are unchanged.

`plan.py` density-bracket change shifts the boundary for sections with energy 36-50. Any song with sections in that range will see more groups activated. This includes most pop and mid-tempo songs.

`tests/golden/baseline.json` will shift after this lands — expected. Re-snapshot via `xlight-evaluate snapshot-analyzer` after acceptance review.

## Historical echoes

Scanned `.wolf/buglog.json` and `.wolf/cerebrum.md` for entries matching `rotation`, `dedup`, `density`, `dim`, `Single Strand`, `Chase Multi Dense`. **No matches.** This isn't re-litigating a prior bug.

PR #122 was an attempt to fix the same symptom but targeted the wrong code path (ethereal branch). This PR targets the actual cause documented in `/tmp/investigations/01_baby_shark_dimness_real_cause.md`.

## Verification

After merge:

```bash
python -m tools.verify_suggestion.run \
    --suggestion 25 --slug dim-section-real-cause \
    --what-changed "Rotation dedup prefers dense fills + relaxed density bracket" \
    --why "63% of Baby Shark renders dim because rotation falls back to sparse Single Strand and density culls 60% of groups"
```

Expected metric deltas vs fresh-main baseline:
- `lit_mean` ↑ 2-5× (predicted similar shape to PR #124)
- `motion_mean` ↑ 1.5-3×
- `distinct_colors_mean` ↑ 1.5-3×
- Third-band activations all ↑

Hard fail criterion: <10% `lit_mean` improvement → revert.
