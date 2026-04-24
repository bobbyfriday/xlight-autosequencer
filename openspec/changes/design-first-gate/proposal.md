## Why

Claude currently jumps from user requests into implementation too quickly. This produces two recurring pains:

1. **Shallow analysis.** Ideas aren't stress-tested from multiple angles before code is written, so designs miss edges and alternatives.
2. **Silent regressions.** Changes land without enumerating their blast radius, so working features break when shared modules (`src/analyzer/`, `src/effects/`, `src/generator/`, `src/review/`, `src/themes/` — each imported by 32–86 files outside itself) are modified.

The OpenSpec artifacts (proposal / design / tasks) already exist but are optional. Writing them doesn't guarantee adversarial review of the plan. `/review-diff` and `/ultrareview` catch flaws in code — there is no equivalent that catches flaws in *plans* before code is written.

## What Changes

- Add a **design-first gate** to `CLAUDE.md`: for any change beyond a single-file bug fix, Claude must produce a design artifact, enumerate the regression surface, list at least one rejected alternative, and consult `.wolf/buglog.json` + `.wolf/cerebrum.md` Do-Not-Repeat before writing code. User approval required before implementation.
- Add a **trivial-path carve-out** so small fixes don't pay the overhead (one-file changes under a size threshold, with a stated root cause, can proceed).
- Add a new **`pre-mortem` skill** at `.claude/skills/pre-mortem/SKILL.md` that takes an OpenSpec change (or an inline design) and produces an adversarial review: regression surface, hidden assumptions, historical echoes from bug/cerebrum logs, unconsidered alternatives, and test gaps.
- Add a thin **slash command** (`/pre-mortem <change-name>`) that invokes the skill against an existing OpenSpec change directory.

Non-goals: no new agent hierarchy, no multi-agent orchestration, no changes to the implementation workflow itself.

## Capabilities

### New Capabilities
- `design-gate`: the behavioral rule set that governs when Claude is allowed to begin implementation, what artifacts are required first, and the carve-out for trivial changes.
- `pre-mortem-review`: the adversarial planning review — the skill that reads a design and produces a structured pre-implementation critique (regression surface, assumptions, historical echoes, alternatives, test gaps).

### Modified Capabilities
<!-- None — no existing specs under openspec/specs/ to modify. -->

## Impact

- **Files modified**: `CLAUDE.md` (add gate section + trivial-path carve-out).
- **Files added**: `.claude/skills/pre-mortem/SKILL.md`, `.claude/commands/pre-mortem.md` (slash command wrapper), `openspec/specs/design-gate/spec.md`, `openspec/specs/pre-mortem-review/spec.md`.
- **No code changes** to `src/` — this is a process/tooling change.
- **No new runtime dependencies.** The skill runs via existing Claude Code harness; the CLI already has `openspec`, `grep`, and `git`.
- **Behavioral impact on Claude**: for non-trivial changes Claude will pause to produce design artifacts and request approval before editing code. Users who want to move fast on a small fix still can via the carve-out.
- **Risk**: design theater (thorough-looking but shallow designs). Mitigated by the `pre-mortem` skill stress-testing the design itself.
- **Risk**: friction on small changes. Mitigated by the carve-out; if it proves too noisy, the threshold is a single knob to tune.
