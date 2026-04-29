## 1. Metric foundation — `MetricDefinition` extension

- [ ] 1.1 Add `higher_is_better: bool = True` field to `MetricDefinition` in `src/evaluation/metrics/__init__.py`. Default `True` keeps all existing registrations valid without code changes.
- [ ] 1.2 Audit each existing metric registration and set `higher_is_better` explicitly where it differs from the default:
  - `src/evaluation/metrics/effects.py`: `effect_type_histogram` → `higher_is_better=False` (unknown_effect_fraction: lower is better)
- [ ] 1.3 Write `tests/evaluation/test_metric_definition.py` — verify `higher_is_better` default, explicit False, and that existing metric registrations remain valid.

## 2. Vitality metrics

- [ ] 2.1 Create `src/evaluation/metrics/vitality.py` — implement `brightness_proxy_mean` (duration-weighted mean of Rec.601 palette luminance across all placements; scalar 0–255) and `brightness_proxy_cv` (coefficient of variation of per-placement luminance; scalar ≥0). Handle edge cases: no placements → value=0.0 reliability="ok"; placement with no palette_colors → skip that placement.
- [ ] 2.2 Register both metrics: `gated=True`, `pro_comparable=False`, `higher_is_better=True` for both (brighter and more varied = better).
- [ ] 2.3 Write `tests/evaluation/test_vitality_metrics.py`:
  - All-black palette → `brightness_proxy_mean=0.0`
  - All-white palette → `brightness_proxy_mean=255.0`
  - Mixed palette → spot-check Rec.601 math
  - Single placement → `brightness_proxy_cv=0.0` (no variation with one sample)
  - Two placements with identical luminance → `brightness_proxy_cv=0.0`
  - Two placements with very different luminance → CV > 0.5
  - Empty placements → both return 0.0

## 3. Suitability metrics

- [ ] 3.1 Create `src/evaluation/metrics/suitability.py` — implement four metrics:
  - `distinct_effect_count`: count of unique non-"Unknown" `effect_type` values across all placements; scalar (float cast of int).
  - `effect_repeat_rate`: fraction of placements where the same `(model_name, effect_type)` appeared within the last 30_000 ms on the same model; scalar 0.0–1.0. Window size configurable via `audio_context.get("repeat_window_ms", 30_000)`.
  - `per_prop_type_diversity`: per inferred prop type, count distinct effect names; structured payload `{"by_type": {prop_type: count}, "min_diversity": int}`; scalar = min diversity (flag if min ≤ 2). Prop types inferred from `SequenceSummary.inferred_prop_types`.
  - `bad_pairing_pct`: fraction of placements that match `OBVIOUSLY_BAD_PAIRINGS` (see design.md for the 6-entry dict). Skip placements whose model is not in `inferred_prop_types`. Return 0.0 if no placements have known prop types.
- [ ] 3.2 Register all four metrics: `gated=True`; `distinct_effect_count` and `per_prop_type_diversity` are `higher_is_better=True`; `effect_repeat_rate` and `bad_pairing_pct` are `higher_is_better=False`.
- [ ] 3.3 Write `tests/evaluation/test_suitability_metrics.py`:
  - `distinct_effect_count`: empty → 0; 3 placements same effect → 1; 3 different → 3; "Unknown" excluded.
  - `effect_repeat_rate`: no repeats → 0.0; same model + effect within 29s → counted; same model + effect at 31s → not counted; different model same effect → not counted.
  - `per_prop_type_diversity`: 2 prop types × 3 effects each → min=3; one prop type with 1 effect → min=1 (flagged); missing prop type from inferred_prop_types → skipped.
  - `bad_pairing_pct`: Plasma on outline → violation; Plasma on tree → no violation; unknown model → skipped; all unknown models → 0.0.

## 4. Microscope runner

- [ ] 4.1 Create `src/microscope/__init__.py` (empty).
- [ ] 4.2 Create `src/microscope/runner.py` — `MicroscopeResult` dataclass and `run_song(audio_path, layout_path, output_dir, config_overrides) -> MicroscopeResult`:
  - Builds `GenerationConfig` with production defaults (`curves_mode="none"`, `transition_mode="subtle"`, `genre="pop"`, `occasion="general"`).
  - Applies `config_overrides` on top (allowed keys are valid `GenerationConfig` fields).
  - Calls `generate_sequence(config)` → output XSQ path.
  - Parses XSQ with `xsq_reader.parse_xsq(xsq_path)` → `SequenceSummary`.
  - Imports all metric modules (including new vitality + suitability), computes all registered metrics via registry dispatcher (reuse `_compute_metrics_for_summary` pattern from `src/cli/evaluate.py`).
  - Returns `MicroscopeResult(slug, audio_path, xsq_path, summary, metrics, generated_at, config_snapshot)`.
  - Output XSQ is written to `output_dir/microscope/<slug>/sequence.xsq` and retained.
