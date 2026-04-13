# Implementation Plan: Vocal Phoneme Timing Tracks

**Branch**: `009-vocal-phoneme-tracks` | **Date**: 2026-03-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-vocal-phoneme-tracks/spec.md`

## Summary

Add opt-in vocal phoneme analysis (`--phonemes` flag, implies `--stems`). WhisperX transcribes and aligns words to the vocal stem, then CMU Pronouncing Dictionary decomposes each word into ARPAbet phonemes mapped to the Papagayo mouth-shape vocabulary (AI, E, O, L, WQ, MBP, FV, etc). The result is a three-layer `.xtiming` XML file (lyrics, words, phonemes) that imports directly into xLights for lip-sync effects, plus a `phoneme_result` section in the standard analysis JSON for the review UI. An optional `--lyrics` flag enables forced alignment against user-provided lyrics for improved accuracy.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: whisperx (faster-whisper + wav2vec2), nltk cmudict, existing deps (vamp, librosa, madmom, demucs, click, Flask)
**Storage**: JSON files + `.xtiming` XML files (local filesystem)
**Testing**: pytest with fixture audio files + mocked WhisperX output
**Target Platform**: macOS (darwin), local machine
**Project Type**: CLI tool
**Performance Goals**: Phoneme analysis on a 4-minute vocal track completes in under 120 seconds (Whisper `base` model on CPU)
**Constraints**: Fully offline — no cloud transcription; Whisper model ~140 MB download on first use
**Scale/Scope**: Single user, local machine; typical songs 3–6 minutes

## Constitution Check

*Constitution version 1.0.0 — ratified 2026-03-22*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | ✅ Pass | Phoneme timing derived entirely from audio analysis of the vocal stem |
| II. xLights Compatibility | ✅ Pass | Output is `.xtiming` XML — xLights native format with Papagayo vocabulary; validated against sample data |
| III. Modular Pipeline | ✅ Pass | PhonemeAnalyzer is a new independent stage; communicates via `PhonemeResult` data contract; does not alter existing TimingTrack pipeline |
| IV. Test-First Development | ✅ Pass | Tests before implementation; fixture audio + mocked WhisperX for deterministic tests |
| V. Simplicity First | ✅ Pass | Single new module (`phonemes.py`), cmudict lookup (no extra ML models), dictionary-based phoneme mapping |

**Complexity Tracking**: No violations. No additional justification needed.

## Project Structure

### Documentation (this feature)

```text
specs/009-vocal-phoneme-tracks/
├── plan.md              # This file
├── research.md          # Phase 0 output — WhisperX, cmudict, Papagayo mapping decisions
├── data-model.md        # Phase 1 output — WordMark, PhonemeMark, PhonemeResult entities
├── quickstart.md        # Phase 1 output — developer onboarding
├── contracts/
│   └── cli.md           # CLI schema: --phonemes, --lyrics flags, .xtiming output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── analyzer/
│   ├── audio.py              # unchanged
│   ├── result.py             # +PhonemeResult | None on AnalysisResult
│   ├── runner.py             # unchanged (phoneme analysis runs separately)
│   ├── scorer.py             # unchanged
│   ├── stems.py              # unchanged (reused — --phonemes implies --stems)
│   ├── phonemes.py           # NEW: PhonemeAnalyzer, PhonemeResult, WordTrack, PhonemeTrack,
│   │                         #       WordMark, PhonemeMark, LyricsBlock, ARPAbet→Papagayo mapping,
│   │                         #       cmudict lookup, phoneme timing distribution
│   ├── xtiming.py            # NEW: XTimingWriter — generates .xtiming XML output
│   └── algorithms/           # unchanged
├── cli.py                    # +--phonemes, +--lyrics flags; wire PhonemeAnalyzer + XTimingWriter
├── export.py                 # +phoneme_result serialization/deserialization in JSON
└── review/
    ├── server.py             # +serve phoneme_result data to UI
    └── static/               # +word/phoneme track visualization on timeline

tests/
├── fixtures/
│   ├── 10s_vocals.wav        # NEW: short WAV with known lyrics for phoneme tests
│   └── expected_phonemes.json # NEW: expected PhonemeResult for fixture
├── unit/
│   ├── test_phonemes.py      # NEW: PhonemeAnalyzer, cmudict mapping, timing distribution
│   └── test_xtiming.py       # NEW: XTimingWriter XML output validation
└── integration/
    └── test_phoneme_pipeline.py  # NEW: end-to-end --phonemes analysis test
```

**Structure Decision**: Single-project layout. Two new files (`phonemes.py`, `xtiming.py`) in `src/analyzer/`; all other changes are additive to existing files.
