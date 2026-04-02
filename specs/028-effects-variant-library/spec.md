# Feature Specification: Effects Variant Library

**Feature Branch**: `028-effects-variant-library`
**Created**: 2026-04-01
**Status**: Draft
**Input**: User description: "Create a large, organized repository of xLights effect variants — specific parameter configurations of base effects — categorized by prop suitability, layer role, music context, and linked to themes for automated sequence generation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and Discover Effect Variants (Priority: P1)

A sequence designer wants to find the right visual effect for a specific situation — e.g., a chase effect that sweeps left-to-right on arches during a high-energy chorus. They browse the effects variant library, filtering by base effect type, prop suitability, and intended musical context, and find several pre-built variants with descriptions of what each looks like.

**Why this priority**: Without a browsable, organized catalog of proven effect variants, users must manually experiment with xLights parameters for every placement. This is the foundational capability that all other stories build on.

**Independent Test**: Can be fully tested by loading the variant library and querying it with filters (prop type, layer, energy level) to receive relevant results with human-readable descriptions.

**Acceptance Scenarios**:

1. **Given** the effects variant library is loaded, **When** a user queries for variants of the "Bars" effect suitable for arches, **Then** the system returns all Bars variants tagged as "good" or "ideal" for linear/arch props, each with a name, description, and parameter values.
2. **Given** a user filters by "high energy" and "beat-synced", **When** results are returned, **Then** only variants with beat or trigger duration types and high-energy intent tags appear.
3. **Given** the library contains variants from multiple base effects, **When** a user browses without filters, **Then** variants are organized by base effect and display their category, layer role, and suitability summary.

---

### User Story 2 - Import Variants from Existing Sequences (Priority: P2)

A user has existing xLights .xsq sequence files that contain effects they like. They want to extract those effect configurations and import them into the variant library so they can be reused in future generated sequences.

**Why this priority**: Mining proven effect configurations from real sequences is the fastest way to populate the library with variants that are known to look good, rather than hand-crafting every variant from scratch.

**Independent Test**: Can be fully tested by pointing the importer at a .xsq file and verifying that extracted effect variants appear in the library with correct parameters, descriptions, and metadata.

**Acceptance Scenarios**:

1. **Given** a valid .xsq sequence file with multiple effects, **When** the user runs the import tool, **Then** each unique effect configuration is extracted as a named variant with its full parameter set. Source color palettes and blend modes are logged for reference but not stored on the variant.
2. **Given** an imported variant duplicates an existing library entry (same base effect and identical parameters), **When** import completes, **Then** the duplicate is flagged and the user can choose to skip, merge, or create as new.
3. **Given** an imported effect uses parameters not in the current effect catalog, **When** import encounters unknown parameters, **Then** they are preserved in the variant and a warning is logged identifying the unknown parameters.

---

### User Story 3 - Create and Edit Custom Variants (Priority: P2)

A user wants to define a new effect variant manually — for example, a "Meteors Gentle Rain" variant of the Meteors effect with specific speed, count, and trail length settings that create a soft falling look. They create the variant, describe what it looks like, tag it with prop suitability and musical context, and save it to their custom library.

**Why this priority**: While importing from sequences bootstraps the library quickly, users also need to hand-craft variants for specific artistic intentions not found in existing sequences.

**Independent Test**: Can be fully tested by creating a custom variant via the interface, saving it, and then retrieving it from the library with all metadata intact.

**Acceptance Scenarios**:

1. **Given** a user selects a base effect (e.g., Meteors), **When** they specify parameter overrides, a descriptive name, visual description, and suitability tags, **Then** the variant is saved to the custom variants directory and appears in library queries.
2. **Given** an existing custom variant, **When** the user edits its parameters or metadata, **Then** the updated variant replaces the previous version and all references in themes remain valid.
3. **Given** a user creates a variant with invalid parameter values (e.g., slider value above maximum), **When** they attempt to save, **Then** validation errors are reported identifying which parameters are out of range.

---

### User Story 4 - Link Variants to Themes (Priority: P3)

A sequence designer wants to update a theme's layer definitions to use specific named variants instead of raw effect names with inline parameter overrides. They browse available variants for an effect, select one that fits the theme's mood, and assign it to a theme layer.

**Why this priority**: Connecting variants to themes is the payoff — it makes the sequence generator produce more intentional, curated visual results by drawing from proven configurations rather than defaults.

