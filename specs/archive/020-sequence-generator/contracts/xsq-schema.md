# XSQ Output Schema Contract

**Date**: 2026-03-26
**Target**: xLights 2024+ `.xsq` format

## XML Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xsequence BaseChannel="0" ChanCtrlBasic="0" ChanCtrlColor="0"
           FixedPointTiming="25" ModelBlending="true">
  <head>
    <version>2024.01</version>
    <author>xlight-autosequencer</author>
    <song>{song_title}</song>
    <artist>{artist}</artist>
    <mediaFile>{relative_path_to_mp3}</mediaFile>
    <sequenceTiming>25 ms</sequenceTiming>
    <sequenceDuration>{duration_seconds}</sequenceDuration>
  </head>

  <ColorPalettes>
    <!-- One entry per unique palette, referenced by index -->
    <ColorPalette>C_BUTTON_Palette1=#FF0000,C_CHECKBOX_Palette1=1,C_BUTTON_Palette2=#00FF00,C_CHECKBOX_Palette2=1</ColorPalette>
  </ColorPalettes>

  <EffectDB>
    <!-- One entry per unique effect parameter combination, referenced by index -->
    <Effect>E_SLIDER_Fire_Height=50,E_CHECKBOX_Fire_GrowWithMusic=0,E_TEXTCTRL_Fadein=200,E_TEXTCTRL_Fadeout=200</Effect>
  </EffectDB>

  <DisplayElements>
    <!-- All models and groups that have effects -->
    <Element type="model" name="{model_name}" visible="1" collapsed="0" active="1"/>
  </DisplayElements>

  <ElementEffects>
    <!-- Effect timeline per model/group -->
    <Element type="model" name="{model_name}">
      <EffectLayer>
        <Effect ref="{effectdb_index}" name="{effect_name}"
                startTime="{start_ms}" endTime="{end_ms}"
                palette="{palette_index}" selected="0"/>
      </EffectLayer>
    </Element>
  </ElementEffects>
</xsequence>
```

## Constraints

- `FixedPointTiming` MUST be `"25"` (25ms / 40fps)
- All `startTime` and `endTime` values MUST be multiples of 25
- Model names in `DisplayElements` and `ElementEffects` MUST match names from the layout XML exactly
- `ref` indices are 0-based into the `EffectDB` list
- `palette` indices are 0-based into the `ColorPalettes` list
- `mediaFile` should be a relative path from the .xsq file to the MP3

## Value Curve Encoding

When a parameter is modulated by a value curve, its entry in the EffectDB uses this format:

```
E_SLIDER_Fire_Height=Active=TRUE|Id=ID_SLIDER_Fire_Height|Type=Ramp|Min=0.00|Max=100.00|Values=0.00:50.00|0.25:75.00|0.50:100.00|0.75:50.00|1.00:25.00
```

- `x` values: normalized position within the effect instance (0.0 = start, 1.0 = end)
- `y` values: parameter value in the parameter's native range
- Points are `|`-delimited, each point is `x:y`
- Maximum ~100 control points per curve (downsampled if needed)

## Fade Parameters

- `E_TEXTCTRL_Fadein={ms}` — Fade in duration in milliseconds
- `E_TEXTCTRL_Fadeout={ms}` — Fade out duration in milliseconds
- Section/bar effects: 200-500ms (proportional to duration)
- Beat/trigger effects: 0 (omitted from EffectDB entry)
