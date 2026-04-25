## Goal

Annotate every selected L2 (bar) and L3 (beat) `TimingMark.confidence` with
the fraction of *other* candidate trackers that agree on that mark within a
tight window, so downstream effect generation can branch on per-beat
certainty (punch vs wash).

## Approach

### Chosen: cross-tracker agreement count, normalized

For each mark `m` in the winning track and each *loser* track `L`, define
"agreement" as `min_{x ∈ L.marks} |x.time_ms - m.time_ms| <= window_ms`.
The per-mark confidence is

```
confidence(m) = agreeing_losers(m) / max(1, total_losers)
```

So with 4 trackers (1 winner + 3 losers): `0.0` when no other tracker
agrees, `1/3 ≈ 0.33` when one agrees, `2/3 ≈ 0.67` when two agree, `1.0`
when all three agree. With 2 trackers: `0.0` or `1.0`.

The winner's own mark contributes nothing to its own confidence — by
definition it is at the mark — so the denominator is `len(losers)`, not
`len(candidates)`.

### Decision 1 — Agreement window: ±35 ms

Beat-tracker rounding error and inter-algorithm timing offsets typically
sit at 10-30 ms (madmom DBN snaps to 10 ms grid, librosa hop-length
defaults to ~23 ms, QM analysis hop is ~20 ms). A 35 ms window catches
genuine same-beat agreement while rejecting next-eighth-note agreement
even at 200 BPM (eighth note = 75 ms; half-window for next eighth = 37.5
ms). At 120 BPM (eighth = 250 ms), 35 ms is well clear.

The existing onset-correlation tiebreak inside `select_best_track` uses
`±50 ms`; we choose tighter than that because we want *agreement on the
specific beat instant*, not "this beat is in the same neighborhood as an
onset". The validator's bar/beat onset alignment uses `±80 ms` and `±50 ms`
respectively for the same reason — onset density is noisier than
beat-tracker output.

**Alternative considered:** ±20 ms (the value mentioned in the task
brief). Rejected — too tight against madmom's 10-ms grid stacked with
librosa's 23-ms hop; we measured the worst-case alignment error at
roughly `5 + 12 = 17 ms`, leaving zero margin.

**Alternative considered:** Tempo-adaptive window (e.g. 1/16th of beat
period). Rejected — adds complexity for no measurable improvement at the
tempo range our analyzer typically sees (60-180 BPM); the fixed 35 ms
window stays well inside an eighth note across that whole range.

### Decision 2 — Confidence metric: raw count, equal weight

We pick the simple normalized count (agreeing losers / total losers)
over two alternatives:

**Alternative considered:** Quality-score-weighted vote. `confidence(m)
= sum(L.quality_score for L in agreeing) / sum(L.quality_score for L in
losers)`. Rejected — `quality_score` already drove the *selection* of
the winner; baking it into the agreement signal double-counts and is
harder to interpret. The point of agreement is to detect "the
algorithms genuinely converge on this beat", which is binary at the
per-tracker level.

**Alternative considered:** Binary threshold (≥3-of-3 → 1.0, else 0.0).
Rejected — discards the gradient. The downstream consumer in
`effect_placer` uses a 0.7 threshold, so a mark with 2-of-3 agreement
(0.67) goes to the wash path; a mark with 3-of-3 (1.0) goes to punch.
A binary metric collapses 0.33 / 0.67 into the same bucket and loses
the ability to tune the consumer threshold later.

### Decision 3 — Single downstream consumer: `_place_per_beat`

We wire exactly one consumer to prove the field reaches a real
user-visible outcome:

`src/generator/effect_placer.py::_place_per_beat` (~line 1099) iterates
`hierarchy.beats.marks` to place per-beat effects. This is currently the
heaviest L3 consumer in the generator and produces visible chase patterns
on Tier 4 BEAT groups.

When `mark.confidence is not None and mark.confidence >= 0.7`: route the
placement through the existing accent path (Strobe, Shockwave) — short
duration, high impact, "punch" feel. When `mark.confidence < 0.7` or is
None: fall through to the existing default placement unchanged. The
0.7 threshold corresponds to "≥2-of-3 losers agree" with 4 trackers
total, which is the perceptual sweet spot for "this is definitely a
beat".

**Alternative considered:** review UI surfacing. Rejected for *this*
proposal — the review UI is a passive consumer; if confidence is
populated but unused in generation, we have not proved the field reaches
the lights. We can add UI surfacing in a follow-up once the generator
consumer is shipped.

**Alternative considered:** L0 wow-trigger boosting. Rejected — L0
impacts are derived from energy curves, not from beat marks; routing
beat confidence into L0 is architectural drift outside this change's
scope.

