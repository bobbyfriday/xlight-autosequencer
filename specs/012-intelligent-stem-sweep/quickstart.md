# Quickstart: Intelligent Stem Analysis Pipeline

**Feature**: 012-intelligent-stem-sweep

## Prerequisites

```bash
# Existing dependencies (should already be installed)
pip install vamp librosa madmom click numpy scipy pytest

# Stems must already be separated (feature 008)
# Verify stems exist:
ls .stems/*/drums.wav bass.wav vocals.wav guitar.wav piano.wav other.wav
```

## Quick Pipeline Run

```bash
# Full automated pipeline (non-interactive)
xlight-analyze pipeline song.mp3

# With interactive stem review
xlight-analyze pipeline song.mp3 --interactive

# Custom output directory and frame rate
xlight-analyze pipeline song.mp3 --output-dir my_export/ --fps 30
```

## Step-by-Step Usage

```bash
# 1. Inspect stem quality
xlight-analyze stem-inspect song.mp3

# 2. Interactive review (override verdicts)
xlight-analyze stem-review song.mp3

# 3. Generate intelligent sweep configs
xlight-analyze sweep-init song.mp3

# 4. Run analysis with sweeps
xlight-analyze analyze song.mp3 --stems --top 3

# 5. Condition and export for xLights
xlight-analyze export-xlights song_analysis.json
```

## Output Structure

```
analysis/
├── drums_beats_qm.xtiming         # Import as timing track in xLights
├── vocals_energy_verse1.xvc        # Apply as value curve to brightness effect
├── vocals_sidechain_chorus1.xvc    # Pumping vocal brightness
├── full_mix_energy_macro.xvc       # Master dimmer curve
├── leader_transitions.xtiming      # Stem leadership changes
└── export_manifest.json            # What was exported and why
```

## Importing into xLights

1. **Timing tracks** (`.xtiming`): Right-click timing area → Import Timing Track → select file
2. **Value curves** (`.xvc`): Copy to your show's `valuecurves/` folder, then select from the value curve picker on any effect property

## Development

```bash
# Run all tests
pytest tests/ -v

# Run only the new modules' tests
pytest tests/unit/test_interaction.py tests/unit/test_conditioning.py tests/unit/test_xvc_export.py -v

# Run the pipeline on a test file
xlight-analyze pipeline tests/fixtures/short_clip.mp3 --output-dir /tmp/test_export/
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `src/analyzer/stem_inspector.py` | Stem quality inspection + interactive review |
| `src/analyzer/interaction.py` | Cross-stem interaction analysis (leader, tightness, sidechain, handoffs) |
| `src/analyzer/conditioning.py` | Downsample, smooth, normalize to 0-100 |
| `src/analyzer/xvc_export.py` | .xvc value curve XML export |
| `src/analyzer/xtiming.py` | .xtiming timing track XML export (extended for beats/onsets) |
| `src/cli.py` | CLI commands: pipeline, stem-review, condition, export-xlights |
