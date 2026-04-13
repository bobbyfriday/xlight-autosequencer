# Reference Sequence Analysis

Analyzing hand-sequenced community .xsq files to understand the vocabulary and grammar
of skilled xLights sequencing. These findings inform how we should improve our
auto-generated sequences.

Tool: `python3 scripts/analyze_reference_xsq.py <file.xsq>`

## Sequences Analyzed

| # | Song | Artist | Duration | Models (active/total) | Effect Placements | Unique Palettes | Sequencer Style |
|---|------|--------|----------|----------------------|-------------------|-----------------|-----------------|
| 1 | Light Of Christmas | TobyMac & Owl City | 3.7 min | 32/73 | 6,302 | 242 | Beat-driven, high energy |
| 2 | Baby Shark | Pinkfong | 1.6 min | 20/311 | 255 | 94 | Sparse, group-based |
| 3 | Away In A Manger | Carrie Underwood | 2.7 min | 28/141 | 1,124 | 37 | Gentle, layered |
| 4 | Christmas Just Ain't Christmas | Idina Menzel | 3.5 min | 12/57 | 1,496 | 96 | Dense, morph-heavy |
| 5 | Shut Up and Dance | Walk the Moon | 3.3 min | 65/93 | 1,425 | 34 | VU Meter-driven, dynamic density |

---

## Sequence 1: Light of Christmas

**Source:** Hand-sequenced community file (xLights 2022.12, Windows)
**Author:** John Storms (listentoourlights.com) — same layout as Baby Shark

### Vocabulary

9 core effects cover 90% of 6,302 total placements:

| Effect | Count | % | Role |
|--------|-------|---|------|
| SingleStrand | 2,537 | 40.3% | Dominant workhorse — used on nearly every model |
| Pinwheel | 826 | 13.1% | Primary on Stars, Spinners |
| Curtain | 673 | 10.7% | Primary on Matrices, MegaTrees |
| Spirals | 440 | 7.0% | MegaTrees, Matrices |
| Shockwave | 374 | 5.9% | Accent hits on Snowflakes, Mini Tree Stars |
| Ripple | 303 | 4.8% | Candy Canes, Spinner, accent layers |
| Bars | 244 | 3.9% | Candy Canes rhythmic patterns |
| On | 214 | 3.4% | Solid color — Mini Trees, Snowflakes |
| Color Wash | 156 | 2.5% | Background wash — various models |

27 effects used total. 24 known xLights effects NEVER used (including Butterfly,
Fire, Fireworks, Lightning, Plasma, Twinkle, Chase).

### Grammar

**Duration:** Beat-level dominant. 48% are 0.5-1s, 30% are 0.25-0.5s, 14% are 2-4s.
1,918 placements under 500ms. Longer effects rare (only Faces/lip-sync).

**Layering:** Matrices=15 layers, MegaTrees=10, Stars=7. Simple props=1-3 layers.
53 models use just 1 layer.

**Density:** 20-30 active models per 10s window. Relatively flat — slight dips in
bridges (20), peaks in choruses (30).

**Repetition:** 63x consecutive same effect+palette on one model layer. Consistency
over variety — Mini Trees run same SingleStrand the entire section.

**Coverage:** 10 models "always on" (>90%), 13 sparse (<30%), 41 empty (sub-models).

### Palette & Timing

- 242 unique palettes, avg 2.8 active colors per palette
- **MusicSparkles: 30%** of palettes, 65 with color value curves, 57 custom SparkleFrequency
- 95.7% of effect boundaries within 25ms of a timing mark
- 90.4% of starts align within 25ms of a beat

### Key Techniques

- **SubBuffer splitting** for quadrant effects on hero props
- **Rotation value curves** (Ramp type) for animation within sustained effects
- **Buffer transforms** (Rotate CC 90, CW 90, Flip Horizontal) for prop orientation
- Heavy multi-layer stacking on Matrices with different effects per layer

---

