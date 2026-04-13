# Quickstart: Section Transitions & End-of-Song Fade Out

## Prerequisites

- Existing sequence generation pipeline (feature 020)
- Song with completed analysis (hierarchy JSON with bars, beats, sections, energy curves)

## Basic Usage

### 1. Generate a sequence with transitions (default: subtle)

```bash
xlight-analyze generate song.mp3 --layout xlights_rgbeffects.xml
```

Transitions are enabled by default in "subtle" mode — 1-beat crossfades at section boundaries and a progressive fade-out at end-of-song.

### 2. Choose a transition mode

```bash
# No transitions (legacy behavior, byte-identical output)
xlight-analyze generate song.mp3 --layout xlights_rgbeffects.xml --transition-mode none

# Subtle: 1-beat crossfades
xlight-analyze generate song.mp3 --layout xlights_rgbeffects.xml --transition-mode subtle

# Dramatic: 1-bar crossfades
xlight-analyze generate song.mp3 --layout xlights_rgbeffects.xml --transition-mode dramatic
```

### 3. Per-theme transition mode

Add `transition_mode` to a theme JSON to override the global setting:

```json
{
  "name": "Ethereal Frost",
  "mood": "ethereal",
  "transition_mode": "dramatic",
  "layers": [...]
}
```

When this theme is active, its sections use "dramatic" crossfades regardless of the global setting.

## What Happens

### Section Transitions

At every section boundary:
1. The outgoing section's last effect placements get a `fade_out_ms` value
2. The incoming section's first effect placements get a `fade_in_ms` value
3. If the same effect continues across the boundary on a group, no crossfade is applied for that group

### End-of-Song Fade Out

For songs with an "outro" section:
- All tiers fade progressively — heroes first, base wash last
- Brightness follows the energy curve for natural dimming

For songs that end abruptly:
- A 3-second fade is applied to the final section's placements

### Boundary Snap Precision

Section boundaries are snapped to the nearest bar line (existing behavior, enhanced):
- Boundaries that would merge are handled (shorter section absorbed)
- Boundaries that would cross are prevented (snap window reduced)

## Verifying Results

After generating, import the `.xsq` into xLights:

1. **Crossfades**: Open the timeline and zoom into a section boundary. Effects should show fade ramps at the boundary.
2. **End-of-song**: Scroll to the end. Effects should dim progressively with upper tiers going dark before the base wash.
3. **Backward compat**: Generate with `--transition-mode none` and compare to a pre-feature generation — output should be identical.

## Known Limitations

- xLights may recalculate fade values on save. If fade values don't survive a save-and-reopen cycle, the feature will need to switch to value curves or overlay effects (documented in assumptions).
- The "progressive" tier fade-out requires at least 8 seconds of outro. Shorter outros use uniform fading.
