# Tasks: Section Transitions & End-of-Song Fade Out

**Input**: Design documents from `/specs/032-section-transitions-fadeout/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md
**Constitution**: v1.0.0 — Test-First Development (Principle IV) requires tests before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create new module and foundational dataclasses

- [X] T001 Create src/generator/transitions.py module with TransitionConfig, CrossfadeRegion, and FadeOutPlan dataclasses per data-model.md
- [X] T002 [P] Add optional transition_mode field to Theme in src/themes/models.py — str | None, default None, include in from_dict()/to_dict(), valid values: "none", "subtle", "dramatic"

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core transition infrastructure that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation

- [X] T003 [P] Write unit tests for TransitionConfig, CrossfadeRegion, FadeOutPlan dataclasses in tests/unit/test_transitions.py — test construction, defaults, validation of mode values
- [X] T004 [P] Write unit tests for compute_crossfade_duration() in tests/unit/test_transitions.py — test subtle mode returns ~1 beat, dramatic returns ~1 bar, none returns 0, clamping to half section length, various BPM values (80, 120, 150)
- [X] T005 [P] Write unit tests for Theme.transition_mode field in tests/unit/test_variant_theme_models.py — test from_dict()/to_dict() with transition_mode present and absent, backward compat

### Implementation for Foundation

- [X] T006 Implement compute_crossfade_duration(bpm, mode, section_duration_ms) in src/generator/transitions.py — returns fade duration in ms: none→0, subtle→60000/bpm (one beat), dramatic→240000/bpm (one bar, 4/4 time), clamped to half section_duration_ms per research.md R2
- [X] T007 Implement detect_same_effect_continuation(placement_a, placement_b) in src/generator/transitions.py — returns True if both placements have same effect_name, xlights_id, and parameters within 10% tolerance per research.md R4

**Checkpoint**: TransitionConfig model works, duration calculation is tempo-aware, same-effect detection works. All foundational tests pass.

---

## Phase 3: User Story 1 — Smooth Section Transitions with Crossfade (Priority: P1) MVP

**Goal**: Apply fade_in_ms/fade_out_ms at section boundaries for smooth transitions

**Independent Test**: Generate a sequence with a verse-to-chorus transition. Verify fade values are non-zero at the boundary.

### Tests for User Story 1

- [X] T008 [P] [US1] Write unit tests for apply_crossfades() in tests/unit/test_transitions.py — given two adjacent SectionAssignments with different effects, verify outgoing placements get fade_out_ms and incoming get fade_in_ms; given same-effect continuation, verify no fade applied; given "none" mode, verify all fades are 0
- [X] T009 [P] [US1] Write integration test in tests/integration/test_transitions_integration.py — generate placements for 3 sections (intro→verse→chorus) with real fixtures, apply crossfades, verify every boundary has non-zero fades on at least one group

### Implementation for User Story 1

- [X] T010 [US1] Implement apply_crossfades(assignments, config, hierarchy) in src/generator/transitions.py — iterate adjacent section pairs; for each group, find the last placement in section A and first in section B; if not a same-effect continuation, set fade_out_ms on A's last placement and fade_in_ms on B's first placement using compute_crossfade_duration(). Respect theme.transition_mode override when set.
- [X] T011 [US1] Integrate apply_crossfades() into build_plan() in src/generator/plan.py — call after all sections have group_effects populated (step 6 per research.md R6). Pass TransitionConfig from generation options.
- [X] T012 [US1] Add --transition-mode option to generate CLI command in src/cli.py — choice of "none", "subtle", "dramatic", default "subtle". Pass through to build_plan() config.

**Checkpoint**: Section boundaries have non-zero fade_in_ms/fade_out_ms values. Same-effect continuations skip crossfade. "none" mode produces zero fades. US1 is independently functional.

---

## Phase 4: User Story 2 — End-of-Song Fade Out (Priority: P1)

**Goal**: Progressive brightness fade-out during final section, following energy curve

**Independent Test**: Generate a sequence for a song with an "outro" label. Verify the final section's placements have fade_out_ms set, with upper tiers fading earlier.

### Tests for User Story 2

- [X] T013 [P] [US2] Write unit tests for build_fadeout_plan() in tests/unit/test_transitions.py — test outro detection (label="outro"), abrupt ending detection (no outro), progressive tier offsets for long outro (>8s), uniform fade for short outro (<8s), fade_out_ms values per tier
- [X] T014 [P] [US2] Write unit tests for apply_fadeout() in tests/unit/test_transitions.py — given a final section with 3 tiers of placements, verify hero tier gets largest fade_out_ms, base tier gets smallest; given abrupt ending, verify 3000ms fade on all tiers

### Implementation for User Story 2

- [X] T015 [US2] Implement build_fadeout_plan(assignments, hierarchy) in src/generator/transitions.py — detect final section; if label is "outro" use full section as fade region; else use last 3000ms (configurable via TransitionConfig.abrupt_end_fade_ms). Compute tier_offsets: progressive for >8s outros (hero=0.0, compound=0.2, prop=0.4, fidelity=0.6, base=0.8), uniform for short ones.
- [X] T016 [US2] Implement apply_fadeout(assignments, fadeout_plan) in src/generator/transitions.py — for each group in the final section, find its tier from the group name prefix (01_BASE→1, 06_PROP→6, 08_HERO→8). Set fade_out_ms on the last placement for each group, with duration = (1.0 - tier_offset) × total fade region. Optionally follow energy curve if hierarchy.energy_curves["full_mix"] is available.
- [X] T017 [US2] Integrate apply_fadeout() into build_plan() in src/generator/plan.py — call after apply_crossfades(). Build FadeOutPlan from the final assignment and hierarchy. Skip if TransitionConfig.fadeout_strategy is "none".

**Checkpoint**: Final section placements have progressive fade_out_ms values. Outro sections get full-length fades. Abrupt endings get 3-second fades. US2 is independently functional.

---

## Phase 5: User Story 3 — Section Boundary Snap Precision (Priority: P2)

**Goal**: Improve existing boundary snapping to prevent merges and crossovers

**Independent Test**: Create sections with boundaries near bar lines. After snapping, verify no zero-length sections exist and no boundaries crossed.

### Tests for User Story 3

- [X] T018 [P] [US3] Write unit tests for improved _snap_sections_to_bars() in tests/unit/test_snap_precision.py — test merge prevention (two boundaries snapping to same bar → shorter section absorbed), crossover prevention (snap window reduced when boundaries are close), existing behavior preserved for well-spaced boundaries

### Implementation for User Story 3

- [X] T019 [US3] Enhance _snap_sections_to_bars() in src/analyzer/orchestrator.py — after snapping, scan for zero-length or <2s sections and merge them into their longer neighbor (prefer merging into the preceding section). Before snapping each boundary, check that moving it wouldn't cross the next/previous boundary; reduce window if so.
- [X] T020 [US3] Add minimum section duration guard — after snap, if any section is shorter than 2000ms, log a warning and absorb it into the preceding section by moving the boundary back

**Checkpoint**: No zero-length sections after snapping. No boundary crossovers. Existing well-spaced boundaries are unchanged. US3 is independently functional.

---

## Phase 6: User Story 4 — Configurable Transition Behavior (Priority: P3)

**Goal**: Three transition modes + theme-level override

**Independent Test**: Generate the same song three times with different modes. Verify "none" matches pre-feature output, "subtle" and "dramatic" produce different fade durations.

### Tests for User Story 4

- [X] T021 [P] [US4] Write unit tests for mode override logic in tests/unit/test_transitions.py — test theme.transition_mode overrides global config; test None theme mode falls back to global; test all three modes produce expected duration ranges
- [X] T022 [P] [US4] Write integration test for backward compatibility in tests/integration/test_transitions_integration.py — generate with mode "none", compare fade values to pre-feature baseline (all zeros)

### Implementation for User Story 4

- [X] T023 [US4] Implement mode resolution in apply_crossfades() in src/generator/transitions.py — for each section boundary, resolve effective mode: theme.transition_mode if set, else config.mode. This is already scaffolded in T010 — this task ensures the override chain works correctly.
- [X] T024 [US4] Add transition_mode to 2-3 builtin themes in src/themes/builtin_themes.json — e.g., "The Void" gets "dramatic", "Glitch City" gets "none" (hard cuts suit the glitch aesthetic)

**Checkpoint**: Mode override works. "none" produces byte-identical fade values to pre-feature output. Theme preferences override global. US4 is independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate end-to-end quality and backward compatibility

- [X] T025 Validate backward compatibility — generate with --transition-mode none, confirm fade_in_ms/fade_out_ms are all 0 on every placement (SC-004)
- [X] T026 Run quickstart.md validation — verify all documented CLI options and behaviors work as described
- [ ] T027 Empirical xLights test — generate a sequence with crossfades, import into xLights, save, reopen, verify fade values survived. Document result in research.md as addendum.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational
  - US1 (Phase 3): No dependencies on other stories — **MVP**
  - US2 (Phase 4): No dependency on US1 (different post-processing pass)
  - US3 (Phase 5): No dependency on US1/US2 (snap is in analyzer, not generator)
  - US4 (Phase 6): Depends on US1 (extends mode resolution in apply_crossfades)
- **Polish (Phase 7)**: Depends on US1 + US2 at minimum

### User Story Dependencies

- **US1 (P1)**: Foundation only — crossfade application
- **US2 (P1)**: Foundation only — fade-out application (independent of crossfades)
- **US3 (P2)**: Foundation only — snap precision (independent, in analyzer pipeline)
- **US4 (P3)**: US1 — extends crossfade mode resolution with theme override

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Principle IV)
- Dataclasses → Logic → Integration with pipeline
- Commit after each task or logical group

### Parallel Opportunities

- T002 can run in parallel with T001 (different files)
- T003 + T004 + T005 can all run in parallel (different test areas)
- T008 + T009 can run in parallel (unit vs integration tests)
- T013 + T014 can run in parallel (different test scenarios)
- US1 and US2 can start in parallel after Foundation (independent post-processing passes)
- US3 can start in parallel with US1/US2 (different pipeline stage)
- T021 + T022 can run in parallel (unit vs integration)

---

## Parallel Example: User Story 1

```bash
# Launch tests in parallel:
Task T008: "Unit tests for apply_crossfades() in tests/unit/test_transitions.py"
Task T009: "Integration test in tests/integration/test_transitions_integration.py"

# After tests written, implement sequentially:
Task T010: "Implement apply_crossfades() in src/generator/transitions.py"
Task T011: "Integrate into build_plan() in src/generator/plan.py" (depends on T010)
Task T012: "Add CLI option in src/cli.py" (depends on T011)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (duration calculation + same-effect detection)
3. Complete Phase 3: User Story 1 (crossfades at boundaries)
4. **STOP and VALIDATE**: Generate a sequence, import into xLights, verify smooth transitions
5. Deliver: Crossfades replace hard cuts at section boundaries

### Incremental Delivery

1. Setup + Foundational → TransitionConfig + duration math
2. Add US1 → Crossfades at boundaries (MVP!)
3. Add US2 → End-of-song fade-out
4. Add US3 → Snap precision improvements
5. Add US4 → Configurable modes + theme override
6. Polish → Backward compat + xLights empirical test

### Parallel Team Strategy

With multiple developers after Foundation:
- Developer A: US1 (crossfades) + US4 (mode config)
- Developer B: US2 (fade-out) + US3 (snap precision)
- Developer C: Polish (validation + xLights test)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Constitution requires test-first: write tests, confirm they fail, then implement
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Key risk: xLights may recalculate fade values on save (T027 tests this empirically)