## Sequence 2: Baby Shark (Jaws Intro)

**Source:** John Storms (listentoourlights.com), xLights 2023.20
**Notable:** 311 total models but only ~20 active — extreme group-based approach

### Vocabulary

7 core effects cover 90% of just 255 placements:

| Effect | Count | % | Role |
|--------|-------|---|------|
| On | 82 | 32.2% | Solid color dominant — simple, direct |
| VU Meter | 50 | 19.6% | Audio-reactive visualizer on groups |
| Bars | 34 | 13.3% | Rhythmic patterns on icicles, trunks |
| Wave | 34 | 13.3% | Movement across deer, treeline, snowflakes |
| Butterfly | 12 | 4.7% | Accent on groups and bracelets |
| Faces | 11 | 4.3% | Singing tree lip-sync |
| Fan | 10 | 3.9% | Star toppers |

Only 14 effects used total. Very restrained vocabulary for a short, fun song.

### Grammar

**Duration:** Bimodal distribution — short accents (0.5-1s: 66) AND long sustained
holds (8-16s: 50, 16-30s: 10). Not much in between. The "On" effect splits between
quick flashes (0.25-0.5s: 28) and long holds (8-16s: 29).

**Layering:** 291 of 311 models use just 1 layer. Only `_HOUSE ALL` gets 5 layers.
Most complexity is in group hierarchy, not layer stacking.

**Density:** Builds from 9 models at start to 24 at peak (60s), drops to 16 near
end, final burst at 22. Clear dynamic arc.

**Repetition:** Max 15x consecutive (VU Meter on _EVERYTHING-NotStrobes). More
moderate repetition than Light of Christmas — shorter song, more variety per section.

**Coverage:** Only 20 of 311 models have effects. Effects are on high-level groups
(`_EVERYTHING-NotStrobes`, `_DEER`, `_TREELINE`) not individual props.

### Palette & Timing

- 94 unique palettes despite only 255 placements — high palette-per-effect ratio
- Avg 2.7 active colors per palette
- **MusicSparkles: 13%** of palettes
- 8 timing tracks including multiple beat rates and lyrics

### Key Techniques

- **Group-level sequencing:** Effects on `_EVERYTHING-NotStrobes` (whole house),
  `_DEER`, `_TREELINE` etc. — NOT individual models
- **VU Meter with timing tracks:** Spectrogram and Timing Event types tied to
  beat/lyric tracks for audio-reactive patterns
- **DMX integration:** DMX Bracelets model with custom channel control
- **Transition effects:** Fan with high Revolutions (1784-3600) on star toppers

---

## Sequence 3: Away In A Manger

**Source:** Community file (xLights 2023.18), likely BFLS (Big Fun Light Show)
**Notable:** Gentle hymn — very different sequencing approach than upbeat songs

### Vocabulary

4 core effects cover 90% of 1,124 placements:

| Effect | Count | % | Role |
|--------|-------|---|------|
| Shockwave | 520 | 46.3% | Dominant — pulsing radial bursts on everything |
| SingleStrand | 307 | 27.3% | Sustained linear movement on arches, spirals |
| Pinwheel | 108 | 9.6% | Rotating patterns on spinners, matrices |
| Morph | 101 | 9.0% | Smooth color transitions on mini trees, outlines |

Only 15 effects used. 36 NEVER used (the most restrictive vocabulary of all 5).
**No Bars, Butterfly, Color Wash, VU Meter, or Garlands** — stripped down to essentials.

### Grammar

**Duration:** Longer than other sequences. Dominant: 2-4s (461, 41%), then 4-8s
(282, 25%), then 1-2s (217, 19%). Zero effects under 250ms. This is a slow song
and the sequencer matches that tempo with longer, breathing effects.

**Notable: Twinkle runs ENTIRE SONG.** 20 Twinkle placements spanning 155s each
(the full song) act as a persistent sparkle base layer on every major model.
This is a "set and forget" base that all other effects layer on top of.

