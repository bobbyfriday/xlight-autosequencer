# Feature Specification: Section Transitions & End-of-Song Fade Out

**Feature Branch**: `032-section-transitions-fadeout`
**Created**: 2026-04-02
**Status**: Draft
**Input**: User description: "End-of-Song Fade Out — smooth visual wind-down instead of abrupt cut. Section Transition Boundary Cleanup — crossfades and snap precision at boundaries. Those are both related and I'd like to think about ideas of how we can accomplish both of them together."

## Clarifications

### Session 2026-04-02

- Q: How should crossfades and fade-outs be rendered in xLights — fade fields, value curves, or overlay effects? → A: Use fade_in_ms/fade_out_ms fields on EffectPlacement directly (simplest approach). Fall back to an alternative if xLights mangles the values on save.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Smooth Section Transitions with Crossfade (Priority: P1)

When the sequence generator places effects for adjacent sections, the transition between them should feel smooth rather than jarring. Currently effects cut abruptly at section boundaries — the last frame of one section and the first frame of the next have completely different effects, palettes, and parameters. The system should apply brief crossfade behavior at section boundaries so that outgoing effects fade down and incoming effects fade up, creating a professional visual blend.

**Why this priority**: Section transitions are the most visible quality issue in generated sequences. Every song has 10-30 section boundaries, and each one currently creates a harsh visual cut. Fixing this has the highest impact-per-boundary improvement across the entire sequence.

**Independent Test**: Generate a sequence for a song with a verse-to-chorus transition. Verify that the last portion of the verse section's effects includes a fade-out, and the first portion of the chorus section's effects includes a fade-in. Import into xLights and visually confirm the transition is smooth.

**Acceptance Scenarios**:

1. **Given** two adjacent sections with different themes, **When** effects are placed, **Then** the outgoing section's effects on each group have a fade-out applied to their final portion, and the incoming section's effects have a fade-in on their initial portion.
2. **Given** two adjacent sections with the same theme, **When** effects are placed, **Then** the transition uses a shorter crossfade (since the visual change is smaller) or no crossfade if the effects are identical.
3. **Given** a section boundary that falls on a bar line, **When** the crossfade is applied, **Then** the fade duration aligns with the bar/beat grid rather than using an arbitrary millisecond value.
4. **Given** a fast song (>150 BPM), **When** crossfades are applied, **Then** the fade duration is shorter than for a slow song (<100 BPM) to match the musical pacing.

---

### User Story 2 — End-of-Song Fade Out (Priority: P1)

Songs that end with a gradual energy decrease (outro sections, final drops) should have a smooth visual fade-out rather than effects cutting to black on the last frame. The system detects the song's ending character and applies an appropriate visual wind-down — dimming brightness, progressively dropping upper tiers, or both.

**Why this priority**: The end of the show is the most memorable moment. An abrupt cut to black after 4 minutes of carefully synced visuals feels broken. A smooth fade-out gives the sequence a polished, intentional ending.

**Independent Test**: Generate a sequence for a song with a clearly labeled "outro" section. Verify that effects progressively dim or deactivate during the outro, reaching near-zero brightness by the final frame. Import into xLights and confirm the visual wind-down.

**Acceptance Scenarios**:

1. **Given** a song with an "outro" section at the end, **When** effects are placed for the outro, **Then** all tiers have a brightness ramp from full brightness at the start of the outro to zero at the end.
2. **Given** a song that ends abruptly (no outro, last section is a chorus at high energy), **When** effects are placed, **Then** a brief fade-out is applied to the final 2-4 seconds of the last section, regardless of energy.
3. **Given** a song with a long outro (>15 seconds), **When** the fade-out is applied, **Then** upper tiers (hero, compound) fade out first, followed by mid tiers (prop, fidelity), leaving the base tier (whole-house wash) as the last to fade — creating a progressive visual wind-down.
4. **Given** a song with an outro whose energy decreases gradually, **When** the fade-out is applied, **Then** the brightness follows the energy curve (not a linear ramp) so the visual dimming matches the musical dynamics.

