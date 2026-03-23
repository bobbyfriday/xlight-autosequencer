# Feature Specification: Configurable Quality Scoring

**Feature Branch**: `006-quality-score-config`
**Created**: 2026-03-22
**Status**: Placeholder
**Input**: Replace the current fixed quality scoring logic with a configurable, explainable scoring system that lets users define what makes a "good" timing track for their use case — tuning weights, thresholds, and scoring criteria — and understand why any given track received its score.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand Why a Track Scored the Way It Did (Priority: P1)

A user runs analysis and sees that their preferred drum track scored lower than an onset
track they find musically uninteresting. They want to understand the reasoning — which
scoring criteria penalized the drum track and why — so they can decide whether to trust
the score or override it.

**Why this priority**: A black-box score breeds distrust. Explainability is what makes
scoring a tool rather than a gatekeep. Users need this before they can meaningfully
configure scoring.

**Acceptance Scenarios**:

1. **Given** a completed analysis run, **When** the user requests score details for a
   named track, **Then** the output shows each scoring criterion, the value measured,
   the score contribution, and a plain-language description of what was evaluated.
2. **Given** two tracks with different scores, **When** the user compares them, **Then**
   the breakdown makes clear which criteria produced the score difference.
3. **Given** a track that scores well on density but poorly on regularity, **When** the
   breakdown is shown, **Then** those two dimensions are reported separately rather than
   collapsed into a single number.

---

### User Story 2 - Adjust Scoring Weights and Thresholds (Priority: P1)

A user lighting a song with a fast, busy arrangement wants denser timing tracks than
the defaults favour. Another user lighting ambient music wants sparser tracks. Both
want to configure the scoring criteria so the auto-selected top tracks match their
aesthetic preference without manual track selection every time.

**Why this priority**: Default scoring is optimized for a generic case. Different music
genres, display types, and user preferences require different definitions of "good."

**Acceptance Scenarios**:

1. **Given** a configuration that increases the weight of track density, **When**
   analysis runs and tracks are scored, **Then** denser tracks rank higher than they
   did under default weights.
2. **Given** a configuration that sets a minimum mark count threshold, **When** tracks
   are scored, **Then** tracks below the threshold are excluded from the ranked output
   regardless of other score components.
3. **Given** default configuration, **When** analysis runs, **Then** scoring results
   are identical to the pre-configuration-layer baseline.
4. **Given** an invalid scoring configuration (weight outside valid range, unknown
   criterion name), **When** analysis starts, **Then** the tool rejects it with a
   descriptive error before running any analysis.

---

### User Story 3 - Save and Share Scoring Profiles (Priority: P2)

A user who has tuned scoring weights for a particular genre or display type can save
those settings as a named profile and reuse them across sessions or share them with
other users.

**Acceptance Scenarios**:

1. **Given** a customized scoring configuration, **When** the user saves it as a named
   profile, **Then** running analysis with that profile name applies the saved settings.
2. **Given** a scoring profile file, **When** it is loaded on a different machine,
   **Then** it produces identical scoring results for the same input tracks.

---

### Edge Cases

- A configuration where all weights are zero (undefined scoring).
- A configuration where the minimum threshold eliminates all tracks from the output.
- Scoring a track that has zero timing marks.
- A profile that references a scoring criterion removed in a newer version of the tool.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every scored track MUST include a per-criterion breakdown in the output,
  showing the measured value and score contribution for each criterion.
- **FR-002**: The scoring system MUST expose at minimum: mark density, regularity
  (variance of inter-mark intervals), total mark count, and coverage (fraction of
  song duration containing marks).
- **FR-003**: Users MUST be able to configure the weight of each scoring criterion via
  a configuration file.
- **FR-004**: Users MUST be able to set minimum and maximum thresholds for any
  scoring criterion; tracks outside thresholds are excluded from ranked output.
- **FR-005**: The configuration schema MUST be documented so users can understand and
  edit it without reading source code.
- **FR-006**: Scoring configuration MUST be saveable as named profiles on the filesystem.
- **FR-007**: Default scoring behavior MUST be preserved when no custom configuration
  is provided — existing analysis results MUST remain comparable.
- **FR-008**: Score breakdowns MUST include a plain-language label for each criterion
  so non-technical users can interpret the output.

### Key Entities

- **ScoringCriterion**: A single measurable dimension of track quality — name,
  description, measured value, weight, score contribution, threshold (optional).
- **ScoreBreakdown**: The full per-track scoring result — overall score, list of
  ScoringCriteria with values and contributions, pass/fail threshold results.
- **ScoringConfig**: A user-defined configuration — map of criterion name to weight,
  threshold rules, profile name (optional).
- **ScoringProfile**: A named, saved ScoringConfig stored on the filesystem.

---

## Success Criteria *(mandatory)*

- A user who disagrees with a track's auto-ranking can identify the specific scoring
  criterion responsible by reading the score breakdown alone, without inspecting code.
- Adjusting a single criterion weight changes the ranking of at least one track in a
  reference test set in the expected direction.
- All scoring criteria, their default weights, and their valid ranges are discoverable
  from the tool without reading source code.
- Custom scoring profiles produce identical results across machines and sessions when
  the same profile and input are used.

---

## Assumptions

- The current scorer (`scorer.py`) uses density and regularity as primary criteria;
  these become the first configurable criteria in this feature.
- Score breakdowns are added to the existing JSON output structure rather than a
  separate file.
- "Plain-language labels" means a short description string per criterion, not a
  natural language generation system.

---

## Open Questions

- **OQ-001**: Should scoring criteria be extensible (user-defined criteria via plugin
  or script), or is a fixed set of named criteria sufficient?
- **OQ-002**: How should criteria interact — are they always a weighted sum, or should
  the user be able to define AND/OR threshold logic?

---

## Out of Scope

- Machine learning-based scoring or scoring that learns from user feedback.
- A graphical interface for score configuration (may be added to the review UI later).
- Automatic scoring profile recommendation based on genre detection.
