## Why

The diagnostic at `docs/microscope-tier-effectiveness.md` (PR #155) showed
that the four-fixture microscope panel exercises only three of the
generator's eight tiers — `08_HERO`, occasionally `04_BEAT`, and
sparingly `02_GEO`. Tiers `01_BASE`, `03_TYPE`, `05_TEX`, `06_PROP`, and
`07_COMP` receive zero placements across all four fixtures. Two recent
dogfood attempts (weighted suitability, fade-out exploration) had no
panel signal because the code paths they targeted are unreachable on
the current corpus.

The cheap path to fix this is fixture engineering: pick a small set of
additional CC0 songs whose mood/energy profiles are known to activate
the dormant tiers, register them in the panel manifests, baseline.
This unblocks tier-level dogfood work without touching generator
internals — and gives any future redesign of `_compute_active_tiers`
something concrete to measure against.

## What Changes

- Add 3-4 CC0 fixtures to `tests/fixtures/cc0_music/manifest.json`,
  each chosen to exercise a different tier-activation path:
  - **`structural-no-phrase`** — a song with structural sections that
    don't have strong bar-locked phrase periodicity. Targets
    **tier 6 PROP**.
  - **`ethereal`** — a slow/atmospheric song with ethereal-mood
    sections. Targets **tier 1 BASE** and isolates **tier 8 HERO** in
    its quiet-section form.
  - **`structural-phrase`** — a song with structural sections AND
    strong phrase structure. Targets **tier 2 GEO call-response** at
    higher density than the existing fixtures.
  - **`aggressive-rhythmic`** (optional, may already be covered by
    `nostalgic_piano`) — a high-energy song with sustained
    aggressive-mood sections. Targets **tier 4 BEAT** for fuller
    coverage.

- Extend the panel manifest schema with a per-fixture
  **`tier_intent: list[str]`** field that documents which tiers each
  fixture is meant to exercise (e.g.,
  `["08_HERO", "06_PROP"]`). Used by the verification step and as
  reviewer-facing documentation; does not change generation behavior.

- Add a verification gate `xlight-evaluate microscope verify-coverage`
  that fails if any fixture's actual tier breakdown
  (`tier_placement_breakdown` payload) doesn't include every tier
  listed in its `tier_intent`. Surfaces fixture-rot if a future song
  re-analysis (e.g., classifier change) drifts the mood routing.

- Re-baseline both panels with the expanded fixture set. The
  `metric_set_hash` is unchanged (no new metrics) — only the
  per-slug `baseline.json` files grow.

## Capabilities

### New Capabilities
- `microscope-panel-tier-coverage`: the expanded fixture set, the
  `tier_intent` manifest field, and the verify-coverage gate.

### Modified Capabilities
None. The existing `microscope-placement-coverage` capability is
untouched; coverage remains computed the same way and stays
backward-compatible with old panel manifests (missing `tier_intent`
defaults to empty / "no expectation").

## Impact

**Code touched**
- `tests/fixtures/cc0_music/manifest.json` — new fixture entries
  (URL + checksum + license metadata).
- `tests/fixtures/reference/panel_manifest.json` and
  `panel_manifest_matrix.json` — new slugs, optional
  `tier_intent` field per slug.
- `src/microscope/panel.py` — read and propagate `tier_intent` (no
  generation impact; it lands on `MicroscopeResult` for the verify
  gate to consume).
- `src/microscope/verify.py` — new module with the verify-coverage
  logic.
- `src/cli/microscope.py` — new `verify-coverage` subcommand.
- `tests/microscope/test_verify_coverage.py` — new file, ~6 tests.
- `tests/golden/microscope/<new-slug>/baseline.json` and matrix
  counterparts — new baselines for each added fixture.

**Out of scope**
- This proposal does **not** redesign tier activation logic or the
  GEO call/response framing. If, after fixture expansion, tiers 6/7
  are still unreachable on the panel, that's an empirical finding
  that would justify a separate design proposal — but only with
  evidence in hand.
- Per-tier directional metrics (e.g., "tier 6 was active but produced
  no placements"). The existing `tier_placement_breakdown` is enough
  to detect this case once fixtures land.
- CI runtime growth. Adding fixtures grows panel run time; if it
  becomes a problem we'll deal with it via parallelism (already
  supported via `--parallel`) or a `--quick` panel subset, not by
  trimming the panel.

**Research dependency**
- This proposal succeeds only if 3-4 CC0 songs can be found whose
  analyzed mood/energy profiles trigger the target tiers. Phase 1 of
  the tasks file is the research step (try candidate songs, observe
  their tier breakdown, accept or reject). If the research finds
  zero songs that trigger tier 6 PROP, that itself is the actionable
  finding — it would mean the gating logic in
  `_compute_active_tiers` is the bottleneck, not fixture coverage,
  and the redesign path becomes the next proposal.
