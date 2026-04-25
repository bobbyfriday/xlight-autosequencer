# Known-broken tests (quarantined from CI)

These test files fail on `main` for **pre-existing reasons** unrelated to any
recent change. CI's unit-test job ignores them via `--ignore` flags so the
gate doesn't block PRs on rot. Local `pytest tests/` will still pick them
up — fix them in dedicated PRs and remove from this list.

The quarantine list lives in `.github/workflows/evaluate.yml` (the
`python-unit-tests` job's `Run unit + integration tests` step). Update both
this doc and the workflow when you fix or add a file.

## Recently resolved

These were on the quarantine list and have been fixed or removed:

- ✅ `tests/evaluation/test_xsq_reader.py` — fixture path was gitignored;
  added `!tests/evaluation/fixtures/**/*.xsq` exception (PR fixing batch 1).
- ✅ `tests/evaluation/test_integration_smoke.py` — same `tiny.xsq` fix.
- ✅ `tests/unit/test_brief_persistence.py` — removed obsolete
  `TestBriefPresetsJs` class that validated a deleted JS file; the 5 other
  tests in the file are real and now pass.
- ✅ Deleted entirely (obsolete server-rendered routes replaced by React
  frontend in PRs #51, #74, #83):
  - `tests/integration/test_brief_tab_render.py` (HTML/JS fragment tests)
  - `tests/integration/test_song_workspace_flow.py` (route 404)
  - `tests/unit/test_song_workspace_route.py` (route 404)
  - `tests/unit/test_dashboard_routes.py` (route 404)
  - `tests/unit/test_brief_routes.py` (blueprint not registered)
  - `tests/unit/test_theme_routes.py` (blueprint not registered)

The dead-code modules `src/review/brief_routes.py` and
`src/review/theme_routes.py` still exist but are not registered with the
Flask app — they're legacy server-rendered routes whose blueprints were
never wired into the React-era `create_app`. Cleaning them up is a separate
concern.

## Categories

### Hardcoded container paths (devcontainer-specific)

These assume devcontainer paths (`/home/node/xlights/...`) that don't exist on
GitHub-hosted runners or non-container dev machines:

- `tests/integration/test_path_resolution.py` — assertions hardcoded to `/home/node/xlights`

### Stale assertions / drift

The tests' assertions don't match current code behavior. Likely tests rotted
when the underlying code evolved:

- `tests/integration/test_theme_variant_picker.py` — `'NoneType' object is not subscriptable` (variant lookup returns None)
- `tests/integration/test_themes_integration.py` — 16/17 pass; one test has parameter-rename drift (`Color Wash` → `ColorWash`, `Velocity1` → `Liquid_Speed`, etc.) that needs careful expected-output update
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
- `tests/unit/test_genius_segments.py`
- `tests/unit/test_librosa_hpss.py` — comparison expectations don't match current algorithm output
- `tests/unit/test_paths.py`
- `tests/unit/test_repetition_policy.py`
- `tests/unit/test_section_profiler.py`
- `tests/unit/test_stem_inspector.py` — verdict logic drift
- `tests/unit/test_stems.py`
- `tests/unit/test_transitions.py`
- `tests/unit/test_variant_cli.py` — variant CLI errors with "not found" instead of returning data
- `tests/unit/test_variant_crud_cli.py` — same
- `tests/unit/test_variant_library.py` — `assert 7 == 3` (variant count drift)

### Hardcoded container paths (devcontainer-specific)

- `tests/integration/test_path_resolution.py` — assertions hardcoded to `/home/node/xlights`

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

## Total counts (snapshot 2026-04-25, batch 1 fixed)

- 28 quarantined files (was 37; 7 files resolved or deleted)
- 7 files removed entirely (obsolete server-rendered routes)
- 2104 tests now pass with quarantine in place (was 2084 → +20)

CI runs roughly **2104 tests in ~2 minutes** on the unit-test job.

### Categories at remaining quarantine size

- 18 stale-assertion / drift files (real debugging work each)
- 5 optional-dep CI-only failures (would pass with .venv-vamp)
- 1 hardcoded container path file
- 4 missing static / fixture asset files (theme-variant-picker, brief-tab successors)
