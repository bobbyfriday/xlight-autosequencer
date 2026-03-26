# Hierarchy Levels (L0–L6)

[< Back to Index](README.md) | See also: [Pipeline](pipeline.md) · [Algorithm Categories](algorithm-categories.md)

The orchestrator assembles analysis results into a 7-level timing hierarchy. Each level represents a different temporal scale of the music, from song-level sections down to sub-beat transients.

---

## Overview

```
Level   Name        Scale           Typical Count    What It Represents
─────   ──────────  ──────────────  ─────────────    ──────────────────────────
L0      Derived     Variable        10–50            Computed energy features
L1      Sections    10–60 seconds   5–15             Song structure (verse/chorus)
L2      Bars        1–4 seconds     50–100           Measure boundaries
L3      Beats       250–600 ms      200–400          Rhythmic pulse
L4      Events      10–500 ms       200–2000/stem    Transients and onsets
L5      Dynamics    continuous       ~20 fps          Energy envelopes per stem
L6      Harmony     1–10 seconds    10–100           Chords and key changes
```

---

## L0: Derived Features

**What:** Computed features derived from other levels — not from raw audio algorithms.

**Contents:**
- **energy_impacts** — Moments where energy jumps sharply upward (e.g., chorus entrance, drop)
- **energy_drops** — Moments where energy falls sharply (e.g., breakdown, transition to verse)
- **gaps** — Silent or near-silent regions (>500ms below threshold)

**How they're computed:**
- Energy impacts: large positive derivative in L5 energy curves
- Energy drops: large negative derivative in L5 energy curves
- Gaps: sustained low values in L5 energy curves + absence of L4 events

**xLights use:** Energy impacts trigger "wow" effects (all lights flash, color burst). Energy drops trigger fade-to-dark or slow transitions. Gaps are rest periods with minimal lighting.

```
L5 Energy:  ~~~~╱‾‾‾‾╲__╱‾‾‾‾‾‾‾‾╲____________________________╱‾‾‾‾
L0 Impact:       ▲                                                ▲
L0 Drop:                  ▼
L0 Gap:                                     ◄────── gap ──────►
```

---

## L1: Sections

**What:** Song structure boundaries — intro, verse, chorus, bridge, outro.

**Source algorithms:**
- `segmentino` (preferred) — labels repeated sections (A1, B, A2)
- `qm_segments` (fallback) — unlabeled section boundaries

**Selection:** Best-scoring structure algorithm.

**Typical output:**
```
 0:00    0:15     0:45     1:15     1:45     2:15     2:45     3:15    3:28
  │ intro │ verse1 │chorus1 │ verse2 │chorus2 │ bridge │chorus3 │ outro │
```

**xLights use:** Each section gets a distinct "theme" — a combination of effects, colors, and intensity levels. The intro might be slow fades in cool colors, the chorus might be bright warm chases, the bridge might introduce a unique effect.

**Why it matters:** Sections are the macro structure that makes a light show feel intentional. Without them, effects are random over time. With them, the show has narrative arc.

---

## L2: Bars

**What:** Measure/bar boundaries — the "1" beat of each measure.

**Source algorithms (best-of):**
- `madmom_downbeats` — RNN downbeat classifier (most accurate)
- `qm_bars` — QM bar-beat tracker
- `librosa_bars` — every 4th librosa beat

**Selection:** Highest quality_score wins.

**Typical output:** 50–100 marks for a 3.5-minute song

**xLights use:** Bar boundaries are the "scene change" level. They're where you'd switch between two alternating chase patterns, advance a color rotation, or trigger a mid-level transition. Too fast for scene changes (those are L1), too slow for beat-synced flashes (those are L3).

```
L3 Beats:  | | | | | | | | | | | | | | | | | | | | | | | | | | | |
L2 Bars:   |       |       |       |       |       |       |       |
           beat 1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4
```

---

## L3: Beats

**What:** The rhythmic pulse — every beat in the music.

**Source algorithms (best-of):**
- `madmom_beats` — most accurate overall
- `librosa_beats` — always available
- `qm_beats` — stable on regular meter
- `beatroot_beats` — good on swing/rubato
- `aubio_tempo` — lightweight supplementary

**Selection:** Highest quality_score wins.

**Typical output:** 200–400 marks

**xLights use:** Beat-synced effects — flash on every beat, alternating colors per beat, chase advancement per beat. This is the most commonly used timing level for xLights sequences.

**Quality indicators:** A good beat track has:
- Regular spacing (regularity > 0.8)
- Consistent density (1–4 beats/sec)
- Full coverage (>95% of song duration)

---

## L4: Events

**What:** Sub-beat transients and onsets — every discrete musical event per stem.

**Source algorithms (per-stem):**
- `librosa_onsets` (full_mix)
- `aubio_onset` (per available stem)
- `qm_onsets_*` (per available stem)
- `percussion_onsets` (drums stem)

**Selection:** The orchestrator runs onset detectors on each available stem and keeps per-stem results. This is the only level with stem-specific output.

**Structure:**
```json
{
  "events": {
    "full_mix": {"name": "librosa_onsets", "marks": [...]},
    "drums":    {"name": "aubio_onset", "marks": [...]},
    "bass":     {"name": "aubio_onset", "marks": [...]},
    "vocals":   {"name": "aubio_onset", "marks": [...]},
    "guitar":   {"name": "aubio_onset", "marks": [...]},
    "piano":    {"name": "aubio_onset", "marks": [...]}
  }
}
```

