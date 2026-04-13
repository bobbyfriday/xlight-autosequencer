# Research: Stem Separation

**Branch**: `008-stem-separation` | **Date**: 2026-03-22
**Phase**: 0 — All NEEDS CLARIFICATION resolved before Phase 1 design

---

## Decision 1: Stem Separation Library

**Decision**: Use **Demucs v4** (`demucs` PyPI package, `htdemucs_6s` 6-stem model)

**Rationale**:
- Produces six stems: drums, bass, vocals, guitar, piano, other — enabling more precise algorithm routing than the 4-stem model
- Guitar and piano stems allow harmony/chord algorithms to target the most relevant harmonic content for each song type
- Fully offline; no cloud API calls — satisfies constitution Technical Constraint
- Python package, pip-installable — fits existing Python 3.11+ stack
- CPU-capable (GPU optional, not required)
- Actively maintained (Meta AI Research); best objective quality among open-source options
- `htdemucs_6s` processes a 4-minute song in ~75–120 s on modern CPU (slightly slower than 4-stem), keeping us within the SC-003 3× overhead bound

**Alternatives considered**:

| Library | Status | Reason Rejected |
|---------|--------|----------------|
| Spleeter (Deezer) | Maintenance reduced | Older model quality; dependency conflicts with newer Python environments |
| Open-Unmix | Active | Lower separation quality than Demucs on standard benchmarks |
| Asteroid | Active | Research-focused, less production-ready CLI integration |

---

## Decision 2: Stem Cache Storage Location

**Decision**: Store stems in a `.stems/<source_hash>/` directory adjacent to the source MP3 file.

Example:
```
~/music/song.mp3
~/music/.stems/a3f8c2d1/drums.wav
~/music/.stems/a3f8c2d1/bass.wav
~/music/.stems/a3f8c2d1/vocals.wav
~/music/.stems/a3f8c2d1/other.wav
~/music/.stems/a3f8c2d1/manifest.json
```

**Rationale**:
- Stems belong to the source file, not to a specific analysis run; storing them with the source file makes them shareable across multiple analysis runs
- The hash-keyed subdirectory allows stale detection without a separate lookup step
- Keeps the analysis output directory clean

**Alternatives considered**:

| Approach | Reason Rejected |
|----------|----------------|
| Alongside analysis JSON | Analysis runs are per-output-dir; stems would be duplicated for re-runs |
| Central cache dir (`~/.cache/xlight/stems/`) | Harder to discover, clean up, or move with the project |

---

## Decision 3: Stale Cache Detection

**Decision**: Use **MD5 hash of the source MP3 file** as the cache key. Store the hash in `manifest.json` alongside the stems. On each stem-enabled run, recompute the hash and compare.

**Rationale**:
- More reliable than mtime — copying or touching a file resets mtime but not content hash
- MD5 is fast enough for typical MP3 file sizes (3–10 MB: <50 ms)
- The hash already serves as the subdirectory name, making stale detection implicit (if the hash directory exists → cache valid)

**Alternatives considered**:

| Approach | Reason Rejected |
|----------|----------------|
| mtime comparison | Unreliable across file copies, backups, or cloud sync |
| SHA-256 | Marginally slower, no meaningful security benefit for this use case |
| File size + mtime | Still unreliable; size collisions possible |

---

## Decision 4: Algorithm-to-Stem Routing

**Decision**: Add a `preferred_stem: str` class attribute to `base.Algorithm`. The runner reads this attribute and passes the appropriate pre-loaded audio array. Default value is `"full_mix"` to preserve backward compatibility.

**Routing table**:

| Algorithm | Preferred Stem | Rationale |
|-----------|---------------|-----------|
| `vamp_beats` (QM bar-beat tracker, BeatRoot) | `drums` | Beat detection is most accurate on isolated percussion |
| `vamp_onsets` (QM onset detector) | `drums` | Onsets dominated by transients; drums stem reduces harmonic interference |
| `vamp_structure` (QM segmenter, tempo) | `full_mix` | Structural analysis benefits from all spectral content |
| `vamp_pitch` (pYIN note events) | `vocals` | Pitch tracking works best on monophonic or near-monophonic signal |
| `vamp_harmony` (Chordino, NNLS chroma) | `piano` | Piano is the richest harmonic source; falls back to `guitar` mix if piano stem is silent |
| `librosa_beats` | `drums` | Same rationale as vamp_beats |
| `librosa_bands` (frequency band energy) | `full_mix` | Band energy analysis is intended to capture the full spectrum |
| `librosa_hpss` (HPSS drums + harmonic) | `full_mix` | HPSS does its own source separation internally; running on a stem would be redundant |
| `madmom_beat` (RNN+DBN) | `drums` | DBN beat tracking benefits strongly from isolated drums |

**Alternatives considered**:

| Approach | Reason Rejected |
|----------|----------------|
| Routing config file (YAML/JSON) | Adds configuration complexity with no user benefit; routing is stable per algorithm |
| Per-run stem override flag | Out of scope for this feature; adds CLI surface area without clear demand |

---

## Decision 5: Stem Audio Format

**Decision**: Store stems as **WAV files** (16-bit, 44.1 kHz, stereo).

**Rationale**:
- Demucs outputs WAV by default; no re-encoding needed
- WAV is lossless — no quality degradation in the analysis pipeline
- All downstream audio libraries (vamp, librosa, madmom) read WAV natively

**Alternatives considered**:

| Format | Reason Rejected |
|--------|----------------|
| FLAC | Lossless and compressed, but adds encoding step and dependency |
| MP3 | Lossy; introduces artifacts into stem that degrade analysis accuracy |

---

## Resolved: All NEEDS CLARIFICATION

All unknowns from the spec Assumptions are resolved above. No open questions remain.
