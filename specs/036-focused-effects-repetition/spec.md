# Feature Specification: Focused Effect Vocabulary + Embrace Repetition

**Feature Branch**: `036-focused-effects-repetition`
**Created**: 2026-04-09
**Status**: Draft
**Input**: Phase 1 of the Sequence Quality Refinement plan (035). Addresses the two highest-impact structural gaps between auto-generated sequences and hand-sequenced community references: effect vocabulary is too broad (our generator rotates through ~10 effects evenly) and the rotation engine actively penalizes repetition (community sequences sustain 15-63 consecutive identical effect+palette placements per model).

## Clarifications

### Session 2026-04-09

- Q: Are working set weights hand-curated per theme, algorithmically derived from theme layer structure, or hybrid? → A: Algorithmically derived from existing theme layer structure (no manual data entry per theme).
- Q: Does Phase 1 repetition policy apply to beat tier (Tier 4) which uses a chase pattern? → A: No. Beat tier chase pattern is unchanged. Phase 1 applies only to non-beat tiers.

## User Scenarios & Testing

### User Story 1 - Focused Working Set Per Theme (Priority: P1)

As a user generating a sequence, I want each theme to define a small, weighted working
set of core effects (4-8) so that the generated output looks coherent and intentional --
like a human sequencer who has found what works and commits to it.

**Why this priority**: Reference analysis shows every skilled sequencer uses 4-9 core
effects for 90% of placements, with the top effect alone accounting for 30-73%. Our
generator distributes placements too evenly across ~10 effects, producing visual
incoherence. This is the single biggest "it doesn't look right" factor.

**Independent Test**: Generate a sequence for any song, run the reference analyzer on
the output. The top 5 effects should account for 80%+ of total placements, and the
distribution should show a clear dominant effect (top effect > 25%).

**Acceptance Scenarios**:

1. **Given** a generated sequence for any song, **When** analyzed with the reference
   analyzer tool, **Then** the top 5 effects account for at least 80% of total
   placements.
2. **Given** a theme assignment for a section, **When** effects are placed, **Then**
   the active effect pool for that section contains at most 8 distinct effects, weighted
   by the theme's character rather than uniformly distributed.
3. **Given** the same theme used across multiple non-adjacent sections (e.g., Chorus 1
   and Chorus 3), **When** effects are placed, **Then** both sections use the same core
   effects from the theme's working set.
4. **Given** a theme that inherently defines only 2-3 effects in its layers, **When**
   effects are placed, **Then** the focused vocabulary constraint is naturally satisfied
   with no additional filtering or padding.

---

### User Story 2 - Sustained Repetition Within Sections (Priority: P1)

As a user, I want the generator to maintain the same effect+palette combination on a
model for the duration of a section rather than rotating effects every few bars, so that
each section has a coherent visual identity -- like how community sequencers hold a
single effect for dozens of consecutive placements.

**Why this priority**: Reference analysis shows 15-63 consecutive same effect+palette
placements per model within a section is normal. Our rotation engine applies a 0.3x
penalty for intra-section reuse and a 0.5x penalty for cross-section same-label reuse,
which is backwards -- it creates visual chaos instead of cohesion.

**Independent Test**: Generate a sequence for a song with sections lasting 30+ seconds.
Analyze consecutive repetition per model. Base-tier models should show 10+ consecutive
same effect+palette runs within a section.

**Acceptance Scenarios**:

1. **Given** a section lasting 30+ seconds, **When** effects are placed on a base-tier
   model, **Then** the same effect+palette combination runs for the entire section
   duration without interruption.
2. **Given** a section lasting 30+ seconds, **When** effects are placed on an upper-tier
   model, **Then** the same effect runs for the section, though palette or parameters
   may vary for visual interest.
3. **Given** repeated sections with the same label (e.g., Chorus 1 and Chorus 2),
   **When** effects are placed, **Then** the same core effect is used on matching models,
   but palette or parameters may differ to provide freshness.
4. **Given** a section transition (e.g., Verse to Chorus), **When** the new section
   begins, **Then** the effect vocabulary changes noticeably to visually mark the
   transition.

---

### User Story 3 - Theme Working Set Weights (Priority: P2)

As a user, I want the theme's working set to include frequency weights so that one or
two "signature" effects dominate the section while remaining effects serve as accents,
matching the 30-73% top-effect dominance seen in community sequences.

**Why this priority**: It is not enough to simply limit the pool size. Community
sequences show a steep distribution curve -- one effect dominates, a few support it,
and the rest are rare accents. Uniform selection from a smaller pool would still look
too varied.

