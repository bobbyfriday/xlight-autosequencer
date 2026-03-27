# xlight-autosequencer

Automatically generate xLights sequences from audio files. Analyzes your music, detects beats/onsets/chords/sections, groups your layout props, and applies themed effects — all driven by the audio.

## What It Does

1. **Audio Analysis** — Analyzes MP3 files to extract beats, onsets, chords, sections, energy curves, and stem separation (drums/bass/vocals/guitar/piano)
2. **Layout Grouping** — Reads your `xlights_rgbeffects.xml` and auto-generates 8-tier Power Groups (spatial, rhythmic, prop type, compound, heroes)
3. **Effect Library** — 35 xLights effects cataloged with parameters, prop suitability ratings, and analysis-to-parameter mappings
4. **Theme Engine** — 21 composite "looks" (Inferno, Aurora, Winter Wonderland, etc.) organized by mood, occasion, and genre
5. **Review UI** — Browser-based timeline for visualizing timing tracks, synchronized playback, and export

---

## Quick Start

### Prerequisites

- **Python 3.11 or 3.12** — [python.org](https://www.python.org/downloads/) or `brew install python@3.12`
- **ffmpeg** — `brew install ffmpeg`
- **Vamp plugins** (recommended) — Download from [vamp-plugins.org](https://vamp-plugins.org/pack.html) and copy `.dylib` files to `~/Library/Audio/Plug-Ins/Vamp/`:
  - QM Vamp Plugins, BeatRoot, pYIN, NNLS Chroma/Chordino, Silvet

### Install

```bash
git clone https://github.com/bobbyfriday/xlight-autosequencer.git
cd xlight-autosequencer
python3.12 -m venv .venv
source .venv/bin/activate

# Install everything
pip install -e ".[all]"

# PyTorch (required for stem separation and phonemes)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# nltk data (for phoneme analysis)
python -c "import nltk; nltk.download('cmudict')"
```

> **macOS Python.org installer:** Run `open "/Applications/Python 3.12/Install Certificates.command"` once for SSL certs.

### Optional: Vamp + madmom secondary environment

Vamp and madmom require NumPy 1.x, which conflicts with whisperx. A separate venv is auto-detected:

```bash
python3.12 -m venv .venv-vamp
source .venv-vamp/bin/activate
pip install "numpy<2" vamp madmom librosa soundfile
deactivate
```

When `.venv-vamp/` exists, Vamp and madmom algorithms run through it automatically (~14 additional tracks).

---

## Usage

### Review UI (recommended starting point)

```bash
source .venv/bin/activate
xlight-analyze review
```

Opens `http://localhost:5173` with drag-and-drop analysis, timeline visualization, and export.

### Analyze a song

```bash
# Basic analysis (beats, onsets, chords)
xlight-analyze analyze song.mp3

# Full analysis with stems and phonemes
xlight-analyze analyze song.mp3 --stems --phonemes

# End-to-end pipeline: analyze → export .xtiming + .xvc files for xLights
xlight-analyze pipeline song.mp3 --output-dir ./xlight-export
```

### Group your layout

```bash
# Preview Power Groups without modifying files
xlight-analyze group-layout ~/xLights/xlights_rgbeffects.xml --dry-run

# Generate groups (creates .xml.bak backup first)
xlight-analyze group-layout ~/xLights/xlights_rgbeffects.xml

# Use a show profile to filter tiers
xlight-analyze group-layout ~/xLights/xlights_rgbeffects.xml --profile energetic
```

---

## Output Files

```
song.mp3
song/
├── song_analysis.json          # Full analysis (cached by MD5)
├── song.xtiming                # xLights timing file (phonemes)
├── song.lyrics.txt             # Auto-transcribed lyrics (edit and rerun)
├── stems/                      # Separated audio stems
│   ├── drums.mp3, bass.mp3, vocals.mp3, guitar.mp3, piano.mp3, other.mp3
│   └── manifest.json
└── analysis/                   # xLights export files
    ├── song_timing.xtiming     # All timing tracks
    ├── drums_beat.xvc          # Value curves (full resolution + macro)
    └── export_manifest.json
```

### Importing into xLights

| File | How to import |
|------|---------------|
| `*.xtiming` | Sequence editor → right-click → Import Timing Tracks |
| `*.xvc` | Effect → value curve editor → load from file |

---

## CLI Reference

```bash
# Analysis
xlight-analyze analyze song.mp3 [--stems] [--phonemes] [--genius]
xlight-analyze summary song_analysis.json
xlight-analyze review [song_analysis.json]

# xLights pipeline
xlight-analyze pipeline song.mp3 [--output-dir DIR] [--interactive] [--top N]
xlight-analyze export-xlights song_analysis.json --output-dir DIR

# Layout grouping
xlight-analyze group-layout layout.xml [--profile energetic|cinematic|technical] [--dry-run]
xlight-analyze group-layout layout.xml [--hero "Prop Name"] [--no-auto-heroes]

# Stem tools
xlight-analyze stem-inspect song.mp3
xlight-analyze stem-review song.mp3 [--yes]
xlight-analyze sweep-init song.mp3 [--dry-run]
```

---

## Project Structure

```
src/
├── analyzer/               # Audio analysis pipeline
│   ├── audio.py            # MP3 loading
│   ├── result.py           # Data classes (TimingTrack, etc.)
│   ├── runner.py           # Orchestrates algorithm runs
│   ├── orchestrator.py     # Hierarchy assembly (L0–L6)
│   ├── scorer.py           # Quality scoring
│   ├── stems.py            # Demucs stem separation
│   ├── phonemes.py         # WhisperX phoneme analysis
│   ├── xtiming.py          # .xtiming XML writer
│   ├── xvc_export.py       # .xvc value curve writer
│   ├── pipeline.py         # End-to-end export pipeline
│   └── algorithms/         # Individual algorithm implementations
├── grouper/                # xLights layout → Power Groups
│   ├── layout.py           # Parse xlights_rgbeffects.xml
│   ├── classifier.py       # Normalize, classify, detect heroes
│   ├── grouper.py          # 8-tier group generation
│   └── writer.py           # Inject groups back into XML
├── effects/                # xLights effect catalog
│   ├── builtin_effects.json  # 35 effect definitions
│   ├── models.py           # EffectDefinition, EffectParameter, AnalysisMapping
│   ├── library.py          # Load, query, custom overrides
│   └── validator.py        # Schema validation
├── themes/                 # Composite effect themes
│   ├── builtin_themes.json # 21 theme definitions
│   ├── models.py           # Theme, EffectLayer
│   ├── library.py          # Load, query by mood/occasion/genre
│   └── validator.py        # Theme validation (checks effect refs)
├── cli.py                  # Click CLI entry point
├── cache.py                # MD5-keyed analysis cache
├── library.py              # ~/.xlight/library.json song index
├── export.py               # JSON serialization
└── review/
    ├── server.py           # Flask app
    └── static/             # Browser UI (vanilla JS + Canvas)
```

---

## Known Issues

| Issue | Fix |
|-------|-----|
| `SSLCertVerificationError` during demucs download | Run `open "/Applications/Python 3.12/Install Certificates.command"` (Python.org installs only) |
| `No module named 'demucs.api'` | `pip install -U demucs` (need ≥ 4.0.1) |
| `TorchCodec is required` warning | Harmless — can be ignored |
| `FileNotFoundError: ffmpeg` | Add ffmpeg to PATH: `export PATH="/opt/homebrew/bin:$PATH"` |
| Stem separation slow on first run | Normal — demucs downloads ~200 MB model. Cached after first run. |
| whisperx alignment model fails | `pip install huggingface_hub && huggingface-cli login` |

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

---

## Documentation

Detailed docs for each subsystem are in [`docs/`](docs/README.md).
