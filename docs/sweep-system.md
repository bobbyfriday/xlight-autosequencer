# Parameter Sweep System

[< Back to Index](README.md) | See also: [Algorithm Reference](algorithms.md) · [Quality Scoring](quality-scoring.md) · [Stem Routing](stem-separation.md)

The sweep system tests many combinations of algorithms, stems, and parameters to find the optimal settings for each song. Instead of using default parameters, it tries hundreds of permutations on a 30-second sample and picks the winners.

---

## Why Sweep?

Different songs benefit from different algorithm parameters. A fast punk song might need different onset detection sensitivity than a slow ballad. The sweep system automates what would otherwise be manual trial-and-error:

```
Without sweep (defaults):        With sweep (optimized):
──────────────────────────       ──────────────────────────
qm_beats + defaults              qm_beats + inputtempo=145
  → score: 0.72                    → score: 0.94

qm_onsets_hfc + defaults         qm_onsets_complex + drums stem
  → score: 0.65                    → score: 0.91
```

---

## Sweep Matrix Concept

The sweep matrix is a 3-dimensional cross-product:

```
                    Algorithms
                    ─────────────────────────
                    │ qm_beats              │
                    │ librosa_beats         │
                    │ qm_onsets_complex     │
                    │ qm_onsets_hfc         │
                    │ chordino_chords       │
                    │ ...                   │
                    └──────────┬────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         ┌─────────┐    ┌──────────┐    ┌──────────┐
         │ drums   │    │ bass     │    │ full_mix │
         │         │    │          │    │          │
         │ param   │    │ param    │    │ param    │
         │ set A   │    │ set A    │    │ set A    │
         │ param   │    │ param    │    │ param    │
         │ set B   │    │ set B    │    │ set B    │
         │ param   │    │ param    │    │ param    │
         │ set C   │    │ set C    │    │ set C    │
         └─────────┘    └──────────┘    └──────────┘
              │                │                │
              ▼                ▼                ▼
         3 perms          3 perms          3 perms  = 9 total for this algo
```

**Total permutations** = algorithms × stems × parameter combinations

The matrix is capped at **500 permutations** by default to keep run time reasonable.

---

## Two Sweep Modes

### 1. Single-Algorithm Sweep (`xlight-analyze sweep`)

Test one algorithm with different parameter values and stems:

```bash
xlight-analyze sweep song.mp3 --config sweep_config.json
```

**Config format:**
```json
{
  "algorithm": "qm_beats",
  "sweep": {
    "inputtempo": [80, 100, 120, 140, 160],
    "constraintempo": [0, 1]
  },
  "fixed": {},
  "stems": ["drums", "bass", "full_mix"]
}
```

This runs 5 × 2 × 3 = **30 permutations**.

### 2. Full Matrix Sweep (`xlight-analyze sweep-matrix`)

Test all algorithms across all available stems:

```bash
xlight-analyze sweep-matrix song.mp3
```

The matrix auto-discovers:
- **Available algorithms** based on installed capabilities
- **Available stems** from the stem separation cache
- **Tunable parameters** from the stem affinity table
- **Parameter value ranges** from Vamp plugin descriptors

---

## Sweep Execution Flow

```
1. SETUP
   ├── Load audio
   ├── Detect available stems (KEEP/REVIEW/SKIP verdicts)
   ├── Build algorithm list based on capabilities
   ├── Compute parameter permutations per algorithm
   ├── Dedup identical (algo, stem, params) triples
   └── Display matrix size, confirm with user

2. SAMPLE SELECTION
   ├── Default: 30-second segment from the middle of the song
   ├── --sample-start: fixed position (ms)
   └── --sample-duration: segment length (default: 30s)

3. EXECUTION (parallel)
   ├── For each permutation:
   │   ├── Load target stem audio
   │   ├── Set algorithm parameters
   │   ├── Run algorithm on sample segment
   │   ├── Score result
   │   └── Write incremental JSON
   └── Collect all PermutationResult objects

4. RANKING
   ├── Sort results by quality_score descending
   ├── Per-algorithm best selection (highest score, tie-break: fewer marks)
   └── Write sweep_report.json

5. OPTIONAL: FULL-SONG RE-RUN
   ├── Re-run winning parameter sets on full audio (not sample)
   ├── Export .xtiming and .xvc files
   └── Write winners/winners.json for review UI
```

---

## Permutation Result

Each permutation produces:

```
┌────────────────────────────────────────────────┐
│  PermutationResult                              │
│                                                │
│  algorithm:     "qm_onsets_complex"            │
│  stem:          "drums"                        │
│  parameters:    {"dftype": 3, "threshold": 0.5}│
│  result_type:   "timing"                       │
│                                                │
│  quality_score: 0.91                           │
│  mark_count:    342                            │
│  avg_interval:  608 ms                         │
│  dynamic_range: 0.85                           │
│  duration_ms:   1240                           │
│  status:        "success"                      │
└────────────────────────────────────────────────┘
```

