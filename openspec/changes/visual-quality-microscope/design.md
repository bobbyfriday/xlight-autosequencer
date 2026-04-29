## Context

### The flailing pattern
The project's generator pipeline is feature-complete: value curves (`src/generator/value_curves.py`, 358 lines), section transitions (`src/generator/transitions.py`, 301 lines), and chord color blending (`src/generator/chord_colors.py`, 463 lines) are all wired in. None of these are disabled stubs — they run on every generation. Yet the user describes output as "dim, lifeless, wrong effects on wrong props, boring, repetitive." The disconnect is not missing code; it's missing measurement. The features fire, but nobody can tell whether they're making the show look meaningfully different.

The existing evaluation harness (`src/evaluation/`) measures regression: does the new code produce the same placements as the old code? It does not measure quality: does this show look better than last month's? The `tests/golden/baseline.json` is a structural snapshot, not a quality score.

### The three complaints, made measurable
1. **Dim / lifeless**: the show doesn't breathe with the music. Proxy: mean palette luminance across all placements (proxy for "how bright"), and the coefficient of variation of per-placement luminance (proxy for "how much it varies" — a flat value means the energy curve isn't driving brightness). Computed from `Placement.palette_colors` in the parsed `SequenceSummary`.

2. **Boring / repetitive**: same effect on same prop within 30 seconds; only 3–4 distinct effects appear in the whole show; certain prop types get only 1 effect. Metrics: `distinct_effect_count`, `effect_repeat_rate`, `per_prop_type_diversity`.

3. **Wrong effects on wrong props**: Plasma on a Single Line roofline, Bars on a radial spinner, Single Strand on a Matrix. Metric: `bad_pairing_pct` against an explicit `OBVIOUSLY_BAD_PAIRINGS` dict (6–8 known-bad combinations that are unambiguously wrong regardless of song or mood).

### Building on what exists
`src/evaluation/xsq_reader.py` already parses an XSQ file into a `SequenceSummary` containing `Placement` objects with `effect_type`, `model_name`, `palette_colors`, `start_ms`, `end_ms`, and `layer_index`. The `model_name` token-matching already infers `inferred_prop_types` from model names. The metric registry (`src/evaluation/metrics/__init__.py`) already has `register()` + `get_registry()`. New metric modules plug in exactly as the existing `effects.py`, `pacing.py`, `palette.py`, `alignment.py`, `sections.py`, `internal.py` modules do.

