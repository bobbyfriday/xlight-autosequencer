# Data Model: Unified Dashboard

**Feature**: 027-unified-dashboard | **Date**: 2026-03-31

## Entities

### LibraryEntry (existing, extended at serve time)

The core data structure for songs in the library. Stored in `~/.xlight/library.json`.

| Field | Type | Description |
|-------|------|-------------|
| source_hash | string | MD5 hash of source audio file (primary key) |
| source_file | string | Absolute path to source MP3 |
| filename | string | Basename of source file |
| analysis_path | string | Path to `_hierarchy.json` output |
| duration_ms | int | Song duration in milliseconds |
| estimated_tempo_bpm | float | Detected BPM |
| track_count | int | Number of timing tracks |
| stem_separation | bool | Whether stems were generated |
| analyzed_at | int | Unix timestamp in ms |
| relative_source_file | string? | Portable path (cross-environment) |
| relative_analysis_path | string? | Portable path (cross-environment) |

**Dashboard-enriched fields** (computed at serve time, not persisted):

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| title | string | ID3 tags or Genius cache or filename | Song title for display |
| artist | string | ID3 tags or Genius cache or "Unknown" | Artist name for display |
| quality_score | float | Analysis JSON `overall_quality` | 0-1 quality score |
| has_story | bool | `os.path.exists(story_path)` | Whether story JSON exists |
| has_phonemes | bool | `os.path.exists(phonemes_path)` | Whether phoneme data exists |
| file_exists | bool | `os.path.exists(source_file)` | Whether source MP3 still exists on disk |
| analysis_exists | bool | `os.path.exists(analysis_path)` | Whether analysis output exists |

### Theme (existing, from src/themes/models.py)

| Field | Type | Description |
|-------|------|-------------|
| name | string | Unique theme name (primary key) |
| mood | string | "ethereal", "aggressive", "dark", "structural" |
| occasion | string | "christmas", "halloween", "general" |
| genre | string | "rock", "pop", "classical", "any" |
| intent | string | Human-readable description of the theme's visual intent |
| layers | list[EffectLayer] | Ordered list of effect layers |
| palette | list[string] | Hex color strings for primary palette |
| accent_palette | list[string] | Hex color strings for accent colors |
| variants | list[ThemeVariant] | Alternative layer configurations |

**EffectLayer** (nested):

| Field | Type | Description |
|-------|------|-------------|
| effect | string | xLights effect name |
| blend_mode | string | Layer blending mode |
| parameter_overrides | dict | Effect-specific parameter overrides |

**ThemeVariant** (nested):

| Field | Type | Description |
|-------|------|-------------|
| layers | list[EffectLayer] | Alternative layer set |

**Custom theme storage**: Each custom theme is a standalone JSON file at `~/.xlight/custom_themes/{slug}.json` following the same schema as entries in `builtin_themes.json`.

### LayoutGrouping (existing, no changes)

Managed by the existing grouper module. No data model changes needed — the dashboard simply provides navigation to the existing grouper page.

## Relationships

```
LibraryEntry 1──* Analysis files (on disk)
LibraryEntry 1──? Story file (on disk, optional)
LibraryEntry 1──? Phoneme data (on disk, optional)
LibraryEntry 1──* Stem files (in .stems/<hash>/, optional)

Theme (built-in) ──read-only──> builtin_themes.json
Theme (custom) ──read/write──> ~/.xlight/custom_themes/*.json
```

## State Transitions

### AnalysisJob (existing, unchanged)

```
idle → running → done
                → error
```

### Library Entry Lifecycle (extended with delete)

```
[not exists] → analyzed → [updated via re-analyze]
                        → deleted (library entry removed)
                           → files kept on disk (default)
                           → files also deleted (optional)
```

### Custom Theme Lifecycle (new)

```
[not exists] → created → edited → saved
                       → deleted
built-in → duplicated → [enters custom lifecycle]
```
