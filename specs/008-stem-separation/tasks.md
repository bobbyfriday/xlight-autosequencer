# Tasks: Stem Separation

**Input**: Design documents from `/specs/008-stem-separation/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/cli.md ✓

**Organization**: Tasks grouped by user story for independent implementation and testing.
**Tests**: Included — constitution (IV. Test-First Development) mandates TDD with failing tests before implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Add new dependency and test fixture.

- [x] T001 Add `demucs` to project dependencies in `pyproject.toml`
- [x] T002 Add short (10s) royalty-free mixed WAV fixture at `tests/fixtures/10s_mixed.wav` for deterministic stem routing tests (note: use a real short audio file — not generated — so vamp/librosa/madmom produce reproducible output)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend existing data structures and base classes that all three user stories depend on. Must complete before any user story phase begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Add `stem_source: str` field with default `"full_mix"` to `TimingTrack` dataclass in `src/analyzer/result.py`
- [x] T004 [P] Update `export.py` to serialize `stem_source` on write and deserialize on read (missing field → `"full_mix"` for backward compatibility)
- [x] T005 [P] Add `preferred_stem: str = "full_mix"` class attribute to `Algorithm` abstract base class in `src/analyzer/algorithms/base.py`
- [x] T006 [P] Set `preferred_stem` on each algorithm class per routing table: `vamp_beats.py` → `"drums"`, `vamp_onsets.py` → `"drums"`, `vamp_pitch.py` → `"vocals"`, `vamp_harmony.py` → `"piano"`, `librosa_beats.py` → `"drums"`, `madmom_beat.py` → `"drums"` (leave `vamp_structure`, `librosa_bands`, `librosa_hpss` at `"full_mix"`)

**Checkpoint**: Foundation ready — `TimingTrack` carries `stem_source`, all algorithms declare `preferred_stem`. User story phases can now begin.

---

## Phase 3: User Story 1 — Analyze with Stem Separation (Priority: P1) 🎯 MVP

**Goal**: `xlight-analyze analyze song.mp3 --stems` separates audio into 6 stems using Demucs `htdemucs_6s`, routes algorithms to their preferred stem, and records `stem_source` on every output track.

**Independent Test**: Run `xlight-analyze analyze tests/fixtures/10s_mixed.wav --stems`, verify 6 WAV files are created in `.stems/<hash>/`, verify output JSON has `stem_source` set on every track, verify beat tracks show `"drums"`.

### Tests for User Story 1

> **Write these tests FIRST — confirm they FAIL before implementing T009–T012**

- [x] T007 [US1] Write failing unit test: `StemSeparator.separate()` returns a `StemSet` with 6 non-empty arrays and correct `sample_rate` in `tests/unit/test_stems.py`
- [x] T008 [P] [US1] Write failing integration test: `analyze --stems` on fixture produces JSON where `stem_source` is `"drums"` on beat tracks and `"vocals"` on pitch tracks in `tests/integration/test_stem_pipeline.py`

### Implementation for User Story 1

- [x] T009 [US1] Create `StemSet` dataclass (fields: `drums`, `bass`, `vocals`, `guitar`, `piano`, `other` as `np.ndarray`; `sample_rate: int`) in `src/analyzer/stems.py`
- [x] T010 [US1] Implement `StemSeparator.separate(audio_path: Path) -> StemSet` using `demucs` `htdemucs_6s` model (no caching yet — added in US2) in `src/analyzer/stems.py`
- [x] T011 [US1] Update `runner.py` `run()` to accept `stems: StemSet | None = None`; when provided, select the audio array matching each algorithm's `preferred_stem` (fall back to full-mix array when stem is `"full_mix"` or `stems is None`); set `track.stem_source = algorithm.preferred_stem`
- [x] T012 [US1] Add `--stems / --no-stems` option (default: `--no-stems`) to `xlight-analyze analyze` in `src/cli.py`; when `--stems` is passed, instantiate `StemSeparator`, call `separate()`, pass `StemSet` to `runner.run()`

**Checkpoint**: `xlight-analyze analyze song.mp3 --stems` works end-to-end. Tracks have correct `stem_source`. Tests T007–T008 pass.

---

## Phase 4: User Story 2 — Stem Caching (Priority: P2)

**Goal**: Stems are cached to disk on first run and reused on subsequent runs. Stale cache (source file changed) is detected and regenerated automatically. Separation failure falls back to full-mix analysis with a warning.

**Independent Test**: Run `--stems` twice on the same file; confirm second run prints "cache hit" and completes the separation phase in under 2 seconds. Modify the file and re-run; confirm stems are regenerated.

### Tests for User Story 2

> **Write these tests FIRST — confirm they FAIL before implementing T014–T016**

- [x] T013 [US2] Write failing unit tests for `StemCache` covering: cache miss (no dir), cache hit (hash matches), stale cache (hash mismatch → regenerate), and failed separation (fallback to full-mix) in `tests/unit/test_stems.py`

### Implementation for User Story 2

- [x] T014 [US2] Implement `StemCache` class in `src/analyzer/stems.py`: stores stems as WAV files under `.stems/<md5_hash>/` adjacent to source file; writes/reads `manifest.json` with `source_hash`, `source_path`, `created_at`, and stem file names
- [x] T015 [US2] Update `StemSeparator.separate()` to check `StemCache` before running Demucs (cache hit → load WAVs into `StemSet`, skip model); after separation → write stems to cache
- [x] T016 [US2] Wrap `StemSeparator.separate()` call in `src/cli.py` with try/except; on failure print a warning and set `stems = None` so `runner.run()` falls back to full-mix analysis

**Checkpoint**: Re-running `--stems` on the same file is instant (cache hit). Modifying the source triggers regeneration. A bad separation falls back gracefully. Tests T013 pass.

---

## Phase 5: User Story 3 — Stem Visibility (Priority: P3)

**Goal**: The `xlight-analyze summary` command shows a `Stem` column per track. The review UI displays the stem source label on each track in the timeline.

**Independent Test**: Run `xlight-analyze summary output.json` on a stem-separated analysis file and confirm the `Stem` column is present. Open the review UI on the same file and confirm stem labels appear on each track.

### Implementation for User Story 3

- [x] T017 [US3] Update `xlight-analyze summary` in `src/cli.py` to include a `Stem` column in the track table output, reading `stem_source` from each `TimingTrack`; tracks without `stem_source` (legacy files) display `full_mix`
- [x] T018 [US3] Update review UI track rendering in `src/review/static/` to display the `stem_source` value as a small label badge on each track row in the timeline; handle missing `stem_source` gracefully by showing `full_mix`

**Checkpoint**: All three user stories are independently functional and testable. Tests pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T019 [P] Run full test suite (`pytest tests/ -v`) and confirm all tests pass including T007, T008, T013
- [x] T020 [P] Verify backward compatibility: load a pre-existing analysis JSON (no `stem_source` field) through `summary` and review UI — confirm no errors, tracks display `full_mix`
- [x] T021 Update `CLAUDE.md` Recent Changes section to document feature 008-stem-separation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — no dependency on US2 or US3
- **US2 (Phase 4)**: Depends on Phase 3 (extends `StemSeparator` built in US1)
- **US3 (Phase 5)**: Depends on Phase 2 only — `stem_source` field added in Foundational; can run in parallel with US1/US2 if desired
- **Polish (Phase 6)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no story dependencies
- **US2 (P2)**: After US1 — extends `StemSeparator` from US1
- **US3 (P3)**: After Phase 2 — independent of US1/US2 (reads `stem_source` written by runner)

### Within Each User Story

- Tests MUST be written and confirmed **FAILING** before implementation begins (constitution IV)
- `StemSet` before `StemSeparator` (T009 before T010)
- `StemSeparator` before runner integration (T010 before T011)
- Runner integration before CLI flag (T011 before T012)

### Parallel Opportunities

- T004, T005, T006 can all run in parallel (different files)
- T007, T008 can be written in parallel (different test files)
- T017, T018 can run in parallel (different files — CLI vs UI)
- T019, T020 can run in parallel

---

## Parallel Example: Foundational Phase

```
In parallel:
  T004: Update export.py for stem_source serialization
  T005: Add preferred_stem to base.Algorithm
  T006: Set preferred_stem on all algorithm classes
```

## Parallel Example: User Story 1 Tests

```
In parallel:
  T007: Unit test for StemSeparator in tests/unit/test_stems.py
  T008: Integration test for --stems pipeline in tests/integration/test_stem_pipeline.py
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `xlight-analyze analyze song.mp3 --stems` works, tracks have correct `stem_source`, tests pass
5. This is a shippable increment — caching and UI labels can follow

### Incremental Delivery

1. Setup + Foundational → data model extended
2. US1 → `--stems` works, uncached → demo-able
3. US2 → caching added → practical for daily use
4. US3 → stem labels in UI → full feature complete

---

## Notes

- [P] tasks involve different files with no blocking dependencies
- Tests are mandatory per constitution (IV. Test-First Development) — write failing tests before each implementation phase
- `htdemucs_6s` downloads model weights (~200 MB) on first use; this is expected and not an error
- If Demucs is unavailable in the test environment, mock `StemSeparator.separate()` with pre-recorded WAV fixtures for unit/integration tests
- `preferred_stem = "piano"` for `vamp_harmony` — if the piano stem is near-silent for a given song, the runner should fall back to `"other"` stem rather than passing silence to the algorithm
