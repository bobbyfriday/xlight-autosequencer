# Research: Vamp Plugin Parameter Tuning

**Phase**: 0 — Research
**Branch**: `005-vamp-parameter-tuning`
**Date**: 2026-03-22

---

## Decision: vamp Python host parameter API

**Decision**: Use `vamp.vampyhost.load_plugin(plugin_key, sample_rate)` to obtain a
plugin object, then call `plugin.get_parameter_descriptors()` to enumerate all tunable
parameters at runtime.

**Rationale**: The vamp Python host (vampyhost) exposes full plugin metadata without
requiring the plugin to be run. Each `ParameterDescriptor` object carries:
- `identifier` — the key used in `parameters={}` kwarg to `vamp.collect()`
- `name` — human-readable name
- `description` — longer description
- `unit` — units string (e.g., "Hz", "ms", or "")
- `min_value`, `max_value` — float bounds
- `default_value` — float default
- `is_quantized` — whether the value must be an integer step
- `quantize_step` — step size when `is_quantized` is True
- `value_names` — list of string labels for enum-style parameters

**Alternatives considered**:
- Static parameter registry (hardcoded per-plugin) — rejected: would drift from actual
  plugin versions; runtime discovery is authoritative.
- Parsing Vamp plugin RDF metadata files — rejected: overkill, vampyhost already exposes
  this.

**Verification needed**: Confirm `vamp.vampyhost` is importable from the existing vamp
Python package used in this project. The module is part of the `vamp` PyPI package.

---

## Decision: Parameter passing in vamp.collect()

**Decision**: `vamp.collect(data, rate, plugin_key, output=output_name, parameters=dict)`
already accepts a `parameters` dict. This dict is passed directly to the plugin before
processing. The sweep runner will pass each permutation's parameter dict here.

**Rationale**: Already in use in `vamp_onsets.py` (e.g., `parameters={"dftype": 3}`).
No changes to the vamp library are required.

**Key distinction**: The `output=` kwarg is NOT a plugin parameter — it selects which
output stream to collect (beats, onsets, etc.). The `parameters=` kwarg controls the
plugin's internal settings. These must be kept separate.

---

## Decision: Algorithm refactor to use self.parameters

**Decision**: Refactor all Vamp `_run()` methods so the `parameters=` kwarg to
`vamp.collect()` reads from `self.parameters` rather than hardcoded dicts. The `output`
selector remains a separate `vamp_output` class attribute.

**Rationale**: Without this refactor, the sweep runner cannot vary parameters by
simply instantiating an algorithm with a different `parameters` dict. The refactor is
minimal (3 files changed, each change is a one-liner).

**Scope of change**:
- `vamp_onsets.py` — 3 algorithms, each hardcodes `parameters={"dftype": N}` → use `self.parameters`
- `vamp_beats.py`, `vamp_structure.py`, `vamp_pitch.py`, `vamp_harmony.py` — clean up
  `parameters` class attribute (remove "output" key which belongs in `vamp_output`)
- No behavior change for existing defaults; all existing tests must still pass

---

## Decision: Quality score as coarse filter, not ground truth

**Decision**: Quality score ranks sweep permutations as a starting point. The review UI
is the authoritative validation step before committing to a parameter set.

**Rationale**: The existing scorer measures density (250–1000 ms sweet spot) and
regularity (coefficient of variation). Optimizing purely for this score can reward
smoothed-but-inaccurate outputs that hit the density range with regular intervals
even if they don't align with actual audio events. The score is useful for:
- Eliminating clearly bad permutations (too dense < 100ms, zero marks, pure noise)
- Providing an initial ranking when exploring a large sweep

It should NOT be used as the only signal. After seeing the ranked list, users should
load the top 2-3 candidates in the review UI and listen.

**Implementation note**: The sweep report output JSON includes full TimingTrack data
for every permutation, so any permutation can be loaded into the review UI directly.
The `sweep-save` command should accept `--rank N` to save any ranked result, not
just rank 1.

---

## Decision: Permutations are per-algorithm, not cross-algorithm

**Decision**: A single sweep config targets one algorithm. To sweep multiple algorithms,
run the sweep command multiple times with different configs.

**Rationale**: Cross-algorithm combinations multiply the search space exponentially and
are hard to evaluate (different algorithms produce different track types). Per-algorithm
sweep keeps the space manageable and results directly comparable.

---

## Decision: Sweep config format — JSON file

**Decision**: Use a JSON file for sweep config:
```json
{
  "algorithm": "qm_onsets_complex",
  "sweep": {
    "sensitivity": [0.2, 0.3, 0.5, 0.7, 0.9]
  },
  "fixed": {
    "dftype": 3
  }
}
```

**Rationale**: Consistent with the project's existing JSON-everywhere convention.
Simple to author manually or generate programmatically. `fixed` allows the user to hold
some parameters constant while varying others.

---

## Decision: Saved config storage location

**Decision**: Named configs saved to `~/.xlight/sweep_configs/<name>.json`.

**Rationale**: Consistent with `~/.xlight/library.json` from feature 010. User-level
storage means configs persist across projects and audio files.

**Format**:
```json
{
  "name": "tight-onsets",
  "algorithm": "qm_onsets_complex",
  "parameters": {"dftype": 3, "sensitivity": 0.5},
  "source_sweep": "/path/to/sweep_report.json",
  "created_at": "2026-03-22T12:00:00Z"
}
```

---

## Decision: Runtime permutation limit + estimate

**Decision**: Before running, compute permutation count (product of all candidate list
lengths). If > 20, print a warning with the estimated count and runtime (based on a
benchmark run-time per algorithm), then prompt for confirmation unless `--yes` flag
is passed.

**Rationale**: Preventing surprise 200-run sweeps on a 5-minute audio file. A QM onset
run typically takes 2–5 seconds on a 3-minute file, so 50 permutations = 100–250 seconds.

---

## Known Vamp plugin parameters (selected)

| Plugin | Parameter | Type | Range | Default |
|--------|-----------|------|-------|---------|
| qm-onsetdetector | `dftype` | enum | 0=HFC, 1=Spectral, 2=Phase, 3=Complex | 3 |
| qm-onsetdetector | `sensitivity` | float | 0–100 | 50 |
| qm-onsetdetector | `whiten` | bool | 0–1 | 0 |
| qm-tempotracker | `maxbpm` | float | 50–250 | 190 |
| qm-tempotracker | `minbpm` | float | 50–250 | 50 |
| qm-barbeattracker | `maxbpm` | float | 50–250 | 250 |
| qm-barbeattracker | `minbpm` | float | 10–220 | 10 |
| beatroot-vamp:beatroot | (none known) | — | — | — |

**Note**: These are from QM Vamp Plugins documentation. Runtime discovery via
`get_parameter_descriptors()` is the authoritative source — the above is for planning
purposes only.
