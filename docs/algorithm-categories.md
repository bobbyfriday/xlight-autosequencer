# Algorithm Categories

[< Back to Index](README.md) | See also: [Algorithm Reference](algorithms.md) · [Hierarchy Levels](hierarchy.md)

Algorithms are grouped into categories based on the type of musical information they extract. Each category has its own [scoring profile](quality-scoring.md) with appropriate density and regularity ranges.

---

## Beat Trackers

**Purpose:** Find the regular rhythmic pulse — where you'd clap or tap your foot.

**xLights use:** Synchronize on/off flash effects, chase sequences, and strobes to the beat.

```
Audio:    ♩    ♩    ♩    ♩    ♩    ♩    ♩    ♩
Beats:    |    |    |    |    |    |    |    |
          0   500  1000 1500 2000 2500 3000 3500  (ms)
```

| Algorithm | Library | Approach | Strengths |
|-----------|---------|----------|-----------|
| `librosa_beats` | librosa | Onset strength + dynamic programming | Fast, always available |
| `madmom_beats` | madmom | RNN + DBN (neural network) | Most accurate on complex rhythms |
| `qm_beats` | vamp | Spectral autocorrelation | Stable on metrically regular music |
| `beatroot_beats` | vamp | Multi-agent model | Good on swing and syncopation |
| `aubio_tempo` | vamp | Time-domain beat tracking | Lightweight, good supplementary |

**How they compare:**
- `madmom_beats` generally produces the most musically accurate beats, especially on songs with fills, breaks, or tempo changes
- `librosa_beats` is the reliable fallback — always available, good enough for most pop/rock
- `qm_beats` and `beatroot_beats` provide alternative perspectives; the sweep system tests which works best per song
- The orchestrator picks the **best-scoring beat track** for L3 of the hierarchy

**Typical density:** 1–4 marks/second (60–240 BPM range)

---

## Bar/Downbeat Trackers

**Purpose:** Find measure boundaries — the "ONE" of each bar.

**xLights use:** Trigger scene changes, color palette shifts, or effect transitions at bar boundaries. Bars define the medium-scale structure that prevents effects from changing too frequently.

```
Beats:    |    |    |    |    |    |    |    |    |    |    |    |
Bars:     |              |              |              |
          ▼              ▼              ▼              ▼
          1  2  3  4     1  2  3  4     1  2  3  4     1  2  3  4
```

| Algorithm | Library | Approach |
|-----------|---------|----------|
| `librosa_bars` | librosa | Every 4th librosa beat |
| `madmom_downbeats` | madmom | RNN downbeat classifier (3/4 and 4/4) |
| `qm_bars` | vamp | QM bar-beat tracker |

**How they compare:**
- `madmom_downbeats` is the only one that truly classifies beat position — it knows whether a beat is 1, 2, 3, or 4
- `librosa_bars` simply divides beats by 4, which can drift if the beat tracker skips or adds a beat
- `qm_bars` uses a metrical model that's more sophisticated than dividing by 4

**Typical density:** 0.2–1.0 marks/second

---

## Onset Detectors

**Purpose:** Find note attacks, transients, and any sudden spectral change — the individual "events" in the music.

**xLights use:** Drive per-note effects, accent lights, and reactive patterns that respond to every musical event. Onsets are the most granular timing data.

```
Audio: ♩  ♪♪  ♩  ♬♬♬  ♩    ♩  ♪♪  ♩
Onsets: |  ||  |  |||  |    |  ||  |
```

| Algorithm | Library | Method | Character |
|-----------|---------|--------|-----------|
| `librosa_onsets` | librosa | Full-spectrum onset strength | Catches everything |
| `qm_onsets_complex` | vamp | Complex-domain STFT | Good all-around |
| `qm_onsets_hfc` | vamp | High-frequency content | Fast, percussion-biased |
| `qm_onsets_phase` | vamp | Phase deviation | Conservative, fewer marks |
| `aubio_onset` | vamp | Mel-scaled onset | Balanced speed/accuracy |
| `percussion_onsets` | vamp | Percussion-specific | Ignores sustained tones |
| `bbc_rhythm` | vamp | Rhythmic features | Very dense (~5ms spacing) |

**How they compare:**
- `qm_onsets_complex` is the most balanced — it catches both percussive and tonal onsets
- `qm_onsets_hfc` is biased toward high-frequency attacks (cymbals, hi-hats, consonants)
- `qm_onsets_phase` is the most conservative — fewer false positives but misses subtle events
- `percussion_onsets` only catches drum/percussion hits
- `bbc_rhythm` is special — it's essentially a continuous rhythm activation at ~200 Hz, not a sparse onset list

**Typical density:** 1–8 marks/second (varies widely by musical density)

---

## Frequency Band Analyzers

**Purpose:** Split the spectrum into low/mid/high and detect peaks in each. Lets different light groups respond to different instruments.

**xLights use:** Map bass to floor-level lights, mid to tree-level, treble to star/arch lights. Creates visual frequency separation.

```
Treble: ░░░░░░░░░░░░░░░░░░░░░░░░████████░░  4k–20k Hz  → Arches, stars
Mid:    ░░░░░░░░████████████████░░░░░░░░░░░░  250–4k Hz  → Trees, megatree
Bass:   ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  20–250 Hz  → Ground, floods
```

