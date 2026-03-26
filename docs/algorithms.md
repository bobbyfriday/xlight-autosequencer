# Algorithm Reference

[< Back to Index](README.md) | See also: [Algorithm Categories](algorithm-categories.md) · [Stem Routing](stem-separation.md) · [Quality Scoring](quality-scoring.md)

This is the complete catalog of all analysis algorithms. Each algorithm takes a mono audio array and sample rate, and produces either a **TimingTrack** (discrete marks) or a **ValueCurve** (continuous 0–100 envelope).

---

## Summary Table

| # | Name | Library | Type | Stem | Output | What It Detects |
|---|------|---------|------|------|--------|-----------------|
| 1 | `librosa_beats` | librosa | beat | drums | marks | Beat pulse via onset strength |
| 2 | `librosa_bars` | librosa | bar | drums | marks | Bar downbeats (every 4th beat) |
| 3 | `librosa_onsets` | librosa | onset | full_mix | marks | Full-spectrum onset transients |
| 4 | `bass` | librosa | frequency | full_mix | marks | 20–250 Hz energy peaks |
| 5 | `mid` | librosa | frequency | full_mix | marks | 250–4000 Hz energy peaks |
| 6 | `treble` | librosa | frequency | full_mix | marks | 4000–20000 Hz energy peaks |
| 7 | `drums` | librosa | percussion | full_mix | marks | Percussive component onsets (HPSS) |
| 8 | `harmonic_peaks` | librosa | harmonic | full_mix | marks | Harmonic component onsets (HPSS) |
| 9 | `madmom_beats` | madmom | beat | drums | marks | RNN+DBN beat tracking |
| 10 | `madmom_downbeats` | madmom | bar | drums | marks | RNN+DBN downbeat tracking |
| 11 | `qm_beats` | vamp | beat | drums | marks | QM tempo tracker beats |
| 12 | `qm_bars` | vamp | bar | drums | marks | QM bar-beat tracker bars |
| 13 | `beatroot_beats` | vamp | beat | drums | marks | Multi-agent beat prediction |
| 14 | `qm_onsets_complex` | vamp | onset | drums | marks | Complex-domain phase onset |
| 15 | `qm_onsets_hfc` | vamp | onset | drums | marks | High-frequency content onset |
| 16 | `qm_onsets_phase` | vamp | onset | drums | marks | Phase deviation onset |
| 17 | `aubio_onset` | vamp | onset | drums | marks | Aubio mel-based onset |
| 18 | `aubio_tempo` | vamp | beat | drums | marks | Aubio beat tracking |
| 19 | `aubio_notes` | vamp | melody | vocals | marks | Aubio note transcription |
| 20 | `percussion_onsets` | vamp | onset | drums | marks | Percussion-specific transients |
| 21 | `bbc_rhythm` | vamp | onset | drums | marks | BBC rhythmic features |
| 22 | `pyin_notes` | vamp | melody | vocals | marks | Monophonic note events (pYIN) |
| 23 | `pyin_pitch_changes` | vamp | melody | vocals | marks | Pitch transition points |
| 24 | `chordino_chords` | vamp | harmonic | piano | marks | Chord recognition with labels |
| 25 | `nnls_chroma` | vamp | harmonic | piano | marks | Per-frame chromagram peaks |
| 26 | `qm_key` | vamp | harmonic | full_mix | marks | Key/tonality change events |
| 27 | `qm_segments` | vamp | structure | full_mix | marks | Section boundaries |
| 28 | `segmentino` | vamp | structure | full_mix | marks | Grouped section segmentation |
| 29 | `qm_tempo` | vamp | tempo | full_mix | marks | Tempo variation events |
| 30 | `qm_transcription` | vamp | melody | piano | marks | Polyphonic note transcription |
| 31 | `silvet_notes` | vamp | melody | piano | marks | Polyphonic transcription + velocity |
| 32 | `bbc_energy` | vamp | value_curve | full_mix | curve | RMS energy envelope |
| 33 | `bbc_spectral_flux` | vamp | value_curve | full_mix | curve | Spectral change rate |
| 34 | `bbc_peaks` | vamp | value_curve | drums | curve | Amplitude peak/trough envelope |
| 35 | `amplitude_follower` | vamp | value_curve | full_mix | curve | Smoothed amplitude envelope |
| 36 | `tempogram` | vamp | value_curve | drums | curve | Tempo stability over time |

