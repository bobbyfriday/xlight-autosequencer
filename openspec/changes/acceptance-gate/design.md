## Context

The repo already carries considerable regression infrastructure that grew independently over several features:

- `src/evaluation/` — "Quality Calibration Harness." Generator-layer metrics (placements_per_minute, density_energy_correlation, etc.) with a baseline stored at `tests/golden/baseline.json` and a CLI (`xlight-evaluate check|snapshot|compare`). Runs in CI via `.github/workflows/evaluate.yml` but gracefully skips when the corpus manifest's absolute paths aren't available (maintainer-local music library).
- `src/validation/` — "Sequence Validation Framework." Deterministic scorers that take a `SequencePlan` + `HierarchyResult` and return 0–100. Works on synthetic scenarios (no audio needed), so it runs anywhere.
- `tests/fixtures/*.wav` — short audio clips (10-second and shorter) for unit tests.
- `tests/golden/baseline.json` — populated generator baseline. Historical reports in `tests/golden/reports/`.
- `tests/ui/` — mostly empty. `fixtures/` + a `strip_states_README.md`. No flow tests.
- Vitest for React component unit tests under `src/review/frontend/tests/`.

What is **missing** relative to the user's ask ("upload files, analyze with everything, compare to baseline, test the UI, run before humans review"):

1. **Analyzer-layer regression.** Generator baselines exist; analyzer-layer baselines (per-algorithm timing tracks) do not. An analyzer change that shifts beat positions by 20ms won't fail the existing gate unless it happens to move generator metrics.
2. **UI flow regression.** No automated browser-driven tests. `openwolf designqc` captures screenshots for manual review but does not assert behavior.
3. **A portable corpus.** The current baseline references `/home/node/xlights/baseline-sequences/...` which exists on the maintainer's machine only. CI skips. A change that breaks generation on mainstream inputs isn't caught until a human runs it locally.
4. **A single entry point.** `xlight-evaluate check` covers generator quality. `pytest` covers unit tests. Nothing wraps everything with a single pass/fail verdict.

This change unifies those gaps under a single `acceptance-gate` capability without rewriting what works. The existing `xlight-evaluate check` + generator baseline stay exactly as they are; the gate invokes them as one of its suites.

## Goals / Non-Goals

**Goals:**

- Produce a single command (`xlight-evaluate gate`) that runs the full pre-human-review acceptance suite and exits 0 (all pass), non-zero (regression detected), with a structured JSON report.
- Extend regression coverage to the analyzer layer with per-algorithm golden outputs and tolerance rules appropriate to each algorithm's determinism.
- Add UI flow regression covering the critical upload → analyze → view → export path of the web review UI.
- Commit a small portable fixture corpus so the gate runs on any CI or developer machine without external dependencies.
- Keep the gate fast enough to run on every PR (target: under 10 minutes on GitHub-hosted CI).
- Integrate into the OpenSpec workflow so every change has a running gate before human review.

**Non-Goals:**

- Replacing or restructuring `src/evaluation/` or `src/validation/`. They are sound; the gate wraps them.
- Covering the Tauri desktop shell or any packaging-specific behavior (the `tests/packaging/smoke` suite exists separately).
- Pixel-exact UI visual regression. Too brittle for a weekly-changing frontend.
- Full-song corpora. The gate uses short fixtures. Long-form regression remains the maintainer's local `xlight-evaluate check` run.
- Mutation testing, property-based testing, or fuzzing. Out of scope.

## Decisions

### 1. Single entry point via `xlight-evaluate gate`

**Decision:** Add a `gate` subcommand to the existing `xlight-evaluate` CLI (`src/cli/evaluate.py`). It orchestrates three sub-suites in parallel where possible:

1. **Analyzer suite** — runs all algorithms on each fixture, compares outputs to `tests/golden/analyzer/baseline.json`.
2. **Generator suite** — reuses the existing `xlight-evaluate check` behavior with the portable fixture corpus.
3. **UI suite** — spawns Flask backend + Vite dev server, runs Playwright flow tests, captures screenshots via `openwolf designqc`.

