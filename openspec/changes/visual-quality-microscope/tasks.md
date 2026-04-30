## 1. Foundation — `MetricDefinition` extension and prop-type vocabulary

- [ ] 1.1 Add `higher_is_better: Optional[bool] = None` field to
      `MetricDefinition` in `src/evaluation/metrics/__init__.py`.
      **Default `None`** — *not* `True`. A `True` default would silently
      add improvement claims to every metric the moment it registers.
- [ ] 1.2 Audit each existing metric registration. Leave
      `higher_is_better` at `None` for every existing metric (none have
      been validated against rendered output). Document the audit
      result in the docstring.
- [ ] 1.3 Add `radial` and `vertical` tokens to
      `_PROP_TYPE_TOKENS` in `src/evaluation/xsq_reader.py` (additive;
      no existing inference result changes).
- [ ] 1.4 Write `tests/evaluation/test_metric_definition.py` —
      `higher_is_better` defaults to `None`, accepts `True`/`False`,
      existing registrations remain valid.
- [ ] 1.5 Write `tests/evaluation/test_xsq_reader_prop_inference.py` —
      `RadialSpinner` → `radial`; `OutlineRoofLeft` → `outline`;
      previously-matched names (`MatrixCenter`, `MegaTree`, `ArchLeft`)
      still infer their old types.

## 2. Vitality metrics (palette luminance)

- [ ] 2.1 Create `src/evaluation/metrics/vitality.py`. Implement:
      - `palette_luminance_mean` (duration-weighted Rec.601 luma across
        all placements; scalar 0–255).
      - `palette_luminance_cv` (**also duration-weighted** — std/mean
        across per-placement means using the same weighting). Names
        deliberately do not say "brightness" or "breathing".
- [ ] 2.2 Register both: `gated=True`, `pro_comparable=False`,
      `higher_is_better=None` (direction-of-good not validated). Metric
      descriptions explicitly say "palette-derived proxy; not a
      measurement of rendered light."
- [ ] 2.3 Write `tests/evaluation/test_vitality_metrics.py`:
      - All-black palette → `palette_luminance_mean=0.0`.
      - All-white palette → `palette_luminance_mean=255.0`.
      - Mixed palette → spot-check Rec.601 math.
      - Single placement → `palette_luminance_cv=0.0`.
      - Two placements with identical luminance → `cv=0.0`.
      - Two placements with widely-different luminance and unequal
        durations → `cv` reflects duration-weighted population (not
        the unweighted population).
      - Empty placements → both metrics return 0.0 with
        `reliability="no_placements"`.

## 3. Suitability metrics (variety + parallel fit signals)

- [ ] 3.1 Create `src/evaluation/metrics/suitability.py`. Implement six
      metrics:
      - `distinct_effect_count` (scalar, `higher_is_better=None`).
      - `effect_repeat_rate` (scalar 0.0–1.0, window via
        `audio_context.get("repeat_window_ms", 30_000)`,
        `higher_is_better=False` with description noting the
        "lower is better" claim is user preference, not validated).
      - `per_prop_type_diversity` (structured `{by_type, min_diversity}`,
        scalar = min, `higher_is_better=None`).
      - `bad_pairing_pct_handlist` against `HANDLIST_BAD_PAIRINGS`
        (scalar 0.0–1.0, `higher_is_better=False`, description flags
        "unvalidated").
      - `bad_pairing_pct_catalog` against
        `src/effects/builtin_effects.json:prop_suitability` value
        `"not_recommended"` (scalar, `higher_is_better=False`,
        description flags "unvalidated").
      - `pairing_disagreement_pct` — fraction of evaluable placements
        where exactly one of the two pairing signals flagged the
        placement (scalar, `higher_is_better=None` — direction unknown,
        this metric *is* the finding).
- [ ] 3.2 Cache the catalog JSON load (read once on module import; cope
      with missing file by returning 0.0 on `bad_pairing_pct_catalog`
      and `pairing_disagreement_pct` with `reliability="catalog_missing"`).
- [ ] 3.3 Write `tests/evaluation/test_suitability_metrics.py`:
      - `distinct_effect_count`: empty → 0; 3 same → 1; 3 different →
        3; "Unknown" excluded.
      - `effect_repeat_rate`: no repeats → 0.0; same model+effect at
        29s → counted; same at 31s → not counted; different model
        same effect → not counted.
      - `per_prop_type_diversity`: 2 prop types × 3 effects → min=3;
        one prop type with 1 effect → min=1; missing prop type
        skipped.
      - `bad_pairing_pct_handlist`: Plasma on `outline` → flagged;
        Plasma on `tree` → not flagged; unknown model → skipped.
      - `bad_pairing_pct_catalog`: Pinwheel on `arch` → flagged
        (`not_recommended`); Plasma on `outline` → not flagged
        (`possible`); unknown effect → skipped.
      - `pairing_disagreement_pct`: Plasma on `outline` → flagged
        (handlist=BAD, catalog=possible → disagreement); Pinwheel on
        `arch` → flagged (handlist=BAD, catalog=not_recommended → BOTH
        flag, no disagreement; verify the *agreement* case does NOT
        contribute to `pairing_disagreement_pct`).

