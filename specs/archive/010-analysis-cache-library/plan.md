# Implementation Plan: Analysis Cache and Song Library

**Branch**: `010-analysis-cache-library` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-analysis-cache-library/spec.md`

## Summary

Add analysis result caching and a song library browser. The existing `_analysis.json` output
file doubles as the cache, keyed by MD5 hash of the source audio stored in a new `source_hash`
field on `AnalysisResult`. Re-running `analyze` on the same file loads the cached result in
< 3 seconds. A global library index at `~/.xlight/library.json` registers every analyzed song.
The review UI home page becomes a library browser; `review song.mp3` auto-resolves to the
cached analysis for that file.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click 8+, Flask 3+ (existing); no new dependencies
**Storage**: JSON files — `_analysis.json` (existing, extended with `source_hash`); `~/.xlight/library.json` (new)
**Testing**: pytest with synthetic WAV fixtures (existing)
**Target Platform**: macOS (darwin), local machine
**Project Type**: CLI tool + local web review UI
**Performance Goals**: Cache hit completes in < 3 seconds; library page loads in < 1 second for ≤ 500 entries
**Constraints**: Fully offline; no new Python dependencies
**Scale/Scope**: Single user, local machine; up to ~500 analyzed songs in library

## Constitution Check

*Constitution version 1.0.0 — ratified 2026-03-22*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | ✅ Pass | Caching stores the output of audio analysis, not a substitute for it. First run always performs full audio analysis. `--no-cache` ensures the pipeline is always accessible. |
| II. xLights Compatibility | ✅ Pass | No change to output format or timing track schema. `source_hash` is additive metadata. |
| III. Modular Pipeline | ✅ Pass | Cache check is a new independent stage before the runner; library write is a new independent stage after. Both communicate via `AnalysisResult`. Replacing either requires changes only in `cache.py` or `library.py`. |
| IV. Test-First Development | ✅ Pass | Tests for `AnalysisCache`, `Library`, and cache pipeline written before implementation. |
| V. Simplicity First | ✅ Pass | No new dependencies. Reuses existing `_analysis.json` as cache file. Library is a flat JSON. No speculative features. |

**Complexity Tracking**: No violations. No additional justification needed.

## Project Structure

### Documentation (this feature)

```text
specs/010-analysis-cache-library/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── cli.md           # CLI schema: --no-cache, /library route, /analysis?hash=
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── analyzer/
│   └── result.py             # +source_hash: str | None field on AnalysisResult
├── cache.py                  # NEW: AnalysisCache (is_valid, load, save by MD5)
├── library.py                # NEW: Library index (~/.xlight/library.json)
├── cli.py                    # +--no-cache flag; cache check/write; review accepts audio files
└── review/
    ├── server.py             # +GET /library; +GET /analysis?hash=; update home route
    └── static/
        ├── library.html      # NEW: library browse page (replaces upload-only home)
        └── library.js        # NEW: library fetch + render + navigate to timeline

tests/
├── unit/
│   ├── test_cache.py         # NEW: AnalysisCache unit tests
│   └── test_library.py       # NEW: Library unit tests
└── integration/
    └── test_cache_pipeline.py # NEW: end-to-end cache pipeline test
```

**Structure Decision**: Single-project layout. Two new modules (`cache.py`, `library.py`) stay
at the `src/` root alongside `export.py`. New static files are in the existing `review/static/`
directory. No new packages or sub-modules needed.
