# Stem Separation & Routing

[< Back to Index](README.md) | See also: [Algorithm Reference](algorithms.md) · [Pipeline](pipeline.md)

Stem separation splits a mixed audio file into individual instrument tracks. This dramatically improves algorithm accuracy — a beat tracker on isolated drums isn't confused by melodic rhythm, and a chord detector on isolated piano isn't distorted by drum harmonics.

---

## Demucs htdemucs_6s Model

The system uses Meta's **demucs** model (`htdemucs_6s`) which separates audio into **6 stems** in a single pass:

```
                        ┌─────────────────────┐
                        │    Input: song.mp3    │
                        │    (full stereo mix)  │
                        └──────────┬──────────┘
                                   │
                          demucs htdemucs_6s
                          (hybrid transformer)
                                   │
          ┌────────┬───────┬───────┼───────┬────────┬────────┐
          ▼        ▼       ▼       ▼       ▼        ▼        ▼
       drums     bass   vocals  guitar   piano    other   full_mix
                                                          (original)
```

**Output:** 6 mono float32 MP3 files + 1 full_mix (the original audio unchanged).

**Cache location:** `.stems/<md5>/` adjacent to the source file

```
Song Name/
  ├── stems/
  │   ├── manifest.json    ← source_hash, model name, timestamps
  │   ├── drums.mp3
  │   ├── bass.mp3
  │   ├── vocals.mp3
  │   ├── guitar.mp3
  │   ├── piano.mp3
  │   └── other.mp3
  ├── song_hierarchy.json
  └── ...
```

---

## Stem Affinity Table

Each algorithm declares a `preferred_stem` — the stem it should analyze for best results. The orchestrator routes each algorithm to its preferred stem.

### Beat & Bar Algorithms → drums

```
Algorithm            Preferred Stem    Why
───────────────────  ────────────────  ────────────────────────────────────
librosa_beats        drums             Kick and snare define the beat pulse
librosa_bars         drums             Downbeats clearest in percussion
madmom_beats         drums             RNN trained on percussive features
madmom_downbeats     drums             Downbeat distinction clearest in drums
qm_beats             drums             Spectral autocorrelation of drums
qm_bars              drums             Metrical model on drum pattern
beatroot_beats       drums             Multi-agent beat tracking on drums
aubio_tempo          drums             Beat detection from percussive attacks
```

### Onset & Percussion Algorithms → drums (mostly)

```
Algorithm            Preferred Stem    Why
───────────────────  ────────────────  ────────────────────────────────────
qm_onsets_complex    drums             Percussive onsets have strong transients
qm_onsets_hfc        drums             High-freq content rich in cymbals
qm_onsets_phase      drums             Phase breaks at drum attacks
aubio_onset          drums             Mel-scaled onsets clearest in drums
percussion_onsets    drums             Designed specifically for percussion
bbc_rhythm           drums             Rhythm features from drum pattern
librosa_onsets       full_mix          Catches ALL instruments' onsets
```

**Note:** `librosa_onsets` intentionally uses `full_mix` to capture onsets from every instrument, complementing the drum-focused onset detectors.

### Pitch & Melody Algorithms → vocals

```
Algorithm            Preferred Stem    Why
───────────────────  ────────────────  ────────────────────────────────────
pyin_notes           vocals            pYIN needs monophonic input
pyin_pitch_changes   vocals            Pitch contour is the vocal melody
aubio_notes          vocals            Note detection on vocal line
```

### Harmony Algorithms → piano

```
Algorithm            Preferred Stem    Why
───────────────────  ────────────────  ────────────────────────────────────
chordino_chords      piano             Harmonic content clearest in keys
nnls_chroma          piano             Chromagram from harmonic instruments
qm_transcription     piano             Polyphonic transcription of chords
silvet_notes         piano             Note transcription on harmonic audio
```

### Full-Mix Algorithms

