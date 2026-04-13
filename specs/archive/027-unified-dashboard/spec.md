# Feature Specification: Unified Dashboard

**Feature Branch**: `027-unified-dashboard`
**Created**: 2026-03-31
**Status**: Draft
**Input**: User description: "I want to create a new feature where we first come into a homepage, we see the files we currently have analysis on. We can upload a new file. I really want to flush that out and make that a first-class citizen. From that, I want the ability to go to a theme editor to manage your themes, manage your songs, manage your grouping, have all that in one place."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Song Library Homepage (Priority: P1)

A user launches the application and lands on a homepage that displays all previously analyzed songs in a clear, browsable list. Each song shows key metadata (title, artist, duration, BPM, quality score, stem availability, analysis date). The user can sort and filter this list. From any song entry, the user can navigate to review that song's timeline, story, phonemes, or sequence output.

**Why this priority**: The homepage is the central hub of the entire application. Without it, users have no way to discover or navigate to other features. It replaces the current basic upload page as the primary entry point and makes the tool feel like a cohesive product rather than a collection of disconnected views.

**Independent Test**: Can be fully tested by launching the app and verifying the song list renders with correct metadata, sorting works, and clicking a song navigates to its review page.

**Acceptance Scenarios**:

1. **Given** the user has 5 previously analyzed songs, **When** they open the application, **Then** all 5 songs appear on the homepage with title, artist, duration, BPM, quality score, and analysis date.
2. **Given** the homepage is loaded, **When** the user clicks on a song row, **Then** they are navigated to that song's timeline review view.
3. **Given** the homepage is loaded with multiple songs, **When** the user sorts by quality score descending, **Then** songs reorder from highest to lowest quality score.
4. **Given** no songs have been analyzed yet, **When** the user opens the application, **Then** a welcome state is shown with a prominent prompt to upload their first song.

---

### User Story 2 - Upload and Analyze from Homepage (Priority: P1)

A user can upload a new MP3 file directly from the homepage. The upload flow is integrated into the homepage experience rather than being a separate disconnected page. During analysis, the user sees real-time progress. When analysis completes, the new song appears in the library list and the user can immediately navigate to review it.

**Why this priority**: Uploading and analyzing songs is the core workflow. Integrating it into the homepage makes the primary user journey seamless (arrive, upload, analyze, review) without page-hopping.

**Independent Test**: Can be fully tested by uploading an MP3 from the homepage and verifying progress displays, analysis completes, and the song appears in the library.

**Acceptance Scenarios**:

1. **Given** the user is on the homepage, **When** they drag-and-drop an MP3 file onto the upload area, **Then** analysis begins and progress is displayed in real time.
2. **Given** analysis is running, **When** each algorithm completes, **Then** a progress indicator updates showing which step is active and how many are done.
3. **Given** analysis completes successfully, **When** the progress finishes, **Then** the new song appears in the library list and the user is offered a link to review it.
4. **Given** analysis fails, **When** an error occurs, **Then** the user sees a clear error message with an option to retry.

---

### User Story 3 - Navigation Hub to All Tools (Priority: P1)

From the homepage, the user can navigate to any management tool: theme editor, layout grouping editor, song story review, and phoneme editor. The navigation is persistent across all views so the user can always return to the homepage or jump between tools without losing context.

**Why this priority**: The homepage's value as a "unified dashboard" depends on it being a reliable navigation hub. Users need to move fluidly between tools without memorizing URLs or relying on back buttons.

**Independent Test**: Can be fully tested by navigating from the homepage to each tool and back, verifying all navigation links work and the current location is indicated.

**Acceptance Scenarios**:

1. **Given** the user is on the homepage, **When** they look at the navigation area, **Then** they see links to: Theme Editor, Layout Grouping, and the Song Library (current view).
2. **Given** the user is on any page in the application, **When** they look at the navigation, **Then** they can return to the homepage with one click.
3. **Given** the user navigates to the theme editor, **When** they click the homepage link, **Then** they return to the homepage with their previous library state preserved (sort order, filters).

---

### User Story 4 - Theme Management (Priority: P2)

