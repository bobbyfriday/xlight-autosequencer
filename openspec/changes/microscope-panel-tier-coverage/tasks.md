## 1. Research — find candidate fixtures

- [ ] 1.1 Identify a candidate CC0 song expected to trigger **tier 6 PROP** (structural mood + weak phrase periodicity). Likely sources: Free Music Archive, Wikimedia Commons. Filter for non-4/4 / poly-meter / through-composed pieces 90-180s long.
- [ ] 1.2 Identify a candidate for **tier 1 BASE** (sustained ethereal mood — slow, atmospheric, no strong rhythmic structure). 90-180s.
- [ ] 1.3 Identify a candidate for **tier 2 GEO call-response density** (structural mood with strong bar-locked phrase periodicity). 90-180s.
- [ ] 1.4 Verify each candidate's license: page must explicitly declare CC0 (or equivalent — Public Domain Mark). Record the license URL alongside the song URL.
- [ ] 1.5 For each candidate, run `xlight-evaluate microscope run <candidate.mp3> --output-dir microscope-out-research/<slug>` and inspect `tier_placement_breakdown.payload.active_tiers`. Accept only if it includes the target tier.
- [ ] 1.6 Record the research outcome in `docs/microscope-tier-effectiveness.md` (append a "Fixture research log" section): each candidate evaluated, target tier, observed tiers, accept/reject + reason. Negative results stay logged.

## 2. Manifest plumbing — accept tier_intent

- [ ] 2.1 Update `src/microscope/panel.py` to accept either string or `{slug, tier_intent}` object entries in the manifest's `slugs` array. Validate at load time; raise `ValueError` on malformed entries (missing `slug`, non-list `tier_intent`).
- [ ] 2.2 Extend `MicroscopeResult` (or a sibling field on the panel-level result) so each per-fixture result carries its declared `tier_intent`. Default to empty list when absent.
- [ ] 2.3 Add unit tests `tests/microscope/test_panel_manifest_intent.py` covering: legacy string slug → empty intent; object slug → intent populated; malformed entry → `ValueError` with the offending key/slug named.

## 3. verify-coverage subcommand

- [ ] 3.1 Create `src/microscope/verify.py` with `verify_panel_coverage(manifest_path, output_dir) -> VerifyReport` returning per-fixture pass/fail and a global verdict.
- [ ] 3.2 Add `xlight-evaluate microscope verify-coverage --manifest --output-dir` subcommand in `src/cli/microscope.py`. Exit codes: 0 success, 2 manifest/output-dir error, 6 coverage regression.
- [ ] 3.3 Tests `tests/microscope/test_verify_coverage.py`: all-fixtures-pass case; one-fixture-missing-tier case; manifest-malformed case; output-dir-missing case; required-tier-has-no-fixture case.
- [ ] 3.4 Document the subcommand in CLAUDE.md alongside the existing four microscope commands.

## 4. Add the new fixtures

- [ ] 4.1 Add accepted candidates from §1 to `tests/fixtures/cc0_music/manifest.json` with URL, sha256, and license URL.
- [ ] 4.2 Add slugs to `tests/fixtures/reference/panel_manifest.json` and `panel_manifest_matrix.json` as object entries with `tier_intent` populated.
- [ ] 4.3 Verify each new fixture downloads cleanly and the existing analysis pipeline succeeds against it.

## 5. Re-baseline both panels

- [ ] 5.1 Run `xlight-evaluate microscope panel` on the default and matrix panels with the expanded slug list. (`metric_set_hash` is unchanged from main, so `microscope sensitivity` does NOT need a re-run unless main has shifted in the meantime.)
- [ ] 5.2 Promote new baselines: `microscope baseline` for both panels.
- [ ] 5.3 Verify zero deltas on a follow-up `microscope panel --baseline` run.
- [ ] 5.4 Run `xlight-evaluate microscope verify-coverage` on both panels — must exit 0.

## 6. Documentation + commit

- [ ] 6.1 Update `docs/microscope-tier-effectiveness.md` with the post-expansion tier coverage matrix (which tiers are now reachable) and the verdict on whether further redesign is needed.
- [ ] 6.2 Confirm `pytest tests/evaluation/ tests/microscope/ tests/cli/` is green.
- [ ] 6.3 PR body should call out: (a) which fixtures were added, (b) which tier each one targets, (c) any tiers that were targeted but rejected (negative results), (d) whether the diagnostic data still motivates a tier-activation redesign.
