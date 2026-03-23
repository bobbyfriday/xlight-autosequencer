# Feature Specification: Vamp Plugin Parameter Tuning

**Feature Branch**: `005-vamp-parameter-tuning`
**Created**: 2026-03-22
**Status**: Draft
**Input**: Add the ability to tune plugin algorithms by trying several permutations of parameters to see if tuning them can produce better results.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a Parameter Sweep on an Algorithm (Priority: P1)

A user suspects the default parameters and/or the default stem for a Vamp algorithm
(e.g., the QM onset detector) are not optimal for a specific song. They want to define
a set of candidate values for one or more parameters **and** a list of stems to try,
have the tool automatically run every combination, and see which pairing of parameters
+ stem produces the highest quality score.

**Why this priority**: This is the core value of the feature — automated exploration
replaces manual trial-and-error. Stem choice is as impactful as parameter choice: an
onset detector run against the isolated drums stem often outperforms the same detector
on full mix, or vice versa. Both dimensions must be tunable together.

**Independent Test**: Can be tested by defining a sweep with 2 stems × 3 sensitivity
values = 6 permutations, verifying all 6 runs complete, and confirming the output
includes a quality score and stem label per permutation.

**Acceptance Scenarios**:

1. **Given** a sweep config specifying two parameters with 3 candidate values each and
   2 stems, **When** the sweep runs, **Then** the tool executes 18 permutations (3 × 3 × 2)
   and records a quality score for each.
2. **Given** a completed sweep, **When** the user views the results, **Then** permutations
   are ranked by quality score, highest first, with the winning parameter set **and stem**
   clearly identified.
3. **Given** a sweep config with an invalid parameter value (wrong type or out of range),
   **When** the sweep is started, **Then** the tool rejects the config before any run
   begins, naming the invalid parameter and its valid range.
4. **Given** a sweep config requesting stems but demucs is not installed, **When** the
   sweep is started, **Then** the tool warns that stem separation is unavailable and
   offers to proceed using full_mix only.
5. **Given** no sweep config, **When** analysis runs normally, **Then** all algorithms
   use their defaults and behavior is identical to the pre-sweep baseline.

---

### User Story 2 - Discover Tunable Parameters (Priority: P2)

Before defining a sweep, a user needs to know which parameters exist for a given
algorithm, what their valid ranges are, and what the defaults are. They can query
the tool to list all tunable parameters for any installed Vamp plugin.

**Why this priority**: Sweep definition is impossible without parameter discovery.
This story is a prerequisite to P1 but can be built and tested independently as a
read-only command.

**Independent Test**: Can be tested by running the parameter-list command for a known
installed plugin and verifying each parameter shows name, type, range, and default.

**Acceptance Scenarios**:

1. **Given** a request to list parameters for a named algorithm, **When** the tool
   responds, **Then** each parameter shows: name, description, data type, valid range
   or allowed values, and default value.
2. **Given** a plugin that is not installed, **When** the user requests its parameter
   list, **Then** the tool reports the plugin as unavailable rather than returning an
   empty or silent result.

---

### User Story 3 - Apply the Winning Parameter Set (Priority: P3)

After a sweep identifies a better-performing parameter combination, the user wants to
save that configuration and use it for future analysis runs on the same song or
similar songs, without re-running the sweep.

**Why this priority**: Sweep results are only durable if the winning config can be
persisted and reused. Without this, every session starts from scratch.

**Independent Test**: Can be tested by saving the top-ranked result from a sweep and
running a standard analysis with that saved config, confirming the output matches the
sweep's top-ranked permutation.

**Acceptance Scenarios**:

1. **Given** a completed sweep, **When** the user saves the top-ranked result as a
   named config, **Then** running analysis with that config name produces the same
   timing tracks as the winning sweep permutation.
2. **Given** a saved config that references a parameter no longer available (plugin
   updated), **When** the config is loaded, **Then** the tool warns about the missing
   parameter and falls back to the plugin's default for that parameter rather than
   failing.

---

### Edge Cases

- A sweep where every permutation produces zero timing marks (degenerate output).
- A parameter combination that causes a Vamp plugin to crash or hang.
- Sweep config that defines more permutations than a practical limit (e.g., hundreds
  of runs on a long audio file — tool should warn about estimated runtime before starting).