## 4. Microscope runner

- [ ] 4.1 Create `src/microscope/__init__.py` (empty).
- [ ] 4.2 Create `src/microscope/runner.py`. `MicroscopeResult`
      dataclass + `run_song(audio_path, layout_path, output_dir,
      config_overrides) -> MicroscopeResult`:
      - Build `GenerationConfig` with production defaults
        (`curves_mode="none"`, `transition_mode="subtle"`,
        `genre="pop"`, `occasion="general"`) plus an explicit
        **`variation_seed=42`** (so determinism is provable).
      - Apply `config_overrides` (whitelist of known
        `GenerationConfig` keys).
      - Call `generate_sequence(config)` → output XSQ path.
      - Parse XSQ → `SequenceSummary`.
      - Import vitality + suitability + existing metric modules; run
        registry dispatcher (reuse pattern from
        `src/cli/evaluate.py:_compute_metrics_for_summary`).
      - Return `MicroscopeResult(slug, audio_path, xsq_path, summary,
        metrics, generated_at, config_snapshot)`.
      - Output XSQ retained at `output_dir/microscope/<slug>/sequence.xsq`.
- [ ] 4.3 `MicroscopeResult.to_dict()` — JSON-serializable; includes
      slug, ISO timestamp, config snapshot (non-path fields **plus
      variation_seed**), metrics as `{name: {value, kind, reliability}}`.

## 5. Panel runner

- [ ] 5.1 Create `src/microscope/panel.py`. `run_panel(manifest_path,
      layout_path, output_dir, config_overrides, parallel=False)`:
      - Load panel manifest JSON.
      - Resolve each slug's MP3: check
        `tests/fixtures/cc0_music/<slug>.mp3`; if any are missing,
        call
        `tests.validation.download_fixtures.download_all()`
        once for the run (this is the function that exists; **do not
        invoke a fictitious `ensure_fixture(slug)`**).
      - Call `run_song()` per entry; if `parallel=True`, use
        `concurrent.futures.ProcessPoolExecutor(max_workers=3)`.
      - Return list ordered by manifest slug list.
- [ ] 5.2 Create `tests/fixtures/reference/panel_manifest.json` with
      slugs `["funshine", "maple_leaf_rag", "nostalgic_piano",
      "space_ambience"]` referencing
      `tests/fixtures/cc0_music/manifest.json` and
      `tests/fixtures/reference/layout.xml`.

## 6. Diff tool

- [ ] 6.1 Create `src/microscope/diff.py`. `DiffReport` dataclass +
      `diff_results(current, baseline_dir) -> DiffReport`:
      - Per (song, metric): absolute + relative delta (guard
        baseline=0 with `relative_pct=None`).
      - `format_table()` columns: Song | Metric | Baseline |
        Current | Delta | %Change | Direction.
      - Direction:
        - `higher_is_better=None` → `↑` / `↓` only (no `✓`/`✗`).
        - `True` / `False` → `↑✓` / `↓✗` (or inverted) as appropriate.
      - Missing baseline → row says `NEW`.
      - Missing current metric → `MISSING`.
      - Structured-only metrics (no scalar) → excluded from the table
        with a footnote count.
- [ ] 6.2 Write `tests/microscope/test_diff.py` — table format,
      direction arrows for all three `higher_is_better` cases,
      missing-baseline handling, structured-metric exclusion.

## 7. Layout fixture rename

- [ ] 7.1 Rename `RooflineLeft` → `OutlineRoofLeft` and
      `RooflineRight` → `OutlineRoofRight` in
      `tests/fixtures/reference/layout.xml`. Update model-group
      `models=` attribute. Update XML comments.
- [ ] 7.2 Rename `StarSpinner` → `RadialSpinner` in the layout.
      Update model-group attribute. Update XML comments.
- [ ] 7.3 Correct the layout's header comment to say **9 props**
      (count: MatrixCenter, MegaTree, TreeLeft, TreeRight, ArchLeft,
      ArchRight, OutlineRoofLeft, OutlineRoofRight, RadialSpinner) and
      to acknowledge that `MegaTree` matches `mega` before `tree`
      (existing inference quirk; documented, not changed).

## 8. CLI

