# Quickstart: Effect & Variant Library UI Wiring

**Feature**: 031-effect-variant-ui-wiring

## Prerequisites

- Python 3.11+ with project dependencies installed (`pip install -e .`)
- Flask dev server runnable (`xlight-analyze review`)

## Development Workflow

### Run the web app

```bash
# Start with any analysis JSON (or no args for upload page)
xlight-analyze review
# Opens browser at localhost:5173
```

### Key pages

- **Theme Editor**: `http://localhost:5173/themes/` — where the variant picker will be added
- **Variant Library**: `http://localhost:5173/variants/` — new browser page (after implementation)

### Frontend development

No build step. Edit JS/CSS/HTML files in `src/review/static/` and refresh the browser.

### Test the variant API (already working)

```bash
# List all Bars variants
curl http://localhost:5173/variants?effect=Bars

# Score variants for a context
curl -X POST http://localhost:5173/variants/query \
  -H "Content-Type: application/json" \
  -d '{"base_effect": "Bars", "energy_level": "high", "tier_affinity": "foreground"}'

# Coverage stats
curl http://localhost:5173/variants/coverage
```

### Run tests

```bash
# All tests
pytest tests/ -v

# Variant API tests specifically
pytest tests/integration/test_variant_api_browse.py -v

# Theme integration tests
pytest tests/integration/test_themes_integration.py -v
```

## Files to modify

| File | Change |
|------|--------|
| `src/review/static/theme-editor.js` | Add variant picker to `createLayerRow()`, update `getLayerDataFromContainer()` |
| `src/review/static/theme-editor.css` | Add variant picker styles |
| `src/review/static/navbar.js` | Add "Variant Library" nav item |
| `src/review/variant_routes.py` | Add route to serve variant-library.html |
| `src/review/static/variant-library.html` | New page |
| `src/review/static/variant-library.js` | New page logic |
| `src/review/static/variant-library.css` | New page styles |

## Key code locations

- **Layer row creation**: `src/review/static/theme-editor.js` line 605 (`createLayerRow()`)
- **Layer data extraction**: `src/review/static/theme-editor.js` line 873 (`getLayerDataFromContainer()`)
- **Alternate editor** (formerly variant editor): `src/review/static/theme-editor.js` line 807 (`renderVariantEditor()`)
- **Variant API endpoints**: `src/review/variant_routes.py` lines 75-215
- **Navbar items**: `src/review/static/navbar.js` line 8 (`NAV_ITEMS`)
- **EffectLayer model**: `src/themes/models.py` line 24 (`variant_ref` field)
