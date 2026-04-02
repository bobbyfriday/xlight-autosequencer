# Research: Effect & Variant Library UI Wiring

**Feature**: 031-effect-variant-ui-wiring
**Date**: 2026-04-01

## R1: Variant Picker Integration Point

**Decision**: Add inline expandable variant picker below the effect dropdown in each layer row within `createLayerRow()` (theme-editor.js, lines 605-699).

**Rationale**: The variant list per effect is small (typically 3-8 variants), so inline presentation avoids the overhead of a modal. The picker appears after effect selection and clears when the effect changes. This keeps the user in context while browsing variants.

**Alternatives considered**:
- Modal dialog: Rejected — too disruptive for a small selection set; modals break flow when editing multiple layers.
- Sidebar flyout: Rejected — story review flyouts work for complex content but variant selection is a simple pick-from-list action.

## R2: API Consumption Strategy

**Decision**: The theme editor's variant picker will call existing `/variants` endpoint (GET with `?effect=<name>` filter) for the basic picker, and `/variants/query` (POST with scoring context) for ranked suggestions when theme mood/energy context is available.

**Rationale**: Both endpoints are fully implemented and tested in `variant_routes.py`. The GET endpoint returns variants with `inherited` metadata (category, layer_role, prop_suitability from base effect). The POST endpoint scores variants against a `ScoringContext`. No new backend code needed.

**Alternatives considered**:
- New dedicated `/themes/api/variants` endpoint: Rejected — would duplicate existing variant_routes functionality. The theme editor JS can call `/variants` directly.
- Embedding variant data in the `/themes/api/effects` response: Rejected — would bloat the effects payload and couple variant data to effect loading.

## R3: Data Flow for variant_ref

**Decision**: When a user selects a variant in the picker:
1. Set a `data-variant-ref` attribute on the layer row DOM element
2. Populate parameter overrides from the variant's `parameter_overrides`
3. Mark variant-provided params with a CSS class to distinguish from user overrides
4. On save, `getLayerDataFromContainer()` extracts `variant_ref` from the DOM attribute

When a user detaches a variant:
1. Clear `data-variant-ref`
2. Keep current parameter values (they become manual overrides)
3. Remove the variant-provided CSS class from all params

**Rationale**: The `variant_ref` field already exists on `EffectLayer` and is serialized/deserialized correctly. The effect_placer resolution chain (variant params → layer overrides) already works. The UI just needs to set the field.

**Alternatives considered**:
- Store variant_ref in a hidden input: Works but data attributes are cleaner for DOM-based state in this codebase's pattern.

## R4: Variant Browser Page Architecture

**Decision**: Create a new standalone page (`variant-library.html` + `variant-library.js` + `variant-library.css`) served at `/variants/` via the existing variant blueprint. The page follows the same pattern as theme-editor: shared navbar, CSS variables for dark theme, vanilla JS with fetch calls.

**Rationale**: Consistent with existing page architecture (dashboard, theme-editor, story-review). No build step needed. The variant blueprint already has all the API endpoints; just needs a route to serve the HTML page.

**Alternatives considered**:
- Tab within theme editor: Rejected — the variant browser is a reference tool independent of theme editing; embedding it would clutter the theme editor.
- Reuse story-review flyout pattern: Rejected — the browser needs filtering, grouping, and detail views that warrant a full page.

## R5: Terminology in UI

**Decision**: In the UI, "variant" always means an effect variant from the library. The existing "theme variants" (alternate layer sets within a theme) will be renamed to "alternates" in the UI labels. The `renderVariantEditor()` function in theme-editor.js will be renamed to `renderAlternateEditor()` and its UI labels updated.

**Rationale**: Avoids user confusion between two different concepts sharing the same name. The data model field names (`ThemeVariant`, `variants` list on Theme) remain unchanged in Python — only UI-facing labels change.

**Alternatives considered**:
- Keep both as "variant": Rejected — user testing of the theme editor showed confusion when "Variant 1" (alternate layers) appeared alongside a variant picker for effect presets.
- Rename effect variants to "presets": Rejected — "variant" is the canonical term in the codebase and API routes; renaming would require changing URLs and backend code.

## R6: Navigation Integration

**Decision**: Add "Variant Library" as a fourth item in `navbar.js` NAV_ITEMS array, positioned after "Theme Editor". URL: `/variants/`, icon: library/grid icon.

**Rationale**: The variant browser is a top-level tool comparable to Theme Editor and Layout Grouping. It needs its own nav entry for discoverability. Placing it after Theme Editor groups the two related tools together.

**Alternatives considered**:
- Sub-item under Theme Editor: Rejected — navbar doesn't currently support nested items; adding that complexity is unjustified for one link.
