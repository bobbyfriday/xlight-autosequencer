## 1. Corpus wiring (reuse existing CC0 pattern)

- [x] 1.1 Formalize `tests/fixtures/cc0_music/manifest.json` with structured fields per track: `slug`, `filename`, `source_url`, `genre`, `tempo_bpm`, `duration_seconds`, `expected_section_count`, `license`, **`sha256`** (expected hash captured at baseline creation). Include only the 4 FreePD-sourced tracks: `space_ambience`, `nostalgic_piano`, `maple_leaf_rag`, `funshine`.
- [x] 1.2 Remove `black_box_legendary.mp3` from `tests/validation/download_fixtures.py` (Pixabay license, not CC0 — keeping licensing story unambiguous). Update the README accordingly, removing the Pixabay row from the tracks table.
- [x] 1.3 Extend `tests/validation/download_fixtures.py`: after each download, compute SHA-256 and compare against manifest. On mismatch, delete the downloaded file and exit with code `8` (infrastructure failure). Add a `--update-hashes` flag that regenerates the manifest's hashes (deliberate rotation path).
- [x] 1.4 Add retry-with-backoff (3 attempts, 2s/4s/8s) around `urlretrieve` in the download script to absorb transient network flakes. Each attempt has a 30s timeout.
- [x] 1.5 Add local-corpus support: reader for `~/.xlight/eval_corpus.json`, shape `{"entries": [{"path": "/absolute/path/to/song.mp3", "slug": "...", ...}]}`. The gate merges local entries into the active corpus list. Local entries are NOT hash-verified (user's own files).
- [x] 1.6 Document both the CC0 corpus and the local-corpus augmentation in `tests/fixtures/cc0_music/README.md` — show a sample `~/.xlight/eval_corpus.json` and state that local entries are optional and never committed.
- [x] 1.7 Verify each of the 4 CC0 tracks downloads, hash-verifies, plays, and analyzes successfully via `xlight-analyze analyze <fixture>`; use these outputs as the initial baseline.

## 2. Analyzer baseline infrastructure

- [x] 2.1 Create `src/evaluation/analyzer_baseline.py` — `TrackSnapshot`, `FixtureSnapshot`, `AnalyzerBaseline` dataclasses; `check_track` / `check_fixture` / `load` / `save` functions. Parallel to the existing generator baseline module.
- [x] 2.2 Define the analyzer baseline JSON shape: `{schema_version, fixtures: {<slug>: {algorithms: {<name>: {event_times_ms: [...], event_labels: [...], tolerance: {...}}}}}}`
- [x] 2.3 Implement per-algorithm tolerance comparison: count tolerance %, timing tolerance ms, algorithm-specific rules (enharmonic equivalents for chordino, section merge window for qm_segmenter).
- [ ] 2.4 Generate `tests/golden/analyzer/baseline.json` from the 4 corpus fixtures via `xlight-evaluate snapshot --analyzer` (**deferred — requires full analyzer pipeline run; baseline is generated after the CLI subcommand lands in Cluster 3**)
- [x] 2.5 Write `tests/evaluation/test_analyzer_baseline.py` — 19 tests covering: load/save round-trip, schema mismatch, count tolerance at boundary, count mismatch short-circuit, timing tolerance at boundary, multiple timing violations, enharmonic-equivalent chord matching (on and off), section merge window, missing-fixture report, new-algorithm-no-baseline warning (not a hard fail), tolerance lookup defaults.

## 3. Acceptance-gate orchestrator

- [x] 3.1 Create `src/evaluation/acceptance_gate.py` — the orchestrator that dispatches analyzer + generator + UI suites and aggregates results into a single JSON report
- [x] 3.2 Add `gate` subcommand to `src/cli/evaluate.py` with flags: `--quick`, `--skip-ui`, `--fixture <slug>`, `--report <path>`, `--analyzer-baseline <path>`. Also add `snapshot-analyzer` subcommand to populate the analyzer baseline.
- [x] 3.3 Implement exit codes: 0 (pass), 6 (regression), 4 (no baseline), 8 (infrastructure failure). Priority order: infra > no-baseline > regression > pass.
- [x] 3.4 Implement report output: JSON at `tests/golden/reports/gate-<ISO-timestamp>.json` + human-readable table to stdout via `format_summary()`
- [ ] 3.5 Implement parallel execution: fixtures run concurrently in the analyzer + generator suites (ProcessPoolExecutor); UI flows run sequentially with Playwright — **deferred, v1 runs fixtures sequentially; add parallelism in a follow-up if CI budget demands it**
- [x] 3.6 Write `tests/evaluation/test_gate_cli.py` — 16 tests covering: exit-code aggregation (5 cases), `run_gate` happy/regression/no-baseline/infra paths, CLI help + command registration, `format_summary` output, report-path override, `--skip-ui` doesn't invoke pytest.

## 4. UI flow regression

- [x] 4.1 Add `playwright` + `pytest-playwright` + `pytest-rerunfailures` to `pyproject.toml` as a new `ui-tests` optional-dependencies group (pinned: `playwright>=1.48`, `pytest-playwright>=0.5`, `pytest-rerunfailures>=14.0`). Keeps Playwright out of the default install.
- [ ] 4.2 Add a GitHub Actions step to install Playwright browsers (`playwright install chromium --with-deps`) in `evaluate.yml`, **cached via `actions/cache@v4`** keyed on `playwright-${{ runner.os }}-${{ hashFiles('pyproject.toml') }}` targeting `~/.cache/ms-playwright/` so cache hits skip the ~30s browser download. **(Cluster 6 — CI workflow)**
- [x] 4.3 Register a new `ui` pytest marker in `pyproject.toml` `[tool.pytest.ini_options].markers` AND update `addopts = "-m 'not capture_only and not ui'"` so a bare `pytest` invocation excludes UI flows by default. The acceptance-gate orchestrator invokes them explicitly with `pytest -m ui`. Verified: bare pytest collects 0 UI flows; `pytest -m ui` skips cleanly with exit 0 when Playwright is absent.
- [x] 4.4 Create `tests/ui/conftest.py` — starts with `pytest.importorskip("playwright")` so missing-Playwright environments see SKIP (not ERROR). Session-scoped `flask_server` fixture spawns `create_app(testing=True)` on a dynamic port via `wsgiref.simple_server` (no separate Vite server — Flask serves the built bundle). Waits for port readiness, tears down on session end. Auto-skip if `src/review/frontend/dist/index.html` or CC0 corpus is missing.
- [x] 4.5 Implement `tests/ui/flows/test_upload_flow.py` — drag-drop/file-pick upload via `file-input` testid, verify `analyze-screen` renders, `metadata-banner` visible.
- [x] 4.6 Implement `tests/ui/flows/test_analyze_flow.py` — upload if library empty, wait for analyze screen, confirm no UI crash through network-idle.
- [x] 4.7 Implement `tests/ui/flows/test_view_flow.py` — library ↔ analyze round-trip, assert song rows present, click to return to analyze.
- [x] 4.8 Implement `tests/ui/flows/test_export_flow.py` — navigate toward export, assert one of {export-form, source-missing-block, layout-required, incomplete-theming} is visible (all are coherent states).
- [x] 4.9 Three-strike retry via `@pytest.mark.flaky(reruns=2, reruns_delay=1)` from `pytest-rerunfailures` on each flow. UI only — analyzer/generator suites do NOT retry.
- [x] 4.10 Write `tests/ui/README.md` covering first-time setup, running (`pytest -m ui` or gate), flow coverage table, server setup, selectors, debugging flakes with Playwright trace viewer, and the retry policy.
- [x] 4.11 Add content-verification flow (`tests/ui/flows/test_content_flow.py`, marker `content`) that uploads → triggers real analysis → asserts UI-displayed section count, song title, and duration match `tests/fixtures/cc0_music/manifest.json` values within tolerance (sections ±2, duration ±3s). Added data-testids on Analyze.tsx: `analyze-header-title`, `analyze-header-meta`, `sections-detected-count`, `inspector-sections-header` (with `data-section-count` attribute). Skips cleanly when madmom/vamp aren't installed. Registered `content` pytest marker.
- [x] 4.12 Reshape `--quick` gate mode: previously skipped UI entirely, now runs ONLY the content flow (`pytest -m "ui and content"` — one upload + real analysis). Full gate runs all five flows (`pytest -m ui`). Unit tests updated to exercise the new `run_ui_suite(skip=, quick=)` signature.

## 5. Optional visual regression (advisory)

- [ ] 5.1 Integrate `openwolf designqc` screenshot capture into UI flow tests (each flow captures a screenshot at its end state)
- [ ] 5.2 Store goldens under `tests/golden/ui/<flow>.jpg` (compressed, small)
- [ ] 5.3 Implement pixel-diff comparison with a threshold; log WARNING on mismatch but do NOT fail the gate (advisory-only for this change)
- [ ] 5.4 Document in `tests/ui/README.md` that screenshot diffs are advisory and how to update goldens

## 6. CI workflow integration

- [ ] 6.1 Update `.github/workflows/evaluate.yml` to invoke `xlight-evaluate gate` instead of `xlight-evaluate check`
- [ ] 6.2 Add a CI step that runs `tests/validation/download_fixtures.py` before the gate; cache the downloaded MP3s via `actions/cache@v4` keyed on the script's SHA so subsequent runs don't re-download. Remove the old `tests/golden/pro_reference/manifest.json` skip logic (CC0 corpus is always available).
- [ ] 6.3 Upload the gate's JSON report as a workflow artifact so regressions can be inspected from PR UI
- [ ] 6.4 Verify the workflow passes on a clean PR with no changes
- [ ] 6.5 Verify the workflow fails on a PR that intentionally breaks a tolerance (add a throwaway commit that shifts a number, confirm red CI, then remove)

## 7. Workflow integration documentation

- [ ] 7.1 Update `CLAUDE.md` Design-First Gate section to mention `xlight-evaluate gate` as the pre-merge check; cross-reference from the Stress-Testing section
- [ ] 7.2 Update `.claude/skills/openspec-archive-change/SKILL.md` (if writable) or add a note to `CLAUDE.md` that running `xlight-evaluate gate --quick` before archiving a change is recommended
- [ ] 7.3 Add a `.wolf/cerebrum.md` Key Learning entry describing the gate command, its exit codes, and when to run which mode (`gate` vs `gate --quick` vs `gate --skip-ui`)

## 8. Validation

- [ ] 8.1 Run `xlight-evaluate gate` locally against the committed corpus; verify it passes and produces the expected report
- [ ] 8.2 Run `xlight-evaluate gate --quick` locally; verify it completes under 2 minutes on a typical dev machine
- [ ] 8.3 Confirm `openspec validate acceptance-gate --strict` passes
- [ ] 8.4 Run `/pre-mortem acceptance-gate` against this change's own artifacts as a self-check; iterate on design/specs if the report surfaces material gaps
- [ ] 8.5 Open a test PR that intentionally breaks a tolerance; verify the gate catches it in CI; close without merging
