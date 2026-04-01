# Research: Unified Dashboard

**Feature**: 027-unified-dashboard | **Date**: 2026-03-31

## R1: Shared Navigation Pattern for Multi-Page Vanilla JS App

**Decision**: Client-side JavaScript navbar injection via a shared `navbar.js` module loaded on every page.

**Rationale**: The project uses static HTML files served by Flask (no server-side templating like Jinja). A JS-injected navbar is the lowest-friction approach: each page adds two tags (`<link>` for CSS, `<script>` for JS) and the navbar renders itself. This avoids introducing a templating engine, build step, or iframe-based approach.

**Alternatives considered**:
- **Jinja2 templates**: Would require converting all HTML files to `.html` Jinja templates, adding `render_template()` calls to every route, and creating a base layout. High migration cost for existing pages.
- **iframe-based shell**: A single shell page with an iframe loading each tool. Breaks audio playback context, canvas rendering, and URL-based navigation. Poor UX.
- **Web Components**: `<nav-bar>` custom element. More elegant but adds complexity for a single-user local tool with no build system.

## R2: Unifying Upload Mode and Review Mode

**Decision**: Always register all routes in `create_app()`. The mode parameter controls which page opens first but doesn't restrict route availability.

**Rationale**: Currently, upload-mode routes (library, upload, progress) are only registered when `analysis_path is None`, and review-mode routes (analysis, audio, stems) are only registered when both paths are provided. The dashboard needs library routes available even in review mode. The simplest change: register both sets unconditionally. Guard route handlers that need a current job with a "no active job" check rather than conditional route registration.

**Alternatives considered**:
- **Two Flask apps behind a proxy**: Overly complex for a local tool.
- **Conditional redirects**: Keep mode separation but add redirect routes. Fragile and confusing URL model.

## R3: Theme CRUD Storage Pattern

**Decision**: Each custom theme is a standalone JSON file in `~/.xlight/custom_themes/`, named `{slugified_name}.json`. The existing `load_theme_library()` already reads this directory.

**Rationale**: The theme library loader already scans `~/.xlight/custom_themes/*.json` and merges results with built-in themes. Writing follows the same pattern: one file per theme, same JSON schema as built-in themes. No new storage mechanism needed.

**Alternatives considered**:
- **Single `custom_themes.json` file**: Simpler but risks corruption if write fails mid-file. One-file-per-theme is safer and allows individual theme backup/sharing.
- **SQLite database**: Overkill for <50 themes in a local tool.

## R4: Song Library Deletion and File Cleanup

**Decision**: `Library.remove_entry(hash)` removes the index entry. A separate `delete_files_for_entry(entry)` handles optional disk cleanup of analysis artifacts.

**Rationale**: Separation of concerns — library index management vs filesystem operations. The library entry stores paths to analysis files, stems directory, and story files. The delete function uses those paths to clean up. Default behavior is index-only removal (safe, reversible by re-analyzing).

**Alternatives considered**:
- **Always delete files**: Risky; user may want to keep large stem files while reorganizing library.
- **Soft delete (archive flag)**: Adds complexity for a feature users will rarely use.

## R5: Dashboard Song List — Server-Side vs Client-Side Processing

**Decision**: Client-side sorting and filtering. The existing `/library` endpoint returns all entries; the dashboard JS handles sort/filter/search in the browser.

**Rationale**: The expected scale is <200 songs. Transferring all entries as JSON and processing client-side is fast, avoids new server endpoints, and allows instant UI feedback (no round-trip for sort changes). The existing `/library` endpoint already returns the full list.

**Alternatives considered**:
- **Server-side pagination/sorting**: Necessary for 10k+ items. Premature for this scale.
- **Virtual scrolling**: Needed if list exceeds viewport significantly. Can be added later if library grows.

## R6: Existing Library Endpoint Enhancement

**Decision**: Extend the `/library` JSON response to include additional metadata needed by the dashboard: title, artist (from ID3 tags or Genius cache), and file existence status.

**Rationale**: The current `LibraryEntry` stores `filename`, `duration_ms`, `estimated_tempo_bpm`, `track_count`, `stem_separation`, and `analyzed_at`. The dashboard needs title and artist for display and search. These can be extracted at serve time from the analysis JSON (which stores Genius metadata) or from ID3 tags via mutagen. File existence is a quick `os.path.exists()` check for the "missing" indicator.

**Alternatives considered**:
- **Store title/artist in LibraryEntry**: Would require schema migration and re-analysis of existing entries. Better to derive at serve time.
- **Separate metadata endpoint**: Adds a second API call. Better to enrich the existing endpoint.