---

### User Story 3 — Section Boundary Snap Precision (Priority: P2)

Section boundaries should align precisely with musical structure — bar lines, beat positions, or phrase boundaries. Currently some boundaries derived from audio analysis fall between beats, creating effects that start or end at musically awkward moments. The system should snap section boundaries to the nearest appropriate musical position.

**Why this priority**: Misaligned boundaries cause effects to start mid-beat or end between bars, which looks like a timing error even when the effect selection is good. Fixing snap precision improves perceived quality without changing effect choices.

**Independent Test**: Generate a sequence and compare section boundary timestamps to the nearest bar/beat positions. Verify that all boundaries fall within one beat of a bar line.

**Acceptance Scenarios**:

1. **Given** a section boundary at an arbitrary timestamp, **When** boundary snapping is applied, **Then** the boundary moves to the nearest bar line within a configurable snap window.
2. **Given** a section boundary that is already on a bar line, **When** boundary snapping is applied, **Then** the boundary does not move.
3. **Given** two boundaries that would merge after snapping (both snap to the same bar), **When** snapping is applied, **Then** the shorter section is absorbed into its neighbor rather than creating a zero-length section.
4. **Given** a snap window larger than the gap between two boundaries, **When** snapping is applied, **Then** the snap window is reduced to prevent boundary crossover.

---

### User Story 4 — Configurable Transition Behavior (Priority: P3)

Users can control transition and fade-out behavior via generation options — choosing between no transitions (legacy behavior), subtle crossfades, or dramatic transitions. Theme authors can also specify per-theme transition preferences.

**Why this priority**: Different shows and songs benefit from different transition styles. Christmas shows may want gentle crossfades; Halloween shows may want hard cuts. This gives users and theme authors creative control.

**Independent Test**: Generate the same song with three different transition settings (none, subtle, dramatic) and verify the output differs in fade durations.

**Acceptance Scenarios**:

1. **Given** the transition mode is set to "none", **When** effects are placed, **Then** behavior is identical to pre-feature output (full backward compatibility).
2. **Given** the transition mode is set to "subtle", **When** crossfades are applied, **Then** fade durations are 1-2 beats long.
3. **Given** the transition mode is set to "dramatic", **When** crossfades are applied, **Then** fade durations are 1-2 bars long.
4. **Given** a theme specifies its own transition preference, **When** that theme is active, **Then** the theme preference overrides the global setting.

---

### Edge Cases

- What happens when a section is shorter than the crossfade duration? The crossfade is clamped to half the section length, ensuring at least half the section plays at full brightness.
- What happens when the song has only one section? No crossfade is applied (no transition), but end-of-song fade-out still applies.
- What happens when section boundaries are already perfectly aligned to bars? No snap adjustment needed — boundaries are left in place.
- What happens with a song that has no detected beats or bars? Crossfades use a fixed duration (500ms default) instead of beat-aligned fades. Snap precision is skipped.
- What happens when the "outro" section is only 2 seconds long? The fade-out compresses to fit the available time but still completes from full to zero brightness.
- What happens when two adjacent sections use the same effect on the same group? No crossfade is needed for that group — the effect continues seamlessly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST apply crossfade behavior at section boundaries, with outgoing effects fading out and incoming effects fading in over a brief overlap period.
- **FR-002**: Crossfade duration MUST be tempo-aware — derived from the song's beat/bar grid rather than a fixed millisecond value. Faster songs get shorter crossfades.
- **FR-003**: When two adjacent sections use the same effect on the same group, the system MUST skip the crossfade for that group and let the effect continue uninterrupted.
- **FR-004**: The system MUST detect end-of-song conditions (outro label, final section, decreasing energy) and apply a brightness fade-out over the final section or final seconds.
- **FR-005**: The end-of-song fade-out MUST be progressive — upper tiers fade first, lower tiers last — when the outro is long enough (>8 seconds) to support staggered fading.
- **FR-006**: The end-of-song fade-out brightness curve MUST follow the section's energy curve when available, rather than a simple linear ramp.
- **FR-007**: Songs that end abruptly (no outro, high-energy final section) MUST still receive a brief fade-out over the final 2-4 seconds.
- **FR-008**: Section boundaries MUST be snapped to the nearest bar line within a configurable window (default: half the median bar interval).
- **FR-009**: Boundary snapping MUST NOT create zero-length sections — if two boundaries would merge, the shorter section is absorbed.
- **FR-010**: The system MUST support three transition modes: "none" (legacy), "subtle" (1-2 beats), and "dramatic" (1-2 bars), configurable per generation.
- **FR-011**: Themes MUST be able to specify a preferred transition mode that overrides the global default.
- **FR-012**: The "none" transition mode MUST produce output identical to pre-feature behavior for full backward compatibility.

