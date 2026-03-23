# Research: Audio Analysis and Timing Track Generation

**Branch**: `001-audio-timing-tracks` | **Date**: 2026-03-22

---

## Decision 1: Language

**Decision**: Python 3.11+

**Rationale**: Python has the most mature ecosystem for audio analysis (librosa, madmom,
aubio, essentia all have Python bindings). NumPy/SciPy underpin all of them. The
xLights community also has Python scripting support. No other language comes close
for the breadth of audio analysis libraries available.

**Alternatives considered**:
- JavaScript/Node: Limited audio DSP ecosystem; no equivalent to librosa.
- Rust: Excellent performance but immature audio analysis library ecosystem.
- C++: Used internally by aubio/essentia but too much friction for rapid iteration.

---

## Decision 2: Primary Audio Analysis Framework

**Decision**: Vamp plugins (via the `vamp` Python package) as the primary analysis
framework, supplemented by librosa 0.10+ for spectral/band analysis and madmom 0.16+
for neural-net beat tracking.

**Rationale**:

Vamp (vamp-plugins.org) is a plugin architecture for audio analysis algorithms,
developed at Queen Mary University of London. It provides a standardized interface
that dozens of well-validated analysis algorithms implement. Key advantages:
- Runs entirely offline; plugins are local shared libraries
- Each plugin outputs event/feature timestamps directly — no post-processing needed
  to extract timing marks
- The plugin ecosystem covers beat tracking, onset detection, pitch, chords, structure,
  and more in a single unified API
- The `vamp` Python package (`pip install vamp`) wraps the Vamp host SDK and loads
  plugins from the system plugin directory (`~/Library/Audio/Plug-Ins/Vamp/` on macOS)

**Key plugin packs used**:

| Pack | Install | Algorithms provided |
|------|---------|-------------------|
| QM Vamp Plugins | qm-vamp-plugins (.dylib) | Beat, bar, onset, tempo, segmentation, chroma, MFCC |
| BeatRoot Vamp | beatroot-vamp (.dylib) | BeatRoot induction beat tracker |
| pYIN | pyin (.dylib) | Probabilistic YIN pitch tracker (note events) |
| NNLS Chroma + Chordino | nnls-chroma (.dylib) | Chroma features, chord change detection |
| Tony / Silvet | silvet (.dylib) | Polyphonic note transcription |

librosa supplements Vamp for:
- Frequency band energy peaks (bass/mid/treble) — not covered by Vamp plugins
- HPSS (Harmonic-Percussive Source Separation) for drum isolation

madmom supplements Vamp for:
- RNN+DBN beat tracking — neural-net accuracy that outperforms all Vamp beat trackers
  on complex rhythms; provides a high-quality comparison track alongside Vamp beat outputs

**Alternatives considered**:
- librosa-only: Only 9 track types possible; Vamp gives access to 15+ additional
  algorithms without custom implementation.
- essentia (MTG Barcelona): Comprehensive but complex C++ build; Vamp covers the same
  algorithms via standardized plugins already compiled and distributed.
- aubio: Good onset/beat library but no plugin architecture; adding it would add a
  dependency for 1-2 tracks that Vamp plugins already cover better.

---

## Decision 3: MP3 Loading

**Decision**: Use librosa's built-in loading (`librosa.load()`), which delegates to
soundfile + audioread. audioread handles MP3 via ffmpeg.

**Dependency**: ffmpeg must be installed on the system (standard on macOS via Homebrew:
`brew install ffmpeg`). This is a documented prerequisite, not bundled.

**Rationale**: librosa.load() returns a normalized float32 numpy array and sample rate,
which is the universal input format for every algorithm we use. Loading once and passing
the array through eliminates redundant file I/O.

**Alternatives considered**:
- pydub: Higher-level but adds a dependency; librosa.load() is sufficient.
- torchaudio: Brings in PyTorch — massive dependency for a CLI tool.

