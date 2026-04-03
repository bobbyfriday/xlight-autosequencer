# Unaddressed Review Items

Items identified during the code and UX review (April 2026) that were **not**
addressed in the current round of improvements. These are tracked here for
future consideration.

---

## Code & Architecture

### Unvalidated Deserialization in result.py
`TimingTrack.from_dict()` and similar methods don't validate input data types.
A malformed JSON with `"confidence": "not_a_float"` silently becomes `None`.
**Suggested fix:** Add pydantic validation or explicit type checking in
`from_dict()` methods. Raise `TypeError` on mismatches.

### Missing Scoring Config Validation
No validation that weights sum to ~1.0, target ranges are valid, or thresholds
are reachable. Users can create invalid profiles producing nonsensical scores.
**Suggested fix:** Add `ScoringConfig.validate()` that checks constraints on load.

### Environment Pollution in Story Builder Subprocess
`src/story/builder.py` passes the entire `os.environ` to the Genius subprocess,
including potentially sensitive API tokens.
**Suggested fix:** Whitelist specific env vars instead of passing entire environ.

### Incomplete Error Propagation in Review Server
Background analysis thread catches all exceptions and sets `job.error_message`
but doesn't log the full traceback. Users only see truncated error text.
**Suggested fix:** Store `traceback.format_exc()` in job state and emit it via
SSE for development/debug mode.

### Weak Abstraction in TimingTrack
`TimingTrack` carries algorithm output, analysis metadata, serialization,
and presentation concerns in one class. Hard to extend.
**Suggested fix (large refactor):** Split into `TimingTrack` (pure data),
`TimingTrackMetadata`, and `TimingTrackView` classes.

### Implicit Module Dependencies
Import chain from `plan -> story/builder -> analyzer/genius_segments ->
analyzer/phonemes -> analyzer/orchestrator -> analyzer/runner` creates tight
coupling and makes isolated testing difficult.
**Suggested fix:** Dependency injection for cross-module callables.

### O(n^2) Peak Detection in Validator
`src/analyzer/validator.py` peak detection iterates all marks without index
optimization. Slow for 10-minute songs with 5000+ marks.
**Suggested fix:** Pre-compute frame indexes, use numpy vectorized operations.

### No Memoization in Cross-Song Tuner
`src/analyzer/cross_song_tuner.py` recomputes statistics across songs on
every call without caching.
**Suggested fix:** `@lru_cache` or explicit memoization with invalidation.

### Circular Import Risk
`src/analyzer/result.py` uses `TYPE_CHECKING` for forward references to
`phonemes` and `structure` modules. Runtime imports would break.
**Suggested fix:** Add CI check for circular imports; use
`from __future__ import annotations` everywhere.

### Memory Overhead in Parallel Runner
Full audio array is shared across ThreadPoolExecutor workers. With 4 workers
on a 5-minute MP3, memory usage can reach 800MB+.
**Suggested fix:** Use `max_workers=2` by default; add memory estimation.

### Numpy Version Constraint
`numpy>=1.24,<2` pins below 2.0 due to vamp/madmom ABI. Blocks numpy 2.0
performance improvements.
**Suggested fix:** Long-term: negotiate with upstream or provide alternatives.

---

## UX & Usability

### Missing Tab Completion
CLI has no bash/zsh completion support. Users must type full command names.
**Suggested fix:** Use Click's built-in completion generation.

### No Dry-Run for Most Commands
`--dry-run` only works for `analyze`. Missing for `export`, `group-layout`,
`sweep`.
**Suggested fix:** Add `--dry-run` flag to export and sweep commands.

### Interactive Track Selection for Export
Export requires exact track name matching. No fuzzy match, interactive
selection, or regex filtering.
**Suggested fix:** Add `--interactive` flag with checklist UI, or `--pattern`
for regex filtering.

### Mobile Responsiveness
Only 1 media query (variant library, 800px). Most pages assume desktop.
**Suggested fix:** Add responsive breakpoints for tablets/phones.

### No Search History or Favorites
Library search is functional but has no history or saved searches.
**Suggested fix:** localStorage-based recent searches, star/favorite button.

### No Playlist/Collection Support
Library is flat with no grouping by artist/album or custom playlists.
**Suggested fix:** Collections sidebar with artist/album grouping.

### No Bulk Operations in Dashboard
Each song managed individually. No multi-select for batch operations.
**Suggested fix:** Checkbox column, "Selected: N" toolbar with bulk actions.

### No Comparison Mode in Timeline
Can only view one song at a time. No side-by-side comparison.
**Suggested fix:** Split view for comparing analyses.

### No Custom Annotations in Timeline
Marks are from algorithms only. Users can't add notes or bookmarks.
**Suggested fix:** User annotation layer with save/load.

### Story Review Flyout Non-Obvious
Flyout panel initially closed, "Accents" button unlabeled.
**Suggested fix:** Visible expand arrow, default-open Details tab, onboarding hint.

### Theme Editor Lacks Visual Preview
No color palette preview, no side-by-side comparison, no "apply to song" button.
**Suggested fix:** Theme preview cards with color swatches and sample effects.

### Variant Library Filters Unexplained
5 filter types with no guidance on what they mean.
**Suggested fix:** Introductory text and quick-reference sidebar.

### Layout Grouping No Clear Success State
No visual indication of grouping coverage or quality.
**Suggested fix:** Coverage indicator showing grouped/ungrouped prop counts.

### No xLights Compatibility Validation
Export generates .xsq files without validating they're valid xLights files.
**Suggested fix:** Pre-export validation against xLights schema.

### JSON Output Opaque to Users
Analysis JSON is 10,000+ lines with no schema documentation for users.
**Suggested fix:** JSON viewer in web UI, `xlight-analyze inspect` command,
schema docs.

### No Analysis Version Diffing
Re-analyzing overwrites previous results with no comparison.
**Suggested fix:** Keep last N analysis runs, show diff between versions.

### No Interactive Onboarding Tour
Web UI has no guided first-use walkthrough.
**Suggested fix:** Step-by-step tooltip tour triggered on first visit.

### No Video/GIF Tutorials
Documentation is text-only.
**Suggested fix:** GIF demos in README, video walkthroughs.

### Long Operations Lack Checkpoint Recovery
If stem separation crashes at 4:50 of 5 min, restart from scratch.
**Suggested fix:** Checkpoint after each stem completes, `--resume` flag.

### No Collaboration Features
No ability to share analyses, add comments, or compare with collaborators.
**Suggested fix:** Export/import analysis bundles, annotation layer.

### No Quality Metrics for Generated Sequences
Generated sequences have no quality feedback.
**Suggested fix:** Post-generation scoring with per-section breakdown.

---

## Inconsistent Patterns (Low Priority)

### Error Message Format Inconsistency
Mix of `WARNING:`, `ERROR:`, `[ERROR]` formats across codebase.
**Status:** Partially addressed (CLI now uses `_rich_error()`). Backend logging
still uses mixed formats.

### Magic Numbers
Constants like 60ms attack windows, 0.6 thresholds scattered without named
constants. Low impact but reduces readability.

### Orchestrator vs Runner vs Pipeline Naming
Unclear responsibilities between `orchestrator.py`, `runner.py`, `pipeline.py`,
and `parallel.py`. Documentation added but code structure unchanged.
