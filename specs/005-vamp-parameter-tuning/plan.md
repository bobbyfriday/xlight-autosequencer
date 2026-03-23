# Implementation Plan: Vamp Plugin Parameter Tuning

**Branch**: `005-vamp-parameter-tuning` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-vamp-parameter-tuning/spec.md`

---

## Summary

Add a parameter sweep capability to `xlight-analyze`: given a sweep config (JSON file
listing candidate values for one or more parameters), automatically run every permutation
of a target Vamp algorithm, score each result with the existing quality scorer, and
produce a ranked report. Three supporting CLI commands (`params`, `sweep-suggest`,
`sweep-save`) provide parameter discovery, candidate generation, and config persistence.
A small prerequisite refactor makes Vamp algorithm `_run()` methods use `self.parameters`
so the sweep runner can vary parameters without subclassing.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: vamp, numpy, click 8+ (all existing — no new deps)
**Storage**: JSON files (local filesystem); new `~/.xlight/sweep_configs/` directory
**Testing**: pytest
**Target Platform**: macOS local CLI (offline)
**Project Type**: CLI tool
**Performance Goals**: Sweep of ≤ 50 permutations completes without special optimisation;
audio loaded once and reused across all permutations
**Constraints**: No new pip dependencies; offline; permutation count warned before
execution if > 20
**Scale/Scope**: Single audio file per sweep run; single algorithm per sweep config

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | PASS | Sweep is fully audio-driven; parameters control analysis, not timing |
| II. xLights Compatibility | N/A | This feature produces no sequence output |
| III. Modular Pipeline | PASS | `SweepRunner` is a new composable stage; does not modify existing runner |
| IV. Test-First Development | PASS | Tests written before implementation per all tasks |
| V. Simplicity First | PASS | No new dependencies; sweep runner is a thin wrapper over existing `Algorithm.run()`; no ML/optimization |

**Complexity Tracking**: No violations. No entry required.

---

## Project Structure

### Documentation (this feature)

```text
specs/005-vamp-parameter-tuning/
├── plan.md              # This file
├── research.md          # Phase 0 — vamp API, quality score framing, design decisions
├── data-model.md        # Phase 1 — entities and schema
├── quickstart.md        # Phase 1 — usage guide
├── contracts/
│   └── cli-commands.md  # Phase 1 — CLI command contracts + JSON schemas
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
src/
├── analyzer/
│   ├── algorithms/
│   │   ├── base.py               # Add vamp_output class attribute
│   │   ├── vamp_beats.py         # Refactor: use self.parameters + self.vamp_output
│   │   ├── vamp_onsets.py        # Refactor: use self.parameters + self.vamp_output
│   │   ├── vamp_structure.py     # Refactor: clean up parameters attr
│   │   ├── vamp_pitch.py         # Refactor: clean up parameters attr
│   │   └── vamp_harmony.py       # Refactor: clean up parameters attr
│   ├── sweep.py                  # NEW: SweepRunner, SweepConfig, PermutationResult, SweepReport
│   └── vamp_params.py            # NEW: VampParamDiscovery (wraps vampyhost)
├── cli.py                        # Add: params, sweep-suggest, sweep, sweep-save commands

tests/
├── unit/
│   ├── test_vamp_params.py       # NEW: parameter discovery unit tests (with mock)
│   └── test_sweep.py             # NEW: SweepRunner unit tests (with mock vamp)
└── integration/
    └── test_sweep_integration.py # NEW: end-to-end sweep on fixture audio
```

**Structure Decision**: Single-project layout (Option 1). All new code fits within the
existing `src/analyzer/` module and `src/cli.py` extension pattern.

---

## Implementation Phases

### Phase A — Prerequisite: Algorithm Refactor

**Goal**: Make Vamp algorithm `_run()` methods use `self.parameters` so the sweep runner
can control parameters without subclassing.

**Changes**:

1. `base.py`: Add `vamp_output: str | None = None` class attribute.

2. `vamp_onsets.py` — three algorithms:
   - Add `vamp_output = "onsets"` class attribute to each
   - Remove "output" key from `parameters` dict
   - Change `vamp.collect(..., parameters={"dftype": N})` →
     `vamp.collect(..., output=self.vamp_output, parameters=self.parameters)`

3. `vamp_beats.py` — three algorithms:
   - Add `vamp_output = "beats"` (or `"bars"`) class attribute
   - Remove "output" key from `parameters` dict
   - Change `vamp.collect(..., output="beats")` → `vamp.collect(..., output=self.vamp_output, parameters=self.parameters)`

4. `vamp_structure.py`, `vamp_pitch.py`, `vamp_harmony.py`:
   - Add appropriate `vamp_output` class attributes
   - Clean `parameters` dicts (remove "output" keys)
   - Update `vamp.collect()` calls accordingly

**Validation**: All existing tests pass. Existing analysis behavior is identical.

---

### Phase B — Parameter Discovery

**Goal**: New `VampParamDiscovery` class that wraps the vamp Python host to expose
parameter metadata for any installed plugin.

**New file**: `src/analyzer/vamp_params.py`

```
VampParamDiscovery
  .list_params(plugin_key: str, sample_rate: int = 44100) -> list[ParameterDescriptor]
  .suggest_values(descriptor: ParameterDescriptor, steps: int) -> list[float]
  .validate_params(plugin_key: str, params: dict, sample_rate: int = 44100) -> list[str]
      # returns list of error messages; empty = valid