| Algorithm | Frequency Range | Typical Marks |
|-----------|----------------|---------------|
| `bass` | 20–250 Hz | ~900 (kick drum, bass guitar) |
| `mid` | 250–4,000 Hz | ~250 (vocals, guitar, keys) |
| `treble` | 4,000–20,000 Hz | ~470 (cymbals, sibilance, brightness) |

**Note:** These use the full mix rather than stems because the band-pass filtering already isolates the frequency content. Using the drums stem with the bass algorithm would miss the bass guitar.

---

## Percussion Analyzers

**Purpose:** Isolate drum and percussive events from the rest of the music.

**xLights use:** Drive strobe effects, flash groups, and any "hit" response that should follow the drummer.

| Algorithm | Method |
|-----------|--------|
| `drums` (librosa) | HPSS percussive component → onset detection |
| `percussion_onsets` (vamp) | Vamp percussion-specific onset detection |
| `bbc_peaks` (vamp) | Amplitude peak envelope of drums stem (value curve) |

**`drums` vs `percussion_onsets`:** The librosa `drums` algorithm uses HPSS (Harmonic-Percussive Source Separation) on the full mix, while `percussion_onsets` runs a dedicated percussion onset detector on the drums stem. They complement each other — HPSS catches percussive events that leak into other stems, while `percussion_onsets` is more precise on isolated drums.

---

## Melody & Pitch Analyzers

**Purpose:** Track the vocal melody, note events, and pitch transitions.

**xLights use:** Sync lip-sync phoneme effects to vocal timing, or create melodic light patterns that follow the singer.

| Algorithm | Polyphony | Source |
|-----------|-----------|--------|
| `pyin_notes` | Monophonic | Vocals stem |
| `pyin_pitch_changes` | Monophonic | Vocals stem |
| `aubio_notes` | Simple poly | Vocals stem |
| `qm_transcription` | Full polyphonic | Piano stem |
| `silvet_notes` | Full polyphonic | Piano stem |

**Monophonic vs polyphonic:**
- `pyin_*` algorithms assume one note at a time — ideal for vocals
- `qm_transcription` and `silvet_notes` detect multiple simultaneous notes — ideal for piano/guitar chords
- Polyphonic detectors produce co-temporal marks (multiple marks at the same timestamp for chord notes)

---

## Harmony Analyzers

**Purpose:** Identify chord progressions, key signatures, and harmonic rhythm.

**xLights use:** Drive color palette changes — each chord or key gets a color family. Harmonic rhythm is slower than beat rhythm, creating medium-scale visual structure.

| Algorithm | What It Detects |
|-----------|----------------|
| `chordino_chords` | Chord changes with labels (C, Am, F, G) |
| `nnls_chroma` | 12-bin pitch class distribution per frame |
| `qm_key` | Key/tonality changes (modulations) |

**`chordino_chords`** is the most directly useful — it labels each chord change, so you could map "major chords = warm colors, minor chords = cool colors."

**`qm_key`** is very sparse (most songs have 0–3 key changes) but marks major structural transitions.

---

## Structure Analyzers

**Purpose:** Find song section boundaries — intro, verse, chorus, bridge, outro.

**xLights use:** The highest-level timing data. Defines which "scene" the light show is in. Different sections get different effect themes and intensity levels.

| Algorithm | Approach |
|-----------|----------|
| `qm_segments` | Spectral self-similarity novelty curve |
| `segmentino` | Self-similarity with section grouping (labels repeats) |

**`segmentino`** is more sophisticated — it not only finds boundaries but labels which sections are repetitions of each other (A1, B, A2 means the first and third sections are similar). This is valuable for ensuring the same light patterns appear during repeated choruses.

**Typical output:** 5–15 segments for a pop song

---

## Value Curve Analyzers

**Purpose:** Produce continuous 0–100 intensity envelopes rather than discrete timing marks.

**xLights use:** Drive dimmer levels, color intensity, and smooth animation effects. Value curves create organic-feeling brightness changes rather than on/off switching.

```
Mark-based (beats):    |    |    |    |    |    |
Curve-based (energy):  ~~~╱‾‾‾‾╲__╱‾‾╲___╱‾‾‾‾‾╲~~
```

| Algorithm | What It Measures | Stem |
|-----------|-----------------|------|
| `bbc_energy` | RMS loudness | full_mix |
| `bbc_spectral_flux` | Timbral change rate | full_mix |
| `bbc_peaks` | Amplitude peaks | drums |
| `amplitude_follower` | Smoothed amplitude | full_mix |
| `tempogram` | Tempo stability | drums |

These are all sampled at ~20 fps (50ms per frame) and normalized to integer values 0–100. They're exported as `.xvc` (xLights Value Curve) files.

---

## How Categories Map to Hierarchy Levels

```
Category              Hierarchy Level    Scale
────────────────────  ─────────────────  ──────────────
Structure             L1 Sections        Song-level
Bars                  L2 Bars            Measure-level
Beats                 L3 Beats           Beat-level
Onsets, Percussion,   L4 Events          Sub-beat
  Frequency Bands
Value Curves          L5 Dynamics        Continuous
Harmony, Melody       L6 Harmony         Varies
```

See [Hierarchy Levels](hierarchy.md) for how the orchestrator assembles the best algorithm from each category into the 7-level structure.

---

## Related Docs

- [Algorithm Reference](algorithms.md) — Full details on each algorithm
- [Hierarchy Levels](hierarchy.md) — How categories map to L0–L6
- [Quality Scoring](quality-scoring.md) — Category-specific scoring ranges
