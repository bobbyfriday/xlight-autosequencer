# Feature Specification: Sequence Generator

**Feature Branch**: `020-sequence-generator`
**Created**: 2026-03-26
**Status**: Draft
**Dependencies**: Feature 016 (Hierarchy Orchestrator — analysis pipeline), Feature 017 (Layout Grouping — power groups), Feature 018 (Effect Library — effect catalog), Feature 019 (Effect Themes — theme catalog)

## Context

This is the culmination feature that ties the entire xLight AutoSequencer pipeline together. Today the system can analyze music into timing tracks, classify energy tiers, separate stems, group layout props into power tiers, and catalog effects and themes — but it cannot produce a finished xLights sequence. Users must manually import timing marks and hand-place effects.

This feature closes the gap: given an MP3 file and an xLights layout, it generates a complete `.xsq` sequence file with effects applied to models and groups, synchronized to the music's timing tracks, themed by song section, and ready to open in xLights for final tweaking.

Preview/rendering of the light show is left to xLights — the user opens the generated `.xsq` to see the visual result.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - End-to-End Sequence Generation (Priority: P1)

A user provides an MP3 file and their xLights layout file. The system runs analysis (or uses a cached analysis), determines the song's characteristics, selects appropriate themes, maps effects to layout groups aligned with timing tracks, and writes a `.xsq` sequence file that opens in xLights with effects already placed on the timeline.

**Why this priority**: This is the core value proposition — without sequence output, nothing else matters.

**Independent Test**: Run the generator on a test MP3 with a sample layout. Open the resulting `.xsq` file in xLights (or validate its XML structure). Confirm effects are placed on models, synchronized to timing marks, and span the full song duration.

**Acceptance Scenarios**:

1. **Given** an MP3 file and an xLights layout XML, **When** the generator runs, **Then** it produces a valid `.xsq` file that xLights can open without errors.
2. **Given** a generated `.xsq` file, **When** opened in xLights, **Then** effects are visible on the timeline placed on model groups from the layout.
3. **Given** a generated sequence, **When** the timeline is inspected, **Then** effects align with musical timing — beat-synced effects land on beats, section transitions coincide with song structure boundaries.
4. **Given** a song with distinct sections (verse, chorus, bridge), **When** the sequence is generated, **Then** different visual themes are applied to different sections, creating contrast and variety.
5. **Given** a layout with multiple power group tiers, **When** the sequence is generated, **Then** different groups receive different effects — not every prop does the same thing at the same time.
6. **Given** any generated sequence, **When** inspected, **Then** effects have appropriate color palettes from the selected theme and parameter values within the effect library's defined ranges.

---

### User Story 2 - Wizard-Driven Song Setup (Priority: P1)

A CLI wizard guides the user through sequence generation. It accepts the MP3 file path, optionally auto-detects song metadata (title, genre, occasion), and lets the user confirm or override these choices before generation begins. The wizard reuses the existing interactive CLI patterns from feature 014.

**Why this priority**: Users need control over genre/occasion selection since it drives theme choices. Auto-detection is best-effort — the user always knows their song better.

**Independent Test**: Run the wizard, provide an MP3. Confirm it presents detected metadata, allows overrides, and proceeds to generation.

**Acceptance Scenarios**:

1. **Given** the user runs the wizard with an MP3 path, **When** the wizard starts, **Then** it attempts to read song metadata (ID3 tags: title, artist, genre) and presents findings for confirmation.
2. **Given** the wizard presents detected metadata, **When** the user overrides the genre or occasion, **Then** the override is used for theme selection.
3. **Given** no metadata can be detected, **When** the wizard runs, **Then** it prompts the user to provide genre and occasion (with sensible defaults like "general" occasion and "pop" genre).
4. **Given** the user provides an xLights layout file path, **When** the wizard runs, **Then** it reads the layout and reports how many models and power groups were found.
5. **Given** an existing cached analysis for the same MP3, **When** the wizard runs, **Then** it reuses the cache rather than re-analyzing (with an option to force re-analysis).

---

### User Story 3 - Theme and Effect Assignment Preview (Priority: P2)

Before generating the final sequence, the system shows the user a summary of what will be generated: which themes are assigned to which song sections, which effect types will appear on which groups, and the overall color palette. The user can accept, modify assignments, or regenerate with different options.

**Why this priority**: Users need to see and approve the plan before committing to a full generation pass. This is the "I'd like this / I don't want this" control loop.

**Independent Test**: Run the generator up to the preview step. Confirm it displays section-to-theme mappings and group-to-effect assignments. Modify a theme choice and confirm the change is reflected in the regenerated output.

**Acceptance Scenarios**:

