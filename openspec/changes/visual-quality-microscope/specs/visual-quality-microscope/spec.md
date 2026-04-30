## ADDED Requirements

### Requirement: Metric direction-of-good defaults to unknown

`MetricDefinition.higher_is_better` SHALL default to `None`. A `None`
value indicates that the direction-of-good for the metric has not been
validated against rendered output. The diff tool SHALL render movement
arrows (`↑` / `↓`) but MUST NOT render improvement claims (`✓` / `✗`)
for `None`-direction metrics.

A `True` default would silently add improvement claims to every
existing metric registration; this is forbidden.

#### Scenario: Existing metric registered without explicit direction

- **WHEN** a metric module registers a `MetricDefinition` without
  passing `higher_is_better`
- **THEN** the registry SHALL store `higher_is_better = None`
- **AND** the diff tool SHALL render `↑` / `↓` movement arrows for
  this metric without `✓` / `✗` overlays

#### Scenario: Metric registered with explicit direction

- **WHEN** a metric module registers a `MetricDefinition` with
  `higher_is_better=False` and the metric description flags the
  direction as "unvalidated"
- **THEN** the registry SHALL store `higher_is_better = False`
- **AND** the diff tool SHALL render `↑✗` for positive deltas and
  `↓✓` for negative deltas

### Requirement: Palette-luminance metrics are duration-weighted and disclaim brightness

The `palette_luminance_mean` and `palette_luminance_cv` metrics SHALL
be computed by:

- Parsing each placement's `palette_colors` from `xsq_reader.py`.
- Computing per-color luminance using the Rec.601 luma formula
  (`L = 0.299*R + 0.587*G + 0.114*B`, range 0–255).
- Computing per-placement mean luminance over active colors.
- Aggregating to the song level as a duration-weighted mean (longer
  placements count more).
- Computing the coefficient of variation as
  `(duration-weighted std-dev) / (duration-weighted mean)` so both
  metrics describe the same population under the same weighting.

Metric names MUST NOT contain phenomenon-implying language such as
`brightness`, `breathing`, or `dynamics`. Descriptions MUST state
explicitly that the values are palette-derived proxies, not
measurements of rendered light.

#### Scenario: Empty placements

- **WHEN** the `SequenceSummary` contains zero placements
- **THEN** both `palette_luminance_mean` and `palette_luminance_cv`
  SHALL return `0.0`
- **AND** their `MetricResult.reliability` SHALL be `"no_placements"`

#### Scenario: Two placements with widely different luminance and unequal duration

- **WHEN** placement A has duration 1000 ms and per-color luminance
  255, and placement B has duration 9000 ms and per-color luminance
  10
- **THEN** `palette_luminance_mean` SHALL equal the
  duration-weighted mean (`(255*1000 + 10*9000) / 10000`)
- **AND** `palette_luminance_cv` SHALL be computed from the same
  duration-weighted population (NOT the unweighted population)

### Requirement: Pairing-fit signals are computed in parallel without picking a winner

The microscope SHALL compute three parallel pairing-fit metrics:

- `bad_pairing_pct_handlist`: fraction of evaluable placements whose
  `(effect_type, prop_type)` matches an entry in
  `HANDLIST_BAD_PAIRINGS` (a short list of widely-claimed-bad
  pairings, documented as opinion).
- `bad_pairing_pct_catalog`: fraction of evaluable placements where
  the catalog at `src/effects/builtin_effects.json:effects[<effect>].prop_suitability[<prop>]`
  is `"not_recommended"`.
- `pairing_disagreement_pct`: fraction of evaluable placements where
  exactly one of the two signals flagged the placement (i.e., the
  two sources disagree).

The microscope MUST NOT designate either source as ground truth in
v1. Both metrics SHALL carry `higher_is_better=False` with
descriptions that explicitly flag the directional claim as
"unvalidated until rendered output corroborates."

#### Scenario: Catalog and handlist disagree on a placement

- **WHEN** a placement's `effect_type` is `"Plasma"` and its inferred
  `prop_type` is `"outline"`
- **AND** the catalog records `prop_suitability.outline = "possible"`
  for `Plasma`
- **AND** the handlist records `Plasma → {outline, arch}` as bad
- **THEN** `bad_pairing_pct_handlist` SHALL count this placement
- **AND** `bad_pairing_pct_catalog` SHALL NOT count this placement
- **AND** `pairing_disagreement_pct` SHALL count this placement

#### Scenario: Catalog and handlist agree that a placement is bad

- **WHEN** a placement's `effect_type` is `"Pinwheel"` and its
  inferred `prop_type` is `"arch"`
- **AND** the catalog records `prop_suitability.arch = "not_recommended"`
- **AND** the handlist records `Pinwheel → {outline, arch}` as bad
- **THEN** both `bad_pairing_pct_handlist` and `bad_pairing_pct_catalog`
  SHALL count this placement
