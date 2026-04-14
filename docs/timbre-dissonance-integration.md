# Timbre, Dissonance, and Stem Dominance — Generator Integration RFC

Status: **Investigation / RFC — not implemented**
Related feature: `043-tier-selection` (see `specs/043-tier-selection/` if present)
Last updated: 2026-04-14

## Context

The sequence generator today decides tier activation, palette, brightness, and
effect placement from two primary signals:

- `section.energy_score` (0–100) → bucketed into `ethereal / structural / aggressive`
- Phrase structure detected via `_has_strong_phrase_structure()` (043)

Three richer musical signals are computed upstream but under-utilized (or fully
unused) in the generator:

| Signal | Status in generator |
|---|---|
| Tonality (chord quality, key) | ✅ active — palette blend + brightness via tension |
| Dissonance / tension | ⚠ partially active — brightness modulation only |
| Timbre (spectral brightness, centroid) | ❌ dormant — story-only |
| Stem dominance (drums-led / vocal-led / instrumental) | ❌ dormant — analyzer only |

This doc catalogs where these signals are computed, where they are (or could be)
consumed, and ranks candidate integrations by impact. It is not a spec — when a
follow-up feature is scoped, that work gets its own `specs/NNN-*/` directory.

---

## 1. Timbre (spectral brightness, centroid)

### Where it's computed

- `src/analyzer/stem_inspector.py:59-95` — librosa-based
  `spectral_centroid_hz` per stem
- `src/story/stem_curves.py:54-111` — assembles `spectral_centroid_hz` per stem
  and full_mix, line 108 emits the combined structure
- `src/story/section_profiler.py:266-275` — derives `spectral_brightness`
  label (`"bright"` / `"dark"` / `"neutral"`) from treble_ratio; estimates
  `spectral_centroid_hz` from treble_ratio

### Where it's consumed today

Only by the review UI / story pipeline. No reference to `spectral_brightness`
or `spectral_centroid_hz` in `src/generator/**`.

### Candidate integrations (generator)

Ranked by expected impact ÷ effort:

1. **Palette saturation / warmth** (small effort, high impact)
   - Bright sections → saturated, high-chroma palette (clear whites, vivid
     saturated hues)
   - Dark sections → muted, warm palette (amber, deep reds, low saturation)
   - Hook into `_resolve_palette()` at
     [`src/generator/effect_placer.py`](../src/generator/effect_placer.py) line ~1000;
     apply saturation scaling before or after chord blending
   - Works section-wide — no per-placement cost

2. **Effect variant bias** (medium effort, high impact)
   - Bright → Twinkle, Meteors, Sparkle, Shimmer (crisp, detailed)
   - Dark → Color Wash, Ripple, Plasma, Warp (soft, sustained)
   - Extend the `WorkingSet` weighting (see `src/generator/working_set.py`) to
     accept a timbre bias that re-weights eligible variants

3. **MusicSparkles frequency** (small effort, small impact)
   - Bright sections already "look crisp" — more sparkles reinforce
   - Plug into the existing `compute_music_sparkles()` call inside
     `place_effects()`; add a timbre multiplier

4. **Duration scaling modifier** (medium effort, medium impact)
   - Bright → bias shorter effect placements (snappy, percussive feel)
   - Dark → bias longer placements (sustained, contemplative)
   - Modify `compute_duration_target()` in
     [`src/generator/effect_placer.py`](../src/generator/effect_placer.py); it
     already takes BPM and energy — add a timbre factor

5. **Prop affinity weighting** (larger effort, medium impact)
   - Bright favors high-pixel-density props (Tune To Matrix, Panel Matrix,
     ChromaStar) for detail resolution
   - Dark favors soft-glow props (GE Practical bulbs, Flakes)
   - Would interact with the future prop-suitability matrix (see
     `CLAUDE.md` "Prop Effect Suitability" future work section)

