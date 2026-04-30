## Context

### The flailing pattern
The project's generator pipeline is feature-complete: value curves
(`src/generator/value_curves.py`), section transitions
(`src/generator/transitions.py`), and chord color blending
(`src/generator/chord_colors.py`) are wired in and run on every
generation. None are disabled stubs. Yet the user describes output as
"dim, lifeless, wrong effects on wrong props, boring, repetitive." The
disconnect is not missing code; it's missing measurement.

The existing evaluation harness (`src/evaluation/`) measures regression:
does the new code produce the same placements as the old code? It does
not measure quality. The `tests/golden/baseline.json` is a structural
snapshot.

### The framing: nothing is ground truth yet
This is the load-bearing constraint. We cannot validate whether any
quality metric is right because we have no rendered-output reference
against which to validate it. Two existing artifacts each *claim* to
encode what's good:

1. `src/effects/builtin_effects.json:prop_suitability` — a
   hand-curated map per effect with values
   `{ideal, good, possible, not_recommended}` per prop type
   (`{matrix, outline, arch, vertical, tree, radial}`).
2. The user's intuition + community lore that certain pairings (Plasma
   on a 1D outline, Bars on a radial spinner) "obviously look bad."

These two sources **disagree on most pairings the user reaches for
first**. The catalog says Plasma on outline is `possible` and Fire on
outline is `good`; the lore says both are bad. Neither has been
validated against rendered video. Picking one as truth in v1 would
smuggle in an unearned ground-truth claim and bias every downstream
metric.

The microscope's design therefore:
- Computes both signals and reports them side-by-side.
- Adds a `pairing_disagreement_pct` so the magnitude of the
  catalog-vs-handlist gap is itself a number.
- Strips phenomenon-implying language ("breathing", "violation") from
  metric names and descriptions until rendered-output observation says
  otherwise.
- Defers committing a golden baseline until sensitivity tests confirm
  each metric moves under predictable interventions.

### Building on what exists
`src/evaluation/xsq_reader.py` already parses an XSQ into a
`SequenceSummary` containing `Placement` objects with `effect_type`,
`model_name`, `palette_colors`, `start_ms`, `end_ms`, and
`layer_index`. The metric registry
(`src/evaluation/metrics/__init__.py`) already exposes `register()` +
`get_registry()`. New metric modules plug in like the existing ones.