**Independent Test**: Can be fully tested by assigning a variant to a theme layer and generating a sequence plan that resolves the variant into concrete effect parameters.

**Acceptance Scenarios**:

1. **Given** a theme layer currently references a base effect with parameter overrides, **When** a matching variant exists in the library, **Then** the theme can be updated to reference the variant by name and the inline overrides are replaced.
2. **Given** a theme references a variant by name, **When** the sequence generator builds a plan, **Then** the variant's full parameter set, suitability, and duration type are used for placement.
3. **Given** a theme references a variant that no longer exists in the library, **When** the theme is loaded, **Then** a validation warning identifies the missing variant and the system falls back to the base effect defaults.

---

### User Story 5 - Categorize and Tag Variants for Automated Selection (Priority: P3)

As the variant library grows, the sequence generator should be able to automatically select the best variant for a given context — choosing based on prop type, energy level, section role (verse/chorus/bridge), and layer position. The user tags variants with this metadata so the generator can make intelligent selections.

**Why this priority**: This transforms the library from a manual lookup tool into an intelligent selection engine, which is the ultimate goal for fully automated sequence generation.

**Independent Test**: Can be fully tested by querying the library with a multi-dimensional context (prop type + energy + section role + layer) and verifying the returned variants are appropriate matches ranked by suitability.

**Acceptance Scenarios**:

1. **Given** variants are tagged with energy ranges (low/medium/high), **When** the generator queries for a chorus section with energy score 85, **Then** only high-energy variants are returned.
2. **Given** multiple variants match a query context, **When** results are returned, **Then** they are ranked by a composite suitability score combining prop fit, energy match, and layer role fit.
3. **Given** no variants match all query dimensions, **When** the generator queries, **Then** the system falls back gracefully — relaxing constraints in priority order (layer role first, then energy, then prop type) until at least one result is found.

---

### Edge Cases

- What happens when a .xsq file contains effects from newer xLights versions with unknown effect types? The importer preserves the raw data and flags for manual review.
- How does the system handle conflicting variant names? Custom variants take precedence over built-in. Name collisions within the same scope are rejected at save time.
- What happens when a variant's base effect is removed from the xLights effect catalog? The variant remains but is marked as "orphaned" with a validation warning.
- How are direction-based permutations handled (left/right, up/down, CW/CCW)? Each direction is a distinct variant of the same base effect, explicitly named and tagged (e.g., "Bars Sweep Up", "Bars Sweep Down").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support an effect variant entity that extends a single base xLights effect with a specific set of parameter values, a human-readable name, a visual description, and categorization metadata. Variants do not include color palettes (theme-owned) or blend modes (theme-layer-owned). Multi-effect compositions remain the theme's responsibility.
- **FR-002**: System MUST store built-in variants in a bundled catalog file and custom user variants in per-file storage under the user's configuration directory.
- **FR-003**: System MUST support querying variants by any combination of: base effect name, inherited base effect dimensions (category, prop suitability, layer role, duration type), and variant-specific tags (tier affinity, energy level, speed feel, direction, section roles, scope, genre affinity).
- **FR-004**: System MUST validate that all variant parameter values fall within the ranges defined by the base effect's parameter schema.
- **FR-005**: System MUST extract effect configurations from .xsq sequence files and convert them into variant entries, preserving all effect parameters. Color palettes and blend modes from the source sequence are logged for reference but not stored on the variant (palettes are theme-owned, blend modes are theme-layer-owned).
- **FR-006**: System MUST detect duplicate variants during import by comparing base effect name and parameter values (identity is effect + parameters, not name). Duplicates are flagged and the user can skip, merge, or create as new.
- **FR-007**: System MUST allow themes to reference effect variants by name as an alternative to inline parameter overrides, with the variant's parameters taking precedence.
- **FR-008**: System MUST fall back to base effect defaults when a theme references a variant that does not exist in the library.
- **FR-009**: System MUST support direction-based variant permutations (e.g., up/down, left/right, clockwise/counter-clockwise) as distinct named variants of the same base effect.
- **FR-010**: System MUST support tagging variants with the following variant-specific metadata dimensions (base effect dimensions like category, layer_role, duration_type, and prop_suitability are inherited from the parent effect and not duplicated):
  - **Tier affinity**: background, mid, foreground, or hero — where in the render hierarchy this variant looks best
  - **Energy level**: low, medium, or high — the visual intensity of this configuration
  - **Speed feel**: slow, moderate, or fast — human-labeled perception of the variant's motion
  - **Direction**: explicit directional tag (e.g., sweep-left, rain-down, expand-out, clockwise) when applicable
  - **Section roles**: verse, chorus, bridge, intro, outro, build, drop — which song sections this variant suits
  - **Scope**: single-prop or group — whether the variant reads well on one fixture or needs a coordinated group
  - **Genre affinity**: any, rock, classical, pop, electronic, etc. — musical style this variant complements