**xLights use:** Per-stem events map to per-group lights:

```
Stem      Light Group Example      Effect
────────  ───────────────────────  ──────────────
drums     Ground strobes, floods   Flash on hit
bass      Low elements, woofers    Pulse on note
vocals    Face/lip elements        Follow singing
guitar    Mid-height elements      Note accents
piano     Upper elements           Chord stabs
```

**Typical density:** 200–1000 marks per stem, depending on instrument activity

---

## L5: Dynamics

**What:** Continuous energy envelopes (0–100) per stem — how loud each instrument is over time.

**Source algorithms (per-stem):**
- `bbc_energy` — RMS energy
- `bbc_spectral_flux` — timbral change rate
- `amplitude_follower` — smoothed amplitude

**Output format:** ValueCurve objects at ~20 fps

```
drums energy:    ░░▓▓░░▓▓░░▓▓░░▓▓░░▓▓░░▓▓░░▓▓░░▓▓░░▓▓░░
bass energy:     ▓▓▓▓▓▓░░░░▓▓▓▓▓▓░░░░▓▓▓▓▓▓░░░░▓▓▓▓▓▓░░
vocals energy:   ░░░░░░▓▓▓▓▓▓▓▓░░░░░░▓▓▓▓▓▓▓▓░░░░▓▓▓▓▓▓
```

**xLights use:** Value curves drive dimmer levels directly — the light brightness follows the energy of its assigned stem. Exported as `.xvc` files.

**Relationship to L0:** L0 energy_impacts and energy_drops are derived from these curves by finding sharp derivatives.

---

## L6: Harmony

**What:** Chord progressions and key changes.

**Source algorithms:**
- `chordino_chords` — chord labels (C, Am, F, G)
- `qm_key` — key detection and modulation points

**Typical output:**
```
 0:00    0:03    0:06    0:09    0:12    0:15
  │  C   │  Am  │  F   │  G   │  C   │  ...
```

**xLights use:** Chord changes drive color palette shifts. One approach:
- Major chords → warm palette (red, orange, gold)
- Minor chords → cool palette (blue, purple, teal)
- Dominant 7ths → accent color (green, pink)
- Key changes → full palette reset

**Density:** Much sparser than beats — typically 0.5–2 changes per second of harmonic rhythm.

---

## How Levels Interact

The levels create a multi-scale timing framework:

```
L1 (Sections):    │ intro          │ verse                    │ chorus
                   │                │                          │
L2 (Bars):        │    |    |    | │    |    |    |    |    | │    |
                   │                │                          │
L3 (Beats):       │  | | | | | | | │ | | | | | | | | | | | | │ | | | |
                   │                │                          │
L4 (Events):      │ ||| || | || |  │||| || |||| ||| || ||||  │||||||||||
                   │                │                          │
L5 (Dynamics):    │ ~~~ low ~~~    │ ~~~~ building ~~~~       │ HIGH ~~~
                   │                │                          │
L6 (Harmony):     │  C    Am       │  F    G    C    Am       │ F  G
```

**Decision hierarchy for light effects:**
1. **L1** decides the overall scene (which effect theme)
2. **L2** decides when to advance within a scene (next sub-pattern)
3. **L3** decides the primary rhythm of effects
4. **L6** decides color at any moment
5. **L4** adds per-instrument detail and accent
6. **L5** modulates brightness continuously
7. **L0** triggers special moments (impacts, drops, gaps)

---

## Output Schema (2.0.0)

The `HierarchyResult` is saved as `*_hierarchy.json`:

```json
{
  "schema_version": "2.0.0",
  "source_file": "/path/to/song.mp3",
  "source_hash": "d17796b2cd4fea69...",
  "filename": "song.mp3",
  "duration_ms": 208110,
  "estimated_bpm": 116.0,
  "capabilities": {"vamp": true, "madmom": true, "demucs": true},
  "stems_available": ["drums", "bass", "vocals", "guitar", "piano", "other"],

  "energy_impacts": [...],
  "energy_drops": [...],
  "gaps": [...],

  "sections": [
    {"label": "intro", "start_ms": 0, "end_ms": 15000},
    {"label": "verse", "start_ms": 15000, "end_ms": 45000},
    ...
  ],

  "bars": {"name": "madmom_downbeats", "marks": [...], "quality_score": 0.95},
  "beats": {"name": "madmom_beats", "marks": [...], "quality_score": 0.98},

  "events": {
    "full_mix": {"name": "librosa_onsets", "marks": [...]},
    "drums": {"name": "aubio_onset", "marks": [...]},
    ...
  },

  "chords": {"name": "chordino_chords", "marks": [...]},
  "key_changes": {"name": "qm_key", "marks": [...]}
}
```

---

## Related Docs

- [Pipeline](pipeline.md) — How the hierarchy is assembled
- [Algorithm Categories](algorithm-categories.md) — Which algorithms feed each level
- [Quality Scoring](quality-scoring.md) — How the "best" algorithm is selected per level
- [Data Structures](data-structures.md) — TimingTrack, TimingMark, ValueCurve