**Layering:** Matrix and Mega Tree get 12 layers each. MegaSpinners get 9.
Most other models get 4-5 layers — more uniform than other sequences.

**Density:** Very stable 24-28 active models throughout. Minimal variation —
appropriate for a gentle hymn that shouldn't have dramatic intensity swings.

**Repetition:** Max 16x consecutive (Shockwave on Snowflakes). Moderate.

**Coverage:** 18 models "always on" (96.2% coverage each). Only 2 sparse, 113 empty.
Very clean: effects on groups, sub-models all empty.

### Palette & Timing

- Only 37 unique palettes — the most restrained palette of all sequences
- Avg 2.8 active colors per palette
- **MusicSparkles: 8%** — minimal, appropriate for gentle hymn
- 50ms timing resolution (not 25ms) — less precise, matching the slower tempo
- Beat alignment looser: only 15.9% within 25ms, 74.7% within 100ms

### Key Techniques

- **Full-song base layer:** Twinkle on every model for the entire duration
- **SubBuffer quadrants** on Shockwave for different radial centers
- **Morph for color transitions:** Smooth start→end morphs instead of abrupt changes
- **BufferStyle "Per Model Per Preview"** on Shockwave for model-aware rendering
- **Gentle Fadein/Fadeout** on many effects (0.2s-2s) — no hard cuts
- **Pictures effect** with Nativity Scene images on matrices (seasonal content)

---

## Sequence 4: Christmas Just Ain't Christmas

**Source:** Community file (xLights 2020.45)
**Notable:** Only 12 active models out of 57 — extremely focused sequencing

### Vocabulary

5 core effects cover 90% of 1,496 placements:

| Effect | Count | % | Role |
|--------|-------|---|------|
| Morph | 455 | 30.4% | Dominant — smooth color transitions everywhere |
| SingleStrand | 372 | 24.9% | Linear chase patterns on outlines, arches |
| Shockwave | 295 | 19.7% | Radial pulses on spinners, snowflakes |
| Bars | 120 | 8.0% | Rhythmic movement on mega tree, outlines |
| Butterfly | 118 | 7.9% | Organic patterns on arches, spinners |

Only 10 effects used total. 41 NEVER used. Morph as #1 effect is unique to this
sequence — this sequencer favors smooth organic transitions over hard cuts.

### Grammar

**Duration:** 1-2s dominant (742, 50%), then 2-4s (411, 27%). Beat-aligned but
at a slower pace than Light of Christmas. Very few sub-second effects (20 total).

**Layering:** Modest. MegaTree gets 6 layers (the max), most models get 2-4.
Arches and Spiral Trees get 4 layers with 80 overlapping segments — heavy
concurrent effects on outline props.

**Density:** Perfectly flat — 10-12 active models every 10s window. The most
stable density of any sequence. Only 12 models used but ALL are active nearly
all the time.

**Repetition:** Max 24x consecutive (SingleStrand on multiple models). Morph
patterns repeat 12x with DIFFERENT palettes per repeat — same effect structure
but cycling through color schemes.

**Coverage:** 10 models at 99%+ coverage, 2 at 57-64%. Zero sparse models.
45 empty. This sequencer uses every model they sequence to its fullest.

### Palette & Timing

- 96 unique palettes, avg 3.1 active colors
- **MusicSparkles: 0%** — never used
- 18 palettes with color value curves, 13 custom SparkleFrequency
- Only 1 timing track (Beat Count: 415 marks)
- Beat alignment: 23.4% within 25ms, 67.7% within 100ms — looser sync

### Key Techniques

- **Morph-heavy approach:** Using Morph to smoothly transition between color
  states rather than cutting between effects. Creates flowing, organic feel.
- **Blur value curves** on Bars effect — animated blur intensity
- **Transition value curves** on Curtain — custom In/Out transition adjustments
- **BufferStyle variety:** "Horizontal Per Model", "Per Model/Strand" for
  different rendering modes on the same effect type
