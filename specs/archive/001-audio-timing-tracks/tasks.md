---
description: "Task list for 001-audio-timing-tracks"
---

# Tasks: Audio Analysis and Timing Track Generation

**Input**: Design documents from `specs/001-audio-timing-tracks/`
**Constitution**: v1.0.0 — Test-First is mandatory; tests must fail before implementation begins.
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[US1/US2/US3]**: Maps to user story in spec.md
- All file paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Project initialization and directory structure.

- [X] T001 Create `pyproject.toml` with Python 3.11+ metadata and dependencies: `librosa`, `madmom`, `vamp`, `click`, `pytest`, `numpy`, `scipy`
- [X] T002 Create directory skeleton: `src/analyzer/algorithms/`, `tests/unit/`, `tests/integration/`, `tests/fixtures/`
- [X] T003 [P] Create `src/__init__.py`, `src/analyzer/__init__.py`, `src/analyzer/algorithms/__init__.py`
- [X] T004 [P] Create `tests/fixtures/README.md` documenting fixture file licenses and sources
- [X] T005 [P] Generate `tests/fixtures/beat_120bpm_10s.mp3` — 10-second synthetic clip, 120 BPM, clear quarter-note beat, royalty-free
- [X] T006 [P] Generate `tests/fixtures/ambient_10s.mp3` — 10-second ambient/drone clip with no detectable beat (edge case)
- [X] T007 [P] Configure pytest in `pyproject.toml`: `testpaths = ["tests"]`, `filterwarnings` for madmom deprecations

---

## Phase 2: Foundational

**Purpose**: Core data contracts, abstract interfaces, and infrastructure that ALL algorithm
implementations depend on. No user story work begins until this phase is complete.

**⚠️ CRITICAL**: Algorithm implementations (Phase 3) cannot start until T008–T016 are complete.

- [X] T008 Implement data classes in `src/analyzer/result.py`: `TimingMark(time_ms: int, confidence: float | None)`, `TimingTrack`, `AnalysisAlgorithm`, `AnalysisResult` per `data-model.md` schema — including `quality_score` field on `TimingTrack`
- [X] T009 [P] Write unit tests for all data classes in `tests/unit/test_result.py` — confirm they FAIL before T008 is implemented, then GREEN after
- [X] T010 [P] Implement abstract `Algorithm` base class in `src/analyzer/algorithms/base.py` — interface: `name: str`, `element_type: str`, `run(audio: np.ndarray, sample_rate: int) -> TimingTrack`; raises `NotImplementedError`; handles exceptions without crashing the runner
- [X] T011 [P] Implement quality scorer in `src/analyzer/scorer.py` — inputs: `TimingTrack`; outputs: `quality_score` float 0.0–1.0 using density + regularity formula from `research.md` Decision 8
- [X] T012 [P] Write unit tests for scorer in `tests/unit/test_scorer.py` — test density edge cases: <100ms avg (score near 0), 500ms avg (score ~1.0), >5000ms avg (score ~0.5); confirm FAIL before T011
- [X] T013 [P] Implement MP3 loader in `src/analyzer/audio.py` — `load(path: str) -> tuple[np.ndarray, int, AudioFile]`; uses `librosa.load()` as mono float32; populates `AudioFile` fields from `data-model.md`; raises `ValueError` on invalid file
- [X] T014 [P] Write unit tests for audio loader in `tests/unit/test_audio.py` — test valid MP3, invalid path, corrupt file; confirm FAIL before T013
- [X] T015 [P] Implement JSON export/import in `src/export.py` — `write(result: AnalysisResult, path: str)` and `read(path: str) -> AnalysisResult`; timestamps as ints; marks sorted ascending by `time_ms`; schema_version `"1.0"`
- [X] T016 Implement `AnalysisRunner` skeleton in `src/analyzer/runner.py` — `__init__(algorithms: list[Algorithm])`, `run(audio_path: str) -> AnalysisResult`; loads audio once via `audio.py`; iterates algorithms; catches per-algorithm failures and logs to stderr; calls scorer on each track; assembles `AnalysisResult`

**Checkpoint**: data classes, base interface, scorer, loader, exporter, and runner skeleton all implemented and passing unit tests.

---

