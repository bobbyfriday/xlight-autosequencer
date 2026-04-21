# Feature Specification: x-onset Frontend Redo

**Feature Branch**: `051-x-onset-frontend`
**Created**: 2026-04-21
**Status**: Draft
**Input**: User description: "Redo the review/dashboard frontend from scratch using the x-onset design handoff — a 6-screen DAW-style flow (library → drop → analyze → timeline → theme → export) with a coherent JSON API to replace the current ad-hoc Flask-rendered UI"

## Clarifications

### Session 2026-04-21

- Q: How are songs uniquely identified in the library — by file path, by audio content hash, or not deduplicated at all? → A: By audio content hash (same audio = same library entry regardless of source path; reuses the existing analysis cache keying).
- Q: When a themed song is re-analyzed and the section boundaries change, what happens to existing theme assignments? → A: Preserve by time overlap (new section inherits the theme of the old section it overlaps most with), with a pre-commit review dialog listing assignments that moved, were dropped, or now need themes — user confirms before the new analysis replaces the old.
- Q: What can the user do with a library entry whose source audio file is missing? → A: Read-only review and theme assignment edits are allowed; playback, live preview, and export are blocked until the audio is relocated.
- Q: How do library folders work — auto-inferred, explicit single-folder, explicit multi-folder (tags), or none in v0? → A: Explicit user-created folders; each song belongs to exactly one folder (or the default "Unfiled"). User creates, renames, deletes folders and drags songs between them.
- Q: What happens when analysis is interrupted mid-run (app closed, crash)? → A: Discard the partial run. On re-open the song returns to "draft" status and analysis must be restarted from scratch.
- Q: What happens to theme assignments when sections are split, merged, or when a ghost boundary is promoted? → A: Split — both new sections inherit the original's theme. Merge — result keeps the first section's theme; the second's assignment is discarded. Promote ghost — both sides inherit from the section being split.
- Q: How do users remove a song from the library, and what gets cleaned up? → A: Two-step delete. Step 1 — "remove from library" drops app state (sections, themes, preferences). Step 2 — app offers to purge the analysis cache and stems for that content hash; user confirms. The source audio file on disk is never touched.
- Q: Where does the xLights prop layout come from for export (per-song picker, one-time import, auto-scan, or per-session picker)? → A: One-time layout import in a settings step; the imported layout is reused for every song's export. Changing layouts requires re-import.
- Q: When is user state written to disk — on exit, on every change, or something in between? → A: On every meaningful state change (theme assignment, section edit, folder move, import, preference toggle). High-frequency events (playhead position, scrub, energy pulse) are debounced to roughly one second.
- Q: When a user assigns a new theme to a section that has per-section parameter overrides, what happens to the overrides? → A: Overrides reset to defaults on theme change. The new theme starts with its default parameters; the user tunes again if needed.
- Q: When analysis completes, are sections auto-assigned default themes, left unassigned, or does the song become "themed" automatically? → A: Auto-populate with analyzer-suggested default themes; song enters "analyzed" status (not "themed"). The song flips to "themed" only after the user opens the theme screen and either accepts the defaults (single "accept all" action) or overrides individual assignments.
- Q: What does a first-run user with nothing imported and no xLights layout configured see? → A: Land on the LIBRARY screen with a centered empty-state ("Drop an MP3 to start" dashed drop target). xLights layout import is deferred until the user reaches the export screen; at that point export is blocked with a clear "import your xLights layout to continue" prompt and inline action.
- Q: How do users move their library between machines or back it up? → A: Explicit "Export library" and "Import library" actions produce/consume a bundle containing all library state (songs by content hash, sections, themes, parameter overrides, folders, preferences). Audio files are NOT bundled — they're referenced by hash and users reconnect them on import. No cloud sync.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — First-Song Happy Path (Priority: P1)

A new hobbyist installs the tool, opens it, drops an MP3 of a Christmas song into the app, waits for analysis to complete, reviews the detected sections on a timeline, assigns a named lighting theme to each section, and exports the result to a file their xLights install can play. This single journey — from empty app to finished light show — is the entire product.

**Why this priority**: Nothing else matters if a user can't go from "I have an MP3" to "I have a light show." Every other story assumes this flow works. Shipping this alone (with only one song at a time, no library management, no section edits) is the minimum viable product.

