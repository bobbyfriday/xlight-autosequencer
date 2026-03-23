# Quickstart: Stem Separation

**Branch**: `008-stem-separation` | **Date**: 2026-03-22

---

## Install New Dependency

```bash
pip install demucs
```

Demucs downloads the `htdemucs_6s` model weights on first use (~200 MB, cached in `~/.cache/torch/`).

---

## Run Analysis with Stem Separation

```bash
# Standard analysis (unchanged)
xlight-analyze analyze song.mp3

# Analysis with stem separation (opt-in)
xlight-analyze analyze song.mp3 --stems
```

On first run with `--stems`, stem separation takes 1–3 minutes depending on song length and CPU. Subsequent runs on the same file are instant (cached).

---

## Verify Stems Were Used

```bash
xlight-analyze summary song_analysis.json
```

The `Stem` column shows which stem each track was derived from. Beat tracks should show `drums`, pitch tracks should show `vocals`.

---

## Stem Cache Location

Stems are stored adjacent to the source MP3:

```
song.mp3
.stems/
└── a3f8c2d1/          ← MD5 hash of song.mp3
    ├── drums.wav
    ├── bass.wav
    ├── vocals.wav
    ├── guitar.wav
    ├── piano.wav
    ├── other.wav
    └── manifest.json
```

To clear the cache for a file, delete the `.stems/` directory. The next `--stems` run will regenerate.

---

## New Module: `src/analyzer/stems.py`

Key public interface for implementers:

```python
class StemSeparator:
    def separate(self, audio_path: Path) -> StemSet: ...
    # Checks cache; runs Demucs if miss; returns loaded StemSet

class StemSet:
    drums: np.ndarray
    bass: np.ndarray
    vocals: np.ndarray
    guitar: np.ndarray
    piano: np.ndarray
    other: np.ndarray
    sample_rate: int
```

---

## Algorithm Routing

Each algorithm declares its preferred stem via a class attribute:

```python
# base.py
class Algorithm(ABC):
    preferred_stem: str = "full_mix"  # default

# vamp_beats.py
class VampBeats(Algorithm):
    preferred_stem = "drums"
```

The runner selects the correct audio array from the `StemSet` before calling `algorithm.run()`.

---

## Running Tests

```bash
pytest tests/ -v                          # all tests
pytest tests/unit/test_stems.py -v       # stem separator unit tests
pytest tests/integration/ -v             # end-to-end with --stems
```

Fixture: a short WAV file (`tests/fixtures/10s_drums_bass.wav`) is used to test stem routing without running full Demucs separation.