**Independent Test**: Generate a sequence and count effect placements by type. The
top effect should account for at least 25% of all placements, and the distribution
should follow a steep curve (top 2 effects > 50%).

**Acceptance Scenarios**:

1. **Given** a theme with a weighted working set, **When** effects are selected for
   placement, **Then** higher-weighted effects appear proportionally more often than
   lower-weighted ones.
2. **Given** a generated sequence, **When** the effect distribution is analyzed,
   **Then** the top effect accounts for at least 25% of total placements.
3. **Given** a generated sequence, **When** the effect distribution is analyzed,
   **Then** the top 2 effects together account for at least 50% of total placements.

---

### User Story 4 - Independent Toggle (Priority: P2)

As a user or developer, I want the focused vocabulary and repetition behaviors to be
individually toggleable so that each can be tested in isolation, compared against the
previous baseline, and reverted if needed without affecting other generator behavior.

**Why this priority**: This is Phase 1 of a 5-phase refinement. Each phase must be
independently verifiable. A toggle also allows A/B comparison during visual validation
in xLights.

**Independent Test**: Generate two sequences for the same song -- one with Phase 1
behaviors enabled, one with them disabled. The disabled version should produce output
identical to the current baseline. The enabled version should show measurably different
effect distributions and repetition patterns.

**Acceptance Scenarios**:

1. **Given** the focused vocabulary behavior is disabled, **When** a sequence is
   generated, **Then** the output matches the pre-Phase-1 baseline behavior exactly.
2. **Given** the repetition behavior is disabled but focused vocabulary is enabled,
   **When** a sequence is generated, **Then** the effect pool is narrowed but rotation
   penalties still apply as before.
3. **Given** both behaviors are enabled, **When** a sequence is generated, **Then** the
   output shows both a narrower effect distribution and higher consecutive repetition
   counts compared to baseline.
4. **Given** all Phase 1 behaviors are disabled, **When** the existing test suite is
   run, **Then** all tests pass with no regressions.

---

### Edge Cases

- What happens when a theme defines only 1-2 effects in its layers? The focused
  vocabulary constraint is naturally satisfied; no additional filtering or minimum
  pool size is needed.
- What happens when a song has a single long section with no transitions? The sustained
  repetition behavior should hold the same effect+palette for the entire section, which
  may produce a very uniform sequence. This is correct behavior for a song with no
  structural variation.
- What happens when a theme's working set weights are all equal? The system should
  degrade gracefully to approximately uniform selection within the working set (still
  limited to the pool size, still better than the full library).
- What happens when cross-section transitions use the same theme? The repetition
  behavior should still allow effect changes at section boundaries even when the theme
  does not change, since section boundaries are the natural point for visual refresh.
- What happens when a very short section (<10 seconds) occurs? The effect should still
  hold for the full section duration rather than being cut short -- even one or two
  placements should use the same effect.
- What happens when the toggle is flipped mid-generation (e.g., enabled for some
  sections, disabled for others)? This is not a supported scenario. The toggle applies
  to the entire generation run.
- What happens on the beat tier (Tier 4)? Phase 1 does not change beat tier behavior.
  The existing chase pattern (round-robin beats across groups) is preserved. Focused
  vocabulary and repetition policy apply only to non-beat tiers.

## Requirements

### Functional Requirements

- **FR-001**: Each theme MUST have a working set of at most 8 effects, algorithmically
  derived from the theme's existing layer structure (e.g., bottom-layer effect gets
  highest weight, upper layers get decreasing weights). The working set is used for
  90%+ of placements when that theme is active. Effects outside the working set may
  still appear but only as rare accents.
- **FR-002**: The working set MUST include frequency weights that produce a steep
  distribution curve, with the top effect receiving the highest weight and remaining
  effects receiving progressively lower weights.
- **FR-003**: The rotation engine MUST allow the same effect+palette to repeat
  consecutively within a section without penalty on non-beat tiers. Intra-section
  reuse on the same model should be the default behavior, not a penalized exception.
  Beat tier (Tier 4) retains its existing chase distribution pattern unchanged.
- **FR-004**: Cross-section repetition of the same effect on the same model MUST be
  allowed when sections share the same theme. Cross-section penalties should only
  apply to prevent identical effect assignments across non-adjacent sections of the
  same label, and only at reduced strength.
- **FR-005**: Section boundaries MUST remain the primary point where effect vocabulary
  changes. Within a section, effect+palette consistency is the goal. At section
  transitions, the effect selection should shift noticeably.
- **FR-006**: The focused vocabulary behavior MUST be independently toggleable. When
  disabled, the generator uses the pre-existing full effect pool and rotation logic.