- **Palette cycling with consistent effects:** Same SingleStrand/Morph patterns
  but rotating through different palettes each repetition

---

## Sequence 5: Shut Up and Dance

**Source:** Community file (xLights 2023.20), attributed to Bill Jenkins
**Notable:** VU Meter as 73% of all placements — audio-reactive dominant approach

### Vocabulary

4 core effects cover 90% of 1,425 placements:

| Effect | Count | % | Role |
|--------|-------|---|------|
| VU Meter | 1,035 | 72.6% | Overwhelming dominant — audio-reactive on everything |
| On | 113 | 7.9% | Solid color accents, short flashes |
| Shader | 113 | 7.9% | Custom shader effects on trees, matrices |
| Wave | 41 | 2.9% | Movement patterns on stakes, matrices |

13 effects used total. 38 NEVER used. This is the most extreme single-effect
dominance of any sequence — VU Meter carries the entire show.

### Grammar

**Duration:** 2-4s dominant (541, 38%), then 1-2s (381, 27%), then 8-16s (198, 14%).
Notably, 83 effects under 250ms — these are short "On" flash accents used as
punctuation between VU Meter sections.

**Layering:** Mostly 2 layers (23 models), MegaTrees get 5 layers. Lighter layering
than other sequences — the VU Meter carries visual interest through audio reactivity
rather than layer stacking.

**Density:** DRAMATIC variation — the most dynamic of all sequences. Starts at 14
models, builds to 55-57 during choruses, drops to 13-17 during verses/bridge
(110-140s), then back to 55+ for the finale. This is the only sequence with a
clear verse/chorus density pattern.

**Repetition:** 21x consecutive VU Meter on MegaTrees. 18x Butterfly on Frozen
Brillance. Consistent with other sequences — sustained patterns.

**Coverage:** 7 models "always on" (90%+), but wide middle tier: 28 models at
33-88% coverage. 11 sparse, 28 empty. More graduated coverage than other sequences.

### Palette & Timing

- Only 34 unique palettes — very restrained
- Avg **5.5 active colors per palette** — highest of any sequence, many use 7-8 slots
- **MusicSparkles: 0%** (VU Meter IS the audio reactivity)
- 12 timing tracks including Drums, Bass, Beats (128/256 bpm), Note Onsets,
  Measures, Structure, multiple Lyrics tracks
- 98.1% of effect boundaries within 25ms of any timing mark (extremely tight)

### Key Techniques

- **VU Meter as primary effect:** Types include Spectrogram, Timing Event Color,
  Timing Event Pulse, Timing Event Timed Sweep — each variant tied to different
  timing tracks (Drums, Bass, Beats)
- **Shader (SHADERXYZZY):** 113 variants with extensive SubBuffer, rotation,
  and buffer style customization. Custom visual programs.
- **Saw Tooth value curves** on Wave parameters (Thickness_Percentage, Wave_Height)
  for rhythmic pulsing tied to timing tracks
- **Pinwheel Twist value curves** with custom multi-point curves for oscillating
  twist animation
- **Dramatic density modulation:** Verse=sparse (13 models), Chorus=dense (57 models).
  Individual props are ON/OFF by section to create real dynamic range.
- **Short "On" flashes** (<250ms) as punctuation — 80 of 113 On effects are under 250ms

---

## Cross-Sequence Trends

### 1. Small Working Vocabulary

Every sequencer uses 4-9 core effects for 90% of placements. The full xLights
library has 50+ effects but skilled sequencers find their core set and commit.

| Sequence | Core effects (90%) | Total unique | Top effect % |
|----------|-------------------|--------------|--------------|
| Light of Christmas | 9 | 27 | SingleStrand 40% |
| Baby Shark | 7 | 14 | On 32% |
| Away In A Manger | 4 | 15 | Shockwave 46% |
| Christmas Just Ain't | 5 | 10 | Morph 30% |
| Shut Up and Dance | 4 | 13 | VU Meter 73% |