---

## Librosa Algorithms (8)

These run **in the main process** (no subprocess needed). Always available — no optional dependencies.

### librosa_beats

**Purpose:** Detect the beat pulse of the music — the regular rhythm you'd tap your foot to.

**How it works:**
1. Computes onset strength envelope via `librosa.onset.onset_strength()`
2. Runs dynamic programming beat tracker via `librosa.beat.beat_track()`
3. Converts frame indices to millisecond timestamps

**Parameters:** `hop_length=512` (analysis window step size in samples)

**Preferred stem:** drums — isolating percussion gives cleaner beat detection

**Typical output:** 200–400 marks for a 3.5-minute song at 120 BPM

**Source:** `src/analyzer/algorithms/librosa_beats.py`

---

### librosa_bars

**Purpose:** Mark bar/measure boundaries — every Nth beat where N is the time signature denominator.

**How it works:**
1. Runs the same beat tracker as `librosa_beats`
2. Takes every 4th beat frame: `beat_frames[::beats_per_bar]`
3. Converts to millisecond timestamps

**Parameters:** `hop_length=512`, `beats_per_bar=4`

**Preferred stem:** drums

**Typical output:** 50–100 marks (one per bar)

**Source:** `src/analyzer/algorithms/librosa_beats.py`

---

### librosa_onsets

**Purpose:** Detect any sudden spectral change across all frequencies — note attacks, percussion hits, vocal entrances, etc.

**How it works:**
1. Computes onset strength with backtracking via `librosa.onset.onset_detect(backtrack=True)`
2. Backtracking snaps onsets to the nearest preceding energy minimum
3. Converts frame indices to timestamps

**Parameters:** `hop_length=512`

**Preferred stem:** full_mix — uses the complete audio to catch all instruments

**Typical output:** 300–600 marks

**Source:** `src/analyzer/algorithms/librosa_onset.py` (note: file is `librosa_onset.py`, singular)

---

### bass / mid / treble

**Purpose:** Detect energy peaks in specific frequency bands. These three algorithms split the spectrum into low, mid, and high ranges so different light groups can respond to different frequency content.

**How they work:**
1. Compute STFT with `n_fft=2048, hop_length=512`
2. Zero out frequency bins outside the target range
3. Compute onset strength over the band-limited spectrogram
4. Detect peaks in the band-specific onset envelope

**Frequency ranges:**

```
bass:   ████████░░░░░░░░░░░░░░░░░░░░░░░░  20 – 250 Hz
mid:    ░░░░░░░░████████████████░░░░░░░░░░  250 – 4,000 Hz
treble: ░░░░░░░░░░░░░░░░░░░░░░░░████████░░  4,000 – 20,000 Hz
```

**Preferred stem:** full_mix — band filtering already isolates the frequency content

**Typical output:** bass ~900, mid ~250, treble ~470 marks

**Source:** `src/analyzer/algorithms/librosa_bands.py`

---

### drums

**Purpose:** Isolate and detect percussive transients using Harmonic-Percussive Source Separation.

**How it works:**
1. Runs `librosa.effects.hpss()` to split audio into harmonic and percussive components
2. Takes the **percussive** component
3. Detects onsets in the percussion-only signal

**Parameters:** `hop_length=512`

**Preferred stem:** full_mix — HPSS does its own separation; feeding it the drums stem would double-separate

**Typical output:** 400–600 marks

**Note:** This is different from feeding audio to onset detectors on the drums stem. HPSS is a spectral median-filtering technique that separates sustained tones from transients.

**Source:** `src/analyzer/algorithms/librosa_hpss.py`

---

### harmonic_peaks

**Purpose:** Detect harmonic/melodic onsets — sustained notes, chord changes, and tonal events.

**How it works:**
1. Runs `librosa.effects.hpss()` (same as `drums` above)
2. Takes the **harmonic** component
3. Detects onsets in the harmony-only signal

**Parameters:** `hop_length=512`

**Preferred stem:** full_mix

**Typical output:** 300–500 marks

**Source:** `src/analyzer/algorithms/librosa_hpss.py`

---

## Madmom Algorithms (2)

These use deep learning models (RNN + Dynamic Bayesian Network). They run in the **subprocess** (`.venv-vamp`, numpy<2). Optional — the system works without them but beat accuracy improves significantly with madmom.

