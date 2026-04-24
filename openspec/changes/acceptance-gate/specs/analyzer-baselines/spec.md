## ADDED Requirements

### Requirement: Analyzer baseline captures full timing-track set per fixture

The system SHALL maintain a baseline file at `tests/golden/analyzer/baseline.json` containing, for each fixture in the portable corpus, the complete set of timing tracks produced by every analyzer algorithm (beats, downbeats, sections, onsets, vocal phonemes, chords, and any others currently in `src/analyzer/algorithms/`). Each timing track SHALL store the full list of timestamped events plus a per-algorithm tolerance rule.

#### Scenario: Baseline contains every algorithm's output

- **WHEN** `xlight-evaluate snapshot --analyzer` runs
- **THEN** the resulting `baseline.json` SHALL contain an entry for every `Algorithm` class discoverable under `src/analyzer/algorithms/`
- **AND** each entry SHALL include timestamps for every event the algorithm produced on that fixture

#### Scenario: New algorithm added without baseline update

- **WHEN** a new algorithm class is added to `src/analyzer/algorithms/` but the baseline has not been regenerated
- **THEN** the analyzer suite SHALL report a `no-baseline-for-algorithm` warning
- **AND** the suite SHALL NOT fail the gate solely on that warning
- **AND** the next `xlight-evaluate snapshot --analyzer` run SHALL capture the new algorithm

### Requirement: Per-algorithm tolerance rules

Each algorithm's baseline entry SHALL include a tolerance rule specifying:

- `count_tolerance_pct`: acceptable percentage variance in the total number of events (default 5%).
- `timing_tolerance_ms`: acceptable per-event timestamp drift in milliseconds (default 50ms).
- `algorithm_specific`: optional dict of algorithm-specific rules (e.g., `enharmonic_equivalents: true` for chord trackers, `merge_window_ms: 2000` for section trackers).

Comparison SHALL sort events by timestamp, check counts against `count_tolerance_pct`, then pair events in order and check each pair against `timing_tolerance_ms`. If counts differ by more than tolerance, pairing is abandoned and the count mismatch is reported.

#### Scenario: Algorithm produces same events with <50ms drift

- **WHEN** an analyzer run produces the same number of events as the baseline with every event within 50ms of the corresponding baseline event
- **THEN** the suite SHALL report PASS for that algorithm-fixture pair

#### Scenario: Algorithm produces shifted events beyond tolerance

- **WHEN** an analyzer run produces events shifted by more than `timing_tolerance_ms` relative to the baseline
- **THEN** the suite SHALL report FAIL for that algorithm-fixture pair
- **AND** the report SHALL include the event index and the observed vs expected timestamp

#### Scenario: Chord tracker produces enharmonic equivalent

- **WHEN** a chord tracker produces `F#m` where the baseline has `Gbm` and the algorithm's tolerance has `enharmonic_equivalents: true`
- **THEN** the chord SHALL be considered equivalent for comparison
- **AND** the suite SHALL report PASS on that event

### Requirement: Baseline update requires human review

Updating `tests/golden/analyzer/baseline.json` SHALL be a deliberate developer action via `xlight-evaluate snapshot --analyzer`. The command SHALL print a diff summary (algorithms changed, event count deltas, median timing drift) to stdout before writing the file. The committed baseline diff SHALL be visible in the PR for human review.

#### Scenario: Baseline regeneration shows large drift

- **WHEN** `xlight-evaluate snapshot --analyzer` produces a new baseline where median timing drift exceeds 100ms for any algorithm
- **THEN** the command SHALL print a `LARGE-DRIFT WARNING` in the summary
- **AND** the developer SHALL be able to confirm or abort the snapshot via a prompt (or `--yes` to skip the prompt in CI regeneration flows)
