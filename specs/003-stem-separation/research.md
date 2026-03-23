# Research: Music Stem Separation

**Branch**: `002-stem-separation` | **Date**: 2026-03-22

---

## Background

The current pipeline uses **librosa HPSS** (Harmonic-Percussive Source Separation) for
instrument-level timing tracks. HPSS is a simple 2-way split — percussive vs. harmonic
components of the mixed audio — and produces two tracks: `drums` (percussive onsets) and
`harmonic_peaks` (harmonic content peaks). These are crude approximations because the
separation is based on spectral shape heuristics, not learned instrument models.

Proper music stem separation would give clean isolated waveforms per instrument group
(drums, bass, vocals, other), which the existing onset/beat/peak detectors can then be
run against. This produces far more accurate element-specific timing tracks and replaces
both HPSS-derived tracks with cleaner equivalents, while adding stem types the pipeline
currently cannot produce at all.

---

## Decision 1: Primary Stem Separation Library

**Decision**: Demucs (`htdemucs` v4, by Meta Research)

**Rationale**:

Demucs v4 features Hybrid Transformer Demucs — a hybrid spectrogram/waveform model that
uses a cross-domain Transformer Encoder with self-attention within each domain and
cross-attention across domains. It is the current state-of-the-art open-source stem
separator, winning the MDX Music Demixing Challenge benchmarks and outperforming all
alternatives by approximately 3 dB in perceptual separation quality (roughly a doubling
of perceived separation quality).

**Key properties**:

| Property | Detail |
|----------|--------|
| Default model | `htdemucs` — trained on MusDB + 800 songs |
| Fine-tuned model | `htdemucs_ft` — 4x slower, marginally better |
| 6-stem model | `htdemucs_6s` — adds guitar and piano stems |
| Output | numpy arrays in-memory — no temp file I/O |
| Speed | ~20–30s per 3-min track on CPU; faster on Apple Silicon MPS |
| License | Code: MIT; model weights: download on first run (~80 MB) |
| Maintenance | Actively maintained by Meta Research |
| Install | `pip install demucs` |

The Python API returns separated stems as numpy arrays directly, which fits cleanly into
the existing `audio_array → Algorithm → TimingTrack` pipeline without any file I/O:

```python
from demucs.pretrained import get_model
from demucs.apply import apply_model
import torch

model = get_model("htdemucs")
# sources order: drums, bass, other, vocals
sources = apply_model(model, waveform_tensor)
```

**Fit for this project**: Each stem maps 1:1 to timing track types the project already
targets. Adding a `demucs_` algorithm module follows exactly the same pattern as
`librosa_hpss.py` and `vamp_beats.py`. The existing `Algorithm` interface requires only
`run(audio_array, sample_rate) -> TimingTrack`, so each stem can be its own algorithm
class that isolates the stem then applies onset/peak detection.

**Dependency strategy**: Add as an optional dependency, consistent with the established
pattern for `vamp` and `madmom`:

```toml
[project.optional-dependencies]
stems = ["demucs>=4.0"]
```

If Demucs is not installed, its algorithm classes are skipped with a warning and the
run completes with the remaining algorithms — identical to how missing Vamp plugins are
handled today.

---

## Decision 2: Alternatives Considered

### audio-separator (nomadkaraoke)

A Python wrapper over multiple model architectures — MDX-Net, VR Arch, and Demucs —
ported from Ultimate Vocal Remover (UVR). Key models run via **ONNX Runtime**, making
it usable without PyTorch.

**Why not chosen as primary**:
- API is file-in/file-out oriented rather than numpy in-memory, requiring either temp
  files or patching to fit the existing pipeline interface.
- The ONNX-based models (MDX-Net, VR Arch) have competitive quality but are below
  htdemucs on benchmark scores.
- Demucs can still be used through audio-separator, making it a wrapper without benefit
  over using Demucs directly.

**When to reconsider**: If PyTorch proves too heavy a dependency for the target users,
audio-separator's ONNX path is the best lightweight fallback. It supports CoreML
acceleration on Apple Silicon for the ONNX models.

### Spleeter (Deezer)

Spectrogram-masking-based 2/4/5 stem separator. Fast on CPU (~2s per 3-min track on GPU
vs. Demucs's ~20–30s). Based on TensorFlow 2.x.

**Why not chosen**:
- Not actively maintained since ~2019; surpassed in quality by a significant margin.
- TensorFlow is an equally large dependency as PyTorch, so there is no dependency size
  advantage.
- Spectrogram-only approach does not handle phase, producing metallic artifacts on
  transient-heavy stems (drums, guitar). This would reduce accuracy of onset detection
  run on the separated stems.

### Open-Unmix (sigsep)

PyTorch-based reference implementation, 4 stems, LSTM architecture. Updated to torch 2.0
in April 2024.

**Why not chosen**:
- The best available model (`umxl`) is licensed **CC BY-NC-SA 4.0** (non-commercial
  use only). This is a hard blocker for a tool that may have commercial uses.
- The open model (`umx`) is lower quality than htdemucs.

---

## Comparison Table

| Library | Quality | Stems | PyTorch | Maintained | License |
|---------|---------|-------|---------|------------|---------|
| **Demucs htdemucs** | Best | 4–6 | Required | Yes (Meta) | MIT |
| audio-separator | Good | 2–4 | Optional | Yes | MIT |
| Spleeter | Fair | 2/4/5 | No (TF) | No | MIT |
| Open-Unmix (umxl) | Good | 4 | Required | Slow | Non-commercial |

---

## Timing Tracks Added by Stem Separation

Replacing the two current HPSS-derived tracks and adding new ones:

| Track Name | Source | Replaces | What It Captures |
|------------|--------|----------|-----------------|
| `demucs_drums` | Demucs drums stem + onset detection | `drums` (HPSS) | Drum hits with clean isolation — significantly fewer false positives |
| `demucs_bass` | Demucs bass stem + low-freq peaks | — (new) | Bass note onsets and accents |
| `demucs_vocals` | Demucs vocals stem + onset detection | — (new) | Vocal phrase starts and accent points |
| `demucs_other` | Demucs other stem + onset detection | `harmonic_peaks` (HPSS) | Lead instrument events (guitar, synth, piano) |

These four tracks join the existing 22 tracks, giving the `--top N` scorer more
high-quality options to rank. The density and regularity scoring logic in `scorer.py`
applies without modification.

---

## Speed Consideration

Demucs adds processing time. Benchmarks on a 3-minute track:

| Hardware | htdemucs time |
|----------|---------------|
| Apple M-series (MPS) | ~5–10s |
| CPU only | ~20–30s |
| NVIDIA GPU | ~5–10s |

For the 60-second total analysis target (SC-002), stem separation fits on Apple Silicon
but may push the limit on CPU-only machines. Mitigation: run Demucs as the last step in
the pipeline so all other tracks are produced regardless. Document the time trade-off.
The `htdemucs` model (not `htdemucs_ft`) should be the default — `htdemucs_ft` takes 4x
longer for marginal gain.