### madmom_beats

**Purpose:** Beat tracking using a neural network trained on annotated beat data. Generally more accurate than signal-processing approaches on complex rhythms.

**How it works:**
1. `RNNBeatProcessor()` — runs a recurrent neural network that produces a beat activation function (probability of beat at each frame)
2. `BeatTrackingProcessor(fps=100)` — dynamic programming (Viterbi) to find the optimal beat sequence given the activations and a tempo model

**Preferred stem:** drums

**Typical output:** 200–400 marks, very regular spacing

**Why it's better:** The RNN was trained on human-annotated data, so it understands musical context (syncopation, fills, tempo changes) that pure signal processing misses.

**Source:** `src/analyzer/algorithms/madmom_beat.py`

---

### madmom_downbeats

**Purpose:** Identify bar-level downbeats (beat 1 of each measure) using a separate RNN trained to distinguish beat positions.

**How it works:**
1. `RNNDownBeatProcessor()` — RNN that outputs per-frame probabilities for each beat position
2. `DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)` — joint tempo/meter tracking that handles both 3/4 and 4/4 time
3. Filters output to `beat_position == 1` (downbeats only)

**Preferred stem:** drums

**Typical output:** 50–100 marks (one per bar)

**Source:** `src/analyzer/algorithms/madmom_beat.py`

---

## Vamp Beat Tracking (3)

These use the Vamp plugin host to run C/C++ audio analysis plugins. All run in the subprocess.

### qm_beats

**Purpose:** Beat tracking via the Queen Mary tempo tracker — a well-established spectral autocorrelation approach.

**Plugin:** `qm-vamp-plugins:qm-tempotracker` → output `beats`

**How it works:** Spectral onset detection → autocorrelation for tempo estimation → dynamic programming for beat alignment

**Preferred stem:** drums

**Typical output:** 200–400 marks

---

### qm_bars

**Purpose:** Bar/measure boundary detection from the QM bar-beat tracker.

**Plugin:** `qm-vamp-plugins:qm-barbeattracker` → output `bars`

**How it works:** Similar to QM beats but with a higher-level metrical model that groups beats into bars

**Preferred stem:** drums

**Typical output:** 50–100 marks

---

### beatroot_beats

**Purpose:** Beat tracking using the BeatRoot multi-agent model — good on swing rhythms and syncopation.

**Plugin:** `beatroot-vamp:beatroot` → output `beats`

**How it works:** Multiple "agents" track different tempo hypotheses simultaneously, and the most consistent one wins. This makes it robust to tempo fluctuations and rubato.

**Preferred stem:** drums

**Typical output:** 200–400 marks

---

## Vamp Onset Detectors (3 + 2)

Three algorithms from the QM onset detector plugin using different spectral difference functions, plus aubio and percussion-specific detectors.

### qm_onsets_complex

**Plugin:** `qm-vamp-plugins:qm-onsetdetector` with `dftype=3` (Complex Domain)

**How it works:** Measures deviation from expected magnitude+phase in the complex STFT. Sensitive to both energy and phase changes — good all-around detector.

**Preferred stem:** drums | **Typical output:** ~900 marks

---

### qm_onsets_hfc

**Plugin:** `qm-vamp-plugins:qm-onsetdetector` with `dftype=0` (High-Frequency Content)

**How it works:** Sums frequency-weighted high bins. Fast and responsive to percussive attacks which have strong high-frequency content.

**Preferred stem:** drums | **Typical output:** ~700 marks

---

### qm_onsets_phase

**Plugin:** `qm-vamp-plugins:qm-onsetdetector` with `dftype=2` (Phase Deviation)

**How it works:** Measures how much phase differs from the expected linear progression. Onsets cause phase discontinuities across frequency bins.

**Preferred stem:** drums | **Typical output:** ~365 marks (fewer, more conservative)

---

### aubio_onset

**Plugin:** `vamp-aubio:aubioonset`

**How it works:** Aubio's mel-scaled onset detection — a lightweight, low-latency detector that balances speed and accuracy.

**Preferred stem:** drums | **Typical output:** ~500 marks

---

### percussion_onsets

**Plugin:** `vamp-example-plugins:percussiononsets`

**How it works:** Specialized for drum/percussion transients. Higher sensitivity to sharp attacks, ignores sustained pitch and noise.