**Independent Test**: A fresh install with no prior state opens to an empty library. The user drops a valid MP3, watches the analysis screen to completion, lands on the timeline with detected sections visible, clicks to the theme screen, assigns a theme to each section, clicks export, picks a destination, and receives a file the existing xLights workflow can load. Completing the chain without a dead end passes the test.

**Acceptance Scenarios**:

1. **Given** an empty library, **When** the user drops a valid MP3 onto the drop target, **Then** the file is accepted and analysis begins automatically with a visible progress indicator.
2. **Given** analysis completes successfully, **When** the user navigates to the timeline screen, **Then** the song's detected sections appear as labeled chips aligned to a visible waveform, and playback controls allow scrubbing through the song.
3. **Given** sections are visible on the theme screen, **When** the user selects a section and clicks a theme card, **Then** that theme is assigned to that section and a live lights preview reflects the assignment at the current playhead.
4. **Given** every section has a theme assigned, **When** the user clicks export, **Then** the export screen offers destination choices (xLights project, FSEQ, xsq) and produces a saved file on successful render.
5. **Given** a single section is missing a theme, **When** the user clicks export, **Then** the UI blocks export and indicates which sections still need themes.

---

### User Story 2 — Multi-Song Library Management (Priority: P2)

A returning user has imported a dozen songs over multiple sessions and wants to resume work on one of them. They open the app, see every imported song in the left rail with a status chip (draft / analyzed / themed), filter the list to find the one they want, and jump directly to the screen that matches its status (themed songs open at the theme screen for tweaking; analyzed songs open at the timeline; drafts open at the analyze screen).

**Why this priority**: A one-song workflow is technically useful but doesn't reflect how hobbyists actually work — they prepare a dozen songs per holiday season and iterate on them over weeks. Without library management, every session starts from scratch. P2 because the tool is usable for proof-of-concept on one song without it.

**Independent Test**: After importing three songs and partially progressing each one (one analyzed, one themed, one still in draft), closing and reopening the app shows all three in the library with correct status chips, filter pills show accurate counts, and clicking each song routes to the matching screen.

**Acceptance Scenarios**:

1. **Given** multiple imported songs with different states, **When** the library rail renders, **Then** each song shows title, artist, duration, and a status chip matching its current state.
2. **Given** the library has songs with mixed states, **When** the user clicks the `analyzed` filter pill, **Then** only songs in the analyzed state remain visible.
3. **Given** a song with status `themed`, **When** the user clicks that song, **Then** the app opens directly to the theme screen with that song loaded.
4. **Given** the user closes the app mid-workflow, **When** they reopen it, **Then** the last-active song, screen, and playhead position are restored.

---

### User Story 3 — Section Boundary Editing (Priority: P2)

The audio analyzer sometimes misses a section boundary, merges two sections that should be separate, or places a boundary a few seconds off the musical change. A user on the timeline screen enters "sections edit mode" and can split the current section at the playhead, merge two adjacent sections, delete a section entirely, rename a section, or promote an alternate boundary that the analyzer detected but didn't use. They can also reset all their edits back to the analyzer's original output.

**Why this priority**: Themes assigned to wrong sections produce noticeably-bad light shows, and the analyzer is never perfect. Without editing, users are stuck with detection errors. P2 because a user can still produce acceptable output on well-analyzed songs without this, and because it builds on US1's timeline surface.

**Independent Test**: Load a song whose detected sections contain at least one visibly-wrong boundary. Enter sections edit mode, apply each edit operation (split, merge, delete, rename, promote ghost, reset), and verify the section list and timeline update accordingly. All edits must persist across app restart.

**Acceptance Scenarios**:

1. **Given** the timeline is in sections edit mode, **When** the user presses `S` with the playhead inside a section, **Then** that section splits into two at the playhead position (unless within 0.5s of an existing boundary, in which case the UI rejects the split).
2. **Given** two adjacent sections, **When** the user selects the first and presses `M`, **Then** the two sections merge into one with the first section's name and the combined time range.
3. **Given** the analyzer produced alternate ("ghost") boundaries not used in the active section list, **When** the user promotes a ghost boundary, **Then** that boundary becomes a real section divider.
4. **Given** the user has made multiple edits, **When** they click "reset to detected," **Then** all sections revert to the analyzer's original output.
5. **Given** at least one section exists, **When** the user attempts to delete the only remaining section, **Then** the UI prevents the deletion.

