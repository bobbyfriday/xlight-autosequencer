# Feature Specification: Timing Track Review UI

**Feature Branch**: `002-track-review-ui`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "I want to create a UI which allows the mp3 file to play and to show the timing tracks in relation to the music. The intent is to see how useful the timing tracks would be and then select the timing tracks to use for the next step."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Visualise Timing Tracks Against Audio (Priority: P1)

A user has already run `xlight-analyze analyze` on a song and has an analysis JSON file. They open the review UI, load the song and its analysis, and immediately see all timing tracks laid out as horizontal lanes on a timeline. Each mark on each track is visible as a vertical tick aligned to its position in the song. The user can scan the tracks at a glance and compare how dense or sparse each one is, and read the quality score beside each track name.

**Why this priority**: Without the visual timeline, users cannot evaluate which timing tracks are meaningful. This is the entire purpose of the feature.

**Independent Test**: Load a known analysis JSON. Without playing any audio, the timeline renders all tracks with the correct number of marks visible at the correct proportional positions along the song duration.

**Acceptance Scenarios**:

1. **Given** an analysis JSON with 8+ tracks, **When** the user opens the review UI and loads the files, **Then** each track appears as a named horizontal lane with marks drawn at their correct time positions.
2. **Given** a track with a quality score of 0.98, **When** the timeline is displayed, **Then** the quality score is visible alongside the track name.
3. **Given** a track scored 0.00 flagged as HIGH DENSITY, **When** the timeline is displayed, **Then** the track is visually distinguished (e.g., dimmed or marked) to indicate it is likely not useful.
4. **Given** a song of 4 minutes 49 seconds, **When** the timeline is loaded, **Then** the horizontal axis correctly spans the full song duration.

---

### User Story 2 — Synchronised Audio Playback (Priority: P2)

The user presses Play. The song begins playing and a playhead line moves across the timeline in real time, keeping perfect sync with the audio. As the playhead passes each mark on any track, the user can see exactly when that event fires relative to what they are hearing. The user can click any point on the timeline to jump the playhead and audio to that position. They can pause and resume.

**Why this priority**: Static visualisation alone is useful, but hearing the music while watching the marks fire is what makes the quality judgement intuitive and reliable.

**Independent Test**: Play a 10-second test clip. The playhead travels from start to end within 10 ± 0.5 seconds as measured by wall clock. Clicking at the 50% mark of the timeline scrubs the audio to approximately the halfway point.

**Acceptance Scenarios**:

1. **Given** the timeline is loaded, **When** the user presses Play, **Then** the audio begins and a playhead moves left-to-right in sync with the audio position.
2. **Given** audio is playing, **When** the user presses Pause, **Then** both the audio and the playhead stop at the same position.
3. **Given** audio is paused, **When** the user clicks a point on the timeline, **Then** the audio position jumps to that time and the playhead moves to match.
4. **Given** audio reaches the end of the song, **When** playback completes, **Then** the playhead stops at the end and the Play button resets.

---

### User Story 3 — Quick Track Switching and Focus Mode (Priority: P3)

With 20 tracks on screen at once, it is hard to focus on one. The user wants to rapidly cycle through tracks — one at a time — while the audio keeps playing, so they can compare how each track feels against the music in quick succession. They can press a Next/Prev button (or use keyboard shortcuts) to move focus to the adjacent track. The focused track is prominently highlighted while the others are dimmed but remain visible for spatial reference. The user can also click a Solo button on any track to instantly focus it without cycling.

**Why this priority**: With 20 tracks to evaluate, switching between them quickly while audio plays is the core evaluation workflow. Without it, the user has to mentally compare tracks that are all equally visible, which is cognitively demanding.

**Independent Test**: Load an analysis with 10 tracks. Without touching the mouse, press the Next key 5 times. The 6th track is highlighted and all others are dimmed. Press Prev once — the 5th track is now highlighted.

**Acceptance Scenarios**:

1. **Given** the timeline is displaying multiple tracks, **When** the user presses Next or the equivalent keyboard shortcut, **Then** focus moves to the next track (by display order), that track is prominently highlighted, and all others are dimmed.
2. **Given** a track is in focus, **When** the user presses Prev, **Then** focus moves to the previous track in display order.
3. **Given** the last track is in focus, **When** the user presses Next, **Then** focus wraps to the first track.
4. **Given** any track is displayed, **When** the user clicks its Solo button, **Then** that track immediately enters focus regardless of current keyboard position.
5. **Given** a track is in focus, **When** the user presses a Clear Focus key or clicks the active Solo button again, **Then** all tracks return to equal visibility.
6. **Given** a track is focused and audio is playing, **When** the user switches focus to a different track, **Then** audio playback is uninterrupted.

---

### User Story 4 — Track Selection and Export (Priority: P4)

After reviewing the tracks, the user checks or unchecks individual tracks to include or exclude them. They can see at a glance which tracks are selected. When satisfied, the user clicks Export Selection. A filtered analysis file is saved that contains only the selected tracks — ready for the next pipeline step (xLights sequence generation).

**Why this priority**: The review UI must produce a usable output. Selection and export close the loop from evaluation to action.

