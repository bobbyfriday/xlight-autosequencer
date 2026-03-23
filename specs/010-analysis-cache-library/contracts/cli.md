# CLI Contract: Analysis Cache and Song Library

**Branch**: `010-analysis-cache-library` | **Date**: 2026-03-22

---

## Modified Command: `xlight-analyze analyze`

### New Option

```
--no-cache    Force re-analysis even if a cached result exists for this file.
              Default: disabled (use cache when available).
```

### Full Signature

```
xlight-analyze analyze [OPTIONS] AUDIO_FILE

Options:
  --no-cache             Re-run analysis even if cached result exists
  --stems / --no-stems   Run stem separation before analysis [default: no-stems]
  --top INTEGER          Auto-select top N tracks by quality score
  --output PATH          Output file path [default: <audio_file>_analysis.json]
  --help                 Show this message and exit.
```

### Behavior

| Scenario | Behavior |
|----------|----------|
| `analyze song.mp3` (no cache) | Run all algorithms; write `song_analysis.json`; upsert library |
| `analyze song.mp3` (cache hit) | Load `song_analysis.json`; skip algorithms; print "Cache hit" |
| `analyze song.mp3` (file changed) | MD5 mismatch → re-run; overwrite output; upsert library |
| `analyze song.mp3 --no-cache` | Re-run regardless; overwrite output + library entry |

### Console Output (cache hit)

```
Loading audio: song.mp3
Analysis cache: hit (a3f8c2d1) — skipping algorithms.
Output: song_analysis.json
```

### Console Output (cache miss / first run)

```
Loading audio: song.mp3 (3:34) | BPM: ~128.0
Analysis cache: miss — running 22 algorithms...
  [ 1/22] librosa_beats                     ... done (312 marks)
  ...
Analysis complete. Output: song_analysis.json
```

---

## Modified Command: `xlight-analyze review`

### Extended Behaviour

The `review` command now also accepts an **audio file path** (not just a JSON path).

```
xlight-analyze review [AUDIO_OR_JSON_FILE]
```

| Input | Behaviour |
|-------|-----------|
| No argument | Open review UI home page (library + upload) |
| `.json` file path | Open review timeline for that analysis (existing behaviour) |
| Audio file path (`.mp3`, `.wav`, etc.) | Look up library by MD5; open cached analysis if found |
| Audio file with no cached analysis | Error: "No cached analysis found — run 'analyze song.mp3' first." |

---

## New Flask Route: `GET /library`

Returns the full library index as JSON for the review UI home page.

### Response (200 OK)

```json
{
  "version": "1.0",
  "entries": [
    {
      "source_hash": "a3f8c2d1...",
      "source_file": "/Users/rob/music/song.mp3",
      "filename": "song.mp3",
      "analysis_path": "/Users/rob/music/song_analysis.json",
      "duration_ms": 214000,
      "estimated_tempo_bpm": 128.0,
      "track_count": 18,
      "stem_separation": true,
      "analyzed_at": 1742601600000,
      "source_file_exists": true
    }
  ]
}
```

Entries are sorted by `analyzed_at` descending (most recent first).

`source_file_exists` is computed at request time (not stored in index) by checking whether `source_file` path exists on disk.

### Response (200 OK, empty library)

```json
{
  "version": "1.0",
  "entries": []
}
```

---

## New Flask Route: `GET /analysis?hash=<md5>`

Load a specific analysis from the library by source hash. Used by the library UI when a song is selected.

### Response (200 OK)

Returns the full analysis JSON for the matching entry's `analysis_path`.

### Response (404 Not Found)

```json
{ "error": "No analysis found for hash <md5>" }
```

---

## Library Index File

**Location**: `~/.xlight/library.json`

**Format**:
```json
{
  "version": "1.0",
  "entries": [ ... ]
}
```

Created automatically on first `analyze` run. Never deleted by the tool.