---

### User Story 4 — Per-Section Theme Parameter Tuning (Priority: P3)

A user on the theme screen has assigned themes to every section, but wants finer control on specific sections — the chorus should be brighter, the bridge should dwell longer on each color, the intro should shift colors slower. Each section's inspector shows four parameter sliders (brightness, hit strength, dwell time, color shift) that adjust the theme's behavior for that section only, without changing the theme itself.

**Why this priority**: Users can ship a light show without tuning — the default parameters produce acceptable output. This is a "now I can polish it" feature, not a "make it work" feature. P3 because US1 delivers value without it.

**Independent Test**: On a themed song, adjust each of the four parameter sliders on at least two different sections. Verify the live lights preview reflects the change, the export reflects the change, and parameter values persist across app restart.

**Acceptance Scenarios**:

1. **Given** a section with an assigned theme, **When** the user drags the brightness slider, **Then** the live lights preview updates in real time to reflect the new brightness.
2. **Given** per-section parameter overrides exist, **When** the user exports the song, **Then** the rendered output applies the overrides per section.
3. **Given** the user adjusted parameters on section A but not B, **When** they view the inspector for section B, **Then** section B shows default parameter values.

---

### User Story 5 — Visual Preferences and Keyboard-First Navigation (Priority: P3)

A power user wants to work without taking their hand off the keyboard: switch screens with number keys, play/pause with space, nudge the playhead with arrows, jump sections with Shift+arrows. They also want to toggle between dark and light themes depending on ambient light, switch density between compact and comfortable, and hide the inspector rail when they want more room for the timeline.

**Why this priority**: The app is fully usable with defaults. These preferences are comfort, not capability. P3.

**Independent Test**: Open the tweaks panel, toggle each preference (dark ↔ light, compact ↔ comfortable, inspector visible ↔ hidden). Verify every preference takes effect immediately and persists across app restart. Using only keyboard shortcuts, navigate from the library screen to the export screen and back, and scrub through a song.

**Acceptance Scenarios**:

1. **Given** the tweaks panel is open, **When** the user selects "light," **Then** the entire UI switches palette immediately without reloading.
2. **Given** any screen, **When** the user presses a number key 1–6, **Then** the app switches to the matching screen.
3. **Given** the timeline is visible, **When** the user presses Shift+→, **Then** the playhead jumps to the next section boundary.
4. **Given** the user set preferences in a prior session, **When** they reopen the app, **Then** dark/light, density, and inspector visibility match the saved values.

---

### Edge Cases

- **No sections detected**: If the analyzer returns zero sections for a song (unusual but possible for very short clips or pure-tone test files), the timeline shows a single default section spanning the entire song rather than an empty state.
- **Corrupt or unsupported audio**: The drop screen rejects files that aren't in the supported formats (mp3, wav, flac, aiff) with a clear error message and does not begin analysis.
- **Analysis failure mid-run**: If a detector crashes, the analyze screen shows a red failure row with a retry action that reruns only the failed step, not the entire pipeline.
- **Theme removed that's still assigned**: If a theme definition is removed between sessions (a future possibility once user-authored themes exist), sections assigned to that theme show a "theme missing" placeholder and block export until reassigned.
- **Split near boundary**: A split attempt within 0.5 seconds of an existing boundary is silently ignored to prevent near-zero-width sections.
- **Delete last section**: Deleting the only remaining section is prevented — at least one section must always exist.
- **Seeking past end**: Seek operations are clamped to [0, duration]; no error, just no-op at the edge.
- **Library with hundreds of songs**: Scrolling a library of 200+ songs remains smooth; there is no lazy-load threshold at which the list stalls.
- **Mid-playback screen change**: Playing audio continues uninterrupted when the user switches screens 1–6; switching back returns to the same playhead position.
- **Export before fully themed**: Export is blocked if any section lacks a theme assignment; the UI names the specific unthemed sections.
- **MP3 moved or deleted after import**: If the source audio file is missing when a user opens a library entry, the app shows a "source file missing" state on that entry and offers a "locate file" action. While the audio is missing, the user may review the timeline and edit theme assignments (data that does not require audio); playback, live lights preview, and export are blocked with a clear message until the audio is relocated.
- **Concurrent analysis of multiple songs**: Only one song analyzes at a time; a second import while analysis is running queues and shows a "queued" status on the library entry.

