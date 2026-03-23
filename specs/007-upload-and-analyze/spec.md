# Feature Specification: In-Browser MP3 Upload and Analysis

**Feature Branch**: `007-upload-and-analyze`
**Created**: 2026-03-22
**Status**: Draft
**Input**: User description: "Add MP3 upload and analysis to the review UI. When xlight-analyze review is run with no arguments, the browser shows an upload page where the user can drag-and-drop or select an MP3 file. The server runs the full analysis pipeline in a background thread and streams progress to the browser via Server-Sent Events. When analysis completes the browser automatically navigates to the timeline review UI. The analysis_json argument remains optional — if provided, behaviour is unchanged. The upload page should also let the user toggle vamp and madmom on/off to trade speed for coverage."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Upload an MP3 and Start Analysis (Priority: P1)

A user wants to review a new song they have never analyzed before. They run `xlight-analyze review` with no arguments. Their browser opens to an upload page. They drag their MP3 onto the page (or click to browse). They click Analyze. The analysis runs and they land in the timeline review UI — all without touching the terminal again.

**Why this priority**: This is the core new capability. Without it, the feature does not exist. It collapses a two-command workflow (analyze then review) into a single browser interaction.

**Independent Test**: Run `xlight-analyze review` with no arguments. Confirm the browser opens to an upload page. Upload a valid MP3 and click Analyze. Confirm the browser automatically transitions to the timeline review UI showing the analyzed tracks, without any further terminal commands.

**Acceptance Scenarios**:

1. **Given** `xlight-analyze review` is run with no arguments, **When** the browser opens, **Then** an upload page is displayed with a drag-and-drop zone and a file picker button.
2. **Given** the upload page is open, **When** the user drags an MP3 file onto the drop zone, **Then** the file is accepted and shown as ready to analyze.
3. **Given** an MP3 is selected, **When** the user clicks Analyze, **Then** analysis begins and the page transitions to a progress view.
4. **Given** analysis completes successfully, **When** all algorithms have finished, **Then** the browser automatically navigates to the timeline review UI for that song.
5. **Given** `xlight-analyze review song_analysis.json` is run with an existing analysis file, **When** the browser opens, **Then** it goes directly to the timeline review UI — the upload page is not shown.

---

### User Story 2 — Live Analysis Progress (Priority: P2)

While the analysis is running, the user can see which algorithm is currently executing and how many have completed out of the total. They are not left staring at a blank or spinning screen for several minutes. If any individual algorithm fails, they are informed but the overall analysis continues with the remaining algorithms.

**Why this priority**: Analysis can take 1–3 minutes. Without progress feedback the tool appears frozen. Live progress builds user trust and lets them understand the coverage they are getting.

**Independent Test**: Start an analysis and verify that the progress view updates within 5 seconds of each algorithm completing, showing the algorithm name and completed count (e.g., "5 / 18 — librosa_beats done"). Verify the view updates at least once every 10 seconds until analysis completes.

**Acceptance Scenarios**:

1. **Given** analysis is running, **When** each algorithm finishes, **Then** the progress view updates to show the algorithm name and the count of completed algorithms out of total (e.g., "6 / 18 complete").
2. **Given** analysis is running, **When** an individual algorithm fails, **Then** the progress view notes the failure for that algorithm and continues with the remaining algorithms — the overall analysis is not aborted.
3. **Given** all algorithms have been attempted, **When** the final algorithm completes (or fails), **Then** the browser navigates to the timeline review UI.
4. **Given** analysis is running, **When** the user closes or reloads the browser tab, **Then** analysis continues on the server and the result is still written to disk.

---

### User Story 3 — Algorithm Coverage Controls (Priority: P3)

Before starting analysis, the user can choose to skip the Vamp plugin algorithms and/or the madmom algorithms. Skipping either set reduces the number of timing tracks produced but significantly reduces the time taken. The controls are clearly labelled with the trade-off (approximate track count affected).

**Why this priority**: Vamp and madmom together account for the majority of analysis time. Giving users control over this makes the tool practical for rapid iteration without requiring terminal flags.

**Independent Test**: On the upload page, uncheck both Vamp and madmom, upload an MP3, and click Analyze. Confirm that the resulting analysis contains only librosa-based tracks and completes significantly faster than a full-coverage run on the same file.

**Acceptance Scenarios**:

1. **Given** the upload page is displayed, **When** the user views the algorithm options, **Then** two toggles are shown: one for Vamp plugins and one for madmom, both enabled by default.
2. **Given** the user disables the Vamp toggle and starts analysis, **Then** no Vamp-based tracks appear in the resulting timeline.
3. **Given** the user disables the madmom toggle and starts analysis, **Then** no madmom-based tracks appear in the resulting timeline.
4. **Given** both toggles are disabled and analysis completes, **When** the timeline opens, **Then** only librosa-based tracks are shown.

---

### Edge Cases

- What happens when the user uploads a non-MP3 file (e.g., a PDF or WAV)?
- What happens when the uploaded MP3 is corrupt or unreadable by the audio loader?
- What happens when the MP3 is very short (< 5 seconds) or very long (> 20 minutes)?
- What happens if all selected algorithms fail and zero tracks are produced?
- What happens if the disk runs out of space while writing the analysis result?
- What happens if the user submits a second upload while analysis is already running?
- What happens if the user navigates back to the upload page after analysis completes?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When `xlight-analyze review` is run with no arguments, the browser MUST open to an upload page rather than failing with an error.
- **FR-002**: The upload page MUST accept MP3 files via drag-and-drop onto a designated drop zone.
- **FR-003**: The upload page MUST accept MP3 files via a standard file picker (click-to-browse).
- **FR-004**: The upload page MUST reject non-MP3 files before upload begins, displaying a clear error message.
- **FR-005**: The upload page MUST display toggles for Vamp plugin algorithms and madmom algorithms, both enabled by default.
- **FR-006**: Each toggle MUST display a brief label indicating the trade-off (e.g., approximate number of tracks affected) so the user can make an informed choice.
- **FR-007**: After the user selects an MP3 and clicks Analyze, the server MUST run the analysis pipeline using the selected algorithm coverage.
- **FR-008**: Analysis progress MUST be streamed to the browser in real time, updating after each algorithm completes with the algorithm name and completion count.
- **FR-009**: Individual algorithm failures MUST be noted in the progress view but MUST NOT abort the overall analysis.
- **FR-010**: When analysis completes successfully, the browser MUST automatically navigate to the timeline review UI without requiring any user action.
- **FR-011**: The analysis result MUST be saved alongside the uploaded MP3 as `<filename>_analysis.json`.
- **FR-012**: If analysis produces zero tracks, the user MUST see a clear error message and NOT be navigated to the timeline.
- **FR-013**: The existing `xlight-analyze review <analysis_json>` invocation MUST continue to work exactly as before — no upload page, direct timeline.
- **FR-014**: Only one analysis job may run at a time. If the user attempts to upload while analysis is already running, they MUST receive a clear message that analysis is in progress.

### Key Entities

- **UploadSession**: A single in-progress or completed analysis job triggered from the browser — includes the uploaded MP3 path, selected algorithm options, current progress state, and result path when complete.
- **ProgressEvent**: A single progress update streamed to the browser — includes algorithm name, completed count, total count, and optional error flag for that algorithm.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from running `xlight-analyze review` (no arguments) to seeing the timeline review UI for a new song without any additional terminal commands.
- **SC-002**: Progress updates appear in the browser within 5 seconds of each algorithm completing during a live analysis run.
- **SC-003**: A full-coverage analysis of a 4–5 minute MP3 completes and navigates to the timeline within the same time budget as running `xlight-analyze analyze` directly from the terminal.
- **SC-004**: Disabling both Vamp and madmom reduces total analysis time by at least 50% compared to a full-coverage run on the same file.
- **SC-005**: A first-time user can upload an MP3 and reach the review timeline in under 5 minutes total (including analysis time) with no documentation required.

## Assumptions

- The uploaded MP3 is saved to the server's working directory — the same location as if the user had run `xlight-analyze analyze` from that directory.
- The server process has write permission to its working directory.
- The upload page is only reachable when no `analysis_json` argument was provided at startup — it is not navigable from within the timeline review UI.
- Vamp and madmom toggles default to enabled. Users who want faster runs must opt out explicitly.
- A single server instance handles one upload and one analysis at a time — concurrent multi-user scenarios are out of scope.
- Closing the browser tab does not cancel the analysis job on the server.
- The analysis result produced by the in-browser upload is identical in format to one produced by `xlight-analyze analyze`.

## Out of Scope

- Cancelling an in-progress analysis from the browser.
- Uploading multiple MP3 files in one session.
- Saving or resuming interrupted analysis jobs across server restarts.
- Any form of user authentication or file access controls.
- Displaying a waveform or audio preview on the upload page before analysis.
