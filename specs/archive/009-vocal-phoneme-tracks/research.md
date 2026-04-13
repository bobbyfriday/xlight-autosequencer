# Research: Vocal Phoneme Timing Tracks

**Branch**: `009-vocal-phoneme-tracks` | **Date**: 2026-03-22
**Phase**: 0 — All unknowns resolved before Phase 1 design

---

## Decision 1: Speech Recognition & Word Alignment

**Decision**: Use **WhisperX** (`whisperx` PyPI package) — a pipeline combining `faster-whisper` (CTranslate2 Whisper) for transcription and `wav2vec2` for word-level forced alignment.

**Rationale**:
- Handles both audio-only (FR-006) and lyrics-assisted (FR-007) modes in one pipeline
- Word-level timestamps with high accuracy — wav2vec2 alignment achieves ±50 ms on clean speech
- Fully offline — all models run locally (FR-011)
- Python-native, pip-installable — fits existing stack
- `faster-whisper` is 4× faster than standard Whisper on CPU; a 4-minute track transcribes in ~30–60 s
- Built-in voice activity detection (VAD) suppresses output during instrumental sections (SC-006)

**Alternatives considered**:

| Tool | Reason Rejected |
|------|----------------|
| Montreal Forced Aligner (MFA) | Requires lyrics transcript — cannot do audio-only (FR-006); Kaldi backend adds complex install dependencies |
| Vosk | Smaller models, faster, but lower accuracy; no built-in word-level alignment |
| Gentle | Kaldi-based, maintenance reduced; complex install; no VAD for silence suppression |
| OpenAI Whisper (standard) | Slower than faster-whisper on CPU; no word-level alignment without additional library |

---

## Decision 2: Phoneme Decomposition

**Decision**: Use the **CMU Pronouncing Dictionary** (cmudict) to decompose each recognized word into ARPAbet phonemes, then map ARPAbet to the Papagayo mouth-shape vocabulary.

**Pipeline**:
1. WhisperX produces word-level timestamps: `[("HOLIDAY", 12720, 13530), ...]`
2. cmudict lookup: `HOLIDAY → HH AA L AH D EY`
3. ARPAbet → Papagayo mapping: `HH→etc, AA→AI, L→L, AH→AI, D→etc, EY→E`
4. Distribute time proportionally across phonemes within the word's time span, inserting short `etc` transitions between mouth-shape changes (matching observed sample data patterns)

**Rationale**:
- cmudict covers ~135,000 English words — sufficient for the vast majority of song lyrics
- ARPAbet → Papagayo mapping is well-established and deterministic
- No additional ML model needed — a simple dictionary lookup
- Matches the output structure observed in the sample `.xtiming` file

**ARPAbet → Papagayo Mapping Table**:

| Papagayo | ARPAbet Phonemes |
|----------|-----------------|
| AI | AA, AE, AH, AY, AW |
| E | EH, ER, EY |
| O | AO, OW, OY, UH |
| WQ | W, UW |
| L | L |
| MBP | M, B, P |
| FV | F, V |
| etc | All others: CH, D, DH, G, HH, JH, K, N, NG, R, S, SH, T, TH, Y, Z, ZH |

**Fallback for unknown words**: If a word is not in cmudict, generate a simple pattern: consonant→etc, vowel→AI, based on letter analysis. This handles proper nouns, slang, and non-English words with reasonable (if imperfect) mouth shapes.

**Alternatives considered**:

| Approach | Reason Rejected |
|----------|----------------|
| Phoneme-level forced alignment (wav2vec2-phoneme) | More accurate timing per phoneme, but requires a phoneme-level alignment model + IPA→Papagayo mapping; significantly more complex for marginal accuracy gain on lip-sync |
| g2p (grapheme-to-phoneme) neural model | Additional ML model; cmudict covers >95% of English words adequately |
| Skip phoneme decomposition, word-only | Doesn't meet FR-003 (Papagayo vocabulary required) |

---

## Decision 3: Lyrics-Assisted Mode (FR-007)