## Requirements *(mandatory)*

### Functional Requirements

#### Library and Song Management

- **FR-001**: System MUST display every imported song in a persistent library rail, each showing title, artist, duration, and a status chip reflecting whether the song is a draft, analyzed, or themed.
- **FR-001a**: System MUST identify each library entry by the content hash of its audio bytes, so importing the same audio file from a different path does not create a duplicate entry and any existing analysis, section edits, or theme assignments are shared across all paths referring to the same audio.
- **FR-002**: System MUST support filtering the library by status (all, themed, analyzed, draft).
- **FR-003**: System MUST route clicks on a library entry to the screen appropriate for its state: drafts → analyze, analyzed → timeline, themed → theme.
- **FR-004**: System MUST group library entries by explicit user-created folders (e.g., "Halloween 2026", "Christmas 2025") that can be collapsed or expanded. Each song belongs to exactly one folder; a newly-imported song lands in a default "Unfiled" folder until the user assigns it. Users MUST be able to create, rename, and delete folders, and to move a song between folders (e.g., by drag-and-drop). Deleting a non-empty folder MUST move its contents back to "Unfiled" rather than deleting the songs.
- **FR-005**: System MUST persist the library, per-song state, and current song selection across app restarts.
- **FR-005c**: On first-ever run (no prior state, no imported songs, no saved preferences), the system MUST land the user on the LIBRARY screen with a centered empty-state call-to-action ("Drop an MP3 to start") that also functions as the file drop target. No setup wizard is shown; xLights layout configuration is deferred.
- **FR-005a**: System MUST provide a "remove from library" action on a library entry that drops the app's state for that song (sections, theme assignments, per-section parameter overrides, folder membership, preferences pointing to this song) and returns the entry to a non-listed state. This action MUST NOT modify or delete the source audio file on disk.
- **FR-005b**: After removal, the system MUST offer a second explicit action to purge the analysis cache and stems for the removed song's content hash. The user must confirm this purge before it occurs. Declining leaves the cached artifacts on disk where they can be reused if the same audio is imported again.

#### Import

- **FR-006**: System MUST accept MP3, WAV, FLAC, and AIFF audio files via both a drop target and a browse-file button.
- **FR-007**: System MUST reject unsupported file types with a clear error message and no partial import state.
- **FR-008**: System MUST automatically advance from the drop screen to the analyze screen when a valid file is accepted.

#### Analysis

- **FR-009**: System MUST display the progress of each individual detector (beat, bar, onset, impact, drop, chord, etc.) with a per-detector status (queued, running, done, failed) and a confidence value when applicable.
- **FR-010**: System MUST show an overall progress percentage and an estimated time remaining during analysis.
- **FR-011**: System MUST allow retrying individual failed detectors without restarting the entire analysis.
- **FR-011a**: If analysis is interrupted by the app closing or crashing before completion, the partial run MUST be discarded. The song returns to "draft" status and the user must restart analysis from scratch when they return. Per-detector retry (FR-011) applies only to failed detectors within a completed run, not to interrupted runs.
- **FR-012**: System MUST provide a "review timeline" action that becomes available when analysis completes, and that advances to the timeline screen.
- **FR-012a**: On successful analysis completion, the system MUST auto-populate each detected section's theme assignment with the analyzer's suggested default theme for that section kind. The song enters "analyzed" status; it does NOT automatically become "themed."
- **FR-013**: Analysis results MUST persist so that returning to a previously-analyzed song does not require re-running analysis.
- **FR-013a**: System MUST support re-analyzing a song that already has theme assignments. Before replacing the existing analysis, the system MUST compute a proposed mapping from old sections to new sections by maximum time overlap, and MUST present a review dialog to the user showing: (a) assignments that carry over unchanged, (b) assignments that moved to a new boundary with magnitude of the shift, (c) assignments that were dropped because their section no longer exists, and (d) new sections that now need a theme. The replacement is applied only on user confirmation; cancelling keeps the prior analysis and all assignments intact.

