# Architecture Overview

[< Back to Index](README.md)

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MP3 INPUT                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AUDIO LOADING (librosa)                         │
│  • Mono float32 at native sample rate                               │
│  • MD5 hash computed for caching                                    │
│  • AudioFile metadata (duration, sample rate, filename)             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   STEM SEPARATION        │  │   FULL MIX               │
│   (demucs htdemucs_6s)   │  │   (original audio)       │
│                          │  │                          │
│   6 stems:               │  │   Used by algorithms     │
│   • drums                │  │   that prefer full_mix   │
│   • bass                 │  │   (HPSS, frequency       │
│   • vocals               │  │    bands, energy)        │
│   • guitar               │  │                          │
│   • piano                │  └──────────┬───────────────┘
│   • other                │             │
│                          │             │
│   Cached as MP3 in       │             │
│   .stems/<md5>/          │             │
└──────────┬───────────────┘             │
           │                             │
           └──────────┬──────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ALGORITHM DISPATCH                               │
│                                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │  Main Process        │  │  Subprocess          │                  │
│  │  (.venv, numpy>=2)   │  │  (.venv-vamp,        │                  │
│  │                      │  │   numpy<2)           │                  │
│  │  8 librosa algos     │  │                      │                  │
│  │  • beat tracking     │  │  ~25 vamp algos      │                  │
│  │  • onset detection   │  │  • QM plugins        │                  │
│  │  • HPSS separation   │  │  • BeatRoot          │                  │
│  │  • frequency bands   │  │  • pYIN              │                  │
│  │                      │  │  • Chordino/NNLS     │                  │
│  │                      │  │  • BBC plugins       │                  │
│  │                      │  │  • Aubio             │                  │
│  │                      │  │  • Silvet            │                  │
│  │                      │  │                      │                  │
│  │                      │  │  2 madmom algos      │                  │
│  │                      │  │  • RNN beat tracker   │                  │
│  │                      │  │  • RNN downbeat       │                  │
│  └─────────────────────┘  └─────────────────────┘                  │
│                                                                     │
│  Communication: NDJSON on stdin/stdout (subprocess protocol)        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     QUALITY SCORING                                  │
│                                                                     │
│  Per-track scoring across 5 criteria:                               │
│  density · regularity · mark count · coverage · min-gap compliance  │
│                                                                     │
│  Category-aware ranges (beats vs onsets vs harmony, etc.)           │
│  Weighted average → quality_score 0.0–1.0                           │
│  See: quality-scoring.md                                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     HIERARCHY ASSEMBLY                               │
│                                                                     │
│  L0  Derived       energy impacts, drops, gaps                      │
│  L1  Sections      intro / verse / chorus / bridge / outro          │
│  L2  Bars          downbeats (bar boundaries)                       │
│  L3  Beats         beat-level pulse                                 │
│  L4  Events        per-stem onsets and transients                   │
│  L5  Dynamics      energy curves per stem                           │
│  L6  Harmony       chord changes, key changes                       │
│                                                                     │
│  See: hierarchy.md                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
          ┌──────────┐  ┌──────────┐  ┌──────────┐
          │  JSON     │  │ .xtiming │  │  .xvc    │
          │  Cache    │  │  XML     │  │  XML     │
          │           │  │          │  │          │
          │  Analysis │  │  Timing  │  │  Value   │
          │  result   │  │  marks   │  │  curves  │
          │  + scores │  │  for     │  │  for     │
          │           │  │  xLights │  │  xLights │
          └──────────┘  └──────────┘  └──────────┘

                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     REVIEW UI (Flask + Canvas)                       │
