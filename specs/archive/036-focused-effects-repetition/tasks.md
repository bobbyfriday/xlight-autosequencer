# Tasks: Focused Effect Vocabulary + Embrace Repetition

**Input**: Design documents from `/specs/036-focused-effects-repetition/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Included — the constitution requires test-first development (Principle IV).

**Organization**: Tasks grouped by user story. US1+US2 are P1 (core changes), US3+US4 are P2 (refinement+toggles).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: Add toggle flags and WorkingSet dataclass to existing codebase

- [X] T001 Add `focused_vocabulary: bool = True` and `embrace_repetition: bool = True` fields to the generation config dataclass in src/generator/models.py
- [X] T002 [P] Add WorkingSet and WorkingSetEntry dataclasses to src/generator/models.py per data-model.md (fields: effects, theme_name, effect_name, variant_name, weight, source)
- [X] T003 [P] Capture baseline metrics by running `python3 scripts/analyze_reference_xsq.py` on the auto-generated "12 - Magic" sequence in tmp/ and save output to specs/036-focused-effects-repetition/baseline_metrics.txt for before/after comparison

---

## Phase 2: Foundational

**Purpose**: WorkingSet derivation function — core algorithm that all user stories depend on

**CRITICAL**: US1 and US2 both depend on this being complete

- [X] T004 Write failing unit tests for WorkingSet derivation in tests/unit/test_working_set.py: test 1-layer theme, 3-layer theme (Stellar Wind example from data-model.md), theme with effect_pool, theme with alternates, weight normalization sums to 1.0, deduplication of same base effect across layers
- [X] T005 Implement `derive_working_set(theme: Theme, variant_library: VariantLibrary) -> WorkingSet` function in src/generator/effect_placer.py. Algorithm: layer 0 weight=0.40, each subsequent layer=previous/2 (min 0.05), effect_pool splits evenly, alternates at 0.05 each, normalize to sum=1.0, dedup same base effect
- [X] T006 Verify all tests from T004 pass

**Checkpoint**: WorkingSet derivation works for all theme shapes. Ready for integration.

---

## Phase 3: User Story 1 — Focused Working Set Per Theme (Priority: P1) MVP

**Goal**: Each theme produces a small, weighted effect pool. Top-5 effects account for 80%+ of placements. Top effect >25%.

**Independent Test**: Generate a sequence, run the analyzer. Check top-5 effect percentage and top-effect dominance.

### Tests for User Story 1

- [X] T007 [P] [US1] Write failing test in tests/unit/test_working_set.py: given a WorkingSet, weighted random selection over 1000 trials produces distribution within 10% of target weights
- [X] T008 [P] [US1] Write failing integration test in tests/integration/test_phase1_metrics.py: generate a sequence with focused_vocabulary=True, parse output XSQ with analyze_reference_xsq.py logic, assert top-5 effects >= 80% of placements

### Implementation for User Story 1

- [X] T009 [US1] Add `select_from_working_set(working_set: WorkingSet, rng: Random) -> WorkingSetEntry` function in src/generator/effect_placer.py that performs weighted random selection respecting the weight distribution
- [X] T010 [US1] Modify `place_effects()` in src/generator/effect_placer.py to derive a WorkingSet from the section's theme at the start of each section (when `focused_vocabulary=True`), and use it for tier 1-2 (BASE, GEO) effect selection instead of the fixed layer variant
- [X] T011 [US1] Modify tier 5-8 effect selection in src/generator/effect_placer.py: when `focused_vocabulary=True`, replace `_build_effect_pool()` / `_PROP_EFFECT_POOL` fallback with `select_from_working_set()` so prop/compound/hero tiers draw from the same WorkingSet as other tiers
- [X] T012 [US1] Modify `build_rotation_plan()` in src/generator/rotation.py: when `focused_vocabulary=True`, constrain the variant pool to only variants whose base_effect appears in the WorkingSet (pass WorkingSet to rotation plan builder)
- [X] T013 [US1] Wire WorkingSet through src/generator/plan.py: derive WorkingSet per theme in the section loop (between rotation plan build and place_effects call), pass to place_effects and rotation plan
- [X] T014 [US1] Verify T007 and T008 tests pass. Run analyzer on generated output and confirm top-5 >= 80%, top-1 >= 25%

**Checkpoint**: Generated sequences use a focused effect vocabulary. Effect distribution matches reference patterns.

---

## Phase 4: User Story 2 — Sustained Repetition Within Sections (Priority: P1)

**Goal**: Same effect+palette holds for an entire section on each non-beat-tier model. Consecutive repetition reaches 10+ per model.

**Independent Test**: Generate a sequence, run the analyzer. Check consecutive repetition counts on base-tier models.

### Tests for User Story 2

- [X] T015 [P] [US2] Write failing test in tests/unit/test_repetition_policy.py: given embrace_repetition=True, rotation engine assigns same variant to same group across all calls within one section (no intra-section dedup)
- [X] T016 [P] [US2] Write failing test in tests/unit/test_repetition_policy.py: given embrace_repetition=True, cross-section penalty is 0.85 (not 0.5) for same-label sections
- [X] T017 [P] [US2] Write failing test in tests/unit/test_repetition_policy.py: given embrace_repetition=True, beat tier (tier 4) groups are excluded from repetition policy changes (chase pattern preserved)

### Implementation for User Story 2

- [X] T018 [US2] Modify `build_rotation_plan()` in src/generator/rotation.py: when `embrace_repetition=True`, remove the `used_in_section` set tracking and the unused-variant preference logic (lines ~269-275) so the same variant is reused for every group within a section
- [X] T019 [US2] Modify cross-section penalty in src/generator/rotation.py: when `embrace_repetition=True`, change the penalty multiplier from 0.5 to 0.85 for same-label section reuse (lines ~260-267)
- [X] T020 [US2] Add tier-4 guard in src/generator/rotation.py: ensure beat-tier (tier 4) groups are excluded from the repetition policy changes — they continue using existing chase pattern behavior regardless of the toggle
- [X] T021 [US2] Verify T015, T016, T017 tests pass. Run analyzer on generated output and confirm consecutive repetition >= 10 on base-tier models

**Checkpoint**: Effects sustain within sections. Base-tier models show 10+ consecutive same effect+palette.

---

## Phase 5: User Story 3 — Theme Working Set Weights (Priority: P2)

**Goal**: Top effect accounts for 25%+ of placements, top 2 for 50%+. Steep distribution curve.

**Independent Test**: Generate a sequence, count placements by effect type. Verify steep distribution.

### Implementation for User Story 3

- [X] T022 [US3] Review the weight distribution from T005 implementation against all 21 built-in themes in src/themes/builtin_themes.json — verify each theme produces a WorkingSet where the top entry has weight >= 0.25 and top 2 entries sum >= 0.45. Adjust halving ratio if needed.
- [X] T023 [US3] Write integration test in tests/integration/test_phase1_metrics.py: generate sequences for at least 2 different themes, verify top effect >= 25% and top 2 >= 50% of placements in each
- [X] T024 [US3] If any themes produce flat distributions (e.g., single-layer themes with large effect_pools), add special handling in `derive_working_set()` to ensure the primary layer variant always gets >= 0.30 weight even after pool splitting

**Checkpoint**: Weight distribution produces steep curves matching reference sequence patterns.

---

## Phase 6: User Story 4 — Independent Toggle (Priority: P2)

**Goal**: Each behavior independently toggleable. Disabled = identical to pre-Phase-1 baseline.

**Independent Test**: Generate with toggles off, compare to baseline. Generate with each toggle individually, verify independent effects.

### Implementation for User Story 4

- [X] T025 [US4] Write test in tests/unit/test_working_set.py: with focused_vocabulary=False, place_effects uses original _PROP_EFFECT_POOL and unconstrained variant selection (pre-Phase-1 behavior)
- [X] T026 [US4] Write test in tests/unit/test_repetition_policy.py: with embrace_repetition=False, rotation engine applies original 0.5x cross-section penalty and intra-section dedup (pre-Phase-1 behavior)
- [X] T027 [US4] Add conditional logic in src/generator/effect_placer.py: check `config.focused_vocabulary` before using WorkingSet. When False, fall through to original _PROP_EFFECT_POOL and layer-based selection
- [X] T028 [US4] Add conditional logic in src/generator/rotation.py: check `config.embrace_repetition` before applying new penalty values. When False, use original 0.5x penalty and used_in_section dedup
- [X] T029 [US4] Write regression test in tests/integration/test_phase1_metrics.py: with both toggles=False, assert existing test suite passes and output metrics match baseline_metrics.txt from T003
- [X] T030 [US4] Verify all existing tests pass with both toggles disabled (no regressions)

**Checkpoint**: Toggles work independently. Disabled state matches pre-Phase-1 baseline exactly.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [X] T031 Run full analyzer comparison: generate a sequence with both toggles enabled, run analyze_reference_xsq.py, compare all metrics against baseline_metrics.txt and reference sequences. Document results in specs/036-focused-effects-repetition/validation_results.md
- [X] T032 Run `pytest tests/ -v` to confirm full test suite passes (no regressions)
- [X] T033 Clean up any dead code: remove _PROP_EFFECT_POOL constant and _build_effect_pool() function from src/generator/effect_placer.py if they are only used when focused_vocabulary=False (keep them if the toggle path needs them)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001, T002 from Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (T004-T006)
- **US2 (Phase 4)**: Depends on Foundational (T004-T006). Can run in parallel with US1.
- **US3 (Phase 5)**: Depends on US1 (needs WorkingSet wired up)
- **US4 (Phase 6)**: Depends on US1 + US2 (needs both behaviors implemented to toggle them)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Foundational only — no dependency on other stories
- **US2 (P1)**: Foundational only — no dependency on other stories. Can parallelize with US1.
- **US3 (P2)**: Depends on US1 (weight tuning requires working WorkingSet)
- **US4 (P2)**: Depends on US1 + US2 (toggle testing requires both features)

### Within Each User Story

- Tests written first and FAIL before implementation (TDD per constitution)
- Implementation tasks are sequential within a story
- Verify checkpoint before moving to next story

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- T007 and T008 can run in parallel (different test files)
- T015, T016, T017 can run in parallel (same test file but independent test cases)
- US1 and US2 implementation can run in parallel after Foundational phase

---

## Parallel Example: US1 + US2

```text
# After Foundational phase (T004-T006) is complete:

# Stream A: User Story 1 (focused vocabulary)
T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014

# Stream B: User Story 2 (embrace repetition) — can run in parallel
T015 → T016 → T017 → T018 → T019 → T020 → T021
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006)
3. Complete Phase 3: US1 — Focused Vocabulary (T007-T014)
4. Complete Phase 4: US2 — Embrace Repetition (T015-T021)
5. **STOP and VALIDATE**: Run analyzer, compare to baseline and reference sequences
6. If metrics look good, proceed to US3+US4 for polish

### Incremental Delivery

1. Setup + Foundational → WorkingSet derivation works
2. US1 → Effect distribution matches reference patterns → Validate
3. US2 → Repetition matches reference patterns → Validate
4. US3 → Weight tuning verified across all themes → Validate
5. US4 → Toggles work, no regressions → Validate
6. Polish → Full comparison documented

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- The constitution requires TDD (test-first) — tests are included
- Baseline metrics (T003) are essential for before/after comparison
- The analyzer tool (scripts/analyze_reference_xsq.py) is the primary validation mechanism
- Beat tier (Tier 4) is explicitly excluded from all Phase 1 changes
