# Quickstart: Palette Restraint

## What Changed

Generated xLights sequences now use 2-4 active palette colors instead of activating
all 8 slots. High-energy sections (choruses, drops) expand to 4-6 colors. Hero props
get richer palettes than background props. Pattern effects may get MusicSparkles
overlay in high-energy sections.

## Quick Verification

Generate a sequence and run the analyzer:

```bash
python3 scripts/analyze_reference_xsq.py output.xsq
```

Check the palette section:
- **Average active colors**: should be 2.0-4.0 (was 5-8 before)
- **MusicSparkles enabled**: should be 10-30% of palettes
- **Hero vs base palette variety**: hero models should show 30%+ more unique palettes

## Toggle Off

To revert to previous behavior (all slots active, no MusicSparkles):

```python
config = GenerationConfig(
    ...,
    palette_restraint=False,
)
```

## How It Works

1. **Before**: `color_palette = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"]`
   → 5 active checkboxes in XSQ

2. **After**: palette trimmed to 2-3 colors for a verse section on a base-tier model:
   `color_palette = ["#FF0000", "#00FF00"]` → 2 active checkboxes

3. **High-energy chorus on hero tier**: palette kept at 5-6 colors with MusicSparkles:
   `color_palette = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"]`
   + `C_SLIDER_MusicSparkles=68`