### Decision 4 — Single-tracker fallback: confidence = None

When `len(losers) == 0` (only one tracker available — quick profile, or
madmom and vamp both unavailable in CI), we cannot compute agreement and
leave `mark.confidence = None`. The validator's existing track-level
fallback then fills the value with the regularity+alignment score, which
matches today's behavior exactly.

**Alternative considered:** confidence = 1.0 ("trust the only available
tracker"). Rejected — overstates certainty; a single librosa beat track
with no cross-check is exactly the case where we are *least* sure, not
most.

**Alternative considered:** confidence = 0.5. Rejected — sets every beat
to the same value, which any threshold consumer reads as either all-on or
all-off, defeating the per-mark purpose. None is honest: "no signal
available," and consumers branch on `is None` already.

### Decision 5 — Ordering: selector annotation runs before validator

Today `validator.py:230` and `:244` overwrite **every** L2 and L3
`mark.confidence` with a single track-level scalar (the same value for
every mark in the track). If we annotate first and validate second, the
validator clobbers our work.

The fix: change `validator.py` to set `mark.confidence = score` only when
`mark.confidence is None`. The `score` becomes a track-level fallback for
marks the selector did not annotate (single-tracker case) and a no-op
otherwise. The track-level score is still surfaced in
`HierarchyResult.validation['beats']['score']` and
`['bars']['score']` for the report.

**Alternative considered:** Add a separate `agreement: Optional[float]`
field on `TimingMark` so validator and selector populate distinct slots.
Rejected — schema churn for the JSON snapshot, golden baseline
regeneration, more `from_dict` churn, and downstream consumers would have
to read both fields and reconcile. The single `confidence` field with
clear precedence (per-mark agreement when computed, track-level scalar as
fallback) is simpler and stays in the existing 0–1 contract.

## Files touched

- `src/analyzer/selector.py` — **modified**.
  - Add `annotate_agreement_confidence(winner: TimingTrack, losers:
    list[TimingTrack], window_ms: int = 35) -> None` (mutates in place).
  - Add `select_best_beat_track_with_candidates(candidates,
    onset_times_ms) -> tuple[TimingTrack | None, list[TimingTrack]]`
    returning the winner and the non-winning candidates.
  - Same for `select_best_bar_track_with_candidates`.
  - Existing `select_best_beat_track`, `select_best_bar_track`,
    `select_best_track`, `rank_tracks` signatures **unchanged** —
    callers outside the orchestrator (e.g. `rank_tracks` in
    `orchestrator.py:1245`, sweep tooling) keep working.
- `src/analyzer/orchestrator.py` — **modified**.
  - Replace L2 / L3 calls (~lines 412, 425) with the
    `_with_candidates` variants.
  - Call `annotate_agreement_confidence(bars, bar_losers, 35)` if
    `bars` is not None and `bar_losers` is not empty.
  - Same for beats.
  - The existing `_select_beat_with_bpm_check` wrapper at line 1229
    must be updated to thread `candidates` through; it currently
    returns only the winner.
- `src/analyzer/validator.py` — **modified**.
  - In the L2 bars block (line 229-230) and L3 beats block (line
    243-244), guard `mark.confidence` writes with
    `if mark.confidence is None`.
- `src/generator/effect_placer.py` — **modified**.
  - In `_place_per_beat` (~line 1099), branch on `mark.confidence` to
    select between accent and default placement params (no new
    parameters threaded through `_place_per_beat`'s signature; the
    function already has access to the marks).
- `tests/unit/test_selector.py` — **added**.
- `tests/integration/test_orchestrator_beat_confidence.py` — **added**.
- `tests/golden/analyzer/baseline.json` — **modified** (re-snapshot).
- `openspec/changes/beat-confidence-annotation/specs/analyzer-beat-confidence/spec.md`
  — **added** (this proposal's spec delta).

## Regression surface

Public symbols modified or whose behavior changes:

| Symbol | File | Change | Callers (grep) | Status |
|---|---|---|---|---|
| `TimingMark.confidence` semantics | `result.py:98` | Same type `Optional[float]`, same 0–1 range; for L2/L3 marks the value is now per-mark agreement instead of track-level scalar | `validator.py:230,244,263,286,299,312` (writers); `result.py:180,371,563` (serialize); `sweep.py:148` (read for export); `orchestrator.py:1223` (re-uses confidence on synthesized mark — preserved behavior); `tests/unit/test_result.py:17,22` (asserts None or float — still passes) | All readers expect `Optional[float]` in 0–1 range; per-mark vs track-level granularity is a value change, not a contract change. Re-snapshot golden baseline to update written values. |
| `select_best_beat_track(candidates, onset_times_ms)` | `selector.py:129` | Signature unchanged; remains a thin wrapper | `orchestrator.py:240` (import only — direct call replaced; orchestrator now uses `_with_candidates` variant) | Untouched callers continue working. |
| `select_best_bar_track(candidates, onset_times_ms)` | `selector.py:121` | Signature unchanged; remains a thin wrapper | `orchestrator.py:240` (import only) | Untouched. |
| `select_best_track(candidates, onset_times_ms)` | `selector.py:50` | Signature and behavior unchanged | none outside selector module | Untouched. |
| `rank_tracks(candidates, onset_times_ms)` | `selector.py:93` | Unchanged | `orchestrator.py:1243-1245` | Untouched. |
| `_select_beat_with_bpm_check` | `orchestrator.py:1229` | Internal; return shape extended to `(winner, losers)` | `orchestrator.py:425` (sole caller) | Caller updated in same diff. |
| `validate_hierarchy(result)` | `validator.py:182` | Behavior change: bar/beat mark-confidence writes are now guarded; track-level score still surfaced in `report['bars']['score']` / `report['beats']['score']` | `orchestrator.py:702`; `tests/integration/test_orchestrator_*` | Caller signature unchanged. Tests asserting `report['bars']['score']` keep passing. |
| `_place_per_beat(...)` | `effect_placer.py:1099` | Internal; reads `mark.confidence` (already in scope) | `effect_placer.py:761,1002,1067` | All call sites pass through unchanged. |

Schema (JSON) impact: `TimingMark.confidence` already round-trips through
`to_dict` / `from_dict` (`result.py:180, 200, 563, 571, 621, 626, 631,
636, 650`); no schema field is added. Golden baseline values change for
L2 / L3 marks; baseline regeneration captures it.

CLI / public API: no flags added or changed. `xlight-analyze analyze`
still produces the same set of files; only the populated values inside
`_analysis.json` for L2 / L3 mark confidences are different (more
granular).

## Historical echoes

Searched `.wolf/buglog.json` and `.wolf/cerebrum.md` for entries matching
this change's files (`selector.py`, `validator.py`, `orchestrator.py`,
`effect_placer.py`), symbols (`select_best_*`, `annotate_agreement_*`,
`TimingMark.confidence`), and topics (beat agreement, cross-tracker,
confidence annotation). **No matches found.**

The closest neighboring change is
`openspec/changes/archive/2026-04-25-fix-misclassified-curves/`, which
also touched `src/analyzer/` shared infrastructure and re-snapshotted the
analyzer golden baseline. Lessons applied here:

- Confirm `Optional` field semantics across all readers before changing
  the populated values — done in the table above.
- Re-snapshot `tests/golden/analyzer/baseline.json` and run the
  acceptance gate (`xlight-evaluate gate`) before merge.
- Keep the spec delta tightly scoped to the new capability; do not
  extend unrelated specs.

## Test plan

- Unit (`tests/unit/test_selector.py`):
  - `annotate_agreement_confidence` — three losers all agree → 1.0;
    none agree → 0.0; one agrees → 1/3.
  - Empty losers → confidence remains `None` (single-tracker fallback).
  - Window boundary: loser at exactly `±35 ms` counts as agreeing;
    `36 ms` does not.
  - Multiple loser marks within window count once (not double-counted).
- Integration (`tests/integration/test_orchestrator_beat_confidence.py`):
  - Run hierarchy on a fixture; assert at least one L3 beat mark has
    `confidence` not equal to the track-level score (proves
    per-mark annotation took effect).
  - Assert the validator's `report['beats']['score']` still equals the
    pre-change formula.
  - Assert single-tracker profile (`profile="quick"`) leaves
    `mark.confidence` populated by validator fallback (existing
    behavior preserved).
- Golden baseline: regenerate `tests/golden/analyzer/baseline.json`
  via `xlight-evaluate snapshot-analyzer` and verify the diff is
  confined to per-mark `confidence` values on L2 / L3 tracks.
- Generator regression: `tests/unit/test_effect_placer.py` (or
  equivalent) — confirm `_place_per_beat` selects punch vs wash branch
  by stubbing a high- and a low-confidence mark.
- Acceptance gate: `xlight-evaluate gate` (full mode) before merge.

## Open questions

- Should L0 impact / drop marks also receive cross-tracker agreement?
  (Currently they are derived from energy curves, not from competing
  trackers, so there is no "loser" set — leaving out of scope.)
- Should the 0.7 consumer threshold be a config value? Deferred until we
  have field experience tuning it.
