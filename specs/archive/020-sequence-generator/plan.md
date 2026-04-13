# Implementation Plan: Sequence Generator

**Branch**: `020-sequence-generator` | **Date**: 2026-03-26 | **Spec**: [spec.md](spec.md)
**Constitution**: v1.0.0

## Summary

Build the sequence generator — the culmination feature that takes an MP3 file and xLights layout, runs the full analysis pipeline, selects themes based on section energy/genre/occasion, maps effects to power groups aligned with timing tracks, and writes a valid `.xsq` file. Includes a CLI wizard for interactive control and section-level regeneration for iterative refinement.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click 8+ (CLI), questionary 2+ (wizard prompts), rich 13+ (progress/tables), mutagen (ID3 tags), xml.etree.ElementTree (stdlib, XSQ generation)
**Storage**: `.xsq` XML files (output), JSON analysis cache (existing)
**Testing**: pytest
**Target Platform**: macOS / Linux (local CLI tool)
**Project Type**: CLI tool
**Performance Goals**: Sequence generation (excluding analysis) completes in under 30 seconds for a 3-minute song. Full wizard flow under 5 minutes.
**Constraints**: Offline operation only. No new dependencies beyond what's already installed.
**Scale/Scope**: Single song at a time. Layout files typically have 10-200 models.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | **PASS** | All timing derives from analysis. Effect placement uses beat/bar/onset marks from analyzed audio. Fallback BPM spacing only when no analysis available. |
| II. xLights Compatibility | **PASS** | Output is `.xsq` XML targeting xLights 2024+. Model names preserved from layout. Effect names match xLights IDs. Validated by schema contract. |
| III. Modular Pipeline | **PASS** | Generator is a new pipeline stage consuming existing stage outputs (HierarchyResult, PowerGroups, EffectLibrary, ThemeLibrary) via defined data contracts. No shared mutable state. |
| IV. Test-First Development | **PASS** | Unit tests per module (energy derivation, theme selection, effect placement, XSQ serialization). Integration test: MP3 → .xsq with fixture validation. |
| V. Simplicity First | **PASS** | No speculative abstractions. Direct function calls to existing libraries. Simple energy→mood mapping. Template-free XML generation with ElementTree. |

**Post-Phase 1 Re-check**: All principles still pass. Data model adds no unnecessary abstractions. XSQ schema contract directly serves xLights compatibility principle.

## Project Structure

### Documentation (this feature)

```text
specs/020-sequence-generator/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: technical decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: usage guide
├── contracts/
│   ├── cli-commands.md  # CLI command interface
│   └── xsq-schema.md   # XSQ output format contract
└── tasks.md             # Phase 2 (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── generator/                    # NEW — sequence generation module
│   ├── __init__.py
│   ├── energy.py                 # Section energy derivation (L5 + L0)
│   ├── theme_selector.py         # Theme selection engine (energy→mood→theme)
│   ├── effect_placer.py          # Effect placement on timeline (duration, timing, fades)
│   ├── value_curves.py           # Analysis mapping → value curve generation
│   ├── xsq_writer.py            # XSQ XML serialization with deduplication
│   ├── plan.py                   # SequencePlan builder (ties it all together)
│   └── models.py                 # Dataclasses: SongProfile, SectionEnergy, SequencePlan, etc.
├── generator_wizard.py           # NEW — interactive wizard for sequence generation
├── cli.py                        # MODIFIED — add generate/generate-wizard commands
└── [existing modules unchanged]

tests/
├── unit/
│   └── test_generator/           # NEW
│       ├── test_energy.py        # Energy derivation tests
│       ├── test_theme_selector.py
│       ├── test_effect_placer.py
│       ├── test_value_curves.py
│       ├── test_xsq_writer.py
│       ├── test_plan.py
│       └── test_wizard.py
├── integration/
│   └── test_sequence_generation.py  # NEW — end-to-end MP3→.xsq
└── fixtures/
    ├── sample_layout.xml         # NEW — minimal xLights layout for testing
    └── expected_sequence.xsq     # NEW — golden file for XSQ validation
```

**Structure Decision**: New `src/generator/` module following the existing pattern of `src/analyzer/`, `src/grouper/`, `src/effects/`, `src/themes/`. Wizard in a separate file at `src/` root following the existing `src/wizard.py` pattern. CLI commands added to existing `src/cli.py`.

## Implementation Phases

### Phase 1: Core Data Models & Energy Derivation

**Goal**: Establish data model and derive per-section energy scores from analysis data.

**Modules**: `src/generator/models.py`, `src/generator/energy.py`

**Key Decisions**:
- `SectionEnergy` derives energy from L5 energy curves + L0 impact boost
- Energy score 0-100 maps to mood tiers: 0-33=ethereal, 34-66=structural, 67-100=aggressive
- Impact boost: +5 per L0 energy_impact in section range, capped at 100

