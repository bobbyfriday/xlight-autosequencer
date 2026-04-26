# Tasks

## Parsing
- [ ] Add `SubModel` dataclass + `parse_pixel_ranges` in `src/grouper/layout.py`.
- [ ] Update `parse_layout` to populate `Prop.sub_models: list[SubModel]`.
- [ ] `tests/unit/test_submodel_parsing.py` — pixel-range parser cases.

## Grouper
- [ ] `_tier6_radial_subgroups` in `src/grouper/grouper.py`.
- [ ] Wire it into `generate_groups` after the existing tier-6 helper.
- [ ] Set `prop_type="radial"` on the new groups.
- [ ] Update `src/grouper/classifier.py:143` to use `sm.name` and emit
      fully-qualified `Parent/SubModel` member addresses.
- [ ] `tests/unit/test_grouper_submodels.py` — new groups; negative cases.

## Placement
- [ ] Add `_place_radial_chase_on_subgroup` in `src/generator/effect_placer.py`.
- [ ] Dispatch to it from the three tier-6 entry points (rotation_plan,
      WorkingSet, pool fallback) when `group.prop_type == "radial"`.
- [ ] `tests/integration/test_radial_effect.py` — end-to-end placement.

## Variant
- [ ] Append "Radial Bloom" to `src/variants/builtins/Single Strand.json`.

## Test fixture migration
- [ ] Update `tests/unit/test_grouper_classifier.py` fixtures from
      `sub_models=["Eyes", "Mouth"]` to use `SubModel` instances.
- [ ] Update `tests/unit/test_grouper_layout.py` asserts (existing tests
      check name membership; switch to `.name`).
- [ ] `tests/unit/test_grouper_groups.py`, `test_symmetry.py`,
      `validation/scenarios.py` — `sub_models=[]` literals are unchanged.

## Verification (local)
- [ ] `pytest tests/unit/test_grouper_layout.py tests/unit/test_grouper_classifier.py tests/unit/test_grouper_groups.py tests/unit/test_grouper_submodels.py tests/unit/test_submodel_parsing.py tests/integration/test_radial_effect.py -v`
- [ ] `pytest tests/unit/test_generator/test_plan.py -v` (regression).
- [ ] `pytest tests/integration/test_sequence_generation.py -v` (regression).