#### Timeline Review

- **FR-014**: System MUST display the song's waveform aligned to a time ruler, with clickable scrubbing and a visible playhead that moves continuously during playback.
- **FR-015**: System MUST render detected sections as labeled chips on the timeline, colored by assigned theme when themes exist.
- **FR-016**: System MUST show a live lights preview strip that reflects the currently-assigned theme at the current playhead position.
- **FR-017**: System MUST show raw detector tracks (one lane per detector) with visible events per detector, and MUST allow the user to toggle individual tracks on and off.
- **FR-018**: System MUST provide transport controls (play, pause, skip to start, jump prev/next section, skip to end) and display the current timecode with tabular numerals.
- **FR-019**: System MUST display bar and beat information for the current playhead position.

#### Section Editing

- **FR-020**: System MUST provide a "sections edit mode" on the timeline that changes the inspector to show section-editing tools.
- **FR-021**: System MUST support splitting a section at the current playhead position, except when the playhead is within 0.5 seconds of an existing boundary. When a section is split, both resulting sections MUST inherit the original section's theme assignment and per-section parameter overrides.
- **FR-022**: System MUST support merging a selected section with its adjacent follower. The merged result MUST keep the first section's theme assignment and per-section parameter overrides; the second section's assignment is discarded.
- **FR-023**: System MUST support deleting a selected section, except when it is the only remaining section.
- **FR-024**: System MUST support renaming a section.
- **FR-025**: System MUST expose analyzer-detected alternate ("ghost") boundaries that were not used in the final section list, and support promoting any ghost to a real boundary. Promoting a ghost boundary splits its enclosing section; both resulting sections inherit the original's theme assignment and per-section parameter overrides.
- **FR-026**: System MUST support resetting all section edits to the analyzer's original output with a single action.
- **FR-027**: Section edits MUST persist across app restarts.

#### Theme Assignment

- **FR-028**: System MUST present a grid of built-in themes, each with a name, description, color swatches, and a small animated preview specific to the current section's kind.
- **FR-029**: System MUST allow the user to select one section and assign any theme from the grid to it with a single click.
- **FR-029a**: A song transitions from "analyzed" to "themed" only after the user visits the theme screen and either (a) clicks an "accept all defaults" action confirming the auto-populated assignments, or (b) has explicitly assigned every section at least once (including re-assigning a section to the same theme it auto-populated with). Merely having every section non-empty because of auto-population is not sufficient.
- **FR-030**: System MUST visually distinguish the currently-assigned theme on the grid (active card) from the rest.
- **FR-031**: System MUST display a strip of every section as chips in time order, with the currently-selected chip visually highlighted and each chip's color derived from its assigned theme.
- **FR-032**: System MUST expose per-section parameter sliders (brightness, hit strength, dwell time, color shift) in the inspector for fine-tuning a theme's behavior on the selected section without modifying the theme itself.
- **FR-032a**: When the theme assigned to a section changes, per-section parameter overrides on that section MUST reset to the new theme's defaults. Overrides are not carried across theme changes.
- **FR-033**: Theme assignments and per-section parameter overrides MUST persist across app restarts.

#### Export

- **FR-034**: System MUST provide export to at least three destination formats: xLights project, FSEQ file, and xsq file.
- **FR-035**: System MUST block export when one or more sections lack a theme assignment, and MUST identify the specific sections that need themes.
- **FR-035a**: System MUST block export when the source audio file cannot be located on disk. The user must first use the "locate file" action to point to the audio before export becomes available.
- **FR-036**: System MUST display a per-prop mapping table showing prop name, LED count, pixel range, and theme-driven colors before export.
- **FR-036a**: System MUST accept the user's xLights prop layout as a one-time import in a settings / preferences step. The imported layout is reused for every song's export until the user re-imports a different layout.
- **FR-036b**: If the user attempts to export before a layout has been imported, the system MUST block export and direct the user to the layout-import step with a clear message.
- **FR-036c**: Only one layout is active at a time. Re-importing replaces the prior layout; the system MUST warn the user that existing exports were produced against the prior layout and that re-exporting against the new layout may produce different output.
- **FR-037**: System MUST provide a scrubbable render preview that animates the full export on the timeline.

