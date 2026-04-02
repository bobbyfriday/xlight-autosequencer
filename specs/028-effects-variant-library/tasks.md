# Tasks: Effects Variant Library

**Input**: Design documents from `/specs/028-effects-variant-library/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Constitution**: v1.0.0 — Test-First Development (Principle IV) requires tests before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create module structure and test fixtures

- [X] T001 Create src/variants/ module with __init__.py per plan.md project structure
- [X] T002 [P] Create test fixture files: tests/fixtures/variants/valid_custom_variant.json and tests/fixtures/variants/builtin_variants_minimal.json with sample variant data matching data-model.md schema
- [X] T003 [P] Create tests/fixtures/xsq/sample_sequence.xsq — minimal valid .xsq file with 3-4 distinct effect configurations for import testing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core variant data model, validation, and library — MUST complete before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation

- [X] T004 [P] Write unit tests for EffectVariant and VariantTags dataclasses in tests/unit/test_variant_models.py — test from_dict(), field defaults, serialization to dict
- [X] T005 [P] Write unit tests for validate_variant() in tests/unit/test_variant_validator.py — test valid variant, missing fields, invalid base_effect, out-of-range parameters, invalid tag enums
- [X] T006 [P] Write unit tests for VariantLibrary in tests/unit/test_variant_library.py — test load from builtin + custom merge, get(), query by filters, save_custom_variant(), delete_custom_variant()

### Implementation for Foundation

- [X] T007 Implement EffectVariant and VariantTags dataclasses with from_dict()/to_dict() in src/variants/models.py — fields per data-model.md, validation enums as module constants
- [X] T008 Implement validate_variant() in src/variants/validator.py — accepts dict + EffectLibrary, returns list of error strings, validates base_effect exists, parameter storage_names valid, values in range, tag enums valid
- [X] T009 Implement VariantLibrary class in src/variants/library.py — load_variant_library() loads src/variants/builtin_variants.json + ~/.xlight/custom_variants/*.json, get() by name, query() with multi-filter AND logic, save_custom_variant(), delete_custom_variant()
- [X] T010 Create initial src/variants/builtin_variants.json with schema_version "1.0.0" and 5-10 seed variants for testing (Bars, Meteors, Color Wash, Fire variants)

**Checkpoint**: Foundation ready — EffectVariant model loads, validates, queries, and persists. All foundational tests pass.

---

## Phase 3: User Story 1 — Browse and Discover Effect Variants (Priority: P1) MVP

**Goal**: Users can browse, filter, and find effect variants by base effect, prop type, energy, tier, section role, and other tags via CLI and web dashboard.

**Independent Test**: Load the variant library and run queries with filters — verify correct results returned with names, descriptions, and parameter values.

### Tests for User Story 1

- [X] T011 [P] [US1] Write unit tests for variant list/show/coverage CLI commands in tests/unit/test_variant_cli.py — test output format, filter application, empty results handling
- [X] T012 [P] [US1] Write integration tests for GET /variants, GET /variants/<name>, GET /variants/coverage endpoints in tests/integration/test_variant_api_browse.py — test filter params, response shape, 404 handling

### Implementation for User Story 1

- [X] T013 [US1] Add `variant list` CLI command in src/cli.py — options: --effect, --energy, --tier, --section, --prop, --scope, --format (table/json). Table output: Name, Base Effect, Energy, Tier, Speed, Direction, Scope, Description. Loads VariantLibrary and applies filters per contracts/cli-commands.md
- [X] T014 [US1] Add `variant show <name>` CLI command in src/cli.py — case-insensitive lookup, display full variant detail including inherited base effect info (category, layer_role, duration_type, prop_suitability) per contracts/cli-commands.md
- [X] T015 [US1] Add `variant coverage` CLI command in src/cli.py — show variant count per base effect, prop coverage, tag completeness per contracts/cli-commands.md
- [X] T016 [P] [US1] Add GET /variants endpoint in src/review/server.py — query params: effect, energy, tier, section, prop, scope, q (free-text). Returns variants with inherited base effect dimensions per contracts/api-endpoints.md
- [X] T017 [P] [US1] Add GET /variants/<name> endpoint in src/review/server.py — returns single variant with inherited info, 404 if not found per contracts/api-endpoints.md
- [X] T018 [P] [US1] Add GET /variants/coverage endpoint in src/review/server.py — returns coverage stats per contracts/api-endpoints.md

**Checkpoint**: Users can browse and search variants via CLI (`variant list --energy high --prop arch`) and web dashboard (GET /variants?energy=high&prop=arch). US1 is independently functional.

---

## Phase 4: User Story 2 — Import Variants from Existing Sequences (Priority: P2)

**Goal**: Extract proven effect configurations from .xsq sequence files and import them as variants with deduplication detection.

**Independent Test**: Point the importer at a .xsq file with multiple effects — verify extracted variants have correct parameters, duplicates are flagged, unknown effects are preserved with warnings.

### Tests for User Story 2

- [X] T019 [P] [US2] Write unit tests for extract_variants_from_xsq() in tests/unit/test_variant_importer.py — test extraction from sample .xsq, deduplication detection, unknown effect handling, auto-naming
- [X] T020 [P] [US2] Write integration test for variant import CLI and POST /variants/import endpoint in tests/integration/test_variant_import.py — test dry-run, skip-duplicates, file upload

### Implementation for User Story 2

- [X] T021 [US2] Implement extract_variants_from_xsq() in src/variants/importer.py — uses parse_xsq() from src/generator/xsq_writer.py to get EffectPlacement objects, groups by (effect_name, sorted parameters) for dedup, auto-generates names from effect + distinguishing params, logs source palettes/blend modes for reference, flags unknown effects
- [X] T022 [US2] Add `variant import <xsq-path>` CLI command in src/cli.py — options: --dry-run, --auto-name, --skip-duplicates. Shows per-variant status and summary count per contracts/cli-commands.md
- [X] T023 [P] [US2] Add POST /variants/import endpoint in src/review/server.py — multipart file upload, dry_run and skip_duplicates query params, returns imported/duplicates/unknown summary per contracts/api-endpoints.md

**Checkpoint**: Import from .xsq produces correctly extracted, deduplicated variant entries. US2 is independently functional.

---

## Phase 5: User Story 3 — Create and Edit Custom Variants (Priority: P2)

**Goal**: Users can manually create, edit, and delete custom effect variants via CLI and web dashboard with full validation.

**Independent Test**: Create a custom variant with parameters and tags, edit it, verify changes persist, delete it, verify it's gone.

### Tests for User Story 3

- [X] T024 [P] [US3] Write unit tests for variant create/edit/delete CLI commands in tests/unit/test_variant_crud_cli.py — test creation, validation errors, edit of custom, rejection of built-in edit, deletion
- [X] T025 [P] [US3] Write integration tests for POST/PUT/DELETE /variants endpoints in tests/integration/test_variant_api_crud.py — test create, 409 name conflict, edit, 403 built-in, delete, 404 not found

### Implementation for User Story 3

- [X] T026 [US3] Add `variant create` CLI command in src/cli.py — options: --from-file, --effect, --name. Interactive prompts for effect selection, parameter overrides, tags. Validates via validate_variant() before saving per contracts/cli-commands.md
- [X] T027 [US3] Add `variant edit <name>` CLI command in src/cli.py — options: --from-file. Rejects built-in variants. Validates updated variant per contracts/cli-commands.md
- [X] T028 [US3] Add `variant delete <name>` CLI command in src/cli.py — rejects built-in variants per contracts/cli-commands.md
- [X] T029 [P] [US3] Add POST /variants endpoint in src/review/server.py — validate, check name uniqueness, save to custom dir. Returns 201/400/409 per contracts/api-endpoints.md
- [X] T030 [P] [US3] Add PUT /variants/<name> endpoint in src/review/server.py — validate, reject built-in edits (403), replace custom variant per contracts/api-endpoints.md
- [X] T031 [P] [US3] Add DELETE /variants/<name> endpoint in src/review/server.py — reject built-in deletes (403), remove custom variant per contracts/api-endpoints.md

**Checkpoint**: Full CRUD on custom variants works via both CLI and web dashboard. Validation catches invalid params and out-of-range values. US3 is independently functional.

---

## Phase 6: User Story 4 — Link Variants to Themes (Priority: P3)

**Goal**: Theme layers can reference variants by name. The sequence generator resolves variant parameters during placement with fallback to base effect defaults.

**Independent Test**: Assign a variant to a theme layer, generate a sequence plan, verify the variant's parameters appear in the output. Remove the variant, verify fallback to defaults with a warning.

### Tests for User Story 4

- [x] T032 [P] [US4] Write unit tests for EffectLayer.variant_ref and theme validation in tests/unit/test_variant_theme_models.py — test variant_ref parsing, validation of ref against VariantLibrary, fallback on missing ref
- [x] T033 [P] [US4] Write integration test for variant resolution in generator in tests/integration/test_variant_theme_integration.py — test parameter resolution chain (base → variant → theme override), missing variant fallback

### Implementation for User Story 4

- [x] T034 [US4] Add optional variant_ref field to EffectLayer dataclass in src/themes/models.py — str | None, default None, include in from_dict()/to_dict()
- [x] T035 [US4] Update validate_theme() in src/themes/validator.py — when variant_ref is set: validate it exists in VariantLibrary, validate variant's base_effect matches layer's effect field. Warn (not error) on missing variant per FR-008
- [x] T036 [US4] Update load_theme_library() in src/themes/library.py — accept optional variant_library parameter for variant_ref validation
- [x] T037 [US4] Update effect_placer.py to resolve variants in src/generator/effect_placer.py — in _make_placement() or place_effects_on_group(), when layer has variant_ref: look up variant, merge variant.parameter_overrides over base effect defaults, then merge layer.parameter_overrides on top. Resolution chain: base defaults → variant overrides → theme layer overrides

**Checkpoint**: Themes can reference variants. Generator resolves variant→parameters. Missing variants fall back gracefully. US4 is independently functional.

---

## Phase 7: User Story 5 — Categorize and Tag for Automated Selection (Priority: P3)

**Goal**: The sequence generator can automatically select the best variant for a placement context using weighted multi-dimensional scoring with progressive fallback.

**Independent Test**: Query the library with a context (prop type + energy + tier + section role) and verify ranked results. Query with no matches and verify graceful fallback returns results.

### Tests for User Story 5

- [X] T038 [P] [US5] Write unit tests for rank_variants() scorer in tests/unit/test_variant_scorer.py — test scoring weights, exact match vs adjacent vs mismatch, progressive fallback order, empty result handling
- [X] T039 [P] [US5] Write integration test for POST /variants/query endpoint in tests/integration/test_variant_query.py — test contextual query, score breakdown, relaxed filters in response

### Implementation for User Story 5

- [X] T040 [US5] Implement rank_variants() in src/variants/scorer.py — accepts query context (base_effect, prop_type, energy_level, tier_affinity, section_role, scope, genre) + VariantLibrary + EffectLibrary. Scores each variant per weighted model in data-model.md (prop=0.30, energy=0.25, tier=0.20, section=0.15, scope=0.05, genre=0.05). Returns sorted list of (variant, score, breakdown)
- [X] T041 [US5] Implement progressive fallback in src/variants/scorer.py — when no results above threshold: drop section_role → drop genre → widen energy → widen tier → drop scope → return all for base effect by prop suitability
- [X] T042 [US5] Add POST /variants/query endpoint in src/review/server.py — accepts context JSON, returns ranked variants with scores and breakdown per contracts/api-endpoints.md
- [X] T043 [US5] Integrate scorer with effect_placer.py in src/generator/effect_placer.py — in _build_effect_pool() or tier 6-7 rotation logic, use rank_variants() to select variant instead of round-robin from _PROP_EFFECT_POOL when VariantLibrary is available

**Checkpoint**: Generator uses scored variant selection. Fallback ensures placement never fails. US5 is independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Populate the built-in catalog and validate coverage

- [X] T044 Populate src/variants/builtin_variants.json with ~30-40 curated core variants extracted from existing theme layers in builtin_themes.json and generator effect pool in effect_placer.py — each variant with complete tags per data-model.md
- [X] T045 Import variants from a single .xsq sequence file using variant import CLI to validate importer and expand catalog toward 100+ target
- [X] T046 Run variant coverage CLI to identify gaps by effect category and prop type, then hand-curate additional variants to fill the most critical gaps
- [ ] T047 Validate all built-in variants pass validate_variant() and have complete tags (tier_affinity, energy_level, speed_feel, direction, section_roles, scope, genre_affinity)
- [ ] T048 Run quickstart.md validation — verify all documented CLI commands and API endpoints work as described

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - US1 (Phase 3): No dependencies on other stories
  - US2 (Phase 4): No dependencies on other stories (uses parse_xsq which already exists)
  - US3 (Phase 5): No dependencies on other stories
  - US4 (Phase 6): No hard dependency on US1-3, but benefits from having variants in library
  - US5 (Phase 7): No hard dependency on US1-4, but benefits from variants + theme integration
- **Polish (Phase 8)**: Depends on US1 + US2 + US3 at minimum (need CRUD + import + browse to populate)

### User Story Dependencies

- **US1 (P1)**: Independent — browse/query existing library
- **US2 (P2)**: Independent — import from .xsq
- **US3 (P2)**: Independent — manual CRUD
- **US4 (P3)**: Independent — theme integration (can test with manually created JSON)
- **US5 (P3)**: Independent — scoring engine (can test with seed variants)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Principle IV)
- Models → Validators → Library → CLI/API endpoints
- Core implementation before integration

### Parallel Opportunities

- T002 + T003 can run in parallel (different fixture files)
- T004 + T005 + T006 can run in parallel (different test files)
- T011 + T012 can run in parallel (CLI tests vs API tests)
- T016 + T017 + T018 can run in parallel with T013-T015 (web endpoints vs CLI commands, different files)
- US1, US2, US3 can all start in parallel after Foundation
- T029 + T030 + T031 can run in parallel (different endpoints, same file but independent functions)

---

## Parallel Example: User Story 1

```bash
# Launch tests in parallel:
Task T011: "Unit tests for variant CLI commands in tests/unit/test_variant_cli.py"
Task T012: "Integration tests for browse API endpoints in tests/integration/test_variant_api_browse.py"

# After tests written, launch CLI and web implementations in parallel:
Task T013-T015: "CLI variant list/show/coverage commands in src/cli.py" (sequential, same file)
Task T016-T018: "Web browse endpoints in src/review/server.py" (parallel, independent functions)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (model + validator + library)
3. Complete Phase 3: User Story 1 (browse + query)
4. **STOP and VALIDATE**: Load variant library, run CLI queries, hit web endpoints
5. Deliver: Users can browse and discover variants

### Incremental Delivery

1. Setup + Foundational → Core variant system works
2. Add US1 → Browse and discover (MVP!)
3. Add US2 → Import from .xsq sequences (library population)
4. Add US3 → Manual CRUD (custom variants)
5. Add US4 → Theme integration (variant references)
6. Add US5 → Automated selection (smart generator)
7. Polish → Populate catalog to 100+

### Parallel Team Strategy

With multiple developers after Foundation:
- Developer A: US1 (browse) + US5 (scoring)
- Developer B: US2 (import) + US3 (CRUD)
- Developer C: US4 (theme integration) + Polish (catalog population)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Constitution requires test-first: write tests, confirm they fail, then implement
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
