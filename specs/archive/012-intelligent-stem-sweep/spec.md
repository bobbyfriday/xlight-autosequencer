# Feature Specification: Intelligent Stem Analysis and Automated Light Sequencing Pipeline

**Feature Branch**: `012-intelligent-stem-sweep`
**Created**: 2026-03-23
**Status**: Draft
**Input**: Full pipeline from stem inspection through xLights value curve and timing track export.

## Overview

This feature delivers a complete automated pipeline that takes a separated-stem song and produces ready-to-import xLights timing tracks and value curves. The pipeline: inspects stem quality, lets the user confirm which stems to use, derives intelligent initial analysis parameters from the audio, runs interaction analysis across stems to understand how instruments relate to each other, conditions the resulting data for hardware compatibility, and exports the finished assets.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stem Quality Inspection (Priority: P1)

A user has separated a song into stems and wants to know which are worth analyzing before spending time on heavy computation. They run a single command that evaluates every stem and returns a KEEP, REVIEW, or SKIP verdict with a plain-language reason and the measurements behind it.

**Why this priority**: Filtering low-quality stems prevents wasted compute and avoids polluting the output with tracks derived from near-silent or sparse audio.

**Independent Test**: Run inspection on a song with known stems; verify a silent stem is SKIPped, an intermittent stem is REVIEWed, and a full-energy stem is KEEPed, each with a matching reason.

**Acceptance Scenarios**:

1. **Given** a song with stems separated, **When** the user runs stem inspection, **Then** each stem receives KEEP, REVIEW, or SKIP with a numerical justification and plain-language explanation.
2. **Given** a nearly-silent stem, **When** inspection runs, **Then** that stem is SKIPped with a reason referencing its low energy level.
3. **Given** a stem active less than 40% of the track, **When** inspection runs, **Then** it receives REVIEW with a reason noting sparse coverage.
4. **Given** a full-energy, consistently active stem, **When** inspection runs, **Then** it receives KEEP with a reason describing its rhythmic or tonal character.

---

### User Story 2 - Interactive Stem Selection (Priority: P2)

After viewing automatic verdicts, the user confirms or overrides each stem's selection through an interactive CLI prompt before any further analysis runs.

**Why this priority**: Automated verdicts are a starting point; users with domain knowledge should be able to override them without re-running inspection.

**Independent Test**: Override one SKIP to KEEP in interactive mode; confirm the final selection reflects the user's choice.

**Acceptance Scenarios**:

1. **Given** inspection results, **When** the user enters interactive review, **Then** each stem is presented with its verdict, metrics, and reason and the user is prompted to accept or change it.
2. **Given** a SKIP stem the user overrides to KEEP, **Then** that stem is included in all subsequent analysis.
3. **Given** the user accepts all suggestions, **Then** the system's automatic verdicts are used unchanged.
4. **Given** all stems end up SKIPped, **Then** the system warns the user and falls back to the full mix.

---

### User Story 3 - Intelligent Sweep Parameter Initialization (Priority: P2)

After stem selection, the system derives sensible starting parameter values for each analysis algorithm from the selected stems' audio properties, producing sweep ranges centered on measured estimates rather than generic defaults.

**Why this priority**: Manual sweep configuration requires audio engineering expertise. Deriving parameters from the audio itself saves time and produces better starting points.

**Independent Test**: Provide a song with a known BPM; verify the generated tempo sweep brackets that value (one below, the estimate, one above).

**Acceptance Scenarios**:

1. **Given** selected stems, **When** sweep initialization runs, **Then** each algorithm receives a config with values derived from measured properties (tempo, signal level, content type).
2. **Given** a song at approximately 120 BPM, **When** configs are generated, **Then** beat-tracking receives at least three tempo values bracketing 120.
3. **Given** a low-energy stem, **When** onset configs are generated, **Then** sensitivity is skewed higher to compensate.
4. **Given** a rhythmically active (high crest factor) stem, **When** configs are generated, **Then** that stem is preferred for beat and onset algorithms.
5. **Given** a tonal (low crest, high centroid) stem, **When** configs are generated, **Then** that stem is preferred for pitch and harmony algorithms.

---

### User Story 4 - Musical Interaction Analysis (Priority: P2)

The system analyzes how stems interact with each other across the full song — which stem is leading at any moment, how tightly the kick drum and bass are locked, and where one melodic voice hands off to another. These relationships produce higher-level "interaction features" used to drive the light sequence.

