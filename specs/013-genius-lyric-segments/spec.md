# Feature Specification: Genius Lyric Segment Timing

**Feature Branch**: `013-genius-lyric-segments`
**Created**: 2026-03-23
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Fetch & Align Genius Segments from CLI (Priority: P1)

A user runs an analysis command on an MP3 that has valid ID3 tags. The system automatically reads the artist and title, fetches verified lyrics from Genius, parses section headers (`[Chorus]`, `[Verse 1]`, etc.) as segment boundaries, and aligns each section to a precise timestamp using the existing vocals stem. The result is a labeled song structure in the analysis output, visible as colored bands in the review UI timeline.

**Why this priority**: This is the core value of the feature — automated, lyrics-accurate song structure detection without any manual input. Every downstream use (xLights effects that change on chorus, segment-aware sweeps) depends on this working end-to-end.

**Independent Test**: Can be fully tested by running `xlight-analyze analyze song.mp3 --genius` on a file with ID3 tags and a Genius match, verifying the output JSON contains a `song_structure` with segment labels and `start_ms` timestamps, and that those timestamps visually align with chorus/verse boundaries in the review UI.

**Acceptance Scenarios**:

1. **Given** an MP3 with `Artist` and `Title` ID3 tags and a matching Genius song, **When** the user runs analysis with `--genius`, **Then** the output contains a `song_structure` entry with one segment per Genius header, each with a `start_ms` aligned to the first word of that section.
2. **Given** a song with a long instrumental intro before the first lyric section, **When** alignment runs on the vocals stem, **Then** the first segment timestamp correctly reflects when vocals begin, not time zero.
3. **Given** the same song analyzed twice with no audio changes, **When** the second run executes, **Then** the cached result is returned without re-fetching Genius or re-running alignment.
4. **Given** an MP3 whose title contains extra text like "Remastered 2024", **When** the system searches Genius, **Then** the extra text is stripped before the search so the correct song is found.

---

### User Story 2 — Genius API Key Configuration (Priority: P2)

A user provides their Genius API token once via environment variable and all subsequent analyses use it automatically without needing to pass it on every command.

**Why this priority**: The feature is unusable without API access. Key management must be smooth enough that users do not have to think about it after initial setup.

**Independent Test**: Can be tested by setting `GENIUS_API_TOKEN` in the environment, running `--genius` analysis, and confirming Genius fetch succeeds without any extra flags. Also tested by deliberately omitting the token and confirming a clear error message is shown.

**Acceptance Scenarios**:

1. **Given** `GENIUS_API_TOKEN` is set in the environment, **When** `--genius` is used, **Then** the token is picked up automatically and no extra flags are required.
2. **Given** no token is configured, **When** `--genius` is used, **Then** the system emits a clear, actionable error message explaining how to obtain and configure a token, and analysis continues producing all non-Genius tracks normally.

---

### User Story 3 — Graceful Fallback When Genius Lookup Fails (Priority: P3)

A user runs analysis with `--genius` on a song that cannot be matched on Genius (rare live recording, incorrectly tagged file, network outage). The analysis completes successfully with all other timing tracks intact; Genius-based segment detection is skipped with a warning.

**Why this priority**: Robustness. Users must never lose their beat/onset/chord results because a lyrics lookup failed. The `--genius` flag should be safe to include in a standard analysis invocation.

**Independent Test**: Can be tested by analyzing a file with a deliberately incorrect title tag and confirming the output JSON contains `timing_tracks` but no Genius-sourced `song_structure`, plus a human-readable warning recorded in the output.

**Acceptance Scenarios**:

1. **Given** no Genius match is found for the song, **When** analysis completes, **Then** all non-Genius timing tracks are present in the output and a warning is recorded.
2. **Given** the Genius API is unreachable due to a network error, **When** analysis runs, **Then** the error is caught, a warning is emitted, and the rest of the pipeline proceeds normally.
3. **Given** Genius returns lyrics with no recognisable section headers, **When** the parser runs, **Then** a warning is recorded noting that no segments were extracted, and no `song_structure` is written.

---

### Edge Cases

