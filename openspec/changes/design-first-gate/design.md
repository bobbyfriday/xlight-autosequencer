## Context

The repo already has extensive process tooling: OpenSpec (`openspec new change`, proposal/design/tasks artifacts), OpenWolf (`.wolf/cerebrum.md`, `.wolf/buglog.json`, `.wolf/anatomy.md`), slash commands (`/review-diff`, `/ultrareview`, `/opsx:propose`, `/opsx:apply`), and a long `CLAUDE.md` with engineering principles and a mandated segment-classification changelog.

Despite all of this, the failure mode observed is that Claude jumps to implementation before the design is stress-tested, and regressions appear because the blast radius of changes wasn't enumerated. The root cause is **behavioral, not tooling**: nothing in `CLAUDE.md` forces a design phase before code, and no artifact explicitly demands a regression-surface enumeration.

Two changes close this gap:

1. A **gate** in `CLAUDE.md` that makes design-first the default for non-trivial changes.
2. A **pre-mortem skill** that makes it cheap to stress-test a design by running an adversarial pass over it.

## Goals / Non-Goals

**Goals:**

- Prevent Claude from starting implementation on non-trivial changes without a written design + regression surface + approval.
- Make multi-angle critique of plans a single skill invocation rather than ad-hoc prompting.
- Keep small, obviously-correct fixes moving without friction via a clear carve-out.
- Reuse existing tooling (OpenSpec, OpenWolf logs, slash commands) rather than inventing parallel structures.

**Non-Goals:**

- Not introducing multi-agent orchestration, peer-review agent swarms, or background worker fleets (discussed and rejected in the prior exploration — coordination overhead typically exceeds benefit for this workload).
- Not changing the implementation or review workflow (`/review-diff`, `/ultrareview`) itself.
- Not replacing OpenSpec — the gate *uses* OpenSpec as the canonical design artifact for non-trivial work.
- Not touching `src/` or any product code.

## Decisions

### 1. The gate lives in `CLAUDE.md`, not a hook

**Decision:** Add a "Design-First Gate" section to `CLAUDE.md` (before "Engineering Principles"). The gate is enforced by Claude reading and respecting it, not by a shell hook that blocks tool calls.

**Why X over Y:**
- A hook that refuses `Edit`/`Write` unless a design.md exists was considered. Rejected because (a) it fights the carve-out for trivial fixes — a hook can't easily judge "is this a one-file bug fix?", (b) hooks block tool calls at the harness level, producing cryptic failures rather than thoughtful behavior, and (c) the user has shown willingness to maintain process rules in `CLAUDE.md` already.
- A standalone `DESIGN_GATE.md` was considered. Rejected because `CLAUDE.md` is always loaded into context; a separate file would need a pointer that might be ignored.

### 2. Trivial-path carve-out uses objective criteria, not judgment

**Decision:** The carve-out qualifies a change as trivial when ALL of:
- Modifies a single file
- Fewer than ~30 lines changed
- A one-sentence root-cause statement is given
- No changes to public APIs, CLI flags, JSON/XML schema fields, or shared modules (`src/analyzer/`, `src/effects/`, `src/generator/`, `src/review/`, `src/themes/` — the modules each imported by 32+ files outside themselves, confirmed via grep at proposal time)

If any condition fails, the full gate applies.

**Why objective criteria:** "Use judgment" rules are ignored under action-bias. Hard lines are the only ones that survive.

### 3. Pre-mortem skill output is a structured markdown report

**Decision:** The skill outputs a single markdown block with fixed sections:
- **Regression surface** — files and symbols touched; grep results for callers of each modified public symbol; shared modules involved; features cross-referenced from `specs/`.
- **Hidden assumptions** — statements in the design that depend on invariants; where those invariants are (or aren't) enforced.
- **Historical echoes** — matching entries from `.wolf/buglog.json` (by tag/file/keyword) and `.wolf/cerebrum.md` Do-Not-Repeat.
- **Alternatives not considered** — at least one concrete alternative and a reason it was rejected; if the design already covers this, the section says so.
- **Test gap** — behaviors that would break silently if the design is wrong; current test coverage of the affected files.
- **Verdict** — `ready-to-implement` | `needs-revision` | `blocked-on-unknowns`, with a one-line reason.

**Why fixed structure:** Adversarial review agents drift toward generic nits when given free rein. Fixed sections force them to populate each lens.

### 4. The skill is invokable both standalone and from a slash command

**Decision:** `.claude/skills/pre-mortem/SKILL.md` is the substantive definition. `.claude/commands/pre-mortem.md` is a one-line wrapper so users can type `/pre-mortem <change-name>`. The skill accepts either an OpenSpec change name (reads `openspec/changes/<name>/proposal.md` + `design.md`) or an inline description.

**Why both:** Slash command is the ergonomic entry point. The skill is the reusable unit — other skills (or future workflows) can invoke it without the CLI layer.

### 5. The gate requires explicit user approval before implementation

**Decision:** After producing the design artifacts, Claude states "Ready for pre-mortem" or "Ready to implement" and waits for the user. It does not auto-proceed, even if the design looks complete.

**Why:** The failure mode being fixed is Claude acting before the user signs off on direction. Removing the approval step reintroduces the problem.

## Risks / Trade-offs

- **Design theater** → Mitigated by the pre-mortem skill's fixed-structure output, which forces each lens to be populated rather than hand-waved. If theater persists, strengthen the skill's rubric rather than the gate.
- **Friction on small changes** → Mitigated by the trivial-path carve-out. If the carve-out is still too strict and users disable the gate within days, loosen the criteria (e.g., raise line threshold) rather than remove the gate.
- **Gate ignored under urgency** → If the user explicitly overrides the gate ("just do it"), Claude should comply but note the skipped gate in the session summary. This keeps the gate from becoming a wall the user must fight.
- **Pre-mortem produces false alarms** → The `verdict` field lets the skill be confident when a change is genuinely simple. If alarms dominate signal, tune the skill's rubric — do not remove the verdict.
- **Duplication with `/review-diff`** → The two reviews are at different stages (pre-code vs post-code) and use different inputs (design doc vs diff). They are complementary, not redundant. Document this explicitly in the skill.
- **Trivial-path criteria are over/under-strict on day one** → Expected. Plan to revisit the criteria after ~10 real changes and adjust.

## Migration Plan

1. Land the `CLAUDE.md` gate and the skill together in a single PR. Landing them separately risks a window where the gate refers to a skill that doesn't exist.
2. No backfill needed — change proposals already in flight can continue under their existing artifacts.
3. If the gate proves net-negative, revert is a single `CLAUDE.md` section deletion and file removal under `.claude/skills/pre-mortem/` and `.claude/commands/pre-mortem.md`. No code or data migrations.

## Open Questions

- Should the gate block or merely warn on `.wolf/buglog.json` historical matches? (Recommendation: warn, include match in design output. Blocking is too strong; the user may have reason to retry.)
- Should the pre-mortem skill auto-run at the end of `/opsx:propose`, or stay manual? (Recommendation: manual for now — adding it to `/opsx:propose` couples two workflows before either is validated.)
- How should the gate interact with `/opsx:apply`? (Recommendation: the gate is satisfied by the existence of proposal/design/tasks + user approval; `/opsx:apply` is one way to reach that state, not the only way.)