**Tests**: `test_energy.py` — known energy curves → expected scores and mood tiers

---

### Phase 2: Theme Selection Engine

**Goal**: Select themes for each section based on energy/genre/occasion, with variety constraints.

**Modules**: `src/generator/theme_selector.py`

**Key Decisions**:
- Query theme library: `query(mood=mood_tier, occasion=occasion, genre=genre)`
- Adjacent sections get different themes (rotate through candidates)
- Repeated section types (Chorus 1, 2, 3) get same theme with `variation_seed` for parameter tweaks
- Fallback: if no themes match filters, broaden to genre="any", then occasion="general"

**Tests**: `test_theme_selector.py` — mock theme library, verify variety and mood mapping

---

### Phase 3: Effect Placement Engine

**Goal**: Map theme effect layers to power groups, place effects on timeline using timing tracks.

**Modules**: `src/generator/effect_placer.py`

**Key Decisions**:
- Layer-to-tier mapping: bottom layers → base/geo groups (tiers 1-2), mid → type/beat (3-4), top → hero/compound (7-8)
- `duration_type` drives instance repetition: section=1 instance, bar=per bar, beat=per beat, trigger=per event
- Energy-driven density: high energy → use ~90% of marks, low → ~50%
- Auto fades: section/bar effects get `min(500, duration_ms * 0.1)` fade; beat/trigger get 0
- Clean cut at section boundaries

**Tests**: `test_effect_placer.py` — verify placement times align with timing marks, fade calculations, density filtering

---

### Phase 4: Value Curve Generation

**Goal**: Generate parameter modulation curves from analysis mappings.

**Modules**: `src/generator/value_curves.py`

**Key Decisions**:
- For each effect with `AnalysisMapping` where target parameter has `supports_value_curve=true`:
  - Extract analysis data for the effect's time range
  - Apply curve_shape transform (linear, log, exp, step)
  - Map input_min/max → output_min/max
  - Downsample to ≤100 control points
  - Output as list of (x, y) tuples normalized to effect instance span

**Tests**: `test_value_curves.py` — known analysis data → expected curve points with each curve shape

---

### Phase 5: XSQ Writer

**Goal**: Serialize a SequencePlan to valid xLights `.xsq` XML.

**Modules**: `src/generator/xsq_writer.py`

**Key Decisions**:
- Deduplicate effect parameter strings → EffectDB (referenced by index)
- Deduplicate color palettes → ColorPalettes (referenced by index)
- Frame-align all times to 25ms multiples
- Model names must exactly match layout XML names
- Value curves encoded inline in EffectDB entries
- Use `xml.etree.ElementTree` for generation

**Tests**: `test_xsq_writer.py` — generate XSQ from test plan, validate XML structure, verify deduplication, check times are frame-aligned

---

### Phase 6: Plan Builder

**Goal**: Tie all components together — build a SequencePlan from inputs.

**Modules**: `src/generator/plan.py`

**Pipeline**:
1. Load/run analysis → HierarchyResult
2. Parse layout → models + power groups
3. Read song metadata → SongProfile
4. Derive section energies → SectionEnergy[]
5. Select themes → SectionAssignment[]
6. Place effects → EffectPlacement[]
7. Generate value curves
8. Assemble SequencePlan
9. Write XSQ

**Tests**: `test_plan.py` — integration-level test with mock data through full pipeline

---

### Phase 7: CLI Wizard & Commands

**Goal**: Interactive wizard and CLI commands for sequence generation.

**Modules**: `src/generator_wizard.py`, `src/cli.py` (modified)

**Wizard Steps**:
1. Audio file validation
2. Layout file selection and summary
3. Song metadata detection (mutagen) and confirmation
4. Occasion selection
5. Analysis run (with progress via rich)
6. Generation plan preview (rich table: section → theme → colors)
7. Theme override prompts
8. Generation confirmation
9. XSQ write + FSEQ guidance message

**CLI Commands**: `generate` (non-interactive with flags) and `generate-wizard` (interactive)

**Tests**: Wizard step tests with mock TTY. CLI integration tests.

---

### Phase 8: Section-Level Regeneration

**Goal**: Re-run generation on specific sections without touching others.

**Modules**: `src/generator/xsq_writer.py` (extended), `src/generator/plan.py` (extended)

**Key Decisions**:
- Parse existing .xsq XML
- Remove effects in target section time range
- Regenerate with new theme for those sections only
- Write back — unmodified sections remain identical

**Tests**: `test_plan.py` — generate, regenerate chorus, verify other sections unchanged

---

### Phase 9: Integration Testing & Polish

**Goal**: End-to-end tests with real audio fixtures, XSQ validation, edge case coverage.

**Tests**:
- Full pipeline: fixture MP3 + sample layout → .xsq → validate XML → check timing alignment
- Edge cases: no power groups, no sections, short song, long song
- Golden file comparison for known inputs