**Why this priority**: A light show that responds only to individual stems in isolation misses the musical logic of the song. Inter-stem relationships (the kick-bass lock, a vocal solo taking over, a guitar answering the vocal) are what make a sequence feel musically intelligent rather than mechanical.

**Independent Test**: Run interaction analysis on a song where the vocal stem is active during a known solo section; verify that the leader-election output assigns the vocal stem as dominant during that section.

**Acceptance Scenarios**:

1. **Given** multiple selected stems, **When** interaction analysis runs, **Then** a frame-by-frame leader track is produced showing which stem holds the highest energy at each point in time.
2. **Given** a section where drums are the loudest stem, **When** a vocal solo starts and the vocal energy exceeds drum energy, **Then** the leader track switches from drums to vocals at the correct time boundary.
3. **Given** a song where kick drum and bass guitar move in sync, **When** cross-correlation is computed, **Then** the output registers high tightness for those sections and the system marks them as candidates for "unison flash" events.
4. **Given** sections where kick and bass are rhythmically independent, **When** cross-correlation is computed, **Then** those sections are marked as candidates for independent per-prop movement.
5. **Given** drum onsets present throughout a section, **When** visual sidechaining is computed, **Then** the output contains a momentary dip in the vocal energy curve at each drum onset, creating negative space.
6. **Given** a melodic motif that ends on the vocal stem and immediately continues on the guitar stem, **When** call-and-response detection runs, **Then** a handoff event is emitted at the transition point.

---

### User Story 5 - Data Conditioning for Hardware Compatibility (Priority: P3)

Before any data is exported, the system processes all feature curves to ensure they are stable, smooth, and within the value range that xLights and pixel hardware can safely consume.

**Why this priority**: Raw audio feature data contains high-frequency variation that causes visible jitter, wasted DMX bandwidth, and potential strain on power supplies. Conditioning is a mandatory step before export.

**Independent Test**: Run conditioning on a raw feature curve with known high-frequency noise; verify the output has reduced peak-to-peak variation and all values fall in the 0–100 integer range.

**Acceptance Scenarios**:

1. **Given** raw feature data sampled at audio rate, **When** conditioning runs, **Then** the output is downsampled to match the target sequence frame rate (20 FPS / 50ms intervals by default).
2. **Given** a conditioned curve, **Then** all values are integers in the range 0–100.
3. **Given** a curve with high-frequency jitter, **When** smoothing is applied, **Then** rapid frame-to-frame variation is reduced without flattening the overall shape of the curve.
4. **Given** a feature value that is always near 0 or always near its maximum, **When** normalization runs, **Then** the output is scaled to use the full 0–100 range so the curve drives visible light changes.

---

### User Story 6 - xLights Export (Priority: P1)

The conditioned analysis data is exported as xLights-compatible files: timing track files for discrete events (beat hits, structural changes, onsets) and value curve files for continuous feature data (energy, brightness, spatial position).

**Why this priority**: Export is the delivery mechanism — without it, all upstream analysis produces no usable artifact.

**Independent Test**: Export a timing track and a value curve for a known song; import both into xLights and verify that beat markers appear at the correct positions and the value curve drives a brightness effect in sync with the audio.

**Acceptance Scenarios**:

1. **Given** conditioned onset/beat data, **When** exported as timing tracks, **Then** the output files can be imported into xLights and show markers at the correct timestamps.
2. **Given** a conditioned energy feature curve, **When** exported as a value curve, **Then** the resulting `.xvc` file is valid XML that xLights can apply to an effect property.
3. **Given** a feature derived from a specific stem (e.g., vocal pitch salience), **When** exported, **Then** the file is named to indicate the source stem and feature type so the user can identify it without opening it.
4. **Given** the interaction analysis outputs (leader track, sidechained curves, handoff events), **When** exported, **Then** leader-track changes appear as timing marks and sidechained curves appear as value curves.
5. **Given** an export run on a song, **Then** all output files are written to the song's `analysis/` directory.

---

### User Story 7 - Automated Full Pipeline (Priority: P3)

A user runs a single command that executes the entire workflow — inspection, optional interactive review, parameter initialization, sweep analysis, interaction analysis, conditioning, and export — producing finished xLights assets without manual intervention.

**Why this priority**: The end goal is full automation. Individual steps are independently valuable, but composing them into one command is what enables non-technical users to benefit from the system.

**Independent Test**: Run the full pipeline command on a song from scratch; confirm xLights-importable timing track and value curve files are present in the output directory when the command completes.

**Acceptance Scenarios**:

1. **Given** an MP3 with stems already separated, **When** the full pipeline command runs, **Then** all steps complete and xLights-ready files are present in the output directory.
2. **Given** the `--interactive` flag is passed, **Then** the pipeline pauses after stem inspection for user confirmation before proceeding.
3. **Given** no stems are available, **When** the full pipeline runs, **Then** the system analyzes the full mix and exports results using full-mix features only.
4. **Given** the pipeline completes, **Then** a summary shows which stems were used, what interactions were detected, and how many output files were produced.

---

### Edge Cases

- No separated stems available: fall back to full mix for all algorithms; warn the user.
- All stems receive SKIP: warn the user and offer to proceed with full mix only.
- BPM detection is unreliable (atonal or ambient track): widen the tempo sweep range and flag low confidence in the config rationale.
- A stem file exists but is unreadable or corrupt: skip that stem with a clear error; continue with remaining stems.
- Kick drum and bass are not both present (e.g., instrumental with no bass guitar): skip cross-correlation; emit a notice.
- No vocal stem detected (instrumental): skip pitch salience and call-and-response detection; continue with remaining steps.
- Feature curve is flat (constant value throughout): skip normalization expansion for that curve and note it in the export manifest.
- The "other" stem contains a high-energy mix of disparate instruments: the system applies its spectral classification heuristic (high variation + low transient sharpness → pad/synth) and routes it to spatial curves rather than timing tracks; if classification is ambiguous, route to both and let the user decide which to use.
- Target frame rate does not evenly divide the audio sample rate: round to nearest valid frame boundary; document any rounding in export metadata.

---

## Requirements *(mandatory)*

### Functional Requirements

**Stem Inspection**

- **FR-001**: The system MUST evaluate each available stem against a defined set of audio quality metrics and produce a KEEP, REVIEW, or SKIP verdict for each stem.
- **FR-002**: Each verdict MUST include a plain-language explanation referencing the specific measurements that led to it (at minimum: energy level, activity coverage, and content character).
- **FR-003**: The system MUST provide a non-interactive display mode showing all verdicts in a formatted summary without user input.
- **FR-004**: The system MUST provide an interactive CLI mode that presents each stem's verdict and allows the user to accept or override it.
- **FR-005**: The system MUST always include the full mix as a fallback, even when separated stems are available.

**Parameter Initialization**

- **FR-006**: The system MUST derive initial parameter values for each algorithm from the properties of selected stems, including at minimum: estimated tempo, average signal level, and content type (rhythmic vs. tonal).
- **FR-007**: For each tunable parameter, the system MUST generate a sweep range that includes values below, at, and above the derived estimate.
- **FR-008**: Algorithms MUST be matched to stems by content affinity (beat/onset algorithms prefer rhythmic stems; pitch/harmony algorithms prefer tonal stems).
- **FR-009**: Each generated sweep configuration MUST include a human-readable rationale for the chosen parameter ranges.
- **FR-010**: All generated sweep configuration files MUST be saved to the song's analysis directory for reuse and inspection.

**Musical Interaction Analysis**

- **FR-011**: The system MUST compute a frame-by-frame leader track indicating which stem holds the dominant energy at each point in time.
- **FR-012**: The leader track MUST be based on a combination of RMS energy and spectral flux across all selected stems.
- **FR-013**: A stem MUST maintain dominant energy for at least 250ms before it is declared the new leader; if the energy delta between the challenger and the current leader exceeds a large threshold (indicating a sudden solo or drop), the hold period MAY be bypassed. This prevents rapid flickering between stems of similar energy.
- **FR-014**: The system MUST compute a rhythmic tightness score between the kick drum and bass stems by comparing the timing of their energy peaks, not their raw waveforms, making the measurement resilient to stem separation artifacts.
- **FR-015**: High-tightness sections MUST be flagged as candidates for unison flash events; low-tightness sections MUST be flagged for independent prop movement.
- **FR-016**: The system MUST compute a sidechained vocal energy curve by applying momentary reductions to the vocal brightness value at drum onset positions, while simultaneously applying a brief increase to a secondary visual dimension (such as saturation or effect size) to create a "pumping" visual contrast rather than a simple dip.
- **FR-017**: The system MUST detect stem handoff events where a melodic motif ends on one stem and immediately continues on another, and emit a spatial transition marker at each handoff.
- **FR-018**: The system MUST classify the "other" stem by its spectral characteristics: if it exhibits high spectral variation but low transient sharpness, it MUST be routed to spatial value curves (slow pans, position sweeps) rather than timing tracks, reflecting its likely pad/synth content.

**Data Conditioning**

