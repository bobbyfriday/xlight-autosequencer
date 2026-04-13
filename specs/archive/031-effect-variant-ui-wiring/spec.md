# Feature Specification: Effect & Variant Library UI Wiring

**Feature Branch**: `031-effect-variant-ui-wiring`
**Created**: 2026-04-01
**Status**: Draft
**Input**: User description: "Wire the effect library and variant library into the web UI so the theme editor, story review, and dashboard can browse, select, and apply pre-tuned effect variants from the variant library."

## Clarifications

### Session 2026-04-01

- Q: Should story review show effect/variant details in section panels? → A: No — the existing theme palette strip is sufficient. Story review is out of scope for this feature.
- Q: How should the variant picker appear in the theme editor? → A: Inline expandable section below the effect dropdown in each layer row.
- Q: How to disambiguate "theme variants" (alternate layer sets) from "effect variants" (library presets)? → A: Rename theme variants to "alternates" in the UI and spec. "Variant" refers exclusively to effect variants from the library.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and Apply Variants in Theme Editor (Priority: P1)

A user is editing a theme and adds an effect layer. After selecting an effect (e.g. "Bars"), they want to see the pre-tuned variants available for that effect — such as "Bars Single 3D Half-Cycle" — instead of manually tweaking every parameter. They pick a variant and the layer's parameters are populated automatically. They can still override individual parameters on top of the variant's defaults.

**Why this priority**: This is the core gap — the variant library exists with 123+ curated variants but is completely invisible in the UI. Connecting it to the theme editor unlocks the library's value and dramatically simplifies theme creation.

**Independent Test**: Can be tested by opening the theme editor, adding an effect layer, selecting an effect, and verifying that matching variants appear for selection. Selecting a variant should populate the parameter overrides and set `variant_ref` on the layer.

**Acceptance Scenarios**:

1. **Given** the theme editor is open and a user adds a new layer, **When** they select "Bars" as the effect, **Then** a variant picker appears showing all Bars variants from the library with their descriptions and tags.
2. **Given** a user has selected a variant for a layer, **When** they view the parameter overrides section, **Then** the variant's parameter values are shown as the base, and the user can override individual parameters on top.
3. **Given** a user has selected a variant for a layer, **When** they save the theme, **Then** the layer's `variant_ref` field is set to the chosen variant name and persists on reload.
4. **Given** a user has a layer with a variant_ref, **When** they want to detach from the variant, **Then** they can clear the variant reference while keeping the current parameter values as manual overrides.

---

### User Story 2 - Context-Aware Variant Suggestions in Theme Editor (Priority: P2)

A user is building a theme intended for high-energy chorus sections. When they select an effect for a layer, the variant picker ranks and highlights variants that match the theme's mood, energy level, and intended use — surfacing the most suitable options first rather than presenting an unsorted list.

**Why this priority**: The variant library's scoring engine already supports context-based ranking. Exposing this in the UI helps users make better choices without needing to understand the tagging system. Builds on P1's variant picker infrastructure.

**Independent Test**: Can be tested by creating a theme with a specific mood/energy profile, adding a layer, and verifying that the variant suggestions are ranked by relevance to the theme's context.

**Acceptance Scenarios**:

1. **Given** a theme has mood set to "aggressive" and the user adds a layer, **When** the variant picker appears, **Then** variants tagged for high-energy sections appear first.
2. **Given** a user is editing a background-tier layer, **When** they browse variants, **Then** variants with tier_affinity "background" are ranked higher than "hero" variants.
3. **Given** variants are displayed in the picker, **When** the user views a variant entry, **Then** they can see the variant's energy level, tier affinity, and section role tags to inform their choice.

---

### User Story 3 - Standalone Variant Library Browser (Priority: P3)

A user wants to explore the full variant library — browsing all available variants across effects, filtering by energy level, tier, section role, or prop suitability, and viewing detailed parameter breakdowns. This serves as a reference and discovery tool separate from the theme editor.

**Why this priority**: While P1-P2 embed variant selection into existing workflows, a dedicated browser helps users understand the full scope of available variants and makes informed decisions about which to use. It also exposes the coverage stats endpoint to show which effects have good variant coverage and which are lacking.