1. **Given** analysis and theme selection are complete, **When** the preview is shown, **Then** the user sees a table of song sections with their assigned themes and color palettes.
2. **Given** the preview, **When** the user sees the effect assignments per group tier, **Then** they can understand which props will do what during each section.
3. **Given** the preview, **When** the user requests a different theme for a specific section, **Then** the system re-plans that section with the new theme.
4. **Given** the preview, **When** the user accepts the plan, **Then** generation proceeds and writes the output files.
5. **Given** the preview, **When** the user requests a full regeneration with a different overall mood, **Then** all section assignments are recalculated.

---

### User Story 4 - XSQ Output with FSEQ Guidance (Priority: P2)

The generator produces a `.xsq` (xLights native sequence XML) file as its primary output. For users who need `.fseq` for playback, the system provides clear instructions on how to render it from the `.xsq` using xLights' built-in export.

**Why this priority**: The `.xsq` is the must-have deliverable. FSEQ rendering requires a full pixel-level engine that xLights already provides — no need to duplicate it.

**Independent Test**: Generate a sequence and confirm the `.xsq` is produced and valid. Confirm the output includes guidance for FSEQ rendering in xLights.

**Acceptance Scenarios**:

1. **Given** a completed generation, **When** output is written, **Then** a `.xsq` file is produced in the output directory.
2. **Given** the `.xsq` file, **When** opened in xLights, **Then** it loads correctly with all effects, models, and timing intact.
3. **Given** the generation output, **When** the user reads the completion message, **Then** it includes instructions for rendering to `.fseq` in xLights.

---

### User Story 5 - Post-Generation Refinement (Priority: P3)

After a sequence is generated, the user can re-run the generator on specific song sections to try different themes or effects without regenerating the entire sequence. This iterative refinement lets the user dial in the look section by section.

**Why this priority**: Full regeneration works but is slow for fine-tuning. Section-level iteration is the efficient workflow for "make the chorus pop more" type adjustments.

**Independent Test**: Generate a full sequence, then re-run targeting only the chorus sections with a different theme. Confirm only those sections changed in the output.

**Acceptance Scenarios**:

1. **Given** an existing generated `.xsq`, **When** the user requests regeneration of a specific section (e.g., "chorus"), **Then** only effects in that section's time range are replaced.
2. **Given** section-level regeneration, **When** the updated `.xsq` is opened in xLights, **Then** unmodified sections remain identical to the original.
3. **Given** section-level regeneration with a new theme, **When** the section is inspected, **Then** it uses the new theme's effects and colors while maintaining timing alignment.

---

### Edge Cases

- What happens when the layout has no power groups (feature 017 not run)? The generator uses individual models directly, treating them as a flat list with no tiered grouping.
- What happens when analysis produces no usable timing tracks? The generator falls back to evenly-spaced timing marks at the detected BPM (or a default 120 BPM).
- What happens when the selected theme references effects not supported by the user's xLights version? Effects are written using standard xLights effect names. Unsupported effects will show as "unknown" in older xLights versions — this is acceptable since xLights handles it gracefully.
- What happens when the song has no detected sections (e.g., ambient music with no clear structure)? The generator treats the entire song as one section and applies a single theme with effect cycling for variety.
- What happens when the layout file path is invalid or the XML is malformed? The wizard reports the error and asks the user to provide a valid layout file.
- What happens with very short songs (under 30 seconds)? The generator uses fewer theme transitions — possibly a single theme for the entire song.
- What happens with very long songs (over 10 minutes)? The generator handles them normally; section-based theme assignment scales with song length.
- What happens with songs that have tempo changes? The generator places effects on actual beat/bar timing marks from analysis, which already reflect the real audio timing. Tempo changes don't affect placement accuracy — the single BPM value is only used for fallback spacing when no timing tracks exist.

## Requirements *(mandatory)*

### Functional Requirements

#### Analysis Integration

- **FR-001**: The system MUST accept an MP3 file and run the full analysis pipeline (or use cached results) to produce timing tracks, hierarchy data, song structure, and energy tiers. When multiple timing tracks exist for the same category (e.g., multiple beat trackers), the system MUST use the top-scoring track per category as determined by the quality scorer (feature 011).
- **FR-002**: The system MUST read an xLights layout XML file to discover models, their pixel counts, and any existing power groups.
- **FR-003**: The system MUST detect song metadata from ID3 tags (title, artist, genre) on a best-effort basis. If detection takes more than 2 seconds, it MUST skip and prompt the user instead.

#### Theme Selection Engine