- **AND** `pairing_disagreement_pct` SHALL NOT count this placement
  (they agree, so there is no disagreement to flag)

#### Scenario: Catalog file is missing or unreadable

- **WHEN** `src/effects/builtin_effects.json` cannot be loaded
- **THEN** `bad_pairing_pct_catalog` and `pairing_disagreement_pct`
  SHALL return `0.0`
- **AND** their `MetricResult.reliability` SHALL be `"catalog_missing"`
- **AND** `bad_pairing_pct_handlist` SHALL still return its computed
  value (independent of the catalog)

### Requirement: Microscope measures the parsed XSQ, not the in-memory SequencePlan

The microscope runner SHALL invoke `generate_sequence()` from
`src.generator.plan` to produce an XSQ file on disk, then parse the
XSQ via `src.evaluation.xsq_reader.parse_xsq()` to produce a
`SequenceSummary`, and compute metrics from that summary.

The runner MUST NOT compute metrics directly from the in-memory
`SequencePlan`. The XSQ is the artifact users load into xLights;
serialization bugs in `src/generator/xsq_writer.py` would otherwise be
invisible to the microscope.

The generated XSQ SHALL be retained at
`<output_dir>/microscope/<slug>/sequence.xsq` for manual inspection
after a run.

#### Scenario: Run on a single song

- **WHEN** the runner is called with a song path, layout path, output
  dir, and config overrides
- **THEN** it SHALL produce an XSQ file at the documented path
- **AND** it SHALL return a `MicroscopeResult` whose `summary` field
  is a `SequenceSummary` parsed from that XSQ

### Requirement: Microscope runs are deterministic given a pinned variation seed

The runner SHALL pin `variation_seed` to a default of `42` in the
`GenerationConfig` it constructs. Running the runner twice on the
same song with the same seed SHALL produce identical scalar metric
values (absolute delta strictly less than `1e-9`).

The seed value SHALL be recorded in the `MicroscopeResult.config_snapshot`
so the JSON output makes determinism inspectable.

#### Scenario: Two consecutive runs with the same seed

- **WHEN** `run_song(song, layout, output_dir, config_overrides={})`
  is called twice in succession with no other changes
- **THEN** every scalar metric in the second result SHALL match the
  first within `1e-9` absolute tolerance

#### Scenario: Two runs with different seeds

- **WHEN** the first run uses `variation_seed=42` and the second uses
  `variation_seed=43`
- **THEN** at least one scalar metric SHALL move by `≥ 1e-3`

### Requirement: Microscope CLI is registered under `xlight-evaluate`

The microscope subcommand group SHALL be registered on the existing
`xlight-evaluate` Click CLI (alongside `gate`, `check`, `compare`,
`snapshot`, `snapshot-analyzer`, `snapshot-section-fidelity`).

The microscope MUST NOT be registered on `xlight-analyze`. The
`xlight-analyze` command's existing subcommand surface (`analyze`,
`summary`, `export`, `review`, `generate`) is dedicated to producing
and exporting analysis output; quality measurement is the
responsibility of `xlight-evaluate`.

The group SHALL expose four subcommands:
- `run <audio_path>` — single-song measurement.
- `panel` — multi-song panel measurement.
- `sensitivity` — runs the sensitivity probes and writes
  `tests/golden/microscope/sensitivity_passed.json` on success.
- `baseline` — copies metric files into the golden directory after
  verifying the sensitivity gate.

#### Scenario: Help output for `xlight-evaluate`

- **WHEN** the user runs `xlight-evaluate --help`
- **THEN** the output SHALL list `microscope` in the Commands section

#### Scenario: Help output for `xlight-analyze`

- **WHEN** the user runs `xlight-analyze --help`
- **THEN** the output SHALL NOT list `microscope` in the Commands
  section

### Requirement: Baseline commits are gated on a passing sensitivity proof

The `baseline` subcommand SHALL refuse to copy metric files into the
golden directory unless
`tests/golden/microscope/sensitivity_passed.json` exists and is at
least as recent as the most recent commit touching any of the
staleness-cone paths:

- `src/evaluation/metrics/` (the metric implementations)
- `src/evaluation/xsq_reader.py` (prop-type inference affects
  pairing metrics)
- `src/effects/builtin_effects.json` (catalog feeds
  `bad_pairing_pct_catalog`)

The check SHALL use `git log -1 --format=%ct -- <staleness-cone>`
and compare the committer timestamp against the proof's `run_at`
ISO timestamp.

The sensitivity proof file SHALL be written only by the
`sensitivity` subcommand, after all of the following probes pass:

1. **Single-effect override** — when every placement is forced to a
   single effect, `distinct_effect_count` equals `1` and
   `effect_repeat_rate` is at least `0.95`.
2. **All-black palette override** — when every placement is forced
   to a palette of `(#000000,)`, `palette_luminance_mean` equals
   `0.0` and `palette_luminance_cv` equals `0.0`.
