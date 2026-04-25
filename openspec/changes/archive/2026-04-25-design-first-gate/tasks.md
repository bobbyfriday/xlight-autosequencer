## 1. CLAUDE.md gate

- [x] 1.1 Add a "Design-First Gate" section to `CLAUDE.md`, placed immediately before "Engineering Principles"
- [x] 1.2 Document the four objective criteria for the trivial-path carve-out (single file, <30 lines, stated root cause, no shared-module or public-API touch)
- [x] 1.3 List the shared modules that always require the full gate (`src/analyzer/`, `src/effects/`, `src/generator/`, `src/review/`, `src/themes/` — the 5 modules each imported by 32+ files outside themselves, per grep at 2026-04-24)
- [x] 1.4 Document the required contents of the design artifact: goal, approach, files touched, alternatives considered, regression surface, historical echoes from buglog/cerebrum
- [x] 1.5 State the explicit-override rule (user can say "just do it"; Claude complies and notes the override in the end-of-session summary)
- [x] 1.6 Cross-reference the pre-mortem skill so the gate points users to it for stress-testing designs

## 2. Pre-mortem skill

- [x] 2.1 Create `.claude/skills/pre-mortem/SKILL.md` with frontmatter (name, description, license) matching the style of other skills under `.claude/skills/`
- [x] 2.2 Define the skill's input contract: either an OpenSpec change name (resolved to `openspec/changes/<name>/`) or an inline design description
- [x] 2.3 Define the skill's output contract: the six fixed sections in order (Regression surface, Hidden assumptions, Historical echoes, Alternatives not considered, Test gap, Verdict)
- [x] 2.4 Document the skill's read-only posture: it MUST NOT edit files under `src/`, `.claude/skills/`, or `CLAUDE.md`
- [x] 2.5 Specify the Verdict values (`ready-to-implement`, `needs-revision`, `blocked-on-unknowns`) and when each applies
- [x] 2.6 Include worked examples of the Regression-surface and Historical-echoes sections so the skill produces consistent output. For Historical echoes, the skill queries `.wolf/buglog.json` which has shape `{"bugs": [...]}` (121 entries at time of writing); match against `tags`, `file`, and keyword-in-`error_message` / `root_cause`. Report matches as a warning with bug ID, not a blocker.
- [x] 2.7 State the complementarity with `/review-diff` and `/ultrareview` explicitly

## 3. Slash command wrapper

- [x] 3.1 Create `.claude/commands/pre-mortem.md` as a thin wrapper that invokes the pre-mortem skill with the user's argument
- [x] 3.2 Handle the no-argument case: prompt the user for which change or design to review before invoking the skill

## 4. Validation

- [x] 4.1 Run `/pre-mortem design-first-gate` against this change's own artifacts as a self-check; iterate on the skill until its output on this change is useful and non-trivial
- [x] 4.2 Verify that `CLAUDE.md` remains under the length at which prior sections start getting truncated in context (spot-check with a long session)
- [x] 4.3 Confirm that `openspec validate design-first-gate --strict` (or equivalent) passes after all artifacts are in place

## 5. Documentation

- [x] 5.1 Add a one-line entry to `.wolf/anatomy.md` for each new file (`.claude/skills/pre-mortem/SKILL.md`, `.claude/commands/pre-mortem.md`)
- [x] 5.2 Append a session note to `.wolf/memory.md` describing the new gate so future sessions pick it up from context
- [x] 5.3 Add a `## Key Learnings` entry to `.wolf/cerebrum.md` capturing the design-first default and the carve-out criteria
