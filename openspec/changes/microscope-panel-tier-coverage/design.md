## Context

The microscope panel was sized at four fixtures during the initial
visual-quality-microscope proposal. PR #155's diagnostic showed that
those four fixtures collectively exercise three of eight generator
tiers. The per-tier and per-group breakdown:

| Tier | Default panel | Notes |
|---|---:|---|
| 08_HERO | 89% of placements | Always active |
| 04_BEAT | 9% | nostalgic_piano only |
| 02_GEO | 0.3% | Call/response barely fires |
| 01, 03, 05, 06, 07 | 0% | Never active |

The placer's `_compute_active_tiers` admits one "partition tier" per
section from `{2, 4, 6, 7}` based on `mood_tier`:

- `ethereal` → tier 8 only (HERO)
- `structural` + strong phrase structure → tiers 2, 8 (GEO)
- `structural` + weak phrase structure → tiers 6, 8 (PROP)
- `aggressive` → tiers 4, 8 (BEAT)

So tier 6 PROP is reachable in principle (structural mood without
strong phrase structure), but no current fixture's analysis yields
that combination. The same is true for tier 1 BASE (`_LOW_TIERS` in
single-layer themes — also analysis-driven).

Engineering fixtures to fill this gap is the cheapest action with
the largest leverage. Once we have data showing each tier *can* be
reached, we know whether subsequent generator changes are
measurable — or whether a tier-activation redesign is unavoidable.

## Goals / Non-Goals

**Goals:**
- Add 3-4 CC0 fixtures so each of tiers 1, 2, 4, 6, 8 receives ≥1
  placement on at least one panel song.
- Document fixture intent so reviewers understand why each fixture
  was added.
- Detect fixture rot — if a future analyzer change shifts mood
  routing and a fixture stops triggering its target tier, the panel
  surfaces the regression.

**Non-Goals:**
- Reach tier 7 COMP. The current `_compute_active_tiers` doesn't
  route any mood to tier 7; reaching it requires generator changes
  that are out of scope here.
- Redesign tier activation gating. If fixture engineering fails
  for some target tier, that's a finding for the next proposal,
  not a fix in this one.
- Fixtures designed to stress specific themes / variants /
  parameters. This proposal's axis is **tier coverage**; theme
  coverage is a separate dimension we may want to add later.

## Decisions

### Decision 1: Add fixtures, don't add config knobs

We could expose a `force_mood_tier` field on `GenerationConfig` and
let the panel inject it per fixture. **Rejected** — that adds a
test-only knob to a production config dataclass, and the resulting
"forced mood" generation isn't representative of any real song. The
panel measures what real shows produce; injecting moods would make
the panel measure what mood injection produces.

### Decision 2: `tier_intent` on the manifest, not in code

Each fixture entry in `panel_manifest.json` gains a
`tier_intent: list[str]` (optional, defaults to `[]`). The
verify-coverage gate reads it. Putting intent in the manifest keeps
fixture metadata next to the fixture entry — easy to update, easy
to grep — without any generator-side knowledge of which song should
trigger which tier.

**Alternative considered:** a sidecar markdown file describing each
fixture. **Rejected** — markdown drifts; the verify-coverage gate
can't consume it. JSON-co-located is the lowest-friction option.

### Decision 3: Verify-coverage gate runs on demand, not in CI

The gate is `xlight-evaluate microscope verify-coverage`, run by
developers when they add a fixture or after analyzer changes. It
**doesn't** become part of the cheap CI tier — fixture downloads +
real generation are expensive and we already explicitly keep that
out of CI per the existing acceptance gate doc.

The gate is run locally before opening this proposal's
implementation PR. After that, it becomes a sanity check developers
can run if they suspect mood drift.

### Decision 4: Re-baseline both panels (default + matrix)

Adding fixtures grows both panels' golden directories. The matrix
panel inherits the same fixture list (per existing
`panel_manifest_matrix.json`), so its baseline set must also expand.
No metric values for the existing four fixtures change — `metric_set_hash`
is unchanged, so the existing `sensitivity_passed.json` remains valid.

### Decision 5: Phase 1 (research) is a real phase, not a placeholder

The research step of finding songs that trigger specific moods is a
genuine cost in this proposal — possibly the largest cost. The
tasks file makes that explicit. Each candidate song must:
1. Have a CC0 license verifiable via its hosting page.
2. Pass the existing `download_fixtures.py` flow (URL + sha256).
3. After analysis, exhibit the target mood routing — verified by
   running `microscope run` against it and checking the
   `tier_placement_breakdown` payload.

If a candidate fails any step we discard it and find another. If we
exhaust reasonable candidates without finding one for a given tier
(e.g. tier 6 PROP), we stop, document the negative result, and the
next proposal redesigns the gating.

## Risks / Trade-offs

- **Research dead-end risk**: 3-4 candidate songs may not be enough
  to cover every dormant tier. Mitigation: the proposal's success
  is defined per-tier, not all-or-nothing. Adding even one fixture
  that triggers tier 6 PROP is shippable on its own.
- **Fixture rot**: a future analyzer change could shift mood
  routing on existing fixtures. Mitigation: the verify-coverage
  gate catches this — `tier_intent` becomes the contract.
- **CI runtime**: adding 3-4 fixtures grows panel time by 75-100%.
  Mitigation: panel is not run in CI today; developers run it
  locally with `--parallel`. If a future workflow integrates it,
  we can subset with `--quick`.
- **License compliance**: every CC0 fixture must be verifiable as
  CC0. Mitigation: candidate URL must point to a page (Wikimedia,
  Free Music Archive, OpenGameArt) that explicitly declares CC0;
  the manifest entry records the license URL.
- **Fixture-coordinate collision**: matrix panel reuses the slugs
  with a different layout. If a new fixture's analysis is sensitive
  to layout properties (it shouldn't be — analysis is audio-only)
  we'd see divergent tier breakdowns. Mitigation: `tier_intent`
  applies to both panels; verify gate runs on both.
