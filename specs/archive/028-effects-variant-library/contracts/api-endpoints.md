# API Contracts: Effects Variant Library

**Feature**: 028-effects-variant-library
**Date**: 2026-04-01

All endpoints are added to the existing Flask review server (`src/review/server.py`).

---

## Endpoints

### `GET /variants`

List all variants with optional filtering.

**Query Parameters**:

| Param | Type | Description |
|-------|------|-------------|
| `effect` | string | Filter by base effect name |
| `energy` | string | Filter: low, medium, high |
| `tier` | string | Filter: background, mid, foreground, hero |
| `section` | string | Filter by section role |
| `prop` | string | Filter by prop type suitability |
| `scope` | string | Filter: single-prop, group |
| `q` | string | Free-text search across name and description |

**Response** (200):
```json
{
  "variants": [
    {
      "name": "Meteors Gentle Rain",
      "base_effect": "Meteors",
      "description": "Soft falling meteors...",
      "parameter_overrides": { "E_SLIDER_Meteors_Count": 5 },
      "tags": {
        "tier_affinity": "background",
        "energy_level": "low",
        "speed_feel": "slow",
        "direction": "rain-down",
        "section_roles": ["verse", "intro"],
        "scope": "single-prop",
        "genre_affinity": "any"
      },
      "is_builtin": true,
      "inherited": {
        "category": "nature",
        "layer_role": "standalone",
        "duration_type": "section",
        "prop_suitability": { "matrix": "ideal", "arch": "good" }
      }
    }
  ],
  "total": 142,
  "filters_applied": { "energy": "low" }
}
```

---

### `GET /variants/<name>`

Get full detail for a single variant.

**Response** (200): Single variant object (same shape as list item above).

**Response** (404): `{ "error": "Variant not found: <name>" }`

---

### `POST /variants`

Create a new custom variant.

**Request body** (JSON):
```json
{
  "name": "Bars Fast Sweep Right",
  "base_effect": "Bars",
  "description": "Quick horizontal bars sweeping right, good for high-energy transitions",
  "parameter_overrides": {
    "E_SLIDER_Bars_BarCount": 4,
    "E_CHOICE_Bars_Direction": "Right",
    "E_SLIDER_Bars_Speed": 80
  },
  "tags": {
    "tier_affinity": "foreground",
    "energy_level": "high",
    "speed_feel": "fast",
    "direction": "sweep-right",
    "section_roles": ["chorus", "build"],
    "scope": "group",
    "genre_affinity": "any"
  }
}
```

**Response** (201): Created variant object.

**Response** (400): `{ "error": "Validation failed", "details": ["..."] }`

**Response** (409): `{ "error": "Variant name already exists: <name>" }`

---

### `PUT /variants/<name>`

Update an existing custom variant.

**Request body**: Same as POST (full replacement).

**Response** (200): Updated variant object.

**Response** (403): `{ "error": "Cannot edit built-in variant: <name>" }`

**Response** (404): `{ "error": "Variant not found: <name>" }`

---

### `DELETE /variants/<name>`

Delete a custom variant.

**Response** (200): `{ "deleted": "<name>" }`

**Response** (403): `{ "error": "Cannot delete built-in variant: <name>" }`

**Response** (404): `{ "error": "Variant not found: <name>" }`

---

### `POST /variants/import`

Import variants from an uploaded .xsq file.

**Request**: `multipart/form-data` with field `xsq_file` (the .xsq file).

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `dry_run` | bool | false | Preview without saving |
| `skip_duplicates` | bool | false | Auto-skip duplicates |

**Response** (200):
```json
{
  "imported": [
    { "name": "Bars_config_1", "base_effect": "Bars", "status": "new" }
  ],
  "duplicates": [
    { "name": "Fire_config_1", "base_effect": "Fire", "existing_name": "Fire Blaze", "status": "skipped" }
  ],
  "unknown": [
    { "effect_type": "NewEffect2025", "status": "flagged" }
  ],
  "summary": { "total_extracted": 45, "new": 32, "duplicates": 10, "unknown": 3 }
}
```

---

### `GET /variants/coverage`

Show variant coverage across base effects.

**Response** (200):
```json
{
  "coverage": [
    {
      "effect": "Bars",
      "category": "pattern",
      "variant_count": 8,
      "prop_coverage": 5,
      "tag_completeness": 0.87
    }
  ],
  "total_variants": 142,
  "effects_with_variants": 28,
  "effects_without_variants": 7
}
```

---

### `POST /variants/query`

Contextual variant query for the sequence generator (ranked results).

**Request body**:
```json
{
  "base_effect": "Meteors",
  "prop_type": "arch",
  "energy_level": "high",
  "tier_affinity": "foreground",
  "section_role": "chorus",
  "scope": "single-prop",
  "genre": "rock",
  "limit": 5
}
```

**Response** (200):
```json
{
  "results": [
    {
      "variant": { "name": "Meteors Storm Burst", "..." : "..." },
      "score": 0.92,
      "score_breakdown": {
        "prop_suitability": 1.0,
        "energy_match": 1.0,
        "tier_match": 1.0,
        "section_match": 0.7,
        "scope_match": 1.0,
        "genre_match": 0.8
      }
    }
  ],
  "relaxed_filters": [],
  "total_candidates": 12
}
```