## Phase 3: User Story 1 — Generate Timing Tracks from an MP3 (Priority: P1) 🎯 MVP

**Goal**: Given an MP3, run all 22 algorithms and write a complete JSON result file.

**Independent Test**: `xlight-analyze analyze tests/fixtures/beat_120bpm_10s.mp3` produces a JSON file
containing 22 (or fewer if Vamp plugins not installed) named timing tracks. The `qm_beats` or
`madmom_beats` track has timestamps that align with the 120 BPM beat (±50ms, ≥90% of marks).

### Tests for User Story 1 (write first — confirm RED before implementing)

- [X] T017 [P] [US1] Write failing unit tests for librosa beat algorithms in `tests/unit/test_librosa_beats.py` — assert `librosa_beats` track has ~20 marks for 10s/120BPM fixture; assert `librosa_bars` has ~5 marks; assert deterministic (run twice, same output)
- [X] T018 [P] [US1] Write failing unit tests for librosa band algorithms in `tests/unit/test_librosa_bands.py` — assert `bass`, `mid`, `treble` tracks exist with mark_count > 0 for 10s fixture; assert all time_ms are integers
- [X] T019 [P] [US1] Write failing unit tests for librosa HPSS algorithms in `tests/unit/test_librosa_hpss.py` — assert `drums` and `harmonic_peaks` tracks produced; assert `drums` has more marks than `harmonic_peaks` for beat_120bpm fixture
- [X] T020 [P] [US1] Write failing unit tests for madmom beat algorithms in `tests/unit/test_madmom_beat.py` — assert `madmom_beats` mark count ≈ `librosa_beats` mark count (within 10%) for same fixture; assert `madmom_downbeats` count ≈ `librosa_bars` count
- [X] T021 [P] [US1] Write failing unit tests for Vamp beat algorithms in `tests/unit/test_vamp_beats.py` — use `pytest.mark.skipif` when Vamp/QM plugins not installed; assert `qm_beats` count ≈ 20 and `beatroot` count ≈ 20 for beat_120bpm_10s fixture
- [X] T022 [P] [US1] Write failing unit tests for Vamp onset algorithms in `tests/unit/test_vamp_onsets.py` — skip if plugin absent; assert `qm_onsets_complex`, `qm_onsets_hfc`, `qm_onsets_phase` each produce > 0 marks; assert HFC and phase produce more marks than complex (typical behavior)
- [X] T023 [P] [US1] Write failing unit tests for Vamp structure algorithms in `tests/unit/test_vamp_structure.py` — skip if plugin absent; assert `qm_segments` produces at least 1 mark and at most 20 for a 10s clip; assert `qm_tempo_changes` mark list is JSON-serializable
- [X] T024 [P] [US1] Write failing unit tests for Vamp pitch algorithms in `tests/unit/test_vamp_pitch.py` — skip if pYIN plugin absent; assert `pyin_notes` and `pyin_pitch_changes` tracks produced with mark_count ≥ 0 (ambient fixture may yield 0 notes)
- [X] T025 [P] [US1] Write failing unit tests for Vamp harmony algorithms in `tests/unit/test_vamp_harmony.py` — skip if nnls-chroma plugin absent; assert `chord_changes` and `chroma_peaks` tracks produced; assert `chroma_peaks` has more marks than `chord_changes`
- [X] T026 [US1] Write failing integration test in `tests/integration/test_full_pipeline.py` — run full `AnalysisRunner` on `beat_120bpm_10s.mp3`; assert JSON output is valid per schema; assert at least 10 tracks present (Vamp may be absent); assert running twice produces identical JSON

### Implementation for User Story 1

