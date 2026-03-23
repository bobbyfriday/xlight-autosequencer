# Feature Specification: Audio Analysis and Timing Track Generation

**Feature Branch**: `001-audio-timing-tracks`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "Audio analysis from MP3 — generate multiple timing tracks using different algorithms, filter noise, produce a handful of meaningful tracks representing musical elements (instruments, sounds, beats) that can be used to highlight specific elements of a song"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Timing Tracks from an MP3 (Priority: P1)

A user provides an MP3 file and runs the tool. The tool analyzes the audio using
multiple algorithms and produces a set of timing tracks — each track being a sequence
of timestamps that mark musically meaningful moments. The user ends up with a file
(or set of files) containing the timing tracks, ready for use in downstream sequencing.

**Why this priority**: This is the entire foundation of the tool. Nothing else can be
built until we can reliably extract timing data from audio.

**Independent Test**: Given a known MP3 file with a clear, identifiable beat, run the
tool and verify that the output contains at least one timing track whose timestamps
align with the audible beat within an acceptable margin (e.g., ±50ms).

**Acceptance Scenarios**:

1. **Given** a valid MP3 file, **When** the user runs the analysis command, **Then**
   the tool produces one or more timing tracks with named timestamps covering the
   duration of the song.
2. **Given** an MP3 file, **When** analysis completes, **Then** the output includes
   tracks representing at least two distinct musical characteristics (e.g., beat-level
   and bar-level, or beats and a detected melodic element).
3. **Given** the same MP3 file run twice, **When** using the same algorithm settings,
   **Then** the output is identical (deterministic results).
4. **Given** an invalid or corrupted file, **When** the user runs the tool, **Then**
   a clear error message is shown and no partial output is written.

---

### User Story 2 - Compare Algorithm Results and Select Best Tracks (Priority: P2)

After generating timing tracks via multiple algorithms, the user wants to review a
summary of what each algorithm produced — how dense the timing marks are, what they
represent — and choose which tracks to keep. The goal is to discard noisy or redundant
tracks and retain only the tracks most useful for lighting a specific song.

**Why this priority**: Many algorithms produce excessive timing marks ("noise") that
would trigger lights too frequently. The ability to evaluate and curate is what makes
the output usable.

**Independent Test**: Given timing track output from Story 1, the user can view a
per-track summary (track name, algorithm, number of timing marks, density) and
select a subset to export, without re-running analysis.

**Acceptance Scenarios**:

1. **Given** a completed analysis run, **When** the user reviews the output summary,
   **Then** each timing track shows its name, source algorithm, total timing mark count,
   and average interval between marks.
2. **Given** a set of generated tracks, **When** the user specifies which tracks to
   keep (by name or index), **Then** only the selected tracks appear in the final
   exported output.
3. **Given** two algorithms that produce tracks covering the same musical element,
   **When** the user reviews the summary, **Then** the summary makes their differences
   visible (e.g., density comparison) so the user can choose the better one.

---

### User Story 3 - Element-Specific Timing Tracks (Priority: P3)

The user wants timing tracks that correspond to specific musical elements — for example,
a track that fires on drum hits, a track that follows a melodic lead line, or a track
that marks frequency-band energy peaks (bass, mid, treble). These tracks allow individual
lighting groups to be choreographed to different layers of the music.

**Why this priority**: Beat-only sequencing looks generic. Element-specific tracks are
what make a display feel musically synchronized. This is a differentiating capability
but depends on Story 1's pipeline being solid first.

**Independent Test**: Given an MP3 with a clearly audible drum pattern and a distinct
melody, the tool produces at least one track whose marks align primarily with percussion
events and at least one whose marks align with a non-percussion element.

**Acceptance Scenarios**:

1. **Given** an MP3 with a prominent bass line, **When** the user requests frequency-band
   analysis, **Then** the output includes a track whose timing marks correspond to
   low-frequency energy peaks.
2. **Given** an analysis run with multiple element-detection algorithms, **When** the
   user views the output, **Then** each track is labeled with the element type it
   represents (e.g., "drums", "bass", "melody", "beat", "bar").
3. **Given** an element-specific track, **When** examined against the source audio,
   **Then** at least 80% of timing marks fall within ±100ms of the corresponding
   musical event.

---

### Edge Cases

- What happens when the MP3 has no detectable beat (ambient/drone music)?
- How does the tool behave with very short files (< 10 seconds)?
- What happens when an algorithm times out or crashes on a specific file?
- How are timing marks handled at the very start and end of the song (boundary conditions)?
- What if two algorithms produce near-identical timing marks — are duplicate tracks surfaced?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept an MP3 file as input and produce one or more timing
  tracks as output.
- **FR-002**: The tool MUST support running multiple audio analysis algorithms against
  the same input file in a single invocation.
- **FR-003**: Each timing track MUST have a human-readable name that identifies the
  algorithm and musical element it represents.
- **FR-004**: The tool MUST output a summary of all generated timing tracks, including
  track name, total mark count, and average interval between marks.
- **FR-005**: The tool MUST allow the user to select a subset of generated tracks for
  final export, discarding unwanted tracks.
- **FR-006**: Output timing tracks MUST be saved as a structured JSON file containing
  all generated tracks and their timing marks. xLights XML export is out of scope for
  this feature and will be handled by a dedicated export stage in a later feature.
- **FR-007**: Analysis results MUST be deterministic: the same input file with the same
  algorithm settings MUST always produce the same timing marks.
- **FR-008**: The tool MUST handle analysis failures for individual algorithms gracefully —
  if one algorithm fails, the others MUST still complete and produce output.
- **FR-009**: Each timing mark MUST record at minimum: a timestamp (in milliseconds from
  start of audio) and the track it belongs to.
- **FR-010**: The tool MUST process audio fully offline, with no network calls.

### Key Entities

- **AudioFile**: The source MP3 input — path, duration, sample rate, detected key metadata.
- **AnalysisAlgorithm**: A named, configured analysis method — name, type (beat/bar/onset/
  frequency-band/instrument), parameters.
- **TimingTrack**: A named sequence of timing marks generated by one algorithm — name,
  source algorithm, list of marks.
- **TimingMark**: A single event within a track — timestamp (ms), optional confidence score.
- **AnalysisResult**: The full output of a run — source file, list of timing tracks, run
  timestamp, algorithm configurations used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a song with a clear 4/4 beat, the beat-detection track aligns with
  audible beats within ±50ms on at least 90% of marks.
- **SC-002**: A complete analysis run on a 3-minute MP3 finishes in under 60 seconds
  on a modern laptop.
- **SC-003**: At least 3 distinct timing track types are produced from a single analysis
  run (e.g., beats, bars, and one element-specific track).
- **SC-004**: After reviewing the summary, a user can identify and discard noisy tracks
  and export only the tracks they want in under 2 minutes.
- **SC-005**: 100% of generated timing tracks are deterministic — running the same file
  twice produces byte-identical timing data.

## Assumptions

- The audio analysis libraries to be used will be confirmed by the user before planning
  begins (user has specific packages in mind and will provide links).
- MP4 input support (video + audio) is out of scope for this feature — MP3 only.
- The tool is invoked via a command-line interface for this feature.
- "Noise" in timing tracks means marks occurring more frequently than is musically
  meaningful for lighting; the specific density threshold will be tuned during implementation.
- Output format will be clarified before implementation (see FR-006).
