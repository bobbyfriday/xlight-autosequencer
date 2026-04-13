# Quickstart: Focused Effect Vocabulary + Embrace Repetition

## What this changes

Two behavioral changes to the sequence generator:

1. **Effect pool is narrower**: Instead of drawing from ~10 hardcoded effects or the
   full variant library, the generator now derives a weighted working set of 4-8 effects
   from each theme's layer structure. The base layer effect dominates (~40% of placements).

2. **Effects repeat within sections**: The rotation engine no longer penalizes reusing
   the same effect on a model within a section. A single effect+palette holds for the
   entire section duration on each model — matching how community sequencers work.

## Files modified

| File | Change |
|------|--------|
| `src/generator/effect_placer.py` | WorkingSet derivation, replaces `_PROP_EFFECT_POOL` |
| `src/generator/rotation.py` | Remove intra-section dedup, relax cross-section penalty |
| `src/generator/plan.py` | WorkingSet initialization before section loop |
| `src/generator/models.py` | WorkingSet/RepetitionPolicy dataclasses (if needed) |

## How to test

### Automated
```bash
pytest tests/unit/test_working_set.py -v
pytest tests/unit/test_repetition_policy.py -v
pytest tests/integration/test_phase1_metrics.py -v
```

### Manual comparison
```bash
# Generate a sequence
# Then analyze with reference tool
python3 scripts/analyze_reference_xsq.py output.xsq

# Check these metrics:
# - Top-5 effects should be 80%+ of placements (was ~50%)
# - Top effect should be 25%+ (was ~15%)
# - Consecutive repetition should show 10+ runs (was 1-3)
```

### Toggle testing
The two behaviors are independently toggleable via generation config:
- `focused_vocabulary=False` → reverts to full pool (pre-Phase-1 behavior)
- `embrace_repetition=False` → reverts to old penalties (pre-Phase-1 behavior)

## What NOT changed

- Beat tier (Tier 4) chase pattern — unchanged
- Theme definitions — no modifications needed (working set derived algorithmically)
- Audio analysis pipeline — no changes
- XSQ output format — identical structure
- Palette generation — no changes (Phase 3)
- Effect durations — no changes (Phase 2)
