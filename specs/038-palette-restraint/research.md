# Research: Palette Restraint

## R1: Current Palette Serialization

**Decision**: Restrain palette by trimming the `color_palette` list before serialization,
not by modifying `_serialize_palette` internals.

**Rationale**: `_serialize_palette` (xsq_writer.py:376-393) already uses `len(colors)` to
determine how many checkboxes are active. Passing a shorter list automatically produces
fewer active slots. This requires zero changes to the serialization function itself.

**Alternatives considered**:
- Adding an `active_count` parameter to `_serialize_palette` — rejected because it
  splits the active count decision across two files instead of keeping it in the placer.
- Adding a post-processing pass to flip checkboxes — rejected because it's more complex
  and error-prone than simply passing fewer colors.

## R2: MusicSparkles Format

**Decision**: MusicSparkles is a palette-level slider, not a per-effect parameter.
Format: `C_SLIDER_MusicSparkles=N` where N is 0-100. Appended to the palette string
alongside C_BUTTON and C_CHECKBOX entries.

**Rationale**: Reference XSQ analysis confirms this is a palette attribute. It appears
inside the ColorPalette entry, not in the Effect entry. Value 0 means disabled; values
20-80 are typical in reference files. The slider value IS the sparkle frequency — there
is no separate `SparkleFrequency` parameter.

**Alternatives considered**:
- Treating as an effect parameter (E_SLIDER_MusicSparkles) — incorrect; reference files
  show it in the palette section.
- Using a checkbox + separate frequency — incorrect; xLights uses a single slider where
  0=off and >0=frequency.

## R3: Active Color Count Targets

**Decision**: Target 2-4 active colors with energy scaling. Formula:
`active = 2 + floor(energy / 33)`, capped by tier.

**Rationale**: Reference analysis of 5 community XSQ files:
- 4 of 5 files average 2.5-3.6 active colors per palette
- 1 outlier (Shut Up and Dance) at 5.5 — VU Meter heavy, not representative
- The formula produces 2 at energy 0-32, 3 at 33-65, 4 at 66-99, 5 at 100
- Tier caps prevent base tiers from exceeding 3, while hero tiers can reach 6

**Alternatives considered**:
- Fixed count of 3 everywhere — rejected; loses the energy-driven dynamic range
  that makes choruses feel richer than verses.
- Continuous scaling (e.g., 2 + energy/25) — rejected; produces fractional values
  and over-complicates what should be a discrete slot count.

## R4: Tier-Based Palette Variety

**Decision**: Different tier caps on active color count:
- Tiers 1-2 (BASE, GEO): max 3 active colors
- Tiers 3-4 (TYPE, BEAT): max 4 active colors
- Tiers 5-6 (TEX, PROP): max 4 active colors
- Tiers 7-8 (COMP, HERO): max 6 active colors

**Rationale**: Reference files show hero models (matrices, mega trees) with more
palette variety than simple props. The tier system already differentiates visual
treatment (dim palette for tiers 1-2, accent for 3+). Extending this to active
color count creates consistent visual hierarchy.

**Alternatives considered**:
- Same cap for all tiers — rejected; misses the visual depth opportunity and
  doesn't match reference file patterns.
- Per-prop-type caps — rejected; over-complicated for minimal benefit. Tier-based
  is sufficient granularity.

## R5: MusicSparkles Probability

**Decision**: Enable MusicSparkles with probability `energy / 200`, producing
0% at energy 0 and 50% at energy 100. Overall sequence average: 10-30% for
typical pop songs with verse/chorus structure.

**Rationale**: Reference files show 8-30% MusicSparkles usage. Energy-based
probability naturally concentrates sparkles in high-energy sections (choruses)
and suppresses them in low-energy sections (verses, intros). The `/200` divisor
was chosen to hit the 10-30% target range for typical song energy distributions.

**Alternatives considered**:
- Fixed 20% probability — rejected; doesn't vary with energy, missing the
  dynamic quality seen in reference files.
- Energy threshold (only above 60) — rejected; too binary, doesn't create
  the gradual increase seen in references.
