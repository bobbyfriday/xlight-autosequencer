# HTTP Route Contracts: Unified Dashboard

**Feature**: 027-unified-dashboard | **Date**: 2026-03-31

## Page Routes

### Dashboard Homepage

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| GET | `/` | `dashboard.html` | Default landing page in all server modes |
| GET | `/library-view` | redirect → `/` | Backward compatibility |
| GET | `/upload` | redirect → `/` | Backward compatibility (old upload page) |

### Theme Editor

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| GET | `/themes/editor` | `theme-editor.html` | Theme browser and editor page |

### Existing Pages (modified with navbar)

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| GET | `/timeline` | `index.html` | Timeline viewer (navbar added) |
| GET | `/story-review` | `story-review.html` | Story review (navbar added) |
| GET | `/phonemes-view` | `phonemes.html` | Phoneme editor (navbar added) |
| GET | `/grouper` | `grouper.html` | Layout grouping (navbar added) |

## API Routes — Library (existing, extended)

### GET `/library`

Returns enriched song library listing.

**Response** `200 OK`:
```json
{
  "entries": [
    {
      "source_hash": "abc123def456",
      "filename": "mad_russians_christmas.mp3",
      "title": "Mad Russian's Christmas",
      "artist": "Trans-Siberian Orchestra",
      "duration_ms": 198000,
      "estimated_tempo_bpm": 148.5,
      "track_count": 22,
      "stem_separation": true,
      "analyzed_at": 1711843200000,
      "quality_score": 0.85,
      "has_story": true,
      "has_phonemes": false,
      "file_exists": true,
      "analysis_exists": true
    }
  ]
}
```

### DELETE `/library/<source_hash>`

Remove a song from the library.

**Request query parameters**:
- `delete_files` (optional, default `false`): If `true`, also delete analysis files, stems, and story files from disk.

**Response** `200 OK`:
```json
{
  "status": "deleted",
  "source_hash": "abc123def456",
  "files_deleted": false
}
```

**Response** `404 Not Found`:
```json
{
  "error": "Entry not found",
  "source_hash": "abc123def456"
}
```

## API Routes — Themes (new blueprint at `/themes`)

### GET `/themes/list`

Returns all themes (built-in + custom).

**Response** `200 OK`:
```json
{
  "themes": [
    {
      "name": "Ethereal Shimmer",
      "mood": "ethereal",
      "occasion": "general",
      "genre": "any",
      "intent": "Gentle, floating...",
      "palette": ["#1a1a2e", "#16213e", "#0f3460", "#e94560"],
      "accent_palette": ["#ff6b6b", "#ffd93d"],
      "layers": [
        {
          "effect": "Shimmer",
          "blend_mode": "Normal",
          "parameter_overrides": {}
        }
      ],
      "variants": [],
      "is_builtin": true
    }
  ]
}
```

### POST `/themes/create`

Create a new custom theme.

**Request body** `application/json`:
```json
{
  "name": "My Custom Theme",
  "mood": "aggressive",
  "occasion": "halloween",
  "genre": "rock",
  "intent": "Dark and energetic",
  "palette": ["#000000", "#ff0000", "#ff6600"],
  "accent_palette": ["#ffffff"],
  "layers": [
    {
      "effect": "Fire",
      "blend_mode": "Normal",
      "parameter_overrides": {}
    }
  ],
  "variants": []
}
```

**Response** `201 Created`:
```json
{
  "status": "created",
  "name": "My Custom Theme"
}
```

**Response** `409 Conflict` (name already exists):
```json
{
  "error": "Theme name already exists",
  "name": "My Custom Theme"
}
```

### PUT `/themes/<name>`

Update an existing custom theme.

**Request body**: Same as POST `/themes/create`.

**Response** `200 OK`:
```json
{
  "status": "updated",
  "name": "My Custom Theme"
}
```

**Response** `403 Forbidden` (attempting to edit built-in theme):
```json
{
  "error": "Cannot edit built-in theme",
  "name": "Ethereal Shimmer"
}
```

### DELETE `/themes/<name>`

Delete a custom theme.

**Response** `200 OK`:
```json
{
  "status": "deleted",
  "name": "My Custom Theme"
}
```

**Response** `403 Forbidden` (attempting to delete built-in theme):
```json
{
  "error": "Cannot delete built-in theme"
}
```

### POST `/themes/duplicate`

Duplicate a theme (built-in or custom) as a new custom theme.

**Request body**:
```json
{
  "source_name": "Ethereal Shimmer",
  "new_name": "My Ethereal Variant"
}
```

**Response** `201 Created`:
```json
{
  "status": "created",
  "name": "My Ethereal Variant"
}
```

## Static Assets

### Shared Navbar

All pages load:
```html
<link rel="stylesheet" href="/static/navbar.css">
<script src="/static/navbar.js"></script>
```

The navbar JS auto-initializes on DOMContentLoaded, injecting a `<nav>` element at the top of `<body>`. It reads `window.location.pathname` to determine the active section.

### Dashboard Page

```html
<link rel="stylesheet" href="/static/navbar.css">
<link rel="stylesheet" href="/static/dashboard.css">
<script src="/static/navbar.js"></script>
<script src="/static/dashboard.js"></script>
```

### Theme Editor Page

```html
<link rel="stylesheet" href="/static/navbar.css">
<link rel="stylesheet" href="/static/theme-editor.css">
<script src="/static/navbar.js"></script>
<script src="/static/theme-editor.js"></script>
```