- [X] T027 [P] [US1] Implement `LibrosaBeatAlgorithm` and `LibrosaBarAlgorithm` in `src/analyzer/algorithms/librosa_beats.py` — use `librosa.beat.beat_track()`; bars = every 4th beat; fix hop_length=512 for determinism
- [X] T028 [P] [US1] Implement `LibrosaBassAlgorithm`, `LibrosaMidAlgorithm`, `LibrosaTrebleAlgorithm` in `src/analyzer/algorithms/librosa_bands.py` — STFT → band energy → peak picking; frequency bands per `research.md`; configurable threshold
- [X] T029 [P] [US1] Implement `LibrosaDrumsAlgorithm` and `LibrosaHarmonicAlgorithm` in `src/analyzer/algorithms/librosa_hpss.py` — `librosa.effects.hpss()` separation; onset detection on each component
- [X] T030 [P] [US1] Implement `MadmomBeatAlgorithm` and `MadmomDownbeatAlgorithm` in `src/analyzer/algorithms/madmom_beat.py` — `RNNBeatProcessor` + `DBNBeatTrackingProcessor`; `RNNDownBeatProcessor`; mark confidence from beat activation
- [X] T031 [P] [US1] Implement `QMBeatAlgorithm` and `BeatRootAlgorithm` in `src/analyzer/algorithms/vamp_beats.py` — `vamp.collect()` with plugin keys per `contracts/cli.md`; `try/except` with `pytest.skip`-compatible detection when plugin absent
- [X] T032 [P] [US1] Implement `QMOnsetComplexAlgorithm`, `QMOnsetHFCAlgorithm`, `QMOnsetPhaseAlgorithm` in `src/analyzer/algorithms/vamp_onsets.py` — `qm-vamp-plugins:qm-onsetdetector` with method parameter per variant; graceful skip if plugin absent
- [X] T033 [P] [US1] Implement `QMSegmenterAlgorithm` and `QMTempoAlgorithm` in `src/analyzer/algorithms/vamp_structure.py` — `qm-vamp-plugins:qm-segmenter` and `qm-vamp-plugins:qm-tempotracker`; graceful skip if plugin absent
- [X] T034 [P] [US1] Implement `PYINNotesAlgorithm` and `PYINPitchChangesAlgorithm` in `src/analyzer/algorithms/vamp_pitch.py` — `pyin:pyin:notes` and `pyin:pyin:smoothedpitchtrack`; extract note onsets and pitch-change points; graceful skip if plugin absent
- [X] T035 [P] [US1] Implement `ChordinoAlgorithm` and `NNLSChromaAlgorithm` in `src/analyzer/algorithms/vamp_harmony.py` — `nnls-chroma:chordino:simplechord` and `nnls-chroma:nnls-chroma:chroma`; graceful skip if plugin absent
- [X] T036 [US1] Register all 22 algorithm instances in `src/analyzer/runner.py` `default_algorithms()` factory function — ordered list covering all tracks in `contracts/cli.md` algorithm reference table
- [X] T037 [US1] Implement `xlight-analyze analyze` CLI command in `src/cli.py` — Click subcommand; accepts `MP3_FILE`, `--output`, `--algorithms`, `--no-vamp`, `--no-madmom`, `--top N`; prints per-algorithm progress lines and scored summary table per `contracts/cli.md`; calls `AnalysisRunner` and `export.write()`; auto-writes `_top<N>.json` if `--top N` provided
- [X] T038 [US1] Run `pytest tests/unit/ tests/integration/ -v` and confirm all Phase 3 tests GREEN

**Checkpoint**: `xlight-analyze analyze <mp3>` works end-to-end. JSON output written. Summary table printed. All unit and integration tests pass.

---

## Phase 4: User Story 2 — Compare Algorithm Results and Select Best Tracks (Priority: P2)

**Goal**: User can view a scored summary of any analysis JSON and export a subset of tracks
without re-running analysis.

**Independent Test**: Given `song_analysis.json` from Phase 3, `xlight-analyze summary song_analysis.json`
prints the 22-track table sorted by quality score. `xlight-analyze export song_analysis.json --top 5`
writes `song_selected.json` containing exactly 5 tracks — the 5 with the highest quality scores.

### Tests for User Story 2 (write first — confirm RED)

- [X] T039 [P] [US2] Write failing unit tests for `summary` command in `tests/unit/test_cli_summary.py` — invoke via Click test client; assert table rows sorted descending by quality_score; assert `** HIGH DENSITY` flag on tracks with avg_interval_ms < 200; assert metadata header line present
- [X] T040 [P] [US2] Write failing unit tests for `export` command in `tests/unit/test_cli_export.py` — test `--select beats,drums` produces JSON with exactly 2 tracks; test `--top 3` produces JSON with 3 highest-scored tracks; test `--select unknown_track` exits with code 4; test missing both `--select` and `--top` exits with code 5

### Implementation for User Story 2

