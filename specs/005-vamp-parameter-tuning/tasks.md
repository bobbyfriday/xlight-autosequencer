# Tasks: Vamp Plugin Parameter Tuning

**Input**: Design documents from `/specs/005-vamp-parameter-tuning/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included — required by project constitution (TDD: Red-Green-Refactor).

**Organization**: Tasks are grouped by implementation dependency order. The algorithm
refactor (Phase 2) is a blocking prerequisite for all user stories. US2 (discovery)
comes before US1 (sweep) because the discovery validation logic is required by US1's
parameter validation acceptance scenario.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story (US1=Run Sweep, US2=Discover Parameters, US3=Apply Config)

---

## Phase 1: Setup

**Purpose**: Stub out new modules so later tasks have a target to write into.

- [ ] T001 Create empty module stubs: `src/analyzer/vamp_params.py` and `src/analyzer/sweep.py` (module docstrings only, no logic)
- [ ] T002 Create empty test files: `tests/unit/test_vamp_params.py`, `tests/unit/test_sweep.py`, `tests/integration/test_sweep_integration.py`

---

## Phase 2: Foundational — Algorithm Refactor

**Purpose**: Make all Vamp `_run()` methods use `self.parameters` + `self.vamp_output`
instead of hardcoded values. This is what enables the sweep runner to vary parameters
without subclassing. **MUST complete before any user story work begins.**

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Add `vamp_output: str | None = None` class attribute to `Algorithm` in `src/analyzer/algorithms/base.py`
- [ ] T004 [P] Refactor `QMOnsetComplexAlgorithm`, `QMOnsetHFCAlgorithm`, `QMOnsetPhaseAlgorithm` in `src/analyzer/algorithms/vamp_onsets.py`: add `vamp_output = "onsets"` attribute, remove `"output"` key from `parameters` dict, change `vamp.collect()` calls to use `output=self.vamp_output, parameters=self.parameters`
- [ ] T005 [P] Refactor `QMBeatAlgorithm`, `QMBarAlgorithm`, `BeatRootAlgorithm` in `src/analyzer/algorithms/vamp_beats.py`: add `vamp_output` attributes (`"beats"` / `"bars"`), remove `"output"` from `parameters` dict, update `vamp.collect()` calls
- [ ] T006 [P] Refactor `QMSegmenterAlgorithm`, `QMTempoAlgorithm` in `src/analyzer/algorithms/vamp_structure.py`: add `vamp_output` attributes, update `vamp.collect()` calls
- [ ] T007 [P] Refactor `PYINNotesAlgorithm`, `PYINPitchChangesAlgorithm` in `src/analyzer/algorithms/vamp_pitch.py`: add `vamp_output` attributes, update `vamp.collect()` calls
- [ ] T008 [P] Refactor `ChordinoAlgorithm`, `NNLSChromaAlgorithm` in `src/analyzer/algorithms/vamp_harmony.py`: add `vamp_output` attributes, update `vamp.collect()` calls
- [ ] T009 Verify all existing algorithm tests pass after refactor — no behavior change expected; run `pytest tests/` and confirm green

**Checkpoint**: All Vamp algorithms now use `self.parameters` + `self.vamp_output`. Existing tests green. User story work can begin.

---

## Phase 3: User Story 2 — Parameter Discovery (Priority: P2)

**Goal**: Provide runtime discovery of tunable Vamp plugin parameters with validation.
US2 is implemented before US1 because `VampParamDiscovery.validate_params()` is
required by the `sweep` command's parameter validation (US1 acceptance scenario 3).

**Independent Test**: Run `xlight-analyze params qm-vamp-plugins:qm-onsetdetector`
and confirm it lists parameters with names, types, ranges, and defaults. Run with an
unknown plugin key and confirm a clear unavailable message (not an error trace).

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (T011–T014)**

- [ ] T010 [P] [US2] Write failing unit tests for `VampParamDiscovery` in `tests/unit/test_vamp_params.py`: mock `vamp.vampyhost.load_plugin()` to return a fake plugin object with known descriptors; test `list_params()` returns correct `ParameterDescriptor` list; test missing plugin returns error (not empty list); test `suggest_values()` returns correct evenly-spaced floats; test `validate_params()` passes valid values and fails out-of-range, wrong-type, and quantization violations

### Implementation for User Story 2

- [ ] T011 [US2] Implement `ParameterDescriptor` dataclass in `src/analyzer/vamp_params.py` with fields: `identifier`, `name`, `description`, `unit`, `min_value`, `max_value`, `default_value`, `is_quantized`, `quantize_step`, `value_names` (see data-model.md)
- [ ] T012 [US2] Implement `VampParamDiscovery.list_params(plugin_key, sample_rate=44100)` in `src/analyzer/vamp_params.py`: call `vamp.vampyhost.load_plugin()`, call `plugin.get_parameter_descriptors()`, map each descriptor to `ParameterDescriptor`; raise `PluginNotFoundError` if plugin unavailable
- [ ] T013 [US2] Implement `VampParamDiscovery.suggest_values(descriptor, steps)` in `src/analyzer/vamp_params.py`: return `steps` evenly-spaced floats between `descriptor.min_value` and `descriptor.max_value`; raise `ValueError` if descriptor is a pure enum (value_names non-empty and not numeric)
- [ ] T014 [US2] Implement `VampParamDiscovery.validate_params(plugin_key, params, sample_rate=44100)` in `src/analyzer/vamp_params.py`: return list of error strings (empty = valid); check each key is a valid identifier, each value is in `[min_value, max_value]`, and quantized params satisfy the step constraint
- [ ] T015 [P] [US2] Add `params` CLI command to `src/cli.py`: accepts `plugin_key` argument and optional `--suggest-steps N`; calls `VampParamDiscovery.list_params()` and prints formatted table per contracts/cli-commands.md; handles plugin-not-found with exit code 1
- [ ] T016 [P] [US2] Add `sweep-suggest` CLI command to `src/cli.py`: accepts `plugin_key` and `param_name` arguments, optional `--steps N` (default 5); calls `VampParamDiscovery.list_params()` then `suggest_values()`; prints values and copy-paste snippet for sweep config; exit code 2 if parameter is non-numeric enum

**Checkpoint**: US2 independently testable. `params` and `sweep-suggest` commands functional. `validate_params()` ready for US1 to consume.

---

## Phase 4: User Story 1 — Run a Parameter Sweep (Priority: P1) 🎯 MVP

**Goal**: Accept a sweep config JSON, run every permutation of a target Vamp algorithm,
score each result with the existing quality scorer, and write a ranked `SweepReport`.

**Independent Test**: Create a sweep config JSON targeting `qm_onsets_complex` with
2 parameter values × 2 parameter values = 4 permutations. Run
`xlight-analyze sweep fixture.mp3 --config sweep.json`. Confirm 4 results appear in
the output ranked by quality score, the report JSON is written, and an invalid
parameter value in the config is caught before any analysis runs.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (T018–T023)**

- [ ] T017 [P] [US1] Write failing unit tests for `SweepConfig` in `tests/unit/test_sweep.py`: test `from_file()` with valid JSON, missing `algorithm` key, key appearing in both `sweep` and `fixed`; test `permutations()` returns correct cartesian product including stems (2 stems × 3 params = 6 `(stem, param_dict)` tuples); test `permutation_count()` = stems × param combos; test with empty `stems` yields algorithm's `preferred_stem`; test `validate()` catches invalid param name, out-of-range value, and invalid stem name using mock `VampParamDiscovery`
- [ ] T018 [P] [US1] Write failing unit tests for `SweepRunner` and `SweepReport` in `tests/unit/test_sweep.py`: mock `Algorithm.run()` to return deterministic `TimingTrack`s; mock a `StemSet` with two stems returning distinct arrays; verify `SweepReport.results` is sorted by `quality_score` descending; verify each result carries the correct `stem` field; verify rank 1 has highest score; verify `SweepReport.to_dict()` / `from_dict()` round-trips cleanly including `stems_tested` and `stem` fields on each result

### Implementation for User Story 1

- [x] T019 [US1] Implement `SweepConfig` dataclass in `src/analyzer/sweep.py` with fields `algorithm`, `stems` (list[str], default empty), `sweep_params`, `fixed_params`; implement `from_file(path)` to load and parse JSON; implement `permutations()` as a generator yielding `(stem, param_dict)` tuples for every cartesian product of stems × parameter combinations (when `stems` is empty, yield `(algorithm.preferred_stem, param_dict)` for each param combo); implement `permutation_count()`; implement `validate(discovery)` returning list of error strings including invalid stem names
- [x] T020 [US1] Implement `PermutationResult` dataclass in `src/analyzer/sweep.py` with fields `rank`, `stem`, `parameters`, `quality_score`, `mark_count`, `avg_interval_ms`, `track`
- [x] T021 [US1] Implement `SweepReport` dataclass in `src/analyzer/sweep.py` with fields per data-model.md (including `stems_tested`); implement `to_dict()`, `from_dict()`, `write(path)`, `read(path)`
- [x] T022 [US1] Implement `SweepRunner` in `src/analyzer/sweep.py`: build algorithm registry mapping name → class from existing Vamp algorithm imports; implement `run(audio_path, config, stems: StemSet | None, progress_callback=None)` — loads audio once via `load()`, iterates `config.permutations()` which yield `(stem, param_dict)` tuples, routes each permutation to the correct stem array via the existing `_select_audio()` logic (or equivalent), instantiates algorithm with overridden `parameters`, calls `algo.run()`, scores with `score_track()`, collects `PermutationResult`s with `stem` field set, sorts by `quality_score` descending, assigns `rank`, returns `SweepReport`
- [x] T023 [US1] Add `sweep` CLI command to `src/cli.py`: accepts `audio_file` argument, `--config PATH` (required), `--output PATH`, `--yes` flag; loads + validates config; if config specifies non-empty `stems`, run `StemSeparator().separate()` (uses cache) before sweep — if demucs unavailable, warn and prompt to fall back to full_mix; computes permutation count (stems × param combos) and prompts confirmation if > 20 and `--yes` not set; runs `SweepRunner.run(audio_path, config, stems)` with progress callback showing stem + params per line; writes report; prints ranked summary table including STEM column per contracts/cli-commands.md; handles exit codes per contract
- [x] T024 [US1] Write integration test in `tests/integration/test_sweep_integration.py`: use existing fixture audio file; mock Vamp plugin calls to return deterministic outputs; mock `StemSet` with two stems; run 2 stems × 2 param values = 4-permutation sweep end-to-end (config → `SweepRunner.run()` → `SweepReport`); assert 4 results, each with a `stem` field, all ranked, all with quality scores ≥ 0.0; assert `stems_tested` in report matches config; assert JSON round-trip produces identical report

**Checkpoint**: US1 independently testable. `sweep` command functional. Sweep report JSON written and ranked correctly.

---

## Phase 5: User Story 3 — Apply the Winning Parameter Set (Priority: P3)

**Goal**: Save a named permutation result from a sweep report as a reusable config
at `~/.xlight/sweep_configs/<name>.json`.

**Independent Test**: Run `xlight-analyze sweep-save report.json --name tight-onsets`.
Confirm `~/.xlight/sweep_configs/tight-onsets.json` exists with correct algorithm,
parameters, and source path. Re-run `sweep-save` on same name and confirm it overwrites.
Use `--rank 2` and confirm the second-ranked permutation's parameters are saved.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (T026)**

- [x] T025 [US3] Write failing unit tests for `SavedConfig` in `tests/unit/test_sweep_save.py`: test `save()` writes correct JSON to a tmp path; test `load()` round-trips all fields; test saving rank 2 from a mock `SweepReport` captures the second-ranked permutation's parameters; test overwrite of existing config

### Implementation for User Story 3

- [x] T026 [US3] Implement `SavedConfig` dataclass in `src/analyzer/sweep.py` with fields `name`, `algorithm`, `stem`, `parameters`, `source_sweep`, `created_at`; implement `save(config_dir)` writing to `<config_dir>/<name>.json`; implement `@classmethod load(name, config_dir)` reading from `<config_dir>/<name>.json`; use `~/.xlight/sweep_configs/` as default dir; create directory if absent
- [x] T027 [US3] Add `sweep-save` CLI command to `src/cli.py`: accepts `report_json` argument, `--name TEXT` (required), `--rank N` (default 1); reads `SweepReport` from file; validates rank is within bounds; constructs `SavedConfig` from the ranked result; calls `SavedConfig.save()`; prints confirmation with algorithm, parameters, score, and output path per contracts/cli-commands.md; handles exit codes per contract

**Checkpoint**: US3 independently testable. Named configs persisted to `~/.xlight/sweep_configs/`. All three user stories functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge case hardening and final validation.

- [x] T028 Add degenerate-sweep handling in `src/analyzer/sweep.py`: if all permutations return zero marks (quality_score = 0.0), include them in the report with a warning printed to stderr; do not fail silently
- [x] T029 Add plugin-exception safety in `SweepRunner.run()` in `src/analyzer/sweep.py`: if a single permutation's `algo.run()` raises or returns `None`, record it as a failed result (quality_score = 0.0, mark_count = 0) and continue; log warning to stderr with the failed parameter set
- [ ] T030 Run quickstart.md end-to-end validation: follow every step in `specs/005-vamp-parameter-tuning/quickstart.md` against a real audio file; confirm all commands work as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundation)**: Depends on Phase 1 — **BLOCKS all user stories**
- **Phase 3 (US2)**: Depends on Phase 2 — can start once foundation complete
- **Phase 4 (US1)**: Depends on Phase 2 + Phase 3 (needs `VampParamDiscovery.validate_params()`)
- **Phase 5 (US3)**: Depends on Phase 4 (`SweepReport` must exist to save from)
- **Phase 6 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US2 (P2)**: Can start after Foundation — no dependency on US1 or US3
- **US1 (P1)**: Depends on Foundation + US2 (for validation) — no dependency on US3
- **US3 (P3)**: Depends on US1 (needs `SweepReport` dataclass)

### Within Each Phase

- Tests MUST be written and confirmed failing before implementation tasks in same phase
- `ParameterDescriptor` before `list_params()` before `validate_params()`
- `SweepConfig` + `PermutationResult` + `SweepReport` before `SweepRunner`
- CLI commands after their supporting classes are implemented

### Parallel Opportunities

- T004–T008: All algorithm refactor tasks — different files, fully parallel
- T010 (US2 tests) and T017–T018 (US1 tests): Can be written in parallel after Foundation
- T015 (`params` command) and T016 (`sweep-suggest` command): Different CLI commands, parallel
- T020 (`PermutationResult`) and T019 (`SweepConfig`): Different dataclasses, parallel within same file

---

## Parallel Example: Phase 2 Algorithm Refactor

```bash
# All five refactor tasks can run simultaneously (different files):
Task T004: Refactor vamp_onsets.py
Task T005: Refactor vamp_beats.py
Task T006: Refactor vamp_structure.py
Task T007: Refactor vamp_pitch.py
Task T008: Refactor vamp_harmony.py
```

## Parallel Example: User Story 2 CLI Commands

```bash
# After T014 (validate_params) is complete:
Task T015: Add `params` command to cli.py
Task T016: Add `sweep-suggest` command to cli.py
```

---

## Implementation Strategy

### MVP First (User Story 1 — Sweep)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundation — algorithm refactor (T003–T009)
3. Complete Phase 3: US2 discovery (T010–T016) — needed for US1 validation
4. Complete Phase 4: US1 sweep (T017–T024)
5. **STOP and VALIDATE**: Run a real sweep against a test MP3, check ranked output
6. Demo working sweep before adding US3

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 → `params` and `sweep-suggest` commands usable independently
3. Phase 4 → Core sweep feature complete (MVP)
4. Phase 5 → Config persistence added
5. Phase 6 → Production-hardened

---

## Notes

- [P] tasks = different files or independent sections, no incomplete dependencies
- [Story] label maps task to user story for traceability
- TDD: all test tasks (T010, T017, T018, T025) must produce failing tests before corresponding implementation tasks run
- Quality score is a coarse filter — see research.md for framing; the sweep report includes full track data so any permutation can be reviewed in the existing review UI
- `parameters` dict on Algorithm subclasses after the Phase 2 refactor contains ONLY actual plugin parameters, never the `output` stream selector
- Saved configs land in `~/.xlight/sweep_configs/` (same parent as `~/.xlight/library.json`)