│                                                                     │
│  • Timeline visualization of all timing tracks                      │
│  • Synchronized audio playback via Web Audio API                    │
│  • Track selection and filtered export                              │
│  • Sweep result comparison                                          │
│  • Phoneme editor for word/phoneme timing                           │
│  • Library browser for multi-song management                        │
│                                                                     │
│  See: review-ui.md                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Location | Role |
|-----------|----------|------|
| **Audio loader** | `src/analyzer/audio.py` | Load MP3 → mono float32 + metadata |
| **Stem separator** | `src/analyzer/stems.py` | Demucs 6-stem separation + MP3 caching |
| **Algorithm base** | `src/analyzer/algorithms/base.py` | Abstract interface all algorithms implement |
| **8 librosa algos** | `src/analyzer/algorithms/librosa_*.py` | In-process analysis (beats, onsets, bands, HPSS) |
| **~25 vamp algos** | `src/analyzer/algorithms/vamp_*.py` | Subprocess analysis via Vamp plugin host |
| **2 madmom algos** | `src/analyzer/algorithms/madmom_beat.py` | RNN beat/downbeat tracking |
| **Runner** | `src/analyzer/runner.py` | Orchestrates algorithm execution |
| **Vamp subprocess** | `src/analyzer/vamp_runner.py` | NDJSON protocol for numpy<2 isolation |
| **Scorer** | `src/analyzer/scorer.py` | Quality scoring with category-aware ranges |
| **Orchestrator** | `src/analyzer/orchestrator.py` | Hierarchy assembly (schema 2.0.0) |
| **Sweep engine** | `src/analyzer/sweep.py`, `sweep_matrix.py` | Parameter optimization across algo×stem matrix |
| **Cache** | `src/cache.py` | MD5-keyed analysis result caching |
| **Library** | `src/library.py` | Global index at `~/.xlight/library.json` |
| **CLI** | `src/cli.py` | Click-based command interface (20+ commands) |
| **Export** | `src/export.py`, `src/analyzer/xtiming.py`, `xvc_export.py` | JSON, .xtiming, .xvc output |
| **Review server** | `src/review/server.py` | Flask app for timeline review |
| **Review UI** | `src/review/static/` | Canvas + Web Audio frontend |

## Two Process Architecture

The system runs algorithms in **two separate Python environments** to handle incompatible numpy versions:

```
┌──────────────────────────┐     NDJSON pipe     ┌──────────────────────────┐
│  Main process (.venv)    │ ◄──────────────────► │  Subprocess (.venv-vamp)  │
│                          │                      │                          │
│  Python 3.11+            │                      │  Python 3.11+            │
│  numpy >= 2.0            │                      │  numpy < 2.0             │
│  librosa 0.10+           │                      │  vamp (plugin host)      │
│  whisperx (optional)     │                      │  madmom 0.16+            │
│  demucs/torch (optional) │                      │  All Vamp plugin packs   │
│                          │                      │                          │
│  Runs: 8 librosa algos   │                      │  Runs: ~25 vamp algos    │
│  Runs: orchestrator      │                      │  Runs: 2 madmom algos    │
│  Runs: Flask server       │                      │                          │
│  Runs: scoring           │                      │  Scores tracks locally    │
│  Runs: stem separation   │                      │  Returns via NDJSON      │
└──────────────────────────┘                      └──────────────────────────┘
```

**Why two processes?** Vamp Python bindings and madmom require numpy<2 for ABI compatibility, while whisperx and modern torch require numpy>=2. The subprocess protocol sends algorithm names and stem paths in, and receives scored timing tracks back as newline-delimited JSON.

## Three Caching Layers

```
Layer 1: Analysis Cache          Layer 2: Stem Cache           Layer 3: Library Index
─────────────────────────        ──────────────────────        ──────────────────────
song_hierarchy.json              .stems/<md5>/manifest.json    ~/.xlight/library.json
• MD5-keyed                      • MD5-keyed                   • Global song index
• Full hierarchy result          • 6 stem MP3 files            • One entry per hash
• Schema version check           • Demucs model metadata       • Paths + metadata
• source_hash validation         • source_hash validation      • Sorted by date
```

All three layers key on the **MD5 hex digest** of the source audio file, computed via streaming (64KB chunks).

## Related Docs

- [Analysis Pipeline](pipeline.md) — Step-by-step walkthrough
- [Algorithm Reference](algorithms.md) — All 35+ algorithms
- [Hierarchy Levels](hierarchy.md) — L0–L6 detail
