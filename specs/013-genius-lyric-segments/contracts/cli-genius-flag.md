# CLI Contract: `--genius` Flag

**Feature**: 013-genius-lyric-segments | **Date**: 2026-03-23

## Command: `xlight-analyze analyze`

### New Option

```
--genius    Enable Genius-based lyric segment detection.
            Requires GENIUS_API_TOKEN environment variable.
            Reads Artist and Title from the file's ID3 tags,
            fetches verified lyrics from Genius, and aligns
            section headers (e.g., [Chorus], [Verse 1]) to
            precise timestamps using forced word alignment.
            Results are written to song_structure in the output JSON.
```

### Full Invocation

```bash
GENIUS_API_TOKEN=<token> xlight-analyze analyze song.mp3 --genius
```

Or with other flags:

```bash
xlight-analyze analyze song.mp3 --stems --phonemes --genius --output out.json
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GENIUS_API_TOKEN` | Yes (when `--genius` is used) | Genius public API token. Obtain from genius.com/api-clients. |

### Exit Behaviour

| Condition | Exit Code | Behaviour |
|-----------|-----------|-----------|
| `--genius` used, `GENIUS_API_TOKEN` set, ID3 tags present, Genius match found | 0 | `song_structure` written to output JSON with `source = "genius"` |
| `--genius` used, `GENIUS_API_TOKEN` missing | 1 | Clear error: `"GENIUS_API_TOKEN not set. Obtain a token at genius.com/api-clients and set the environment variable."` |
| `--genius` used, ID3 tags missing | 0 | Warning emitted; Genius step skipped; all other analysis proceeds normally |
| `--genius` used, no Genius match found | 0 | Warning emitted; Genius step skipped; all other analysis proceeds normally |
| `--genius` used, network error | 0 | Warning emitted; Genius step skipped; all other analysis proceeds normally |
| `--genius` used, lyrics contain no section headers | 0 | Warning emitted; no `song_structure` written from Genius; all other analysis proceeds normally |

### Output JSON Contract

When `--genius` succeeds, the output JSON contains:

```json
{
  "song_structure": {
    "source": "genius",
    "segments": [
      {
        "label": "<section header text>",
        "start_ms": <integer milliseconds>,
        "end_ms": <integer milliseconds>
      }
    ]
  }
}
```

**Invariants**:
- `source` is `"genius"` (distinguishes from librosa-derived structure).
- `label` preserves the raw Genius header text without brackets (e.g., `"Chorus"` not `"[Chorus]"`).
- `start_ms` and `end_ms` are non-negative integers.
- Segments are ordered ascending by `start_ms`.
- Segments are contiguous: `segment[i].end_ms == segment[i+1].start_ms`.
- The last segment's `end_ms` equals the song's total duration in milliseconds.
- The same `label` may appear multiple times (e.g., three `"Chorus"` entries).

### Caching Contract

- On the first `--genius` run: full fetch + alignment executes; result saved to `_analysis.json`.
- On subsequent `--genius` runs: if the cached JSON contains `song_structure.source == "genius"`,
  the Genius step is skipped and the cached segments are returned.
- `--no-cache` forces re-fetch and re-alignment even if a Genius-sourced result is cached.
