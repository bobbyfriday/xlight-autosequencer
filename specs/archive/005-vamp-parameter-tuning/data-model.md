# Data Model: Vamp Plugin Parameter Tuning

**Branch**: `005-vamp-parameter-tuning`
**Date**: 2026-03-22

---

## New Entities

### ParameterDescriptor

Metadata about a single tunable plugin parameter, sourced at runtime from the Vamp
host's `get_parameter_descriptors()`.

| Field | Type | Description |
|-------|------|-------------|
| `identifier` | str | Key used in `parameters={}` when calling the plugin |
| `name` | str | Human-readable display name |
| `description` | str | Longer description of what the parameter controls |
| `unit` | str | Units string (e.g., "Hz", "ms", "" for dimensionless) |
| `min_value` | float | Minimum valid value |
| `max_value` | float | Maximum valid value |
| `default_value` | float | Plugin's built-in default |
| `is_quantized` | bool | True if value must align to `quantize_step` |
| `quantize_step` | float | Step size when quantized (1.0 for integer params) |
| `value_names` | list[str] | Enum labels (non-empty for discrete params) |

**Validation rules**:
- Numeric override must satisfy `min_value ≤ value ≤ max_value`
- Quantized param: `(value - min_value) % quantize_step == 0`
- Enum param: `value` must correspond to a valid index in `value_names`

---

### SweepConfig

Defines which parameter values and which stems to try for a single algorithm. Read
from a JSON file.

| Field | Type | Description |
|-------|------|-------------|
| `algorithm` | str | Algorithm name (e.g., `"qm_onsets_complex"`) |
| `stems` | list[str] | Stems to try (e.g., `["full_mix", "drums"]`). Omit or set to `[]` to use the algorithm's `preferred_stem` only. |
| `sweep` | dict[str, list] | Parameter name → ordered list of candidate values |
| `fixed` | dict[str, value] | Parameters held constant (merged with sweep params) |

**Valid stem names**: `"full_mix"`, `"drums"`, `"bass"`, `"vocals"`, `"guitar"`,
`"piano"`, `"other"` (matches `StemSet` field names from `src/analyzer/stems.py`).

**Constraints**:
- `algorithm` must match a known algorithm name in the pipeline
- Each key in `sweep` must be a valid parameter identifier for the algorithm's plugin
- Each value in `sweep[key]` must satisfy the parameter's validation rules
- `fixed` keys must also be valid parameter identifiers
- No key may appear in both `sweep` and `fixed`
- Stem names must be from the valid set above
- Total permutation count = `max(len(stems), 1)` × product of `len(v)` for all `v` in `sweep.values()`

---

### PermutationResult

The outcome of a single sweep run — one specific combination of parameter values
and stem.

| Field | Type | Description |
|-------|------|-------------|
| `rank` | int | 1-based position in the quality-score-ranked report |
| `stem` | str | Stem used for this permutation (e.g., `"drums"`, `"full_mix"`) |
| `parameters` | dict[str, value] | The exact parameter values used (sweep + fixed) |
| `quality_score` | float | Score from the existing scorer (0.0–1.0) |
| `mark_count` | int | Number of timing marks produced |
| `avg_interval_ms` | int | Average interval between marks in milliseconds |
| `track` | TimingTrack | Full timing track (marks included in report JSON) |

---

### SweepReport

The complete output of a sweep run, written to disk as JSON.

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | str | Always `"1.0"` |
| `audio_file` | str | Absolute path of the analyzed audio file |
| `algorithm` | str | Algorithm name swept |
| `plugin_key` | str | Vamp plugin key |
| `stems_tested` | list[str] | Stems that were included in the sweep |
| `sweep_params` | dict[str, list] | The candidate parameter values that were tested |
| `fixed_params` | dict | Parameters held constant across all permutations |
| `permutation_count` | int | Total number of runs executed |
| `generated_at` | str | ISO-8601 timestamp |
| `results` | list[PermutationResult] | All results, sorted by quality_score descending |

---

### SavedConfig

A named parameter set + stem persisted to `~/.xlight/sweep_configs/<name>.json`.

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | User-assigned identifier (filename stem) |
| `algorithm` | str | Algorithm name |
| `stem` | str | Stem to use (e.g., `"drums"`, `"full_mix"`) |
| `parameters` | dict[str, value] | Complete parameter set to use |
| `source_sweep` | str \| null | Path to the SweepReport this was derived from |
| `created_at` | str | ISO-8601 timestamp |

---

## Modified Entities

### Algorithm (base class — `src/analyzer/algorithms/base.py`)

No schema change. The `parameters` class attribute already exists. The key behavioral
change is that Vamp `_run()` implementations must pass `self.parameters` (minus the
`output` key) to `vamp.collect()` rather than hardcoding the dict.

A new `vamp_output` class attribute is added to Vamp algorithm subclasses to hold the
output stream name, separating it cleanly from plugin parameters.

| Existing Field | Change |
|----------------|--------|
| `parameters: dict` | No schema change; semantics tightened: must only contain actual plugin parameters, not the Vamp output selector |
| `plugin_key: str \| None` | No change |
| *(new)* `vamp_output: str \| None` | Holds the `output=` kwarg value for `vamp.collect()` calls |

---

## JSON File Layout

```
~/.xlight/
└── sweep_configs/
    ├── tight-onsets.json    # SavedConfig
    └── slow-beats.json      # SavedConfig

<audio_dir>/
└── song_sweep_qm_onsets_complex.json    # SweepReport
```

Sweep reports are written adjacent to the audio file, following the same convention as
`_analysis.json` files.
