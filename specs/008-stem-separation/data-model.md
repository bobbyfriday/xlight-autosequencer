# Data Model: Stem Separation

**Branch**: `008-stem-separation` | **Date**: 2026-03-22

---

## Existing Entities — Extensions

### TimingTrack (extended)

Existing entity in `src/analyzer/result.py`. Gains one new field:

| Field | Type | Values | Notes |
|-------|------|--------|-------|
| `stem_source` | `str` | `"drums"`, `"bass"`, `"vocals"`, `"guitar"`, `"piano"`, `"other"`, `"full_mix"` | Set by runner based on algorithm's `preferred_stem`. Defaults to `"full_mix"` when stem separation is not used. |

**Serialization**: Added to the existing JSON output as a top-level field on each track object.

---

## New Entities

### StemSet

Represents the four audio arrays loaded from separated stems for a single source file during one analysis run. Lives in memory only (not persisted).

| Field | Type | Notes |
|-------|------|-------|
| `drums` | `np.ndarray` | Audio array, same sample rate as source |
| `bass` | `np.ndarray` | Audio array |
| `vocals` | `np.ndarray` | Audio array |
| `guitar` | `np.ndarray` | Audio array |
| `piano` | `np.ndarray` | Audio array |
| `other` | `np.ndarray` | Residual stem from `htdemucs_6s` |
| `sample_rate` | `int` | Shared sample rate for all stems |

**Usage**: Created by `StemSeparator.separate()`, passed to `runner.run()` when `--stems` is enabled.

---

### StemCache

Represents the on-disk cache of stem WAV files for a source audio file.

| Field | Type | Notes |
|-------|------|-------|
| `source_path` | `Path` | Absolute path to source MP3 |
| `source_hash` | `str` | MD5 hex digest of source file bytes |
| `stem_dir` | `Path` | `.stems/<source_hash>/` directory adjacent to source file |
| `stems` | `dict[str, Path]` | `{"drums": Path, "bass": Path, "vocals": Path, "guitar": Path, "piano": Path, "other": Path}` |
| `created_at` | `int` | Unix timestamp (ms) of when stems were generated |

**Manifest file** (`manifest.json` in `stem_dir`):
```json
{
  "source_hash": "a3f8c2d1...",
  "source_path": "/abs/path/to/song.mp3",
  "created_at": 1742601600000,
  "stems": {
    "drums": "drums.wav",
    "bass": "bass.wav",
    "vocals": "vocals.wav",
    "guitar": "guitar.wav",
    "piano": "piano.wav",
    "other": "other.wav"
  }
}
```

**Validation**: Cache is valid if and only if `stem_dir` exists and MD5 of the current source file matches `source_hash` in the manifest.

---

### Algorithm.preferred_stem (attribute extension)

Class-level attribute added to `base.Algorithm`. Not a data entity but a routing contract.

| Attribute | Type | Default | Values |
|-----------|------|---------|--------|
| `preferred_stem` | `str` | `"full_mix"` | `"drums"`, `"bass"`, `"vocals"`, `"other"`, `"full_mix"` |

---

## State Transitions

### Stem Cache Lifecycle

```
[No cache]
    │
    ▼  (analyze --stems, no cache found)
[Separating]  ──failure──▶  [Fallback: full_mix analysis]
    │
    ▼  (stems written to disk + manifest)
[Cached]
    │
    ├──  (analyze --stems, same file)  ──▶  [Cache Hit: skip separation]
    │
    └──  (source file changed)  ──▶  [Stale: regenerate]  ──▶  [Cached]
```

---

## JSON Output Changes

Before (existing track object):
```json
{
  "name": "qm-barbeattracker",
  "marks": [0, 512, 1024],
  "quality_score": 0.87
}
```

After (with stem_source field):
```json
{
  "name": "qm-barbeattracker",
  "marks": [0, 512, 1024],
  "quality_score": 0.87,
  "stem_source": "drums"
}
```

Backward compatibility: existing JSON files without `stem_source` are read as `"full_mix"` by the review UI and summary command.