---

## Decision 4: Algorithm Set (Timing Track Types)

**Decision**: 22 tracks produced by default from a single run, drawn from Vamp plugins,
librosa, and madmom. The user then picks the top N via `--top N` or manual selection.

**From QM Vamp Plugins**:

| Track Name | Vamp Key | Element Type | What It Captures |
|------------|----------|--------------|-----------------|
| `qm_beats` | qm-barbeattracker:beats | beat | QM bar-beat tracker — quarter-note beat grid |
| `qm_bars` | qm-barbeattracker:bars | bar | QM bar-beat tracker — bar/downbeat positions |
| `qm_tempo_changes` | qm-tempotracker:tempo | tempo | Points where tempo changes significantly |
| `qm_onsets_complex` | qm-onsetdetector:onsets (complex domain) | onset | Onset detection via complex domain method |
| `qm_onsets_hfc` | qm-onsetdetector:onsets (HFC) | onset | Onset detection via high-frequency content |
| `qm_onsets_phase` | qm-onsetdetector:onsets (phase) | onset | Onset detection via phase deviation |
| `qm_segments` | qm-segmenter:segmentation | structure | Structural section boundaries (verse/chorus/bridge) |

**From BeatRoot Vamp**:

| Track Name | Vamp Key | Element Type | What It Captures |
|------------|----------|--------------|-----------------|
| `beatroot` | beatroot-vamp:beatroot:beats | beat | BeatRoot induction — robust on jazz/irregular rhythms |

**From pYIN**:

| Track Name | Vamp Key | Element Type | What It Captures |
|------------|----------|--------------|-----------------|
| `pyin_notes` | pyin:pyin:notes | melody | Note onset events from probabilistic pitch tracker |
| `pyin_pitch_changes` | pyin:pyin:smoothedpitchtrack | melody | Points where the predominant pitch changes |

**From NNLS Chroma + Chordino**:

| Track Name | Vamp Key | Element Type | What It Captures |
|------------|----------|--------------|-----------------|
| `chord_changes` | nnls-chroma:chordino:simplechord | harmonic | Chord change boundary points |
| `chroma_peaks` | nnls-chroma:nnls-chroma:chroma | harmonic | Chromagram energy peaks (harmonic rhythm) |

**From librosa** (spectral analysis not covered by Vamp):

| Track Name | Library | Element Type | What It Captures |
|------------|---------|--------------|-----------------|
| `librosa_beats` | librosa | beat | librosa beat tracker — comparison baseline |
| `librosa_bars` | librosa | bar | Bar markers derived from librosa beats |
| `librosa_onsets` | librosa | onset | librosa onset detection — all transients |
| `bass` | librosa | frequency | Low-frequency energy peaks (20–300 Hz) |
| `mid` | librosa | frequency | Mid-frequency energy peaks (300–4000 Hz) |
| `treble` | librosa | frequency | High-frequency energy peaks (4000 Hz+) |
| `drums` | librosa | percussion | HPSS percussive component onsets |
| `harmonic_peaks` | librosa | harmonic | HPSS harmonic content peaks |

**From madmom** (neural-net accuracy):

| Track Name | Library | Element Type | What It Captures |
|------------|---------|--------------|-----------------|
| `madmom_beats` | madmom | beat | RNN+DBN beat tracker — most accurate on complex rhythms |
| `madmom_downbeats` | madmom | bar | RNN downbeat detector — bar starts |

**Total: 22 tracks**. The user is expected to keep 3–6 for a typical song.

**Rationale for breadth**: Running 3 different onset detectors (complex, HFC, phase)
with different sensitivities lets the user pick the one that matches their song's
transient character. Running 4 different beat trackers (QM, BeatRoot, librosa, madmom)
exposes algorithm variation — some work better on specific genres. Section boundaries
(`qm_segments`) are useful for triggering color palette changes at verse/chorus breaks.

