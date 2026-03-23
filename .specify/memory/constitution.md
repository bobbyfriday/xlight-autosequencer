<!--
SYNC IMPACT REPORT
==================
Version change: N/A -> 1.0.0 (initial constitution — all placeholders replaced)

Modified principles: N/A (initial creation)

Added sections:
  - Core Principles (5 principles)
  - Technical Constraints
  - Development Workflow
  - Governance

Removed sections: N/A

Templates requiring updates:
  - .specify/templates/plan-template.md     ✅ no changes required (generic gates language sufficient)
  - .specify/templates/spec-template.md     ✅ no changes required (generic structure sufficient)
  - .specify/templates/tasks-template.md    ✅ no changes required (generic structure sufficient)
  - .specify/templates/agent-file-template.md  ✅ no changes required
  - .specify/templates/checklist-template.md   ✅ no changes required

Follow-up TODOs:
  - TODO(TECH_STACK): Language and primary dependencies not yet decided.
    Confirm before Phase 0 of first feature (Python + librosa/aubio likely).
  - TODO(XLIGHT_VERSION): Minimum target xLights version for output compatibility
    not yet specified. Confirm before implementing sequence export.
-->

# XLight AutoSequencer Constitution

## Core Principles

### I. Audio-First Pipeline

The audio track is the authoritative source of truth for all timing decisions.
Every sequence element — beat markers, timing tracks, effect boundaries — MUST
derive from analyzed audio data rather than manual input or arbitrary defaults.

- Audio analysis (beat detection, tempo, frequency bands) MUST run before any
  sequence generation step.
- Timing data MUST be reproducible: the same input file MUST always produce the
  same timing output given the same configuration.
- Manual overrides are permitted only as post-processing adjustments; they MUST
  NOT alter the core analysis pipeline.

**Rationale**: The entire value of this tool is automation. If timing is not
grounded in the audio, the output is no better than manual sequencing.

### II. xLights Compatibility

All output MUST be importable into xLights without modification.

- Output sequence files MUST conform to the xLights XML schema (`.xsq` format).
- Model names, timing track names, and group names MUST follow xLights naming
  conventions (no characters that xLights rejects on import).
- Generated sequences MUST be validated against xLights structure before export
  is considered complete.
- TODO(XLIGHT_VERSION): Define the minimum xLights version targeted for output
  compatibility before the sequence export stage is implemented.

**Rationale**: A sequence that cannot be opened in xLights delivers zero value
to the end user.

### III. Modular Pipeline

The tool is structured as a pipeline of independent, composable stages.

- Each stage (audio ingest, beat/tempo analysis, timing track generation, model
  grouping, sequence assembly, file export) MUST be independently executable
  and testable in isolation.
- Stages MUST communicate via well-defined data contracts (structs or schemas),
  not shared mutable state.
- Replacing a stage (e.g., swapping the audio analysis library) MUST NOT require
  changes to other stages.

**Rationale**: Audio analysis libraries, xLights formats, and grouping strategies
will evolve. A modular pipeline keeps changes local and independently testable.

### IV. Test-First Development

Tests MUST be written and confirmed failing before implementation begins.

- Red-Green-Refactor is enforced: write failing test, implement, make it pass.
- Each pipeline stage MUST have unit tests with known input/output fixtures.
- Integration tests MUST cover the end-to-end path: audio file in, valid xLights
  sequence file out.
- Short, royalty-free fixture audio files MUST be included in the test suite to
  ensure deterministic, reproducible test runs.

**Rationale**: Audio processing is difficult to debug without reproducible,
fixture-based tests. TDD prevents regressions as the pipeline evolves.

### V. Simplicity First

Implement only what is needed for the current feature. No speculative design.

- YAGNI applies: do not build configurability, extensibility, or abstraction
  layers that no current feature requires.
- A working pipeline with fewer features is always preferred over an incomplete
  pipeline with more features.
- Any introduced complexity MUST be justified in the plan's Complexity Tracking
  table before work begins.

**Rationale**: This is a greenfield project. Premature abstraction creates
maintenance debt before there is any value to protect.

## Technical Constraints

- **Input formats**: MP3 (audio) and MP4 (video + audio). Additional formats are
  out of scope until the core pipeline is validated end-to-end.
- **Output format**: xLights sequence file (`.xsq`, XML-based).
- **Runtime**: TODO(TECH_STACK) — language and dependencies not yet decided.
  Python is the likely candidate (librosa or aubio for audio analysis, lxml for
  XML generation) but MUST be confirmed before Phase 0 of the first feature.
- **Offline operation**: The tool MUST operate fully offline. No cloud API calls
  are permitted for audio analysis or sequence generation.
- **Performance baseline**: Processing a 3-minute MP3 MUST complete in under
  60 seconds on a modern laptop. Revise once benchmarked.

## Development Workflow

- Every feature follows the speckit flow: `/speckit.specify` → `/speckit.plan`
  → `/speckit.tasks` → `/speckit.implement`.
- The Constitution Check section in `plan.md` MUST be completed and pass before
  Phase 0 research begins.
- All pull requests MUST include passing tests for every pipeline stage touched.
- Each generated sequence MUST be manually imported into xLights at least once
  before the feature is considered done.
- Commit after each completed task; do not batch unrelated changes in one commit.

## Governance

This constitution supersedes all other development practices and preferences.
Amendments require:

1. A written rationale describing what changed and why.
2. A version bump following the policy below.
3. A migration note if existing features or tests are affected.

**Versioning policy**:
- MAJOR: A principle is removed, renamed, or fundamentally redefined.
- MINOR: A new principle or section is added, or existing guidance is materially
  expanded.
- PATCH: Clarifications, wording fixes, or non-semantic refinements.

**Compliance**: All implementation plans and task lists MUST reference the active
constitution version and confirm compliance before work begins.

**Version**: 1.0.0 | **Ratified**: 2026-03-22 | **Last Amended**: 2026-03-22
