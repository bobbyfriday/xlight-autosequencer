# Cache-key audit — 2026-04-26

Comprehensive audit of every module-level / closure-scoped cache in `src/`
to find any keyed by an unstable identity (CPython `id()` of a mutable
object, or any other key that may collide across logical inputs).

The audit was triggered by the bug found in PR #102 in
`src/analyzer/algorithms/librosa_bands.py`: the STFT cache was keyed by
`(id(audio), sample_rate)`. CPython readily reuses freed memory addresses,
so a second fixture analyzed in the same process could collide with a
stale entry from the first and read back the wrong STFT (3-6× event-count
drift on bass/mid/treble between snapshot runs).

This document inventories every cache discovered, classifies it as
**SAFE** or **FIX**, and explains why.

## Method

```bash
git grep -nE "id\(" -- 'src/*.py'
git grep -nE "(_cache|cache_key)" -- 'src/*.py'
git grep -rnE "lru_cache|@cache\b|cached_property" --include="*.py" src/
git grep -nE "^_[a-zA-Z_]*[Cc]ache" --include="*.py" src/
git grep -rnE "dict\[int," --include="*.py" src/
```

For each hit:
1. Classify as cache (yes/no).
2. If cache: what is the key? Is the key stable across logical calls,
   or stable only across the lifetime of the keyed objects?
3. If unstable: fix.

## Inventory

### Caches keyed by `id()` of a Python object

| # | Site | Key | Lifetime | Verdict |
| - | ---- | --- | -------- | ------- |
| 1 | `src/analyzer/algorithms/librosa_bands.py:21` `_stft_cache` | `(len, sr, ndim, 3 sampled values)` | module-level (process-wide) | **FIXED in PR #102** — was `(id(audio), sr)`, now content fingerprint. |
| 2 | `src/analyzer/selector.py:75,78,82,85,87,103,106,110,113,115` `cvs / norm_corrs` | `id(track)` | function scope; `candidates` list keeps every track alive throughout | **SAFE** — `id()` cannot be recycled while the keyed object is alive in `candidates`. Content fingerprint would *incorrectly* collapse content-equal-but-distinct candidates. |
| 3 | `src/generator/xsq_writer.py:275,281,383` `placement_cache` | `id(placement)` | function scope; `all_placements` dict holds every placement throughout | **SAFE** — same reasoning as #2. Placements are alive in `all_placements` for the entire `write_xsq()` call. |

### Module-level caches keyed by content / path / hash

| # | Site | Key | Verdict |
| - | ---- | --- | ------- |
| 4 | `src/review/server.py:21` `_library_md5_cache` | `(path_str, mtime_ns, size)` | **SAFE** — file-content based; touched-but-unchanged files reuse, modified files recompute. |
| 5 | `src/review/preview_routes.py:37` `_preview_cache` | `(song_hash, section_index, brief_hash)` | **SAFE** — content-derived strings. |
| 6 | `src/review/theme_routes.py:100` `_builtin_names_cache` | (no key — singleton lazy-init) | **SAFE** — single immutable load from disk. |
| 7 | `src/analyzer/orchestrator.py:53,73` `_load_cache` / `_write_cache` | `(audio_path, source_hash)` on disk | **SAFE** — content-hash keyed. |
| 8 | `src/analyzer/runner.py:84` `_resample_cache` | stem name (e.g. `"drums"`) | **SAFE** — function-local dict, freshly created per `analyze()` call; tied to the call's `StemSet`. |
| 9 | `src/analyzer/cross_song_tuner.py:532` `stem_cache` | stem name | **SAFE** — function-local. |
| 10 | `src/analyzer/sweep_matrix.py:412` `stem_cache` | stem name | **SAFE** — function-local. |
| 11 | `src/analyzer/stems.py` `StemCache` | source-content hash on disk | **SAFE** — content-hash keyed. |
| 12 | `src/review/api/v1/library.py` `_analysis_cache_path / _stems_cache_path` | `song_id` (which is itself a content hash) | **SAFE**. |

### `lru_cache` / `cached_property` / `functools.cache`

None present in `src/`. (`grep -rnE "lru_cache|@cache\b|cached_property"` returned no hits.)
This is the highest-risk pattern for id-collision bugs (an `lru_cache` that
takes a mutable arg silently keys by hashable surrogate, but the caller may
not realise the cache survives), so its absence is reassuring.

### `id()` calls in non-cache contexts (false positives from grep)

* `src/cli/evaluate.py:313` — comment in help text, not a cache.
* `src/review/api/v1/analysis.py:53,571` `_run_id()` — generates a UUID
  string, not an `id()` call on an object.
* `src/review/api/v1/export.py:50` `_export_id()` — UUID generator.
* `src/review/api/v1/library.py:37` `_generate_folder_id()` — UUID.
* `src/cache.py:105,140` — `is_valid()` method calls, false hit on
  the regex `id(`.

## Findings

* **id()-keyed caches that needed fixing: 0** (the librosa_bands one was
  already fixed in PR #102, before this audit).
* **id()-keyed caches that are safe: 2** (`selector.py`, `xsq_writer.py`)
  — both function-scoped with all keyed objects held alive in a
  surrounding container. Documented above so future readers don't
  reflexively "fix" them and accidentally collapse content-equal-but-
  distinct entries.
* **No `lru_cache` or `cached_property` decorators** anywhere in `src/`.

## Buglog echoes

`grep` of `.wolf/buglog.json` and `.wolf/cerebrum.md` for "cache",
"stft", "fingerprint", "librosa_bands", "id(" produced no prior entries
matching this bug class. The PR #102 incident was the first time this
pattern was identified in the project. A new buglog entry covering the
class (id-collision in numpy-array-keyed module caches) is added in this
PR so future sessions find the precedent.

## Test additions

* `tests/unit/test_librosa_bands_cache.py` — six regression tests that
  pin the content-fingerprint behaviour of `_audio_fingerprint` and
  `_get_stft_and_freqs`, including a simulation of the id-recycle
  scenario (free arr1, gc, allocate arr2 of different shape, verify
  the cache returns content-correct STFT for arr2).

## Determinism re-check

Not required: no algorithm-cache code was modified by this PR (only a
test file and this audit doc were added). The librosa_bands fingerprint
was already in place before this branch was cut; no analyzer behaviour
changed.