### Key Entities

- **TransitionConfig**: Settings controlling crossfade and fade-out behavior — mode (none/subtle/dramatic), snap window, fade-out strategy.
- **CrossfadeRegion**: A time region spanning a section boundary where outgoing effects fade out and incoming effects fade in. Duration is derived from tempo.
- **FadeOutPlan**: The brightness ramp applied during the final section — maps time to brightness level per tier, following the energy curve or a linear ramp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of section boundaries in generated sequences fall within one beat of the nearest bar line after snapping.
- **SC-002**: When crossfades are enabled, every section transition has a non-zero crossfade duration (except same-effect continuations).
- **SC-003**: End-of-song fade-out reaches zero brightness within the final 500ms of the song for all tiers.
- **SC-004**: In "none" mode, generated output is byte-identical to pre-feature output (backward compatibility).
- **SC-005**: Crossfade durations scale with tempo — songs at 150+ BPM have crossfades under 1 second; songs under 80 BPM have crossfades up to 2 seconds.
- **SC-006**: For songs with a progressive outro, the visual fade-out correlates with the energy curve — brightness at any point during the outro is within 20% of the normalized energy level.

## Assumptions

- Crossfades and fade-outs will be implemented using the existing `fade_in_ms` and `fade_out_ms` fields on EffectPlacement, which are plumbed through to the XSQ writer (`E_TEXTCTRL_Fadein`/`E_TEXTCTRL_Fadeout`) but currently always zero. A previous comment suggested xLights may recalculate these on save — if that proves true during testing, the fallback is value curves or overlay effects.
- The hierarchy provides reliable bar and beat timing for snap precision. Songs without detected bars fall back to fixed-duration crossfades.
- Section labels ("outro", "verse", "chorus", etc.) are reliably classified by the section classifier and can be trusted for end-of-song detection.
- The value curves framework (`src/generator/value_curves.py`) exists but is currently disabled. This feature may enable it for brightness/transparency curves or implement an alternative approach.
- The default transition mode for new generations is "subtle" — existing users who want the old behavior can set "none".

## Scope Boundaries

### In Scope

- Crossfade behavior at all section boundaries (fade-out / fade-in)
- End-of-song fade-out (progressive tier dimming)
- Section boundary snap precision to bar lines
- Tempo-aware crossfade durations
- Three transition modes (none/subtle/dramatic)
- Theme-level transition preference override
- Backward compatibility via "none" mode

### Out of Scope

- Value curves for mid-section parameter animation (brightness/speed ramps within a section — that's a separate feature)
- Multi-layer blend mode changes at transitions (that's the 3D Effects feature)
- Manual per-section transition override UI (future theme editor enhancement)
- Audio-reactive real-time transitions (this is pre-computed, not live)

## Dependencies

- Feature 020 (Sequence Generator) — effect_placer, plan builder, EffectPlacement model
- Feature 016 (Hierarchy Orchestrator) — provides bar/beat timing for snap precision
- Feature 019 (Effect Themes) — theme model for transition preference field
- Feature 030 (Intelligent Effect Rotation) — RotationPlan integration for understanding which effects are on which groups at boundaries
