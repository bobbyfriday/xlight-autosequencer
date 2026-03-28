# Tasks: Sequence Generator

**Input**: Design documents from `/specs/020-sequence-generator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per Constitution Principle IV (Test-First Development).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create module structure and test fixtures

- [x] T001 Create generator module structure: `src/generator/__init__.py`, empty files for `models.py`, `energy.py`, `theme_selector.py`, `effect_placer.py`, `value_curves.py`, `xsq_writer.py`, `plan.py`
- [x] T002 [P] Create test directory `tests/unit/test_generator/` with `__init__.py` and empty test files: `test_energy.py`, `test_theme_selector.py`, `test_effect_placer.py`, `test_value_curves.py`, `test_xsq_writer.py`, `test_plan.py`
- [x] T003 [P] Reuse existing layout fixture at `tests/fixtures/grouper/simple_layout.xml` in `tests/fixtures/sample_layout.xml` with 6-8 models across different types (matrix, arch, vertical, single line) and realistic positions/pixel counts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and energy derivation that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement data model classes in `src/generator/models.py`: `SongProfile`, `SectionEnergy`, `SequencePlan`, `SectionAssignment`, `EffectPlacement`, `XsqDocument`, `GenerationConfig` per data-model.md — include validation (frame alignment, parameter range clamping, start < end)
- [x] T005 Write failing tests for energy derivation in `tests/unit/test_generator/test_energy.py`: test average energy from known L5 curve frames, test L0 impact boost (+5 per impact, capped at 100), test mood tier mapping (0-33=ethereal, 34-66=structural, 67-100=aggressive), test edge cases (empty curve, no impacts, all impacts)
- [x] T006 Implement energy derivation in `src/generator/energy.py`: `derive_section_energies(sections, energy_curves, energy_impacts) -> list[SectionEnergy]` — extract full_mix L5 frames per section time range, average, boost by impact count, assign mood tier. Make tests pass.

**Checkpoint**: Data models defined, energy derivation working with tests passing.

---

## Phase 3: User Story 1 — End-to-End Sequence Generation (Priority: P1) 🎯 MVP

**Goal**: Given an MP3 and layout, generate a valid `.xsq` file with themed effects placed on models aligned to timing tracks.

**Independent Test**: Run generator on fixture MP3 + sample layout → open resulting `.xsq` in xLights → verify effects on timeline.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T007 [P] [US1] Write failing tests for theme selection in `tests/unit/test_generator/test_theme_selector.py`: test energy-to-mood mapping selects correct mood themes, test occasion filtering (christmas/halloween/general), test genre filtering, test adjacent section variety (no same theme twice in a row), test repeated section type gets same theme with different variation_seed, test fallback broadening when no themes match (genre→"any", then occasion→"general")
- [x] T008 [P] [US1] Write failing tests for effect placement in `tests/unit/test_generator/test_effect_placer.py`: test layer-to-tier mapping (bottom layers→tiers 1-2, mid→3-4, top→7-8), test duration_type instance repetition (section=1, bar=per bar, beat=per beat, trigger=per event), test energy-driven density (high~90%, low~50% of marks), test fade calculation (section/bar get proportional 200-500ms, beat/trigger get 0), test clean cut at section boundaries, test frame alignment (all times multiples of 25), test flat model fallback when no power groups
- [x] T009 [P] [US1] Write failing tests for value curve generation in `tests/unit/test_generator/test_value_curves.py`: test linear curve shape mapping, test logarithmic curve shape, test exponential curve shape, test step curve shape, test input_min/max → output_min/max range mapping, test downsampling to ≤100 control points, test normalized x positions (0.0-1.0 within effect span)
- [x] T010 [P] [US1] Write failing tests for XSQ writer in `tests/unit/test_generator/test_xsq_writer.py`: test valid XML structure (root element, head, ColorPalettes, EffectDB, DisplayElements, ElementEffects), test FixedPointTiming="25", test mediaFile reference, test effect parameter serialization (comma-separated key=value), test color palette serialization (C_BUTTON_PaletteN format), test EffectDB deduplication (identical params share index), test palette deduplication, test value curve inline encoding (Active=TRUE|Id=...|Values=x:y|...), test frame-aligned times, test model names match layout

### Implementation for User Story 1

- [x] T011 [US1] Implement theme selection engine in `src/generator/theme_selector.py`: `select_themes(sections: list[SectionEnergy], theme_library: ThemeLibrary, genre: str, occasion: str) -> list[SectionAssignment]` — query by mood+occasion+genre, rotate for variety, assign variation_seed for repeated section types, fallback broadening. Make T007 tests pass.
- [x] T012 [US1] Implement effect placement engine in `src/generator/effect_placer.py`: `place_effects(assignment: SectionAssignment, groups: list[PowerGroup], effect_library: EffectLibrary, hierarchy: HierarchyResult) -> dict[str, list[EffectPlacement]]` — map layers to tiers, consult analysis_mapping for timing source, repeat by duration_type, apply energy-driven density, calculate fades, clean cut at boundaries, frame-align. Make T008 tests pass.
- [x] T013 [US1] Implement value curve generation in `src/generator/value_curves.py`: `generate_value_curves(placement: EffectPlacement, effect_def: EffectDefinition, hierarchy: HierarchyResult) -> dict[str, list[tuple[float, float]]]` — for each AnalysisMapping where supports_value_curve=true, extract analysis data, apply curve_shape, map ranges, downsample. Make T009 tests pass.
- [x] T014 [US1] Implement XSQ writer in `src/generator/xsq_writer.py`: `write_xsq(plan: SequencePlan, output_path: Path)` — build XsqDocument with deduplication, serialize to XML via ElementTree per xsq-schema.md contract, write file. Make T010 tests pass.
- [x] T015 [US1] Implement ID3 metadata reader as helper function in `src/generator/plan.py`: `read_song_metadata(audio_path: Path) -> SongProfile` — use mutagen for title/artist/genre from ID3 tags, populate SongProfile with HierarchyResult duration/bpm
- [x] T016 [US1] Write failing integration test in `tests/unit/test_generator/test_plan.py`: test full pipeline with mock HierarchyResult, mock layout props, real effect/theme libraries → verify SequencePlan has all sections assigned, all groups have placements, XSQ output is valid XML
- [x] T017 [US1] Implement plan builder in `src/generator/plan.py`: `build_plan(config: GenerationConfig, hierarchy: HierarchyResult, props: list[Prop], groups: list[PowerGroup], effect_library: EffectLibrary, theme_library: ThemeLibrary) -> SequencePlan` and `generate_sequence(config: GenerationConfig)` top-level function — orchestrate: load analysis, parse layout, derive energy, select themes, place effects, generate curves, write XSQ. Make T016 tests pass.
- [x] T018 [US1] Add non-interactive `generate` CLI command to `src/cli.py`: accept audio path, layout path, --output-dir, --genre, --occasion, --fresh, --no-wizard flags per cli-commands.md contract. Wire to `generate_sequence()`. Print section→theme summary and FSEQ rendering guidance on completion.

**Checkpoint**: Core generation pipeline works end-to-end via CLI. `xlight-analyze generate song.mp3 layout.xml --no-wizard` produces a valid `.xsq`.

---

## Phase 4: User Story 2 — Wizard-Driven Song Setup (Priority: P1)

**Goal**: Interactive CLI wizard that guides the user through MP3 selection, layout selection, metadata confirmation, and generation.

**Independent Test**: Run `xlight-analyze generate-wizard song.mp3` → wizard prompts for layout, shows detected metadata, allows overrides, generates sequence.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T019 [US2] Write failing tests for wizard in `tests/unit/test_generator/test_wizard.py`: test metadata detection from fixture MP3 with ID3 tags, test default values when no tags present, test config construction from wizard outputs, test TTY fallback to defaults

### Implementation for User Story 2

- [x] T020 [US2] Implement generation wizard in `src/generator_wizard.py`: `GenerationWizard` class following `src/wizard.py` pattern with step methods — `_step_audio()` (validate MP3 exists), `_step_layout()` (prompt for layout path, report model/group counts), `_step_metadata()` (read ID3 via mutagen, present title/artist/genre for confirmation/override), `_step_occasion()` (questionary select: general/christmas/halloween), `_step_confirm()` (show summary, confirm). Returns `GenerationConfig`. Make T019 tests pass.
- [x] T021 [US2] Add `generate-wizard` CLI command to `src/cli.py`: accept optional audio path argument, instantiate `GenerationWizard`, run wizard steps, pass config to `generate_sequence()`. Handle exit code 130 on user cancel.

**Checkpoint**: Interactive wizard works end-to-end. User can run `generate-wizard` and walk through the full flow.

---

## Phase 5: User Story 3 — Theme & Effect Assignment Preview (Priority: P2) + User Story 4 — FSEQ Guidance (Priority: P2)

**Goal**: Show the user a generation plan preview before writing, allow theme overrides. Include FSEQ rendering instructions in output.

**Independent Test**: Run generator → see section→theme table before generation → change a theme → confirm change reflected in output.

### Implementation for User Stories 3 & 4

- [x] T022 [US3] Implement plan preview display in `src/generator_wizard.py`: `_step_preview(plan: SequencePlan)` — use rich Table to show section label, time range, energy score, mood tier, theme name, and color palette swatches. Show group-to-effect summary per tier.
- [x] T023 [US3] Implement theme override step in `src/generator_wizard.py`: `_step_overrides(plan: SequencePlan, theme_library: ThemeLibrary) -> SequencePlan` — for each section, offer questionary prompt to keep or change theme. On change, re-run theme selection + effect placement for that section only. Return updated plan.
- [x] T024 [US3] Wire preview and override steps into the wizard flow in `src/generator_wizard.py`: after analysis, build initial plan → show preview → offer overrides → rebuild if changed → confirm → generate
- [x] T025 [US4] Add FSEQ rendering guidance to XSQ writer output in `src/generator/xsq_writer.py` and CLI output in `src/cli.py`: after writing .xsq, print instructions: "To render FSEQ: Open {output_path} in xLights → Tools → Batch Render (F9) → File → Export Sequence → FSEQ"

**Checkpoint**: Wizard shows plan preview, allows theme changes, and prints FSEQ guidance after generation.

---

## Phase 6: User Story 5 — Post-Generation Refinement (Priority: P3)

**Goal**: Re-run generation on specific sections without regenerating the entire sequence.

**Independent Test**: Generate full .xsq, then re-run with `--section chorus --theme-override "chorus=Inferno"` → only chorus sections change.

### Tests for User Story 5

- [x] T026 [US5] Write failing tests for section regeneration in `tests/unit/test_generator/test_xsq_writer.py` (extend): test parsing existing .xsq, test removing effects in a time range, test inserting new effects in that range, test effects outside range are semantically identical (same effects, times, parameters) before and after

### Implementation for User Story 5

- [x] T027 [US5] Implement XSQ parser in `src/generator/xsq_writer.py`: `parse_xsq(path: Path) -> XsqDocument` — read existing .xsq XML, extract EffectDB, ColorPalettes, DisplayElements, ElementEffects into XsqDocument
- [x] T028 [US5] Implement section regeneration in `src/generator/plan.py`: `regenerate_sections(config: GenerationConfig, existing_xsq: Path)` — parse existing .xsq, identify effects in target section time range, remove them, regenerate with new theme/overrides, merge back, write. Make T026 tests pass.
- [x] T029 [US5] Wire `--section` and `--theme-override` CLI options in `src/cli.py`: when --section is provided, call `regenerate_sections()` instead of `generate_sequence()`. Parse --theme-override as "label=ThemeName" pairs.

**Checkpoint**: Section-level regeneration works. Unmodified sections remain identical.

---

## Phase 7: Polish & Integration Testing

**Purpose**: End-to-end validation, edge cases, and cleanup

- [x] T030 Write end-to-end integration test in `tests/integration/test_sequence_generation.py`: full pipeline with fixture MP3 + sample layout → .xsq → validate XML structure, verify effects on models, assert ≥80% of effects align to beat/onset/section timing marks (SC-003), assert ≥80% of adjacent sections use different themes (SC-004), verify section theme variety
- [x] T031 Add edge case tests in `tests/integration/test_sequence_generation.py`: no power groups (flat model fallback), no detected sections (single section fallback), no timing tracks (BPM fallback), very short song (<30s), empty theme match (fallback broadening)
- [ ] T032 Validate generated .xsq opens in xLights without errors — document manual test results in `specs/020-sequence-generator/checklists/requirements.md`
- [ ] T033 Run quickstart.md validation — execute each command in quickstart.md and verify expected behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — this is the MVP
- **US2 (Phase 4)**: Depends on US1 (needs `generate_sequence()` to exist)
- **US3+US4 (Phase 5)**: Depends on US2 (extends wizard flow) and US1 (needs plan builder)
- **US5 (Phase 6)**: Depends on US1 (needs XSQ writer and plan builder)
- **Polish (Phase 7)**: Depends on US1 at minimum; ideally after all stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependencies on other stories. **This is the MVP.**
- **US2 (P1)**: After US1 — wraps the generation pipeline in an interactive wizard
- **US3 (P2)**: After US2 — adds preview step to the wizard flow
- **US4 (P2)**: After US1 — adds FSEQ guidance message (can be done alongside US3)
- **US5 (P3)**: After US1 — extends XSQ writer with parse/modify capability

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution IV)
- Models/data before logic
- Core logic before integration
- Integration before CLI wiring
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 can run in parallel with each other (Phase 1)
- T007, T008, T009, T010 can ALL run in parallel (US1 tests — different files)
- T011, T013 can run in parallel (theme_selector.py and value_curves.py — independent)
- T030, T031 can run in parallel (different test scenarios in same file, but independent)
- US3 and US4 tasks can largely run in parallel (different files)

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 failing tests together:
Task T007: "Write failing tests for theme selection in tests/unit/test_generator/test_theme_selector.py"
Task T008: "Write failing tests for effect placement in tests/unit/test_generator/test_effect_placer.py"
Task T009: "Write failing tests for value curves in tests/unit/test_generator/test_value_curves.py"
Task T010: "Write failing tests for XSQ writer in tests/unit/test_generator/test_xsq_writer.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (data models + energy derivation)
3. Complete Phase 3: User Story 1 (theme selection → effect placement → value curves → XSQ writer → plan builder → CLI command)
4. **STOP and VALIDATE**: Run `xlight-analyze generate song.mp3 layout.xml --no-wizard` and verify .xsq opens in xLights
5. This is a functional product — a user can generate sequences

### Incremental Delivery

1. Setup + Foundational → Core infrastructure ready
2. US1 → Non-interactive generation works → **MVP!**
3. US2 → Interactive wizard wraps the pipeline → Better UX
4. US3+US4 → Preview + FSEQ guidance → Informed user control
5. US5 → Section regeneration → Efficient refinement workflow
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story is independently testable after its checkpoint
- Constitution IV requires TDD: write failing tests, then implement
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- The plan builder (T017) is the integration point — it ties all US1 components together
- XSQ format details are in contracts/xsq-schema.md — reference during T014 implementation