- **FR-004**: The system MUST select themes for each song section based on: the section's derived energy level, the song's genre, and the song's occasion tag (christmas, halloween, general). Energy level MUST be derived by averaging the full-mix L5 energy curve within each section's time range, boosted by any L0 energy impacts falling within that range. The resulting 0-100 score determines the mood tier for theme selection.
- **FR-005**: The system MUST ensure visual variety — adjacent song sections SHOULD NOT use the same theme unless the song has very few sections. When the same section type repeats (e.g., Chorus 1, 2, 3), the system MUST use the same theme and effects but introduce small parameter variations (speed, color shift, intensity) across repetitions to avoid monotony while maintaining visual coherence.
- **FR-006**: The system MUST support filtering themes by occasion so that Christmas songs get Christmas-themed effects and Halloween songs get Halloween-themed effects.
- **FR-007**: The system MUST map song energy tiers to theme moods: low energy sections to Ethereal themes, medium energy to Structural or Dark, high energy to Aggressive.

#### Effect Mapping

- **FR-008**: The system MUST map theme effect layers onto layout power groups top-down: foundation/base layers go to base and geo groups (tiers 1-2), mid layers go to type and beat groups (tiers 3-4), and accent/top layers go to hero and compound groups (tiers 7-8). This ensures base props carry the foundation effect while hero props get the flashiest layer.
- **FR-009**: The system MUST align effect placement with timing tracks by consulting each effect's `analysis_mapping` field from the effect library (018) to determine the appropriate timing source. For example, strobes fire on onset marks, chases cycle on beat marks, and washes span section boundaries. At section boundaries, effects MUST clean-cut — the outgoing section's effects end and the incoming section's effects begin at the exact boundary timestamp with no overlap or gap.
- **FR-010**: The system MUST apply the theme's color palette to all effects in that section, using the effect library's color parameter names.
- **FR-011**: The system MUST set effect parameters within the ranges defined in the effect library (018). Parameters outside valid ranges MUST be clamped.
- **FR-011a**: The system MUST vary effect density based on section energy level — high-energy sections use most available timing marks, while low-energy sections intentionally skip marks to create visual breathing room. This prevents wall-to-wall effects from overwhelming the viewer.
- **FR-011b**: The system MUST use the effect library's `duration_type` field to determine effect instance length: "section" effects span the full section as a single instance, "bar" effects repeat as individual instances per bar, "beat" effects repeat per beat mark (subject to energy-driven density), and "trigger" effects fire once per mapped analysis event (e.g., onset, impact).
- **FR-011c**: The system MUST apply duration-based fade in/out to effects: "section" and "bar" duration effects MUST include auto-scaled fades (200-500ms, proportional to instance length) for smooth visual transitions. "beat" and "trigger" duration effects MUST use zero fade for snappy on/off response.
- **FR-011d**: The system MUST use the effect library's `AnalysisMapping` definitions to modulate effect parameters via value curves where the target parameter has `supports_value_curve=true`. For each mapping, the system MUST: extract the relevant analysis data (e.g., L5 energy curve), apply the specified `curve_shape` (linear, logarithmic, exponential, step), map values from `input_min`/`input_max` to `output_min`/`output_max`, and write the result as a value curve in the `.xsq` file.
#### Sequence Output

- **FR-012**: The system MUST produce a valid xLights `.xsq` XML file containing: sequence metadata (media file, duration, timing at 25ms / 40fps frame interval), model-to-effect mappings, effect parameters, and color values.
- **FR-013**: The system MUST NOT generate `.fseq` files directly. Instead, it MUST document in its output how the user can render the `.xsq` to `.fseq` using xLights' built-in render and export function.
- **FR-014**: The generated `.xsq` MUST reference the original MP3 as its media file so xLights plays the audio alongside the effects.
- **FR-015**: The system MUST write output files to a configurable directory, defaulting to the same directory as the input MP3.

#### Wizard and User Interaction

- **FR-016**: The system MUST provide a CLI wizard (using the interactive patterns from feature 014) that walks the user through: MP3 selection, layout file selection, metadata confirmation/override, and generation options.
- **FR-017**: The system MUST show a generation plan preview (section-to-theme mapping, group-to-effect summary) before writing output files.
- **FR-018**: The system MUST allow the user to override theme assignments for any section before generation.
- **FR-019**: The system MUST support section-level regeneration — re-running the generator on a subset of sections while preserving others.

### Key Entities

- **SequencePlan**: The complete mapping of song sections to themes, and themes to layout groups — the "blueprint" for what effects go where and when.
- **SectionAssignment**: One song section's theme choice, including the time range, selected theme, and effect-to-group mappings.
- **EffectPlacement**: A single effect instance placed on a specific model/group at a specific time range with resolved parameters and colors.
- **XsqWriter**: Produces the output `.xsq` file from a SequencePlan.
- **GenerationWizard**: The interactive CLI flow that collects inputs, presents the plan, and drives generation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from MP3 file to a working xLights sequence in under 5 minutes (excluding analysis time), including wizard interaction and generation.
- **SC-002**: Generated sequences open in xLights without errors or warnings about invalid effects.
- **SC-003**: At least 80% of effects in a generated sequence are aligned to musical timing events (beats, onsets, section boundaries) rather than arbitrary time positions.
- **SC-004**: Adjacent song sections use different visual themes at least 80% of the time, creating visible contrast when the sequence plays.
- **SC-005**: The wizard correctly reads ID3 genre/title metadata from MP3 files that contain it.
- **SC-006**: Section-level regeneration changes only the targeted sections — unaffected sections remain semantically identical (same effects, same times, same parameters) in the output.
- **SC-007**: A `.xsq` file is produced for every generation run, with FSEQ rendering guidance included in the output.

