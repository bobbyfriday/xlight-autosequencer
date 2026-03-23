# Feature Specification: Vamp Plugin Parameter Tuning

**Feature Branch**: `005-vamp-parameter-tuning`
**Created**: 2026-03-22
**Status**: Placeholder
**Input**: Expose Vamp plugin algorithm parameters as user-configurable settings so that the analysis pipeline can be tuned per-song or globally, replacing the current hard-coded defaults with a configuration layer that enables experimentation and optimization.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Algorithm Parameters Before Analysis (Priority: P1)

A user knows that the default Vamp beat tracker tends to drift on a particular song, or
that the onset detection sensitivity produces too many marks for a dense track. They
want to adjust specific algorithm parameters — without editing source code — and re-run
analysis to see if the results improve.

**Why this priority**: Out-of-box defaults produce acceptable results for typical songs
but fail on outliers. Parameter access is what separates a research tool from a
production pipeline.

**Acceptance Scenarios**:

1. **Given** a configuration file or CLI flag, **When** the user overrides a specific
   Vamp plugin parameter, **Then** analysis uses the overridden value and the output
   records which parameters were used.
2. **Given** the same MP3 run with two different parameter sets, **When** the outputs
   are compared, **Then** the resulting timing tracks differ in ways consistent with
   the parameter changes made.
3. **Given** an invalid parameter value (out of range, wrong type), **When** analysis
   is started, **Then** the tool rejects the configuration with a clear error message
   before running any analysis.
4. **Given** no parameter overrides, **When** analysis runs, **Then** all algorithms
   use their documented defaults and produce identical results to the previous
   non-configurable version.

---

### User Story 2 - Parameter Discovery (Priority: P2)

A user does not know what parameters are available for a given algorithm. They can
query the tool to list all tunable parameters for any installed Vamp plugin, including
the parameter name, description, type, range, and current default value.

**Why this priority**: Parameter tuning is useless if the user cannot discover what
is tunable. Discovery is a prerequisite to informed experimentation.

**Acceptance Scenarios**:

1. **Given** a request to list parameters for a named algorithm, **When** the tool
   responds, **Then** each parameter shows: name, description, data type, valid range
   or allowed values, and default value.
2. **Given** a Vamp plugin that is not installed, **When** the user requests its
   parameter list, **Then** the tool indicates the plugin is unavailable rather than
   returning an empty or error result.

---

### User Story 3 - Parameter Presets (Priority: P3)

Users can save a named set of parameter overrides as a preset and recall it by name
when running analysis. This lets users maintain per-genre or per-song configurations
without re-specifying all values each run.

**Acceptance Scenarios**:

1. **Given** a set of parameter overrides, **When** the user saves them as a named
   preset, **Then** running analysis with that preset name applies all saved overrides.
2. **Given** a preset that references a parameter no longer available (plugin updated),
   **When** the preset is loaded, **Then** the tool warns about the missing parameter
   and skips it rather than failing.

---

### Edge Cases

- A parameter override that puts an algorithm into a degenerate state (e.g., window
  size larger than the audio file).
- Conflicting parameter values between interdependent settings within a plugin.
- Vamp plugin versions that change available parameters between updates.
- Parameter values that are valid but produce zero timing marks.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST allow per-algorithm parameter overrides via a configuration
  file and/or CLI flags.
- **FR-002**: Parameter overrides MUST be validated against each plugin's declared
  parameter schema before analysis begins.
- **FR-003**: The analysis output MUST record the full parameter set (defaults +
  overrides) used for each algorithm run, so results are reproducible.
- **FR-004**: The tool MUST provide a command to list all tunable parameters for a
  named algorithm, including name, description, type, range, and default.
- **FR-005**: Overriding parameters for one algorithm MUST NOT affect any other
  algorithm's parameters.
- **FR-006**: When no overrides are specified, all algorithms MUST behave identically
  to the pre-configuration-layer baseline.
- **FR-007**: Named parameter presets MUST be saveable and loadable from the filesystem.

### Key Entities

- **AlgorithmConfig**: A named set of parameter overrides for a single algorithm —
  algorithm name, map of parameter name → value.
- **AnalysisConfig**: The full configuration for a run — list of AlgorithmConfigs,
  named preset (optional), global defaults.
- **ParameterDescriptor**: Metadata about a single tunable parameter — name,
  description, type, min, max, default, allowed values (for enum types).
- **Preset**: A named, saved AnalysisConfig stored on the filesystem.

---

## Success Criteria *(mandatory)*

- A user with no prior knowledge of Vamp internals can discover, set, and validate a
  parameter override without reading source code.
- Running analysis with an explicit parameter config produces results that differ from
  the defaults in the expected direction (e.g., lower sensitivity → fewer marks).
- All parameters used in a run are captured in the output file, enabling exact
  reproduction of results from a saved analysis JSON alone.
- Invalid parameter values are caught before any analysis runs, with a message that
  identifies the invalid parameter and its valid range.

---

## Assumptions

- Vamp's Python host exposes plugin parameter metadata at runtime; this will be used
  for discovery and validation rather than maintaining a static parameter registry.
- Parameter tuning applies initially to Vamp plugins; librosa and madmom parameter
  exposure may follow in a later iteration.
- Preset storage uses the same JSON file format as the rest of the project.

---

## Out of Scope

- Automated parameter search or optimization (grid search, Bayesian optimization).
- A graphical UI for parameter editing (the review UI from feature 002 may eventually
  expose this, but it is not part of this feature).
- Parameter tuning for librosa or madmom algorithms (Vamp only for initial scope).