The microscope runner does not need to be a new pipeline — it calls `generate_sequence()` from `src/generator/plan.py` (the same function the CLI's `generate` command calls), then parses the output XSQ with `xsq_reader.py`, then computes metrics.

## Goals / Non-Goals

**Goals:**
- Emit a per-song `metrics.json` with all 6 new metrics plus existing registered metrics.
- Run across a 5-song panel in one command so no single song is treated as the truth.
- Compare current metrics against a committed golden so every run is a diff, not a blind report.
- Be fast enough that a developer runs it between commits (~3–5 min per song; ~20 min full panel).
- Be deterministic: same code + same song → identical metrics.

**Non-goals:**
- FSEQ rendering or MP4 output (metrics from XSQ only).
- Fixing the quality problems the metrics surface (Phase B).
- Replacing `xlight-evaluate gate` (the microscope is a companion tool, not a replacement).
- Running in CI (local developer tool only for this change; CI integration is a future decision).
- Adding more than 6 new metrics (2 vitality + 3 variety + 1 fit; expand after Phase B).

## Design

### New metric modules

#### `src/evaluation/metrics/vitality.py`

Two metrics registered under the existing metric registry:

**`brightness_proxy_mean`** (scalar)
- For each `Placement`, parse its `palette_colors` (already tuples of `#RRGGBB` strings from `xsq_reader.py`).
- Compute luminance per color: `L = 0.299*R + 0.587*G + 0.114*B` (Rec.601 luma, range 0–255).
- Per placement: mean luminance of active colors.
- Across all placements: duration-weighted mean (longer placements count more).
- Returns a scalar 0–255. A typical show with bright saturated effects should score 80–140. A dim show scores below 60.
- `pro_comparable=False` (no pro reference available); `gated=True` (compare against our own baseline).

**`brightness_proxy_cv`** (scalar)
- Same per-placement luminance as above.
- Return the coefficient of variation (std-dev / mean) across all per-placement means, unweighted.
- High CV (~0.4+) means brightness varies significantly across the show — "breathing" is happening.
- Low CV (~0.1) means the show is flat — effects are all similar brightness regardless of song energy.
- `gated=True`, `pro_comparable=False`.

#### `src/evaluation/metrics/suitability.py`

Four metrics. Three variety + one fit.

**`distinct_effect_count`** (scalar)
- Count unique `effect_type` values across all non-"Unknown" placements.
- Returns an integer cast as float. A rich show uses 8+ distinct effects. A boring show uses 3–4.
- `gated=True`, `pro_comparable=True` (in principle a pro show has this too).

**`effect_repeat_rate`** (scalar)
- For each (model_name, effect_type) pair, check how many placements occur within 30 seconds of a previous placement of the same effect on the same model.
- Returns the fraction (0.0–1.0) of placements that are "repeats within window."
- High rate (>0.5) means the show cycles through a tiny rotation quickly. Low rate (<0.2) means good variety.
- Window size is a parameter defaulting to 30_000 ms.
- `gated=True`, `pro_comparable=False`.

**`per_prop_type_diversity`** (structured)
- Group placements by inferred prop type (from `SequenceSummary.inferred_prop_types`).
- For each prop type, count distinct `effect_type` values.
- Returns a structured payload: `{prop_type: distinct_effect_count, ...}` plus a scalar summary (min diversity across prop types).
- A prop type with 1–2 distinct effects is flagged; it means that prop class is being starved.
- `gated=True`, `pro_comparable=False`.

**`bad_pairing_pct`** (scalar)
- Define `OBVIOUSLY_BAD_PAIRINGS: dict[str, set[str]]` in `src/evaluation/metrics/suitability.py` (not in a separate module) — maps effect name to the set of prop types it is obviously wrong on:
  ```python
  OBVIOUSLY_BAD_PAIRINGS = {
      "Plasma":        {"outline", "arch"},   # 2D fluid on 1D string = invisible structure
      "Pinwheel":      {"outline", "arch"},   # radial spin on 1D string = meaningless
      "Single Strand": {"matrix"},            # 1D chase on 2D grid = wasted pixels
      "Bars":          {"radial"},            # directional sweep on radial = awkward
      "Fire":          {"arch", "outline"},   # vertical rise on horizontal props = wrong axis
      "Butterfly":     {"outline", "arch"},   # 2D mirror on 1D props = meaningless
  }
  ```
- For each placement: look up `inferred_prop_types[model_name]`, check if `effect_type` is in its bad set.
- Returns fraction of placements that match a bad pairing.
- If `inferred_prop_types` is missing for a model, skip that placement (don't penalize unknowns).
- `gated=True`, `pro_comparable=False`.

### New module: `src/microscope/`

#### `src/microscope/__init__.py`
Empty, marks module boundary.

#### `src/microscope/runner.py`

`run_song(audio_path, layout_path, output_dir, config_overrides) -> MicroscopeResult`

1. Build a `GenerationConfig` with `audio_path`, `layout_path`, `output_dir=tmp_dir`, and defaults for all other fields (genre="pop", occasion="general", transition_mode="subtle", curves_mode="none" — matching the current production defaults so the microscope measures what the user actually gets).
2. Apply `config_overrides` dict on top.
3. Call `generate_sequence(config)` from `src.generator.plan` — this runs analyze + generate + write_xsq, returning the output XSQ path.
4. Parse the XSQ with `xsq_reader.parse_xsq(xsq_path)` → `SequenceSummary`.
5. Import all metric modules (vitality + suitability + existing registered ones).
6. Compute all registered metrics via the registry dispatcher.
7. Return a `MicroscopeResult(slug, audio_path, xsq_path, summary, metrics)`.

`MicroscopeResult` is a dataclass with `to_dict()` → JSON-serializable dict.

The runner does NOT delete the generated XSQ — it's retained in `output_dir/microscope/<slug>/` for manual inspection.

#### `src/microscope/panel.py`

`run_panel(panel_manifest_path, layout_path, output_dir, config_overrides, parallel=False) -> list[MicroscopeResult]`

Loads a panel manifest JSON (`tests/fixtures/reference/panel_manifest.json`), resolves each song's MP3 path, and calls `run_song()` for each entry. If `parallel=True`, runs up to 3 songs concurrently via `concurrent.futures.ProcessPoolExecutor`. Returns list of `MicroscopeResult`s.

Panel manifest schema:
```json
{
  "schema_version": 1,
  "description": "Reference panel for microscope visual quality measurement",
  "cc0_manifest": "tests/fixtures/cc0_music/manifest.json",
  "slugs": ["funshine", "maple_leaf_rag", "nostalgic_piano", "space_ambience"],
  "layout": "tests/fixtures/reference/layout.xml"
}
```

Each slug must exist in the CC0 manifest. MP3 paths are resolved using `tests/validation/download_fixtures.py`'s download logic (reuse, don't duplicate).

#### `src/microscope/diff.py`

`diff_results(current: list[MicroscopeResult], baseline_dir: Path) -> DiffReport`

Loads per-song `baseline.json` files from `baseline_dir`. For each song × metric, computes absolute delta and relative delta. Returns a `DiffReport` with a `format_table()` method that prints:

```
Song            Metric                     Baseline   Current   Delta     %Change
funshine        brightness_proxy_mean      92.4       88.1      -4.3      -4.7%  ↓
funshine        distinct_effect_count      4.0        7.0       +3.0     +75.0%  ↑ ✓
maple_leaf_rag  bad_pairing_pct            0.18       0.09      -0.09    -50.0%  ↑ ✓
...
```

"↑ ✓" = improvement (higher is better for count/diversity metrics; lower is better for bad_pairing_pct / effect_repeat_rate). Direction-of-good is encoded per metric definition (add a `higher_is_better: bool` field to `MetricDefinition`).

### New CLI: `src/cli/microscope.py`

Subcommand group `microscope` registered on the main `xlight-analyze` CLI.

**`xlight-analyze microscope run <song.mp3>`**
- Options: `--layout <path>` (default: `tests/fixtures/reference/layout.xml`), `--output-dir <path>` (default: `./microscope-out/`), `--curves-mode <mode>` (default: none), `--baseline <dir>` (optional, enables diff output).
- Runs `run_song()`, prints metric table to stdout, writes `<output-dir>/<slug>/metrics.json`.
- If `--baseline` given, also prints diff table.

**`xlight-analyze microscope panel`**
- Options: `--manifest <path>` (default: `tests/fixtures/reference/panel_manifest.json`), `--layout <path>`, `--output-dir <path>`, `--parallel`, `--baseline <dir>`.
- Runs `run_panel()`, prints per-song metric tables + aggregate summary (mean across songs per metric).
- If `--baseline` given, also prints diff table.

**`xlight-analyze microscope baseline`**
- Options: `--input-dir <path>` (default: `./microscope-out/`), `--golden-dir <path>` (default: `tests/golden/microscope/`).
- Copies `metrics.json` files from `--input-dir` to `--golden-dir`, committing them as the new baseline.
- Prints: "Baseline updated for N songs. Run `git add tests/golden/microscope/ && git commit` to persist."

### Reference panel manifest

`tests/fixtures/reference/panel_manifest.json` — 4 CC0 songs from the existing corpus:
- `funshine` — pop-funk, 96 BPM, upbeat/mid-energy (tests variety in a typical upbeat song)
- `maple_leaf_rag` — ragtime, 99 BPM, busy rhythmic texture (tests beat-sync and effect rate)
- `nostalgic_piano` — piano, 59 BPM, slow/quiet (tests low-energy section handling)
- `space_ambience` — ambient, 140 BPM label (tests long-form low-density sections)

### Golden baseline

`tests/golden/microscope/<slug>/baseline.json` — committed after the first `microscope panel` run, before any quality fixes. Contains the raw metric values so every subsequent run is a diff. Structure:

```json
{
  "slug": "funshine",
  "generated_at": "2026-04-29T...",
  "config": {"curves_mode": "none", ...},
  "metrics": {
    "brightness_proxy_mean": {"value": 92.4, "kind": "scalar"},
    "brightness_proxy_cv": {"value": 0.13, "kind": "scalar"},
    "distinct_effect_count": {"value": 4.0, "kind": "scalar"},
    "effect_repeat_rate": {"value": 0.61, "kind": "scalar"},
    "bad_pairing_pct": {"value": 0.18, "kind": "scalar"},
    "placements_per_minute": {"value": 14.2, "kind": "scalar"},
    ...
  }
}
```

## Regression surface

**New files (no callers to update):**
- `src/evaluation/metrics/vitality.py`
- `src/evaluation/metrics/suitability.py`
- `src/microscope/__init__.py`
- `src/microscope/runner.py`
- `src/microscope/panel.py`
- `src/microscope/diff.py`
- `src/cli/microscope.py`
- `tests/fixtures/reference/panel_manifest.json`
- `tests/golden/microscope/<slug>/baseline.json` (×4)

**Modified files:**
- `src/cli/__init__.py` — add `from src.cli.microscope import microscope_group` + `cli.add_command(microscope_group, name="microscope")`. One-line addition; existing commands untouched.
- `src/evaluation/metrics/__init__.py` — add `higher_is_better: bool = True` field to `MetricDefinition`. Default `True` is correct for most metrics; set `False` on `bad_pairing_pct`, `effect_repeat_rate`, `unknown_effect_fraction`. Callers of `MetricDefinition(...)` that don't pass `higher_is_better` continue to use the default — no breakage.

**Callers of `MetricDefinition` (must remain compatible):**
- `src/evaluation/metrics/effects.py` — add `higher_is_better=False` (unknown fraction: lower is better)
- `src/evaluation/metrics/pacing.py` — default True OK for `placements_per_minute`; add `higher_is_better=True` explicitly for clarity
- `src/evaluation/metrics/palette.py` — default True OK
- `src/evaluation/metrics/alignment.py` — default True OK (`beat_alignment_pct`)
- `src/evaluation/metrics/sections.py` — default True OK
- `src/evaluation/metrics/internal.py` — default True OK (`tier_utilization`, `theme_assignment_consistency`)

## Historical echoes

From `.wolf/buglog.json`: no entries matching `microscope`, `vitality`, `suitability`, or `bad_pairings`. No precedent to learn from — this is net-new infrastructure.

From `docs/segment-classification-changelog.md`: not relevant (this change does not touch section classification).

From `.wolf/cerebrum.md` Do-Not-Repeat:
- "[2026-04-19] Applied symptom fixes instead of root-cause fixes" — relevant: this change explicitly builds measurement before fixes, which is the opposite of the anti-pattern.
- "[2026-04-19] Did more or less than what was asked" — relevant: scope is intentionally narrow (6 metrics, 1 CLI group, no generator changes, no CI wiring).

## Alternatives considered

**Alternative A: Build metrics on the SequencePlan object directly (not the XSQ)**
- Pro: richer data (access to tier assignments, theme names, working sets, group_density).
- Con: bypasses the serialization layer entirely, so bugs in `xsq_writer.py` that corrupt the output are invisible to the microscope.
- Rejected: the XSQ is the actual artifact users load into xLights. If the XSQ is wrong, the show is wrong regardless of what the SequencePlan says. Metrics must validate the actual output.

**Alternative B: Build a single `xlight-evaluate quality` subcommand and put everything in the existing `src/evaluation/` CLI**
- Pro: keeps all evaluation under one roof.
- Con: `xlight-evaluate` is oriented toward regression against baselines (pass/fail). The microscope is oriented toward open-ended quality exploration (what's the number?). These are different UX goals. Mixing them in one CLI makes both worse.
- Rejected: `xlight-analyze microscope` is a better home because it fits the "analyze a song" mental model, not the "check whether a regression happened" mental model.

**Alternative C: FSEQ rendering and per-frame pixel metrics**
- Pro: measures exactly what xLights renders.
- Con: requires xLights running on the machine. No programmatic FSEQ renderer exists in this codebase. Would add weeks of work before any metric is available.
- Rejected: XSQ palette-derived proxies are imperfect but available now. FSEQ rendering is a future enhancement, not a prerequisite.
