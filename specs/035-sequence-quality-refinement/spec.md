# Feature Specification: Sequence Quality Refinement

**Feature Branch**: `035-sequence-quality-refinement`
**Created**: 2026-04-09
**Status**: Draft
**Input**: Phased improvement plan to make auto-generated xLights sequences look more like hand-sequenced community sequences, based on reference analysis of 5 community .xsq files (docs/reference-sequence-analysis.md).

## User Scenarios & Testing

### User Story 1 - Focused Effect Vocabulary (Priority: P1)

As a user generating a sequence, I want the generator to use a small, proven set of
core effects rather than rotating through the entire library, so that the output looks
coherent and intentional — like a human sequencer who has found what works.

**Why this priority**: Reference analysis shows every skilled sequencer uses 4-9 core
effects for 90% of placements. Our generator rotates too broadly, creating visual
incoherence. This is the single biggest "it doesn't look right" factor.

**Independent Test**: Generate a sequence, run `analyze_reference_xsq.py` on the output.
The top 5 effects should account for 80%+ of placements. Compare effect distribution
against reference sequences.

**Acceptance Scenarios**:

1. **Given** a generated sequence for any song, **When** analyzed with the reference
   tool, **Then** the top 5 effects account for at least 80% of total placements.
2. **Given** a theme assignment for a section, **When** effects are placed, **Then**
   the effect pool for that section is limited to at most 6-8 effects weighted by
   the theme's character (not the full library).
3. **Given** the same theme used across multiple sections, **When** effects are placed,
   **Then** the same core effects repeat (with palette/parameter variation) rather than
   cycling to new effects each section.

---

### User Story 2 - Duration Matches Song Energy (Priority: P1)

As a user, I want effect durations to scale with song tempo and section energy,
so that fast upbeat songs have rapid beat-level effects and slow ballads have
longer breathing effects — matching how human sequencers adapt to the music.

**Why this priority**: Reference analysis shows duration varies dramatically by song
style: 0.5s for upbeat (Light of Christmas), 2-4s for hymns (Away In A Manger).
Our generator uses a fixed approach regardless of tempo.

**Independent Test**: Generate sequences for a fast song (>120 BPM) and a slow song
(<80 BPM). Analyze duration distributions. Fast song should have majority <1s effects,
slow song should have majority 1-4s effects.

**Acceptance Scenarios**:

1. **Given** a song with BPM > 120, **When** a sequence is generated, **Then** the
   median effect duration is under 1 second.
2. **Given** a song with BPM < 80, **When** a sequence is generated, **Then** the
   median effect duration is between 1.5 and 4 seconds, with zero sub-250ms effects.
3. **Given** a song with moderate BPM (80-120), **When** a sequence is generated,
   **Then** the median effect duration falls between the fast and slow ranges.

---

### User Story 3 - Embrace Repetition Within Sections (Priority: P1)

As a user, I want the generator to maintain visual consistency within song sections
rather than constantly changing effects, so that each section has a coherent visual
identity — like how human sequencers hold the same effect+palette for dozens of
consecutive placements.

**Why this priority**: Reference analysis shows 15-63x consecutive same effect+palette
is normal. Our rotation engine actively penalizes repetition, which is backwards —
it creates visual chaos instead of cohesion.

**Independent Test**: Generate a sequence and analyze consecutive repetition. At least
some models should show 10+ consecutive same effect+palette runs within a section.

**Acceptance Scenarios**:

1. **Given** a section lasting 30+ seconds, **When** effects are placed on a model,
   **Then** the same effect+palette combination runs for the entire section on at least
   the base-tier models.
2. **Given** repeated sections (e.g., Chorus 1 and Chorus 2), **When** effects are
   placed, **Then** the same core effect is used but palette or parameters may vary
   for freshness.
3. **Given** a section transition (e.g., Verse to Chorus), **When** the new section
   begins, **Then** the effect vocabulary changes noticeably to mark the transition.

---

### User Story 4 - Dynamic Model Activation by Section (Priority: P2)

As a user, I want the generator to vary how many models are active based on section
energy — fewer models during verses, more during choruses — so that choruses feel
genuinely bigger rather than just changing effects on always-on models.

**Why this priority**: The most impactful visual technique in the reference sequences.
"Shut Up and Dance" goes from 13 active models in verses to 57 in choruses. This
creates real dynamic range that effect changes alone cannot achieve. Ranked P2 because
it requires the P1 changes to be effective — without focused effects and good duration,
just turning models on/off would still look wrong.

