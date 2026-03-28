# Data Model: Sequence Generator (020)

**Date**: 2026-03-26
**Branch**: `020-sequence-generator`

## Entities

### SongProfile

Captures the song's identity and characteristics for theme selection.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `title` | `str` | ID3 tags / user input | Song title |
| `artist` | `str` | ID3 tags / user input | Artist name |
| `genre` | `str` | ID3 tags / user override | Genre (rock, pop, classical, etc.) |
| `occasion` | `str` | User input | "christmas", "halloween", or "general" |
| `duration_ms` | `int` | HierarchyResult | Total song length in milliseconds |
| `estimated_bpm` | `float` | HierarchyResult | Detected tempo |

---

### SectionEnergy

A song section enriched with derived energy data.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `label` | `str` | HierarchyResult.sections | Section type: "intro", "verse", "chorus", "bridge", "outro", "break", "solo" |
| `start_ms` | `int` | HierarchyResult.sections | Section start time |
| `end_ms` | `int` | Computed (start_ms + duration_ms) | Section end time |
| `energy_score` | `int` | Derived from L5 + L0 | 0-100 energy level |
| `mood_tier` | `str` | Derived from energy_score | "ethereal" (0-33), "structural" (34-66), "aggressive" (67-100) |
| `impact_count` | `int` | L0 energy_impacts in range | Number of energy impacts in this section |

**Derivation**: `energy_score = min(100, mean(L5_full_mix_frames_in_range) + impact_count * 5)`

**State**: Immutable once computed. No transitions.

---

### SequencePlan

The complete blueprint for generating a sequence.

| Field | Type | Description |
|-------|------|-------------|
| `song_profile` | `SongProfile` | Song metadata and characteristics |
| `sections` | `list[SectionAssignment]` | Ordered list of section-to-theme mappings |
| `layout_groups` | `list[PowerGroup]` | Power groups from layout (or flat model list) |
| `models` | `list[str]` | All model names from layout |
| `frame_interval_ms` | `int` | Always 25 (40fps) |

**Identity**: One plan per generation run. Identified by song hash + layout hash + generation timestamp.

---

### SectionAssignment

One section's theme and effect mapping.

| Field | Type | Description |
|-------|------|-------------|
| `section` | `SectionEnergy` | The section with energy data |
| `theme` | `Theme` | Selected theme from theme library |
| `group_effects` | `dict[str, list[EffectPlacement]]` | Power group name → list of effect placements |
| `variation_seed` | `int` | Seed for parameter variation on repeated sections |

**Relationships**: References a `Theme` (from feature 019) and contains `EffectPlacement` instances.

---

### EffectPlacement

A single effect instance on the timeline.

| Field | Type | Description |
|-------|------|-------------|
| `effect_name` | `str` | Effect name (matches effect library) |
| `xlights_id` | `str` | xLights internal effect ID |
| `model_or_group` | `str` | Target model or group name |
| `start_ms` | `int` | Effect start time |
| `end_ms` | `int` | Effect end time |
| `parameters` | `dict[str, Any]` | Resolved parameter values (storage_name → value) |
| `color_palette` | `list[str]` | Hex color values for this effect |
| `blend_mode` | `str` | Layer blend mode |
| `fade_in_ms` | `int` | Fade in duration (0 for beat/trigger effects) |
| `fade_out_ms` | `int` | Fade out duration (0 for beat/trigger effects) |
| `value_curves` | `dict[str, list[tuple[float, float]]]` | Parameter name → list of (x, y) control points |

**Validation Rules**:
- `start_ms < end_ms`
- `start_ms` and `end_ms` must be multiples of 25 (frame-aligned)
- All parameter values within effect library's defined min/max ranges
- Color palette has at least 2 entries

---

### XsqDocument

Intermediate representation of the .xsq XML before serialization.

| Field | Type | Description |
|-------|------|-------------|
| `media_file` | `str` | Path to MP3 file |
| `duration_sec` | `float` | Sequence duration in seconds |
| `frame_interval_ms` | `int` | 25 (40fps) |
| `color_palettes` | `list[list[str]]` | Deduplicated palette list |
| `effect_db` | `list[str]` | Deduplicated effect parameter strings |
| `display_elements` | `list[str]` | Model/group names |
| `element_effects` | `dict[str, list[EffectPlacement]]` | Model name → timeline effects |

**Deduplication**: Multiple effect placements with identical parameters share a single EffectDB entry (referenced by index). Same for color palettes.

---

### GenerationConfig

User choices from the wizard.

| Field | Type | Description |
|-------|------|-------------|
| `audio_path` | `Path` | Input MP3 file |
| `layout_path` | `Path` | xLights layout XML file |
| `output_dir` | `Path` | Output directory for .xsq |
| `genre` | `str` | Song genre (detected or overridden) |
| `occasion` | `str` | "christmas", "halloween", or "general" |
| `force_reanalyze` | `bool` | Skip cache and re-run analysis |
| `target_sections` | `list[str] \| None` | Section labels to regenerate (None = all) |
| `theme_overrides` | `dict[int, str] \| None` | Section index → theme name overrides |

---

## Relationships

```
GenerationConfig
  └─ drives ─→ SequencePlan
                  ├─ SongProfile (1:1)
                  ├─ SectionAssignment (1:N, ordered)
                  │    ├─ SectionEnergy (1:1)
                  │    ├─ Theme (1:1, from theme library)
                  │    └─ EffectPlacement (1:N, per group)
                  │         └─ value_curves (0:N, per parameter)
                  └─ PowerGroup (0:N, from layout)
                       └─ model names (1:N)

SequencePlan ──serializes──→ XsqDocument ──writes──→ .xsq file
```

## Upstream Data Dependencies

| Upstream | Data Consumed | Access Pattern |
|----------|--------------|----------------|
| HierarchyResult (016) | sections, beats, bars, energy_curves, energy_impacts, chords, estimated_bpm | `run_orchestrator()` or cached JSON |
| PowerGroup (017) | tier, name, members | `generate_groups()` from layout props |
| EffectLibrary (018) | effects dict, analysis_mappings, duration_type, parameters | `load_effect_library()` |
| ThemeLibrary (019) | themes dict, query by mood/occasion/genre | `load_theme_library()` |
| Layout XML (017) | model names, pixel counts, positions | `parse_layout()` |