The microscope runner is not a new pipeline — it calls
`generate_sequence()` from `src/generator/plan.py` (the same function
the CLI's `generate` command calls), parses the output XSQ, then
computes metrics.

## Goals / Non-Goals

**Goals:**
- Emit a per-song `metrics.json` with all new metrics plus existing
  registered ones.
- Run across a 4-song panel in one command so no single song is
  treated as truth.
- Compare current metrics against a committed golden — but only after
  sensitivity tests prove each metric is responsive.
- Be fast enough that a developer runs it between commits (~3-5 min
  per song; ~20 min full panel).
- Be deterministic given pinned `variation_seed`. Verify by re-running
  with the same seed and asserting zero deltas.

**Non-goals:**
- FSEQ rendering or MP4 output.
- Fixing the quality problems the metrics surface (Phase B).
- Replacing `xlight-evaluate gate`.
- Running in CI.
- Picking a winner between hand-list and catalog before either is
  validated against rendered output.
- Adding more metrics than listed.

## Design

### Extending the prop-type inference vocabulary

`src/evaluation/xsq_reader.py:_PROP_TYPE_TOKENS` currently matches
`{snowflake, outline, candy, matrix, arch, tree, star, deer, house,
mega}` against the lowercased model name. The catalog uses
`{matrix, outline, arch, vertical, tree, radial}`. Intersection: 4
(`matrix`, `outline`, `arch`, `tree`).

**Token-ordering rule (forward-looking, not retroactive).** Tokens
are matched in list order; the first match wins. *New tokens added
by this change* SHALL be inserted at positions that follow the rule
"longest token first; ties broken alphabetically." Existing token
order is preserved as-is to avoid changing any current inference
result. Reordering pre-existing tokens is out of scope.

Append two tokens at the positions the rule indicates:
```python
_PROP_TYPE_TOKENS: list[tuple[str, str]] = [
    ("snowflake", "snowflake"),
    ("vertical", "vertical"),  # NEW (length 8 — placed before length-7 `outline`)
    ("outline", "outline"),
    ("candy", "candy"),
    ("matrix", "matrix"),
    ("radial", "radial"),      # NEW (length 6 — placed after length-6 `matrix` for alphabetical tiebreak)
    ("arch", "arch"),
    ("tree", "tree"),
    ("star", "star"),
    ("deer", "deer"),
    ("house", "house"),
    ("mega", "mega"),
]
```

This is **purely additive** for every existing model name: neither
`vertical` nor `radial` was previously in the list, so no current
inference result changes. Specifically: `MegaTree.lower() = "megatree"`
matches `tree` first (existing behaviour, kept) — `mega` is at the
tail of the list. The reference layout's renamed `RadialSpinner`
relies on `radial` being in the list, but does not depend on its
position relative to `tree`/`star` (no collision exists).

### New metric modules

#### `src/evaluation/metrics/vitality.py`

Two metrics. **Names use the `palette_luminance_*` form, not
`brightness_proxy_*`** — these are computed from palette hex values, not
rendered light.

**`palette_luminance_mean`** (scalar, duration-weighted)
- For each `Placement`, parse `palette_colors` (already tuples of
  `#RRGGBB` strings).
- Compute Rec.601 luma per color: `L = 0.299*R + 0.587*G + 0.114*B`,
  range 0–255.
- Per-placement: mean luminance of active colors.
- Across all placements: duration-weighted mean.
- Range 0–255. No claimed "typical good range" — the baseline is
  whatever the corpus produces today.
- Direction-of-good: **unknown until validated**. Registered with
  `higher_is_better=None`; the diff tool prints "↑/↓" without
  improvement claims until calibrated.

**`palette_luminance_cv`** (scalar, **also duration-weighted** —
matched to `palette_luminance_mean` so the two describe the same
population)
- Same per-placement luminance as above.
- Compute the duration-weighted std-dev / duration-weighted mean across
  per-placement luminances.
- No "breathing happening" claim — that interpretation is what we're
  measuring against, not asserting.
- Direction-of-good: **unknown**, `higher_is_better=None`.

#### `src/evaluation/metrics/suitability.py`

Six metrics. Three variety + three fit (handlist, catalog,
disagreement).

**`distinct_effect_count`** (scalar)
- Count unique non-"Unknown" `effect_type` values.
- Direction-of-good: **unknown**, `higher_is_better=None`. (More
  variety might be busy/distracting; the user hasn't said.)

**`effect_repeat_rate`** (scalar 0.0–1.0)
- For each `(model_name, effect_type)` pair, fraction of placements
  occurring within 30s of a previous matching placement on the same
  model.
- Window size parameterised via
  `audio_context.get("repeat_window_ms", 30_000)`.
- Direction-of-good: **plausibly lower-is-better** but not validated
  — `higher_is_better=False` (provisional; flagged in metric
  description as "user-stated preference, not validated").

**`per_prop_type_diversity`** (structured + scalar)
- Group placements by inferred prop type. Per type, count distinct
  `effect_type` values. Structured payload `{by_type: {...},
  min_diversity: int}`; scalar = min diversity.
- Direction-of-good: **unknown**, `higher_is_better=None`.

**`bad_pairing_pct_handlist`** (scalar 0.0–1.0)
- Define `HANDLIST_BAD_PAIRINGS: dict[str, set[str]]` in
  `suitability.py` — short list of widely-claimed-bad combinations.
  *Documented as opinion*, not fact. The initial list is a
  first-principles draft; **the user has explicitly NOT validated it
  against rendered output**. The first measured value of
  `pairing_disagreement_pct` on the corpus is the cue to revise this
  dict (or to revise the catalog), not to treat either as truth.
  ```python
  # INITIAL DRAFT — not validated against rendered output. First-principles
  # guesses about pairings that "obviously look wrong" on each prop type.
  # Disagrees with src/effects/builtin_effects.json:prop_suitability on
  # most entries; both signals are computed in parallel and
  # `pairing_disagreement_pct` surfaces the gap. Revise this dict (or the
  # catalog) only after the first corpus measurement says the
  # disagreement is concentrated somewhere actionable.
  HANDLIST_BAD_PAIRINGS = {
      "Plasma":        {"outline", "arch"},
      "Pinwheel":      {"outline", "arch"},
      "Single Strand": {"matrix"},
      "Bars":          {"radial"},
      "Fire":          {"arch", "outline"},
      "Butterfly":     {"outline", "arch"},
  }
  ```
- For each placement: if `inferred_prop_types[model_name]` is in the
  effect's bad set, count it. Skip Unknown prop types.
- Direction-of-good: `higher_is_better=False`, **flagged as
  unvalidated** in the metric definition's description.

**`bad_pairing_pct_catalog`** (scalar 0.0–1.0)
- Load `src/effects/builtin_effects.json` once. For each placement,
  look up `effects[effect_type].prop_suitability[prop_type]`. Count it
  if the value is `"not_recommended"`. Skip if any of `effect_type`,
  `prop_type`, or the suitability key is missing.
- Direction-of-good: `higher_is_better=False`, **also flagged as
  unvalidated**.

**`pairing_disagreement_pct`** (scalar 0.0–1.0)
- For each placement where both signals can produce a result (both
  effect and prop type are known to both sources), count if exactly
  one of `bad_pairing_pct_handlist` and `bad_pairing_pct_catalog`
  flagged it.
- Returns the fraction of evaluable placements where the two sources
  disagree. **This is the headline number for the "we have no ground
  truth" framing** — when it's high, neither signal is trustworthy on
  its own.
- Direction-of-good: **unknown** (some disagreement is healthy; we
  don't know what level is OK), `higher_is_better=None`.

### `MetricDefinition` extension

Add an `Optional[bool]` `higher_is_better` field:
```python
@dataclass(frozen=True)
class MetricDefinition:
    ...
    higher_is_better: Optional[bool] = None  # None = direction unknown
```
- `None` = direction-of-good not established; diff tool prints `↑/↓`
  without `✓/✗`.
- `True/False` = direction known; diff tool prints `↑✓/↓✗` etc.

The default is `None` — *not* `True`. A `True` default would silently
add improvement claims to every metric the moment it's registered.

Existing metric registrations stay valid (the field is keyword-only and
optional). Audit task in tasks.md sets explicit values where defensible
and leaves the rest at `None`.

### The structured-vs-scalar distinction

`per_prop_type_diversity` returns a structured payload but registers
its scalar summary (min diversity) as the directional metric.
`effect_type_histogram` (existing in `effects.py`) is purely
structured — it has no scalar, so `higher_is_better` does not apply
and the registration must omit it. The diff tool skips structured
metrics that lack a scalar summary instead of trying to render
direction arrows over a histogram.

### New module: `src/microscope/`

#### `src/microscope/__init__.py` — empty marker.

#### `src/microscope/runner.py`

```python
@dataclass(frozen=True)
class MicroscopeResult:
    slug: str
    audio_path: str
    xsq_path: str
    summary: SequenceSummary
    metrics: dict[str, MetricResult]
    generated_at: str  # ISO 8601 UTC
    config_snapshot: dict  # non-path GenerationConfig fields, including variation_seed

def run_song(audio_path, layout_path, output_dir, config_overrides) -> MicroscopeResult
```

1. Build `GenerationConfig` with production defaults
   (`curves_mode="none"`, `transition_mode="subtle"`, `genre="pop"`,
   `occasion="general"`) **plus an explicit `variation_seed=42`** so
   determinism doesn't drift on rerun. **Note**: `GenerationConfig`
   does not have a `variation_seed` field today — the seed lives on
   per-section `ThemeAssignment` objects in
   `src/generator/models.py`. This change adds
   `variation_seed: int = 42` to `GenerationConfig` and threads it
   through `theme_selector.py` so each `ThemeAssignment` is
   constructed with `variation_seed=config.variation_seed +
   section_index`. This is ~10 lines of plumbing, scoped to this
   change.
2. Apply `config_overrides`.
3. Call `generate_sequence(config)` → output XSQ path.
4. Parse XSQ with `xsq_reader.parse_xsq(xsq_path)` → `SequenceSummary`.
5. Import vitality + suitability + existing metric modules.
6. Compute all registered metrics via the registry dispatcher.
7. Return `MicroscopeResult`.

XSQ retained at `output_dir/microscope/<slug>/sequence.xsq`.

#### `src/microscope/panel.py`

```python
def run_panel(manifest_path, layout_path, output_dir, config_overrides,
              parallel=False) -> list[MicroscopeResult]
```

Panel manifest schema:
```json
{
  "schema_version": 1,
  "description": "Reference panel for microscope visual quality measurement",
  "cc0_manifest": "tests/fixtures/cc0_music/manifest.json",
  "slugs": ["funshine", "maple_leaf_rag", "nostalgic_piano", "space_ambience"],
  "layout": "tests/fixtures/reference/layout.xml"
}
```

MP3 path resolution: check `tests/fixtures/cc0_music/<slug>.mp3`. If
missing, call `tests.validation.download_fixtures.download_all()` (the
function that exists) once for the run and look up the result by slug.
A future task may factor a per-slug `ensure_fixture(slug)` helper, but
this change does not depend on that — it uses the existing batch API.

`parallel=True` uses `concurrent.futures.ProcessPoolExecutor(max_workers=3)`.

#### `src/microscope/diff.py`

```python
@dataclass
class DiffReport:
    rows: list[DiffRow]
    def format_table(self) -> str: ...

def diff_results(current: list[MicroscopeResult], baseline_dir: Path) -> DiffReport
```

For each `(song, metric)`:
- Load `baseline_dir/<slug>/baseline.json`.
- Compute `absolute_delta = current - baseline`,
  `relative_pct = (current - baseline) / baseline * 100` (guarded for
  baseline=0).
- Direction arrow:
  - `higher_is_better=None` → `↑` or `↓` only, no claim.
  - `higher_is_better=True` → `↑✓` (improved) / `↓✗` (regressed).
  - `higher_is_better=False` → inverted.
- Missing baseline: row says `NEW`. Missing current metric: `MISSING`.
- Structured-only metrics (no scalar summary) are excluded from the
  diff table.

### CLI: `xlight-evaluate microscope`

The microscope is a quality-measurement tool that consumes the
`src/evaluation/metrics/` registry. All other "compute scalar metrics
from a corpus" commands (`gate`, `check`, `compare`, `snapshot*`) live
under `xlight-evaluate`. Putting `microscope` in the same CLI is
consistent with that grouping.

Subcommand group `microscope` registered on `xlight-evaluate`:

- **`xlight-evaluate microscope run <song.mp3>`**
  Options: `--layout`, `--output-dir`, `--curves-mode`, `--baseline`,
  `--variation-seed`. Runs `run_song()`, prints metric table, writes
  `metrics.json`. With `--baseline`, also prints diff.

- **`xlight-evaluate microscope panel`**
  Options: `--manifest`, `--layout`, `--output-dir`, `--parallel`,
  `--baseline`, `--variation-seed`. Runs `run_panel()`, prints per-song
  tables + aggregate summary.

- **`xlight-evaluate microscope baseline`**
  Options: `--input-dir`, `--golden-dir`. Copies `metrics.json` files
  to the golden dir. Prints `git add + commit` instructions. **Refuses
  to run if sensitivity tests have not been recorded for the current
  metric set** (see "Sensitivity gate" below). The staleness check
  runs `git log -1 --format=%ct -- <staleness-cone>` and compares
  against the `run_at` timestamp recorded in
  `tests/golden/microscope/sensitivity_passed.json`. The cone is the
  three paths that feed into metric output:
  - `src/evaluation/metrics/`
  - `src/evaluation/xsq_reader.py` (prop-type inference affects
    pairing metrics)
  - `src/effects/builtin_effects.json` (catalog feeds
    `bad_pairing_pct_catalog`)

### Reference panel + layout

`tests/fixtures/reference/panel_manifest.json` — 4 CC0 songs:
`funshine` (96 BPM pop-funk), `maple_leaf_rag` (99 BPM ragtime),
`nostalgic_piano` (59 BPM piano), `space_ambience` (140 BPM ambient).

`tests/fixtures/reference/layout.xml` — model names rewritten so
`_infer_prop_type` produces the prop type the metric expects on every
prop. Mapping:

| Old name | New name | Token | Prop type |
|---|---|---|---|
| MatrixCenter | MatrixCenter | `matrix` | `matrix` |
| MegaTree | MegaTree | `mega` (matched first) | `mega` |
| TreeLeft | TreeLeft | `tree` | `tree` |
| TreeRight | TreeRight | `tree` | `tree` |
| ArchLeft | ArchLeft | `arch` | `arch` |
| ArchRight | ArchRight | `arch` | `arch` |
| RooflineLeft | **OutlineRoofLeft** | `outline` | `outline` |
| RooflineRight | **OutlineRoofRight** | `outline` | `outline` |
| StarSpinner | **RadialSpinner** | `radial` (after token addition) | `radial` |

Note: `MegaTree` matches `mega` before `tree` because of token order;
that's an existing inference quirk, unrelated to this change. The
layout comment is corrected to acknowledge it.

Total prop count is **9** (count it). Layout XML comment updated to
match. Coverage: 5 of 6 catalog types (`matrix`, `outline`, `arch`,
`tree`, `radial`). `vertical` is intentionally absent — the catalog
treats it identically to other 1D types and we don't have a real
vertical prop in the user's xLights install. This is documented as a
known gap, not silently dropped.

### Sensitivity gate (NEW — task §8)

Before any baseline is committed, prove each metric moves in the
predicted direction under known interventions. The
`baseline` CLI subcommand reads
`tests/golden/microscope/sensitivity_passed.json` (written by a new
`xlight-evaluate microscope sensitivity` subcommand) and refuses to
write a golden baseline if the file is missing or stale.

Sensitivity probes:
1. **Single-effect override** — force every placement to a single
   effect via a `config_override`. Expect `distinct_effect_count → 1`,
   `effect_repeat_rate → ~1.0`.
2. **All-black palette override** — force placements to a palette of
   only `#000000`. Expect `palette_luminance_mean → 0`,
   `palette_luminance_cv → 0`.
3. **All-known-bad-pairing override** — force every placement to
   `Plasma` on a model with `outline` prop type. Expect both
   `bad_pairing_pct_handlist` and `bad_pairing_pct_catalog` to move
   in the same direction; the actual *values* may differ (which is the
   finding).
4. **Variation-seed sweep** — re-run with the same seed and assert
   zero delta on every metric (deterministic). Re-run with a flipped
   seed and assert at least one metric moves (the seed has effect).

If any probe fails, the metric or its registration is wrong and the
golden cannot be committed.

## Regression surface

**New files (no callers to update):**
- `src/evaluation/metrics/vitality.py`
- `src/evaluation/metrics/suitability.py`
- `src/microscope/__init__.py`
- `src/microscope/runner.py`
- `src/microscope/panel.py`
- `src/microscope/diff.py`
- `src/microscope/sensitivity.py` (new — drives the sensitivity gate)
- `tests/fixtures/reference/panel_manifest.json`
- `tests/golden/microscope/<slug>/baseline.json` (×4, written only
  after sensitivity passes)
- `tests/golden/microscope/sensitivity_passed.json` (gates baseline
  writes)

**Modified files:**
- `src/cli/evaluate.py` — register the `microscope` subcommand group.
  Existing subcommands untouched.
- `src/evaluation/metrics/__init__.py` — add
  `higher_is_better: Optional[bool] = None` to `MetricDefinition`.
  Default `None` keeps every existing registration semantically
  unchanged (no improvement claim added implicitly).
- `src/evaluation/xsq_reader.py:_PROP_TYPE_TOKENS` — append `radial`
  and `vertical` entries. Additive; existing inferences unchanged.
- `tests/fixtures/reference/layout.xml` — rename Roofline → Outline*
  and StarSpinner → RadialSpinner.

**Callers of `MetricDefinition` (audited; none break):**
- `src/evaluation/metrics/effects.py` — no `higher_is_better` value
  passed today; remains `None`. Future PR (Phase B) sets it once the
  scalar component (e.g., `unknown_effect_fraction`) is split off
  cleanly from the structured `effect_type_histogram`.
- `src/evaluation/metrics/pacing.py`,
  `src/evaluation/metrics/palette.py`,
  `src/evaluation/metrics/alignment.py`,
  `src/evaluation/metrics/sections.py`,
  `src/evaluation/metrics/internal.py` — same; `None` until validated.

## Historical echoes

From `.wolf/buglog.json`: no entries matching `microscope`,
`vitality`, `suitability`, `bad_pairing`, or `palette_luminance`. No
precedent.

From `docs/segment-classification-changelog.md`: not relevant.

From `.wolf/cerebrum.md` Do-Not-Repeat:
- "[2026-04-19] Applied symptom fixes instead of root-cause fixes" —
  relevant. This change is the opposite: build measurement before
  fixes.
- "[2026-04-19] Did more or less than what was asked" — relevant.
  Scope is intentionally narrow.

From this PR's own review (#141): every concrete ask in the
"Concrete asks before approval" list of the bobbyfriday review on
2026-04-30 is addressed in the revisions above. Specifically:
1. PR retitled and body rewritten to reflect spec-only.
2. `bad_pairing_pct` split into handlist + catalog +
   disagreement signals.
3. Layout model names + `_PROP_TYPE_TOKENS` aligned so all 6
   bad-pairing rules can fire.
4. `ensure_fixture(slug)` reference replaced with `download_all()`
   (the function that exists).
5. `brightness_proxy_*` → `palette_luminance_*`; "breathing"
   interpretation stripped.
6. Sensitivity gate added to tasks before §8 commits a golden.
7. CLI moved from `xlight-analyze microscope` to `xlight-evaluate
   microscope`.

## Alternatives considered

**Alternative A: Build metrics on the SequencePlan object directly.**
- Pro: richer data (tier assignments, theme names, group_density).
- Con: bypasses the serialization layer; bugs in `xsq_writer.py` are
  invisible to the microscope.
- Rejected: the XSQ is what users load into xLights. Metrics must
  validate the actual artifact.

**Alternative B (REVISED — was the plan): `xlight-analyze microscope`.**
- Pro: fits the "analyze a song" mental model.
- Con: `xlight-analyze` is for producing/exporting analysis output
  (analyze, summary, export, review, generate). The microscope
  produces *scalar quality metrics*, which is what `xlight-evaluate`
  already does (gate, check, compare, snapshot*). Splitting evaluation
  across two CLIs doubles the surface for no UX gain.
- **Rejected**: putting it in `xlight-evaluate` keeps all metric-
  computing commands in one place. The only mental-model argument for
  `xlight-analyze` was "you point it at a song" — but
  `xlight-evaluate compare` already takes a per-song target, so the
  precedent exists.

**Alternative C: FSEQ rendering and per-frame pixel metrics.**
- Pro: measures exactly what xLights renders.
- Con: requires xLights running; no programmatic FSEQ renderer in this
  codebase.
- Rejected for v1: XSQ palette-derived proxies are imperfect but
  available now. FSEQ rendering is the validation step that *would*
  let us pick a winner between handlist and catalog — explicit future
  work, not a prerequisite.

**Alternative D: Pick one of (handlist, catalog) as truth and use it
for `bad_pairing_pct`.**
- Pro: single metric, simpler diff table.
- Con: smuggles in an unearned ground-truth claim. Picking the
  catalog says "the JSON file is right" without evidence; picking the
  handlist says "user lore is right" without evidence.
- **Rejected**: if either source were validated, this would be the
  right move. Until then, the disagreement *is* the finding and must
  be visible in every report.
