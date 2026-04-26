# Tasks: ethereal active_tiers restoration

- [x] Trace root cause via grep + git log -S; confirm `_compute_active_tiers` returns `{8}` for ethereal
- [x] Read PR #77 (commit 9d6a2c48) — the change that removed Tier 1
- [x] Confirm scope: `_compute_active_tiers` has one call site, one import, no test imports
- [ ] Modify `src/generator/effect_placer.py:1788` to return `frozenset({1, 8})` for ethereal
- [ ] Update the comment block above the change to cite this PR + describe the trade-off
- [ ] Add `tests/unit/test_active_tiers_ethereal.py` covering all three mood branches
- [ ] Run `pytest tests/unit/ -k tier` locally; confirm green
- [ ] Run `pytest tests/integration/test_generate_integration.py` locally; confirm green
- [ ] Commit with structured message + co-author
- [ ] Push branch + open PR with body referencing the design doc and the empirical FSEQ data
