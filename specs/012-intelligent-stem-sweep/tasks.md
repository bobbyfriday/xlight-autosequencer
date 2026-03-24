# Tasks: Intelligent Stem Analysis and Automated Light Sequencing Pipeline

**Input**: Design documents from `/specs/012-intelligent-stem-sweep/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/cli.md ✓, quickstart.md ✓
**Constitution**: v1.0.0 — TDD enforced (IV); tests written before implementation

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label ([US1]–[US7])

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module stubs so tests can be written against them before implementation.

- [x] T001 Create stub files for three new modules with empty public interfaces: `src/analyzer/interaction.py`, `src/analyzer/conditioning.py`, `src/analyzer/xvc_export.py`
- [x] T002 Add all new dataclass types from data-model.md (`InteractionResult`, `LeaderTrack`, `LeaderTransition`, `TightnessResult`, `TightnessWindow`, `SidechainedCurve`, `HandoffEvent`, `StemSelection`, `ConditionedCurve`, `ValueCurveExport`, `TimingTrackExport`, `ExportManifest`) with `to_dict`/`from_dict` to `src/analyzer/result.py`
- [x] T003 Extend `AnalysisResult` with `interaction_result: Optional[InteractionResult] = None` field and update `to_dict`/`from_dict` in `src/analyzer/result.py`

**Checkpoint**: Stubs and data model in place — all story test tasks can now begin in parallel

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No user-story implementation can proceed until stubs exist and data model is defined. Phase 1 fulfills this — no additional blocking infrastructure needed beyond what already exists in the codebase.

**⚠️ CRITICAL**: User story tasks depend on T001–T003 being complete.

---

## Phase 3: User Story 1 — Stem Quality Inspection (Priority: P1) 🎯 MVP

**Goal**: Each available stem receives a KEEP/REVIEW/SKIP verdict with numerical measurements and a plain-language reason. Already largely implemented in `stem_inspector.py` — this phase writes the tests and validates correctness.

**Independent Test**: `pytest tests/unit/test_stem_inspector.py -v` — a silent stem is SKIPped, a sparse stem is REVIEWed, a full-energy stem is KEEPed, each with a matching reason string.

- [x] T004 [P] [US1] Write failing unit tests for `inspect_stems()` verdict thresholds (silent → SKIP, sparse → REVIEW, active → KEEP) in `tests/unit/test_stem_inspector.py`
- [x] T005 [P] [US1] Write failing unit tests verifying each verdict includes `reason` string referencing energy, coverage, and content character in `tests/unit/test_stem_inspector.py`
- [x] T006 [P] [US1] Write failing unit test verifying full mix is always included in results regardless of separated stems in `tests/unit/test_stem_inspector.py`
- [x] T007 [US1] Run tests against existing `inspect_stems()` in `src/analyzer/stem_inspector.py` — fix any threshold, reason-string, or full-mix-inclusion bugs until all US1 tests pass

**Checkpoint**: `stem-inspect` CLI command produces correct verdicts and reasons. US1 independently testable.

---

## Phase 4: User Story 6 — xLights Export (Priority: P1)

**Goal**: Conditioned timing and feature data is exported as `.xtiming` beat/onset files and `.xvc` value curve files that xLights can import without modification.

**Independent Test**: Export a timing track and a value curve from a known analysis result; verify the `.xtiming` has `<Effect>` elements at correct timestamps and the `.xvc` has valid XML with `data` attribute in pipe-delimited format.

### Timing Track Export Extension

- [x] T008 [P] [US6] Write failing unit tests for `write_timing_track()` in `tests/unit/test_xtiming.py` — given a `TimingTrack` with marks at known timestamps, verify `<Effect starttime="..." endtime="..." label="..."/>` elements are generated correctly
- [x] T009 [US6] Add `write_timing_track(track: TimingTrack, output_path: str, track_name: str) -> None` to `src/analyzer/xtiming.py` — exports a single `TimingTrack`'s marks as a one-layer `.xtiming` file; each mark becomes an `<Effect>` with `starttime=mark.time_ms` and `endtime=mark.time_ms + frame_duration_ms`
- [x] T010 [US6] Add `write_timing_tracks(tracks: list[TimingTrack], output_path: str) -> None` to `src/analyzer/xtiming.py` — exports multiple tracks as separate `<timing>` elements within one `.xtiming` file

### Value Curve Export

- [x] T011 [P] [US6] Write failing unit tests for `XvcExporter.write()` in `tests/unit/test_xvc_export.py` — verify root element is `<valuecurve>`, `data` attribute contains `Active=TRUE|Id=ID_VALUECURVE_XVC|Type=Custom|Min=0.00|Max=100.00|`, Values field has semicolon-separated `x:y` pairs with x in [0.00, 1.00] and y in [0.00, 100.00]
- [x] T012 [P] [US6] Write failing unit tests for macro curve export in `tests/unit/test_xvc_export.py` — full-song curve with ≤100 control points, all x values evenly distributed 0.00 to 1.00
- [x] T013 [P] [US6] Write failing unit tests for output file naming convention (`{stem}_{feature}_{qualifier}.xvc`) in `tests/unit/test_xvc_export.py`
- [x] T014 [US6] Implement `XvcExporter` class in `src/analyzer/xvc_export.py` with `write(curve: ConditionedCurve, output_path: str, segment_label: str = "", macro: bool = False) -> ValueCurveExport` — encodes values as Custom type pipe-delimited data attribute, maps frame index → x (0.00–1.00), maps value → y (0.00–100.00), writes XML with `SourceVersion="2024.01"`
- [x] T015 [US6] Implement `write_all(curves: list[ConditionedCurve], output_dir: str, song_structure=None) -> list[ValueCurveExport]` in `src/analyzer/xvc_export.py` — writes one `.xvc` per curve, adds macro curve at reduced resolution (≤100 points) per curve
- [x] T016 [US6] Add `export-xlights` CLI command to `src/cli.py` — reads analysis JSON, runs basic per-track conditioning (50ms hop, window=5 SG filter, 0-100 normalize), exports all timing tracks as `.xtiming` and feature curves as `.xvc` to `--output-dir` (default: `analysis/`), writes `export_manifest.json`

**Checkpoint**: `xlight-analyze export-xlights song_analysis.json` produces importable `.xtiming` and `.xvc` files. US6 independently testable.

---

## Phase 5: User Story 2 — Interactive Stem Selection (Priority: P2)

**Goal**: After viewing automatic verdicts, the user confirms or overrides each stem's selection through an interactive CLI prompt.

**Independent Test**: Mock stdin with one SKIP→KEEP override; verify `StemSelection.overrides` contains that stem name and subsequent analysis uses the overridden verdict.

- [x] T017 [P] [US2] Write failing unit tests for `interactive_review()` in `tests/unit/test_stem_inspector.py` — override SKIP→KEEP yields stem in `StemSelection.stems` as "keep", accept all yields no overrides, all-SKIP triggers `fallback_to_mix=True`
- [x] T018 [US2] Add `interactive_review(metrics: list[StemMetrics], auto_accept: bool = False) -> StemSelection` to `src/analyzer/stem_inspector.py` — for each stem, print verdict/rms_db/coverage/reason, prompt `[K]eep [S]kip [Enter=accept]`, record overrides, return `StemSelection`
- [x] T019 [US2] Add all-SKIP fallback logic to `interactive_review()` in `src/analyzer/stem_inspector.py` — if all stems end up SKIP, set `fallback_to_mix=True`, print warning, and include full_mix in kept stems
- [x] T020 [US2] Add `stem-review` CLI command to `src/cli.py` — runs `inspect_stems()` then `interactive_review()`, prints final selection summary

**Checkpoint**: `xlight-analyze stem-review song.mp3` presents each stem interactively. User override is reflected in printed final selection. US2 independently testable.

---

## Phase 6: User Story 3 — Intelligent Sweep Parameter Initialization (Priority: P2)

**Goal**: Selected stems' audio properties drive sweep parameter ranges, giving each algorithm values centered on measured estimates. Already implemented in `generate_sweep_configs()` — this phase validates correctness and ensures configs are saved to the analysis directory.

**Independent Test**: Provide audio with known BPM; verify generated configs for `qm_beats` contain at least three `inputtempo` values that bracket the measured BPM (one below, the estimate, one above).

- [x] T021 [P] [US3] Write failing unit tests for BPM bracketing in `tests/unit/test_stem_inspector.py` — given measured tempo, verify `_bpm_sweep()` returns [0.8×, 1.0×, 1.25×] rounded values
- [x] T022 [P] [US3] Write failing unit tests for stem affinity routing in `tests/unit/test_stem_inspector.py` — rhythmic stem (high crest) is preferred for beat/onset algorithms; tonal stem (low crest, high centroid) is preferred for pitch/harmony algorithms
- [x] T023 [P] [US3] Write failing unit tests verifying each config has a `_meta.rationale` string describing the parameter choices in `tests/unit/test_stem_inspector.py`
- [x] T024 [P] [US3] Write failing unit tests for low-energy stem sensitivity compensation — given low-RMS stem, onset detector sensitivity range is skewed higher in `tests/unit/test_stem_inspector.py`
- [x] T025 [US3] Run tests against existing `generate_sweep_configs()` in `src/analyzer/stem_inspector.py` — fix any bracketing, affinity, rationale, or sensitivity bugs until all US3 tests pass
- [x] T026 [US3] Verify `sweep-init` CLI command in `src/cli.py` saves all generated config files to the song's `analysis/` directory (not `~/.xlight/sweep_configs/`) — fix output path if needed

**Checkpoint**: `xlight-analyze sweep-init song.mp3` produces JSON config files in `analysis/` with BPM-bracketing sweep ranges and human-readable rationale. US3 independently testable.

---

## Phase 7: User Story 4 — Musical Interaction Analysis (Priority: P2)

**Goal**: Cross-stem relationships (dominant stem, kick-bass lock, vocal sidechain, melodic handoffs) produce higher-level features that drive the light sequence.

**Independent Test**: Run `analyze_interactions()` on stems with a known solo section; verify `LeaderTrack.transitions` includes a transition to the solo stem at the correct timestamp (±50ms tolerance).

- [x] T027 [P] [US4] Write failing unit tests for `compute_leader_track()` in `tests/unit/test_interaction.py` — stem with highest RMS becomes leader, 250ms hold prevents rapid switching, 6dB delta bypasses hold
- [x] T028 [P] [US4] Write failing unit tests for `compute_tightness()` in `tests/unit/test_interaction.py` — synchronized onset envelopes yield score ≥0.7 (label "unison"), unsynchronized yield ≤0.3 (label "independent"), missing bass stem returns None
- [x] T029 [P] [US4] Write failing unit tests for `compute_sidechain()` in `tests/unit/test_interaction.py` — values at drum onset frames are reduced, boost_values at those frames are increased, all values stay in 0-100 range
- [x] T030 [P] [US4] Write failing unit tests for `detect_handoffs()` in `tests/unit/test_interaction.py` — gap within 500ms between stem A offset and stem B onset yields a HandoffEvent at the midpoint with confidence > 0; gap > 1500ms yields no event
- [x] T031 [P] [US4] Write failing unit tests for `classify_other_stem()` in `tests/unit/test_interaction.py` — high spectral variance + low transient sharpness → "spatial"; high transient sharpness → "timing"; intermediate → "ambiguous"
- [x] T032 [US4] Implement `compute_leader_track(stem_audio: dict[str, np.ndarray], sample_rate: int, fps: int = 20, hold_ms: int = 250, delta_db: float = 6.0) -> LeaderTrack` in `src/analyzer/interaction.py` — per-frame RMS energy (weighted 0.7) + spectral flux (weighted 0.3), hold state machine, returns LeaderTrack with frames list and transitions
- [x] T033 [US4] Implement `compute_tightness(drums_audio: np.ndarray, bass_audio: np.ndarray, sample_rate: int, bpm: float, fps: int = 20) -> Optional[TightnessResult]` in `src/analyzer/interaction.py` — onset-envelope windowed cross-correlation (4-bar windows, 1s hop), threshold-based labeling, returns None if either stem is absent
- [x] T034 [US4] Implement `compute_sidechain(vocal_values: list[float], drum_onset_ms: list[int], fps: int = 20, depth: float = 0.4, release_frames: int = 3) -> SidechainedCurve` in `src/analyzer/interaction.py` — multiplicative gain envelope at each onset, exponential recovery, simultaneous boost_values on secondary dimension
- [x] T035 [US4] Implement `detect_handoffs(stem_energy: dict[str, np.ndarray], sample_rate: int, fps: int = 20, max_gap_ms: int = 500) -> list[HandoffEvent]` in `src/analyzer/interaction.py` — smoothed energy active/inactive masks for melodic stems, gap analysis between offset of A and onset of B, confidence based on gap duration
- [x] T036 [US4] Implement `classify_other_stem(other_audio: np.ndarray, sample_rate: int) -> str` in `src/analyzer/interaction.py` — spectral centroid variance vs onset strength ratio heuristic; returns "spatial", "timing", or "ambiguous"
- [x] T037 [US4] Implement `analyze_interactions(stem_audio: dict[str, np.ndarray], sample_rate: int, fps: int = 20, bpm: float = 120.0) -> InteractionResult` in `src/analyzer/interaction.py` — orchestrates T032–T036, handles missing drums/bass/vocals gracefully, returns complete InteractionResult

**Checkpoint**: `analyze_interactions()` returns a populated `InteractionResult` for stems extracted from a real song. US4 independently testable.

---

## Phase 8: User Story 5 — Data Conditioning for Hardware Compatibility (Priority: P3)

**Goal**: All feature curves are downsampled to target FPS, smoothed with peak preservation, and normalized to 0-100 integers before export.

**Independent Test**: Pass a raw onset-strength array with known peak values and high-frequency noise through the full conditioning pipeline; verify output has integer values in [0, 100], reduced frame-to-frame variation, and peak values within 90% of original peak.

- [x] T038 [P] [US5] Write failing unit tests for `downsample()` in `tests/unit/test_conditioning.py` — output length matches `ceil(duration_ms / (1000/fps))`, values are interpolated correctly
- [x] T039 [P] [US5] Write failing unit tests for `smooth()` in `tests/unit/test_conditioning.py` — isolated sharp peaks are preserved (≥90% of original height), frame-to-frame variation of noisy regions is reduced, output has no time lag vs input peak positions
- [x] T040 [P] [US5] Write failing unit tests for `normalize()` in `tests/unit/test_conditioning.py` — all output values integers in [0, 100], flat curve (max-min < 1%) sets `is_flat=True` and skips range expansion, dynamic curve spans 0–100
- [x] T041 [P] [US5] Write failing unit tests for `condition_curve()` in `tests/unit/test_conditioning.py` — full pipeline downsample→smooth→normalize, result is `ConditionedCurve` with correct metadata
- [x] T042 [US5] Implement `downsample(values: np.ndarray, source_sr: int, source_hop: int, target_fps: int) -> np.ndarray` in `src/analyzer/conditioning.py` using `np.interp` to resample to target frame rate
- [x] T043 [US5] Implement `smooth(values: np.ndarray, window_length: int = 5, polyorder: int = 2, peak_restore_ratio: float = 0.9) -> np.ndarray` in `src/analyzer/conditioning.py` using `scipy.signal.savgol_filter` with `scipy.signal.find_peaks` peak reinsertion
- [x] T044 [US5] Implement `normalize(values: np.ndarray) -> tuple[list[int], bool]` in `src/analyzer/conditioning.py` — linear scale to 0-100, flat-curve detection (returns is_flat=True when range < 1% of peak), `np.clip` + `np.round` to integers
- [x] T045 [US5] Implement `condition_curve(raw: np.ndarray, source_sr: int, source_hop: int, target_fps: int, name: str, stem: str, feature: str) -> ConditionedCurve` in `src/analyzer/conditioning.py` — orchestrates T042–T044, documents rounding in metadata when sample_rate doesn't divide evenly

**Checkpoint**: `condition_curve()` transforms raw librosa feature arrays into 0-100 integer sequences at 20 FPS. US5 independently testable.

---

## Phase 9: User Story 7 — Automated Full Pipeline (Priority: P3)

**Goal**: A single command runs all stages end-to-end and produces xLights-ready files.

**Independent Test**: `xlight-analyze pipeline tests/fixtures/short_clip.mp3` completes without error and produces at least one `.xtiming` and one `.xvc` file in the output directory.

- [x] T046 [US7] Write integration test in `tests/integration/test_pipeline.py` — runs `xlight-analyze pipeline` on a fixture MP3 (stems pre-separated), verifies at least one `.xtiming` and one `.xvc` file exist in output dir and both parse as valid XML
- [x] T047 [US7] Implement `run_pipeline(audio_path: str, stem_dir: str, output_dir: str, fps: int, top_n: int, interactive: bool, no_sweep: bool) -> ExportManifest` in `src/analyzer/pipeline.py` — calls `inspect_stems` → optional `interactive_review` → `generate_sweep_configs` → sweep runs → `analyze_interactions` → `condition_curve` per track → `XvcExporter` + `write_timing_tracks` → writes `export_manifest.json`
- [x] T048 [US7] Add no-stems fallback in `run_pipeline()` in `src/analyzer/pipeline.py` — if no stem directory found, skip inspection and interaction analysis, run full-mix-only analysis
- [x] T049 [US7] Add `pipeline` CLI command to `src/cli.py` with options: `--interactive`, `--stem-dir`, `--output-dir`, `--fps`, `--top`, `--scoring-config`, `--no-sweep` per `contracts/cli.md`
- [x] T050 [US7] Add pipeline summary output to `src/cli.py` — after completion, print: stems used (count and names), interaction events detected (leader transitions, handoffs, tightness windows), output file count
- [x] T051 [US7] Wire `--interactive` flag in `src/cli.py` pipeline command — pause after inspection for `interactive_review()` before sweeps and interaction analysis begin

**Checkpoint**: `xlight-analyze pipeline song.mp3` runs end-to-end, producing xLights-ready files and a printed summary. US7 independently testable.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [x] T052 [P] Run full test suite and fix any remaining failures: `pytest tests/ -v` in project root
- [x] T053 [P] Verify `export_manifest.json` contains `warnings` list with flat-curve notices and any missing-stem notices in `src/analyzer/pipeline.py`
- [x] T054 [P] Verify all exported file names follow the `{stem}_{feature}_{qualifier}.{ext}` convention from `contracts/cli.md` in `src/analyzer/xvc_export.py` and `src/analyzer/xtiming.py`
- [ ] T055 Manual import validation per `specs/012-intelligent-stem-sweep/quickstart.md` — import one `.xtiming` and one `.xvc` into xLights and confirm no errors and visible effect

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: No additional blocking tasks beyond Phase 1
- **Phases 3–9 (User Stories)**: All depend on T001–T003 (Phase 1)
  - US1, US6 (both P1) can start in parallel after Phase 1
  - US2, US3, US4 (P2) can start in parallel after Phase 1
  - US5, US7 (P3) can start after US6 (export uses conditioning)
- **Phase 10 (Polish)**: Depends on all user stories

### User Story Dependencies

| Story | Depends On | Notes |
|-------|-----------|-------|
| US1 (P1) | T001–T003 | Mostly already implemented; test-validate only |
| US6 (P1) | T001–T003 | Extends xtiming.py; new xvc_export.py |
| US2 (P2) | T001–T003 | New function in stem_inspector.py |
| US3 (P2) | T001–T003 | Mostly already implemented; test-validate only |
| US4 (P2) | T001–T003 | New interaction.py module |
| US5 (P3) | T001–T003 | New conditioning.py module |
| US7 (P3) | US1, US2, US3, US4, US5, US6 | Pipeline composes all stages |

### Within Each User Story

Tests are written first (fail), then implementation makes them pass (TDD, per Constitution IV).

---

## Parallel Execution Examples

### Phase 1 Parallel Start

```
T001 (create stubs) → T002 (add types to result.py) → T003 (extend AnalysisResult)
```

### After Phase 1: All P1 and P2 Story Tests in Parallel

```
T004/T005/T006  (US1 tests, test_stem_inspector.py)
T008            (US6 xtiming tests, test_xtiming.py)
T011/T012/T013  (US6 xvc tests, test_xvc_export.py)
T017            (US2 tests, test_stem_inspector.py)  ← same file as US1, serialize with US1 tests
T021/T022/T023/T024 (US3 tests, test_stem_inspector.py) ← same file, serialize with US1+US2
T027/T028/T029/T030/T031 (US4 tests, test_interaction.py)
```

### US4 Implementation (all different functions in interaction.py — parallel after tests pass)

```
T032 (compute_leader_track)
T033 (compute_tightness)
T034 (compute_sidechain)
T035 (detect_handoffs)
T036 (classify_other_stem)
↓
T037 (analyze_interactions — depends on T032–T036)
```

### US5 Implementation (parallel functions in conditioning.py)

```
T042 (downsample)
T043 (smooth)
T044 (normalize)
↓
T045 (condition_curve — depends on T042–T044)
```

---

## Implementation Strategy

### MVP First (US1 + US6 — both P1)

1. Complete Phase 1: T001–T003
2. Complete Phase 3 (US1): T004–T007 — validate stem inspection
3. Complete Phase 4 (US6): T008–T016 — export timing tracks and value curves
4. **STOP and VALIDATE**: Can go from analysis JSON → xLights-importable files
5. Demo this MVP before implementing interaction analysis

### Incremental Delivery

1. Setup + Data Model → Foundation ready
2. US1 + US6 → Stem inspect + xLights export (MVP demo)
3. US2 + US3 → Interactive selection + smart sweep params
4. US4 → Interaction analysis (leader, tightness, sidechain, handoffs)
5. US5 → Data conditioning (proper smoothing and normalization)
6. US7 → Full pipeline command
7. Each increment is independently testable and committable

### Already-Implemented Shortcuts

The codebase already has significant implementation for US1 and US3 in `src/analyzer/stem_inspector.py`. Tasks T007 and T025–T026 validate the existing code rather than writing from scratch — expect these to be quick.

---

## Notes

- [P] tasks write to different files and have no pending dependencies
- US1 and US3 tasks are largely validation of existing code; implementation is mostly done
- US4 (`interaction.py`) is the most complex new module — allocate most effort here
- The xvc Custom format: Y values are on 0–100 scale (not 0–1); confirmed from xLights source
- All timestamps must be `int` (milliseconds) — never float, per existing code style
- Commit after each user story checkpoint
