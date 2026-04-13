# Tasks: Genius Lyric Segment Timing

**Input**: Design documents from `/specs/013-genius-lyric-segments/`
**Prerequisites**: plan.md ✓ spec.md ✓ research.md ✓ data-model.md ✓ contracts/ ✓ quickstart.md ✓

**Tests**: Included — Constitution Principle IV (Test-First Development) requires tests before
implementation. All tests must fail before their corresponding implementation begins.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to ([US1], [US2], [US3])

---

## Phase 1: Setup

**Purpose**: Ensure optional dependencies are documented and installable.

- [X] T001 Document `lyricsgenius` and `mutagen` as new optional dependencies in `README.md` (add install section: `pip install lyricsgenius mutagen`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the `genius_segments.py` module scaffold and test file — shared by all
three user stories. No user story implementation can begin until this phase is complete.

**⚠️ CRITICAL**: Both files must exist before any story-phase tasks begin.

- [X] T002 [P] Create `src/analyzer/genius_segments.py` with `LyricSegment` and `GeniusMatch` dataclasses (see data-model.md for fields: `label`, `text`, `occurrence_index` for LyricSegment; `genius_id`, `title`, `artist`, `raw_lyrics` for GeniusMatch)
- [X] T003 [P] Create `tests/unit/test_genius_segments.py` scaffold with imports and shared fixtures (sample raw lyrics string with `[Chorus]`/`[Verse 1]` headers; sample ID3 tag dict)

**Checkpoint**: `src/analyzer/genius_segments.py` and `tests/unit/test_genius_segments.py` exist. All subsequent tasks can begin.

---

## Phase 3: User Story 1 — Fetch & Align Genius Segments from CLI (Priority: P1) 🎯 MVP

**Goal**: Running `xlight-analyze analyze song.mp3 --genius` reads Artist/Title from ID3 tags,
fetches verified Genius lyrics, parses section headers, force-aligns each section to the audio
via WhisperX, and writes `song_structure` (source=`"genius"`) to the output JSON.

**Independent Test**: Run `xlight-analyze analyze <tagged-mp3> --genius` on a file with valid
ID3 tags and a Genius match; confirm the output JSON contains `song_structure.source == "genius"`
with segment entries each having `label`, `start_ms`, `end_ms`. Confirm a second run returns
instantly (cached).

### Tests for User Story 1 (write first — must FAIL before implementation)

- [X] T004 [P] [US1] Write unit tests for `sanitize_title(raw_title)` covering: suffix stripping (`"Remastered 2024"`, `"Live at..."`, parentheticals), clean titles that should not change, empty result guard — in `tests/unit/test_genius_segments.py`
- [X] T005 [P] [US1] Write unit tests for `strip_boilerplate(raw_lyrics)` (removes "N Contributors" prefix line and trailing "Embed" token) and `parse_sections(lyrics)` (returns list of `LyricSegment` with correct `label`, `text`, `occurrence_index`) — in `tests/unit/test_genius_segments.py`
- [X] T006 [P] [US1] Write unit tests for `read_id3_tags(audio_path)` happy path (returns `(artist, title)` tuple) and verify the function signature is importable — in `tests/unit/test_genius_segments.py`
- [X] T007 [US1] Write a unit test for `GeniusSegmentAnalyzer.run()` happy path using `unittest.mock.patch` to mock `lyricsgenius.Genius` and `whisperx.align` — verifies the returned `SongStructure` has `source="genius"` and at least one `StructureSegment` — in `tests/unit/test_genius_segments.py`

### Implementation for User Story 1

- [X] T008 [US1] Add `sanitize_title(raw_title: str) -> str` to `src/analyzer/genius_segments.py` using multi-step regex from research.md R-004 (Remastered/Live/feat. suffixes, parentheticals, trailing ` - ...` patterns)
- [X] T009 [US1] Add `strip_boilerplate(raw_lyrics: str) -> str` and `parse_sections(lyrics: str) -> list[LyricSegment]` to `src/analyzer/genius_segments.py`; `parse_sections` uses `re.split(r'(\[.*?\])', lyrics)` to split on bracketed headers and tracks `occurrence_index` per label
- [X] T010 [US1] Add `read_id3_tags(audio_path: str) -> tuple[str, str]` to `src/analyzer/genius_segments.py` using `mutagen.easyid3.EasyID3`; raises `ValueError` with message if tags are missing (caught by caller)
- [X] T011 [US1] Add `fetch_genius_lyrics(title: str, artist: str, token: str) -> GeniusMatch | None` to `src/analyzer/genius_segments.py`; initialises `lyricsgenius.Genius(token, verbose=False, remove_section_headers=False)`; returns `None` on any failure
- [X] T012 [US1] Add `align_sections(sections: list[LyricSegment], audio_path: str, duration_s: float, vocals_path: str | None, device: str = "cpu") -> list[tuple[LyricSegment, int]]` to `src/analyzer/genius_segments.py`; loads whisperx align model once; creates dummy segment `{"text": s.text, "start": 0.0, "end": duration_s}` per section; extracts first word `start` as `start_ms`; returns `(section, start_ms)` pairs for successfully aligned sections only
- [X] T013 [US1] Add `GeniusSegmentAnalyzer` class to `src/analyzer/genius_segments.py` with `run(audio_path, token, stem_dir=None, duration_ms=0) -> tuple[SongStructure | None, list[str]]`; orchestrates: read_id3 → sanitize → fetch → strip_boilerplate → parse_sections → discover vocals stem → align_sections → compute end_ms boundaries → return `SongStructure(source="genius", segments=[...])`; returns `(None, warnings)` on any failure
- [X] T014 [US1] Add `--genius` boolean flag to `analyze_cmd` in `src/cli.py` with help text: `"Fetch section headers from Genius and align to audio timestamps (requires GENIUS_API_TOKEN env var)"`
- [X] T015 [US1] Wire `GeniusSegmentAnalyzer.run()` call in `analyze_cmd` in `src/cli.py`: after the main analysis and phoneme steps, if `--genius` and not (cache hit with `song_structure.source == "genius"`), call the analyzer and assign result to `analysis_result.song_structure`; append returned warnings to the manifest's `warnings` list
- [X] T016 [US1] Add Genius-aware cache logic to `analyze_cmd` in `src/cli.py`: check `cached_result.song_structure and cached_result.song_structure.source == "genius"` before running the Genius step; after Genius step completes, re-save the updated `AnalysisResult` to the cache JSON via `AnalysisCache.save()`

**Checkpoint**: `xlight-analyze analyze <tagged-mp3> --genius` works end-to-end with Genius match. Second run uses cache. Review UI shows labeled segments.

---

## Phase 4: User Story 2 — Genius API Key Configuration (Priority: P2)

**Goal**: `GENIUS_API_TOKEN` is read from the environment automatically; if missing, a clear
actionable error is shown and the rest of analysis proceeds normally.

**Independent Test**: Run `xlight-analyze analyze song.mp3 --genius` with `GENIUS_API_TOKEN`
unset; confirm exit code 0, clear error message containing the env var name and where to
obtain a token, and all non-Genius timing tracks present in output JSON.

### Tests for User Story 2

- [X] T017 [US2] Write unit test verifying `GeniusSegmentAnalyzer.run()` returns `(None, [warning_message])` when `token` is empty string — warning must mention `GENIUS_API_TOKEN` — in `tests/unit/test_genius_segments.py`

### Implementation for User Story 2

- [X] T018 [US2] In `analyze_cmd` in `src/cli.py`: read `os.environ.get("GENIUS_API_TOKEN", "")` at the start of the `--genius` branch; if empty, emit `click.echo("WARNING: GENIUS_API_TOKEN not set ...")` with link to genius.com/api-clients, append to warnings, and skip the Genius step (do NOT exit 1 — analysis continues per spec US2 AS-2); pass the token into `GeniusSegmentAnalyzer.run()`

**Checkpoint**: `--genius` with missing token shows clear warning and completes normally. With token set, analysis proceeds.

---

## Phase 5: User Story 3 — Graceful Fallback (Priority: P3)

**Goal**: Any failure in the Genius pipeline (missing ID3, no match, network error, no section
headers, per-section alignment failure) is caught, warned, and the rest of analysis completes
successfully with all non-Genius tracks intact.

**Independent Test**: Run `--genius` on a file with a deliberately incorrect title tag;
confirm exit code 0, timing_tracks populated, `song_structure` absent, and a warning in the
output manifest. Also test with the network disabled.

### Tests for User Story 3

- [X] T019 [P] [US3] Write unit test for missing/unreadable ID3 tags path: mock `EasyID3` to raise `ID3NoHeaderError`; verify `run()` returns `(None, [warning])` and does not raise — in `tests/unit/test_genius_segments.py`
- [X] T020 [P] [US3] Write unit test for Genius API failure: mock `Genius.search_song` to raise `Exception`; verify `run()` returns `(None, [warning])` — in `tests/unit/test_genius_segments.py`
- [X] T021 [P] [US3] Write unit test for no-section-headers: provide lyrics with no `[Header]` patterns; verify `parse_sections()` returns empty list and `run()` returns `(None, [warning])` — in `tests/unit/test_genius_segments.py`
- [X] T022 [P] [US3] Write unit test for per-section alignment failure: mock `whisperx.align` to return empty `word_segments` for one section; verify that section is skipped with a per-section warning and other sections are still returned — in `tests/unit/test_genius_segments.py`

### Implementation for User Story 3

- [X] T023 [US3] In `read_id3_tags()` in `src/analyzer/genius_segments.py`: catch `mutagen.id3.ID3NoHeaderError`, `KeyError`, and any `Exception`; raise `ValueError("Missing ID3 tags: Artist and Title required for Genius lookup")` for caller to catch
- [X] T024 [US3] In `fetch_genius_lyrics()` in `src/analyzer/genius_segments.py`: wrap all Genius API calls in try/except; return `None` with no re-raise; log the exception message in the returned warnings via `GeniusSegmentAnalyzer`
- [X] T025 [US3] In `GeniusSegmentAnalyzer.run()` in `src/analyzer/genius_segments.py`: after `parse_sections()`, if section list is empty, append warning `"No section headers found in Genius lyrics for '{title}' — skipping segment detection"` and return `(None, warnings)`
- [X] T026 [US3] In `align_sections()` in `src/analyzer/genius_segments.py`: wrap each section's `whisperx.align()` call in try/except; if `word_segments` is empty or first word has `start=None`, append a per-section warning and continue; only successfully aligned sections are returned
- [X] T027 [US3] In `analyze_cmd` in `src/cli.py`: collect all warnings returned by `GeniusSegmentAnalyzer.run()` and append them to the `manifest.warnings` list so they appear in `export_manifest.json`

**Checkpoint**: All three user stories independently pass. All failure paths produce warnings and clean output.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T028 [P] Update `README.md` with full `--genius` usage section: install steps (`pip install lyricsgenius mutagen`), `GENIUS_API_TOKEN` env var setup, example invocation, note about `--stems` for best accuracy
- [X] T029 [P] Verify vocals stem path discovery in `GeniusSegmentAnalyzer.run()` in `src/analyzer/genius_segments.py`: check `<audio_dir>/stems/vocals.mp3` and `<audio_dir>/.stems/vocals.mp3` using the existing convention from `inspect_stems()`; fall back to `audio_path` if not found; emit notice warning

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — core pipeline, no dependency on US2/US3
- **US2 (Phase 4)**: Depends on Phase 2 — can proceed independently of US1
- **US3 (Phase 5)**: Depends on Phase 3 US1 implementation (fallback paths are in the same functions)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. Core pipeline, no dependency on US2 or US3.
- **US2 (P2)**: Can start after Phase 2. Token check wires into CLI handler; can be done in parallel with US1.
- **US3 (P3)**: Depends on US1 implementation — fallback paths live inside the same functions implemented for US1.

### Within Each User Story (TDD order)

1. Write tests → confirm they FAIL
2. Implement the function/feature
3. Confirm tests PASS
4. Commit

### Parallel Opportunities

- T002 and T003 (Phase 2) can run in parallel
- T004, T005, T006 (US1 tests) can run in parallel
- T019, T020, T021, T022 (US3 tests) can run in parallel
- T028 and T029 (Polish) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests in parallel (T004, T005, T006 are independent test functions):
Task: "Write sanitize_title tests in tests/unit/test_genius_segments.py"
Task: "Write strip_boilerplate/parse_sections tests in tests/unit/test_genius_segments.py"
Task: "Write read_id3_tags tests in tests/unit/test_genius_segments.py"

# After tests written, implement in order (T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016)
# Each subsequent implementation may depend on prior functions
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003)
3. Complete Phase 3: User Story 1 (T004–T016)
4. **STOP and VALIDATE**: Run `xlight-analyze analyze <mp3> --genius`; verify segment output and caching
5. Open review UI; confirm labeled bands appear in timeline

### Incremental Delivery

1. Setup + Foundational → module scaffold ready
2. US1 → end-to-end Genius pipeline works for happy path
3. US2 → clean error handling for missing token
4. US3 → all failure paths graceful; full robustness
5. Polish → documentation and stem discovery verification

---

## Notes

- All test functions in `test_genius_segments.py` must be importable with `pytest tests/unit/test_genius_segments.py -v` before any implementation begins
- `remove_section_headers=False` is critical when initialising `lyricsgenius.Genius` — default is True, which strips the `[Chorus]` headers the entire feature depends on
- WhisperX align model is loaded once per `GeniusSegmentAnalyzer.run()` call and reused for all sections — do not load it inside the per-section loop
- Timestamps are always integers (milliseconds) per project code style
- `song_structure.source = "genius"` is the cache-hit signal for repeat `--genius` runs