- [ ] 8.1 Create `src/cli/microscope.py`. Click group
      `microscope_group` with three subcommands. **Register on
      `xlight-evaluate`, not `xlight-analyze`**:
      - `run <audio_path>` — `run_song()`, prints metric table,
        writes `metrics.json`. With `--baseline`, also prints diff.
      - `panel` — `run_panel()`, per-song tables + aggregate means.
      - `baseline` — copies `metrics.json` files from `--input-dir`
        to `--golden-dir`. **Refuses to run if
        `tests/golden/microscope/sensitivity_passed.json` is missing
        or older than the latest commit touching
        `src/evaluation/metrics/`.**
      - `sensitivity` — runs the sensitivity probes (see §9) and writes
        `tests/golden/microscope/sensitivity_passed.json` on success.
- [ ] 8.2 Register on the existing `xlight-evaluate` CLI group
      (`src/cli/evaluate.py`).
- [ ] 8.3 Write `tests/cli/test_microscope_cli.py` — `--help` output,
      arg validation, sensitivity-gate refusal when the file is
      missing.

## 9. Sensitivity gate (must pass before any golden is committed)

- [ ] 9.1 Create `src/microscope/sensitivity.py`. `run_sensitivity()`:
      drives a small synthetic / forced-override variant of the panel
      and verifies metric responsiveness.
- [ ] 9.2 Probe: **single-effect override** — config_override forcing
      every placement to one effect. Assert
      `distinct_effect_count == 1` and
      `effect_repeat_rate >= 0.95`.
- [ ] 9.3 Probe: **all-black palette override** — config_override
      forcing palette to `(#000000,)`. Assert
      `palette_luminance_mean == 0.0` and `palette_luminance_cv == 0.0`.
- [ ] 9.4 Probe: **forced-bad-pairing override** — every placement
      becomes `Plasma` on a model whose inferred prop type is
      `outline`. Assert `bad_pairing_pct_handlist > 0.95` (handlist
      flags Plasma+outline) AND `bad_pairing_pct_catalog == 0.0`
      (catalog says Plasma+outline is `possible`, not
      `not_recommended`). The point of this probe is to *demonstrate
      the disagreement under a forced condition* — if the two metrics
      ever agree here, one of them is wrong.
- [ ] 9.5 Probe: **deterministic seed** — run twice with
      `variation_seed=42`. Assert all scalar metrics have absolute
      delta `< 1e-9`. Run with `variation_seed=43`. Assert at least
      one scalar metric moves by `≥ 1e-3` (proves the seed has an
      effect; if it doesn't, the runner isn't actually using it).
- [ ] 9.6 Write `tests/microscope/test_sensitivity.py` mirroring each
      probe at unit level (the integration probes drive the real
      pipeline; the unit tests run on a synthetic
      `SequenceSummary`).
- [ ] 9.7 On success, write
      `tests/golden/microscope/sensitivity_passed.json` containing
      `{run_at, metric_set_hash, results}` so the `baseline`
      subcommand can verify it.

## 10. Golden baseline

- [ ] 10.1 After §1–§9 pass: run
      `xlight-evaluate microscope sensitivity` — must succeed.
- [ ] 10.2 Run `xlight-evaluate microscope panel`. Inspect the printed
      tables and `pairing_disagreement_pct` — confirm both pairing
      signals are computed and the disagreement number is non-zero on
      the real corpus (proves the framing is doing useful work).
- [ ] 10.3 Run `xlight-evaluate microscope baseline --golden-dir
      tests/golden/microscope/`. Should write per-song baseline JSONs.
- [ ] 10.4 `git add tests/golden/microscope/ tests/golden/microscope/sensitivity_passed.json`
      and commit.
- [ ] 10.5 Verify reproducibility: re-run `xlight-evaluate microscope
      panel --baseline tests/golden/microscope/`. All scalar deltas
      must be ~0 (deterministic).

## 11. Documentation

- [ ] 11.1 Add a `## Microscope` section to `CLAUDE.md` under
      `## Commands`:
      - `xlight-evaluate microscope run <song.mp3>` — single song.
      - `xlight-evaluate microscope panel` — full panel.
      - `xlight-evaluate microscope sensitivity` — runs the
        sensitivity gate (must pass before baseline).
      - `xlight-evaluate microscope baseline` — save current as
        golden (refuses without sensitivity proof).
      - The three metric families and what they measure.
      - Explicit note: "Metric directions (`higher_is_better`) are
        `None` until validated against rendered output. The diff tool
        prints `↑/↓` movement without `✓/✗` improvement claims."
      - Disagreement framing: "If a generator change moves
        `bad_pairing_pct_handlist` and `bad_pairing_pct_catalog` in
        opposite directions, neither signal is trustworthy — that's
        the diagnostic, not noise to resolve."