**Takeaway:** Each sequencer has a dominant "signature" effect. Variety comes from
palette changes and parameter tweaks, not effect switching.

### 2. Duration Matches Song Energy

| Sequence | Song Style | Dominant Duration |
|----------|-----------|-------------------|
| Light of Christmas | Upbeat pop | 0.5-1s (beat-level) |
| Baby Shark | Children's/fun | Bimodal: 0.5-1s accents + 8-16s holds |
| Away In A Manger | Gentle hymn | 2-4s (bar-level), zero sub-250ms |
| Christmas Just Ain't | Mid-tempo ballad | 1-2s (beat-level, slower tempo) |
| Shut Up and Dance | High energy dance | 2-4s (VU Meter sustains, On flashes) |

**Takeaway:** Duration isn't one-size-fits-all. Slow songs use longer effects.
Fast songs use shorter effects. The generator should scale duration with BPM/energy.

### 3. Intentional Repetition Over Forced Variety

| Sequence | Max consecutive same effect+palette |
|----------|-------------------------------------|
| Light of Christmas | 63x |
| Baby Shark | 15x |
| Away In A Manger | 16x |
| Christmas Just Ain't | 24x |
| Shut Up and Dance | 21x |

**Takeaway:** Repetition is the norm, not a flaw. Sequencers maintain visual
consistency within sections and change at section boundaries, not every bar.

### 4. Hierarchical Model Treatment — Groups Over Sub-Models

| Sequence | Total Models | Active Models | % Active | Empty Models |
|----------|-------------|---------------|----------|--------------|
| Light of Christmas | 73 | 32 | 44% | 41 |
| Baby Shark | 311 | 20 | 6% | 291 |
| Away In A Manger | 141 | 28 | 20% | 113 |
| Christmas Just Ain't | 57 | 12 | 21% | 45 |
| Shut Up and Dance | 93 | 65 | 70% | 28 |

**Takeaway:** Most sequencers work with groups/parent models, leaving individual
sub-models empty. Only Shut Up and Dance addresses many individual models, and
even that leaves 30% empty.

### 5. Palette Restraint

| Sequence | Unique Palettes | Avg Active Colors | MusicSparkles |
|----------|----------------|-------------------|---------------|
| Light of Christmas | 242 | 2.8 | 30% |
| Baby Shark | 94 | 2.7 | 13% |
| Away In A Manger | 37 | 2.8 | 8% |
| Christmas Just Ain't | 96 | 3.1 | 0% |
| Shut Up and Dance | 34 | 5.5 | 0% |

**Takeaway:** Most palettes use only 2-3 active colors, not all 8 slots. The
exception is Shut Up and Dance which uses 5.5 avg — possibly because VU Meter
benefits from more colors for spectrum visualization. MusicSparkles is used
when the effect approach is pattern-based (SingleStrand, Pinwheel) but NOT
when the approach is already audio-reactive (VU Meter).

### 6. Density Patterns Vary by Song Structure

- **Flat density** (Light of Christmas, Manger, Idina): 20-30 models active
  consistently. Works for songs with steady energy.
- **Dynamic density** (Shut Up and Dance): 13→57→13→57 models. Verse/chorus
  contrast through prop activation, not just effect changes.
- **Building density** (Baby Shark): 9→24, builds throughout the short song.

**Takeaway:** The best sequences use model count as an intensity control — not
every model needs to be on all the time. Turning props ON at chorus and OFF
at verse creates visual dynamics that pure effect switching cannot.

### 7. Value Curves and SubBuffer Are Power Tools

All 5 sequences use at least some of:
- **SubBuffer:** Splitting models into regions for different effects (especially
  on matrices, mega trees, large props)
- **Rotation value curves:** Ramp, Saw Tooth, Custom curves to animate rotation
- **Parameter value curves:** Wave Height, Thickness, Blur tied to timing tracks

