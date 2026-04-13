# CLI Contract: Stem Separation

**Branch**: `008-stem-separation` | **Date**: 2026-03-22

---

## Modified Command: `xlight-analyze analyze`

### New Option

```
--stems / --no-stems    Enable stem separation before analysis.
                        Default: disabled (full-mix analysis).
```

### Full Signature

```
xlight-analyze analyze [OPTIONS] AUDIO_FILE

Options:
  --stems / --no-stems   Run stem separation before analysis [default: no-stems]
  --top INTEGER          Auto-select top N tracks by quality score
  --output PATH          Output file path [default: <audio_file>_analysis.json]
  --help                 Show this message and exit.
```

### Behavior

| Scenario | Behavior |
|----------|----------|
| `analyze song.mp3` | Full-mix analysis (unchanged from current behavior) |
| `analyze song.mp3 --stems` | Separate into stems, route algorithms, analyze |
| `analyze song.mp3 --stems` (cached) | Skip separation, load cached stems, analyze |
| Stem separation fails | Warn user, fall back to full-mix analysis, complete normally |

### Console Output (with `--stems`)

```
Loading audio: song.mp3
Stem separation: checking cache...
  → No cache found. Separating (this may take 1-2 minutes)...
  → Stems cached to .stems/a3f8c2d1/
Running 22 algorithms (stem-routed)...
  [qm-barbeattracker]  drums stem  ✓
  [pyin-notes]         vocals stem ✓
  ...
Analysis complete: song_analysis.json
```

```
Loading audio: song.mp3
Stem separation: cache hit (a3f8c2d1)
Running 22 algorithms (stem-routed)...
  ...
```

---

## Modified Command: `xlight-analyze summary`

### Changed Output

Each track line gains a `stem` column:

```
Track                    Stem       Quality  Marks
─────────────────────────────────────────────────────
qm-barbeattracker        drums      0.91     312
madmom-rnn-dbn           drums      0.89     310
pyin-notes               vocals     0.84     188
chordino-changes         piano      0.77      42
qm-onsetdetector-energy  drums      0.72     891
...
```

Tracks from a non-stem analysis show `full_mix` in the Stem column.

---

## Analysis Output Schema (JSON)

### Track Object (extended)

```json
{
  "name": "qm-barbeattracker",
  "marks": [512, 1024, 1536],
  "quality_score": 0.91,
  "stem_source": "drums"
}
```

### Top-level metadata (extended)

```json
{
  "version": "1.0",
  "source_file": "song.mp3",
  "stem_separation": true,
  "stem_cache": ".stems/a3f8c2d1/",
  "tracks": [ ... ]
}
```

`stem_separation: false` and `stem_cache: null` when run without `--stems`.

---

## Backward Compatibility

- Existing analysis JSON files (without `stem_source`) MUST be loaded without error. Missing `stem_source` on a track is treated as `"full_mix"`.
- Existing callers of `xlight-analyze analyze` without `--stems` are unaffected.
