# Research: Section Transitions & End-of-Song Fade Out

## R1: How should crossfades be applied to EffectPlacements?

**Decision**: Modify `_calculate_fades()` in `effect_placer.py` to return non-zero values based on a TransitionConfig. For the outgoing section's last effect placement on each group, set `fade_out_ms`. For the incoming section's first effect placement, set `fade_in_ms`. Apply this as a post-processing pass over the completed placements rather than during initial placement.

**Rationale**: Post-processing is cleaner than modifying the placement loop — the loop doesn't know about adjacent sections. After all sections are placed, we can iterate placement pairs at boundaries and set fade values. The XSQ writer already handles non-zero `E_TEXTCTRL_Fadein`/`E_TEXTCTRL_Fadeout` fields (xsq_writer.py lines 411-415).

**Alternatives considered**:
- **During placement**: Would require the placer to know about the next/previous section, adding coupling.
- **Value curves**: More powerful but the framework is disabled (Phase 1) and untested.
- **Overlay effects**: Guaranteed to work but adds layer complexity.

## R2: How should crossfade duration be derived from tempo?

**Decision**: Crossfade duration = one beat duration for "subtle" mode, one bar duration for "dramatic" mode. Beat duration is calculated as `60000 / BPM` (milliseconds). Bar duration is `beat_duration × beats_per_bar` (typically 4).

Mapping:
- **None**: 0ms (no fade)
- **Subtle**: 1 beat (~400ms at 150 BPM, ~750ms at 80 BPM)
- **Dramatic**: 1 bar (~1600ms at 150 BPM, ~3000ms at 80 BPM)

Clamped to section half-length to prevent fades longer than sections.

**Rationale**: Beat/bar alignment makes crossfades feel musical. The tempo naturally scales the duration — fast songs get quick transitions, slow songs get languid ones.

**Alternatives considered**:
- **Fixed milliseconds**: Doesn't adapt to tempo; 500ms feels fine at 120 BPM but wrong at 60 or 180.
- **Percentage of section**: Unpredictable absolute duration; a 2% fade on a 60-second section is 1.2s, but on a 5-second section is 100ms.

## R3: How should the end-of-song fade-out work?

**Decision**: Detect the final section. If labeled "outro", apply a full-length brightness fade from the section's starting energy to zero. If not an outro (abrupt ending), apply a 3-second fade on the final section's last placements. For progressive tier fading on long outros (>8s), stagger the fade start times: hero tier starts fading at 0%, compound at 20%, prop at 40%, fidelity at 60%, base at 80% through the outro.

Implementation: set `fade_out_ms` on the final placement of each group, with the duration dependent on the group's tier and the outro length.

**Rationale**: The simplest approach that still creates visual depth. Staggered tier fading makes the fade-out feel layered — the audience sees the spotlight dim first, then the props, then the wash, like a theater dimming.

**Alternatives considered**:
- **Linear fade on all tiers simultaneously**: Works but feels flat — everything dims together.
- **Kill tiers sequentially**: Too abrupt — one tier goes dark while others are still bright.
- **Value curve on transparency**: More precise but adds framework dependency.

## R4: How should same-effect continuations be detected (FR-003)?

**Decision**: After placing effects for all sections, compare adjacent sections' placements per group. If the same group has the same `effect_name` with the same `xlights_id` and compatible parameters in both sections, skip the crossfade for that group. "Compatible" means the parameters differ by less than 10% (accounting for variation_seed tweaks).

**Rationale**: Crossfading between identical effects looks like a pointless brightness dip. Detecting continuations avoids this. The 10% tolerance handles the `_apply_variation()` tweaks that make repeated sections slightly different.

**Alternatives considered**:
- **Exact parameter match only**: Too strict — variation_seed creates small differences that shouldn't trigger crossfade.
- **Effect name match only**: Too loose — different parameter sets on the same effect (e.g., Bars with 3 bars vs 7 bars) should crossfade.

## R5: How should boundary snap precision be improved?

**Decision**: The existing `_snap_sections_to_bars()` in `orchestrator.py` already snaps to bar lines with an adaptive 400-1200ms window. Improvements needed:
1. **Merge prevention**: After snapping, check for zero-length or very short (<2 seconds) sections. Absorb them into their longer neighbor.
2. **Boundary crossover prevention**: If snapping would move boundary A past boundary B, reduce the snap window for that boundary.

These are surgical fixes to the existing function, not a rewrite.

**Rationale**: The snap logic is sound; only the edge cases (merge and crossover) need fixing. These are the "cleanup" part of the feature.

**Alternatives considered**:
- **Rewrite from scratch in generator**: Would duplicate the analyzer logic.
- **Move snap to generator**: Wrong pipeline stage — snapping should happen during analysis, before theme selection.

## R6: Where does the transition pass fit in the pipeline?

**Decision**: Add a `apply_transitions()` post-processing step in `build_plan()` after all sections have their `group_effects` populated. This function receives the full list of SectionAssignments and modifies the `fade_in_ms`/`fade_out_ms` fields on boundary placements. It also handles the end-of-song fade-out.

Pipeline order:
1. Derive section energies
2. Snap boundaries (existing, enhanced)
3. Select themes
4. Build rotation plan (feature 030)
5. Place effects per section
6. **NEW: Apply transitions (crossfades + fade-out)**
7. Assemble SequencePlan

**Rationale**: Transitions must be applied after all placements exist, since they need to compare adjacent sections. This is the natural post-processing point.