**Independent Test**: Can be tested by navigating to the variant browser page and verifying that all variants are listed, filters narrow results correctly, and variant detail views show complete information.

**Acceptance Scenarios**:

1. **Given** the user navigates to the variant browser, **When** the page loads, **Then** all variants are listed grouped by base effect with counts per effect.
2. **Given** the variant list is displayed, **When** the user applies an energy filter (e.g. "high"), **Then** only variants tagged with high energy are shown.
3. **Given** a user clicks on a variant, **When** the detail view opens, **Then** it shows the variant's full parameter overrides, tags, description, and which effect it applies to.
4. **Given** the user views coverage statistics, **When** the stats panel loads, **Then** it shows which effects have variants and which do not, helping identify gaps.

---

### Edge Cases

- What happens when a variant referenced by a theme layer is deleted from the library? The system should gracefully degrade — the layer keeps its parameter overrides but shows a warning that the variant_ref is no longer valid.
- What happens when the variant library is empty or fails to load? The theme editor should function normally with manual parameter editing, and the variant picker should show an empty state message.
- What happens when an effect has no variants in the library? The variant picker section should indicate "No variants available" and allow the user to proceed with manual parameter configuration.
- What happens when a variant's base effect definition changes (parameters added/removed)? Stale parameter overrides in the variant should be ignored for removed parameters and new parameters should use their defaults.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The theme editor MUST display a variant picker as an inline expandable section below the effect dropdown when an effect is selected for a layer, showing all variants from the library that match the selected effect.
- **FR-002**: Selecting a variant in the picker MUST populate the layer's parameter overrides with the variant's values and set the layer's `variant_ref` to the variant name.
- **FR-003**: Users MUST be able to override individual parameters on top of a variant's base values, with clear visual distinction between variant-provided and user-overridden values.
- **FR-004**: Users MUST be able to detach a layer from its variant reference while retaining the current parameter values.
- **FR-005**: The variant picker MUST display variant metadata including description, energy level, tier affinity, and section roles.
- **FR-006**: The variant picker MUST rank variants by contextual relevance when theme context (mood, energy, occasion) is available.
- **FR-007**: The system MUST provide a standalone variant browser page accessible from the main navigation.
- **FR-008**: The variant browser MUST support filtering by base effect, energy level, tier affinity, section role, and scope.
- **FR-009**: The variant browser MUST display coverage statistics showing which effects have variants and overall library completeness.
- **FR-010**: The system MUST handle missing or deleted variant references gracefully, displaying a warning without breaking theme editing or sequence generation.
- **FR-011**: The variant picker and browser MUST use the existing variant library endpoints — no duplicate data sources.

### Key Entities

- **Effect Variant**: A pre-tuned parameter configuration for a specific effect, with metadata tags (energy, tier, section roles, scope, genre affinity) and an optional direction cycle.
- **Variant Reference**: A named link from a theme's effect layer to an effect variant, enabling parameter inheritance with local overrides.
- **Scoring Context**: The combination of theme mood, energy, tier, and section role used to rank variant suggestions by relevance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select a pre-tuned variant for any effect layer in the theme editor within 3 clicks (select effect, browse variants, pick one).
- **SC-002**: 100% of the variant library's entries are browsable and selectable through the web UI — no variants are only accessible via the programmatic interface.
- **SC-003**: Variant suggestions in the theme editor are ranked by contextual relevance, with the most suitable variant appearing in the top 3 results for a given theme context at least 80% of the time.
- **SC-004**: The variant browser supports all existing filter dimensions (effect, energy, tier, section role, scope) with results updating in under 1 second.

## Assumptions

- The existing variant library endpoints (`/variants`, `/variants/query`, `/variants/coverage`) are stable and sufficient — no new backend endpoints are needed.
- The existing `variant_ref` field on `EffectLayer` and the parameter resolution chain in the effect placer are correct and do not need modification.
- The theme editor's current effect dropdown and parameter editing UI will be extended, not replaced.
- The variant library contains sufficient curated variants (123+) to provide meaningful suggestions across common effects.
- Story review is out of scope — the existing theme palette strip on sections is sufficient; effect/variant details are not needed there.