**Preferred stem:** drums | **Typical output:** ~370 marks

---

### bbc_rhythm

**Plugin:** `bbc-vamp-plugins:bbc-rhythm`

**How it works:** BBC rhythm feature extraction. Produces discrete rhythmic event marks (unlike the other BBC plugins which produce continuous curves).

**Preferred stem:** drums | **Typical output:** ~35,000 marks (very dense — 5ms spacing, essentially a rhythm activation curve discretized into marks)

**Note:** This produces far more marks than typical onset detectors. It's closer to a continuous signal than a sparse event list.

---

## Vamp Pitch & Melody (5)

### pyin_notes

**Purpose:** Detect individual note events in monophonic audio (one note at a time).

**Plugin:** `pyin:pyin` → output `notes`

**How it works:** Probabilistic YIN (pYIN) tracks the fundamental frequency frame-by-frame using a hidden Markov model over multiple YIN candidates. The `notes` output segments the pitch track into discrete note events.

**Preferred stem:** vocals — pYIN works best on monophonic sources

**Typical output:** 100–300 marks

---

### pyin_pitch_changes

**Purpose:** Mark points where the pitch changes significantly — melodic transitions, interval jumps, vibrato peaks.

**Plugin:** `pyin:pyin` → output `smoothedpitchtrack`

**How it works:**
1. Gets the smoothed pitch contour (Hz per frame)
2. Computes frame-to-frame pitch difference
3. Marks frames where pitch changes by more than ~10 cents

**Preferred stem:** vocals

**Typical output:** 200–500 marks (more than `pyin_notes` because it catches ornamental pitch movement)

---

### aubio_notes

**Plugin:** `vamp-aubio:aubionotes`

**How it works:** Aubio's note tracker — works on both monophonic and simple polyphonic material. Outputs onset time + pitch + duration per note.

**Preferred stem:** vocals | **Typical output:** ~370 marks

---

### qm_transcription

**Purpose:** Polyphonic note transcription — detect multiple simultaneous notes (e.g., piano chords, guitar strumming).

**Plugin:** `qm-vamp-plugins:qm-transcription`

**Preferred stem:** piano

**Typical output:** ~1,176 marks — **many are co-temporal** (same timestamp, different pitches). This is expected for polyphonic content but means 53%+ of intervals are <50ms.

**Known issue:** Produces many 0ms-gap "duplicate" marks because each note of a chord gets its own mark at the same timestamp. Consider deduplication before using for light timing.

---

### silvet_notes

**Purpose:** High-quality polyphonic note transcription with velocity information.

**Plugin:** `silvet:silvet`

**Preferred stem:** piano

**Typical output:** ~600 marks — fewer than `qm_transcription` but still has co-temporal duplicates from polyphonic detection.

---

## Vamp Harmony (3)

### chordino_chords

**Purpose:** Recognize chord changes and label them (e.g., "C maj", "Am", "G7").

**Plugin:** `nnls-chroma:chordino` → output `simplechord`

**How it works:** NNLS chroma extraction → template matching against chord profiles → returns change points with chord name labels.

**Preferred stem:** piano — cleaner harmonic content

**Typical output:** ~100 marks with labels like "C", "Am", "F", "G"

---

### nnls_chroma

**Purpose:** Dense chromagram — 12-bin pitch class distribution per frame. Shows which notes are present at each moment.

**Plugin:** `nnls-chroma:nnls-chroma` → output `chroma`

**How it works:** Non-negative Least Squares pitch estimation produces a 12-element vector (one per semitone C through B) for each analysis frame.

**Preferred stem:** piano

**Typical output:** ~4,500 marks at 46ms spacing — essentially a continuous pitch-class signal discretized into marks.

---

### qm_key

**Purpose:** Detect key/tonality and mark modulation points (key changes).

**Plugin:** `qm-vamp-plugins:qm-keydetector`

**Preferred stem:** full_mix

**Typical output:** 5–20 marks (most songs have few key changes)

---

## Vamp Structure (3)

### qm_segments

**Purpose:** Find song section boundaries — where does the verse end and chorus begin?

**Plugin:** `qm-vamp-plugins:qm-segmenter` → output `segmentation`

**How it works:** Computes a self-similarity matrix from spectral features, then finds novelty peaks that indicate structural transitions.