3. **Forced-bad-pairing via synthetic SequenceSummary** — a
   `SequenceSummary` constructed directly (not via the generator
   pipeline) whose every `Placement` has `effect_type="Plasma"` and
   a `model_name` resolving to `outline` SHALL produce
   `bad_pairing_pct_handlist > 0.95` AND
   `bad_pairing_pct_catalog == 0.0` AND
   `pairing_disagreement_pct > 0.95`. The probe demonstrates the
   handlist/catalog gap under a forced condition; if both pairing
   signals agree here, one is mis-implemented.
4. **Deterministic seed** — two runs with `variation_seed=42`
   produce zero deltas; one run with `variation_seed=43` produces a
   non-zero delta on at least one scalar metric.

#### Scenario: Baseline subcommand without sensitivity proof

- **WHEN** the user runs `xlight-evaluate microscope baseline`
- **AND** `tests/golden/microscope/sensitivity_passed.json` does not
  exist
- **THEN** the command SHALL exit with a non-zero status
- **AND** SHALL print a message instructing the user to run
  `xlight-evaluate microscope sensitivity` first

#### Scenario: Sensitivity proof is older than recent metric changes

- **WHEN** `tests/golden/microscope/sensitivity_passed.json` exists
- **AND** a commit newer than the proof's `run_at` field touches any
  of `src/evaluation/metrics/`, `src/evaluation/xsq_reader.py`, or
  `src/effects/builtin_effects.json`
- **THEN** the `baseline` subcommand SHALL exit with a non-zero
  status
- **AND** SHALL print a message instructing the user to re-run
  sensitivity before committing a new baseline

### Requirement: Prop-type inference covers the catalog vocabulary

`src/evaluation/xsq_reader.py:_PROP_TYPE_TOKENS` SHALL include the
tokens `radial` and `vertical` so that the inferred prop-type
vocabulary aligns with the catalog's
`{matrix, outline, arch, vertical, tree, radial}`.

The token additions SHALL be additive: every model name that resolved
to a specific prop type before this change SHALL resolve to the same
type after.

#### Scenario: Layout model named `RadialSpinner`

- **WHEN** `_infer_prop_type("RadialSpinner")` is called
- **THEN** the function SHALL return `"radial"`

#### Scenario: Layout model named `OutlineRoofLeft`

- **WHEN** `_infer_prop_type("OutlineRoofLeft")` is called
- **THEN** the function SHALL return `"outline"`

#### Scenario: Pre-existing model name `MatrixCenter`

- **WHEN** `_infer_prop_type("MatrixCenter")` is called
- **THEN** the function SHALL still return `"matrix"`
- **AND** the result SHALL match the value produced before the
  `radial` and `vertical` tokens were added

### Requirement: Reference panel and layout SHALL cover five catalog prop types

The reference panel manifest SHALL list four CC0 fixtures and the reference layout SHALL contain at least nine props whose inferred types cover at least five of the six catalog prop-type values.

Specifically, the manifest at `tests/fixtures/reference/panel_manifest.json`
SHALL list `funshine`, `maple_leaf_rag`, `nostalgic_piano`, and
`space_ambience`.

The reference layout at `tests/fixtures/reference/layout.xml` SHALL
contain nine props whose model names cause `_infer_prop_type` to
return prop types covering at least five of the six catalog values
(`matrix`, `outline`, `arch`, `tree`, `radial`).

A documented gap is acceptable for `vertical`, since the user's
xLights install does not include a vertical-only prop. The gap MUST
be documented in the layout XML's header comment.

#### Scenario: Inferred prop types from the reference layout

- **WHEN** the reference layout is parsed
- **AND** `_infer_prop_type` is applied to every model name
- **THEN** the resulting set SHALL include `matrix`, `outline`,
  `arch`, `tree`, and `radial`

### Requirement: Panel runner reuses the existing fixture-download API

`src/microscope/panel.py:run_panel` SHALL resolve each panel slug's
MP3 path by:

1. First checking `tests/fixtures/cc0_music/<slug>.mp3` and using it
   if present.
2. If any slug is missing, calling
   `tests.validation.download_fixtures.download_all()` (the function
   that exists in that module) once for the run, then re-checking
   each slug's path.

The runner MUST NOT call any function named `ensure_fixture(slug)`
in `tests.validation.download_fixtures`. No such function exists in
that module.

#### Scenario: All panel fixtures already downloaded

- **WHEN** `run_panel` is called and every slug's MP3 exists at
  `tests/fixtures/cc0_music/<slug>.mp3`
- **THEN** `download_all()` SHALL NOT be called
- **AND** the runner SHALL produce one `MicroscopeResult` per slug

#### Scenario: At least one panel fixture is missing

- **WHEN** `run_panel` is called and at least one slug's MP3 is
  absent
- **THEN** `download_all()` SHALL be called exactly once for the run
- **AND** the runner SHALL re-resolve the missing slugs from the
  result and proceed