#### Playback and Live Preview

- **FR-038**: Audio playback MUST continue uninterrupted when the user switches between screens.
- **FR-039**: Live lights previews (on the timeline and theme screens) MUST reflect the audio playback state, current playhead, and energy/beat derived values in real time with no visible lag.
- **FR-040**: Seek operations MUST be clamped to the song's valid time range.

#### Keyboard

- **FR-041**: System MUST respond to these global keyboard shortcuts: `space` (play/pause), `←` / `→` (nudge playhead ±1s), `Shift+←` / `Shift+→` (jump to prev/next section boundary), `1`–`6` (switch screens).
- **FR-042**: System MUST respond to these timeline-only shortcuts when sections edit mode is active: `S` (split at playhead), `M` (merge with next), `Del` (delete selected), `R` (rename selected).

#### Visual Preferences

- **FR-043**: System MUST support switching between dark and light color modes with immediate effect (no reload).
- **FR-044**: System MUST support switching between compact and comfortable density modes.
- **FR-045**: System MUST allow the user to hide and show the inspector rail.
- **FR-046**: All visual preferences MUST persist across app restarts.

#### Visual Identity

- **FR-047**: The interface MUST render with the color palette, typography, spacing grid, and component details defined in the design handoff (dark/light token sets, Inter + JetBrains Mono, 4px grid, sharp corners, 1px dividers, unicode glyphs) — the UI must not drift into a soft/rounded generic look.
- **FR-048**: Timecodes MUST display with tabular numerals so digits do not shift during playback.

#### Data Persistence

- **FR-049**: User-authored state (library contents, section edits, theme assignments, parameter overrides, visual preferences, last-screen, last-playhead) MUST survive app restart on the same machine without data loss.
- **FR-049a**: System MUST write state durably on every meaningful user action (theme assignment, section edit, folder change, import, preference toggle). An app crash immediately after such an action MUST NOT lose that action.
- **FR-049b**: High-frequency derived state (playhead position, scrub position, transient UI state) MAY be written on a debounce of up to one second; crash recovery for these values MAY round to the last persisted tick rather than the exact last position.
- **FR-049c**: System MUST provide "Export library" and "Import library" actions that produce and consume a portable bundle containing all machine-local library state: the list of songs (keyed by audio content hash), sections, theme assignments, per-section parameter overrides, folder structure, and user preferences. The bundle MUST NOT include the audio files themselves — audio is referenced by content hash and the user relocates audio on import. Import MUST offer a merge mode (add to existing library) and a replace mode (overwrite existing library). Any song in the imported bundle whose audio is not found on the target machine MUST appear in the library with a "source file missing" state until the user relocates it.

#### Migration

- **FR-050**: The previous dashboard and review UI, together with any server routes that exclusively served it, MUST be removed in the same change that ships the new UI. There is no parallel operation period.
- **FR-051**: The new UI MUST communicate with the backend through a versioned JSON API whose shape is designed for the screens in this spec, rather than inheriting the shape of prior server-rendered endpoints.

### Key Entities