- **FR-007**: The repetition behavior MUST be independently toggleable. When disabled,
  the generator applies the pre-existing intra-section (0.3x) and cross-section (0.5x)
  reuse penalties.
- **FR-008**: When both behaviors are disabled, the generator MUST produce output
  identical to the pre-Phase-1 baseline, and all existing tests MUST pass without
  regression.
- **FR-009**: The prop/compound tier effect pool MUST also respect the focused
  vocabulary constraint rather than drawing from a separate hard-coded list of ~10
  effects.
- **FR-010**: The reference analyzer tool MUST be usable to verify Phase 1 outcomes
  by comparing effect distribution and repetition metrics of generated output against
  reference sequence baselines.

### Key Entities

- **WorkingSet**: A weighted list of 4-8 effects algorithmically derived from a theme's
  layer structure at generation time. Weights are computed from layer position (bottom
  layers = higher weight) and layer count. Defines which effects are placed and their
  relative frequency. The top-weighted effect is the theme's "signature" effect that
  dominates placements. No manual per-theme data entry required.
- **RepetitionPolicy**: Per-section rule governing whether and how much same-effect
  reuse is penalized. In Phase 1, within-section repetition is unrestricted
  (no penalty) and cross-section repetition is lightly penalized only across
  non-adjacent same-label sections.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Generated sequences have top-5 effects accounting for 80%+ of placements
  (reference range: 75-93%; current generator baseline: ~50%).
- **SC-002**: The top effect in any generated sequence accounts for at least 25% of
  total placements (reference range: 30-73%).
- **SC-003**: The top 2 effects together account for at least 50% of total placements
  (reference range: 52-93%).
- **SC-004**: Consecutive same effect+palette repetition on base-tier models reaches
  10+ per section (reference range: 15-63; current generator baseline: 1-3).
- **SC-005**: Within-section effect variety on any single model is at most 2 distinct
  effects (one primary, one optional accent), compared to the current 3-5.
- **SC-006**: Section transitions show a measurable change in effect vocabulary
  (different dominant effect or working set shift) for at least 70% of section
  boundaries where the theme changes.
- **SC-007**: Each Phase 1 behavior (focused vocabulary, repetition policy) can be
  independently enabled/disabled, verified by generating sequences with each toggle
  and confirming distinct metric changes.
- **SC-008**: No regression in the existing test suite when all Phase 1 behaviors
  are disabled.

## Assumptions

- Reference sequences from 5 community .xsq files (docs/reference-sequence-analysis.md)
  are representative of "good" sequencing practices. The structural patterns (vocabulary
  focus, steep distribution, sustained repetition) are consistent across all 5 analyzed
  sequences despite different artistic styles and song types.
- The existing theme definitions provide enough information to algorithmically derive
  a meaningful working set at generation time. Themes already define layers with effect
  variants -- the working set weights are computed from layer position and structure,
  requiring no manual weight data entry per theme.
- The existing analysis hierarchy (sections, energy, BPM) provides sufficient data
  to determine section boundaries for repetition policy. No new audio analysis is
  needed for Phase 1.
- The reference analyzer tool (analyze_reference_xsq.py) can be run on generated
  output to produce comparable metrics for validation.
- The current intra-section penalty (0.3x) and cross-section penalty (0.5x) in the
  rotation engine are the primary mechanisms causing excessive variety; removing or
  inverting these penalties will produce the desired repetition behavior.
- The hard-coded prop effect pool (~10 effects) in the effect placer is a secondary
  source of over-rotation that must also be addressed to achieve the target metrics.

## Relationship to Other Phases

This is **Phase 1** of the 5-phase Sequence Quality Refinement plan (spec 035).

| Phase | Feature | Spec |
|-------|---------|------|
| **Phase 1** | **Focused Effect Vocabulary + Embrace Repetition** | **036 (this spec)** |
| Phase 2 | Duration Scaling | 037 |
| Phase 3 | Palette Restraint | 038 |
| Phase 4 | Dynamic Model Activation | 039 |
| Phase 5 | MusicSparkles + Value Curves | 040 |

**Dependencies**: Phase 1 has no dependencies on other phases. It can be implemented,
tested, and validated independently.

**Dependents**: Phases 2-5 build on the structural foundation established by Phase 1.
In particular, duration scaling (Phase 2) and dynamic model activation (Phase 4)
benefit from having a focused, repetitive base to work with -- varying duration or
model count is more effective when the underlying effect vocabulary is already coherent.
However, all phases are designed to be independently toggleable and none strictly
require Phase 1 to function.