- [X] T041 [US2] Implement `xlight-analyze summary` CLI subcommand in `src/cli.py` — reads JSON via `export.read()`; sorts tracks by quality_score descending; formats and prints table with SCORE, NAME, TYPE, MARKS, AVG INTERVAL columns; flags HIGH DENSITY tracks; supports `--top N` to limit output
- [X] T042 [US2] Implement `xlight-analyze export` CLI subcommand in `src/cli.py` — reads JSON; accepts `--select` (names) or `--top N` (score-ranked); filters `timing_tracks` and corresponding `algorithms` entries; writes filtered `AnalysisResult` to output path; non-destructive (source JSON never modified)
- [X] T043 [US2] Run `pytest tests/unit/test_cli_summary.py tests/unit/test_cli_export.py -v` and confirm GREEN

**Checkpoint**: `summary` and `export` commands work independently of re-analysis. User can review any saved JSON and select tracks. All Phase 4 tests pass.

---

## Phase 5: User Story 3 — Element-Specific Timing Track Accuracy (Priority: P3)

**Goal**: Element-specific tracks (drums, bass, melody/pyin, chord changes) meet the 80%-within-
±100ms accuracy threshold from spec SC acceptance scenario 3.

**Independent Test**: Using a fixture with a clearly audible drum pattern, `drums` track marks
fall within ±100ms of ground-truth drum hit timestamps on ≥80% of marks. Similarly for bass
peaks and pyin note events.

### Tests for User Story 3 (write first — confirm RED)

- [ ] T044 [P] [US3] Create `tests/fixtures/drums_melody_10s.mp3` — 10-second clip with prominent drum hits on beats 1 and 3, and a distinct 4-note melody; include ground-truth annotation file `tests/fixtures/drums_melody_10s_ground_truth.json` with known drum hit timestamps and melody note onset timestamps
- [ ] T045 [P] [US3] Write accuracy validation test for `drums` track in `tests/unit/test_element_drums.py` — load `drums_melody_10s.mp3`, run `LibrosaDrumsAlgorithm`, compare output marks against ground truth; assert ≥80% of marks are within ±100ms of a ground-truth drum hit
- [ ] T046 [P] [US3] Write accuracy validation test for `pyin_notes` track in `tests/unit/test_element_melody.py` — skip if pYIN plugin absent; compare `PYINNotesAlgorithm` output against ground-truth note onsets; assert ≥80% within ±100ms
- [ ] T047 [P] [US3] Write accuracy validation tests for `bass`, `mid`, `treble` tracks in `tests/unit/test_element_frequency.py` — using a fixture with a known bass hit pattern; assert `bass` track marks occur within ±100ms of bass hits on ≥80% of marks; assert `treble` avg_interval_ms < `bass` avg_interval_ms (treble fires more frequently)

### Implementation for User Story 3

- [ ] T048 [US3] Run accuracy tests; if `drums` test fails (<80%), tune HPSS percussive margin and onset threshold in `src/analyzer/algorithms/librosa_hpss.py` until test passes
- [ ] T049 [US3] Run accuracy tests; if `bass` test fails (<80%), tune low-frequency band cutoff and peak-picking delta in `src/analyzer/algorithms/librosa_bands.py` until test passes
- [ ] T050 [US3] Run accuracy tests; if `pyin_notes` test fails (<80%), tune pYIN threshold parameter in `src/analyzer/algorithms/vamp_pitch.py` until test passes (or document limitation if pYIN accuracy is constrained by the algorithm itself)
- [ ] T051 [US3] Run `pytest tests/unit/test_element_*.py -v` and confirm all element accuracy tests GREEN (≥80% threshold met)

**Checkpoint**: All three user stories independently testable and passing. Element-specific tracks meet accuracy criteria.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, documentation, and final validation across all stories.