- **Song**: An imported audio file with associated analysis output. Identity is the audio content hash (not the file path). Key attributes: audio content hash (identity), title, artist, duration, audio source path(s) — a single song may be known by multiple paths on disk — BPM, key, time signature, status (draft / analyzed / themed), folder membership.
- **Section**: A labeled time range within a song. Key attributes: start time, end time, kind (intro / verse / chorus / solo / bridge / outro), label, assigned theme, per-section parameter overrides. Sections belong to exactly one song.
- **Boundary**: A time point separating adjacent sections. A song carries both the active boundaries (producing the final section list) and alternate "ghost" boundaries detected by the analyzer but not promoted.
- **Theme**: A named, reusable lighting behavior. Key attributes: name, description, accent color, color swatches, per-kind animation preset. Themes are built-in for v0.
- **Theme assignment**: A mapping from a single section to exactly one theme, plus optional per-section parameter overrides (brightness, hit strength, dwell time, color shift).
- **Analysis result**: The per-detector output from the analysis pipeline (beats, bars, onsets, impacts, drops, chords, etc.) tied to a song. Immutable once computed; re-running analysis produces a replacement.
- **Export**: A rendered output file targeting a specific destination format (xLights project, FSEQ, xsq). Derived entirely from a song's sections, theme assignments, and parameter overrides.
- **Preferences**: The user's machine-local settings (dark/light, density, inspector visibility, last song, last screen, last playhead position, imported xLights layout path / contents).
- **xLights layout**: The user's prop and pixel configuration, imported once from their xLights install and reused across every song's export. Without a layout the export screen is unavailable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can go from opening the app to exporting their first themed song in under 15 minutes on a 3-minute song, assuming analysis completes successfully on the first try. This budget excludes per-detector retry time (FR-011); a retry does not restart the 15-minute clock.
- **SC-002**: Scrubbing through a 4-minute song on the timeline produces no perceptible frame drops or audio desync on a 5-year-old consumer laptop.
- **SC-003**: Assigning themes to every section of an 8-section song takes under 2 minutes of active user time once analysis is complete.
- **SC-004**: After closing and reopening the app, the user lands on the same screen with the same song and the same playhead position they had at close time, within 2 seconds of first paint, in at least 95% of sessions.
- **SC-005**: 100% of the visual-identity requirements from the design handoff (color tokens, typography, spacing grid, sharp corners, tabular numerals, unicode glyphs) are met on both dark and light modes — verifiable by side-by-side comparison with the prototype.
- **SC-006**: The entire 6-screen flow is usable with keyboard alone — a user can complete the first-song happy path (US1) without touching a mouse or trackpad, except for dropping the initial file and clicking the final export confirmation.
- **SC-007**: A library of 100 imported songs scrolls smoothly and filters instantly (under 200ms between keystroke and filtered list update).
- **SC-008**: Analysis state for a previously-analyzed song is available on the timeline within 1 second of selecting that song from the library — no re-running the pipeline.

## Assumptions

- **Hobbyist users, not enterprise.** A handful of Christmas-display hobbyists will use this; no multi-tenant, no role-based access, no audit logs. Distribution is informal (install instructions, eventually a downloadable shell).
- **Local-only, offline.** All audio, analysis, themes, and outputs stay on the user's machine. No cloud sync, no shared project space, no remote collaboration in v0.
- **Single active user per session.** No multi-cursor, no concurrent edits, no merge conflicts on section data.
- **Built-in themes only in v0.** Users pick from a fixed set of named themes; user-created or user-edited themes are out of scope for this feature (tracked separately as a future "Custom Theme Authoring" feature).
- **No undo/redo in v0.** Section edits and theme assignments are immediate and destructive (within the active song); reset-to-detected exists for sections, but there is no multi-step undo stack. Users who want to "undo" a theme change re-assign the prior theme.
- **Cutover migration.** The existing review/dashboard UI is deleted in the same change that ships the new one; no parallel operation period. Users of the old UI lose access at cutover and must adopt the new UI. There is no export/import path for state held only in the old UI.
- **Analysis pipeline unchanged.** The existing Python audio analysis stack (librosa, vamp, madmom, demucs, etc.) is not modified by this feature — only the UI layer and the JSON-API surface that exposes it.
- **Web-first, desktop-shell optional later.** The interface is delivered as a web app the user opens in a browser against a locally-running server. A desktop shell wrap is out of scope for v0, but the UI is architected so a future wrap does not require a rewrite.
- **Single-song analysis concurrency.** Only one song analyzes at a time; a second import queues.
- **Built-in theme set is stable for v0.** Theme IDs and parameter semantics do not change during v0 in ways that invalidate saved assignments. Any future theme-catalog change must include a migration path.

## Scope Exclusions (explicit non-goals for v0)

- User-authored or user-edited themes (future feature).
- Multi-step undo / redo for any operation.
- Cloud sync or multi-device shared state.
- Multi-user concurrent editing.
- Desktop shell (Electron / Tauri) packaging.
- Batch operations across multiple songs (e.g., "theme these 10 songs the same way").
- Automated theme recommendation ("suggest a theme for this section").
- Audio editing — users cannot trim, stretch, or modify the source MP3 inside the app.
- Rendering real xLights output video inside the app — the render preview is a visual approximation, not a frame-accurate xLights render.