- [ ] 4.3 `MicroscopeResult.to_dict()` — JSON-serializable. Includes slug, generated_at ISO timestamp, config snapshot (just the non-path fields), and metrics as `{name: {value, kind}}`.

## 5. Panel runner

- [ ] 5.1 Create `src/microscope/panel.py` — `run_panel(manifest_path, layout_path, output_dir, config_overrides, parallel=False) -> list[MicroscopeResult]`:
  - Loads panel manifest JSON.
  - Resolves each slug's MP3 path from the CC0 manifest using the download-fixtures path logic (check `tests/fixtures/cc0_music/<slug>.mp3`; if missing, attempt download via `tests/validation/download_fixtures.py`'s `ensure_fixture(slug)` function).
  - Calls `run_song()` per entry; if `parallel=True`, uses `concurrent.futures.ProcessPoolExecutor(max_workers=3)`.
  - Returns list ordered by manifest slug list.
- [ ] 5.2 Create `tests/fixtures/reference/panel_manifest.json` with slugs: `["funshine", "maple_leaf_rag", "nostalgic_piano", "space_ambience"]` referencing `tests/fixtures/cc0_music/manifest.json` and `tests/fixtures/reference/layout.xml`.

## 6. Diff tool

- [ ] 6.1 Create `src/microscope/diff.py` — `DiffReport` dataclass and `diff_results(current: list[MicroscopeResult], baseline_dir: Path) -> DiffReport`:
  - Loads per-song `baseline.json` from `baseline_dir/<slug>/baseline.json`.
  - For each song × metric, computes `absolute_delta = current - baseline` and `relative_pct = (current - baseline) / baseline * 100`.
  - `DiffReport.format_table()` prints aligned columns: Song | Metric | Baseline | Current | Delta | %Change | Direction arrow.
  - Direction arrow uses `MetricDefinition.higher_is_better` to show "↑✓" (improved) vs "↓✗" (regressed) vs "↑✗" / "↓✓" for reverse metrics.
  - Missing baseline for a song → row shows "NEW" instead of delta.
  - Missing metric in current → row shows "MISSING".
- [ ] 6.2 Write `tests/microscope/test_diff.py` — verify table formatting, direction arrows, missing-baseline handling, missing-metric handling.

## 7. CLI

- [ ] 7.1 Create `src/cli/microscope.py` — Click group `microscope_group` with three subcommands:
  - `run <audio_path>` — runs `run_song()`, prints metric table, writes `metrics.json`, optionally diffs.
  - `panel` — runs `run_panel()`, prints per-song tables + aggregate means, optionally diffs.
  - `baseline` — copies `metrics.json` files from `--input-dir` to `--golden-dir`, prints instructions to `git add + commit`.
- [ ] 7.2 Register in `src/cli/__init__.py`: `cli.add_command(microscope_group, name="microscope")`.
- [ ] 7.3 Write `tests/cli/test_microscope_cli.py` — smoke tests via `click.testing.CliRunner`:
  - `microscope --help` shows the group.
  - `microscope run --help` shows options.
  - `microscope panel --help` shows options.
  - `microscope baseline --help` shows options.
  - `microscope run` without args exits non-zero with usage error.
  - `microscope panel --manifest /nonexistent` exits non-zero with error.

## 8. Golden baseline

- [ ] 8.1 After tasks 1–7 pass: run `xlight-analyze microscope panel` with the CC0 songs present locally.
- [ ] 8.2 Run `xlight-analyze microscope baseline --golden-dir tests/golden/microscope/` to write baseline JSON files.
- [ ] 8.3 Commit `tests/golden/microscope/` to the repo. These are the Phase B starting point — every subsequent quality fix should move these numbers.
- [ ] 8.4 Verify sensitivity: run `xlight-analyze microscope panel --baseline tests/golden/microscope/` and confirm all deltas are ~0 (deterministic, same run = same baseline).

## 9. Documentation update

- [ ] 9.1 Add a `## Microscope` section to `CLAUDE.md` under `## Commands`, documenting:
  - `xlight-analyze microscope run <song.mp3>` — single song
  - `xlight-analyze microscope panel` — full panel
  - `xlight-analyze microscope baseline` — save current as golden
  - The three metric families and what they measure
  - "Run the panel before and after any generator change. If no metric moves by >15%, the change had no measurable visual effect."
