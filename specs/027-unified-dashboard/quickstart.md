# Quickstart: Unified Dashboard

**Feature**: 027-unified-dashboard | **Date**: 2026-03-31

## What This Feature Does

Replaces the disconnected upload/library pages with a unified dashboard homepage. Adds a shared navigation bar to all pages, a theme editor for managing visual themes, and song management actions (delete, re-analyze, detail view).

## Key Files to Understand First

1. **`src/review/server.py`** — Flask app factory (`create_app`). Currently has two modes (upload/review). This feature unifies them so dashboard routes are always available.

2. **`src/library.py`** — `Library` class with `upsert()` and `all_entries()`. This feature adds `remove_entry()` and `delete_files_for_entry()`.

3. **`src/themes/library.py`** — `ThemeLibrary` with `load_theme_library()`. This feature adds `save_custom_theme()` and `delete_custom_theme()`.

4. **`src/review/static/`** — All HTML/JS/CSS for the frontend. New files: `dashboard.*`, `theme-editor.*`, `navbar.*`.

## How to Run

```bash
# Start the server (dashboard is the homepage)
xlight-analyze review

# Or with a specific file (opens that file's timeline, dashboard still accessible via nav)
xlight-analyze review song_analysis.json

# Run tests
pytest tests/unit/test_dashboard_routes.py tests/unit/test_library_delete.py -v
```

## Architecture Overview

```
Browser                          Flask Server
  │                                  │
  ├─ GET / ──────────────────────── dashboard.html (song library + upload)
  ├─ GET /themes/editor ─────────── theme-editor.html
  ├─ GET /timeline ──────────────── index.html (+ navbar)
  ├─ GET /story-review ──────────── story-review.html (+ navbar)
  ├─ GET /phonemes-view ─────────── phonemes.html (+ navbar)
  ├─ GET /grouper ───────────────── grouper.html (+ navbar)
  │                                  │
  ├─ GET /library ───────────────── JSON: enriched song list
  ├─ DELETE /library/<hash> ─────── Remove song entry
  ├─ GET /themes/list ───────────── JSON: all themes
  ├─ POST /themes/create ────────── Create custom theme
  ├─ PUT /themes/<name> ─────────── Update custom theme
  ├─ DELETE /themes/<name> ───────── Delete custom theme
  └─ POST /themes/duplicate ─────── Duplicate theme as custom
```

## Implementation Order

1. **Shared navbar** (`navbar.js`, `navbar.css`) — foundation for all navigation
2. **Inject navbar into existing pages** — modify HTML files to load navbar
3. **Dashboard homepage** (`dashboard.html/js/css`) — song list, sort, filter, empty state
4. **Upload integration** — embed upload flow in dashboard, reuse existing endpoints
5. **Song management** — delete endpoint, re-analyze action, detail panel
6. **Unified server mode** — register all routes unconditionally
7. **Theme routes** (`theme_routes.py`) — CRUD API for themes
8. **Theme editor UI** (`theme-editor.html/js/css`) — browse, create, edit, duplicate
9. **Tests** — route tests, library deletion tests

## Conventions

- Dark theme: `#1a1a1a` background, `#4a9eff` accent blue, `#a78bfa` secondary purple
- No frontend framework — vanilla JS, DOM manipulation, fetch API
- Timestamps as integer milliseconds
- Flask blueprints for route grouping (theme routes)
- JSON for all API responses
