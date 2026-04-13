# Feature Specification: Vocal Phoneme Timing Tracks

**Feature Branch**: `009-vocal-phoneme-tracks`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "Vocal phoneme timing tracks for lip-sync lighting effects"

## Overview

Lighting designers who use xLights for vocal-driven shows (singing faces, lip-sync matrix effects) need timing tracks that mark individual words and mouth-shape phonemes synchronized to the vocals. Today this requires an external online tool to generate `.xtiming` files, then manual import into xLights. This feature brings that capability into xlight-autosequencer: given a song, it produces word-level and phoneme-level timing tracks using the Papagayo mouth-shape vocabulary (AI, E, O, L, WQ, MBP, FV, etc) — the same labels xLights expects for lip-sync effects — and outputs a ready-to-import `.xtiming` file alongside the standard analysis JSON.

## Clarifications

### Session 2026-03-22

- Q: Should PhonemeTrack/WordTrack extend the existing TimingTrack (onset-only) model, or be separate entity types with start+end duration marks? → A: Separate entity types — keeps existing TimingTrack model unchanged.
- Q: Should `--phonemes` automatically enable `--stems`, or require the user to pass both flags? → A: `--phonemes` implies `--stems` automatically — vocal isolation is critical for phoneme quality.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Word and Phoneme Timing from Audio (Priority: P1)

A lighting designer runs analysis on a song and receives three new timing layers: a full-lyrics layer, a word-level timing layer, and a phoneme-level (mouth-shape) timing layer. These are exported as an `.xtiming` file that drops directly into xLights without manual editing.

**Why this priority**: This is the core value. Without word/phoneme timing, the user must use an external online tool and manually import the result. Automating this locally removes that friction and satisfies the offline requirement.

**Independent Test**: Run `xlight-analyze analyze song.mp3 --phonemes` on a song with clear vocals, verify the output includes an `.xtiming` file with three EffectLayers (lyrics, words, phonemes), and confirm it imports into xLights without error.

**Acceptance Scenarios**:

1. **Given** an MP3 with intelligible vocals, **When** the user runs analysis with phoneme detection enabled, **Then** the output includes an `.xtiming` file containing three EffectLayers: full lyrics, word-level timing, and phoneme-level timing.
2. **Given** the phoneme layer, **When** the user examines the output, **Then** each phoneme mark uses the Papagayo mouth-shape vocabulary (AI, E, O, L, WQ, MBP, FV, etc) and has both a start time and end time in milliseconds.
3. **Given** a known lyric passage with a specific syllable pattern, **When** the word-level layer is examined, **Then** at least 75% of word boundaries fall within ±100 ms of their audible onset.
4. **Given** an instrumental section within a song, **When** the phoneme layer covers that section, **Then** no spurious word or phoneme marks are generated during the vocal-silent period.
5. **Given** the generated `.xtiming` file, **When** imported into xLights, **Then** the timing track appears with all three layers intact and usable for lip-sync effects.

---

### User Story 2 — Optional Lyrics Input for Improved Accuracy (Priority: P2)

A user provides a lyrics text file alongside the audio. The system uses the lyrics to improve word alignment accuracy, producing tighter phoneme boundaries compared to audio-only inference.

**Why this priority**: Audio-only transcription may struggle with uncommon words, slang, or fast delivery. Providing lyrics is a cheap accuracy boost for users who have them.

**Independent Test**: Run analysis with and without a lyrics file on the same song. Compare word boundary accuracy — the lyrics-assisted run should have equal or better alignment.

**Acceptance Scenarios**:

1. **Given** an MP3 and a matching lyrics text file, **When** the user runs analysis with both inputs, **Then** the word-level timing aligns to the provided lyrics rather than auto-transcribed text.
2. **Given** lyrics are not provided, **When** analysis runs, **Then** the system performs audio-only transcription and still produces word and phoneme timing (degraded accuracy is acceptable).
3. **Given** lyrics that do not match the audio (wrong song), **When** analysis runs, **Then** the system detects the mismatch, falls back to audio-only inference, and warns the user.

---

### User Story 3 — Phoneme Tracks in Review UI (Priority: P3)

A user opens the review UI and can see phoneme timing tracks visualized alongside other analysis tracks. Each phoneme mark displays its mouth-shape label, enabling the user to visually verify alignment before importing into xLights.

**Why this priority**: Visual review catches errors before they reach xLights. This is additive to Stories 1 and 2.

**Independent Test**: Run analysis with `--phonemes`, then open the review UI. Verify the phoneme layer renders with labeled marks and can be played back synchronized with the audio.

**Acceptance Scenarios**:

1. **Given** an analysis with phoneme tracks, **When** the user opens the review UI, **Then** the word and phoneme layers are displayed as labeled marks on the timeline.
2. **Given** the review UI, **When** the user plays audio, **Then** a playback cursor highlights the current word and phoneme marks in sync with the audio.

---

### Edge Cases