**`--top N` scoring** (see Decision 8):
Tracks are ranked by a quality score before `--top N` selection, so the user gets
the N most lighting-useful tracks without having to review all 22 manually.

---

## Decision 5: Determinism Strategy

**Decision**: Fix all random seeds and sort all output arrays before serialization.

**Rationale**: librosa's beat tracker uses a start-phase heuristic that is deterministic
given fixed hop_length. madmom's RNN is deterministic given the same model weights
(bundled with the package). numpy random seed must be fixed in each algorithm's run
method. TimingMark arrays are sorted ascending by time_ms before serialization to
guarantee identical JSON output.

---

## Decision 6: CLI Framework

**Decision**: Click 8+

**Rationale**: Click provides clean command/subcommand structure, automatic `--help`
generation, and type-validated arguments with minimal boilerplate. The three commands
(`analyze`, `summary`, `export`) map naturally to Click subcommands.

**Alternatives considered**:
- argparse: Stdlib but more verbose for subcommands; no automatic help formatting.
- Typer: Wraps Click with type hints; adds a layer of magic that isn't needed yet.

---

## Decision 7: JSON Output Schema

**Decision**: Single JSON file per analysis run, schema versioned at top level.

See `data-model.md` for full schema. Key choices:
- Timestamps stored as integers (milliseconds) to avoid float precision issues.
- Confidence scores stored as floats 0.0–1.0 (null if algorithm doesn't produce them).
- Schema version field enables forward-compatible changes in later features.
- Algorithm parameters stored alongside results for full reproducibility.

---

## Decision 8: Top-N Track Scoring

**Decision**: Score each generated TimingTrack on two axes and combine into a single
quality score used for `--top N` ranking.

**Scoring axes**:

1. **Density score** (0.0–1.0): How well does the average mark interval fit useful
   lighting timings? Score peaks at 250–1000ms avg interval (fits 60–240 BPM lighting
   effects). Penalize heavily below 100ms (too noisy for most effects) and lightly
   above 3000ms (too sparse to be interesting).

   ```
   ideal range: 250ms–1000ms → score 1.0
   < 100ms                   → score 0.0 (unusable noise)
   100ms–250ms               → linear interpolation 0.0–1.0
   1000ms–3000ms             → linear interpolation 1.0–0.5
   > 3000ms                  → score 0.5 (structural use, still valid)
   ```

2. **Regularity score** (0.0–1.0): Is the track regular (beat-like) or erratic
   (onset-like)? Computed as `1 - (stdev(intervals) / mean(intervals))`, clamped to
   [0, 1]. Regular beat tracks score near 1.0; onset tracks score near 0.0.
   Both extremes are useful — the score is informational, not a quality judgement.

**Combined quality score**: `0.6 * density_score + 0.4 * regularity_score`

The weighting favors density appropriateness over regularity because very regular but
too-dense tracks (e.g., `treble` at 135ms avg) should still rank lower than moderately
irregular but well-spaced tracks.

**The score is stored in the JSON output** on each TimingTrack (field: `quality_score`,
float 0.0–1.0). `--top N` sorts by this score descending and keeps N tracks.
The score is also shown in the summary table to help manual selection.

## Decision 9: Vamp Plugin Installation

**Decision**: Vamp plugins are a documented system prerequisite, not bundled.

**Installation** (macOS):
```bash
# Install QM Vamp Plugins, BeatRoot, pYIN, NNLS Chroma, Silvet from vamp-plugins.org
# Place .dylib files in: ~/Library/Audio/Plug-Ins/Vamp/
pip install vamp
python -c "import vamp; print(vamp.list_plugins())"  # verify
```

**Graceful degradation**: If a Vamp plugin is not installed, its corresponding
algorithm(s) are skipped with a warning. The run still completes with whatever
algorithms are available. This means the tool works with just librosa + madmom
if Vamp plugins are not yet installed.