- [ ] T052 [P] Add `--no-vamp` and `--no-madmom` flag handling with informative warnings in `src/cli.py` — warn which tracks will be skipped; still complete with available algorithms
- [ ] T053 [P] Add graceful handling for MP3 files shorter than 10 seconds in `src/analyzer/audio.py` — log warning; algorithms still run but mark counts will be low
- [ ] T054 [P] Add handling for ambient/no-beat files in `src/analyzer/algorithms/librosa_beats.py` and `madmom_beat.py` — return empty TimingTrack with 0 marks rather than crashing when no beat is detected
- [ ] T055 [P] Update `specs/001-audio-timing-tracks/quickstart.md` with verified commands from a real test run
- [ ] T056 Run full test suite `pytest tests/ -v` and confirm all tests pass
- [ ] T057 Run determinism check: analyze same fixture twice, `diff run1.json run2.json` — confirm no output
- [ ] T058 Manually import a `_selected.json` output into xLights (manual step — documents any issues found for next feature)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user story work
- **US1 (Phase 3)**: Depends on Phase 2 completion
- **US2 (Phase 4)**: Depends on Phase 3 completion (needs a real analysis JSON to test against)
- **US3 (Phase 5)**: Depends on Phase 3 completion (algorithm implementations must exist)
- **Polish (Phase 6)**: Depends on all user story phases complete

### Within Phase 3

- T017–T026 (tests): all [P] — write all failing tests in parallel
- T027–T035 (algorithm implementations): all [P] — each is a separate file with no cross-dependencies
- T036 (register algorithms in runner): depends on T027–T035
- T037 (CLI analyze command): depends on T036
- T038 (verify GREEN): depends on T037

### Within Phase 4

- T039–T040 (tests): [P] — write in parallel
- T041–T042 (implementations): sequential (both in `src/cli.py` — edit the same file)
- T043 (verify GREEN): depends on T041–T042

### Within Phase 5

- T044–T047 (fixtures + tests): [P]
- T048–T050 (tuning): sequential — only needed if tests fail; run T051 after each tuning step
- T051 (verify GREEN): depends on T048–T050

---

## Parallel Execution Example: Phase 3

```bash
# Launch all test writing tasks together (all different files):
Task T017: tests/unit/test_librosa_beats.py
Task T018: tests/unit/test_librosa_bands.py
Task T019: tests/unit/test_librosa_hpss.py
Task T020: tests/unit/test_madmom_beat.py
Task T021: tests/unit/test_vamp_beats.py
Task T022: tests/unit/test_vamp_onsets.py
Task T023: tests/unit/test_vamp_structure.py
Task T024: tests/unit/test_vamp_pitch.py
Task T025: tests/unit/test_vamp_harmony.py

# Then launch all algorithm implementations together (all different files):
Task T027: src/analyzer/algorithms/librosa_beats.py
Task T028: src/analyzer/algorithms/librosa_bands.py
Task T029: src/analyzer/algorithms/librosa_hpss.py
Task T030: src/analyzer/algorithms/madmom_beat.py
Task T031: src/analyzer/algorithms/vamp_beats.py
Task T032: src/analyzer/algorithms/vamp_onsets.py
Task T033: src/analyzer/algorithms/vamp_structure.py
Task T034: src/analyzer/algorithms/vamp_pitch.py
Task T035: src/analyzer/algorithms/vamp_harmony.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — skip Vamp if not installed)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (data classes, scorer, runner skeleton)
3. Complete T027–T030 only (librosa + madmom algorithms — no Vamp required)
4. Complete T036 (register librosa + madmom algorithms only)
5. Complete T037 (analyze CLI command)
6. **STOP and VALIDATE**: `xlight-analyze analyze tests/fixtures/beat_120bpm_10s.mp3`
   produces a JSON with 10 tracks. Beat timestamps align with 120 BPM fixture.
7. Add Vamp algorithms (T031–T035) once Vamp plugins are installed

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 (US1) → Full 22-track analysis working → **MVP**
3. Phase 4 (US2) → Summary + export/selection working
4. Phase 5 (US3) → Element-specific accuracy validated
5. Phase 6 → Hardened, documented, manually verified in xLights

---

## Notes

- [P] tasks = different files, no incomplete-task dependencies — safe to parallelize
- [USn] label = maps to user story n in `specs/001-audio-timing-tracks/spec.md`
- Constitution requires tests written and FAILING before implementation — do not skip RED phase
- Vamp unit tests MUST use `pytest.mark.skipif` when plugin is absent — they are not failures
- Commit after each task or logical group (T017–T026 together, T027–T035 together, etc.)
- Do not tune algorithm parameters before writing the accuracy test — test drives the threshold
