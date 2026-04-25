## Why

`src/analyzer/selector.py` currently runs four independent beat trackers
(`librosa_beats`, `qm_beats`, `beatroot_beats`, `madmom_beats`) and selects a
single winner via coefficient-of-variation + onset correlation. The three
losers' marks are computed at full cost on every analysis run and then
discarded. The same wastage applies to bar trackers (`qm_bars`,
`librosa_bars`, `madmom_downbeats`).

The losers carry useful information we are throwing away: **inter-tracker
agreement at each beat**. Beats where 4-of-4 trackers land within a tight
window are perceptually rock-solid and should drive lock-in punch effects
(Strobe, Shockwave). Beats where only the winner fired — and the other three
disagreed — are uncertain and should drive softer wash effects so the lights
do not punch on what may be a phantom beat.

`docs/musical-analysis-design.md:77` flagged "auto-select by confidence score
in the future"; the partial selector landed in 016-hierarchy-orchestrator. This
proposal goes the next step: keep the same winner but annotate every winning
mark with cross-tracker agreement so a downstream consumer can react to
per-beat certainty rather than treating all beats identically.

## What Changes

- Extend `select_best_beat_track` and `select_best_bar_track` in
  `src/analyzer/selector.py` to return both the winner and the *full
  candidate list* (the losers, currently discarded after the call) so the
  caller can compute per-mark agreement.
- Add a new pure function `annotate_agreement_confidence(winner, losers,
  window_ms)` to `src/analyzer/selector.py` that, for each `winner.marks[i]`,
  counts how many `losers` have at least one mark within `±window_ms`,
  normalizes to `[0.0, 1.0]` against the maximum possible agreement, and
  writes the result to `winner.marks[i].confidence`.
- Wire `annotate_agreement_confidence` into `src/analyzer/orchestrator.py`
  immediately after the L2 bar selection (~line 412) and the L3 beat
  selection (~line 425), **before** `validate_hierarchy` is called (~line
  702). The validator currently overwrites `mark.confidence` with a
  track-level scalar; this proposal makes the validator preserve the
  per-mark agreement value when one is already set, falling back to the
  track-level score only on marks where confidence is None.
- Wire one consumer in `src/generator/effect_placer.py::_place_per_beat`
  (~line 1099): when `mark.confidence >= 0.7`, route the placement to the
  high-confidence ("punch") branch (existing accent placement); when
  `mark.confidence < 0.7` or is None, fall through to the existing
  ("wash") path unchanged. This keeps current behavior the default and
  uses the new field only when it is reliably populated.

**Out of scope (tracked separately):**

- Changing which tracker wins (`select_best_track`'s combined regularity +
  onset score is unchanged).
- Per-event confidence for `aubio_onset` / `librosa_onsets` per-stem onset
  tracks (different topology — these tracks are not selected against
  alternatives in the same way).
- Per-frame chroma confidence in the L6 Harmony block.
- Surfacing per-beat confidence in the review UI (separate UX work).
- Using confidence in L0 wow-trigger detection (separate proposal).

## Capabilities

### New Capabilities

- `analyzer-beat-confidence`: Defines the contract for cross-tracker
  agreement annotation on selected beat and bar tracks — the
  `±window_ms` agreement window, the normalization formula, the
  semantics of `TimingMark.confidence` for L2 / L3 marks after
  annotation, the fallback when only one tracker is available, and the
  ordering rule that selector annotation runs before validator
  annotation.

### Modified Capabilities

<!-- No existing specs at openspec/specs/ govern selector behavior or
     mark-level confidence semantics, so no delta files are required. -->

## Impact

**Code changes:**

- `src/analyzer/selector.py` — new `annotate_agreement_confidence`
  function; new `select_best_beat_track_with_candidates` and
  `select_best_bar_track_with_candidates` variants returning
  `(winner, list_of_losers)` tuples; existing `select_best_beat_track`
  / `select_best_bar_track` kept as thin wrappers for non-orchestrator
  callers.
- `src/analyzer/orchestrator.py` — call new variants at the L2/L3
  selection sites; invoke `annotate_agreement_confidence` before
  `validate_hierarchy`.
- `src/analyzer/validator.py` — preserve any pre-existing `mark.confidence`
  on bar/beat marks; only assign track-level score when current value is
  `None`.
- `src/generator/effect_placer.py::_place_per_beat` — branch on
  `mark.confidence >= 0.7`.
- `tests/unit/test_selector.py` (new) — unit tests for
  `annotate_agreement_confidence`.
- `tests/integration/test_orchestrator_beat_confidence.py` (new) —
  end-to-end check that confidence values reach the `HierarchyResult`.
- `tests/golden/analyzer/baseline.json` — re-snapshot to capture new
  per-mark confidence values for L2 / L3 tracks.

**Shared modules touched:** `src/analyzer/` (86 importers), `src/generator/`
(44 importers). Full Design-First Gate applies; regression surface listed in
`design.md`.

**No new dependencies.**

**Backward compatibility:** The `confidence` field on `TimingMark` is already
`Optional[float]`; today it is populated only by `validator.py` (track-level
scalar) and is `None` everywhere else. After this change, L2 / L3 marks
carry a per-mark agreement score in the same `[0.0, 1.0]` range. All existing
readers of `mark.confidence` (enumerated in `design.md`) treat the field as a
0–1 quality score and continue to work; the value is just more granular.
Marks outside L2 / L3 are unchanged. When only one tracker is available
(quick profile, CI without madmom/vamp), confidence falls back to `None`
(see design rationale).