- What happens when the same section label appears multiple times (e.g., three `[Chorus]` blocks)? Each occurrence produces its own timestamped segment with the same label.
- How does the system handle unusual headers like `[Outro]`, `[Bridge]`, `[Guitar Solo]`, or `[Iron Maiden speaks]`? Any bracketed header is treated as a segment boundary regardless of label text.
- What if the vocals stem does not exist (user ran analysis without `--stems`)? The system falls back to aligning against the full mix, with a notice that accuracy may be reduced.
- What if ID3 tags are missing entirely? The system warns and skips Genius lookup; analysis continues without segment detection.
- What if forced alignment cannot place a section's text anywhere in the audio (text not found)? That section is omitted from output with a per-section warning; other sections are still written.
- What if the song is entirely instrumental and has no Genius lyrics? Graceful skip with warning (covered by US3).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read `Artist` and `Title` from the MP3's ID3 tags before querying Genius.
- **FR-002**: System MUST sanitize the title before searching by stripping common suffixes (e.g., "Remastered YYYY", "Live at …", "Radio Edit", parenthetical qualifiers) to improve search hit rate.
- **FR-003**: System MUST fetch verified lyrics from Genius using the sanitized artist and title.
- **FR-004**: System MUST strip Genius boilerplate (contributor count prefix line, "Embed" suffix) from lyrics before parsing.
- **FR-005**: System MUST parse all bracketed section headers (`[…]`) from the lyrics, preserving label text and the lyric body associated with each header.
- **FR-006**: System MUST perform forced word-level alignment of each section's lyric text against the audio, preferring the vocals stem when available and falling back to the full mix otherwise.
- **FR-007**: System MUST map each section header to the timestamp of the first successfully aligned word in that section, producing a `(label, start_ms, end_ms)` record per section.
- **FR-008**: System MUST write the resulting segments into the analysis result's `song_structure` field using the same data shape as the existing structure analyser, so the review UI renders them without code changes.
- **FR-009**: System MUST cache Genius-derived segment results as part of the MD5-keyed analysis cache so repeated runs on the same file do not re-fetch or re-align.
- **FR-010**: System MUST read the Genius API token from the `GENIUS_API_TOKEN` environment variable.
- **FR-011**: System MUST expose a `--genius` flag on the `analyze` CLI command to opt in to Genius-based segment detection.
- **FR-012**: System MUST fall back gracefully — recording a warning and continuing — when: ID3 tags are missing, Genius returns no match, the network is unavailable, no section headers are found, or alignment fails for any section.
- **FR-013**: System MUST record all Genius/alignment warnings in the analysis manifest warnings list.

### Key Entities

- **LyricSegment**: A named section parsed from Genius lyrics. Attributes: `label` (raw header text, e.g. "Chorus"), `text` (the lyric body for that section), `occurrence_index` (which repetition of this label, 0-based).
- **SegmentBoundary**: A timing-resolved segment ready for output. Attributes: `label`, `start_ms`, `end_ms`. Conforms to the existing `SongStructure` segment shape.
- **GeniusMatch**: The result of a Genius API lookup. Attributes: `genius_id`, `title`, `artist`, `raw_lyrics`. Used for caching and audit trail.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For songs with clean ID3 tags and a Genius match, segment `start_ms` timestamps are within ±500 ms of the actual section boundary as perceived by a human listener, in at least 80% of sections across a representative test set of at least 10 songs.
- **SC-002**: The Genius fetch + parse + alignment step adds no more than 60 seconds to a typical 4-minute song's first-run analysis time on CPU.
- **SC-003**: When any Genius or alignment step fails, the rest of the analysis completes successfully and produces a valid output JSON 100% of the time.
- **SC-004**: Repeat runs on the same file return the cached result with zero additional time for the Genius/alignment step.
- **SC-005**: Genius-derived segments appear correctly labeled and time-aligned in the existing review UI timeline with no UI code changes required.

## Assumptions

- The existing WhisperX forced-alignment infrastructure (already used for phoneme analysis) is reused for segment alignment; this feature does not introduce a second alignment model.
- `lyricsgenius` is added as an optional dependency (like `whisperx`) — analysis without `--genius` works without it installed.
- `mutagen` is added as a lightweight dependency; it has no GPU or large-model requirements.
- The Genius public API (free tier) is sufficient for lyric fetching; no premium access is required.
- Section labels from Genius are stored as-is and not normalised (e.g., `[Verse 1]` and `[Verse]` remain distinct labels). Normalisation is a future concern.
- The feature targets the `analyze` command initially; `pipeline` command integration is a follow-on.
- Users of this feature are expected to have previously run `--stems` (or will do so as part of the same invocation) to get the best alignment accuracy; the feature degrades to full-mix alignment otherwise rather than failing.