Output: a single JSON report (`tests/golden/reports/gate-<timestamp>.json`) with per-suite + per-fixture results, and a summary table printed to stdout. Exit codes: 0 = pass, 6 = regression, 4 = no baseline, 8 = infrastructure failure (CI couldn't even run the suite).

**Why X over Y:**
- Three separate commands (`xlight-analyzer-check`, `xlight-generator-check`, `xlight-ui-check`) were considered. Rejected because the user's intent is "one command before humans review," and three commands means three CI jobs, three exit codes, three places to look for regressions.
- A Makefile target wrapping pytest + xlight-evaluate + playwright was considered. Rejected because error reporting is fragmented (each tool has its own format). A Python orchestrator produces one consistent report.
- Reusing `xlight-evaluate check` directly was considered. Rejected because `check` is a specific generator-baseline verb; adding UI/analyzer scope to it confuses its contract.

### 2. UI flow testing: Playwright with Python bindings (`playwright-python`)

**Decision:** Add `playwright` (Python bindings, `pytest-playwright`) as a test-time dependency. Tests live under `tests/ui/flows/test_*.py`, run via pytest, and spawn a Flask backend + Vite dev server as fixtures.

**Why X over Y:**
- Cypress was considered. Rejected because it's Node-only; orchestrating from the Python gate is awkward.
- `openwolf designqc` alone was considered (no Playwright). Rejected because screenshots can only assert visual state, not behavior — "does clicking Upload trigger a POST /api/v1/import and render the analyze screen?" needs flow testing.
- Selenium was considered. Rejected in favor of Playwright's faster + more reliable waits, better tracing, and built-in screenshot support.
- `pytest-playwright` keeps the test runner consistent with the rest of the Python suite — one `pytest` invocation covers unit, integration, evaluation, validation, and UI.

Playwright is ~80MB installed (chromium binary) but that's acceptable CI overhead for the coverage it buys.

### 3. Analyzer baselines use per-algorithm tolerance, not byte-exact matching

**Decision:** `tests/golden/analyzer/baseline.json` stores the full TimingTrack set per fixture per algorithm, plus a tolerance rule per algorithm. Comparison is structural:

- **Count tolerance** — number of events within ±N% (e.g., beat count ±2%, onset count ±10%).
- **Timing tolerance** — per-event timestamp within ±M ms (e.g., beats ±30ms, onsets ±50ms).
- **Ordering** — events sorted by timestamp, no duplicates.
- **Algorithm-specific** — chord sequences allow enharmonic equivalents; section boundaries allow merges within 2 seconds.

A baseline mismatch reports the diff and the out-of-tolerance metric. Updating the baseline is a deliberate `xlight-evaluate snapshot --analyzer` step that emits a diff file for human review before the PR lands.

**Why X over Y:**
- Byte-exact comparison was considered. Rejected because madmom, demucs, and vamp have non-deterministic paths on some platforms (threading, BLAS, GPU fallback) and float accumulation causes sub-ms drift. Exact matching would be perpetually red.
- Score-only comparison (like the existing generator baseline) was considered. Rejected because a scalar like "onset count" hides a problem where every onset has shifted by 100ms.
- Per-event fuzzy matching (Hungarian algorithm style) was considered. Rejected as over-engineered; sorted + timing-tolerance is enough for a regression gate.

### 4. Corpus: reuse existing CC0 download-on-demand pattern + optional local corpus

**Decision:** Two-tier corpus:

- **Default (CI + everyone) — the existing CC0 corpus, restricted to genuinely CC0 tracks.** `tests/fixtures/cc0_music/` documents 5 tracks, but only 4 are CC0: `space_ambience.mp3`, `nostalgic_piano.mp3`, `maple_leaf_rag.mp3`, `funshine.mp3` — all from FreePD. The fifth, `black_box_legendary.mp3`, is from Pixabay and uses the **Pixabay Content License** (CC0-like but not CC0 — restricts resale and some uses). To keep the licensing story unambiguous, the default gate corpus is the **4 FreePD tracks only**. The Pixabay track is removed from the download script and manifest. It can be re-added later as a separately-labeled optional track if that genre (electronic/cinematic) coverage turns out to matter. The 4 remaining tracks still span ambient/piano/ragtime/pop-funk at varied tempos. MP3s are NOT committed (`.gitignore` excludes them) — CI runs the download script once, caches the result between runs, and the repo stays clean. This becomes the gate's default corpus. A formal `tests/fixtures/cc0_music/manifest.json` is added with per-track fields — including an **SHA-256 hash** captured at baseline-creation time — so a silent MP3 replacement at the source URL fails the download step instead of shifting the baseline invisibly.

- **Optional local augmentation — `~/.xlight/eval_corpus.json`.** Developers (including the maintainer) can point the gate at their own music library by adding a manifest file in their home directory listing extra songs by path. This file is local-only, never checked in, and augments the default corpus rather than replacing it. A user who wants to test against a specific song (e.g., the Mariah Carey test case) can add it locally without any licensing or repo concerns.

**Why X over Y:**

- Committing new CC0 fixtures was considered. Rejected — `tests/fixtures/cc0_music/` already exists with a README, curated track list, and download script. Duplicating that work would be wasteful. `.gitignore` already excludes the MP3s, confirming the no-commit stance.
- Local-only corpus (no default, no CI coverage) was considered (matches user instinct to avoid check-ins). Rejected because CI needs something to run the gate against; without a default, the gate becomes a local-only tool and the "nothing merges that breaks the gate" guarantee evaporates. The CC0 corpus gives us CI coverage *without* checking in audio.
- Generating synthetic audio was considered. Rejected — synthetic audio doesn't exercise real harmonic content, vocal tracking, or genre-specific algorithms.

**Operational shape:**

- CI downloads the 5 CC0 MP3s once per runner via the existing `download_fixtures.py`, caches them in `~/.cache/xlight-cc0/` (or the CI cache layer) for subsequent runs.
- If the download fails (network issue, source moved), CI logs the failure and exits with code `8` (infrastructure) — not a regression, a setup failure. The workflow treats these differently.
- The maintainer can still keep the existing `tests/golden/pro_reference/manifest.json` for richer local testing; that stays unchanged.

### 5. Integration with OpenSpec workflow: documented, not auto-run

**Decision:** Document in `CLAUDE.md` and in the `acceptance-gate` spec that the gate should be run before `/opsx:archive`. Do NOT auto-run it from the archive skill — that couples two workflows and makes `/opsx:archive` fail mysteriously when the gate fails.

The GitHub Actions workflow in `.github/workflows/evaluate.yml` stays the hard enforcement: nothing merges to main without the gate passing. Developers can run `xlight-evaluate gate` locally any time; the archive workflow just reminds them to.

**Why X over Y:**
- Auto-running on archive was considered (per the user's "run after every spec is done" language). Rejected because (a) archives are a per-developer ceremony and slow gates kill ceremonies, (b) the hard guarantee should be at merge, not archive, (c) archives often happen in batches.
- Running on every commit push was considered. Rejected because full gate is 3–10 minutes; that's too slow for the inner loop. Pre-merge is the right granularity.
- A pre-commit hook was considered. Rejected for the same reason.

### 6. Flaky-test policy: three-strike retry with hard fail

**Decision:** The UI suite is the flake-risk layer. Each UI flow test gets automatic retries up to 3 times. If a test passes any of the 3 runs, it passes. If it fails 3/3, the gate fails.

For analyzer determinism, flakes are tolerance bugs, not retry candidates. Analyzer failures do not retry.

**Why:** UI flakes are a fact of browser automation (network timing, animation waits). The retry budget buys reliability without hiding real regressions. Analyzer flakes indicate a tolerance rule is too tight — the fix is to widen the tolerance, not retry.

### 7. Pytest default invocation isolation

**Decision:** UI flow tests under `tests/ui/flows/` are marked with a new `@pytest.mark.ui` marker. The repo's `pyproject.toml` `addopts` is extended to exclude `ui` from default `pytest` invocations: `addopts = "-m 'not capture_only and not ui'"`. The acceptance-gate orchestrator selects them explicitly with `-m ui`.

Additionally, `tests/ui/conftest.py` SHALL skip the whole module with `pytest.importorskip("playwright")` at the top — so developers without Playwright installed can run `pytest -m ui` without a crash; they just see all UI tests as skipped.

**Why X over Y:**
- Leaving UI tests marker-less was considered. Rejected because `pytest` alone would discover them and crash on dev machines without Playwright (`playwright` import fails at collection time). Every dev would need Playwright installed just to run `pytest`. That's excessive overhead for unrelated work.
- Moving UI tests outside `tests/` was considered. Rejected because `tests/` is the single discoverable test root and fragmenting it creates friction for CI and developers.

### 8. Playwright browser install is cached in CI

**Decision:** `.github/workflows/evaluate.yml` uses `actions/cache@v4` keyed on the pinned Playwright version (from `pyproject.toml`) to cache `~/.cache/ms-playwright/`. Cache key: `playwright-${{ runner.os }}-${{ hashFiles('pyproject.toml') }}`. A cache miss re-downloads; a hit skips the ~30-second browser download on every run.

**Why X over Y:**
- No caching was considered. Rejected — every CI run pays 30s+ of Chromium download, amplifying the gate's runtime bill unnecessarily.
- Caching the entire pip wheel cache was considered. Rejected as orthogonal — a separate concern that already happens via `actions/setup-python@v5`'s built-in pip cache.

## Risks / Trade-offs

- **[Risk] Playwright adds a new dependency and CI setup complexity** → Mitigation: isolate to `pytest-playwright` plugin; install conditionally in CI (skip UI suite if Playwright unavailable, document workaround). Keep the gate CLI functional with a `--skip-ui` flag for environments where Playwright isn't installed.
- **[Risk] Portable corpus licensing** → Mitigation: source from Free Music Archive or ccMixter with explicit CC0/CC-BY. Include license notes in `tests/fixtures/corpus/LICENSE.md`. If no song fits, generate a synthetic fallback with known-good analyzer outputs.
- **[Risk] Gate runtime grows past the 10-minute CI budget** → Mitigation: the analyzer suite runs in parallel per fixture (fixtures are independent); the UI suite runs in parallel per flow. If it still overruns, split into a fast gate (unit + validation + one fixture) that runs on every push and a full gate that runs on PR label or nightly.
- **[Risk] Analyzer tolerances become theater** → Mitigation: tolerances start strict and widen only when a real-world change produces a principled reason to widen (documented per-algorithm in the baseline file). The `snapshot` step emits a diff that must be human-reviewed — preventing silent tolerance drift.
- **[Risk] UI tests become brittle and disabled** → Mitigation: flow tests target user-observable behavior, not implementation details (test by visible text + aria-label, never by CSS selector). Three-strike retry absorbs transient flakes without hiding real regressions.
- **[Risk] The gate becomes a merge bottleneck when flaky** → Mitigation: SLO — if the gate's false-positive rate exceeds 5% on a rolling 2-week window, treat as a priority-1 bug. The existing `tests/golden/reports/` history lets us measure this.
- **[Risk] Duplication between `src/evaluation/` and the new orchestrator** → Mitigation: the orchestrator is thin — it delegates to the existing framework functions rather than reimplementing them. Analyzer baseline logic mirrors generator baseline logic (parallel structure, shared conventions).
- **[Risk] The trivial-path carve-out (from design-first-gate) tempts adding UI checks to small PRs unnecessarily** → Mitigation: document clearly that `--quick` mode (one fixture, skip UI) is fine for rapid local iteration; the full gate is what runs in CI on PR.

## Migration Plan

1. Land the portable corpus + analyzer baseline snapshot first in a standalone PR (no gate wiring yet). This lets the baseline stabilize before being gated on.
2. Land the `gate` subcommand second, with UI suite initially skipped. Wire `.github/workflows/evaluate.yml` to run `gate` instead of `check`; verify it passes on a few clean PRs.
3. Land the UI suite third, starting with one happy-path flow (upload → analyze → view). Expand coverage iteratively once the infrastructure is stable.
4. Update `CLAUDE.md` to document the gate and reference it from the Design-First Gate section.
5. Rollback plan: revert in reverse order. The existing `xlight-evaluate check` stays functional throughout.

## Resolved Questions (decided 2026-04-24)

- **Playwright:** YES — use Playwright + `pytest-playwright` for UI flow testing.
- **Corpus:** reuse existing `tests/fixtures/cc0_music/` download-on-demand pattern (5 CC0 tracks, no commits, CI downloads once). Optional `~/.xlight/eval_corpus.json` for local augmentation with user's own songs.
- **Tauri UI coverage:** OUT of scope for this change. Web UI + generator `.xsq` output is sufficient coverage — Tauri-specific behavior gets its own suite later if needed.
- **Auto-run from archive:** NO — documentation-only. The gate is developer-invoked locally and enforced in CI; `/opsx:archive` just mentions it.
- **One baseline.json per layer:** YES — single `tests/golden/analyzer/baseline.json` file, parallel to the existing single-file generator baseline.

## Remaining Open Questions

- **Corpus size (5 tracks) vs subset for --quick mode:** the full corpus is 5 tracks. `--quick` mode uses one. Is there a middle tier ("small corpus = 2 tracks for 5-minute CI, full corpus = 5 tracks for 15-minute PR gate")? **Recommendation:** start with one-vs-five; add a middle tier only if CI budget pressure demands it.
- **Cache strategy for downloaded CC0 MP3s in CI:** use `actions/cache@v4` keyed on the download script's SHA to avoid re-downloading every run. **Recommendation:** yes, but only implement if first-run download time is a real bottleneck.
- **Fixture selection for `--quick` mode:** which single track does quick mode pick? Picking the shortest (fastest) hides regressions in longer content. Picking the longest is slow. **Recommendation:** `maple_leaf_rag.mp3` (2:59, clear section structure, medium tempo) — balances coverage and speed. Document this in the `gate --quick` help text.
