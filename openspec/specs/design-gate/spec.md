# design-gate Specification

## Purpose
TBD - created by archiving change design-first-gate. Update Purpose after archive.
## Requirements
### Requirement: Design-first gate for non-trivial changes

Claude SHALL produce a written design artifact and receive explicit user approval before writing or editing application code, for any change that does not qualify for the trivial-path carve-out.

The design artifact SHALL be either:
- an OpenSpec change directory (`openspec/changes/<name>/` with at least `proposal.md` and `design.md`), OR
- an inline plan posted in the conversation that covers: goal, approach, files to be modified, alternatives considered, and regression surface.

Claude MUST NOT begin implementation — defined as invoking `Edit`, `Write`, or `NotebookEdit` against files under `src/`, `.claude/`, `CLAUDE.md`, or any other project code/config — until the user has acknowledged the design.

#### Scenario: User requests a multi-file feature

- **WHEN** the user asks Claude to add a feature, refactor across modules, or make a change touching more than one file
- **THEN** Claude SHALL produce a design artifact before editing any project file
- **AND** Claude SHALL pause and wait for user approval before proceeding to implementation

#### Scenario: User requests a change to a shared module

- **WHEN** the user asks Claude to modify code under `src/analyzer/`, `src/effects/`, `src/generator/`, `src/review/`, or `src/themes/`
- **THEN** the trivial-path carve-out SHALL NOT apply, regardless of change size
- **AND** Claude SHALL produce a design artifact and request approval before editing

#### Scenario: User explicitly overrides the gate

- **WHEN** the user explicitly instructs Claude to skip the design phase (e.g., "just do it", "don't write a design")
- **THEN** Claude SHALL comply and proceed directly to implementation
- **AND** Claude SHALL note the skipped gate in the end-of-session summary so the override is visible

### Requirement: Trivial-path carve-out

A change SHALL qualify for the trivial-path carve-out and bypass the full design-first gate only when ALL of the following are true:

- The change modifies exactly one file.
- The diff contains fewer than ~30 lines of change (added + removed).
- Claude can state the root cause in one sentence ("X happens because Y").
- The change does NOT modify any public API signature, CLI command or flag, JSON/XML schema field, or file under the shared modules listed above.

For trivial-path changes, Claude MAY proceed directly to implementation after stating the root cause, without producing a design artifact.

#### Scenario: One-line bug fix

- **WHEN** the user reports a bug whose fix is a one-line change in a single leaf module with no public-API impact
- **THEN** Claude MAY state the root cause and apply the fix directly
- **AND** Claude SHALL NOT be required to produce a design artifact

#### Scenario: Small change that touches a shared module

- **WHEN** the change is small but modifies `src/analyzer/`, `src/effects/`, `src/generator/`, `src/review/`, or `src/themes/`
- **THEN** the change SHALL NOT qualify as trivial
- **AND** the full design-first gate SHALL apply

### Requirement: Design artifact must enumerate regression surface

For any change subject to the design-first gate, the design artifact SHALL include an enumeration of:

- Public symbols (module-level functions, class methods, CLI flags, schema fields) that will be added, removed, or changed in signature.
- Files and features that import or depend on the modified symbols, identified by grepping callers under `src/` and `tests/`.
- At least one concrete alternative approach, with a one-sentence rationale for why it was rejected.
- Any relevant entries from `.wolf/buglog.json` or `.wolf/cerebrum.md` Do-Not-Repeat that match the change's files, symbols, or topic.

#### Scenario: Design omits regression surface

- **WHEN** Claude produces a design artifact that does not list caller impact for modified public symbols
- **THEN** Claude SHALL complete the enumeration before requesting approval
- **AND** Claude SHALL NOT proceed to implementation on an incomplete design

#### Scenario: Historical echo found in buglog

- **WHEN** the pre-mortem or design process finds a matching entry in `.wolf/buglog.json`
- **THEN** the design SHALL reference the bug ID and summarize the prior fix
- **AND** the design SHALL explain how the current approach either reuses or deliberately diverges from the prior fix

