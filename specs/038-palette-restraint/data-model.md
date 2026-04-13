# Data Model: Palette Restraint

## Modified Entities

### EffectPlacement (src/generator/models.py)

Existing dataclass — add one field:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `music_sparkles` | `int` | `0` | MusicSparkles frequency (0=off, 1-100=enabled with frequency) |

### GenerationConfig (src/generator/models.py)

Existing dataclass — add one field:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `palette_restraint` | `bool` | `True` | Enable palette color count restraint and MusicSparkles |

## New Constants

### Tier Active Color Caps (src/generator/effect_placer.py)

```python
_TIER_PALETTE_CAP: dict[int, int] = {
    1: 3,   # BASE — simple background wash
    2: 3,   # GEO — zone background
    3: 4,   # TYPE — architecture groups
    4: 3,   # BEAT — beat accents (minimal palette)
    5: 4,   # TEX — texture/fidelity
    6: 4,   # PROP — individual props
    7: 6,   # COMP — compound groups (hero-adjacent)
    8: 6,   # HERO — matrices, mega trees (richest palette)
}
```

### Audio-Reactive Effects (src/generator/effect_placer.py)

```python
_AUDIO_REACTIVE_EFFECTS: set[str] = {"VU Meter", "Music"}
```

Effects where MusicSparkles is suppressed (redundant with built-in audio reactivity).

## Palette Serialization Format

### Current Format (xsq_writer.py)

```
C_BUTTON_Palette1=#FF0000,...,C_BUTTON_Palette8=#FFFFFF,
C_CHECKBOX_Palette1=1,...,C_CHECKBOX_Palette8=0
```

### New Format (with MusicSparkles)

```
C_BUTTON_Palette1=#FF0000,...,C_BUTTON_Palette8=#FFFFFF,
C_CHECKBOX_Palette1=1,...,C_CHECKBOX_Palette8=0,
C_SLIDER_MusicSparkles=50
```

MusicSparkles appended only when value > 0. Value 0 = omitted (xLights default).

## Algorithm: Active Color Count

```
input:  section.energy_score (0-100), tier (1-8), len(theme_palette)
output: number of active palette colors (1-6)

base_count = 2 + energy_score // 33     # 2 at low, 3 at mid, 4-5 at high
tier_cap   = _TIER_PALETTE_CAP[tier]    # 3 for base, 6 for hero
result     = min(base_count, tier_cap, len(theme_palette))
result     = max(1, result)             # never zero
```

## Algorithm: MusicSparkles

```
input:  section.energy_score (0-100), effect_name, rng (seeded Random)
output: sparkle_frequency (0-100, where 0 = off)

if effect_name in _AUDIO_REACTIVE_EFFECTS:
    return 0
probability = energy_score / 200.0      # 0.0 at energy=0, 0.5 at energy=100
if rng.random() < probability:
    return 20 + round(energy_score * 0.6)  # 20 at low, 80 at high
else:
    return 0
```
