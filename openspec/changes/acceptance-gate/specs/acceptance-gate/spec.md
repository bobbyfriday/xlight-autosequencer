## ADDED Requirements

### Requirement: Single unified gate command

The system SHALL provide a `xlight-evaluate gate` subcommand that runs the full acceptance suite (analyzer baselines, generator baselines, UI flows) against a portable fixture corpus and exits with one of these codes:

- `0` — all suites pass
- `6` — at least one suite detected a regression
- `4` — no baseline exists for one or more suites (run `xlight-evaluate snapshot --all` first)
- `8` — infrastructure failure (could not run one or more suites — missing dependency, missing fixture, browser did not start)

The command SHALL write a structured JSON report to `tests/golden/reports/gate-<ISO-timestamp>.json` with per-suite + per-fixture results, and SHALL print a human-readable summary table to stdout.

#### Scenario: All suites pass

- **WHEN** `xlight-evaluate gate` is invoked and all suites pass within their tolerance rules
- **THEN** the command SHALL exit with code `0`
- **AND** the summary SHALL show each suite as `PASS` with per-fixture counts

#### Scenario: Analyzer regression detected

- **WHEN** `xlight-evaluate gate` detects a count or timing tolerance violation in the analyzer suite
- **THEN** the command SHALL exit with code `6`
- **AND** the JSON report SHALL include the specific algorithm, fixture, tolerance rule, and observed vs expected values

#### Scenario: Playwright not installed

- **WHEN** `xlight-evaluate gate` is invoked on a system without Playwright available
- **THEN** the command SHALL exit with code `8` unless `--skip-ui` is passed
- **AND** when `--skip-ui` is passed, the command SHALL skip the UI suite and report it as `SKIPPED` in the summary

### Requirement: Quick mode for local iteration

The gate SHALL support a `--quick` flag that runs against a single fixture and skips the UI suite, for rapid local iteration. Quick mode SHALL still use the same pass/fail contract and exit codes; it simply reduces the scope of what is checked.

#### Scenario: Developer runs quick gate locally

- **WHEN** a developer invokes `xlight-evaluate gate --quick`
- **THEN** the gate SHALL run only the analyzer + generator suites against one fixture (the first in the corpus manifest)
- **AND** the gate SHALL complete in under 2 minutes on a typical developer machine

### Requirement: Snapshot command updates all baselines atomically

The system SHALL provide a `xlight-evaluate snapshot --all` subcommand that regenerates every baseline (analyzer + generator) from the current state of the code against the portable corpus, and writes out both baseline files in a single transactional operation. Partial snapshots (e.g., `--analyzer-only`) SHALL also be supported for targeted updates.

#### Scenario: Intentional change shifts analyzer outputs

- **WHEN** a developer intentionally changes an analyzer algorithm and needs to update baselines
- **THEN** running `xlight-evaluate snapshot --analyzer` SHALL update `tests/golden/analyzer/baseline.json` in place
- **AND** the command SHALL print a diff summary of what changed so the developer can review before committing

### Requirement: GitHub Actions runs the gate on every pull request

The `.github/workflows/evaluate.yml` workflow SHALL invoke `xlight-evaluate gate` (not `xlight-evaluate check`) on every pull request to `main` and every push to `main`. The workflow SHALL fail the job if the gate exits with any non-zero code. The workflow SHALL download the CC0 corpus via `tests/validation/download_fixtures.py` as a pre-step; a download failure SHALL result in exit code `8` (infrastructure), which the workflow SHALL treat as a setup failure (not a regression) — surfacing the error but not blocking merge if a re-run succeeds.

#### Scenario: PR opened with analyzer regression

- **WHEN** a pull request introduces a change that causes the analyzer suite to fail
- **THEN** the GitHub Actions job SHALL fail
- **AND** the gate's JSON report SHALL be uploaded as a workflow artifact for inspection

#### Scenario: CC0 corpus downloaded successfully

- **WHEN** the workflow runs and `tests/validation/download_fixtures.py` succeeds
- **THEN** the workflow SHALL run the full gate against the 5 CC0 tracks
- **AND** the workflow SHALL NOT skip the gate under any condition short of infrastructure failure

#### Scenario: CC0 download fails mid-CI

- **WHEN** the CC0 download fails (network error, source moved)
- **THEN** the gate SHALL exit with code `8`
- **AND** the workflow SHALL report this as an infrastructure failure distinct from a regression
- **AND** the workflow SHALL allow a retry without human intervention

### Requirement: CC0 corpus tracks are hash-verified on download

`tests/fixtures/cc0_music/manifest.json` SHALL include an expected SHA-256 hash for each track. The download script SHALL, after fetching each MP3, compute its SHA-256 and compare against the manifest. A hash mismatch SHALL cause the download step to exit with code `8` (infrastructure failure) and SHALL NOT produce a silent baseline shift.

#### Scenario: Source URL silently replaces a track

- **WHEN** the CC0 download script fetches a track whose computed SHA-256 differs from the manifest's expected value
- **THEN** the script SHALL exit with code `8`
- **AND** the error message SHALL name the specific track, the expected hash, and the observed hash
- **AND** the gate SHALL NOT run against the changed MP3

#### Scenario: Hash manifest is regenerated intentionally

- **WHEN** a developer intentionally rotates the corpus and runs `python -m tests.validation.download_fixtures --update-hashes`
- **THEN** the script SHALL write new hashes to the manifest
- **AND** the resulting manifest diff SHALL be visible in the PR for human review

### Requirement: UI flow tests are isolated from default pytest discovery

UI flow tests under `tests/ui/flows/` SHALL be marked with `@pytest.mark.ui` and the repo's pytest `addopts` SHALL exclude the `ui` marker by default (`-m 'not capture_only and not ui'`). The acceptance-gate orchestrator SHALL select them explicitly with `pytest -m ui`. `tests/ui/conftest.py` SHALL call `pytest.importorskip("playwright")` at module load so developers without Playwright installed see all UI tests as SKIPPED rather than as errors.

#### Scenario: Developer runs plain pytest without Playwright

- **WHEN** a developer runs `pytest` with no arguments and no Playwright installed
- **THEN** pytest SHALL collect all other tests normally
- **AND** pytest SHALL NOT discover or attempt to import `tests/ui/flows/`
- **AND** the run SHALL NOT fail due to a missing Playwright install

#### Scenario: Developer runs pytest -m ui without Playwright

- **WHEN** a developer runs `pytest -m ui` and Playwright is not installed
- **THEN** each UI test SHALL report as SKIPPED with a clear reason ("playwright not installed")
- **AND** the exit code SHALL be 0 (no failures, just skips)

### Requirement: Optional local corpus augmentation

The gate SHALL read `~/.xlight/eval_corpus.json` if present and add any listed songs to the corpus for that run. The file SHALL be optional — its absence SHALL NOT affect gate behavior. Songs listed in the local corpus SHALL be referenced by absolute path and SHALL NOT be committed to the repo or reported back to CI.

#### Scenario: User has local corpus augmentation

- **WHEN** `~/.xlight/eval_corpus.json` exists with entries pointing at the user's music library
- **AND** a developer runs `xlight-evaluate gate` locally
- **THEN** the gate SHALL run against the default CC0 corpus PLUS the user's listed songs

#### Scenario: CI run has no local corpus

- **WHEN** the gate runs in CI and `~/.xlight/eval_corpus.json` does not exist
- **THEN** the gate SHALL run against only the default CC0 corpus
- **AND** the gate SHALL NOT error or warn about the missing local file
