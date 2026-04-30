## Why

The project has been making changes to the generator pipeline for months
without being able to prove any change improved the visual quality of
the output show. The result is flailing: 40+ commits touching lyric
alignment, beat confidence, section boundary refinement, and acceptance
gates while the core user complaint — "the rendered show looks dim,
repetitive, and doesn't match the props well" — goes unmeasured.

The root problem is that **there is no feedback loop for visual
quality**. The existing acceptance gate (`xlight-evaluate gate`)
measures *regression*: same placements, same effects, same timing. It
cannot answer "did this change move the show in a direction we believe
to be better?" because we have **no validated ground truth** about what
better even looks like. The hand-coded prop/effect catalog
(`src/effects/builtin_effects.json:prop_suitability`) and any hand-list
of "obviously bad" pairings are both unvalidated opinion until rendered
output corroborates them.

This change builds **measurement infrastructure under the explicit
assumption that nothing is ground truth yet**. Where two opinions exist
about the same thing, we surface both and treat disagreement as the
finding — not as a thing to resolve by picking a winner.

## What Changes

- **Add three new metric families** to `src/evaluation/metrics/`:
  - **Vitality** — mean palette luminance (a *proxy* for brightness;
    not a measurement of rendered light) and the coefficient of
    variation of per-placement luminance.
  - **Variety** — distinct effect count, effect repeat rate within a
    30-second window, per-prop-type effect diversity.
  - **Fit** — *two parallel* "bad pairing" rates plus a disagreement
    rate. We compute both `bad_pairing_pct_handlist` (against an
    explicit short list of widely-claimed-bad pairings) and
    `bad_pairing_pct_catalog` (placements whose
    `effects.json:prop_suitability` value is `not_recommended`),
    plus `pairing_disagreement_pct` for placements where the two
    sources disagree. None of these are framed as "violations" until
    one or the other is validated against rendered output.

- **Add the microscope subcommand to the existing evaluation CLI** —
  `xlight-evaluate microscope` (not `xlight-analyze microscope`; see
  Alternatives in design.md). Runs analyze → generate → compute metrics
  → emit `metrics.json`. Takes a single song or a panel manifest. On
  re-run with `--baseline`, prints a delta table.

- **Create a reference panel** — 4 songs from the existing CC0 corpus
  (`tests/fixtures/cc0_music/manifest.json`) plus the reference layout
  at `tests/fixtures/reference/layout.xml`. The layout is renamed and
  `_PROP_TYPE_TOKENS` is extended so every prop the metrics expect to
  fire on actually surfaces under its intended type.

- **Commit a golden baseline only after sensitivity tests pass** — the
  golden in `tests/golden/microscope/` is meaningless until we've
  verified each metric *moves under known interventions*. Tasks add a
  sensitivity-test phase that must pass before any baseline is
  committed.

- **Extend the prop-type inference vocabulary** — add `radial` and
  `vertical` tokens to `_PROP_TYPE_TOKENS` in
  `src/evaluation/xsq_reader.py` so inference matches the catalog's
  6-type vocabulary instead of the prior 4-type intersection.

Non-goals for this change:
- Fixing the visual quality problems the metrics surface (Phase B).
- FSEQ rendering or MP4 video generation.
- Replacing or modifying the existing `xlight-evaluate gate`.
- Validating either the hand-list or the catalog against rendered
  output (separate work; the microscope is its instrument).
- Treating `higher_is_better` directionality as truth for metrics
  whose direction-of-good is itself unvalidated.
- Adding more than the metrics listed below.

## Capabilities

### New Capability
- `visual-quality-microscope`: the `xlight-evaluate microscope`
  subcommand group plus the supporting metric modules (vitality,
  variety, fit), runner, panel, and diff infrastructure under
  `src/microscope/`.

### Modified Capabilities
- `xlight-evaluate` CLI: gains a `microscope` subcommand group
  (`run`, `panel`, `baseline`). Existing `gate`, `check`, `compare`,
  `snapshot*` are untouched.
- `src/evaluation/metrics/` registry: gains `vitality.py` and
  `suitability.py` modules. Existing metric modules are untouched.
- `src/evaluation/xsq_reader.py`: `_PROP_TYPE_TOKENS` extended with
  `radial` and `vertical`. No behavioural change for existing token
  matches; `Unknown` returns shrink as new tokens cover models that
  previously fell through.
