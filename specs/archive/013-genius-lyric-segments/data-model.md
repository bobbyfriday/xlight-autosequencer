# Data Model: Genius Lyric Segment Timing

**Feature**: 013-genius-lyric-segments | **Date**: 2026-03-23

## Existing Entities (unchanged)

### StructureSegment (`src/analyzer/structure.py`)

Used as the output type for each resolved segment boundary. No changes required.

| Field | Type | Description |
|-------|------|-------------|
| `label` | `str` | Section name, e.g. `"Chorus"`, `"Verse 1"`, `"Bridge"` |
| `start_ms` | `int` | Start time in milliseconds (forced-aligned from first word) |
| `end_ms` | `int` | End time in milliseconds (= next section start, or song duration) |

### SongStructure (`src/analyzer/structure.py`)

Container for all segments. The new module sets `source = "genius"` to distinguish from
librosa-derived structure.

| Field | Type | Description |
|-------|------|-------------|
| `segments` | `list[StructureSegment]` | All resolved segment boundaries, ordered by `start_ms` |
| `source` | `str` | `"genius"` when populated by this feature; `"librosa"` otherwise |

---

## New Entities (`src/analyzer/genius_segments.py`)

### LyricSegment

Intermediate in-memory entity produced by the lyric parser. Not persisted.

| Field | Type | Description |
|-------|------|-------------|
| `label` | `str` | Raw header text without brackets, e.g. `"Chorus"`, `"Verse 1"` |
| `text` | `str` | Lyric body for this section (stripped whitespace) |
| `occurrence_index` | `int` | 0-based index of this label's occurrence (first `[Chorus]` → 0, second → 1) |

**Validation rules**:
- `label` must be non-empty after bracket stripping.
- `text` may be empty (e.g., an instrumental break with a header but no lyrics); such
  segments produce a warning and are skipped for alignment.

### GeniusMatch

Represents a successful Genius API lookup. Stored transiently during a run for audit;
not directly persisted (the resolved `SongStructure` is what gets cached).

| Field | Type | Description |
|-------|------|-------------|
| `genius_id` | `int` | Genius song ID |
| `title` | `str` | Song title as returned by Genius |
| `artist` | `str` | Artist name as returned by Genius |
| `raw_lyrics` | `str` | Raw lyrics string before any stripping or parsing |

---

## Data Flow

```text
MP3 file
  │
  ├─► mutagen.EasyID3 ──────────────────► artist: str, title: str
  │                                           │
  │                                    sanitize_title()
  │                                           │
  │                                    lyricsgenius.Genius.search_song()
  │                                           │
  │                                    GeniusMatch (raw_lyrics)
  │                                           │
  │                                    strip_boilerplate()
  │                                           │
  │                                    parse_sections() ──► list[LyricSegment]
  │                                           │
  ├─► vocals stem (or full mix) ──────► whisperx.align() per section
  │                                           │
  │                              first aligned word start_ms per section
  │                                           │
  │                                    compute end_ms boundaries
  │                                           │
  │                                    list[StructureSegment]
  │                                           │
  └────────────────────────────────────► SongStructure(source="genius")
                                              │
                                    AnalysisResult.song_structure
                                              │
                                    MD5-keyed _analysis.json cache
```

---

## JSON Output Shape

`song_structure` in `_analysis.json` when populated by this feature:

```json
{
  "song_structure": {
    "source": "genius",
    "segments": [
      { "label": "Intro", "start_ms": 0, "end_ms": 14200 },
      { "label": "Verse 1", "start_ms": 14200, "end_ms": 42600 },
      { "label": "Chorus", "start_ms": 42600, "end_ms": 71400 },
      { "label": "Verse 2", "start_ms": 71400, "end_ms": 99800 },
      { "label": "Chorus", "start_ms": 99800, "end_ms": 128200 },
      { "label": "Bridge", "start_ms": 128200, "end_ms": 156600 },
      { "label": "Chorus", "start_ms": 156600, "end_ms": 210000 }
    ]
  }
}
```

Note: The same label (e.g., `"Chorus"`) can appear multiple times. Each occurrence is its
own `StructureSegment` with independent timestamps, matching the edge case defined in the spec.
