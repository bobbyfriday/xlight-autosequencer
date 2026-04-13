# Implementation Plan: Palette Restraint

**Branch**: `038-palette-restraint` | **Date**: 2026-04-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/038-palette-restraint/spec.md`

## Summary

Reduce active palette colors from all 8 slots to 2-4, matching the 2.8 average
observed in reference sequences. Scale active count by section energy (2-3 for
verses, 4-6 for choruses). Add MusicSparkles and SparkleFrequency support as
energy-driven palette enhancements.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Flask 3+ (web server), click 8+ (CLI), existing generator pipeline
**Storage**: JSON files (theme definitions, variant library), XML files (.xsq output)
**Testing**: pytest
**Target Platform**: Linux/macOS (devcontainer)
**Project Type**: CLI + web service (sequence generator)
**Performance Goals**: No additional processing time — palette restraint is a filter on existing data
**Constraints**: Output must be valid xLights XSQ with no ApplySetting errors
**Scale/Scope**: ~21 built-in themes, each with 3-8 palette colors

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Audio-First Pipeline | PASS | Palette restraint uses existing section energy from audio analysis. No new audio processing. |
| II. xLights Compatibility | PASS | Output format uses standard C_BUTTON_Palette / C_CHECKBOX_Palette / C_SLIDER_MusicSparkles. All validated against reference XSQ files. |
| III. Modular Pipeline | PASS | Changes are confined to palette serialization (xsq_writer.py) and color selection (effect_placer.py). No cross-stage mutations. |
| IV. Test-First Development | PASS | Unit tests for palette restraint, MusicSparkles, energy scaling. Integration tests for metric validation. |
| V. Simplicity First | PASS | No new abstractions — modifies existing `_serialize_palette` and palette construction in `place_effects`. Feature toggle for reversion. |

## Project Structure

### Documentation (this feature)

```text
specs/038-palette-restraint/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # N/A — no new external interfaces
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (changes)

```text
src/generator/
├── xsq_writer.py        # _serialize_palette: active slot restraint, MusicSparkles
├── effect_placer.py      # Palette color selection: energy-based active count
├── models.py             # PaletteConfig on EffectPlacement (sparkle flag, active count)
└── plan.py               # Wire palette_restraint toggle from GenerationConfig
```

## Phase 0: Research

### Key Findings

**1. Current palette serialization (xsq_writer.py:376-393)**
- `_serialize_palette` always fills 8 slots with C_BUTTON_Palette entries
- Checkbox logic: slots 1 through `len(colors)` get `=1`, rest get `=0`
- The number of active checkboxes equals `len(color_palette)` on EffectPlacement
- **To restrain: pass fewer colors in `color_palette`, not change serialization logic**

**2. MusicSparkles format (from reference XSQ files)**
- Palette attribute: `C_SLIDER_MusicSparkles=50` (0-100 range)
- Not a checkbox — it's a slider where 0 = off, >0 = enabled with frequency
- Appears in the palette string alongside C_BUTTON and C_CHECKBOX entries
- Reference usage: 8-30% of palettes, values typically 20-80
- SparkleFrequency is the same slider — `C_SLIDER_MusicSparkles` IS the frequency

**3. Active color count in reference files**
- 12 - Magic: avg 3.6 active colors (3-5 range)
- Light of Christmas: avg 2.8 active colors (2-4 range)
- Away In A Manger: avg 2.5 active colors (2-3 range)
- Baby Shark: avg 3.1 active colors (3-4 range)
- Shut Up and Dance: avg 5.5 active colors (outlier — VU Meter heavy)
- **Target: 2.0-4.0 average, matching 4 of 5 references**

**4. Where to control active count**
- `effect_placer.py` constructs the palette as a `list[str]` and passes to `_make_placement`
- The list length determines how many checkboxes are active in serialization
- **Restraint approach: trim the palette list before passing to `_make_placement`**
- Energy-based scaling: trim to 2-3 for low energy, keep 4-5 for high energy

**5. Tier-based variety**
- Tiers 1-2 already use `_dim_palette(theme.palette, 0.40)` — dimmed background
- Tiers 3+ use accent palette — `_lighten_palette(theme.palette, 0.5)`
- Hero tiers (7-8) can get more active colors than base tiers (1-2)
- Implementation: apply different trim targets per tier

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where to restrain | Trim `color_palette` list in `place_effects` | Simplest — `_serialize_palette` already uses list length for checkboxes |
| MusicSparkles format | `C_SLIDER_MusicSparkles=N` in palette string | Matches reference XSQ format; single slider controls both enable + frequency |
| Energy scaling formula | `active_count = 2 + floor(energy / 33)` | Gives 2 at low, 3 at medium, 4-5 at high; capped per tier |
| Tier caps | Base: max 3, Mid: max 4, Hero: max 6 | Matches reference pattern of richer hero palettes |
| Feature toggle | `palette_restraint: bool = True` on GenerationConfig | Consistent with `focused_vocabulary` and `embrace_repetition` toggles |
| MusicSparkles probability | `energy / 200` (0-50% based on energy) | ~10-30% overall for mixed-energy sequences |

## Phase 1: Data Model & Contracts

### Data Model Changes

**EffectPlacement** (src/generator/models.py) — add field:
```python
music_sparkles: int = 0  # 0=off, 1-100=sparkle frequency
```

**GenerationConfig** (src/generator/models.py) — add field:
```python
palette_restraint: bool = True
```

### Palette Restraint Algorithm

```
For each EffectPlacement:
  1. Start with the full theme palette (list of hex colors)
  2. Determine target active count:
     - base_count = 2 + floor(section.energy_score / 33)  → 2, 3, or 4
     - tier_cap = {1: 3, 2: 3, 3: 4, 4: 3, 5: 4, 6: 4, 7: 6, 8: 6}
     - target = min(base_count, tier_cap[tier], len(palette))
  3. Trim palette to target colors (take first N from theme order)
  4. Determine MusicSparkles:
     - Skip if effect is audio-reactive (VU Meter)
     - Probability = section.energy_score / 200 (clamped 0.0-0.5)
     - If enabled: frequency = 20 + (section.energy_score * 0.6)  → 20-80 range
  5. Pass trimmed palette + sparkle value to _make_placement
```

### Serialization Changes

**_serialize_palette** (xsq_writer.py) — add MusicSparkles:
```
Current:  C_BUTTON_Palette1=..., ..., C_CHECKBOX_Palette1=..., ...
Proposed: C_BUTTON_Palette1=..., ..., C_CHECKBOX_Palette1=..., ..., C_SLIDER_MusicSparkles=50
```

The `music_sparkles` field from EffectPlacement needs to be passed through to
`_serialize_palette` or appended in `_serialize_effect_params`. Since MusicSparkles
is a palette attribute (not an effect parameter), it belongs in the palette string.

### No New External Interfaces

No contracts needed — this feature modifies internal palette construction and
serialization. No new CLI flags, API endpoints, or file formats.

## Complexity Tracking

| Component | Complexity | Justification |
|-----------|-----------|---------------|
| Palette trimming in effect_placer | Low | Slice existing list by computed count |
| Energy-based active count | Low | Simple arithmetic: 2 + energy // 33 |
| Tier-based caps | Low | Dict lookup per tier |
| MusicSparkles serialization | Low | Append one key-value to palette string |
| MusicSparkles probability | Low | RNG check against energy-derived threshold |
| Feature toggle | Low | Single boolean gate, consistent with existing toggles |

Total estimated complexity: **Low**. No new abstractions, no new data flows.
All changes are local to palette construction and serialization.