**Independent Test**: Load an analysis with 8 tracks. Deselect 3 tracks. Click Export. The resulting file contains exactly 5 tracks matching the selected names, with all mark data intact.

**Acceptance Scenarios**:

1. **Given** the timeline is displayed, **When** the user unchecks a track, **Then** the track is visually marked as excluded (greyed out or hidden) and will not appear in the export.
2. **Given** tracks are selected, **When** the user clicks Export Selection, **Then** a file is saved containing only the checked tracks with all their timing marks preserved.
3. **Given** no tracks are selected, **When** the user clicks Export Selection, **Then** the system warns the user that no tracks are selected and does not write a file.
4. **Given** a previous export file exists at the default output path, **When** a new export is performed, **Then** the user is informed the file will be overwritten before it is saved.

---

### Edge Cases

- What happens when the analysis JSON has zero tracks (all algorithms failed)?
- What happens when the MP3 file referenced in the analysis JSON no longer exists at that path?
- What happens when the analysis JSON is corrupt or missing required fields?
- What if the song is very short (< 5 seconds) or very long (> 10 minutes)?
- What happens when Next/Prev is pressed and there is only one track loaded?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The UI MUST allow the user to load an existing analysis JSON file (from `xlight-analyze analyze` output).
- **FR-002**: The UI MUST display all timing tracks from the analysis as horizontal lanes in a single scrollable timeline view.
- **FR-003**: Each timing track lane MUST show the track name, quality score, element type, and mark count.
- **FR-004**: Each mark on a timing track MUST be rendered as a vertical line at its correct proportional position along the song duration.
- **FR-005**: Tracks with a quality score of 0.00 or with an average mark interval below 200ms MUST be visually distinguished to signal they may not be useful for lighting.
- **FR-006**: The UI MUST play the MP3 file associated with the analysis and display a moving playhead that stays in sync with the current audio position.
- **FR-007**: The user MUST be able to pause and resume audio playback.
- **FR-008**: The user MUST be able to click anywhere on the timeline to jump audio playback to that position.
- **FR-009**: Each track MUST have a checkbox or toggle to include or exclude it from the selection.
- **FR-010**: The UI MUST provide an Export Selection action that writes a filtered analysis JSON containing only the selected tracks.
- **FR-011**: The export output path MUST default to `<input_basename>_selected.json` alongside the source analysis file.
- **FR-012**: The UI MUST display a warning if the user attempts to export with zero tracks selected.
- **FR-013**: The UI MUST display a clear error and allow the user to locate the audio file manually when the path in the JSON does not exist.
- **FR-014**: The timeline MUST display a time axis (mm:ss) so users can correlate marks to song positions without playing audio.
- **FR-015**: Tracks MUST be displayed sorted by quality score descending by default so the best candidates appear at the top.
- **FR-016**: The UI MUST provide Next and Previous controls (and equivalent keyboard shortcuts) to cycle focus through tracks one at a time while audio continues playing.
- **FR-017**: When a track is in focus, it MUST be visually prominent (e.g., full opacity, highlighted border) while all other tracks are dimmed but remain visible.
- **FR-018**: Each track MUST have a Solo button that immediately focuses that track, equivalent to cycling to it with Next/Prev.
- **FR-019**: The user MUST be able to clear focus (return all tracks to equal visibility) via a dedicated control or by clicking the active Solo button again.
- **FR-020**: Switching focus between tracks MUST NOT interrupt audio playback.

### Key Entities

- **ReviewSession**: The currently loaded analysis JSON and audio file pair, including the user's current track selection state.
- **TrackLane**: The visual representation of one timing track — name, score, element type, mark count, selection state.
- **Playhead**: The moving cursor that reflects the current audio position in the timeline.
- **ExportSelection**: The filtered subset of tracks the user has chosen, written as a compatible analysis JSON.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can load an analysis JSON with 20 tracks and see all tracks rendered within 3 seconds of loading.
- **SC-002**: The playhead position deviates from actual audio position by no more than 100ms during continuous playback.
- **SC-003**: A user can evaluate all tracks, make a selection, and export in under 2 minutes for a typical 4–5 minute song.
- **SC-004**: The exported selection JSON is accepted by `xlight-analyze summary` without errors.
- **SC-005**: A first-time user can identify the top 3 highest-quality tracks within 30 seconds of loading the UI.

## Assumptions

- The user has already run `xlight-analyze analyze` and has a valid analysis JSON before opening the review UI.
- The MP3 file is on the local filesystem — no streaming or network access is required.
- The UI runs locally on the same machine as the audio file.
- The exported selection uses the same JSON schema as the existing analysis output, ensuring compatibility with downstream pipeline steps.
- Tracks are sorted by quality score descending by default; manual drag-to-reorder is out of scope.
- Focus/solo mode is a viewing aid — it does not affect the export selection state.
- The UI is single-session: it handles one song at a time.

## Out of Scope

- Editing or adjusting individual timing marks within the UI.
- Re-running audio analysis from within the UI.
- Comparing multiple songs simultaneously.
- Saving or restoring review sessions between UI launches.
- Any form of user accounts, cloud storage, or sharing.