A user navigates to a theme editor where they can browse all available themes (built-in and custom). They can view theme details including mood, palette colors, accent colors, and layer configurations. They can create new custom themes, edit existing custom themes, and preview how a theme's color palette looks.

**Why this priority**: Theme management is a key creative workflow. Currently themes exist only as JSON files with no visual management interface. A theme editor elevates themes from a developer concept to a user-facing feature.

**Independent Test**: Can be fully tested by navigating to the theme editor, browsing built-in themes, creating a custom theme with specific palette and mood, saving it, and verifying it persists.

**Acceptance Scenarios**:

1. **Given** the user navigates to the theme editor, **When** the page loads, **Then** all built-in and custom themes are listed with their name, mood, and a visual palette preview.
2. **Given** the user clicks "Create Theme", **When** they fill in name, mood, palette colors, accent colors, and base effect, **Then** the theme is saved as a custom theme and appears in the list.
3. **Given** a custom theme exists, **When** the user selects it for editing, **Then** they can modify any field and save the changes.
4. **Given** a built-in theme is selected, **When** the user views it, **Then** they can see all details but editing is disabled (read-only). They can duplicate it to create a custom variant.

---

### User Story 5 - Song Management Actions (Priority: P2)

From the homepage, users can perform management actions on their analyzed songs: delete a song from the library, re-run analysis with different options, view analysis details and quality breakdown, and open any of the song-specific tools (timeline, story, phonemes).

**Why this priority**: Beyond just listing songs, users need to manage their library. Re-analyzing with different settings and cleaning up old entries are common workflows that currently require CLI commands.

**Independent Test**: Can be fully tested by selecting a song and performing delete, re-analyze, and detail-view operations, verifying each action works correctly.

**Acceptance Scenarios**:

1. **Given** a song is in the library, **When** the user clicks a delete action, **Then** they are asked to confirm, and upon confirmation the song is removed from the library.
2. **Given** a song is in the library, **When** the user selects "Re-analyze", **Then** analysis runs again with the option to change analysis settings (stems, phonemes, story), and the updated results replace the previous entry.
3. **Given** the user clicks on a song's detail view, **When** the detail panel opens, **Then** they see the full quality score breakdown, track list, available stems, and analysis metadata.

---

### User Story 6 - Layout Grouping Access (Priority: P2)

From the homepage, a user can navigate to the layout grouping editor. The grouping editor retains its current drag-and-drop functionality for organizing props into tier-based groups, but is now accessible as a first-class section of the unified dashboard rather than a hidden route.

**Why this priority**: Layout grouping is essential for sequence generation but is currently accessible only via a direct URL. Making it a top-level navigation item makes the end-to-end workflow (analyze songs, set up groups, choose themes, generate sequence) discoverable.

**Independent Test**: Can be fully tested by navigating to the layout grouping editor from the homepage, loading a layout file, and performing drag-and-drop grouping operations.

**Acceptance Scenarios**:

1. **Given** the user clicks "Layout Grouping" in the navigation, **When** the grouping editor loads, **Then** they can load an xLights layout file and see their props organized by tier.
2. **Given** the grouping editor is loaded, **When** the user drags a prop from one group to another, **Then** the prop moves and the change can be saved.

---

### Edge Cases

- What happens when the library file is missing or corrupted? The homepage should display an empty state and allow uploads rather than showing an error.
- What happens when a song's analysis file has been deleted from disk but the library entry remains? The song should show a "missing" indicator with an option to re-analyze or remove the entry.
- What happens when the user uploads a file that has already been analyzed? The system should detect the duplicate (by file hash) and offer to re-analyze or navigate to the existing entry.
- What happens when analysis is running and the user navigates away from the homepage? Analysis should continue in the background and the result should appear when the user returns.

## Clarifications

### Session 2026-03-31