```
Algorithm            Preferred Stem    Why
───────────────────  ────────────────  ────────────────────────────────────
bass                 full_mix          Band-pass filter already isolates bass
mid                  full_mix          Band-pass filter isolates mid freqs
treble               full_mix          Band-pass filter isolates treble
drums (HPSS)         full_mix          HPSS does its own percussive split
harmonic_peaks       full_mix          HPSS does its own harmonic split
qm_segments          full_mix          Structure needs full spectral context
segmentino           full_mix          Section detection uses all instruments
qm_tempo             full_mix          Tempo from overall rhythmic content
qm_key               full_mix          Key detection uses all harmonic info
bbc_energy           full_mix          Overall loudness envelope
bbc_spectral_flux    full_mix          Timbral change across all instruments
amplitude_follower   full_mix          Overall amplitude envelope
```

### Diagram: Stem Routing

```
                    ┌─────────────────────────────────────────┐
                    │              ALGORITHMS                   │
                    └─────────────────────────────────────────┘

drums ─────────────── beat trackers (5), onset detectors (6)
  │                   percussion_onsets, bbc_peaks, bbc_rhythm
  │                   tempogram
  │
bass ─────────────── (supplementary for beat trackers in sweep)
  │
vocals ───────────── pyin_notes, pyin_pitch_changes, aubio_notes
  │                   (+ phoneme analysis via WhisperX)
  │
guitar ───────────── (onset detectors in L4 per-stem sweep)
  │
piano ────────────── chordino, nnls_chroma, qm_transcription
  │                   silvet_notes
  │
other ────────────── (onset detectors in L4 per-stem sweep)
  │
full_mix ─────────── frequency bands (3), HPSS (2), structure (2)
                      energy curves (3), key detection, tempo
                      librosa_onsets
```

---

## Stem Inspection

Before running algorithms, you can inspect stem quality:

```bash
xlight-analyze stem-inspect song.mp3
```

This evaluates each stem and produces a verdict:

| Metric | What It Measures |
|--------|-----------------|
| RMS dB | Average loudness — is there actual content? |
| Crest dB | Peak-to-average ratio — is it dynamic? |
| Coverage % | What fraction of the song has content above noise floor |
| Spectral centroid Hz | Center of frequency mass — sanity check for stem type |

**Verdicts:**
- **KEEP** — Good content, use this stem
- **REVIEW** — Marginal content, worth checking manually
- **SKIP** — Too quiet or empty, don't waste algorithms on it

Example output:
```
Stem      RMS dB   Crest dB   Coverage   Centroid    Verdict
────────  ───────  ────────   ────────   ─────────   ───────
drums     -18.2    12.4       95%        2,340 Hz    KEEP
bass      -22.1    10.8       88%          180 Hz    KEEP
vocals    -19.5    14.2       72%        1,250 Hz    KEEP
guitar    -28.4     8.1       45%        1,800 Hz    REVIEW
piano     -35.2     6.3       22%        3,100 Hz    SKIP
other     -31.0     7.5       38%        2,800 Hz    REVIEW
```

---

## Why Stem Separation Matters

Without stems, all algorithms analyze the same mixed audio. With stems:

1. **Beat tracking improves** — drum attacks are unambiguous when bass and vocals are removed
2. **Chord detection improves** — piano harmonics aren't muddied by drum resonance
3. **Per-instrument lighting** — different light groups can follow different instruments
4. **Sweep optimization** — the sweep matrix tests each algorithm on multiple stems to find the best pairing

**Trade-off:** Stem separation adds ~30–60 seconds of processing time (GPU) or several minutes (CPU-only) but the results are cached and reused across all subsequent analysis runs.

---

## Related Docs

- [Algorithm Reference](algorithms.md) — Individual algorithm details
- [Pipeline](pipeline.md) — Where stem separation fits in the pipeline
- [Sweep System](sweep-system.md) — Testing algorithm×stem combinations
