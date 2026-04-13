# CLI Contract: Vamp Parameter Tuning Commands

**Branch**: `005-vamp-parameter-tuning`
**Date**: 2026-03-22

These commands are added to the existing `xlight-analyze` CLI group in `src/cli.py`.

---

## `xlight-analyze params <plugin_key>`

List all tunable parameters for an installed Vamp plugin.

### Arguments

| Name | Required | Description |
|------|----------|-------------|
| `plugin_key` | Yes | Vamp plugin key, e.g. `qm-vamp-plugins:qm-onsetdetector` |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--suggest-steps N` | — | For each numeric param, also print N evenly-spaced candidate values across the valid range |

### Output (stdout)

```
Plugin: qm-vamp-plugins:qm-onsetdetector

  PARAM         TYPE     RANGE          DEFAULT   DESCRIPTION
  dftype        enum     0–3            3         Detection function type
                         0=HFC 1=Spectral 2=Phase 3=Complex
  sensitivity   float    0.0–100.0      50.0      Onset sensitivity
  whiten        bool     0–1            0         Adaptive whitening

Use these keys in your sweep config's "sweep" or "fixed" sections.
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Plugin not found or vamp package unavailable |

---

## `xlight-analyze sweep-suggest <plugin_key> <param_name> [--steps N]`

Print N evenly-spaced candidate values for a numeric parameter across its valid range.

### Arguments

| Name | Required | Description |
|------|----------|-------------|
| `plugin_key` | Yes | Vamp plugin key |
| `param_name` | Yes | Parameter identifier (from `params` command) |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--steps N` | `5` | How many evenly-spaced values to generate |

### Output (stdout)

```
Suggested values for 'sensitivity' (range 0.0–100.0, default 50.0):
  [0.0, 25.0, 50.0, 75.0, 100.0]

Add to your sweep config:
  "sensitivity": [0.0, 25.0, 50.0, 75.0, 100.0]
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Plugin or parameter not found |
| 2 | Parameter is not numeric (enum/bool — list all values with `params`) |

---

## `xlight-analyze sweep <audio_file> --config <sweep.json>`

Run a parameter sweep for one algorithm against an audio file.

### Arguments

| Name | Required | Description |
|------|----------|-------------|
| `audio_file` | Yes | Path to the MP3 file to analyze |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--config PATH` | — | Path to sweep config JSON (required) |
| `--output PATH` | `<audio>_sweep_<algorithm>.json` | Where to write the SweepReport |
| `--yes` | False | Skip the permutation-count confirmation prompt |

### Behavior

1. Load and validate the sweep config JSON against the plugin's parameter schema.
2. If `stems` is specified (and non-empty), run stem separation once via `StemSeparator`
   (uses existing `StemCache` — fast on re-runs). If demucs is unavailable, warn and
   offer to proceed with `full_mix` only.
3. Compute permutation count = stems × parameter combinations. If > 20 and `--yes` not
   set, print:
   ```
   Sweep will run 18 permutations across 2 stems (~36–90 seconds).
   Proceed? [y/N]:
   ```
4. Load audio once, then run each permutation in sequence with progress:
   ```
   [01/18] stem=drums, sensitivity=0.2, dftype=3 ... done (112 marks, score: 0.68)
   [02/18] stem=drums, sensitivity=0.3, dftype=3 ... done ( 98 marks, score: 0.71)
   ...
   [10/18] stem=full_mix, sensitivity=0.2, dftype=3 ... done (145 marks, score: 0.52)
   ...
   ```
5. Write the SweepReport JSON.
6. Print ranked summary:
   ```
   Sweep complete: 18 permutations (2 stems × 9 param combos)

   RANK  SCORE   MARKS   AVG INTERVAL   STEM       PARAMETERS
      1  0.74      98        510 ms     drums      sensitivity=0.3, dftype=3
      2  0.71     112        445 ms     drums      sensitivity=0.5, dftype=3
      3  0.68     134        378 ms     full_mix   sensitivity=0.3, dftype=3
   ...

   Report: /path/to/song_sweep_qm_onsets_complex.json
   Use 'sweep-save' to persist the winning config (stem + parameters).
   ```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Audio file or config not readable |
| 2 | Config validation failure (lists invalid params) |
| 3 | Output not writable |
| 130 | User cancelled at confirmation prompt |

---

## `xlight-analyze sweep-save <report_json> --name <config_name>`

Save a permutation result from a sweep report as a named reusable config.

### Arguments

| Name | Required | Description |
|------|----------|-------------|
| `report_json` | Yes | Path to a SweepReport JSON from the `sweep` command |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--name TEXT` | — | Name for the saved config (required; used as filename) |
| `--rank N` | `1` | Which ranked result to save (1 = best) |

### Output (stdout)

```
Saved config 'tight-onsets':
  Algorithm : qm_onsets_complex
  Parameters: dftype=3, sensitivity=0.3
  Score     : 0.74 (rank 1 of 45)
  Saved to  : ~/.xlight/sweep_configs/tight-onsets.json
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Report not readable or rank out of range |
| 3 | Cannot write to `~/.xlight/sweep_configs/` |

---

## Sweep Config JSON Schema

```json
{
  "algorithm": "<algorithm_name>",
  "stems": ["<stem_name>", ...],
  "sweep": {
    "<param_identifier>": [<value1>, <value2>, ...]
  },
  "fixed": {
    "<param_identifier>": <value>
  }
}
```

**`stems`** is optional. Valid values: `"full_mix"`, `"drums"`, `"bass"`, `"vocals"`,
`"guitar"`, `"piano"`, `"other"`. If omitted or empty, the algorithm's `preferred_stem`
is used and no stem dimension is added to the sweep.

**Example — sweep params and stems together**:

```json
{
  "algorithm": "qm_onsets_complex",
  "stems": ["full_mix", "drums"],
  "sweep": {
    "sensitivity": [20, 50, 80],
    "whiten": [0, 1]
  },
  "fixed": {
    "dftype": 3
  }
}
```

This config produces 2 stems × 3 sensitivity × 2 whiten = **12 permutations**, all
with `dftype` fixed at 3.

**Example — params only (no stem sweep)**:

```json
{
  "algorithm": "qm_onsets_complex",
  "sweep": {
    "sensitivity": [20, 40, 50, 60, 80]
  },
  "fixed": {
    "dftype": 3
  }
}
```

This config produces 5 permutations, all run against the algorithm's default
`preferred_stem`.

**Constraints**:
- `algorithm` must be a known algorithm name
- All stem names must be from the valid set above
- All parameter keys must be valid identifiers for that algorithm's plugin
- All values must pass parameter range/type validation
- A key must not appear in both `sweep` and `fixed`
