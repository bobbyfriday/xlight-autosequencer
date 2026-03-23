# Data Model: Analysis Cache and Song Library

**Branch**: `010-analysis-cache-library` | **Date**: 2026-03-22

---

## Existing Entities — Extensions

### AnalysisResult (extended)

Existing entity in `src/analyzer/result.py`. Gains one new field:

| Field | Type | Values | Notes |
|-------|------|--------|-------|
| `source_hash` | `str \| None` | MD5 hex digest | Set at write time; `None` for results produced before this feature. A `None` value means no cache lookup is possible — analysis always re-runs. |

**Serialization**: Written as a top-level field on the analysis JSON object. Missing field on read → `None` (backward compatible).

---

## New Entities

### LibraryEntry

One entry in the library index representing a single previously analyzed song. Stored inside `library.json` as an array element.

| Field | Type | Notes |
|-------|------|-------|
| `source_hash` | `str` | MD5 hex digest of source audio file — primary key |
| `source_file` | `str` | Absolute path to source audio file |
| `filename` | `str` | Basename of source file (e.g., `song.mp3`) |
| `analysis_path` | `str` | Absolute path to `_analysis.json` output file |
| `duration_ms` | `int` | Duration of the song in milliseconds |
| `estimated_tempo_bpm` | `float` | Estimated BPM from the analysis |
| `track_count` | `int` | Number of timing tracks in the analysis |
| `stem_separation` | `bool` | Whether stems were used in this analysis run |
| `analyzed_at` | `int` | Unix timestamp (ms) when analysis was written |

**Example**:
```json
{
  "source_hash": "a3f8c2d1e9b047f3a2c81d56f3e9b120",
  "source_file": "/Users/rob/music/song.mp3",
  "filename": "song.mp3",
  "analysis_path": "/Users/rob/music/song_analysis.json",
  "duration_ms": 214000,
  "estimated_tempo_bpm": 128.0,
  "track_count": 18,
  "stem_separation": true,
  "analyzed_at": 1742601600000
}
```

---

### LibraryIndex

The full library index file stored at `~/.xlight/library.json`.

| Field | Type | Notes |
|-------|------|-------|
| `version` | `str` | Schema version, currently `"1.0"` |
| `entries` | `list[LibraryEntry]` | All library entries, in any order |

**Example**:
```json
{
  "version": "1.0",
  "entries": [
    { "source_hash": "a3f8...", ... },
    { "source_hash": "bb91...", ... }
  ]
}
```

**Invariant**: At most one entry per `source_hash`. Upserting by `source_hash` replaces the existing entry.

---

## State Transitions

### Analysis Cache Lifecycle

```
[No output file / no source_hash]
    │
    ▼  (analyze, no --no-cache)
[Fresh analysis run]
    │
    ▼  (write _analysis.json with source_hash, upsert library)
[Cached]
    │
    ├── (analyze same file, no --no-cache)  ──▶  [Cache Hit: load JSON, skip algorithms]
    │
    ├── (source file content changes)  ──▶  [Cache Miss: MD5 mismatch → fresh run]
    │
    └── (--no-cache)  ──▶  [Forced fresh run → overwrites cache + library entry]
```

### Library Entry Lifecycle

```
[No entry] ──▶ (analyze completes) ──▶ [Entry added]
                                              │
                  (re-analyze same file) ──▶ [Entry updated: analyzed_at, track_count, stem_separation]
                                              │
                  (source file deleted)  ──▶ [Entry remains; source_file_exists = false at read time]
```

---

## JSON Schema — analysis JSON (extended)

```json
{
  "schema_version": "1.0",
  "source_file": "/abs/path/to/song.mp3",
  "source_hash": "a3f8c2d1e9b047f3a2c81d56f3e9b120",
  "filename": "song.mp3",
  "duration_ms": 214000,
  "sample_rate": 44100,
  "estimated_tempo_bpm": 128.0,
  "run_timestamp": "2026-03-22T10:00:00+00:00",
  "stem_separation": true,
  "stem_cache": "/abs/path/to/.stems/",
  "algorithms": [ ... ],
  "timing_tracks": [ ... ]
}
```

`source_hash` is new; all other fields are unchanged.

---

## Backward Compatibility

- Existing analysis JSON files without `source_hash` are loaded without error (`source_hash = None`).
- When `analyze` is run on a file whose output JSON lacks `source_hash`, it is treated as a cache miss — analysis always re-runs and the new output includes `source_hash`.
- Existing library index files without a `version` field default to `"1.0"` behaviour.
