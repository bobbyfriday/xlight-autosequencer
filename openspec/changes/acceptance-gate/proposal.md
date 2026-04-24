## Why

Changes land that break working behavior in ways no existing test catches — typically in the analyzer pipeline, the generator output, or the review UI. A human is always the last stop before merge, which is slow and error-prone. The repo already has most of the machinery for an automated pre-merge check (`src/evaluation/` quality gate, `src/validation/` scorers, `tests/golden/baseline.json`, `.github/workflows/evaluate.yml`, fixture audio), but it is fragmented: generator quality is gated, analyzer output and UI behavior are not. There is no single "acceptance gate" command that runs everything and reports go/no-go before a human reviews.

## What Changes

- **Unify** existing evaluation + validation infrastructure under a single entry point (`xlight-evaluate gate` or equivalent) that runs the full acceptance suite and returns one exit code.
- **Add analyzer-level regression checks** — golden outputs for the full timing-track set (beats, downbeats, sections, onsets, vocal phonemes, etc.) compared with structural tolerance per algorithm.
- **Add UI flow regression** — automated happy-path tests that upload a fixture, navigate the analyze screen, run an analysis, and assert the result renders without errors. Screenshot-based visual regression via the existing `openwolf designqc`.
- **Wire up the existing CC0 corpus as the default** — `tests/fixtures/cc0_music/` documents 5 tracks, but only 4 are genuinely CC0 (ambient, piano, ragtime, pop/funk — all from FreePD). The fifth (`black_box_legendary.mp3`) uses the Pixabay Content License, not CC0, and is dropped from the default corpus to keep the licensing story clean. The 4 FreePD tracks become the gate's default corpus. MP3s are not committed (and stay that way — no repo bloat, no licensing worry) but CI downloads them on first run via `tests/validation/download_fixtures.py` and caches them. Each track's expected SHA-256 hash is recorded in the manifest so silent source-URL replacements fail fast instead of shifting the baseline invisibly.
- **Support an optional local corpus** — a user can point the gate at their own music library via `~/.xlight/eval_corpus.json` (parallel to the existing `tests/golden/pro_reference/manifest.json` maintainer pattern) for richer testing. Local-only, never checked in, no rights concerns.
- **Hook into the OpenSpec workflow** — document (and optionally automate) running the gate before `/opsx:archive` completes a change, and keep the existing `.github/workflows/evaluate.yml` trigger on PRs so nothing merges that breaks the gate.
- Keep existing `xlight-evaluate check` / `snapshot` / `compare` subcommands intact; `gate` is additive, wrapping them plus the new analyzer + UI suites.

Non-goals (for this change):
- Full-song regression coverage (corpus stays small — 2–3 fixtures — for CI speed).
- Visual pixel-exact UI regression (structural + sectioned-screenshot diffing only).
- Replacing pytest, Vitest, or the existing evaluation framework — this sits *on top* of them.
- Covering the Tauri desktop shell (#52) — stays out of scope; CI runs against the web review UI.

## Capabilities

### New Capabilities
- `acceptance-gate`: the single unified pre-merge check. Runs the analyzer pipeline + generator pipeline + UI flow + visual regression against a portable fixture corpus, and returns a pass/fail verdict with a structured report.
- `analyzer-baselines`: golden outputs for analyzer timing tracks (per algorithm, per fixture song) with per-track tolerance rules, stored under `tests/golden/analyzer/` and managed via a `snapshot` / `check` workflow parallel to the existing generator baseline.
- `ui-flow-regression`: automated browser-driven acceptance tests that exercise the React review UI's core flows (upload → analyze → view → export) against a running backend + frontend, integrated into the acceptance gate.

### Modified Capabilities
<!-- None — no existing specs under openspec/specs/. The existing evaluation + validation modules have no formal spec yet; they are modified in practice (wrapped by the new `gate` command) but no spec-level behavior of theirs changes in a way that needs a delta file. -->

## Impact

- **Files modified**: `src/cli/evaluate.py` (add `gate` subcommand), `.github/workflows/evaluate.yml` (run gate, not just check), `pyproject.toml` (new test-time deps if any — TBD in design).
- **Files added**:
  - `src/evaluation/acceptance_gate.py` — the orchestrator that runs analyzer + generator + UI suites and aggregates results.
  - `src/evaluation/analyzer_baseline.py` — analyzer snapshot/check logic parallel to the existing generator baseline.
  - `tests/golden/analyzer/baseline.json` — analyzer-level golden outputs.
  - `tests/fixtures/cc0_music/manifest.json` — formalized corpus manifest (genre, tempo, expected-section-count, source URL per track). README already exists.
  - `tests/ui/flows/*.spec.ts` (or `tests/ui/flows/*.py`) — UI flow tests, tool TBD in design.
  - `openspec/specs/acceptance-gate/spec.md`, `openspec/specs/analyzer-baselines/spec.md`, `openspec/specs/ui-flow-regression/spec.md` — the new capability specs.
- **New dependencies**: likely **Playwright** for UI flow tests (industry standard for browser automation, has good Python + Node bindings). Alternative is to stay with `openwolf designqc` screenshots only — flagged as an open question in design.md.
- **Runtime cost**: full gate on a ~60-second fixture is expected to take 1–3 minutes per song (analyzer is the bottleneck — vamp + madmom + demucs). With 2–3 fixtures and UI flows, the full gate should fit comfortably within a ~10-minute CI budget. Local runs can be scoped to one fixture via a `--quick` flag.
- **No breaking changes** to existing CLI, JSON schemas, or public APIs. `xlight-evaluate gate` is additive.
- **Operational impact**: the gate becomes the pre-human-review check for every PR. If the gate is flaky or slow, it becomes the bottleneck — the design must address both (determinism + budget).