- **FR-019**: The system MUST downsample all feature data to a configurable target frame rate (default: 20 FPS / 50ms intervals).
- **FR-020**: The system MUST apply smoothing to all continuous feature curves using a method that preserves the sharpness of peaks (e.g., snare hits, drop onsets) while eliminating sub-frame jitter. A method that lags behind the audio and makes lights feel sluggish is unacceptable.
- **FR-021**: The system MUST normalize all output values to integers in the range 0–100.

**xLights Export**

- **FR-022**: Discrete event data (beat hits, onset events, handoff events, structural boundaries) MUST be exported as xLights-compatible timing track files.
- **FR-023**: Continuous feature data (energy curves, sidechained curves, spectral centroid curves, pitch salience curves, leader-track transitions) MUST be exported as xLights value curve (`.xvc`) XML files.
- **FR-024**: Value curve files MUST store one integer value (0–100) per sequence frame for the full duration of the song, formatted in the data encoding that xLights expects when importing `.xvc` files.
- **FR-025**: Each export file MUST be named to indicate its source stem, feature type, and algorithm so users can identify it without opening it.
- **FR-026**: All export files MUST be written to the song's `analysis/` directory.
- **FR-027**: The system MUST support both macro value curves (full-song duration, for master dimmer use) and micro value curves (short duration, for effect-specific use).

**Full Pipeline**

- **FR-028**: A single command MUST run all steps end-to-end: inspection, optional interactive selection, parameter initialization, sweep analysis, interaction analysis, conditioning, and export.
- **FR-029**: The full pipeline command MUST support an `--interactive` flag that pauses for user stem confirmation before proceeding.

### Key Entities

- **Stem**: An isolated audio track (drums, bass, vocals, guitar, piano, other, or full mix) with associated quality metrics and a selection verdict.
- **Stem Verdict**: A KEEP / REVIEW / SKIP classification with measurements and plain-language reasoning.
- **Sweep Configuration**: Per-algorithm parameter ranges and fixed values, with the stem(s) to analyze and the rationale for the ranges.
- **Leader Track**: A time-series record of which stem holds dominant energy at each frame.
- **Tightness Score**: A time-series measure of rhythmic lock between kick drum and bass guitar, derived by comparing onset peak timing rather than raw audio to avoid stem separation artifacts.
- **Sidechained Curve**: A continuous feature curve modified by drum onset positions to create dynamic contrast.
- **Handoff Event**: A timestamped marker where a melodic motif transitions from one stem to another.
- **Value Curve** (`.xvc`): A conditioned, normalized continuous feature exported for use as an xLights effect property driver.
- **Timing Track**: A conditioned, discrete-event export for use as an xLights beat/marker track.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from a raw song file (with stems already separated) to a full set of xLights-ready timing tracks and value curves in under 5 minutes via the automated pipeline.
- **SC-002**: At least 80% of intelligently derived parameter ranges contain the optimal parameter value (as determined by the highest quality-scored result from a broader manual sweep).
- **SC-003**: Timing tracks produced from intelligently initialized sweeps score at least 15% higher on average quality metrics than tracks produced with static default parameters.
- **SC-004**: The interactive stem review workflow allows a user to review and confirm or override verdicts for a 6-stem song in under 2 minutes.
- **SC-005**: All exported value curve files load without error in xLights and produce visible light changes when applied to a brightness or position effect property.
- **SC-006**: Leader-track transitions align with audibly perceptible stem energy changes within a tolerance of 1 sequence frame (50ms at 20 FPS).
- **SC-007**: High-tightness kick/bass sections are identified with at least 85% recall when compared to manually labeled sections in a reference song.
- **SC-008**: Zero analysis runs are wasted on SKIPped stems, confirming the filtering step reduces unnecessary computation.

---

## Assumptions

- Stem separation has already been run before this pipeline is invoked. This feature does not perform separation itself.
- The full mix is always available as a fallback regardless of stem availability.
- The default target frame rate for export is 20 FPS (50ms intervals); this is configurable.
- Parameter sweep ranges are bounded to physically meaningful values (e.g., BPM between 40 and 240) to prevent nonsensical configurations.
- The kick drum signal is derived from the drums stem; the bass signal is derived from the bass stem. Cross-correlation requires both to be KEEPed.
- Value curves are intended as automation inputs in xLights (driving brightness, position, rotation, etc.) rather than as direct channel values.
- Smoothing preserves musically meaningful transitions (beat hits, drops) while eliminating sub-frame noise. The smoothing window is configurable.
- Users are comfortable with a terminal/CLI workflow; no GUI is required for this feature.
