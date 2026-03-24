# Research: Genius Lyric Segment Timing

**Feature**: 013-genius-lyric-segments | **Date**: 2026-03-23

## R-001: WhisperX Forced Alignment with Pre-Known Lyrics

**Decision**: Reuse the existing `_align_with_lyrics` pattern from `src/analyzer/phonemes.py`.

**Rationale**: The codebase already performs forced alignment with externally-provided text.
`_align_with_lyrics` creates a synthetic segment `{"text": lyrics_text, "start": 0.0,
"end": duration_s}` that spans the full song and calls `whisperx.align()`. The same pattern
applies per-section: create one synthetic segment per Genius section, align against the full
audio, and pick the first word with a non-None `start` as `start_ms` for that section header.

**Approach for segment alignment**:
1. Load audio via `whisperx.load_audio(audio_path)` (resamples to 16 kHz internally).
2. Run a brief transcription (`model.transcribe`) to detect language — OR reuse the language
   already determined by phoneme analysis if it ran first.
3. Load `whisperx.load_align_model(language_code, device)` once and reuse for all sections.
4. For each `LyricSegment`: call `whisperx.align([{"text": segment.text, "start": 0.0,
   "end": duration_s}], align_model, metadata, audio, device)`.
5. Extract `aligned["word_segments"][0]["start"]` as the section's start time in seconds.

**Edge cases**:
- If `word_segments` is empty or the first word has `start=None`, skip that section with a
  per-section warning.
- WhisperX `align()` does not guarantee every word will be located; only the first aligned
  word is needed per section.

**Alternatives considered**: Running WhisperX transcription first then re-aligning — rejected
because it requires an accurate prior transcription of song audio, which is unreliable for
heavily produced pop/rock. Dummy-segment approach bypasses this.

---

## R-002: lyricsgenius Library API

**Decision**: Use `lyricsgenius.Genius(token, verbose=False, remove_section_headers=False)`.

**Rationale**: `remove_section_headers=False` is critical — lyricsgenius strips `[Chorus]`
etc. by default. Disabling this preserves the headers needed for parsing.

**Key API surface**:
```python
genius = lyricsgenius.Genius(token, verbose=False, remove_section_headers=False)
song = genius.search_song(title, artist)   # returns None on failure
raw_lyrics = song.lyrics                   # includes headers + boilerplate
```

**Boilerplate stripping**:
- First line: often `"N Contributors to 'Song Title' Lyrics"` — strip lines matching
  `^\d+\s+Contributor`.
- Last token: often the string `"Embed"` appended without a newline — strip with
  `raw_lyrics.rstrip()` then `re.sub(r'\d*Embed\s*$', '', ...)`.
- Both strip operations are applied before header parsing.

**Rate limiting / network errors**: Wrap `genius.search_song()` in a try/except. On any
exception (network, HTTP error, timeout), log a warning and return `None`.

**Alternatives considered**: Scraping Genius HTML directly — rejected; lyricsgenius is the
standard Python library for this purpose and handles authentication, pagination, and search
ranking.

---

## R-003: mutagen ID3 Tag Reading

**Decision**: Use `mutagen.easyid3.EasyID3` for Artist and Title extraction.

**Rationale**: `EasyID3` provides a dictionary-like interface over the most common ID3 tag
fields with standardised key names (`"artist"`, `"title"`). It is lighter-weight than the
full `mutagen.id3.ID3` API for this use case.

**Error handling**:
- `EasyID3` raises `mutagen.id3.ID3NoHeaderError` if no ID3 header is present.
- Missing keys (e.g., `"artist"` not in dict) raise `KeyError`.
- Both are caught and result in a "missing ID3 tags" warning; Genius lookup is skipped.

**Code pattern**:
```python
from mutagen.easyid3 import EasyID3
try:
    tags = EasyID3(audio_path)
    artist = tags["artist"][0]
    title  = tags["title"][0]
except Exception:
    return None, "Missing or unreadable ID3 tags"
```

---

## R-004: Title Sanitisation Regex

**Decision**: Apply a multi-step regex to strip common suffixes before Genius search.

**Rationale**: Titles like "Highway to Hell (Remastered 2024)" or "Back in Black - Live" fail
Genius search because they do not match the canonical song title.

**Sanitisation steps** (applied in order):
1. Strip trailing `" - Remastered YYYY"` or similar: `re.sub(r'\s*-\s*Remastered\s*\d*', '', title, flags=re.I)`
2. Strip trailing parenthetical/bracket qualifiers: `re.sub(r'\s*[\(\[].*[\)\]]$', '', title)`
3. Strip common descriptor suffixes: `re.sub(r'\s*(feat\.|ft\.|featuring|with|live|acoustic|radio edit|explicit|demo|single)\b.*$', '', title, flags=re.I)`
4. Strip trailing ` - ` with anything after: `re.sub(r'\s*-\s*.+$', '', title)` (applied
   conservatively — only if the result is non-empty)
5. Strip whitespace: `title.strip()`

**Alternatives considered**: NLP-based title normalisation — rejected (over-engineering, no
current requirement for multilingual or fuzzy title matching).

---

## R-005: Caching Strategy — Genius Results in Existing Cache

**Decision**: Store Genius-derived `song_structure` in the existing MD5-keyed analysis JSON.
On repeat `--genius` runs, check `cached_result.song_structure.source == "genius"` to
determine whether to use the cached segments or re-run.

**Rationale**: `AnalysisResult.song_structure` is already serialised/deserialised by
`to_dict()` / `from_dict()`. No new cache file or mechanism is needed. The `source` field
on `SongStructure` distinguishes Genius-derived (`"genius"`) from librosa-derived
(`"librosa"`).

**Cache hit conditions for `--genius`**:
- Cache file exists AND source_hash matches audio MD5 AND `song_structure.source == "genius"`.

**Cache miss conditions**:
- `--no-cache` flag passed.
- Cache file does not exist.
- Source hash mismatch.
- Cached `song_structure` is None or has `source != "genius"`.

**Implementation in `analyze_cmd`**: After the existing cache load, check the above
conditions. If Genius cache hit, skip the Genius step. If miss (even if rest of analysis is
cached), run only the Genius step and update the cached JSON in place.

---

## R-006: Vocals Stem Path Discovery

**Decision**: Locate the vocals stem using the stem cache directory convention
(`.stems/<md5>/vocals.mp3` or `stems/vocals.mp3` adjacent to the audio file), falling back
to the full mix if not found.

**Rationale**: The existing `StemCache` and `inspect_stems` code already searches for stems
in `<audio_dir>/stems/` and `<audio_dir>/.stems/`. The Genius alignment module reuses this
convention rather than introducing a new path resolution mechanism.

**Fallback behaviour**: If the vocals stem does not exist, emit a warning
("Vocals stem not found — using full mix; alignment accuracy may be reduced") and use the
original audio path. This satisfies FR-006 and the edge case in the spec.

---

## R-007: Section `end_ms` Calculation

**Decision**: `end_ms` for section N = `start_ms` of section N+1. For the last section,
`end_ms` = `AnalysisResult.duration_ms`.

**Rationale**: Genius lyrics do not include explicit end timestamps. Using the next section's
start as the current section's end produces contiguous, non-overlapping segments that fill
the timeline — the same convention used by the existing `SongStructure` from librosa. Sections
where alignment failed are skipped; their time range is absorbed by adjacent sections.
