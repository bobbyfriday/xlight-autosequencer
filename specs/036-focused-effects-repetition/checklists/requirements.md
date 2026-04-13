# Requirements Checklist: 036 - Focused Effect Vocabulary + Embrace Repetition

## Spec Quality

- [x] Spec has User Scenarios & Testing section with prioritized stories
- [x] Each user story has a priority level (P1, P2, etc.)
- [x] Each user story has acceptance scenarios in Given/When/Then format
- [x] Each user story has an independent test description
- [x] Each user story explains why it has its assigned priority
- [x] Edge cases are identified and documented
- [x] Spec has Requirements section with Functional Requirements
- [x] Spec has Key Entities section
- [x] Spec has Success Criteria section with Measurable Outcomes
- [x] Spec has Assumptions section
- [x] Spec has Relationship to Other Phases section

## Content Quality

- [x] Spec focuses on WHAT and WHY, not HOW (no implementation details)
- [x] No language, framework, or API specifics mentioned in requirements
- [x] Written for non-technical stakeholders
- [x] Every functional requirement is testable
- [x] Every success criterion is measurable and technology-agnostic
- [x] Success criteria reference concrete numeric targets from reference analysis

## Functional Requirements Coverage

- [x] FR-001: Theme working set limited to at most 8 effects (covers US1)
- [x] FR-002: Working set includes frequency weights for steep distribution (covers US3)
- [x] FR-003: Intra-section same-effect repetition allowed without penalty (covers US2)
- [x] FR-004: Cross-section repetition allowed for same-theme sections (covers US2)
- [x] FR-005: Section boundaries are primary effect change points (covers US1, US2)
- [x] FR-006: Focused vocabulary behavior is independently toggleable (covers US4)
- [x] FR-007: Repetition behavior is independently toggleable (covers US4)
- [x] FR-008: No regression when both behaviors are disabled (covers US4)
- [x] FR-009: Prop/compound tier respects focused vocabulary (covers US1)
- [x] FR-010: Reference analyzer usable for Phase 1 validation (covers all US)

## Success Criteria Coverage

- [x] SC-001: Top-5 effects >= 80% of placements (maps to FR-001, FR-002)
- [x] SC-002: Top effect >= 25% of placements (maps to FR-002)
- [x] SC-003: Top-2 effects >= 50% of placements (maps to FR-002)
- [x] SC-004: Consecutive repetition >= 10 per section (maps to FR-003)
- [x] SC-005: Within-section variety <= 2 per model (maps to FR-003, FR-005)
- [x] SC-006: Section transitions show vocabulary change >= 70% (maps to FR-005)
- [x] SC-007: Each behavior independently toggleable (maps to FR-006, FR-007)
- [x] SC-008: No regression when disabled (maps to FR-008)

## User Story Acceptance Scenario Coverage

- [x] US1 covers effect pool size constraint
- [x] US1 covers cross-section consistency for same theme
- [x] US1 covers natural satisfaction when theme defines few effects
- [x] US2 covers sustained repetition on base-tier models
- [x] US2 covers upper-tier parameter variation
- [x] US2 covers same-label section reuse with palette variation
- [x] US2 covers section transition vocabulary change
- [x] US3 covers weighted selection producing steep distribution
- [x] US3 covers top-effect and top-2 dominance metrics
- [x] US4 covers disabled-equals-baseline behavior
- [x] US4 covers independent toggle of each behavior
- [x] US4 covers combined enabled behavior
- [x] US4 covers no test regression when disabled

## Traceability

- [x] All user stories trace to at least one functional requirement
- [x] All functional requirements trace to at least one success criterion
- [x] All success criteria have numeric targets derived from reference analysis
- [x] Parent spec (035) Phase 1 scope is fully covered (US1 + US3 from 035)
- [x] Reference analysis findings are accurately reflected in targets and rationale
