# Tasks: Vocal Phoneme Timing Tracks

**Input**: Design documents from `/specs/009-vocal-phoneme-tracks/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Included per constitution principle IV (Test-First Development).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Install new dependencies and prepare fixture data

- [ ] T001 Add whisperx and nltk to project dependencies in pyproject.toml
- [ ] T002 [P] Create test fixture audio file tests/fixtures/10s_vocals.wav (short WAV with known spoken words for deterministic tests)
- [ ] T003 [P] Create expected phoneme output fixture tests/fixtures/expected_phonemes.json (WordMarks + PhonemeMarks for the fixture audio)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data classes and mappings that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Define WordMark, PhonemeMark, WordTrack, PhonemeTrack, LyricsBlock, and PhonemeResult dataclasses in src/analyzer/phonemes.py (data-model.md entities; no logic yet)
- [ ] T005 Implement ARPAbet-to-Papagayo mapping table and cmudict lookup helper in src/analyzer/phonemes.py (research.md Decision 2 mapping table; include unknown-word fallback)
- [ ] T006 Implement phoneme timing distribution algorithm in src/analyzer/phonemes.py (research.md Decision 4: weighted duration distribution with etc transitions between mouth-shape changes)
- [ ] T007 Add optional `phoneme_result: PhonemeResult | None` field to AnalysisResult in src/analyzer/result.py

**Checkpoint**: Foundation ready — data classes, mapping, and timing distribution in place

---

## Phase 3: User Story 1 — Word and Phoneme Timing from Audio (Priority: P1) MVP

**Goal**: Run `xlight-analyze analyze song.mp3 --phonemes` and get an `.xtiming` file with three EffectLayers (lyrics, words, phonemes) plus `phoneme_result` in JSON output.

**Independent Test**: Run analysis with `--phonemes` on a song with clear vocals, verify `.xtiming` file has three layers with Papagayo labels, and verify JSON contains `phoneme_result`.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Unit tests for ARPAbet-to-Papagayo mapping and cmudict lookup in tests/unit/test_phonemes.py (verify all ARPAbet phonemes map correctly; verify unknown-word fallback)
- [ ] T009 [P] [US1] Unit tests for phoneme timing distribution in tests/unit/test_phonemes.py (verify weighted distribution sums to word duration; verify etc transitions inserted between different categories)
- [ ] T010 [P] [US1] Unit tests for PhonemeAnalyzer.analyze() in tests/unit/test_phonemes.py (mock WhisperX transcription output; verify WordTrack and PhonemeTrack produced from mock data)
- [ ] T011 [P] [US1] Unit tests for XTimingWriter in tests/unit/test_xtiming.py (verify XML structure: timings > timing > 3 EffectLayers; verify Effect attributes label/starttime/endtime; verify song name sanitization)
- [ ] T012 [P] [US1] Unit tests for phoneme_result JSON serialization/deserialization in tests/unit/test_phonemes.py (round-trip PhonemeResult through export.py; verify backward compat when phoneme_result is null/absent)

### Implementation for User Story 1

- [ ] T013 [US1] Implement PhonemeAnalyzer.analyze() in src/analyzer/phonemes.py — WhisperX transcription + wav2vec2 alignment, cmudict decomposition, timing distribution; returns PhonemeResult (research.md Decisions 1-4, 6)
- [ ] T014 [US1] Implement XTimingWriter.write() in src/analyzer/xtiming.py — generate .xtiming XML with three EffectLayers (lyrics, words, phonemes) using xml.etree.ElementTree (research.md Decision 5; contracts/cli.md XML schema)
- [ ] T015 [US1] Add phoneme_result serialization/deserialization to src/export.py (serialize PhonemeResult to JSON phoneme_result section; deserialize with backward compat for missing field)
- [ ] T016 [US1] Add --phonemes flag to CLI analyze command in src/cli.py (--phonemes implies --stems; wire PhonemeAnalyzer after stem separation; write .xtiming alongside JSON output; contracts/cli.md behavior table)
- [ ] T017 [US1] Handle edge cases in src/analyzer/phonemes.py and src/cli.py — no vocals detected (empty result + warning), phoneme analysis failure (warning, don't block other tracks), instrumental sections (no spurious marks via WhisperX VAD)
- [ ] T018 [US1] Integration test for end-to-end --phonemes analysis in tests/integration/test_phoneme_pipeline.py (run CLI with --phonemes on fixture audio; verify JSON has phoneme_result; verify .xtiming file written and valid XML)

**Checkpoint**: `xlight-analyze analyze song.mp3 --phonemes` produces valid .xtiming + JSON with phoneme_result

---

## Phase 4: User Story 2 — Optional Lyrics Input for Improved Accuracy (Priority: P2)

**Goal**: User provides a lyrics text file via `--lyrics` flag; system uses it for forced alignment instead of auto-transcription, improving word boundary accuracy.

**Independent Test**: Run analysis with `--phonemes --lyrics lyrics.txt` and verify word-level timing aligns to the provided lyrics. Run with mismatched lyrics and verify fallback to audio-only with warning.

### Tests for User Story 2

- [ ] T019 [P] [US2] Unit tests for lyrics-assisted alignment in tests/unit/test_phonemes.py (mock WhisperX alignment-only mode with provided text; verify words come from provided lyrics not auto-transcription)
- [ ] T020 [P] [US2] Unit tests for lyrics mismatch detection in tests/unit/test_phonemes.py (mock low alignment coverage < 50%; verify fallback to audio-only mode and warning returned)

### Implementation for User Story 2

- [ ] T021 [US2] Extend PhonemeAnalyzer.analyze() in src/analyzer/phonemes.py to accept lyrics_path parameter — read and normalize lyrics, use WhisperX alignment-only mode (research.md Decision 3)
- [ ] T022 [US2] Implement mismatch detection in src/analyzer/phonemes.py — compute alignment coverage; if < 50% words aligned, fall back to audio-only and return warning (research.md Decision 3)
- [ ] T023 [US2] Add --lyrics PATH option to CLI in src/cli.py — pass to PhonemeAnalyzer; warn and ignore if --phonemes not enabled (contracts/cli.md behavior table)
- [ ] T024 [US2] Add lyrics_source field tracking ("auto" vs "provided") to WordTrack serialization in src/export.py

**Checkpoint**: `--lyrics` flag works, mismatch detection falls back gracefully, lyrics_source tracked in output

---

## Phase 5: User Story 3 — Phoneme Tracks in Review UI (Priority: P3)

**Goal**: Review UI displays word and phoneme timing layers on the timeline with labeled marks, synchronized to audio playback.

**Independent Test**: Run analysis with `--phonemes`, open review UI, verify word/phoneme layers render with labels and cursor highlights current marks during playback.

### Tests for User Story 3

- [ ] T025 [P] [US3] Unit tests for phoneme data endpoint in tests/unit/test_review_server.py (verify /analysis response includes phoneme_result when present; verify absent when no phoneme data)

### Implementation for User Story 3

- [ ] T026 [US3] Extend /analysis endpoint in src/review/server.py to serve phoneme_result data (include word_track and phoneme_track in JSON response when available)
- [ ] T027 [US3] Add word/phoneme track rendering to review UI in src/review/static/ (render WordTrack and PhonemeTrack as labeled duration marks on the timeline canvas; display Papagayo labels on phoneme marks)
- [ ] T028 [US3] Add playback cursor sync for phoneme layers in src/review/static/ (highlight current word and phoneme marks during audio playback; scroll to active region)

**Checkpoint**: Review UI shows word/phoneme layers with labels, synced to playback

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T029 Update summary command output in src/cli.py to include phoneme track info (word count, phoneme count, language detected) when phoneme_result is present
- [ ] T030 Run quickstart.md validation — verify all commands from quickstart.md work end-to-end
- [ ] T031 Verify .xtiming backward compatibility — confirm existing analysis JSON files without phoneme_result load without error

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (dependencies installed) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
- **User Story 2 (Phase 4)**: Depends on Phase 3 (extends PhonemeAnalyzer from US1)
- **User Story 3 (Phase 5)**: Depends on Phase 3 (needs phoneme_result data to display)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only — core pipeline
- **US2 (P2)**: Depends on US1 — extends PhonemeAnalyzer with lyrics input
- **US3 (P3)**: Depends on US1 — needs phoneme_result in JSON to render; independent of US2

### Within Each User Story

- Tests written and FAIL before implementation
- Data classes/models before services
- Core logic before CLI wiring
- CLI wiring before integration tests

### Parallel Opportunities

**Phase 1**: T002 and T003 can run in parallel (different fixture files)
**Phase 2**: T004-T007 are sequential (each builds on prior data classes)
**Phase 3 Tests**: T008, T009, T010, T011, T012 can all run in parallel (different test focuses)
**Phase 4 Tests**: T019 and T020 can run in parallel
**US2 + US3**: US3 can start as soon as US1 completes, in parallel with US2

---

## Parallel Example: User Story 1

```
# Launch all US1 tests in parallel (write first, verify they fail):
T008: ARPAbet mapping tests in tests/unit/test_phonemes.py
T009: Timing distribution tests in tests/unit/test_phonemes.py
T010: PhonemeAnalyzer tests in tests/unit/test_phonemes.py
T011: XTimingWriter tests in tests/unit/test_xtiming.py
T012: JSON serialization tests in tests/unit/test_phonemes.py

# Then implement sequentially:
T013: PhonemeAnalyzer.analyze() in src/analyzer/phonemes.py
T014: XTimingWriter.write() in src/analyzer/xtiming.py
T015: Export serialization in src/export.py
T016: CLI --phonemes flag in src/cli.py
T017: Edge case handling
T018: Integration test
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (dependencies + fixtures)
2. Complete Phase 2: Foundational (data classes, mapping, timing distribution)
3. Complete Phase 3: User Story 1 (PhonemeAnalyzer + XTimingWriter + CLI + export)
4. **STOP and VALIDATE**: Test with a real song — verify `.xtiming` imports into xLights
5. Deliver MVP: audio-only phoneme analysis with `.xtiming` output

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. Add US1 -> Test independently -> MVP! (audio-only phoneme analysis)
3. Add US2 -> Test independently -> Lyrics-assisted accuracy boost
4. Add US3 -> Test independently -> Visual review before xLights import
5. Polish -> Quickstart validation, backward compat verification