**Recommended first step:** palette saturation (#1). Highest impact per line of
code, no architecture changes, fits cleanly alongside the existing chord-blend
pipeline.

---

## 2. Dissonance / tension

### Where it's computed

- `src/generator/chord_colors.py:245-283` — `build_tension_curve()`. Each chord
  is classified via `classify_tension()` (line 261), producing scores in
  roughly 10–80. V7→I resolutions get an extra dip (line 264-268). Output is
  a time-indexed list of `(ms, tension)` pairs.

### Where it's consumed today

- [`src/generator/effect_placer.py:450`](../src/generator/effect_placer.py#L450) —
  `tension_curve` constructed from chord marks
- [`src/generator/effect_placer.py:992-995`](../src/generator/effect_placer.py#L992-L995) —
  `tension_at_time()` samples the curve at each placement's midpoint; passed
  to `adjust_palette_brightness()` which scales brightness: tension 10 → 55%,
  tension 80 → 115% (see `src/generator/chord_colors.py:305-320`).

**That's the only use.** Placement timing, effect selection, density, and
duration are tension-blind.

### Candidate integrations

1. **Placement density on builds / resolutions** (medium effort, high impact)
   - High and rising tension → compress placements, add accent overlays,
     increase beat-density coefficient
   - Falling tension (V7→I, cadence) → space placements, let the release
     "breathe" visually
   - Hook into `_apply_density_filter()` at
     [`src/generator/effect_placer.py`](../src/generator/effect_placer.py) and
     the per-beat placement loops — scale the filter threshold by local
     tension slope

2. **Effect variant selection** (medium effort, medium impact)
   - High tension → aggressive variants (Strobe, Fire, Shockwave)
   - Low tension / resolution → soft variants (Color Wash, Shimmer, Wave)
   - Same `WorkingSet` weighting extension as timbre #2

3. **Value curves within placements** (large effort, high impact)
   - Value curves are currently disabled (see `src/generator/value_curves.py`
     and CLAUDE.md "Value Curves Integration" future-work note)
   - Tension-driven ramps would let a single placement *build* or *release*
     internally — e.g. Fire height ramps up through a build, Ripple speed
     decelerates at a resolution
   - This is the biggest payoff but requires the value-curves plumbing to
     come online first

4. **Color hue shifts** (small effort, small-medium impact)
   - High tension nudges palette toward red/amber (warm, anxious)
   - Resolution nudges toward cool blue/green (calm, resolved)
   - Extend `_resolve_palette()` to apply a tension-driven HSV hue rotation
     alongside the existing brightness adjustment

**Recommended first step:** placement density (#1). Tension is most audibly
reflected in *when things happen* in music; matching that in the visual
domain is more musically grounded than brightness alone.

---

## 3. Stem dominance

### Where it's computed

- `src/analyzer/interaction.py:21-79` — `compute_leader_track()` scores each
  stem per frame using RMS (0.7 weight) + spectral flux (0.3 weight) and
  returns the dominant stem with transition points
- `src/analyzer/result.py:504-507` — `hierarchy.energy_curves:
  dict[str, ValueCurve]` exposes per-stem energy
- `src/story/section_profiler.py` — extracts per-stem energy distributions
  into `SectionCharacter`

### Where it's consumed today

Only the `drums` curve is sampled, and only for drum-accent gating
([`src/generator/effect_placer.py`](../src/generator/effect_placer.py) near
line 1470). No reference to leader tracks, stem dominance transitions, or
vocal/bass/piano curves influencing placement, palette, or effect selection.

### Candidate integrations

1. **Tier-selection refinement** (medium effort, very high impact)
   - Overlay stem dominance on the existing energy→mood bucketing
   - Drums-led structural section → override to Tier 4 (BEAT chase) even if
     energy score suggests GEO/PROP
   - Vocal-led structural → bias toward Tier 8 (HERO spotlight) + Tier 6
     (simple PROP variety) so the matrices "sing along"
   - Instrumental / harmonic (no dominant stem or piano-led) → GEO
     call-response or Tier 1 ambient wash
   - Hook: extend `_compute_active_tiers()` at
     [`src/generator/effect_placer.py`](../src/generator/effect_placer.py) to
     take a dominance hint sampled from the leader track at section midpoint

2. **Palette warmth by lead stem** (small effort, medium impact)
   - Vocal-led → warm palette (skin tones, golds, soft whites)
   - Drums-led → cool aggressive palette (blues, cyans, whites with amber
     accents)
   - Piano/strings-led → pastel or cool jewel tones
   - Bass-led → deep saturated tones

3. **Effect variant bias by lead stem** (medium effort, medium impact)
   - Vocal-led → Shimmer, Twinkle, Color Wash (sustained, expressive)
   - Bass-led → Plasma, Wave (slow, heavy)
   - Drums-led → Strobe, Bars, Shockwave (sharp, percussive)
   - Guitar/lead-led → Meteors, Spirals (kinetic)

4. **Solo / lead-in detection** (large effort, high impact)
   - `interaction.py` can detect solo passages (one stem dominates while
     others are quiet). These are prime hero-spotlight moments.
   - Trigger hero-tier-only placements during detected solos regardless of
     mood bucket

**Recommended first step:** tier-selection refinement (#1). Stem dominance is
arguably a *better* signal than energy bucketing for choosing which tier
should carry the section. Currently the tier decision is driven by a crude
1D energy projection; adding dominance makes the choice musically coherent.

---

## Suggested follow-up sequence

1. **Tier selection refinement via stem dominance** (above, #1 under stem
   dominance) — highest leverage; directly improves the 043 tier-selection
   feature that just shipped
2. **Palette saturation via timbre** (above, #1 under timbre) — small, safe,
   highly visible improvement
3. **Placement density via tension** (above, #1 under tension) — medium
   effort, strongly felt musically
4. **Value-curves bringup + tension ramps** — large effort but unlocks a
   dimension we're currently missing entirely

Each of the first three can land as an independent feature in the 044+ range.
