# Tasks: Effect & Variant Library UI Wiring

**Input**: Design documents from `/specs/031-effect-variant-ui-wiring/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — constitution requires test-first development.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No project initialization needed — all infrastructure exists. This phase handles the one shared prerequisite.

- [x] T001 Rename "Variant" labels to "Alternate" for theme alternate layer sets in src/review/static/theme-editor.js (rename `renderVariantEditor` → `renderAlternateEditor`, update UI labels "Variant 1" → "Alternate 1", update `getVariantData` → `getAlternateData`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add variant data caching to theme editor state so all user stories can consume variant data.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Add `variantCache` dict to theme editor state object and implement `loadVariantsForEffect(effectName)` function that fetches from `/variants?effect={name}` and caches results in `state.variantCache` in src/review/static/theme-editor.js
- [x] T003 Update `getLayerDataFromContainer()` in src/review/static/theme-editor.js to extract `variant_ref` from layer row DOM (read `data-variant-ref` attribute) and include it in the returned layer data object

**Checkpoint**: Foundation ready — variant data fetching and serialization in place.

---

## Phase 3: User Story 1 — Browse and Apply Variants in Theme Editor (Priority: P1) MVP

**Goal**: When a user selects an effect for a layer, an inline variant picker appears showing matching variants from the library. Selecting a variant populates parameter overrides and sets `variant_ref`.

**Independent Test**: Open theme editor → add layer → select effect → verify variants appear → pick one → verify params populate → save → verify variant_ref persists on reload.

### Tests for User Story 1

- [x] T004 [P] [US1] Write integration test for variant picker API flow in tests/integration/test_theme_variant_picker.py: test that GET /variants?effect=Bars returns variants, test that selecting a variant and saving a theme preserves variant_ref, test that clearing variant_ref retains parameter values
- [x] T005 [P] [US1] Write integration test for broken variant_ref handling in tests/integration/test_theme_variant_picker.py: test that a theme with a variant_ref pointing to a deleted variant loads without error and shows a warning indicator

### Implementation for User Story 1

- [x] T006 [US1] Implement `renderVariantPicker(layerRow, effectName)` function in src/review/static/theme-editor.js that creates an inline expandable section below the effect dropdown, calls `loadVariantsForEffect()`, and renders variant cards with name, description, and tag badges (energy, tier, section roles)
- [x] T007 [US1] Wire variant picker into `createLayerRow()` in src/review/static/theme-editor.js: call `renderVariantPicker()` after effect select creation; on effect change, clear and re-render picker for new effect; on variant select, set `data-variant-ref` on the layer row and call `applyVariantToLayer()`
- [x] T008 [US1] Implement `applyVariantToLayer(layerRow, variant)` in src/review/static/theme-editor.js that populates parameter overrides from variant.parameter_overrides, marks variant-provided params with CSS class `variant-provided`, and refreshes the parameter UI via existing `refreshLayerParams()`
- [x] T009 [US1] Implement `detachVariant(layerRow)` in src/review/static/theme-editor.js that clears `data-variant-ref`, removes `variant-provided` CSS class from all params (converting them to manual overrides), and collapses the variant picker to "No variant selected" state
- [x] T010 [US1] Add broken variant_ref detection in `createLayerRow()` in src/review/static/theme-editor.js: when loading a layer with `variant_ref` that doesn't match any variant in cache, show a warning badge ("Variant not found") and allow the user to detach or pick a new variant
- [x] T011 [US1] Add variant picker CSS styles in src/review/static/theme-editor.css: `.variant-picker` collapsible section, `.variant-card` with hover state, `.variant-selected` highlight, `.variant-provided` parameter badge, `.variant-warning` for broken refs, tag badge styles for energy/tier/section

**Checkpoint**: User Story 1 fully functional — variant picker works in theme editor, variant_ref persists on save/reload.

---

## Phase 4: User Story 2 — Context-Aware Variant Suggestions (Priority: P2)

**Goal**: When a theme has mood/energy/occasion metadata set, the variant picker ranks variants by contextual relevance using the scoring API.

**Independent Test**: Create theme with mood "aggressive" → add layer → select effect → verify high-energy variants appear first with score indicators.

### Tests for User Story 2

- [x] T012 [P] [US2] Write integration test for context-aware scoring in tests/integration/test_theme_variant_picker.py: test that POST /variants/query with energy_level=high returns variants sorted by score, test that score breakdown is included in response

### Implementation for User Story 2

- [x] T013 [US2] Implement `buildScoringContext()` in src/review/static/theme-editor.js that reads current theme metadata (mood, occasion, genre) from the edit form and maps mood to energy_level (aggressive→high, ethereal→low, etc.) and determines tier_affinity from layer position (bottom=background, top=hero)
- [x] T014 [US2] Update `renderVariantPicker()` in src/review/static/theme-editor.js to call POST `/variants/query` with scoring context when theme metadata is available (fallback to GET `/variants?effect=X` when no context), sort results by score descending, and show a relevance indicator (score badge or bar) on each variant card
- [x] T015 [US2] Display variant tag details in picker cards in src/review/static/theme-editor.js: add small badges for energy_level, tier_affinity, and section_roles on each variant card so users can see why a variant ranks high or low

**Checkpoint**: User Stories 1 AND 2 both work — picker shows ranked variants when theme context exists, falls back to unranked list otherwise.

---

## Phase 5: User Story 3 — Standalone Variant Library Browser (Priority: P3)

**Goal**: A dedicated page at `/variants/` where users can browse all variants, filter by multiple dimensions, view details, and see coverage statistics.

**Independent Test**: Navigate to `/variants/` → verify all variants listed grouped by effect → apply filters → verify results narrow → click variant → verify detail view shows full info → check coverage stats panel.

### Tests for User Story 3

- [x] T016 [P] [US3] Write integration test for variant browser page serving in tests/integration/test_variant_api_browse.py: test that GET /variants/ returns HTML page, test that existing API endpoints still work alongside the page route

### Implementation for User Story 3

- [x] T017 [US3] Add page-serve route to src/review/variant_routes.py: `@variant_bp.route("/")` serves variant-library.html (before the existing API routes to avoid path conflicts)
- [x] T018 [P] [US3] Create src/review/static/variant-library.html with shared navbar include, filter bar section, variant list section, variant detail panel, and coverage stats section
- [x] T019 [US3] Implement variant list and filtering in src/review/static/variant-library.js: fetch all variants from GET /variants on load, render grouped by base_effect with counts, implement filter controls (effect dropdown, energy toggle, tier toggle, section multi-select, scope toggle, free-text search) that re-fetch with query params
- [x] T020 [US3] Implement variant detail view in src/review/static/variant-library.js: clicking a variant card opens a detail panel showing full parameter_overrides table, all tags, description, direction_cycle info, and inherited base effect metadata (category, layer_role, prop_suitability)
- [x] T021 [US3] Implement coverage statistics panel in src/review/static/variant-library.js: fetch from GET /variants/coverage, render summary counts (total variants, effects with/without variants), render per-effect coverage bars showing variant count
- [x] T022 [US3] Create src/review/static/variant-library.css with styles for filter bar, variant cards, detail panel, coverage stats, and responsive layout matching existing dark theme CSS variables
- [x] T023 [US3] Add "Variant Library" nav item to NAV_ITEMS array in src/review/static/navbar.js after "Theme Editor" entry, with href `/variants/` and appropriate icon

**Checkpoint**: All 3 user stories independently functional. Full variant library accessible via both theme editor picker and standalone browser.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [x] T024 [P] Verify all existing tests still pass with `pytest tests/ -v` — no regressions from theme-editor.js changes
- [x] T025 Validate quickstart.md scenarios end-to-end: run web app, test variant picker in theme editor, test variant browser page, test coverage stats

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — rename can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (rename must be done before adding new variant functionality to avoid confusion)
- **User Story 1 (Phase 3)**: Depends on Phase 2 (needs variantCache and getLayerDataFromContainer changes)
- **User Story 2 (Phase 4)**: Depends on Phase 3 (builds on variant picker from US1)
- **User Story 3 (Phase 5)**: Depends on Phase 2 only (standalone page, independent of theme editor picker)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational only — core MVP
- **User Story 2 (P2)**: Depends on User Story 1 — extends the variant picker with scoring
- **User Story 3 (P3)**: Depends on Foundational only — can run in parallel with US1/US2

### Within Each User Story

- Tests written first and confirmed failing before implementation
- Implementation tasks follow dependency order within the story
- Story checkpoint validates independently before moving on

### Parallel Opportunities

- T004 + T005 (US1 tests) can run in parallel
- T006 + T011 (variant picker logic + CSS) can partially overlap (CSS can start early)
- T012 (US2 test) can run in parallel with US1 implementation
- T016, T017, T018 (US3 setup) can partially overlap with US1/US2 work
- US1 and US3 can run in parallel after Phase 2 (different files entirely)

---

## Parallel Example: User Story 1

```text
# Tests first (parallel):
T004: "Integration test for variant picker API flow in tests/integration/test_theme_variant_picker.py"
T005: "Integration test for broken variant_ref handling in tests/integration/test_theme_variant_picker.py"

# Then implementation (T006-T010 sequential, T011 CSS parallel with any):
T006: "Implement renderVariantPicker() in src/review/static/theme-editor.js"
T011: "Add variant picker CSS styles in src/review/static/theme-editor.css" [P with T006-T010]
```

## Parallel Example: US1 + US3 Concurrent

```text
# After Phase 2, these can run in parallel:
Developer A (Theme Editor): T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011
Developer B (Browser Page): T016 → T017 → T018 → T019 → T020 → T021 → T022 → T023
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Rename alternates (T001)
2. Complete Phase 2: Foundational cache + serialization (T002-T003)
3. Complete Phase 3: Variant picker in theme editor (T004-T011)
4. **STOP and VALIDATE**: Test variant picker independently
5. This alone delivers the core value — variant library accessible in the primary workflow

### Incremental Delivery

1. Setup + Foundational → Rename complete, cache ready
2. Add User Story 1 → Variant picker works in theme editor (MVP!)
3. Add User Story 2 → Picker now ranks by context (enhanced)
4. Add User Story 3 → Standalone browser available (reference tool)
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All API endpoints already exist and are tested — this is purely frontend work plus one page-serve route
- No Python model changes needed — variant_ref field already exists on EffectLayer
- Commit after each task or logical group
