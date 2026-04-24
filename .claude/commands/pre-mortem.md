---
description: Adversarial review of a design BEFORE implementation. Reads an OpenSpec change (or inline description) and produces a structured six-section report (regression surface, hidden assumptions, historical echoes, unconsidered alternatives, test gap, verdict). Complements /review-diff.
---

## User Input

```text
$ARGUMENTS
```

The argument is either:
- An **OpenSpec change name** (e.g., `design-first-gate`) — the skill will resolve
  it to `openspec/changes/<name>/` and read `proposal.md`, `design.md`, and any
  `specs/**/*.md`.
- An **inline design description** — free-form text describing the proposed change.

## Preflight

1. If `$ARGUMENTS` is empty:
   - Ask the user: "Which design should I review? Provide an OpenSpec change name
     (e.g., `design-first-gate`) or paste a design description inline."
   - Do NOT attempt to run the skill until input is provided.

2. If `$ARGUMENTS` looks like an OpenSpec change name (matches the name of a
   directory under `openspec/changes/`):
   - Verify the directory exists: `test -d openspec/changes/<name>/`
   - If it does not exist, run `openspec list --json` and suggest the closest
     matches to the user; do NOT invent artifacts.

3. If `$ARGUMENTS` is inline text, use it directly as the design input.

## Execution

Invoke the `pre-mortem` skill with the resolved input. Follow the skill's
contract — produce all six sections (Regression surface, Hidden assumptions,
Historical echoes, Alternatives not considered, Test gap, Verdict), in order,
with concrete `file:line` citations.

## Important

- This command is **read-only**. It must not edit any project file. If the
  design is incomplete, say so in the Verdict (`needs-revision`) and list the
  revisions needed — do NOT edit the design artifact.
- This command reviews the **plan**, not the diff. If the user has already
  written code, point them at `/review-diff` or `/ultrareview` instead.