- Two parameters within the same plugin that are interdependent (one valid range
  depends on the value of the other).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept a sweep config that defines, for a target algorithm,
  a list of candidate values for each parameter to vary AND an optional list of stems
  to try (e.g., `["full_mix", "drums", "bass"]`).
- **FR-002**: The tool MUST automatically execute every combination of parameter values
  × stems and record a quality score and stem label per permutation. Stem separation
  MUST run once and be reused across all permutations that share the same audio source.
- **FR-002a**: When stems are requested, the tool MUST use the existing stem cache
  (`StemCache`) so that repeated sweeps on the same file do not re-run Demucs.
- **FR-002b**: When stems are requested but stem separation is unavailable (demucs not
  installed), the tool MUST warn the user and offer to continue with full_mix only.
- **FR-003**: Sweep results MUST be ranked by quality score and presented in a
  summary that identifies the top-performing parameter combination **and stem**.
- **FR-004**: All parameter values in a sweep config MUST be validated against each
  plugin's declared schema before any permutation runs.
- **FR-005**: The tool MUST provide a command to list all tunable parameters for a
  named algorithm, including name, description, type, valid range, and default value.
- **FR-005a**: For numeric parameters, the tool MUST be able to suggest a set of
  evenly-spaced candidate values across the valid range, so users have a starting
  point without guessing.
- **FR-006**: The tool MUST allow the top-ranked (or any named) sweep result to be
  saved as a reusable config for future analysis runs.
- **FR-007**: When no sweep config is provided, all algorithms MUST behave identically
  to their pre-sweep baseline.
- **FR-008**: Sweep permutations for each algorithm MUST be independent — varying
  parameters for one algorithm MUST NOT affect results for other algorithms.
- **FR-009**: The tool MUST display the estimated number of permutations and a
  runtime estimate before executing a sweep, allowing the user to cancel.

### Key Entities

- **SweepConfig**: Defines the sweep — target algorithm, parameter name → list of
  candidate values, and an optional list of stems to try.
- **PermutationResult**: A single sweep run — the specific parameter values used,
  the stem used, the resulting timing track, and the quality score.
- **SweepReport**: The full output of a sweep — all PermutationResults ranked by
  quality score, with the winning combination (parameters + stem) highlighted.
- **SavedConfig**: A named, persisted parameter set + stem derived from a sweep
  result, loadable for future analysis runs.
- **ParameterDescriptor**: Metadata for a single tunable parameter — name,
  description, type, min, max, default, allowed values (for enum types).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a sweep across 2 stems × 5 parameter values = 10 permutations on
  a 3-minute audio file, all runs complete and results are ranked without user
  intervention. Stem separation runs once regardless of how many permutations use stems.
- **SC-002**: The top-ranked permutation (parameter set + stem) from a sweep produces
  a measurably higher quality score than the default parameter + default stem run on
  the same file.
- **SC-003**: A user with no prior knowledge of Vamp internals can discover available
  parameters, define a stem + parameter sweep, and obtain ranked results without
  reading source code.
- **SC-004**: Invalid parameter values in a sweep config are caught before any
  analysis runs, with an error message identifying the invalid parameter and its
  valid range.
- **SC-005**: Saving and reloading a winning sweep config (including its stem) produces
  identical quality scores to the original sweep run on the same audio file.

---

## Assumptions

- Vamp's Python host exposes plugin parameter metadata at runtime; this is used for
  discovery and validation rather than maintaining a static parameter registry.
- The existing quality scorer (`scorer.py`) provides a sufficient signal for ranking
  permutations; no new scoring logic is required for the initial scope.
- Parameter sweeps apply to Vamp plugin algorithms only in this feature; librosa and
  madmom parameter exposure is a separate future feature.
- Permutations are per-algorithm (not cross-algorithm combinations), keeping the
  combinatorial space manageable.
- Saved configs use the existing JSON file format used throughout the project.

---

## Out of Scope

- Automated optimization (Bayesian search, genetic algorithms, gradient-based tuning).
- A graphical UI for sweep configuration or result visualization.
- Cross-algorithm parameter optimization (finding optimal combos across multiple
  algorithms simultaneously).
- Parameter tuning for librosa or madmom algorithms.
