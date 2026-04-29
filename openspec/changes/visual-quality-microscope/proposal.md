## Why

The project has been making changes to the generator pipeline for months without being able to prove any change improved the visual quality of the output show. The result is flailing: 40+ commits touching lyric alignment, beat confidence, section boundary refinement, and acceptance gates while the core user complaint — "the rendered show looks dim, repetitive, and doesn't match the props well" — goes unmeasured and unaddressed.

The root problem is not that the code is broken; it's that **there is no feedback loop for visual quality**. The existing acceptance gate (`xlight-evaluate gate`) measures regression against a generator baseline: same placements, same effects, same timing. It cannot measure whether a change made the show *more visually compelling* — brighter, more varied, better matched to prop types, less repetitive. Without that signal, every visual change is guesswork.

## What Changes

- **Add three new metric families** to `src/evaluation/metrics/` that measure visual quality dimensions the existing harness does not cover:
  - **Vitality** — how "alive" is the show? Metrics: mean palette luminance (brightness proxy), coefficient of variation of per-placement luminance (breathing / dynamics).
  - **Variety** — how rich is the effect vocabulary? Metrics: distinct effect count, effect repeat rate within a 30-second window, per-prop-type effect diversity.
  - **Fit** — how well do effects match their props? Metrics: percentage of placements that violate known-bad prop/effect pairings.

- **Add `xlight-analyze microscope` subcommand** — a pipeline command that runs analyze → generate → compute metrics → emit a `metrics.json` report. Takes a single song or a panel directory. On re-run, compares current metrics against a committed golden baseline and prints a delta table so the user can see whether a code change moved the numbers.

- **Create a reference panel** — 5 songs reusing the existing CC0 corpus (4 tracks from `tests/fixtures/cc0_music/manifest.json`) plus the reference layout at `tests/fixtures/reference/layout.xml`. The panel covers genre, tempo, and energy diversity so no single song is overfitted.

- **Commit a golden baseline** — initial `tests/golden/microscope/` directory with per-song `baseline.json` files capturing current metric values. This makes every subsequent run a diff, not a blind number.

Non-goals for this change:
- Fixing the visual quality problems the metrics surface (that is Phase B work, using the microscope as its instrument).
- FSEQ rendering or MP4 video generation (metrics are computed from the SequencePlan / XSQ, not from rendered pixels).
- Replacing or modifying the existing `xlight-evaluate` acceptance gate.
- Prop suitability matrix, layer blending, value-curve tuning, or any generator architecture changes.
- Adding more than 6 new metrics (minimum viable signal; expand after Phase B confirms which ones are diagnostic).

## Capabilities

### New Capabilities
- `visual-quality-microscope`: the `xlight-analyze microscope` subcommand — run the full pipeline on a song or panel, emit a structured metrics report, and diff against a committed golden baseline.
- `vitality-metrics`: two new metrics in `src/evaluation/metrics/vitality.py` measuring brightness proxy and per-placement brightness variation.
- `variety-metrics`: three new metrics in `src/evaluation/metrics/suitability.py` measuring effect-vocabulary richness, repeat rate, and per-prop-type diversity.
- `fit-metrics`: one new metric in `src/evaluation/metrics/suitability.py` measuring bad prop/effect pairing rate against an explicit `OBVIOUSLY_BAD_PAIRINGS` list.

### Modified Capabilities
- `xlight-analyze` CLI: gains a `microscope` subcommand group. Existing commands (`analyze`, `summary`, `export`, `review`, `generate`) are untouched.
- `src/evaluation/metrics/` registry: gains `vitality` and `suitability` metric modules. Existing metrics are untouched.