- Q: Should song-specific tools (timeline, story, phonemes) render inside the dashboard frame or as separate pages? → A: Song tools open as standalone pages but with a shared nav bar injected at the top of each page.
- Q: Should the dashboard be available in all server launch modes or only in upload/library mode? → A: Dashboard is always available. When launched with a specific file, that song's tool opens but the nav bar is present so the user can navigate to the dashboard at any time.
- Q: When deleting a song, should it remove just the library entry or also delete files from disk? → A: Remove the library entry and offer an optional checkbox to also delete analysis files from disk (default: keep files).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST display a homepage as the default landing page when launched without a specific file. When launched with a specific file, the app opens to that song's tool page but the dashboard remains accessible via the shared nav bar.
- **FR-002**: The homepage MUST list all songs in the analysis library with title, artist, duration, BPM, quality score, stem availability, and analysis date.
- **FR-003**: The song list MUST support sorting by any displayed column (title, duration, BPM, quality score, date).
- **FR-004**: The song list MUST support text-based filtering/search across song titles and artists.
- **FR-005**: The homepage MUST provide an integrated upload area for new MP3 files with drag-and-drop support.
- **FR-006**: Upload and analysis progress MUST be displayed in real time on the homepage.
- **FR-007**: The application MUST provide a shared navigation bar at the top of every page (homepage, theme editor, layout grouping, and all song-specific tool pages) with links to: Homepage (Song Library), Theme Editor, and Layout Grouping.
- **FR-008**: The navigation MUST indicate which section is currently active. Song-specific tool pages (timeline, story, phonemes) open as standalone pages with the shared nav bar, not embedded within the dashboard.
- **FR-009**: The theme editor MUST display all built-in and custom themes with name, mood, and a visual color palette preview.
- **FR-010**: Users MUST be able to create new custom themes specifying name, mood, occasion, genre, color palette, accent palette, and layer configuration.
- **FR-011**: Users MUST be able to edit and delete their custom themes.
- **FR-012**: Built-in themes MUST be displayed as read-only with an option to duplicate as a custom theme.
- **FR-013**: Users MUST be able to delete songs from the library (with confirmation). The delete confirmation MUST include an optional checkbox to also remove analysis files, stems, and story files from disk (default: keep files on disk).
- **FR-014**: Users MUST be able to re-analyze a song with different analysis options.
- **FR-015**: Users MUST be able to view a song's analysis detail including quality score breakdown and track list.
- **FR-016**: From a song entry, users MUST be able to navigate to that song's timeline review, story review, or phoneme editor.
- **FR-017**: The homepage MUST display an appropriate empty state when no songs have been analyzed.
- **FR-018**: The application MUST detect duplicate uploads by file hash and offer to re-analyze or navigate to the existing entry.
- **FR-019**: Analysis MUST continue running in the background if the user navigates away and results MUST appear when the user returns.

### Key Entities

- **Song Entry**: Represents an analyzed song in the library. Attributes include source file reference, file hash, title, artist, duration, tempo, quality score, available stems, analysis date, and references to analysis/story/phoneme outputs.
- **Theme**: Represents a visual theme for sequence generation. Attributes include name, mood, occasion, genre, color palette, accent palette, intent description, and layer effect configurations. Can be built-in (read-only) or custom (editable).
- **Layout Grouping**: Represents a saved arrangement of xLights props organized into tier-based groups for sequence generation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate from the homepage to any tool (theme editor, layout grouping, song review) within 2 clicks.
- **SC-002**: Users can upload and begin analyzing a new song within 10 seconds of landing on the homepage.
- **SC-003**: Users can find a specific song in a library of 50+ songs within 15 seconds using sort or filter.
- **SC-004**: Users can create a new custom theme and see it listed alongside built-in themes in under 2 minutes.
- **SC-005**: Users can complete the full workflow (upload, analyze, review, configure theme, set up groups) without using the command line or manually editing files.
- **SC-006**: All previously analyzed songs are visible on the homepage upon launch with no manual refresh or file path entry required.

## Assumptions

- The existing library index is the source of truth for analyzed songs. The homepage reads from this existing data structure.
- The homepage is a new default route that replaces the current basic upload page as the entry point.
- New pages follow the same vanilla JavaScript + HTML + CSS pattern used by existing pages (no frontend framework migration).
- Theme creation and editing writes to the existing custom themes directory following the established theme file format.
- The layout grouping editor's existing functionality is preserved as-is; the change is making it accessible from the unified navigation.
- Song metadata (title, artist) comes from ID3 tags or from Genius lookup results stored in the analysis cache.
