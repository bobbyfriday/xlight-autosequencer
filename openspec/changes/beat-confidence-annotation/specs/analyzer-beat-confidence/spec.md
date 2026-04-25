## ADDED Requirements

### Requirement: Selected L3 beat marks carry per-mark cross-tracker agreement confidence

The orchestrator SHALL compute a per-mark agreement score for every mark in the selected L3 beat track when at least one non-winning beat-tracker candidate is available. The score SHALL be written to `TimingMark.confidence` as a `float` in the closed interval `[0.0, 1.0]`.

#### Scenario: Three losers all agree on a beat

- **WHEN** four beat trackers (`librosa_beats`, `qm_beats`, `beatroot_beats`, `madmom_beats`) all run, the winner is selected, and for a given winner mark every one of the three loser tracks has at least one mark within ±35 ms of the winner mark
- **THEN** that mark's `confidence` SHALL equal `1.0`

#### Scenario: No losers agree on a beat

- **WHEN** four beat trackers run, the winner is selected, and for a given winner mark none of the three loser tracks has any mark within ±35 ms
- **THEN** that mark's `confidence` SHALL equal `0.0`

#### Scenario: Partial agreement is normalized

- **WHEN** N total losers are available and exactly K of them have at least one mark within ±35 ms of a given winner mark
- **THEN** that mark's `confidence` SHALL equal `K / N` rounded to 3 decimal places

### Requirement: Selected L2 bar marks carry per-mark cross-tracker agreement confidence

The orchestrator SHALL apply the same per-mark agreement annotation to the selected L2 bar track using the bar candidate set (`qm_bars`, `librosa_bars`, `madmom_downbeats`) and the same ±35 ms window.

#### Scenario: Bar agreement uses the same window

- **WHEN** at least one non-winning bar tracker candidate is available
- **THEN** every mark in the selected L2 bar track SHALL have `confidence` set to a `float` in `[0.0, 1.0]` derived from cross-tracker agreement within ±35 ms

### Requirement: Single-tracker fallback leaves selector confidence as None

The orchestrator SHALL NOT fabricate a confidence value when no loser candidates exist; in that case `TimingMark.confidence` is left as `None` after the selector step, and the validator's track-level fallback SHALL populate it.

#### Scenario: Quick profile yields one beat tracker only

- **WHEN** the analyzer runs with `profile="quick"` (librosa-only) and only `librosa_beats` is available
- **THEN** the selector SHALL leave `confidence = None` on every L3 beat mark immediately after selection
- **AND** the subsequent validator step SHALL populate each mark with the track-level beat score (preserving today's behavior)

### Requirement: Validator preserves selector-assigned confidence on bar and beat marks

The validator SHALL only overwrite `TimingMark.confidence` on L2 / L3 marks when the existing value is `None`. When the selector has already annotated a per-mark agreement value, the validator SHALL leave that value in place but SHALL still report the track-level score in `HierarchyResult.validation['bars']['score']` / `['beats']['score']`.

#### Scenario: Pre-populated confidence is preserved

- **WHEN** a beat mark enters `validate_hierarchy` with `confidence = 0.667`
- **THEN** the validator SHALL leave `confidence = 0.667` unchanged
- **AND** `report['beats']['score']` SHALL still reflect the regularity + onset alignment scalar

#### Scenario: Unset confidence falls back to track-level score

- **WHEN** a beat mark enters `validate_hierarchy` with `confidence = None`
- **THEN** the validator SHALL set `confidence` to the track-level beat score

### Requirement: Per-beat effect placement branches on confidence

The generator SHALL read `TimingMark.confidence` on L3 beat marks during per-beat placement. When `confidence is not None and confidence >= 0.7`, the placement SHALL be routed through the high-confidence ("punch") branch; otherwise the placement SHALL use the existing default ("wash") path. Behavior when `confidence is None` SHALL be identical to behavior before this change.

#### Scenario: High-confidence beat receives punch placement

- **WHEN** `_place_per_beat` encounters a mark with `confidence = 0.8`
- **THEN** the placement SHALL go to the punch branch

#### Scenario: Low-confidence beat receives wash placement

- **WHEN** `_place_per_beat` encounters a mark with `confidence = 0.3`
- **THEN** the placement SHALL go to the default wash branch

#### Scenario: None confidence preserves pre-change behavior

- **WHEN** `_place_per_beat` encounters a mark with `confidence is None`
- **THEN** the placement SHALL go to the same branch it would have taken before this proposal landed

### Requirement: Agreement window is fixed at thirty-five milliseconds

The agreement window SHALL be `35 ms` (symmetric, so `±35 ms` total span of `70 ms`). This value SHALL be passed as the `window_ms` argument to `annotate_agreement_confidence` from the orchestrator and SHALL NOT be configurable through CLI flags or settings files in this change.

#### Scenario: Mark at exactly the window boundary counts as agreeing

- **WHEN** a loser mark sits at exactly `35 ms` distance from a winner mark
- **THEN** it SHALL be counted as agreeing

#### Scenario: Mark just outside the window does not count

- **WHEN** a loser mark sits at `36 ms` distance from a winner mark
- **THEN** it SHALL NOT be counted as agreeing

### Requirement: Selector exposes candidate-list variants for the orchestrator

The selector module SHALL expose `select_best_beat_track_with_candidates` and `select_best_bar_track_with_candidates` functions that return the tuple `(winner: TimingTrack | None, losers: list[TimingTrack])`. The existing `select_best_beat_track` and `select_best_bar_track` functions SHALL remain available with unchanged signatures for non-orchestrator callers.

#### Scenario: With-candidates variant returns winner plus losers

- **WHEN** `select_best_beat_track_with_candidates` is called with four candidates
- **THEN** it SHALL return a tuple whose first element is the chosen winner (or None)
- **AND** whose second element is a list of the remaining three candidates in deterministic order

#### Scenario: Single candidate yields empty loser list

- **WHEN** `select_best_beat_track_with_candidates` is called with exactly one candidate
- **THEN** it SHALL return that candidate as the winner and an empty list as the losers
