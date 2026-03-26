# Analysis Pipeline

[< Back to Index](README.md) | See also: [Architecture Overview](architecture-overview.md) · [Hierarchy Levels](hierarchy.md)

This document walks through the complete analysis pipeline from MP3 input to xLights-ready output.

---

## Pipeline Overview

```
 ┌──────┐   ┌──────────┐   ┌───────────┐   ┌───────────┐   ┌─────────┐   ┌────────┐
 │ MP3  │──▶│  Audio    │──▶│  Stem     │──▶│ Algorithm │──▶│ Scoring │──▶│Hierarchy│
 │ File │   │  Loading  │   │ Separation│   │ Execution │   │& Ranking│   │Assembly │
 └──────┘   └──────────┘   └───────────┘   └───────────┘   └─────────┘   └────┬───┘
                                                                               │
                                           ┌───────────────────────────────────┘
                                           │
                                           ▼
                              ┌──────────────────────────┐
                              │  Export                   │
                              │  • _hierarchy.json        │
                              │  • .xtiming (timing marks)│
                              │  • .xvc (value curves)    │
                              └──────────────────────────┘
```

---

## Step 1: Audio Loading

**Module:** `src/analyzer/audio.py`

```python
audio, sample_rate, metadata = audio.load("song.mp3")
```

What happens:
1. **librosa.load()** reads the MP3 via ffmpeg, converting to mono float32 at the file's native sample rate
2. **MD5 hash** is computed (streaming, 64KB chunks) for cache keying
3. **AudioFile** metadata is assembled: path, filename, duration_ms, sample_rate

The audio array is the raw material that all algorithms work with. It's a 1-dimensional numpy array of float32 values in the range [-1.0, 1.0].

**Cache check:** Before doing any work, the pipeline checks if a valid `_hierarchy.json` exists with a matching `source_hash`. If so, it returns the cached result immediately.

---

## Step 2: Stem Separation

**Module:** `src/analyzer/stems.py`

```
                     Full Mix (original audio)
                            │
                     demucs htdemucs_6s
                            │
           ┌────────┬───────┼───────┬────────┬────────┐
           ▼        ▼       ▼       ▼        ▼        ▼
        drums     bass   vocals  guitar   piano    other
```

**What happens:**
1. **Cache check:** Look for `.stems/<md5>/manifest.json` with matching source_hash
2. **Demucs htdemucs_6s** runs if no cached stems — separates audio into 6 stems in a single pass
3. Each stem is saved as an **MP3 file** in `.stems/<md5>/` alongside a manifest
4. Stems are loaded back as mono float32 arrays via librosa

**The 6 stems:**

| Stem | Contains | Used By |
|------|----------|---------|
| drums | Kick, snare, hi-hat, cymbals, percussion | Beat/onset/percussion algorithms |
| bass | Bass guitar, synth bass, low-end | Beat algorithms (supplementary) |
| vocals | Singing, spoken word, vocal harmonies | Pitch/melody, phoneme analysis |
| guitar | Electric/acoustic guitar | Onset detectors |
| piano | Piano, keys, synth pads | Chord/harmony algorithms |
| other | Everything else (strings, horns, effects) | General analysis |

**Why separate?** Algorithms work better on isolated sources. A beat tracker on the drums stem doesn't get confused by melodic rhythm. A chord detector on the piano stem doesn't pick up drum harmonics.

**When stems aren't available:** Algorithms fall back to `full_mix` (the original audio).

See [Stem Separation & Routing](stem-separation.md) for the full affinity table.

---

## Step 3: Algorithm Execution

**Modules:** `src/analyzer/runner.py`, `src/analyzer/vamp_runner.py`

The orchestrator builds an algorithm list based on available capabilities:

```
Capability Detection:
  librosa  → always available (8 algorithms)
  vamp     → check for .venv-vamp and plugin .dylib files (~25 algorithms)
  madmom   → check for madmom in .venv-vamp (2 algorithms)
```

