# Contract: Variant Picker API (Frontend ↔ Backend)

All endpoints already exist. This documents the contracts the frontend will consume.

## GET /variants?effect={name}

**Used by**: Theme editor variant picker (fetches variants when effect is selected)

**Request**:
```
GET /variants?effect=Bars
```

**Response** (200):
```json
{
  "variants": [
    {
      "name": "Bars Single 3D Half-Cycle",
      "base_effect": "Bars",
      "description": "Single bar sweeping in 3D with half-cycle rotation",
      "parameter_overrides": {
        "E_TEXTCTRL_Bars_BarCount": 1,
        "E_CHECKBOX_Bars_3D": true,
        "E_SLIDER_Bars_Cycles": 5
      },
      "tags": {
        "tier_affinity": "mid",
        "energy_level": "medium",
        "speed_feel": "moderate",
        "direction": "left-to-right",
        "section_roles": ["verse", "chorus"],
        "scope": "group",
        "genre_affinity": "any"
      },
      "direction_cycle": null,
      "is_builtin": true,
      "inherited": {
        "category": "bars-lines",
        "layer_role": "standalone",
        "duration_type": "section",
        "prop_suitability": {
          "SingleLine": "ideal",
          "Matrix": "good",
          "Tree": "good"
        }
      }
    }
  ],
  "total": 5,
  "filters_applied": {
    "effect": "Bars"
  }
}
```

## POST /variants/query

**Used by**: Theme editor context-aware ranking (when theme has mood/energy set)

**Request**:
```json
{
  "base_effect": "Bars",
  "energy_level": "high",
  "tier_affinity": "foreground",
  "section_role": "chorus",
  "genre": "rock",
  "min_score": 0.3
}
```

**Response** (200):
```json
{
  "results": [
    {
      "variant": { "...same shape as above..." },
      "score": 0.85,
      "breakdown": {
        "energy_match": 1.0,
        "tier_match": 0.8,
        "section_match": 0.7,
        "genre_match": 0.9
      }
    }
  ],
  "relaxed_filters": [],
  "total": 3
}
```

## GET /variants/coverage

**Used by**: Variant browser coverage statistics panel

**Response** (200):
```json
{
  "coverage": [
    {
      "effect": "Bars",
      "variant_count": 5,
      "has_variants": true
    },
    {
      "effect": "Butterfly",
      "variant_count": 0,
      "has_variants": false
    }
  ],
  "total_variants": 123,
  "effects_with_variants": 34,
  "effects_without_variants": 22
}
```

## GET /variants/{name}

**Used by**: Variant browser detail view

**Response** (200): Single variant object (same shape as array items above)
**Response** (404): `{"error": "Variant not found: {name}"}`
