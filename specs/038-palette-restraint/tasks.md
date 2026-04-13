# Tasks: Palette Restraint

**Input**: Design documents from `/specs/038-palette-restraint/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Included — the constitution requires test-first development (Principle IV).

**Organization**: Tasks grouped by user story. US1 is P1 (MVP), US2+US5 are P2, US3+US4 are P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: Add toggle flag and model field to existing codebase

- [ ] T001 Add `palette_restraint: bool = True` field to GenerationConfig dataclass in src/generator/models.py
- [ ] T002 [P] Add `music_sparkles: int = 0` field to EffectPlacement dataclass in src/generator/models.py
- [ ] T003 [P] Add `_TIER_PALETTE_CAP` constant dict and `_AUDIO_REACTIVE_EFFECTS` set to src/generator/effect_placer.py

---

## Phase 2: Foundational

**Purpose**: Palette trimming function — core algorithm that all user stories depend on

**CRITICAL**: US1 depends on this; US2-US5 build on it

- [ ] T004 Write failing unit tests for `restrain_palette()` in tests/unit/test_palette_restraint.py: test energy=0 gives 2 colors, energy=50 gives 3, energy=80 gives 4, single-color theme stays at 1, palette with fewer colors than target returns all
- [ ] T005 Implement `restrain_palette(palette: list[str], energy_score: int, tier: int) -> list[str]` in src/generator/effect_placer.py. Algorithm: `target = min(2 + energy // 33, _TIER_PALETTE_CAP[tier], len(palette))`, return `palette[:max(1, target)]`
- [ ] T006 Verify all tests from T004 pass

**Checkpoint**: Palette trimming works for all energy/tier combinations. Ready for integration.

---

## Phase 3: User Story 1 — Restrained Color Count (Priority: P1) MVP

**Goal**: Palettes use 2-4 active colors instead of all 8 slots. Average active colors per sequence is 2.0-4.0.

**Independent Test**: Generate a sequence, run `analyze_reference_xsq.py`. Average active colors per palette should be between 2.0 and 4.0.

### Tests for User Story 1

- [ ] T007 [P] [US1] Write failing integration test in tests/integration/test_palette_restraint.py: generate a sequence with palette_restraint=True, count active checkboxes per palette, assert average is between 2.0 and 4.0
- [ ] T008 [P] [US1] Write failing unit test in tests/unit/test_palette_restraint.py: with palette_restraint=False, palette list length equals theme palette length (no trimming)

### Implementation for User Story 1

- [ ] T009 [US1] Modify `place_effects()` in src/generator/effect_placer.py: when `palette_restraint=True`, call `restrain_palette()` on each palette before passing to `_make_placement()`. Pass section energy and group tier to the function
- [ ] T010 [US1] Wire `palette_restraint` toggle through src/generator/plan.py: pass `config.palette_restraint` to `place_effects()` call
- [ ] T011 [US1] Add conditional in src/generator/effect_placer.py: when `palette_restraint=False`, skip palette trimming (pass full palette as before)
- [ ] T012 [US1] Regenerate tests/validation/baseline_v1.json after default changes
- [ ] T013 [US1] Verify T007 and T008 tests pass. Run analyzer on generated output and confirm average active colors is 2.0-4.0

**Checkpoint**: US1 complete — all palettes are restrained to 2-4 active colors.

---

## Phase 4: User Story 2 — Hero Props Get More Palette Variety (Priority: P2)

**Goal**: Hero-tier models (tiers 7-8) receive up to 5-6 active colors while base-tier models stay at 2-3.

**Independent Test**: Generate a sequence with a layout containing both hero and base groups. Compare unique palette count per tier. Hero tier should have 30%+ more unique palettes.

### Tests for User Story 2

- [ ] T014 [P] [US2] Write failing test in tests/unit/test_palette_restraint.py: `restrain_palette()` with tier=8, energy=80 returns 5-6 colors; same palette with tier=1, energy=80 returns max 3

### Implementation for User Story 2

- [ ] T015 [US2] Verify `_TIER_PALETTE_CAP` values from T003 produce correct tier differentiation: tier 1-2 cap at 3, tier 7-8 cap at 6. Adjust if T014 test fails
- [ ] T016 [US2] Write integration test in tests/integration/test_palette_restraint.py: generate sequence, compare unique palette count for hero-tier vs base-tier groups, assert hero tier has 30%+ more unique palettes
- [ ] T017 [US2] Verify T014 and T016 tests pass

**Checkpoint**: Hero models get richer palettes than base models.

---

## Phase 5: User Story 5 — Accent Colors for High-Energy Sections (Priority: P2)

**Goal**: High-energy sections expand to 4-6 active colors via the energy scaling formula. Low-energy sections stay at 2-3.

**Independent Test**: Generate a sequence for a song with verse/chorus contrast. Compare average active colors between low and high energy sections. High-energy sections should average 1+ more active colors.

### Tests for User Story 5

- [ ] T018 [P] [US5] Write failing test in tests/unit/test_palette_restraint.py: `restrain_palette()` with energy=20 on tier 7 returns 2 colors; with energy=85 on tier 7 returns 4-5 colors (at least 2 more)

### Implementation for User Story 5

- [ ] T019 [US5] Write integration test in tests/integration/test_palette_restraint.py: generate sequence, group palettes by section energy (low <40, high >70), assert high-energy sections average 1+ more active colors
- [ ] T020 [US5] Verify T018 and T019 pass. The energy scaling formula from T005 should already handle this — no new code expected, just verification

**Checkpoint**: Energy-based color scaling confirmed across sections.

---

## Phase 6: User Story 3 — MusicSparkles on Pattern Effects (Priority: P3)

**Goal**: 10-30% of palettes have MusicSparkles enabled. Only on pattern-based effects, not audio-reactive ones.

**Independent Test**: Generate a sequence, inspect palettes. MusicSparkles appears on 10-30% of palettes and only on pattern-based effects.

### Tests for User Story 3

- [ ] T021 [P] [US3] Write failing unit test in tests/unit/test_palette_restraint.py: `compute_music_sparkles(energy=80, effect_name="Bars", rng)` returns non-zero value some percentage of the time; `compute_music_sparkles(energy=80, effect_name="VU Meter", rng)` always returns 0
- [ ] T022 [P] [US3] Write failing integration test in tests/integration/test_palette_restraint.py: generate sequence with palette_restraint=True, count palettes with MusicSparkles > 0, assert 10-30% of total

### Implementation for User Story 3

- [ ] T023 [US3] Implement `compute_music_sparkles(energy_score: int, effect_name: str, rng: Random) -> int` in src/generator/effect_placer.py. Returns 0 for audio-reactive effects. Otherwise probability = energy/200; if triggered, frequency = 20 + round(energy * 0.6)
- [ ] T024 [US3] Modify `_make_placement()` in src/generator/effect_placer.py: accept `music_sparkles` parameter and set it on EffectPlacement
- [ ] T025 [US3] Call `compute_music_sparkles()` in `place_effects()` for each placement when `palette_restraint=True`, pass result to `_make_placement()`
- [ ] T026 [US3] Modify `_serialize_palette()` in src/generator/xsq_writer.py: accept optional `music_sparkles: int` parameter. When > 0, append `C_SLIDER_MusicSparkles={value}` to the palette string
- [ ] T027 [US3] Update `_ensure_palette()` and palette serialization call chain in src/generator/xsq_writer.py to pass `music_sparkles` from EffectPlacement through to `_serialize_palette()`
- [ ] T028 [US3] Verify T021 and T022 pass

**Checkpoint**: MusicSparkles appears on pattern effects in high-energy sections.

---

## Phase 7: User Story 4 — Custom SparkleFrequency (Priority: P3)

**Goal**: MusicSparkles frequency scales with section energy — higher energy = more frequent sparkles.

**Independent Test**: Generate a sequence, compare MusicSparkles values across sections. Values should correlate with section energy.

### Tests for User Story 4

- [ ] T029 [P] [US4] Write failing test in tests/unit/test_palette_restraint.py: `compute_music_sparkles(energy=20, ...)` when triggered returns value in 20-35 range; `compute_music_sparkles(energy=90, ...)` when triggered returns value in 70-80 range

### Implementation for User Story 4

- [ ] T030 [US4] Verify the energy-scaled frequency formula from T023 (`20 + round(energy * 0.6)`) already produces correct range: energy=20 → 32, energy=90 → 74. No new code expected — this is verification that US3 implementation covers US4
- [ ] T031 [US4] Write integration test in tests/integration/test_palette_restraint.py: generate sequence, collect all non-zero MusicSparkles values grouped by section energy, assert higher-energy sections have higher average sparkle frequency
- [ ] T032 [US4] Verify T029 and T031 pass

**Checkpoint**: SparkleFrequency varies meaningfully with section energy.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T033 Verify `palette_restraint=False` produces identical output to pre-feature behavior (regression test in tests/integration/test_palette_restraint.py)
- [ ] T034 Run `pytest tests/ -v` to confirm full test suite passes with no regressions
- [ ] T035 Run analyzer comparison: generate sequence with toggle on, run `analyze_reference_xsq.py`, document metrics in specs/038-palette-restraint/validation_results.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — MVP target
- **US2 (Phase 4)**: Depends on Phase 2 — can run parallel with US1 (different test focus)
- **US5 (Phase 5)**: Depends on Phase 2 — can run parallel with US1 (verification only)
- **US3 (Phase 6)**: Depends on Phase 2 — independent of US1/US2/US5
- **US4 (Phase 7)**: Depends on US3 (uses compute_music_sparkles from T023)
- **Polish (Phase 8)**: Depends on all user stories complete

### Parallel Opportunities

- T001, T002, T003 can run in parallel (different files/locations)
- T007, T008 can run in parallel (different test files)
- T014, T018 can run in parallel (same test file but independent tests)
- T021, T022, T029 can run in parallel (independent test cases)
- US1, US2, US5 can run in parallel after foundational phase
- US3 can start any time after foundational phase

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006)
3. Complete Phase 3: US1 (T007-T013)
4. **STOP and VALIDATE**: Average active colors is 2.0-4.0
5. This alone delivers the biggest visual improvement

### Incremental Delivery

1. US1 → palette restraint working (MVP)
2. US2 + US5 → tier differentiation + energy scaling confirmed
3. US3 + US4 → MusicSparkles with energy-scaled frequency
4. Polish → regression tests, analyzer validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- US2 and US5 are largely verification tasks — the core algorithm from US1 handles both
- US4 is verification that US3's formula covers the frequency scaling requirement
- Total: 35 tasks across 8 phases