- Songs with no identifiable vocals or purely instrumental tracks — phoneme analysis should produce an empty track and warn the user.
- Vocals in non-English languages — the system should still attempt analysis, but accuracy may be reduced; the user should be informed of the language detected.
- Heavily processed vocals (heavy reverb, pitch correction, vocoder) — may reduce transcription quality.
- Rap/spoken word vs. melodic singing — phoneme boundaries are denser and faster in speech.
- Very short vocal phrases (ad-libs, backing vocals) — should still be captured if audible.
- Overlapping vocals (harmonies, duets) — the system should process the dominant vocal line.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST produce word-level and phoneme-level timing tracks from the vocal content of an audio file.
- **FR-002**: Phoneme analysis MUST operate on the isolated vocal stem (from stem separation, feature 008) when available, falling back to full-mix audio when stems are not provided.
- **FR-003**: Phoneme labels MUST use the Papagayo mouth-shape vocabulary: AI, E, O, L, WQ, MBP, FV, etc (rest/neutral).
- **FR-004**: The output MUST include an `.xtiming` XML file matching the xLights timing format with three EffectLayers: full lyrics, word-level, and phoneme-level.
- **FR-005**: Each effect in the `.xtiming` file MUST have a `label`, `starttime`, and `endtime` attribute with times in milliseconds.
- **FR-006**: Phoneme analysis MUST function without requiring the user to provide a lyrics transcript — audio-only inference is the baseline.
- **FR-007**: When a lyrics text file is provided, the system MUST use it to improve word alignment accuracy via forced alignment.
- **FR-008**: Phoneme analysis MUST be opt-in via a command-line option, leaving default analysis unchanged. Enabling phoneme analysis MUST automatically enable stem separation (the `--phonemes` flag implies `--stems`).
- **FR-009**: If phoneme analysis fails or no vocals are detected, the system MUST complete all other analysis and report a warning — it MUST NOT block the rest of the pipeline.
- **FR-010**: Word and phoneme timing data MUST also be included in the standard analysis JSON output alongside other timing tracks for use in the review UI.
- **FR-011**: The system MUST operate fully offline — no cloud transcription services.

### Key Entities

- **WordMark**: A timing mark representing a single word. Has a label (the word text, uppercased), start time, and end time in milliseconds.
- **PhonemeMark**: A timing mark representing a mouth-shape phoneme. Has a label (Papagayo category), start time, and end time in milliseconds.
- **WordTrack**: A collection of WordMarks for one audio file. Separate entity type from TimingTrack — uses start/end duration ranges rather than onset-only marks.
- **PhonemeTrack**: A collection of PhonemeMarks for one audio file. Separate entity type from TimingTrack — uses start/end duration ranges rather than onset-only marks.
- **LyricsTranscript**: An optional text input providing lyric content to improve forced alignment accuracy.
- **XTimingFile**: An XML output file in xLights `.xtiming` format containing three EffectLayers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Word boundary timing aligns within ±100 ms of audible word onset for at least 75% of words on a reference track with known lyrics.
- **SC-002**: Phoneme tracks are generated without requiring a lyrics file — audio-only inference achieves the word accuracy target above.
- **SC-003**: Providing a lyrics file improves word boundary accuracy to at least 85% of words within ±100 ms.
- **SC-004**: Phoneme analysis on a 4-minute vocal track completes in under 120 seconds.
- **SC-005**: The generated `.xtiming` file imports into xLights without modification and all three layers are recognized.
- **SC-006**: Zero spurious word or phoneme marks appear during instrumental sections lasting 5 seconds or longer.
- **SC-007**: Failure to produce phoneme tracks does not prevent any other timing tracks from being generated.

## Assumptions

- Feature 008 (stem separation) is a prerequisite — `--phonemes` automatically enables stem separation so the vocal stem is always available for phoneme analysis.
- The Papagayo mouth-shape vocabulary (AI, E, O, L, WQ, MBP, FV, etc) is the standard used by xLights for lip-sync; no custom phoneme sets are needed.
- The `.xtiming` XML format follows the xLights schema: `<timings>` root, `<timing name="...">` container, `<EffectLayer>` per layer, `<Effect label="..." starttime="..." endtime="..." />` per mark.
- Word labels are uppercased in the output (matching observed xLights convention from sample data).
- The implementation approach (local forced aligner vs. local speech recognition + phoneme mapping) will be determined during the planning/research phase; the spec is intentionally approach-agnostic.
- English vocals are the primary target; other languages may work with reduced accuracy.
- PhonemeTrack and WordTrack are separate entity types from TimingTrack. They use start/end duration ranges rather than onset-only marks. This keeps the existing 22-algorithm TimingTrack model unchanged and maps cleanly to the `.xtiming` three-layer structure.

## Out of Scope

- Full lyrics transcription as a standalone user-facing feature (the goal is timing marks, not text output).
- Speaker diarization (identifying who is singing which phrase).
- Real-time phoneme detection during playback.
- Custom phoneme vocabularies beyond the Papagayo set.
- Editing or correcting phoneme timing within this tool (users can edit in xLights after import).
- Support for video input (MP4 lip-sync) — audio track only.
