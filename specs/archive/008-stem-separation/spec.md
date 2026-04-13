# Feature Specification: Stem Separation

**Feature Branch**: `008-stem-separation`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "003-stem-separation"

## Overview

When analyzing a song for lighting sequencing, the quality of timing tracks (beats, onsets, pitch, harmony) suffers because all algorithms receive the full mixed audio. A drums algorithm works better when it only hears drums; a pitch algorithm works better without a kick drum muddying the signal.

This feature adds audio stem separation as a preprocessing step: before running timing analysis, the system splits the MP3 into isolated stems (drums, bass, vocals, other/melody). Each analysis algorithm is then routed to the stem most relevant to its purpose, producing cleaner, more accurate timing tracks.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Analyze with Stem Separation (Priority: P1)

A lighting designer runs the standard analysis command on a song and gets noticeably cleaner timing tracks — beats from the drums stem, pitch from the vocals/melody stem — without needing to change their workflow.

**Why this priority**: This is the core value of the feature. Everything else depends on separation working correctly and producing better tracks.

**Independent Test**: Run `xlight-analyze analyze song.mp3 --stems` on a test track, verify stem files are created, and compare quality scores of beat/pitch tracks against a non-stem run.

**Acceptance Scenarios**:

1. **Given** an MP3 file, **When** the user runs analysis with stem separation enabled, **Then** the system separates the audio into six stems (drums, bass, vocals, guitar, piano, other) before running algorithms.
2. **Given** separation completes, **When** algorithms run, **Then** beat-tracking algorithms receive the drums stem, pitch algorithms receive the vocals stem, and harmony/chord algorithms receive the piano or guitar stem.
3. **Given** a stem-separated analysis completes, **When** the user views the summary, **Then** quality scores for beat and pitch tracks are equal to or higher than the non-stem baseline for the same file.

---

### User Story 2 - Stem Caching (Priority: P2)

A user re-runs analysis with different algorithm settings on a song they've already separated. The stem separation step is skipped and cached stems are reused, making the re-run fast.

**Why this priority**: Stem separation is slow (minutes per song). Without caching, iterating on algorithm settings becomes impractical.

**Independent Test**: Run analysis twice on the same file with stems enabled; confirm the second run skips separation and completes faster.

**Acceptance Scenarios**:

1. **Given** stems have already been generated for a song, **When** the user runs analysis again on the same file, **Then** the system detects existing stems and skips the separation step.
2. **Given** the source MP3 has changed (modified timestamp or content), **When** analysis runs, **Then** the system regenerates stems rather than using stale cache.

---

### User Story 3 - Stem Visibility in Review UI (Priority: P3)

A user reviews timing tracks in the browser UI and can see which stem each track was derived from, helping them understand why a track looks the way it does.

**Why this priority**: Transparency aids trust and debugging, but does not block core functionality.

**Independent Test**: Load a stem-analyzed JSON in the review UI and verify each track label identifies its source stem.

**Acceptance Scenarios**:

1. **Given** an analysis produced with stem separation, **When** the user opens the review UI, **Then** each timing track displays a label indicating its source stem (e.g., "drums", "bass", "vocals", "guitar", "piano", "other", or "full mix").
2. **Given** an analysis produced without stem separation, **When** the user opens the review UI, **Then** tracks display "full mix" as their source, and the UI renders normally without errors.

---

### Edge Cases

- What happens when stem separation fails mid-process (e.g., out of disk space, corrupted output)?
- How does the system handle very short files (under 10 seconds) where separation quality is unreliable?
- What if the song is already an isolated instrument (e.g., a drum loop) — does separation still run?
- How are stems handled when the source MP3 is replaced or renamed?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support an opt-in option to enable stem separation during analysis, leaving the default behavior (full-mix analysis) unchanged.
- **FR-002**: When stem separation is enabled, the system MUST produce six stems: drums, bass, vocals, guitar, piano, and other.
- **FR-003**: The system MUST route each analysis algorithm to the stem best suited to its purpose (drums algorithms → drums stem, pitch algorithms → vocals stem, harmony algorithms → piano/guitar stems, onset detectors → drums stem).
- **FR-004**: Generated stem files MUST be cached alongside the analysis output and reused on subsequent runs for the same source file.
- **FR-005**: The system MUST detect when cached stems are stale (source file changed) and regenerate them automatically.
- **FR-006**: If stem separation fails, the system MUST fall back to full-mix analysis and report a warning — it MUST NOT silently produce partial results.
- **FR-007**: The analysis output MUST record which stem each timing track was derived from.
- **FR-008**: The `xlight-analyze summary` command MUST display the stem source alongside each track.
- **FR-009**: The review UI MUST display the stem source for each track.

### Key Entities

- **Stem**: An isolated audio component derived from a mixed source file. Has a name (drums, bass, vocals, guitar, piano, other), a source file reference, and a generation timestamp.
- **Stem Cache**: A set of stem files associated with a specific source audio file, used to avoid redundant reprocessing. Keyed by source file identity.
- **Timing Track** (extended): Already exists; gains a `stem_source` attribute indicating which stem (or "full mix") the track was generated from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Beat timing tracks produced from stem separation score higher on quality assessment than their full-mix equivalents for at least 80% of test songs.
- **SC-002**: A re-analysis run on a previously separated song completes the separation phase in under 2 seconds (cache hit).
- **SC-003**: Analysis with stem separation enabled completes within 3× the time of a non-stem run on a 4-minute song (separation overhead is bounded).
- **SC-004**: 100% of timing tracks in a stem-separated analysis output include a non-empty stem source label.
- **SC-005**: When stem separation fails, the system falls back and completes full-mix analysis in 100% of failure cases rather than erroring out.

## Assumptions

- Stem separation is opt-in: the default `xlight-analyze analyze` behavior remains full-mix analysis. Users explicitly enable stem separation to get higher-quality tracks. This preserves existing behavior and avoids surprising slowdowns on upgrade.
- Six stems are used: drums, bass, vocals, guitar, piano, other. The `htdemucs_6s` model is used for separation.
- Stem files are stored alongside the analysis output.
- The review UI stem labels are read from the analysis JSON and require no additional network calls.
- Performance target of 3× overhead is based on typical 4-minute pop/electronic songs; very long files (30+ minutes) are out of scope.

## Out of Scope

- Manual stem uploading (user provides their own pre-separated stems).
- Stem playback in the review UI (stems are used for analysis only; the UI plays the original mix).
- More than six stems.
- Stem quality editing or adjustment controls.