**Decision**: When a lyrics file is provided, replace WhisperX's auto-transcription with the provided text, then use wav2vec2 to force-align the provided words to the audio.

**Pipeline (lyrics-assisted)**:
1. Read lyrics file → normalize (strip formatting, uppercase)
2. Run WhisperX alignment-only mode with the provided text (skip transcription step)
3. Produce word-level timestamps from forced alignment
4. Proceed with cmudict phoneme decomposition as normal

**Mismatch Detection**: After alignment, compute a confidence score based on the proportion of words that received valid alignment timestamps. If fewer than 50% of provided words align successfully, flag a mismatch warning and fall back to audio-only mode.

**Rationale**:
- WhisperX supports alignment-only mode (provide text + audio → word timestamps)
- Avoids transcription errors for known lyrics
- Mismatch detection via alignment coverage is simple and reliable

---

## Decision 4: Phoneme Timing Distribution Within Words

**Decision**: Distribute phoneme durations proportionally within each word's time span, with `etc` transition markers inserted between mouth-shape changes.

**Algorithm**:
1. For word with `N` phonemes spanning `duration` ms:
   - Assign base duration: `duration / N` per phoneme
   - Vowel phonemes (AI, E, O) get 1.5× weight; consonants (etc, MBP, FV, L, WQ) get 0.75× weight
   - Insert 50 ms `etc` transition between consecutive phonemes of different categories
   - Adjust proportionally so total equals word duration
2. Round all times to nearest integer (ms)

**Rationale**:
- Matches the timing patterns observed in the sample `.xtiming` file, which shows short `etc` transitions between mouth shapes
- Weighted distribution gives vowels more screen time (they're the visible mouth shapes in lip-sync)
- Simple, deterministic, no additional ML model required

---

## Decision 5: `.xtiming` XML Generation

**Decision**: Generate XML using the `xml.etree.ElementTree` standard library module. Use the structure observed in the sample data.

**Structure**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<timings>
    <timing name="{song_name}" SourceVersion="2024.01">
        <EffectLayer>
            <!-- Layer 1: Full lyrics as single block -->
            <Effect label="{all lyrics}" starttime="{first_word_start}" endtime="{last_word_end}" />
        </EffectLayer>
        <EffectLayer>
            <!-- Layer 2: Word-level timing -->
            <Effect label="{WORD}" starttime="{start}" endtime="{end}" />
            ...
        </EffectLayer>
        <EffectLayer>
            <!-- Layer 3: Phoneme-level timing -->
            <Effect label="{PAPAGAYO}" starttime="{start}" endtime="{end}" />
            ...
        </EffectLayer>
    </timing>
</timings>
```

**Naming convention**: `timing name` is derived from the source filename, stripped of extension and sanitized (no spaces, xLights-safe characters).

**SourceVersion**: Set to `"2024.01"` (recent stable xLights version).

---

## Decision 6: Whisper Model Size

**Decision**: Default to **Whisper `base` model** for CPU-only environments. Allow override via environment variable or config for users with GPU who want higher accuracy.

**Rationale**:
- `base` model (~140 MB) balances accuracy and speed on CPU; transcribes 4-min song in ~30 s
- `medium` model (~1.5 GB) is more accurate but 3–5× slower on CPU; better for GPU users
- Model weights download on first use, cached in `~/.cache/huggingface/`
- Constitution performance baseline: "3-minute MP3 under 60 seconds" — `base` model keeps total phoneme pipeline (transcription + alignment + decomposition) under 120 s

**Alternatives**:

| Model | Size | CPU Speed (4-min song) | Reason Not Default |
|-------|------|----------------------|-------------------|
| tiny | ~39 MB | ~10 s | Too low accuracy for word boundaries |
| small | ~244 MB | ~45 s | Good alternative; slightly over budget for total pipeline |
| medium | ~1.5 GB | ~90 s | Exceeds pipeline time budget on CPU |
| large-v3 | ~3 GB | ~180 s | Too slow for CPU; GPU only |

---

## Resolved: All NEEDS CLARIFICATION

All unknowns from the spec Assumptions are resolved. No open questions remain.
