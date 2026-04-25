# pre-mortem-review Specification

## Purpose
TBD - created by archiving change design-first-gate. Update Purpose after archive.
## Requirements
### Requirement: Pre-mortem skill produces structured adversarial review of a plan

The pre-mortem skill SHALL accept either an OpenSpec change name or an inline design description as input, and SHALL produce a structured markdown report with the following sections in this order:

1. **Regression surface** — files and public symbols modified; callers of each modified symbol grepped from `src/` and `tests/`; shared modules involved; cross-references to features/specs that use them.
2. **Hidden assumptions** — statements in the design that depend on invariants, with pointers to where those invariants are (or are not) enforced in the codebase.
3. **Historical echoes** — matching entries from `.wolf/buglog.json` (by tag, file, or keyword) and `.wolf/cerebrum.md` Do-Not-Repeat; empty list stated explicitly if none match.
4. **Alternatives not considered** — at least one concrete alternative approach and a reason it was rejected; if the design already addresses this, the section SHALL say so explicitly.
5. **Test gap** — behaviors that would break silently if the design is wrong; current test coverage of the affected files with pointers to specific test files, or a statement that no tests exist.
6. **Verdict** — exactly one of `ready-to-implement`, `needs-revision`, or `blocked-on-unknowns`, with a one-line reason.

The skill SHALL NOT write or edit any file under `src/`, `.claude/skills/` (other than its own test fixtures), or `CLAUDE.md`. It is a read-and-report skill.

#### Scenario: Invoked against an existing OpenSpec change

- **WHEN** the skill is invoked with the name of a change directory under `openspec/changes/`
- **THEN** the skill SHALL read `proposal.md` and `design.md` from that directory
- **AND** the skill SHALL produce all six sections of the report in order

#### Scenario: Invoked with inline design description

- **WHEN** the skill is invoked with an inline description rather than a change name
- **THEN** the skill SHALL treat the description as the design input
- **AND** the skill SHALL produce the same six-section report

#### Scenario: No historical matches found

- **WHEN** no entries in `.wolf/buglog.json` or `.wolf/cerebrum.md` Do-Not-Repeat match the change
- **THEN** the Historical echoes section SHALL state "No matches found" rather than being omitted

#### Scenario: Design is clearly complete and low-risk

- **WHEN** the skill's analysis finds no gaps, no untouched callers, and no historical echoes
- **THEN** the Verdict SHALL be `ready-to-implement`
- **AND** the one-line reason SHALL cite the specific evidence that supports readiness

### Requirement: Slash command wraps the skill

A slash command `/pre-mortem` SHALL exist at `.claude/commands/pre-mortem.md` and SHALL invoke the pre-mortem skill with the argument provided.

#### Scenario: User types /pre-mortem with a change name

- **WHEN** the user types `/pre-mortem <change-name>`
- **THEN** the slash command SHALL invoke the pre-mortem skill with that change name
- **AND** the skill SHALL resolve the OpenSpec change directory and produce the report

#### Scenario: User types /pre-mortem with no argument

- **WHEN** the user types `/pre-mortem` with no argument
- **THEN** the command SHALL ask the user which change or design to review
- **AND** the command SHALL NOT attempt to run the skill until input is provided

### Requirement: Pre-mortem is complementary to code review, not redundant

The pre-mortem skill SHALL operate on design artifacts (pre-code) and SHALL NOT replace `/review-diff` or `/ultrareview`, which operate on diffs (post-code). The skill's documentation MUST state this distinction explicitly so users know when to use each.

#### Scenario: User asks which review to run

- **WHEN** the user is uncertain whether to run `/pre-mortem` or `/review-diff`
- **THEN** the skill documentation SHALL make clear that `/pre-mortem` runs before code is written and `/review-diff` runs after
- **AND** running both at their respective stages SHALL be the recommended path for non-trivial changes