Shut Up and Dance is the most extreme — Saw Tooth curves on Wave parameters
tied to drum/bass timing tracks, and custom multi-point curves on Pinwheel Twist.

### 8. Effects Never Used Across ALL 5 Sequences

These effects appear in zero sequences analyzed:
- Candle, Fill, Fireworks, Glediator, Life, Lightning, Lines, Liquid,
  Music, Plasma, Servo, Snowstorm, Spirograph, State, Tendril

These are either niche/deprecated or unsuitable for outdoor Christmas displays.

### 9. Universally Popular Effects

Effects used in 4+ of 5 sequences:
- **On** (5/5) — solid color, universally useful
- **Shockwave** (5/5) — radial burst, good accent/pulse
- **SingleStrand** (4/5) — chase patterns, linear movement
- **Pinwheel** (4/5) — rotation, good on radial/star props
- **VU Meter** (4/5) — audio-reactive visualization
- **Butterfly** (4/5) — organic patterns
- **Faces** (4/5) — lip-sync (specialized)

### 10. Beat Alignment Varies More Than Expected

| Sequence | Effect starts within 25ms of beat |
|----------|----------------------------------|
| Light of Christmas | 90.4% |
| Shut Up and Dance | 56.3% |
| Away In A Manger | 15.9% |
| Christmas Just Ain't | 23.4% |

**Takeaway:** Only the upbeat, beat-driven sequences have tight beat alignment.
Slower/gentler songs align more loosely — effects land between beats for a more
flowing feel. Our generator's strict beat-snapping may be wrong for slow songs.

---

## Implications for Our Generator

| Our Current Approach | What References Show | Priority | Suggested Change |
|---------------------|---------------------|----------|-----------------|
| Wide effect rotation across pool | 4-9 core effects = 90% of placements | **HIGH** | Reduce working set per theme. Weight heavily toward proven effects (SingleStrand, Shockwave, On, Pinwheel, Morph). |
| Effects placed per-bar or per-section | Duration scales with song energy (0.5s for fast, 2-4s for slow) | **HIGH** | Scale effect duration with BPM. Fast songs → beat-level, slow songs → bar-level. |
| Rotation engine penalizes repetition | 15-63x consecutive same effect is normal | **HIGH** | Remove or weaken cross-section repetition penalty. Allow sustained patterns. |
| All tiers get effects for every section | 6-70% of models are active, rest empty | **HIGH** | Use model count as intensity control. Verse=fewer active models, Chorus=more. |
| All 8 palette colors populated | Average 2.8 active colors (2-3 typical) | **MEDIUM** | Use 2-4 active palette colors. Leave unused slots disabled. |
| No MusicSparkles | Used on 8-30% of palettes in pattern-based sequences | **MEDIUM** | Add MusicSparkles to palettes when using pattern effects (not VU Meter). |
| No SubBuffer usage | Extensively used on hero props across all sequences | **MEDIUM** | Implement SubBuffer splitting for matrices and large multi-region props. |
| No Rotation/parameter value curves | Used in all sequences for animation | **MEDIUM** | Add Ramp/SawTooth rotation curves to sustained effects (>2s). |
| Uniform beat-grid snapping | Slow songs only 16-23% on-beat | **MEDIUM** | Loosen beat-snap for low-BPM songs. Allow between-beat placement. |
| Uniform density (all models always active) | Dynamic: 13→57 model count varies by section | **MEDIUM** | Modulate active model count by section energy. Low energy = fewer models. |
| No full-song base layer | Manger uses Twinkle spanning entire song on all models | **LOW** | Consider persistent base layer (Twinkle/On) for gentle songs. |
| No "On" effect for solid color holds | "On" used in all 5 sequences (2-32% of placements) | **LOW** | Add "On" as a valid effect for low-energy sections or accent flashes. |
| No Shader/custom visual programs | Shut Up and Dance uses 113 Shader placements | **LOW** | Future consideration — requires custom shader content. |
