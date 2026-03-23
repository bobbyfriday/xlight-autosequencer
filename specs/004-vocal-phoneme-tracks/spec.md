# Feature Specification: Vocal Phoneme Timing Tracks

**Feature Branch**: `004-vocal-phoneme-tracks`
**Created**: 2026-03-22
**Status**: Placeholder
**Input**: Generate timing tracks from phoneme-level analysis of the vocal stem — each mark corresponds to a phoneme boundary or syllable onset within the lyrics, enabling lighting choreography synchronized to individual vocal sounds.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phoneme-Level Vocal Timing Tracks (Priority: P1)

A user analyzes a song and receives timing tracks where marks correspond to individual
phoneme onsets within the vocal line — not just "vocal phrase starts" but the specific
moment each consonant or vowel attack occurs. This enables lighting effects that follow
the rhythm and texture of sung words rather than just phrase boundaries.

**Why this priority**: Beat and onset tracks capture musical structure. Phoneme tracks
capture lyric rhythm — a distinct and more expressive layer for vocal-forward songs.

**Acceptance Scenarios**:

1. **Given** an MP3 with intelligible vocals, **When** phoneme analysis runs, **Then**
   the output includes at least one timing track whose marks correspond to phoneme or
   syllable boundaries in the vocal line.
2. **Given** a known lyric with a specific syllable pattern, **When** the phoneme track
   is examined, **Then** at least 75% of detected marks fall within ±80ms of expected
   syllable onsets.
3. **Given** an instrumental section, **When** phoneme analysis runs over that segment,
   **Then** no spurious marks are generated in the vocal-silent period.
4. **Given** phoneme analysis is unavailable (missing dependency or API), **When** the
   pipeline runs, **Then** it completes with all other tracks and notifies the user that
   phoneme tracks were skipped.

---

### User Story 2 - Phoneme Type Tagging (Priority: P2)

Beyond just timing, the user can see which type of phoneme each mark represents (e.g.,
consonant attack, vowel sustain, sibilant, stop). This allows lighting rules to respond
differently to different vocal textures — e.g., a flash on hard consonants vs. a hold
on open vowels.

**Why this priority**: Phoneme type metadata turns a timing track into a richer event
stream. This is additive to Story 1 and only pursued if the underlying analysis provides
type data without significant extra cost.

**Acceptance Scenarios**:

1. **Given** a phoneme timing track, **When** the user exports it, **Then** each mark
   includes a phoneme category label (at minimum: consonant / vowel / silence).
2. **Given** a song with prominent sibilant consonants, **When** the phoneme track is
   reviewed, **Then** those events carry a label that distinguishes them from vowel
   onsets.

---

### Edge Cases

- Songs with no identifiable vocals or purely instrumental tracks.
- Vocals in non-English languages (phoneme models may have reduced accuracy).
- Heavily processed vocals (heavy reverb, pitch correction, vocoder).
- Rap/spoken word vs. melodic singing — phoneme boundaries are denser and faster.
- Songs where lyrics are not available and must be inferred from audio alone.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST produce at least one timing track whose marks correspond to
  phoneme or syllable onsets in the vocal content of the audio.
- **FR-002**: Phoneme analysis MUST operate on the isolated vocal stem (from stem
  separation, feature 003) rather than the mixed audio where possible.
- **FR-003**: Phoneme analysis MUST function without requiring the user to provide a
  lyrics transcript — audio-only inference is the baseline.
- **FR-004**: Providing a lyrics transcript MUST improve phoneme mark accuracy when
  available, as an optional enhancement.
- **FR-005**: Phoneme timing tracks MUST integrate into the existing scoring and
  selection workflow alongside all other algorithm outputs.
- **FR-006**: Phoneme analysis MUST be an optional dependency — if unavailable, the
  pipeline MUST complete and skip phoneme tracks with a notification.
- **FR-007**: The implementation approach (local model vs. external API vs. forced
  aligner) MUST be evaluated during planning; API dependency and offline capability
  must both be considered.

### Key Entities

- **PhonemeMark**: A TimingMark extended with phoneme category metadata — timestamp,
  phoneme label, confidence.
- **PhonemeTrack**: A TimingTrack composed of PhonemeMarks.
- **LyricsTranscript**: An optional text input providing lyric content to improve
  forced alignment accuracy.

---

## Success Criteria *(mandatory)*

- Phoneme timing marks align with audible syllable onsets within ±80ms on at least
  75% of marks for a reference track with known lyrics.
- Phoneme tracks are generated without requiring a pre-provided lyrics file (audio-only
  inference achieves the accuracy target above).
- Phoneme analysis on a 3-minute vocal track completes in under 120 seconds on a
  typical developer machine.
- Failure to produce phoneme tracks does not prevent any other timing tracks from
  being generated.

---

## Assumptions

- Feature 003 (stem separation) is a prerequisite — phoneme analysis should run on the
  isolated vocal stem, not the mixed audio.
- The primary implementation approach is TBD: options include forced alignment (e.g.,
  Gentle, Montreal Forced Aligner, WhisperX), audio-only phoneme detection, or a
  commercial transcription API. This needs a research spike before planning.
- Phoneme type tagging (Story 2) is only in scope if the chosen approach provides
  phoneme category data with minimal additional cost.

---

## Open Questions

- **OQ-001**: Which phoneme analysis approach to use — local forced aligner
  (WhisperX/Gentle/MFA), a commercial API, or a hybrid? Trade-offs: accuracy, offline
  capability, cost, reproducibility.
- **OQ-002**: What happens when the vocal stem has poor quality after separation? Should
  we fall back to mixed-audio phoneme detection or skip?
- **OQ-003**: Is a lyrics-optional mode achievable with acceptable accuracy, or should
  lyrics be strongly recommended?

---

## Out of Scope

- Full lyrics transcription as a user-facing feature (the goal is timing marks, not text output).
- Speaker diarization (identifying who is singing which phrase).
- Real-time phoneme detection.