**Independent Test**: Generate a sequence for a song with clear verse/chorus structure.
Run the analyzer and check density-over-time. Chorus windows should show 30-50% more
active models than verse windows.

**Acceptance Scenarios**:

1. **Given** a low-energy section (energy < 40), **When** effects are placed, **Then**
   only base-tier and select mid-tier models are active (50-70% of available models).
2. **Given** a high-energy section (energy > 70), **When** effects are placed, **Then**
   all tiers are active including hero and compound models (85-100% of available models).
3. **Given** the density-over-time analysis of a generated sequence, **When** compared
   to the same analysis of a reference sequence for a song of similar style, **Then**
   the dynamic range (max - min active models) is within 50% of the reference range.

---

### User Story 5 - Palette Restraint (Priority: P2)

As a user, I want generated palettes to use 2-4 active colors rather than all 8 slots,
so that color schemes are cleaner and more intentional — matching the 2.8 average active
colors seen in reference sequences.

**Why this priority**: Simpler palettes look more professional. Using all 8 colors
creates muddy, unfocused color schemes. This is a straightforward change with
immediate visual improvement.

**Independent Test**: Generate a sequence, analyze palette patterns. Average active
colors per palette should be 2-4.

**Acceptance Scenarios**:

1. **Given** a generated sequence, **When** palettes are analyzed, **Then** the average
   active colors per palette is between 2 and 4.
2. **Given** a theme with a 4-color palette, **When** the palette is serialized to XSQ,
   **Then** only those 4 colors have active checkboxes; remaining slots are disabled.
3. **Given** a high-energy section with an accent palette, **When** colors are applied,
   **Then** accent colors are added as additional active slots (up to 5-6 max) rather
   than replacing the base palette.

---

### User Story 6 - MusicSparkles Integration (Priority: P3)

As a user, I want the generator to use xLights MusicSparkles on appropriate palettes,
so that pattern-based effects have an audio-reactive sparkle overlay — a technique used
in 30% of palettes in pattern-heavy reference sequences.

**Why this priority**: MusicSparkles is a widely used audio-reactive feature in community
sequences that we completely ignore. It adds visual life to pattern effects. Lower priority
because it's additive polish, not a structural fix.

**Independent Test**: Generate a sequence and verify MusicSparkles appears on 10-30% of
palettes, specifically those using pattern effects (SingleStrand, Pinwheel, Bars).

**Acceptance Scenarios**:

1. **Given** a placement using a pattern-based effect (SingleStrand, Bars, Pinwheel),
   **When** the palette is generated, **Then** MusicSparkles has a chance of being
   enabled (based on section energy and effect type).
2. **Given** a placement using an audio-reactive effect (VU Meter), **When** the palette
   is generated, **Then** MusicSparkles is NOT enabled (redundant with the effect).
3. **Given** a generated sequence, **When** palettes are analyzed, **Then** 10-30% of
   palettes have MusicSparkles enabled.

---

### User Story 7 - Rotation Value Curves on Sustained Effects (Priority: P3)

As a user, I want sustained effects (lasting >2 seconds) to use rotation or parameter
value curves, so that long-running effects have internal animation rather than appearing
static — matching the Ramp and SawTooth curves seen across all reference sequences.

**Why this priority**: Value curves add visual movement to effects without changing the
effect itself. All 5 reference sequences use them. Lower priority because it's refinement
on top of the structural changes.

**Independent Test**: Generate a sequence, count effects with value curves. Effects
lasting >2s should have rotation value curves at a rate matching reference sequences.

**Acceptance Scenarios**:

1. **Given** an effect placement lasting >2 seconds, **When** the effect supports
   rotation, **Then** a Ramp-type rotation value curve is applied.
2. **Given** an effect placement lasting <1 second, **When** placed, **Then** no
   value curves are applied (too short to perceive).
3. **Given** a generated sequence, **When** analyzed, **Then** the percentage of
   effects with value curves is comparable to reference sequences.

---

### Edge Cases

- What happens when a song has very few sections (e.g., ambient music with no verse/chorus)? Dynamic model activation should degrade gracefully to steady-state.
- What happens when BPM detection fails or returns an extreme value? Duration scaling should clamp to reasonable bounds (minimum 250ms, maximum 8s for non-Faces effects).
- What happens when a theme defines only 1-2 effects in its layers? The focused vocabulary constraint is naturally satisfied; no additional filtering needed.
- What happens when all models are in a single group (no tier hierarchy)? Model activation cannot create verse/chorus contrast; should fall back to effect-only dynamics.

## Requirements

### Functional Requirements