Algorithms are then dispatched in two streams:

### In-Process (librosa)

The 8 librosa algorithms run directly in the main Python process:
- No subprocess overhead
- Share the loaded audio array in memory
- Run sequentially (they're fast enough that parallelism isn't needed)

### Subprocess (vamp + madmom)

The ~27 vamp and madmom algorithms run in a separate process with numpy<2:

```
Main Process                         Subprocess (.venv-vamp)
─────────────                        ──────────────────────
                    ┌──────────┐
  Send request ───▶ │  stdin   │ ───▶ Load audio
  (JSON)            │  (pipe)  │      Route to stems
                    └──────────┘      Run each algorithm
                                      Score each track
                    ┌──────────┐
  Receive ◀──────── │  stdout  │ ◀─── Emit progress (NDJSON)
  progress events   │  (pipe)  │      Emit results
                    └──────────┘
```

**NDJSON protocol messages:**
- `{"event": "progress", "idx": 5, "total": 25, "name": "qm_beats", "mark_count": 210}`
- `{"event": "warn", "name": "silvet_notes", "message": "..."}`
- `{"event": "done", "tracks": [...], "algorithms": [...]}`
- `{"event": "error", "message": "..."}`

Each algorithm receives its preferred stem audio and produces either a **TimingTrack** (list of marks) or a **ValueCurve** (continuous envelope).

---

## Step 4: Quality Scoring

**Module:** `src/analyzer/scorer.py`

Every track is scored against category-specific criteria:

```
                    ┌─────────────────────────────────────┐
                    │  Algorithm Output (TimingTrack)      │
                    │  • 210 marks                        │
                    │  • spanning 0ms to 207,000ms        │
                    │  • avg interval 987ms               │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │  Category Lookup                    │
                    │  element_type = "beat"              │
                    │  → use "beats" scoring profile      │
                    └──────────────────┬──────────────────┘
                                       │
               ┌───────────┬───────────┼───────────┬───────────┐
               ▼           ▼           ▼           ▼           ▼
          ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
          │Density  │ │Regular- │ │Mark     │ │Coverage │ │Min Gap  │
          │1.01/sec │ │ity 0.92│ │Count 210│ │0.99     │ │Compliance│
          │         │ │         │ │         │ │         │ │0.98     │
          │Range:   │ │Range:   │ │Range:   │ │Range:   │ │Thresh:  │
          │1.0–4.0  │ │0.6–1.0 │ │100–800  │ │0.8–1.0 │ │≥ 25ms   │
          │         │ │         │ │         │ │         │ │         │
          │Score:   │ │Score:   │ │Score:   │ │Score:   │ │Score:   │
          │1.00     │ │1.00     │ │1.00     │ │1.00     │ │0.98     │
          │         │ │         │ │         │ │         │ │         │
          │Weight:  │ │Weight:  │ │Weight:  │ │Weight:  │ │Weight:  │
          │0.25     │ │0.25     │ │0.15     │ │0.15     │ │0.20     │
          └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
               │           │           │           │           │
               └───────────┴───────────┴─────┬─────┴───────────┘
                                             │
                                    Weighted Average
                                             │
                                       ▼ = 0.996
                                    quality_score
```

See [Quality Scoring](quality-scoring.md) for details on each criterion and category-specific ranges.

---

## Step 5: Hierarchy Assembly

**Module:** `src/analyzer/orchestrator.py`

The orchestrator takes all scored tracks and assembles them into a 7-level hierarchy:

```
╔══════════════════════════════════════════════════════════════════╗
║  L1 SECTIONS                                                    ║
║  intro (0-15s) │ verse (15-45s) │ chorus (45-75s) │ verse ...   ║
╠══════════════════════════════════════════════════════════════════╣
║  L2 BARS        |       |       |       |       |       |      ║
╠══════════════════════════════════════════════════════════════════╣
║  L3 BEATS     | | | | | | | | | | | | | | | | | | | | | | |   ║
╠══════════════════════════════════════════════════════════════════╣
║  L4 EVENTS   ||| || |||| ||| || |||| ||| || |||| ||| || ||||   ║
║  (per stem)                                                     ║
╠══════════════════════════════════════════════════════════════════╣
║  L5 DYNAMICS  ~~~╱‾‾╲__╱‾‾‾╲___╱‾‾‾‾‾╲__╱‾╲___╱‾‾‾╲____~~   ║
║  (per stem)                                                     ║
╠══════════════════════════════════════════════════════════════════╣
║  L6 HARMONY   C  │  Am  │  F  │  G  │  C  │  Am  │  F  │ G    ║
╚══════════════════════════════════════════════════════════════════╝
```

**Selection logic:** For each level, the orchestrator picks the **best-scoring** algorithm:
- L2 Bars: best of `qm_bars`, `librosa_bars`, `madmom_downbeats`
- L3 Beats: best of `qm_beats`, `librosa_beats`, `madmom_beats`, `beatroot_beats`, `aubio_tempo`
- L4 Events: runs onset detectors per-stem and keeps per-stem results
- L5 Dynamics: runs energy curves per-stem
- L6 Harmony: `chordino_chords` for chords, `qm_key` for key changes

**L0 Derived** features (energy impacts, drops, gaps) are computed from the L5 curves and L3/L4 timing data rather than from raw audio.

See [Hierarchy Levels](hierarchy.md) for full detail on each level.

---

## Step 6: Output & Export

### JSON Output

The hierarchy result is written as `song_hierarchy.json`:

```json
{
  "schema_version": "2.0.0",
  "source_file": "/path/to/song.mp3",
  "source_hash": "d17796b2cd4fea69532abb045d2fc155",
  "duration_ms": 208110,
  "estimated_bpm": 116.0,
  "stems_available": ["drums", "bass", "vocals", "guitar", "piano", "other"],
  "sections": [...],
  "bars": {...},
  "beats": {...},
  "events": {"full_mix": {...}, "drums": {...}, ...},
  "chords": {...},
  "key_changes": {...}
}
```

### .xtiming Export

Timing marks are exported as xLights-compatible XML:

```xml
<timings>
  <timing name="song" SourceVersion="2024.01">
    <EffectLayer>
      <Effect label="" starttime="500" endtime="1000" />
      <Effect label="" starttime="1000" endtime="1500" />
    </EffectLayer>
  </timing>
</timings>
```

### .xvc Export

Value curves are exported for xLights dimmer/intensity control:

```xml
<valuecurve data="Active=TRUE|Id=ID_VC|Type=Custom|Min=0.00|Max=100.00|
Values=0.00:45.00;0.01:52.30;0.02:61.10;..." />
```

See [Export Formats](export-formats.md) for details.

---

## Pipeline Variants

The pipeline can be invoked several ways:

| Command | What It Does |
|---------|-------------|
| `xlight-analyze analyze song.mp3` | Full hierarchical pipeline → `_hierarchy.json` |
| `xlight-analyze wizard song.mp3` | Interactive prompts → configure and run pipeline |
| `xlight-analyze sweep-matrix song.mp3` | Parameter optimization across algo×stem combos |
| `xlight-analyze review song.mp3` | Run pipeline then open review UI |
| Upload via Flask UI | Drag-and-drop MP3 → background pipeline → timeline |

All paths converge on the same orchestrator and produce the same `HierarchyResult` schema.

---

## Related Docs

- [Architecture Overview](architecture-overview.md) — System diagram
- [Algorithm Reference](algorithms.md) — What each algorithm does
- [Hierarchy Levels](hierarchy.md) — L0–L6 detail
- [Quality Scoring](quality-scoring.md) — How tracks are ranked
- [Export Formats](export-formats.md) — Output file formats