```

`ParameterDescriptor` dataclass: see data-model.md for full field list.

**CLI command**: `xlight-analyze params <plugin_key> [--suggest-steps N]`
**CLI command**: `xlight-analyze sweep-suggest <plugin_key> <param_name> [--steps N]`

---

### Phase C — Sweep Runner

**Goal**: `SweepRunner` class that generates all permutations, runs each, and returns
a ranked `SweepReport`.

**New file**: `src/analyzer/sweep.py`

```
SweepConfig (dataclass)
  algorithm: str
  sweep_params: dict[str, list]
  fixed_params: dict

  @classmethod from_file(path) -> SweepConfig
  .validate(discovery: VampParamDiscovery) -> list[str]  # empty = valid
  .permutations() -> Iterator[dict]  # yields one param dict per permutation
  .permutation_count() -> int

PermutationResult (dataclass)
  rank: int
  parameters: dict
  quality_score: float
  mark_count: int
  avg_interval_ms: int
  track: TimingTrack

SweepReport (dataclass)
  schema_version: str
  audio_file: str
  algorithm: str
  plugin_key: str
  sweep_params: dict
  fixed_params: dict
  permutation_count: int
  generated_at: str
  results: list[PermutationResult]    # sorted by quality_score desc

  .to_dict() -> dict
  @classmethod from_dict(d: dict) -> SweepReport
  .write(path: str) -> None
  @classmethod read(path: str) -> SweepReport

SweepRunner
  __init__(algorithm_registry: dict[str, type[Algorithm]])
  .run(audio_path: str, config: SweepConfig,
       progress_callback=None) -> SweepReport
```

**Key behavior**:
- Loads audio once via existing `load()` function
- For each permutation: instantiates the algorithm class with overridden `parameters`,
  calls `algo.run(audio, sr)`, scores with `score_track()`
- Collects all `PermutationResult` objects, sorts by `quality_score` descending,
  assigns `rank` (1 = best)
- Returns `SweepReport`; caller writes to disk

**Algorithm registry**: A dict mapping algorithm name → algorithm class, built from
the existing `default_algorithms()` pool. Only Vamp algorithms are exposed in v1.

---

### Phase D — CLI Commands

**Goal**: Wire up the four new CLI commands in `src/cli.py`.

Commands and their full contracts are in `contracts/cli-commands.md`.

**Summary**:

| Command | Phase | Description |
|---------|-------|-------------|
| `params` | B | List plugin parameters with types, ranges, defaults |
| `sweep-suggest` | B | Print N evenly-spaced candidate values for a numeric param |
| `sweep` | C | Run a full parameter sweep; write SweepReport JSON |
| `sweep-save` | C | Save a ranked permutation from a SweepReport as a named config |

**`sweep-save` storage**: `~/.xlight/sweep_configs/<name>.json`
Format: `SavedConfig` — see data-model.md.

---

### Phase E — Tests

**Goal**: Full test coverage for new code, written before implementation.

**Unit tests**:

- `tests/unit/test_vamp_params.py`
  - Mock `vamp.vampyhost.load_plugin()` to return a fake plugin with known descriptors
  - Test `list_params()`, `suggest_values()`, `validate_params()` with valid and invalid inputs
  - Test that missing plugin returns appropriate error (not empty list)

- `tests/unit/test_sweep.py`
  - `SweepConfig.from_file()` — valid JSON, missing algorithm, duplicate key in sweep+fixed
  - `SweepConfig.validate()` — invalid param name, out-of-range value, non-quantized step
  - `SweepConfig.permutations()` — correct cartesian product count and values
  - `SweepRunner.run()` — mock `Algorithm.run()` to return deterministic tracks; verify
    report is ranked correctly, worst permutation at bottom
  - `SweepReport.to_dict()` / `from_dict()` — round-trip serialization

**Integration tests**:

- `tests/integration/test_sweep_integration.py`
  - Use the existing short royalty-free fixture audio file
  - Run a 2-parameter × 2-value = 4-permutation sweep against a mock Vamp algorithm
    (since actual Vamp plugins are not guaranteed in CI)
  - Verify: report has 4 results, all ranked, all have quality scores, JSON round-trips

**Refactor regression tests**:

- Verify existing unit tests for all refactored Vamp algorithm files still pass after
  Phase A changes (no behavior change expected)

---

## Key Design Decisions (from research.md)

1. **Blind sweep only** — user provides explicit candidate values; no automated search
2. **Quality score as filter, not verdict** — sweep report includes full track data so
   finalists can be validated in the review UI
3. **Per-algorithm sweeps** — one algorithm per sweep config; no cross-algorithm combos
4. **No new pip dependencies** — uses existing vamp, numpy, click
5. **Audio loaded once** — performance: single audio load for all N permutations
6. **Confirmation gate** — sweeps with > 20 permutations require explicit confirmation
   (or `--yes`) to prevent surprise long runs

---

## Out of Scope (this feature)

- Loading a SavedConfig automatically via `analyze --param-config <name>` (follow-on)
- Librosa or madmom parameter sweeps
- Graphical UI for sweep config or results
- Automated optimization (Bayesian, genetic, etc.)
