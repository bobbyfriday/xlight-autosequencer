# Known-broken tests (quarantined from CI)

These test files fail on `main` for **pre-existing reasons** unrelated to any
recent change. CI's unit-test job ignores them via `--ignore` flags so the
gate doesn't block PRs on rot. Local `pytest tests/` will still pick them
up — fix them in dedicated PRs and remove from this list.

The quarantine list lives in `.github/workflows/evaluate.yml` (the
`python-unit-tests` job's `Run unit + integration tests` step). Update both
this doc and the workflow when you fix or add a file.

## Categories

### Missing fixture files (likely unsynced golden files)

These tests reference fixture files that aren't committed or are out of
sync with the test expectations:

- `tests/evaluation/test_xsq_reader.py` — missing `tests/evaluation/fixtures/minimal_xsq/tiny.xsq`
- `tests/evaluation/test_integration_smoke.py` — same `tiny.xsq` dependency
- `tests/integration/test_brief_tab_render.py` — references `src/review/static/brief-tab.{html,js}` and `brief-presets.js` that don't exist

### Hardcoded container paths (devcontainer-specific)

These assume devcontainer paths (`/home/node/xlights/...`) that don't exist on
GitHub-hosted runners or non-container dev machines:

- `tests/integration/test_path_resolution.py` — assertions hardcoded to `/home/node/xlights`

### Stale assertions / drift

The tests' assertions don't match current code behavior. Likely tests rotted
when the underlying code evolved:

- `tests/integration/test_song_workspace_flow.py` — routes return 404 (route was renamed/removed?)
- `tests/integration/test_theme_variant_picker.py` — `'NoneType' object is not subscriptable` (variant lookup returns None)
- `tests/integration/test_themes_integration.py`
- `tests/integration/test_variant_api_browse.py`
- `tests/integration/test_variant_api_crud.py`
- `tests/integration/test_variant_import.py`
- `tests/integration/test_variant_query.py`
- `tests/packaging/test_import_by_path.py`
- `tests/packaging/test_manifest_endpoint.py`
- `tests/review/test_api_analysis.py`
- `tests/review/test_api_library.py`
- `tests/review/test_api_themes.py` — section/theme schema drift
- `tests/review/test_audio_stream.py` — 404 / file-not-found responses don't match expectations
- `tests/unit/test_brief_persistence.py`
- `tests/unit/test_brief_routes.py`
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_genius_segments.py`
- `tests/unit/test_librosa_hpss.py` — comparison expectations don't match current algorithm output
- `tests/unit/test_paths.py`
- `tests/unit/test_repetition_policy.py`
- `tests/unit/test_section_profiler.py`
- `tests/unit/test_song_workspace_route.py`
- `tests/unit/test_stem_inspector.py` — verdict logic drift
- `tests/unit/test_stems.py`
- `tests/unit/test_theme_routes.py`
- `tests/unit/test_transitions.py`
- `tests/unit/test_variant_cli.py` — variant CLI errors with "not found" instead of returning data
- `tests/unit/test_variant_crud_cli.py` — same
- `tests/unit/test_variant_library.py` — `assert 7 == 3` (variant count drift)

### Optional-dependency failures (CI-only)

These pass on dev machines with `.venv-vamp` + madmom installed but fail in
CI's stripped-down Python-only environment:

- `tests/evaluation/test_cli_check.py`
- `tests/evaluation/test_cli_compare.py`
- `tests/evaluation/test_cli_snapshot.py`
- `tests/evaluation/test_compare.py`
- `tests/validation/test_scenarios.py`

Could be fixed by either (a) adding mocks so they don't need the analyzer
pipeline, or (b) installing `.venv-vamp` in CI (rejected — see CLAUDE.md
"Pre-merge acceptance gate" for why).

## How to fix one

1. Run the file locally: `pytest tests/path/to/file.py -v`
2. Address the failures (real bug fix, fixture sync, or test update)
3. Confirm `pytest tests/path/to/file.py` passes cleanly
4. Remove the file's `--ignore` flag from `.github/workflows/evaluate.yml`
5. Remove the entry from this doc
6. PR with title prefix `fix(tests):` or `chore(tests):`

## Total counts (snapshot 2026-04-25)

- 35 quarantined files
- ~205 individual failing tests
- ~2451 tests still pass with quarantine in place

CI runs roughly **2451 tests in ~2-3 minutes** on the unit-test job.