- **FR-011**: System MUST rank query results by a composite suitability score when multiple variants match a context query.
- **FR-012**: System MUST validate variant references in themes and report warnings for missing or orphaned variants.
- **FR-013**: Users MUST be able to create, edit, and delete custom variants through both the CLI and the web dashboard, with full CRUD support in each interface.
- **FR-014**: System MUST ship with a populated built-in variant catalog covering the most commonly used effect configurations across major prop types.

### Key Entities

- **Effect Variant**: A named, reusable configuration of a base xLights effect. Comprises a unique name, reference to the base effect, a complete parameter override set (excluding color palette and blend mode, which are theme-owned), and a visual description. Inherits base effect dimensions (category, layer_role, duration_type, prop_suitability) from its parent effect. Carries variant-specific tags: tier affinity, energy level, speed feel, direction, section roles, scope, and genre affinity.
- **Variant Catalog**: The aggregate collection of all effect variants — both built-in (shipped with the application, read-only) and custom (user-created, editable). Supports filtered querying and ranked retrieval.
- **Variant Reference**: A named pointer from a theme layer to a specific effect variant, replacing inline parameter overrides with a library lookup.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The built-in variant catalog ships with at least 100 distinct, described effect variants covering all 7 effect categories and all major prop types.
- **SC-002**: Users can find a suitable effect variant for a given context (prop type + energy + layer) within 3 query attempts or fewer.
- **SC-003**: Importing effects from a typical .xsq sequence file (50+ effects) completes and produces deduplicated variant entries with no manual parameter entry required.
- **SC-004**: Sequences generated using variant-linked themes produce visually distinct results compared to sequences using only base effect defaults — measured by parameter diversity across placements.
- **SC-005**: 90% of variants in the built-in catalog include accurate prop suitability ratings validated against at least one real prop type.
- **SC-006**: Theme authors can replace inline parameter overrides with variant references and the generated output is identical to the previous inline approach.

## Clarifications

### Session 2026-04-01

- Q: Which interface should support variant CRUD operations (CLI, web dashboard, or both)? → A: Both CLI and web dashboard support full create, edit, delete, and browse operations.
- Q: Should variants carry their own color palette or inherit from the theme? → A: Palettes always inherited from theme. Variants define only parameters and behavior, not colors.
- Q: How should the initial built-in catalog of 100+ variants be populated? → A: Hybrid — hand-curate ~30-40 core variants from existing themes and generator effect pool, then bulk-import from real .xsq sequences to reach 100+.
- Q: What defines variant uniqueness for duplicate detection? → A: Base effect name + parameter values. Two variants with identical effect and parameters are duplicates regardless of name. Names are display labels, not identity keys.
- Q: Should blend mode live on the variant or on the theme layer? → A: Theme owns blend mode. Variants define only effect parameters and behavior. Multi-layer compositions (e.g., two shockwaves stacked, or base + modifier) are the theme's responsibility — each layer references a single-effect variant, and the theme controls blend mode and layer order. Composite effect stacks are not in scope for this feature.

## Assumptions

- The existing 35-effect catalog in `builtin_effects.json` and its parameter schema serve as the authoritative source of truth for base effects and valid parameter ranges.
- Variants are parameter-level configurations — they do not introduce new effects or new parameters beyond what the base effect defines.
- The .xsq import workflow targets xLights 2024.x format sequences. Older formats may require manual adjustment.
- The built-in variant catalog will be populated iteratively: (1) hand-curate ~30-40 core variants from existing theme layers and the generator's effect pool, (2) import from a single .xsq sequence to validate the importer and assess variant yield, (3) identify coverage gaps by effect category and prop type, (4) expand with additional sequences targeted at filling those gaps until reaching 100+.
- Custom variants follow the same file-per-entry convention used by custom effects and custom themes.
