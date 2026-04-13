# Research: Sequence Generator (020)

**Date**: 2026-03-26
**Branch**: `020-sequence-generator`

## R1: xLights .xsq XML Format

**Decision**: Generate `.xsq` files using `xml.etree.ElementTree` (stdlib), following the xLights 2024+ XML schema.

**Rationale**: The `.xsq` format is well-understood from examining existing xLights files and the codebase already uses `ElementTree` for `.xtiming` and layout XML. No third-party XML library needed.

**Key Structure**:
```xml
<xsequence BaseChannel="0" ChanCtrlBasic="0" ChanCtrlColor="0"
           FixedPointTiming="25" ModelBlending="true">
  <head>
    <version>2024.01</version>
    <mediaFile>song.mp3</mediaFile>
    <sequenceTiming>25 ms</sequenceTiming>
    <sequenceDuration>180.0</sequenceDuration>
  </head>
  <ColorPalettes>
    <ColorPalette>C_BUTTON_Palette1=#FF0000,...</ColorPalette>
  </ColorPalettes>
  <EffectDB>
    <Effect>E_CHECKBOX_Fire_GrowWithMusic=0,E_SLIDER_Fire_Height=50,...</Effect>
  </EffectDB>
  <DisplayElements>
    <Element type="model" name="ModelName" visible="1" active="1"/>
  </DisplayElements>
  <ElementEffects>
    <Element type="model" name="ModelName">
      <EffectLayer>
        <Effect ref="0" name="Fire" startTime="1000" endTime="5000" palette="0"/>
      </EffectLayer>
    </Element>
  </ElementEffects>
</xsequence>
```

**Key Details**:
- `FixedPointTiming="25"` = 25ms frame interval (40fps)
- Effects reference an EffectDB by index (`ref`), not inline
- Color palettes are also referenced by index
- Value curves are encoded inline in the EffectDB entry as `Active=TRUE|Id=...|Type=Ramp|...|Values=x:y|x:y|...`
- Times are in milliseconds (integer strings)
- Models in `DisplayElements` must match model names from the layout XML

**Alternatives Considered**:
- lxml: More features but unnecessary dependency for simple XML generation
- Template-based string generation: Fragile, hard to maintain

---

## R2: Energy Derivation Per Section

**Decision**: Compute a 0-100 energy score per section by averaging the full-mix L5 energy curve within the section's time range, then boosting by L0 energy impacts.

**Rationale**: Sections in `HierarchyResult` have labels and time ranges but no energy classification. The L5 energy curve provides per-frame (typically 20fps) values 0-100 that can be sliced to any time range. L0 impacts add the "feel" of dynamic moments.

**Algorithm**:
1. Extract frames from `energy_curves["full_mix"]` that fall within `[section.start_ms, section.end_ms]`
2. Compute mean of those frame values → `base_energy` (0-100)
3. Count L0 `energy_impacts` within the section time range → `impact_count`
4. Boost: `final_energy = min(100, base_energy + impact_count * 5)` (each impact adds 5 points, capped at 100)
5. Map to mood tier: 0-33 → Ethereal, 34-66 → Structural/Dark, 67-100 → Aggressive

**Alternatives Considered**:
- Peak energy: Overweights brief moments, not representative of section feel
- Simple average without impacts: Undervalues dynamic sections with builds

---

## R3: ID3 Tag Reading for Song Metadata

**Decision**: Use `mutagen` (already a project dependency from feature 013) for ID3 tag reading.

**Rationale**: `mutagen` is already installed and provides fast, reliable ID3v2 tag parsing. It handles MP3, M4A, and other formats. Reading title/artist/genre from tags is a single function call. The 2-second timeout in FR-003 is easily met since tag reading is nearly instantaneous (no audio decoding).

**Alternatives Considered**:
- tinytag: Lightweight but new dependency
- eyed3: Heavier, unnecessary for our needs
- ffprobe: Requires subprocess, slower

---

## R4: Effect Parameter Serialization for .xsq

**Decision**: Serialize effect parameters as comma-separated `key=value` pairs in the EffectDB, matching xLights' native format.

**Rationale**: xLights stores each effect definition as a single string of comma-separated parameters: `E_SLIDER_Fire_Height=50,E_CHECKBOX_Fire_GrowWithMusic=0,...`. The effect library's `EffectParameter.storage_name` field already provides the exact xLights XML field names. Parameters not explicitly set should be omitted (xLights uses its own defaults).

**Value Curve Encoding**: When a parameter is driven by a value curve, the format is:
```
E_SLIDER_Fire_Height=Active=TRUE|Id=ID_SLIDER_Fire_Height|Type=Ramp|Min=0.00|Max=100.00|Values=0.00:50.00|0.25:75.00|0.50:100.00|0.75:50.00|1.00:25.00
```
Where x values are normalized position (0.0-1.0) within the effect's time span, and y values are the parameter value.

---

## R5: Color Palette Serialization

**Decision**: Convert theme hex color palettes to xLights `C_BUTTON_Palette` format.

**Rationale**: xLights stores color palettes as comma-separated entries: `C_BUTTON_Palette1=#FF0000,C_CHECKBOX_Palette1=1,C_BUTTON_Palette2=#00FF00,C_CHECKBOX_Palette2=1,...`. Each color gets a `C_BUTTON_PaletteN` (hex value) and `C_CHECKBOX_PaletteN` (enabled=1). Maximum 8 palette entries.

---

## R6: Wizard Pattern Reuse

**Decision**: Follow the existing `WizardRunner` pattern from `src/wizard.py` — a class with step methods using questionary prompts, returning a config dataclass.

**Rationale**: The pattern is established, tested, and handles TTY detection gracefully. The sequence wizard adds new steps (layout file, occasion, theme preview) but follows the same structure.

---

## R7: Section-Level Regeneration Strategy

**Decision**: Parse the existing `.xsq`, identify effects within the target section's time range, remove them, regenerate with new theme, and write back.

**Rationale**: The `.xsq` is XML that can be parsed, modified, and re-serialized. Effects have explicit `startTime`/`endTime` attributes that can be matched against section boundaries. Effects outside the target range are preserved untouched, achieving byte-level stability for unmodified sections.

**Alternatives Considered**:
- Full regeneration with section override: Simpler but doesn't guarantee stability of other sections
- Diff-and-patch: Over-engineered for XML modification
