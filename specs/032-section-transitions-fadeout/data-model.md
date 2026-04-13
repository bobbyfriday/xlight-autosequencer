# Data Model: Section Transitions & End-of-Song Fade Out

## Entities

### TransitionConfig

Settings controlling crossfade and fade-out behavior for a generation run.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| mode | str | "subtle" | Transition mode: "none", "subtle", or "dramatic" |
| snap_window_ms | int \| None | None | Override for boundary snap window. None = use adaptive default (half median bar interval, 400-1200ms) |
| fadeout_strategy | str | "progressive" | End-of-song strategy: "progressive" (staggered tier fade), "uniform" (all tiers together), or "none" |
| abrupt_end_fade_ms | int | 3000 | Fade duration for songs that end without an outro |

### CrossfadeRegion

A computed region spanning a section boundary where fades are applied.

| Field | Type | Description |
|-------|------|-------------|
| boundary_ms | int | The section boundary timestamp |
| section_a_index | int | Index of the outgoing section |
| section_b_index | int | Index of the incoming section |
| fade_duration_ms | int | Computed fade duration (from tempo + mode) |
| skip_groups | set[str] | Group names where same-effect continuation was detected — no crossfade applied |

### FadeOutPlan

The brightness ramp for the final section, per tier.

| Field | Type | Description |
|-------|------|-------------|
| start_ms | int | Start of the fade-out (beginning of outro, or N seconds before end) |
| end_ms | int | End of the fade-out (end of song) |
| is_outro | bool | True if the final section is labeled "outro" |
| tier_offsets | dict[int, float] | Tier number → fade start offset as fraction (0.0-1.0) of the fade region. Hero=0.0, compound=0.2, prop=0.4, fidelity=0.6, base=0.8 for progressive; all 0.0 for uniform |

### Theme (extended)

Existing dataclass in `src/themes/models.py`, extended with one optional field.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| transition_mode | str \| None | None | **NEW**: Per-theme transition mode override ("none", "subtle", "dramatic"). None = use generation default. |

## Relationships

```
TransitionConfig (from CLI or defaults)
  │
  ├── mode → determines CrossfadeRegion.fade_duration_ms
  ├── fadeout_strategy → determines FadeOutPlan.tier_offsets
  │
  └── apply_transitions(assignments, config, hierarchy)
        │
        ├── compute CrossfadeRegion for each section boundary
        │     └── set fade_out_ms on outgoing placements
        │     └── set fade_in_ms on incoming placements
        │
        └── compute FadeOutPlan for final section
              └── set fade_out_ms on all placements in final section
                    (staggered by tier per tier_offsets)

Theme.transition_mode → overrides TransitionConfig.mode for sections using that theme
```

## Crossfade Duration Calculation

```
BPM = hierarchy.estimated_bpm
beat_ms = 60000 / BPM
bar_ms = beat_ms × 4  (assuming 4/4 time)

Mode     Duration
─────    ────────────────────
none     0
subtle   beat_ms (capped at half section length)
dramatic bar_ms  (capped at half section length)
```

## Progressive Fade-Out Tier Offsets

For a long outro (>8 seconds), each tier starts fading at a different point:

```
Tier   Name        Fade starts at    Fades over
────   ──────────  ────────────────  ──────────
8      Hero        0% of outro       100% of outro
7      Compound    20% of outro      80% of outro
6      Prop        40% of outro      60% of outro
5      Fidelity    60% of outro      40% of outro
1-2    Base/Geo    80% of outro      20% of outro
```

For short outros (<8s) or uniform strategy, all tiers fade from 0% to 100% together.

## Validation Rules

- TransitionConfig.mode must be one of: "none", "subtle", "dramatic"
- TransitionConfig.fadeout_strategy must be one of: "progressive", "uniform", "none"
- CrossfadeRegion.fade_duration_ms must be > 0 (except mode "none") and ≤ half the shorter adjacent section
- FadeOutPlan.end_ms must equal the song's duration_ms
- Theme.transition_mode must be None or one of the three valid modes