---

## Winner Selection

After all permutations run, `auto_select_best()` picks one winner per algorithm:

```
qm_onsets_complex:
  #1  drums   dftype=3  score=0.91  ← WINNER
  #2  bass    dftype=3  score=0.84
  #3  drums   dftype=0  score=0.79

qm_beats:
  #1  drums   inputtempo=140  score=0.95  ← WINNER
  #2  drums   inputtempo=120  score=0.93
  #3  bass    inputtempo=140  score=0.88

librosa_beats:
  #1  drums   hop=512  score=0.89  ← WINNER (only 1 param set)
```

**Tie-breaking:** When two permutations have equal quality_score, the one with **fewer marks** wins. This prefers cleaner, sparser results over noisy dense ones.

---

## Output Files

```
song/
  └── sweep/
      ├── sweep_report.json          ← All results, ranked
      ├── sweep_qm_beats.json        ← Per-algorithm detail
      ├── sweep_qm_onsets_complex.json
      ├── sweep_librosa_beats.json
      ├── sweep_bbc_energy.json
      ├── ...
      └── winners/
          ├── winners.json            ← Full-song marks for winners
          ├── qm_beats_drums.xtiming  ← xLights timing export
          ├── bbc_energy_full_mix.xvc ← xLights value curve export
          └── ...
```

### sweep_report.json structure:

```json
{
  "audio_file": "song.mp3",
  "total_permutations": 342,
  "sample_duration_ms": 30000,
  "results": [
    {
      "algorithm": "qm_beats",
      "stem": "drums",
      "parameters": {"inputtempo": 140},
      "quality_score": 0.95,
      "mark_count": 62,
      "avg_interval_ms": 484
    },
    ...
  ]
}
```

---

## Viewing Sweep Results

### CLI

```bash
# Show all results ranked
xlight-analyze sweep-results sweep/sweep_report.json

# Filter by algorithm
xlight-analyze sweep-results sweep/sweep_report.json --algorithm qm_beats

# Show only the best per algorithm
xlight-analyze sweep-results sweep/sweep_report.json --best

# Re-run displayed results on full song and export
xlight-analyze sweep-results sweep/sweep_report.json --best --export
```

### Review UI

The sweep results are viewable in the browser:

```bash
xlight-analyze review song.mp3
```

Navigate to the sweep tab to see:
- Ranked list of all permutation results
- Filter by algorithm and stem
- Timeline visualization showing marks for selected results
- Side-by-side comparison of two results
- Export selected results as .xtiming/.xvc

---

## Parameter Discovery

To see what parameters are tunable for a Vamp plugin:

```bash
xlight-analyze params qm-vamp-plugins:qm-tempotracker
```

Output:
```
Parameter         Type    Range        Default  Description
────────────────  ──────  ───────────  ───────  ───────────────────
inputtempo        float   50.0–190.0   120.0   Expected tempo
constraintempo    enum    0, 1         0       Lock to input tempo
```

To get suggested sweep values:
```bash
xlight-analyze sweep-suggest qm-vamp-plugins:qm-tempotracker inputtempo --steps 5
# → [50.0, 85.0, 120.0, 155.0, 190.0]
```

---

## TOML Configuration

Sweep parameters can be configured via TOML:

```toml
[params.qm_beats]
inputtempo = [80, 100, 120, 140, 160]
constraintempo = [0, 1]

[params.qm_onsets_complex]
dftype = [0, 1, 2, 3]

[params.librosa_beats]
# No tunable params — uses defaults
```

Load with:
```bash
xlight-analyze sweep-matrix song.mp3 --config sweep_config.toml
```

---

## Practical Example

Running a sweep on "Highway to Hell" (AC/DC):

```bash
$ xlight-analyze sweep-matrix highway.mp3

Detecting capabilities... vamp: yes, madmom: yes, demucs: yes
Loading stems... 6 stems available (drums, bass, vocals, guitar, piano, other)

Sweep matrix:
  Algorithms: 24
  Stems per algo: 1-6 (based on affinity)
  Parameter combinations: 1-10 per algo
  Total permutations: 347

Sample: 30s starting at 60000ms
Proceed? [Y/n] y

Running permutations... ████████████████████████ 347/347

Top results per algorithm:
  qm_beats        drums   inputtempo=120  score=0.96
  madmom_beats    drums   (default)       score=0.98
  librosa_beats   drums   hop=512         score=0.89
  qm_onsets_hfc   drums   dftype=0        score=0.91
  chordino        piano   (default)       score=0.88

Re-run winners on full song? [Y/n] y
Exporting to highway/sweep/winners/...
```

---

## Related Docs

- [Algorithm Reference](algorithms.md) — What parameters each algorithm accepts
- [Stem Routing](stem-separation.md) — How stems are selected for sweep
- [Quality Scoring](quality-scoring.md) — How permutations are ranked