## Clarifications

### Session 2026-03-26

- Q: How do theme effect layers map to layout power group tiers? → A: Theme layers map top-down to group tiers — base/geo groups get foundation layers, hero groups get accent/top layers, following the 8-tier hierarchy.
- Q: Which timing track drives which effects? → A: The effect library's existing `analysis_mapping` field determines the timing track for each effect (e.g., strobes use "onsets", chases use "beats").
- Q: What frame interval / timing resolution for the generated sequence? → A: 25ms (40fps) for maximum precision.
- Q: How to handle repeated section types (e.g., Chorus 1, 2, 3)? → A: Same effects with small variations — keep the core look consistent but introduce minor parameter tweaks (speed, color shift, intensity) to avoid monotony.
- Q: Should we build FSEQ rendering or defer to xLights? → A: Defer — generate `.xsq` only. Document how the user renders to `.fseq` in xLights.

### Session 2026-03-26 (round 2)

- Q: How should section transitions work visually? → A: Clean cut — effects end and begin exactly at section boundaries. No crossfade or gap.
- Q: Should every timing mark trigger an effect or leave gaps? → A: Energy-driven density — high-energy sections use most marks, low-energy sections leave gaps for breathing room.
- Q: Which timing track to use when multiple exist per category? → A: Use the top-scoring track per category as determined by the quality scorer (feature 011).

### Session 2026-03-26 (round 3 — mechanics deep dive)

- Q: How does effect `duration_type` translate to timeline placement? → A: Repeating instances — "beat" effects repeat every active beat mark, "bar" effects repeat every bar, "section" effects span the whole section. "trigger" effects fire once on their mapped event.
- Q: How to derive energy level per section (sections lack energy tiers)? → A: Weighted average — average the full-mix energy curve within the section's time range, boosted by L0 energy impacts landing in that section. Impacts raise the score to better capture dynamic sections with builds or dramatic hits.
- Q: How should fade in/out work for effects? → A: Duration-based auto fades — section and bar effects get auto-scaled fades (200-500ms) for smooth transitions, beat and trigger effects get zero fade for snappy response.
- Q: Should the generator modulate effect parameters via analysis value curves? → A: Yes — use analysis mappings to drive parameters on effects that support value curves (e.g., energy → speed, spectral flux → brightness). This is how the sequence "goes with the music."
- Q: How to handle tempo changes? → A: Known limitation — assume constant tempo. Beat/bar timing marks already reflect actual audio timing, so effect placement on marks is correct regardless. Single BPM is only used for fallback spacing when no timing tracks exist.

## Assumptions

- Feature 019 (Effect Themes) is complete and the theme catalog is loadable.
- Feature 018 (Effect Library) is complete and the effect catalog is loadable.
- Feature 017 (Layout Grouping) power groups are the preferred way to distribute effects, but the generator works without them (flat model list fallback).
- Feature 016 (Hierarchy Orchestrator) provides song structure, timing tracks, and energy curves. Energy per section is derived at generation time (not provided directly by 016).
- The `.xsq` XML format follows xLights' documented structure. The generator targets xLights 2024+ format compatibility.
- FSEQ generation is deferred to xLights. The system outputs `.xsq` only and documents how to render to `.fseq` within xLights.
- Preview/rendering of the actual light show is left to xLights itself. This feature does not attempt to simulate or render the visual output — the user opens the `.xsq` in xLights to see the result.
- "Looks good" is defined by: variety across sections, consistency within sections, alignment with musical energy, and appropriate color palettes for the occasion. These are encoded as heuristic rules, not subjective judgment.
- Auto-detection of whether a song is Christmas/Halloween/etc. is best-effort via ID3 tags and title keywords. The user can always override.
- The wizard interaction model follows the patterns established in feature 014 (CLI Wizard Pipeline).
- Tempo is assumed constant (single `estimated_bpm` from analysis). Beat and bar timing marks already reflect actual audio timing regardless of tempo changes, so effect placement on marks is correct. The single BPM value is only used as a fallback for generating evenly-spaced marks when no timing tracks exist.
- Song sections do not carry energy tiers directly. Energy per section is derived at generation time by averaging the full-mix L5 energy curve within each section's time range, boosted by L0 energy impacts.
