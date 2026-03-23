# Data Model: Vocal Phoneme Timing Tracks

**Branch**: `009-vocal-phoneme-tracks` | **Date**: 2026-03-22

---

## New Entities

### WordMark

A single word with start/end timing, derived from WhisperX alignment.

| Field | Type | Notes |
|-------|------|-------|
| `label` | `str` | Uppercased word text (e.g., `"HOLIDAY"`) |
| `start_ms` | `int` | Start time in milliseconds |
| `end_ms` | `int` | End time in milliseconds |

---

### PhonemeMark

A single mouth-shape phoneme with start/end timing, derived from cmudict decomposition.

| Field | Type | Notes |
|-------|------|-------|
| `label` | `str` | Papagayo category: `"AI"`, `"E"`, `"O"`, `"L"`, `"WQ"`, `"MBP"`, `"FV"`, `"etc"` |
| `start_ms` | `int` | Start time in milliseconds |
| `end_ms` | `int` | End time in milliseconds |

---

### WordTrack

Collection of word-level timing marks for one audio file. Separate from `TimingTrack`.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Track identifier (e.g., `"whisperx-words"`) |
| `marks` | `list[WordMark]` | Ordered by `start_ms` |
| `lyrics_source` | `str` | `"auto"` (WhisperX transcription) or `"provided"` (user-supplied lyrics) |

---

### PhonemeTrack

Collection of phoneme-level timing marks for one audio file. Separate from `TimingTrack`.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Track identifier (e.g., `"whisperx-phonemes"`) |
| `marks` | `list[PhonemeMark]` | Ordered by `start_ms` |

---

### LyricsBlock

Full concatenated lyrics as a single block, for the first EffectLayer in the `.xtiming` file.

| Field | Type | Notes |
|-------|------|-------|
| `text` | `str` | All words joined, preserving order |
| `start_ms` | `int` | Start of first word |
| `end_ms` | `int` | End of last word |

---

### PhonemeResult

Container for all phoneme analysis output for one audio file. Wraps the three layers.

| Field | Type | Notes |
|-------|------|-------|
| `lyrics_block` | `LyricsBlock` | Layer 1: full lyrics |
| `word_track` | `WordTrack` | Layer 2: word-level timing |
| `phoneme_track` | `PhonemeTrack` | Layer 3: phoneme-level timing |
| `source_file` | `str` | Path to the source audio |
| `language` | `str` | Detected language code (e.g., `"en"`) |
| `model_name` | `str` | Whisper model used (e.g., `"base"`) |

---

## Existing Entities — No Changes

- **TimingTrack**: Unchanged. PhonemeTrack/WordTrack are separate entity types.
- **TimingMark**: Unchanged. WordMark/PhonemeMark are separate types with start+end rather than onset-only.
- **AnalysisResult**: Extended to include an optional `phoneme_result: PhonemeResult | None` field alongside the existing `tracks` list.

---

## JSON Output Changes

The existing analysis JSON gains a new top-level section:

```json
{
  "version": "1.0",
  "source_file": "song.mp3",
  "stem_separation": true,
  "tracks": [ ... ],
  "phoneme_result": {
    "lyrics_block": {
      "text": "I FOUND OUT LONG AGO ...",
      "start_ms": 5640,
      "end_ms": 117720
    },
    "word_track": {
      "name": "whisperx-words",
      "lyrics_source": "auto",
      "marks": [
        {"label": "I", "start_ms": 5640, "end_ms": 5820},
        {"label": "FOUND", "start_ms": 5820, "end_ms": 6390}
      ]
    },
    "phoneme_track": {
      "name": "whisperx-phonemes",
      "marks": [
        {"label": "AI", "start_ms": 5640, "end_ms": 5820},
        {"label": "FV", "start_ms": 5820, "end_ms": 6055},
        {"label": "O", "start_ms": 6055, "end_ms": 6290},
        {"label": "etc", "start_ms": 6290, "end_ms": 6390}
      ]
    },
    "language": "en",
    "model_name": "base"
  }
}
```

When `--phonemes` is not used, `phoneme_result` is `null` or absent. Backward-compatible: existing consumers ignore the new field.

---

## `.xtiming` Output File

Written alongside the analysis JSON when `--phonemes` is enabled:

- Filename: `{source_name}.xtiming` (e.g., `song.xtiming`)
- Location: Same directory as the analysis JSON output
- Structure: See `contracts/cli.md` for full XML schema

---

## Papagayo Vocabulary Reference

| Label | Mouth Shape | Example Sounds |
|-------|-------------|---------------|
| AI | Wide open | "ah", "eye", "I" |
| E | Mid open | "eh", "er", "ay" |
| O | Round | "oh", "ow" |
| WQ | Pursed | "w", "oo" |
| L | Tongue forward | "l" |
| MBP | Closed | "m", "b", "p" |
| FV | Teeth on lip | "f", "v" |
| etc | Neutral/rest | All other consonants, transitions |
