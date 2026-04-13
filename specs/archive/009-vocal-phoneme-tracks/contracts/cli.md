# CLI Contract: Vocal Phoneme Timing Tracks

**Branch**: `009-vocal-phoneme-tracks` | **Date**: 2026-03-22

---

## Modified Command: `xlight-analyze analyze`

### New Options

```
--phonemes / --no-phonemes    Enable vocal phoneme analysis. Implies --stems.
                              Default: disabled.
--lyrics PATH                 Optional lyrics text file for improved accuracy.
                              Only used when --phonemes is enabled.
```

### Full Signature

```
xlight-analyze analyze [OPTIONS] AUDIO_FILE

Options:
  --stems / --no-stems       Run stem separation before analysis [default: no-stems]
  --phonemes / --no-phonemes Run vocal phoneme analysis (implies --stems) [default: no-phonemes]
  --lyrics PATH              Lyrics text file for forced alignment [optional, requires --phonemes]
  --top INTEGER              Auto-select top N tracks by quality score
  --output PATH              Output file path [default: <audio_file>_analysis.json]
  --help                     Show this message and exit.
```

### Behavior

| Scenario | Behavior |
|----------|----------|
| `analyze song.mp3` | Standard analysis (unchanged) |
| `analyze song.mp3 --phonemes` | Stem separation + standard analysis + phoneme analysis; outputs JSON + `.xtiming` |
| `analyze song.mp3 --phonemes --lyrics lyrics.txt` | Same as above but uses provided lyrics for word alignment |
| `analyze song.mp3 --stems` | Stem separation + standard analysis only (no phonemes) |
| `analyze song.mp3 --lyrics lyrics.txt` | Warning: `--lyrics` ignored without `--phonemes`; standard analysis only |
| Phoneme analysis fails | Warning printed; standard analysis completes normally |
| No vocals detected | Warning: "No vocals detected"; `.xtiming` file not written; JSON has `phoneme_result: null` |

### Console Output (with `--phonemes`)

```
Loading audio: song.mp3
Stem separation: checking cache... cache hit (a3f8c2d1)
Running 22 algorithms (stem-routed)...
  ...
Phoneme analysis:
  → Transcribing vocals (whisper base model)...
  → Aligning words to audio...
  → Decomposing 87 words into phonemes...
  → Writing song.xtiming (3 layers: lyrics, 87 words, 342 phonemes)
Analysis complete: song_analysis.json + song.xtiming
```

```
Loading audio: song.mp3
Stem separation: checking cache... cache hit (a3f8c2d1)
Running 22 algorithms (stem-routed)...
  ...
Phoneme analysis:
  → Transcribing vocals (whisper base model)...
  → Warning: No vocals detected in audio. Skipping phoneme analysis.
Analysis complete: song_analysis.json
```

```
Loading audio: song.mp3
Phoneme analysis:
  → Using provided lyrics: lyrics.txt (142 words)
  → Aligning words to audio...
  → Warning: Lyrics mismatch — only 23% of words aligned. Falling back to audio-only.
  → Transcribing vocals (whisper base model)...
  ...
```

---

## Output Files

### `.xtiming` XML (new)

Written when `--phonemes` is enabled and vocals are detected.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<timings>
    <timing name="{song_name}" SourceVersion="2024.01">
        <EffectLayer>
            <Effect label="{full lyrics text}" starttime="{first_word_start}" endtime="{last_word_end}" />
        </EffectLayer>
        <EffectLayer>
            <Effect label="{WORD}" starttime="{start}" endtime="{end}" />
            <!-- one per word -->
        </EffectLayer>
        <EffectLayer>
            <Effect label="{PAPAGAYO}" starttime="{start}" endtime="{end}" />
            <!-- one per phoneme -->
        </EffectLayer>
    </timing>
</timings>
```

- `timing name`: Source filename without extension, sanitized for xLights
- `SourceVersion`: `"2024.01"` (xLights compatibility)
- Layer 1: Single `<Effect>` with full lyrics text concatenated
- Layer 2: One `<Effect>` per word, label uppercased
- Layer 3: One `<Effect>` per Papagayo phoneme

### Analysis JSON (extended)

See `data-model.md` for the `phoneme_result` schema added to the JSON output.

---

## Backward Compatibility

- Existing analysis JSON files (without `phoneme_result`) MUST load without error. Missing field is treated as `null`.
- `--lyrics` without `--phonemes` prints a warning and is ignored (no error).
- `.xtiming` file is only written when phonemes are enabled and vocals are detected; no file is created otherwise.