**Preferred stem:** full_mix | **Typical output:** 5–15 marks

---

### segmentino

**Purpose:** Advanced song structure segmentation with section grouping — identifies which sections are repetitions of each other.

**Plugin:** `segmentino:segmentino`

**How it works:** Self-similarity analysis that not only finds section boundaries but labels repeated sections (e.g., "A1", "B", "A2", "C", "A3").

**Preferred stem:** full_mix

**Typical output:** 5–15 marks with labels and durations

---

### qm_tempo

**Purpose:** Track tempo variations over time — tempo acceleration, deceleration, and rubato.

**Plugin:** `qm-vamp-plugins:qm-tempotracker` → output `tempo`

**Preferred stem:** full_mix

**Typical output:** Tempo change events (sparse for steady-tempo songs)

---

## Value Curve Algorithms (5)

These produce **continuous envelopes** (0–100 per frame) rather than discrete timing marks. They're stored as `ValueCurve` objects and exported as `.xvc` files for xLights.

```
Value curves sample the audio at a fixed frame rate and produce a
continuous intensity value. They drive smooth dimming/brightening
effects rather than on/off triggers.

    100 ┤         ╭─╮
        │        ╭╯ ╰╮     ╭──╮
     50 ┤  ╭─╮  │    │   ╭╯  ╰─╮
        │ ╭╯ ╰──╯    ╰───╯     ╰──
      0 ┤─╯
        └──────────────────────────── time
```

### bbc_energy

**Purpose:** RMS energy envelope — overall loudness over time.

**Plugin:** `bbc-vamp-plugins:bbc-energy`

**Frame rate:** ~20 fps (50ms per frame) | **Preferred stem:** full_mix

**Use case:** Drive overall brightness of all lights proportional to song energy.

---

### bbc_spectral_flux

**Purpose:** Rate of spectral change — how much the timbre is changing frame-to-frame.

**Plugin:** `bbc-vamp-plugins:bbc-spectral-flux`

**Frame rate:** ~20 fps | **Preferred stem:** full_mix

**Use case:** High spectral flux = lots of timbral change (transitions, builds). Low = steady state. Good for triggering color changes or effect switches.

---

### bbc_peaks

**Purpose:** Amplitude peak/trough detection — envelope of local maxima.

**Plugin:** `bbc-vamp-plugins:bbc-peaks`

**Frame rate:** ~20 fps | **Preferred stem:** drums

**Use case:** Drive percussive light effects that follow the amplitude envelope of the drum track.

---

### amplitude_follower

**Purpose:** Smoothed amplitude envelope with attack/release dynamics.

**Plugin:** `vamp-example-plugins:amplitudefollower`

**Frame rate:** ~20 fps | **Preferred stem:** full_mix

**Use case:** Similar to `bbc_energy` but with built-in smoothing that prevents jittery rapid changes. Good for smooth fading effects.

---

### tempogram

**Purpose:** Tempo stability visualization — shows how consistent the rhythmic pulse is over time.

**Plugin:** `tempogram:tempogram`

**Frame rate:** ~20 fps | **Preferred stem:** drums

**How it works:** Computes autocorrelation-based tempogram (tempo bins × time), averages across tempo bins to produce a single confidence-of-tempo curve.

**Use case:** High values = strong, steady beat. Low values = breakdown, rubato, or silence. Could gate beat-synced effects.

---

## Algorithm Availability

Not all algorithms run every time. Availability depends on installed software:

| Requirement | Algorithms | Install |
|-------------|-----------|---------|
| **Always available** | 8 librosa algorithms | `pip install librosa` |
| **Vamp plugins** | ~25 vamp algorithms | Vamp host + plugin .dylib files |
| **madmom** | 2 madmom algorithms | `pip install madmom` (numpy<2) |
| **demucs** | Stem separation routing | `pip install demucs` + torch |

The orchestrator auto-detects what's installed and builds the algorithm list accordingly. See [Architecture Overview](architecture-overview.md) for the two-process setup.

---

## Related Docs

- [Algorithm Categories](algorithm-categories.md) — Algorithms grouped by purpose
- [Stem Separation & Routing](stem-separation.md) — Which stem each algorithm analyzes
- [Quality Scoring](quality-scoring.md) — How output is scored
- [Sweep System](sweep-system.md) — Automated parameter tuning
