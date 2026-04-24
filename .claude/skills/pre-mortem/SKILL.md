---
name: pre-mortem
description: Adversarial review of a design BEFORE implementation. Reads an OpenSpec change (proposal + design) or an inline design description and produces a structured six-section report that stress-tests the plan for regression surface, hidden assumptions, historical echoes, unconsidered alternatives, and test gaps — ending with a verdict. Use before writing code on any non-trivial change, especially when shared modules (src/analyzer, src/effects, src/generator, src/review, src/themes) are touched. Complements /review-diff and /ultrareview which review post-code diffs.
license: MIT
metadata:
  author: xlight-autosequencer
  version: "1.0"
---

Run an adversarial pass over a design **before** implementation. The goal is to
catch flaws while they are still cheap to fix — in the plan, not in committed code.

This skill is **read-only**. It MUST NOT write or edit files under `src/`,
`.claude/skills/`, `CLAUDE.md`, or any project code. It only reads and reports.

---

## Input

One of:

- **OpenSpec change name** (preferred): the skill reads
  `openspec/changes/<name>/proposal.md` and `openspec/changes/<name>/design.md`
  if they exist, plus any `specs/**/*.md` under that directory.
- **Inline design description**: a free-form text description of the proposed
  change. Treated the same way as a design.md for analysis purposes.

If both are provided, prefer the OpenSpec change (it is more structured). If
neither is resolvable, ask the user which design to review — do not fabricate one.

---

## Output — six fixed sections, in this order

The output is a single markdown block. Each section MUST be populated. If a
section genuinely has nothing to report, state that explicitly ("No matches found",
"No assumptions identified") — do NOT omit the section.

### 1. Regression surface

List, for the change:

- **Files to be modified / added / removed** — specific paths, with the operation.
- **Public symbols affected** — module-level functions, class methods, CLI flags,
  JSON/XML schema fields that are added, removed, or change signature.
- **Callers found** — for each modified public symbol, grep callers from `src/`
  and `tests/`. List them with file paths. State which are updated by the design
  and which are expected to be untouched (and why that's safe).
- **Shared modules involved** — flag any touch of `src/analyzer/`, `src/effects/`,
  `src/generator/`, `src/review/`, `src/themes/`. These are high-blast-radius.
- **Cross-feature references** — if the design cross-references feature numbers
  (e.g., "built on feature 034"), verify the referenced spec or module still
  exists and flag any drift.

**Example shape:**

```
### 1. Regression surface

Files:
- MODIFY src/generator/plan.py (lines ~40–120, _build_effect_pool)
- ADD src/generator/prop_affinity.py
- MODIFY tests/unit/test_plan.py

Public symbols changed:
- src/generator/plan.py::_build_effect_pool — signature: added `prop_type` arg.
  Callers grepped (`grep -r _build_effect_pool src/ tests/`):
  - src/generator/builder.py:L201 — UPDATED in design
  - src/generator/builder.py:L340 — UPDATED in design
  - tests/unit/test_plan.py — UPDATED in design
  All 3 callers accounted for.

Shared modules touched:
- src/generator/ — HIGH RISK (44 importers outside the module).

Cross-feature references:
- Design cites feature 041 (prop-type affinity). Verified:
  openspec/specs/041 does not exist — feature 041 lives only in CLAUDE.md
  "Active Technologies". Note: no spec to validate against.
```

### 2. Hidden assumptions

List statements in the design that depend on invariants or conditions not
explicitly enforced. For each, point to where the invariant is (or is NOT)
enforced in code. Examples of assumptions worth flagging:

- "X is always non-empty" — is there a guard?
- "Y is called before Z" — is ordering enforced or incidental?
- "All entries in `foo.json` have field `bar`" — is there a schema check?
- Timing assumptions (async order, cache warm, file exists on disk)
- Invariants maintained by convention rather than code

If no load-bearing assumptions are found, state that explicitly.

### 3. Historical echoes

Scan `.wolf/buglog.json` and `.wolf/cerebrum.md` for matches.

**`.wolf/buglog.json`** has the shape `{"bugs": [{"id": "bug-NNN", "tags": [...],
"file": "...", "error_message": "...", "root_cause": "...", "fix": "..."}, ...]}`.
At time of writing it contains ~121 entries. Match on:

- `tags` overlap with the change's topic keywords
- `file` in the design's "files touched" list
- Keyword-in-`error_message` or keyword-in-`root_cause`

For each match, cite the `id`, summarize the prior `root_cause` and `fix`, and
state whether the current design reuses, avoids, or diverges from that approach.

**`.wolf/cerebrum.md`** — scan the `## Do-Not-Repeat` section for matches on files
or topics in the design. Cite any matching entry by its first line.

Matches are **warnings, not blockers**. The design is free to deliberately
revisit an earlier approach; it just has to do so knowingly.

If no matches, state "No matches found in buglog.json or cerebrum Do-Not-Repeat".

### 4. Alternatives not considered

The design must contain at least one rejected alternative with a rationale.
Check whether it does. If it does:

- State that the alternatives section is present and summarize what was considered.
- Propose at least one *additional* alternative the design did not mention, and
  give a one-sentence reason it might be worth considering.

If the design has no alternatives section:

- Propose at least two plausible alternatives with one-sentence rationales each.
- Flag the missing section as a required revision before implementation.

### 5. Test gap

- List behaviors that would break silently if the design is wrong. These are
  the behaviors most in need of test coverage.
- For each affected file, identify existing tests (grep `tests/unit/test_<name>.py`,
  `tests/integration/`, etc.). Report coverage as present / partial / absent.
- If the change adds new behavior, state whether the design's `tasks.md`
  includes a test for it. If not, flag as **NO REGRESSION TEST**.

### 6. Verdict

Exactly one of:

- **`ready-to-implement`** — no significant gaps; regression surface is enumerated
  and small; no historical echoes or the design addresses them; alternatives
  considered; test plan exists. One-line reason citing the specific evidence.
- **`needs-revision`** — gaps are fixable by updating the design (missing
  regression-surface entries, missing alternative rationale, untested behavior,
  unresolved historical echo). List the specific revisions needed.
- **`blocked-on-unknowns`** — fundamental questions about scope or approach
  remain. List the open questions that must be answered before a design can
  proceed.

The verdict MUST be followed by a one-line rationale citing the specific
evidence that drove it. Do not hedge.

---

## Relationship to other reviews

| When              | Tool              | Reviews what |
|-------------------|-------------------|--------------|
| Before code       | `/pre-mortem`     | The design artifact (proposal.md + design.md) |
| After code, local | `/review-diff`    | The committed diff vs main |
| After code, cloud | `/ultrareview`    | Multi-agent adversarial review of the branch |

For non-trivial changes the recommended path is: **pre-mortem → implement →
review-diff**. The three reviews operate on different inputs and catch different
classes of defect — they are complementary, not redundant.

---

## Guardrails

- **Read-only.** No tool calls that write to project files. You may write
  temporary scratch notes to `/tmp/` if needed, but not to the repo.
- **No design repair.** If the design is incomplete, the verdict is
  `needs-revision` — do NOT edit the design artifact yourself.
- **Ground every claim in a concrete file, line, or grep result.** Do not
  produce vague findings like "this might interact with the analyzer" — either
  name the file and function or drop the finding.
- **No rubber-stamping.** If the analysis genuinely finds nothing wrong, say so
  with `ready-to-implement` and cite the evidence. But confirm the evidence —
  silence is not the same as verification.
- **Stay in scope.** Review the design you are given. Do not propose scope
  expansions unless the design's goal cannot be met without them (and say so
  explicitly if that's the case).
