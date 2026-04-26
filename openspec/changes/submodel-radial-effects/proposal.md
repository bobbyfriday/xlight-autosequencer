# SubModel-Aware Radial Effects (PR #8 of show-improvement plan)

## Goal

Light Custom-model rings (Ring 1 → Ring 2 → Ring 3) on the beat instead of
flashing the whole flake/gingerbread/snowflake as one solid blob.

## Why

The user's `xlights_rgbeffects.xml` defines Custom models with `<subModel>`
children that group pixels into named regions ("Ring 1", "Ring 2", "Ring 3",
"Spoke 1"…). Today `src/grouper/layout.py:88` parses subModel **names** into
`Prop.sub_models: list[str]` and the generator never targets them — every
Custom prop fires as one solid blob. The dense-sample analysis in the
parent plan flagged this as "custom flakes lighting as one solid blob
(subModels unused)."

Promoting subModels to first-class effect targets unlocks visibly radial
patterns (a "blooming" sequence inner→middle→outer) without touching any
other prop type.

## Scope

In:
- Parse `<subModel ... line0="..." line1="..."/>` pixel-range attributes.
- New `SubModel` dataclass on `Prop`, replacing the `list[str]` field.
- A new tier-6 PROP power group per Custom prop whose subModels match the
  `Ring \d+` (or `Spoke \d+`) pattern, with each ring as a chase target.
- One new variant JSON wired into the rotation pool for that group.
- Unit + integration tests covering parsing, grouping, and placement.

Out (deferred):
- Generic per-subModel addressing for non-radial subModels (Eyes / Mouth on
  singing faces, Window panes, etc.) — only `Ring N` / `Spoke N` patterns
  are recognised in this PR.
- `WorldPosX/Y/Z` offset support for nested subModels — the current
  generator doesn't use subModel positions for any decision.
- UI changes (review-page subModel visualisation).
- The verify_suggestion video render (orchestrator handles that after merge).

## Approach

1. **Parsing.** Add `parse_pixel_ranges(s) -> tuple[int, ...]` (handles mixed
   "1-13", "1,14,17", "95-96,94,1,14,16-15"). Replace `Prop.sub_models:
   list[str]` with `Prop.sub_models: list[SubModel]` where
   `SubModel(name, pixel_indices: tuple[int, ...])`. Update the call-sites
   that still treat it as a list of names.

2. **Grouper.** New tier-6 helper `_tier6_radial_subgroups(props)` emits one
   `PowerGroup` per Custom prop whose subModels match `^Ring \d+$` or
   `^Spoke \d+$`. The group's `members` list is the **fully-qualified
   subModel addresses** (`"Snowflake 1/Ring 1"`, …) in radial order.

3. **xsq writer.** No schema change needed — `Element name=` already accepts
   `Parent/SubModel` paths (xLights convention). The writer already emits
   `Per Model Default` buffer style for tier ≥ 4 which renders each member
   independently.

4. **Variant.** New `Single Strand.json` variant `"Radial Bloom"` — a
   center-out fireworks chase. Combined with the radial-chase placer it
   sequences Ring 1, 2, 3, … on successive beats.

5. **Wiring.** Add a `_place_radial_chase_on_subgroup` helper to
   `effect_placer.py` and dispatch to it from the existing tier-6 entry
   points (rotation_plan path and WorkingSet/pool fallback) when the group
   has `prop_type == "radial"`.

### Alternative considered

**Sub-groups as a `PowerGroup.sub_groups: list[SubGroup]` field.** This
matches the prompt's hint and would keep one parent group with nested
sub-groups, requiring the placer to learn a new "expand sub-groups into
chase targets" path. Rejected: it doubles the surface area (two ways to
represent a group of effect targets), and the existing chase placer can
already do this work member-by-member if we model each subModel address as
a member of a flat PowerGroup. The fully-qualified-name convention
(`"Parent/SubModel"`) is already how xLights addresses subModels — no new
abstraction needed downstream.

## Files touched

| Path | Change |
|---|---|
| `src/grouper/layout.py` | M — `SubModel` dataclass; `parse_pixel_ranges`; replace `Prop.sub_models` |
| `src/grouper/grouper.py` | M — new `_tier6_radial_subgroups`, called from `generate_groups` |
| `src/grouper/classifier.py` | M — line 143 reads `sub_models` as list of strings; update to use `.name` |
| `src/generator/effect_placer.py` | M — new `_place_radial_chase_on_subgroup`, dispatched from tier-6 entry points |
| `src/variants/builtins/Single Strand.json` | M — append "Radial Bloom" variant |
| `tests/unit/test_grouper_layout.py` | M — adapt fixtures to SubModel |
| `tests/unit/test_grouper_classifier.py` | M — adapt fixtures |
| `tests/unit/test_submodel_parsing.py` | A — new |
| `tests/unit/test_grouper_submodels.py` | A — new |
| `tests/integration/test_radial_effect.py` | A — new |
| `openspec/changes/submodel-radial-effects/{proposal,design,tasks}.md` | A |

## Regression surface

`Prop.sub_models` callers (grep `src/` + `tests/`):

| Caller | Use today | Action |
|---|---|---|
| `src/grouper/layout.py` | Construction | Updated |
| `src/grouper/classifier.py:143` | `members = p.sub_models if p.sub_models else [p.name]` | Update to `[f"{p.name}/{sm.name}" for sm in p.sub_models]` |
| `src/validation/scenarios.py:59-94` | `sub_models=[]` literals | Still valid (empty list satisfies new type) |
| `tests/unit/test_grouper_classifier.py:21,101,115,136` | `sub_models=["Eyes", "Mouth"]` style | Update fixtures to use `[SubModel("Eyes",())]` |
| `tests/unit/test_grouper_layout.py:52-61` | Asserts names in list | Update asserts |
| `tests/unit/test_grouper_groups.py:22,273,280` | `sub_models=[]` literals | No change |
| `tests/unit/test_symmetry.py:26` | `sub_models=[]` literal | No change |
| `tests/unit/test_generator/test_plan.py`, `tests/integration/*`, `tests/validation/*` | `sub_models=[]` literals | No change |

`PowerGroup` has 162 references. None inspect a `members` element to assert
it's a top-level prop name (vs. a `Parent/SubModel` path). The xsq writer
writes group names directly as `<Element name>` — subModels work because
xLights honors `Parent/SubModel` paths there.

`generate_groups` callers (cli_old, generator_wizard, editor, preview,
plan x2, server) — none care about new tier-6 entries; they iterate.

Shared modules touched per CLAUDE.md: `src/grouper/`, `src/generator/`,
`src/variants/builtins/`. All require the design gate; this proposal is it.

## Historical echoes

- `.wolf/buglog.json`: 0 entries match `submodel`, `sub_model`, `grouper`,
  `tier 6`, `PowerGroup`, `Custom`, `flake`. No prior fixes to echo.
- `.wolf/cerebrum.md`: 0 entries match the same terms.
- `~/.claude/.../MEMORY.md`: nothing relevant.
- The plan file (`merry-gliding-hedgehog.md`) explicitly calls this out
  as the largest of the 10 PRs and warns it crosses a different shared
  module than the other 9 — estimate 1-2 days.

No prior failed attempts found.
