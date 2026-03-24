# Quickstart: Genius Lyric Segment Timing

**Feature**: 013-genius-lyric-segments | **Date**: 2026-03-23

## Prerequisites

1. Install new dependencies:
   ```bash
   pip install mutagen lyricsgenius
   ```

2. Ensure `whisperx` is already installed (required for `--phonemes`; reused here):
   ```bash
   pip show whisperx
   ```

3. Obtain a Genius API token from [genius.com/api-clients](https://genius.com/api-clients)
   (free tier, no approval required for basic access).

4. Set the token in your environment:
   ```bash
   export GENIUS_API_TOKEN="your-token-here"
   ```

5. Verify your MP3 has ID3 tags:
   ```bash
   python -c "from mutagen.easyid3 import EasyID3; t = EasyID3('song.mp3'); print(t['artist'], t['title'])"
   ```

---

## Scenario 1: Basic Genius Analysis

Analyze a song and populate `song_structure` with Genius-derived segments:

```bash
xlight-analyze analyze "01 - Highway to Hell.mp3" --genius
```

**Expected output**:
```
Analyzing: 01 - Highway to Hell.mp3
[Genius] Fetching lyrics for "Highway to Hell" by "AC/DC"...
[Genius] Found song #171448. Parsing 8 sections.
[Genius] Aligning sections to audio...
[Genius] Aligned 7/8 sections. 1 skipped (no text).
[Genius] song_structure written (source=genius, 7 segments).
...
```

**Verify in output JSON**:
```bash
python -c "
import json
with open('analysis/01_-_Highway_to_Hell_analysis.json') as f:
    d = json.load(f)
ss = d.get('song_structure', {})
print('source:', ss.get('source'))
for seg in ss.get('segments', []):
    print(f\"  {seg['label']}: {seg['start_ms']}ms – {seg['end_ms']}ms\")
"
```

---

## Scenario 2: Genius + Stems (Best Accuracy)

Run stem separation first, then use the vocals stem for alignment:

```bash
xlight-analyze analyze "song.mp3" --stems --genius
```

With both `--stems` and `--genius`, the vocals stem is used for WhisperX alignment,
significantly improving timestamp accuracy for songs with long instrumental intros.

---

## Scenario 3: Caching Verification

Run the same song twice and confirm the second run is instant:

```bash
time xlight-analyze analyze "song.mp3" --genius   # first run: full pipeline
time xlight-analyze analyze "song.mp3" --genius   # second run: cached
```

The second run should skip the Genius fetch and alignment entirely. The output JSON's
`song_structure.source` will be `"genius"` from the cache.

To force re-analysis:
```bash
xlight-analyze analyze "song.mp3" --genius --no-cache
```

---

## Scenario 4: Missing API Token (Error Path)

```bash
unset GENIUS_API_TOKEN
xlight-analyze analyze "song.mp3" --genius
```

**Expected**: Clear error message, exit code 1:
```
ERROR: GENIUS_API_TOKEN not set. Obtain a token at genius.com/api-clients
and set: export GENIUS_API_TOKEN="<your-token>"
```

---

## Scenario 5: No Genius Match (Graceful Fallback)

Analyze a file with a deliberately incorrect title tag:

```bash
# All other timing tracks still produced; only song_structure is absent
xlight-analyze analyze "rare_live_recording.mp3" --genius
```

**Expected**:
- Exit code 0.
- `timing_tracks` fully populated.
- `song_structure` absent from JSON (or null).
- Warning in output: `"No Genius match found for 'rare live recording' by 'unknown artist'"`

---

## Scenario 6: Review UI with Genius Segments

After a successful `--genius` run, open the review UI:

```bash
xlight-analyze review analysis/song_analysis.json
```

Genius-derived segments appear as colored bands in the timeline labeled with their section
names (`Chorus`, `Verse 1`, etc.), identical to librosa-derived structure bands. No UI
code changes are required.

---

## Testing Integration Scenarios (for SC-001 validation)

To validate the ±500 ms accuracy criterion across 10 songs:

1. Select 10 songs with clean ID3 tags and known Genius matches.
2. Run `--genius` on each.
3. Open the review UI for each and compare segment start timestamps against your own
   listening judgment.
4. Record deviation per segment. At least 80% of segments must land within ±500 ms.

Note: Songs with long instrumental intros benefit strongly from `--stems` for the vocals
separation step.