- **FR-001**: The generator MUST limit the active effect pool per section to a focused
  working set (at most 8 effects) rather than the full library.
- **FR-002**: Effect duration MUST scale with song BPM and section energy. High BPM
  (>120) sections use beat-level durations (0.25-1s). Low BPM (<80) sections use
  bar-level durations (1.5-4s).
- **FR-003**: The rotation engine MUST allow the same effect+palette to repeat
  consecutively within a section without penalty. Cross-section penalties should
  only apply to prevent the same effect appearing in the same role across non-adjacent
  sections of the same label.
- **FR-004**: The generator MUST modulate the number of active models per section based
  on section energy. Low-energy sections activate fewer tiers/groups than high-energy
  sections.
- **FR-005**: Palette serialization MUST activate only the colors defined by the theme
  (typically 2-4), not fill all 8 slots with active checkboxes.
- **FR-006**: The palette generator MUST support MusicSparkles as an optional enhancement
  on pattern-based effects, controlled by section energy and effect type.
- **FR-007**: Effects lasting >2 seconds MUST have rotation or parameter value curves
  applied when the effect definition supports them.
- **FR-008**: Each change MUST be independently toggleable so that individual improvements
  can be tested in isolation and reverted if needed.
- **FR-009**: The reference analyzer tool (`analyze_reference_xsq.py`) MUST be usable
  as a regression/comparison tool — run on generated output and compare metrics against
  baseline and reference sequences.
- **FR-010**: The generator MUST preserve all existing functionality as the default
  behavior. New behaviors are opt-in via configuration until validated.

### Key Entities

- **EffectProfile**: A curated set of 4-8 effects with weights, associated with a theme
  mood or song energy level. Controls which effects are placed and how frequently.
- **DurationStrategy**: Maps BPM ranges and energy levels to effect duration targets.
  Replaces the current fixed duration_type behavior.
- **ActivationCurve**: Per-section specification of which tiers are active, derived from
  section energy. Controls the "breathing" of model activation across the song.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Generated sequences have top-5 effects accounting for 80%+ of placements
  (reference range: 75-93%).
- **SC-002**: Duration distribution of generated sequences correlates with song BPM
  within the ranges observed in reference sequences (fast: median <1s, slow: median 1.5-4s).
- **SC-003**: Consecutive repetition on base-tier models reaches 10+ per section
  (reference range: 15-63).
- **SC-004**: Density-over-time analysis shows measurable verse/chorus contrast
  (at least 20% more active models in high-energy sections vs low-energy sections).
- **SC-005**: Average active palette colors is between 2 and 4 (reference avg: 2.8).
- **SC-006**: Each improvement phase can be individually enabled/disabled without
  affecting other phases, verified by generating sequences with each phase toggled.
- **SC-007**: No regression in existing test suite when all new behaviors are disabled.

## Assumptions

- Reference sequences from 5 community .xsq files (docs/reference-sequence-analysis.md)
  are representative of "good" sequencing practices. While artistic style varies,
  the structural patterns (vocabulary focus, duration scaling, repetition) are consistent
  across all 5 and likely generalize.
- The existing analysis hierarchy (BPM, energy, sections) provides sufficient data
  to drive the new behaviors. No new audio analysis is needed.
- Changes will be implemented as phases that can be individually toggled, allowing
  incremental validation. Phase ordering follows the priority assignments above.
- The `analyze_reference_xsq.py` tool is the primary comparison mechanism. Visual
  evaluation in xLights remains the ultimate judge but is manual and not automatable.

## Phasing Strategy

Changes are organized into phases that can be implemented, tested, and validated
independently. Each phase has a clear "before/after" metric from the analyzer.

| Phase | Stories | Key Metric | Risk |
|-------|---------|------------|------|
| Phase 1 | US1 (Focused Vocabulary) + US3 (Embrace Repetition) | Top-5 effect % jumps from ~50% to 80%+ | Low — narrows existing behavior |
| Phase 2 | US2 (Duration Scaling) | Duration distribution matches BPM | Medium — changes timing fundamentals |
| Phase 3 | US5 (Palette Restraint) | Active colors drops from 8 to 2-4 | Low — straightforward serialization change |
| Phase 4 | US4 (Dynamic Model Activation) | Density variation across sections | Medium — changes what models are used |
| Phase 5 | US6 (MusicSparkles) + US7 (Value Curves) | Palette features, curve count | Low — additive enhancements |

Each phase is validated by:
1. Running the analyzer on generated output and comparing to baseline
2. Running the analyzer on the same output and comparing to reference sequences
3. Visual spot-check in xLights for at least one test song
