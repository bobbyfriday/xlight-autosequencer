# Design: SubModel-Aware Radial Effects

## 1. Pixel-range parser

```python
# src/grouper/layout.py
def parse_pixel_ranges(spec: str) -> tuple[int, ...]:
    """Parse an xLights subModel line attribute into 1-indexed pixel indices.

    Tokens are comma-separated; each token is either "N" or "N-M".  Reverse
    ranges ("16-15") are valid in xLights and yield indices in reverse order.
    Whitespace is tolerated; empty tokens are dropped.

    Examples
    --------
    >>> parse_pixel_ranges("1,14,17")
    (1, 14, 17)
    >>> parse_pixel_ranges("1-13")
    (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
    >>> parse_pixel_ranges("95-96,94,1,14,16-15")
    (95, 96, 94, 1, 14, 16, 15)
    """
```

Edge cases:
- Empty / whitespace string → `()`.
- Single-digit range "5-5" → `(5,)`.
- Reverse range "16-15" → `(16, 15)` (xLights uses the order to drive
  effect direction inside the subModel; we preserve it).
- Non-numeric token → raise `ValueError`. No silent swallowing.

## 2. SubModel dataclass

```python
@dataclass(frozen=True)
class SubModel:
    name: str                         # e.g. "Ring 1"
    pixel_indices: tuple[int, ...]    # 1-indexed, in declaration order
```

Frozen so it can live in sets and be safely shared across PowerGroups.

`Prop.sub_models: list[SubModel]` (was `list[str]`).

`parse_layout` reads each `<subModel>` element. Pixel indices are gathered
by concatenating `line0`, `line1`, `line2`, … in numeric order until an
attribute is missing. For effect-targeting purposes the union is what
matters — declaration order is preserved.

A bad token in user XML logs and skips that line rather than failing the
whole layout load — a single typo shouldn't break loading 80+ models.

## 3. Tier-6 radial sub-groups

```python
# src/grouper/grouper.py
_RADIAL_SUBMODEL_PATTERNS = {
    "Rings":  re.compile(r"^Ring\s*(\d+)$",  re.IGNORECASE),
    "Spokes": re.compile(r"^Spoke\s*(\d+)$", re.IGNORECASE),
    "Arms":   re.compile(r"^Arms?\s*(\d+)$", re.IGNORECASE),
    "Arrows": re.compile(r"^Arrow\s*(\d+)$", re.IGNORECASE),
}
_RADIAL_MIN_MEMBERS = 2

def _tier6_radial_subgroups(props: list[Prop]) -> list[PowerGroup]: ...
```

Behaviour:
- A Custom prop with subModels `Ring 1, Ring 2, Ring 3, Spoke 1..6`
  produces:
  - `06_PROP_<sanitize(name)>_Rings` with 3 members
  - `06_PROP_<sanitize(name)>_Spokes` with 6 members
- Skip threshold: ≥ 2 matching subModels per pattern. A single ring is
  just a flash.
- Sort by integer suffix (1, 2, 10 — not lexicographic).
- Group `prop_type` is set to `"radial"` so existing `prop_suitability`
  filtering routes radial-friendly effects.
- Hooked into `generate_groups` after `_tier6_prop_type`.

Coexistence with existing `_tier6_prop_type`:
- The existing helper groups by **name pattern across props** — all
  "Snowflake" props go in one group (horizontal concept).
- The new helper groups by **subModel pattern within a single prop** —
  different rings of the same flake (vertical concept).
- Both groups can target the same prop without conflict because
  rotation_plan picks a different variant per group, and the xsq writer
  emits independent `<Element>` blocks. The user gets *both*: a
  whole-flake variant on the horizontal group, plus a radial chase on the
  vertical group.

If this turns out to overdraw on the same prop in practice (verified by
the orchestrator's render after merge), we can add a mutual-exclusion
flag in a follow-up. Not solving it now because the verify-suggestion
video is the right place to see whether it overdraws.

## 4. Classifier update (HERO tier)

`src/grouper/classifier.py:143` currently does:

```python
members = p.sub_models if p.sub_models else [p.name]
```

Becomes:

```python
members = (
    [f"{p.name}/{sm.name}" for sm in p.sub_models]
    if p.sub_models else [p.name]
)
```

This is a behaviour change for HERO groups whose underlying prop has
subModels (e.g. a singing face hero). Before: HERO members were the bare
subModel names ("Eyes", "Mouth") which xLights would not resolve. After:
they're fully qualified ("SingingFace/Eyes", "SingingFace/Mouth"). The
new behaviour is correct; the old behaviour is a latent bug exposed by
this change. Tests that asserted the old shape are updated.

## 5. New variant: Radial Bloom

Append to `src/variants/builtins/Single Strand.json`:

```json
{
  "name": "Radial Bloom",
  "base_effect": "Single Strand",
  "description": "Center-out fireworks chase across radial subModels (Ring 1 → 2 → 3). Best on flakes / snowflakes / gingerbread custom models.",
  "parameter_overrides": {
    "E_CHECKBOX_Chase_Group_All": 0,
    "E_CHOICE_Chase_Type1": "From Middle",
    "E_CHOICE_SingleStrand_Colors": "Palette",
    "E_CHOICE_SingleStrand_FX": "Fireworks 1D",
    "E_CHOICE_SingleStrand_FX_Palette": "* Colors Only",
    "E_SLIDER_Color_Mix1": 75,
    "E_SLIDER_FX_Intensity": 160,
    "E_SLIDER_FX_Speed": 160,
    "E_SLIDER_Number_Chases": 1
  },
  "tags": {
    "tier_affinity": "foreground",
    "energy_level": "high",
    "speed_feel": "fast",
    "direction": null,
    "section_roles": ["chorus", "drop", "build"],
    "scope": "group",
    "genre_affinity": "any"
  }
}
```

## 6. Placement wiring

New helper in `src/generator/effect_placer.py`:

```python
def _place_radial_chase_on_subgroup(
    effect_def, layer, group, section, hierarchy, palette, params,
    direction_cycle=None,
) -> list[EffectPlacement]:
    """Sequence a radial group's members on successive beats.

    Beat i fires on members[i % len(members)] so the rings light up in
    declaration order.  Falls back to a single section-span placement on
    the whole group when no beats track is available.
    """
```

Dispatched from the existing tier-6 entry points in `place_effects`:
- The `tier in (5,6,7,8) and rotation_plan is not None` branch
- The `tier in (6,7) and focused_vocabulary` (WorkingSet) branch
- The `tier in (6,7)` pool-fallback branch

In each, when `group.prop_type == "radial"` and `len(group.members) >= 2`,
call the new helper and `continue` instead of falling through to
`_place_effect_on_group`. ~25 lines net. Every other tier-6 caller is
untouched.

## 7. Tests

- `tests/unit/test_submodel_parsing.py` — table test of
  `parse_pixel_ranges` over the cases in §1, including malformed-input
  ValueError.
- `tests/unit/test_grouper_submodels.py` — synthetic Custom prop with
  `Ring 1/2/3` and `Spoke 1..6`; assert two new tier-6 groups appear with
  the right members and prop_type. Negative case: a non-Custom prop or a
  Custom prop with no `Ring N` subModels emits no radial group.
- `tests/integration/test_radial_effect.py` — drive `place_effects` with
  a synthetic radial PowerGroup, the new variant, and a beat track; assert
  the resulting placements alternate `model_or_group` across the rings on
  successive beats.

No video / Docker render — the orchestrator handles that after merge.
