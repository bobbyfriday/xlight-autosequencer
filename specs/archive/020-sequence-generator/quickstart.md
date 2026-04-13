# Quickstart: Sequence Generator (020)

## Prerequisites

- Python 3.11+
- All existing dependencies installed (`pip install -r requirements.txt`)
- `mutagen` already installed (from feature 013)
- `questionary` and `rich` already installed (from feature 014)
- An MP3 file to sequence
- An xLights layout file (`xlights_rgbeffects.xml`) from your show directory

## Generate a Sequence (Wizard Mode)

```bash
# Interactive wizard — walks you through everything
xlight-analyze generate-wizard song.mp3

# Or specify both files upfront
xlight-analyze generate song.mp3 ~/xlights/xlights_rgbeffects.xml
```

The wizard will:
1. Detect song metadata (title, artist, genre) from ID3 tags
2. Ask you to confirm or override genre and occasion (christmas/halloween/general)
3. Read your layout and report models and power groups found
4. Run analysis (or use cached results)
5. Show a generation plan — which themes go on which sections
6. Let you override theme choices before generating
7. Write the `.xsq` file

## Generate Without Wizard

```bash
# Non-interactive with all options specified
xlight-analyze generate song.mp3 layout.xml \
  --genre rock \
  --occasion christmas \
  --output-dir ./output \
  --no-wizard
```

## Regenerate a Section

```bash
# Change just the chorus theme
xlight-analyze generate song.mp3 layout.xml \
  --section chorus \
  --theme-override "chorus=Inferno"
```

## Open in xLights

1. Open xLights
2. File → Open Sequence → select the generated `.xsq`
3. Effects are already placed on your models/groups
4. Preview and tweak as needed

## Render to FSEQ (in xLights)

1. Open the `.xsq` in xLights
2. Tools → Batch Render (or press F9 to render all)
3. File → Export → FSEQ to save the binary playback file

## Development

```bash
# Run tests
pytest tests/unit/test_sequence_generator/ -v
pytest tests/integration/test_sequence_generation.py -v

# Generate with debug output
xlight-analyze generate song.mp3 layout.xml --verbose
```

## Architecture Overview

```
MP3 ──→ Orchestrator (016) ──→ HierarchyResult
                                     │
Layout XML ──→ Grouper (017) ──→ PowerGroups
                                     │
                          ┌──────────┤
                          ▼          ▼
                    SongProfile + SectionEnergy[]
                          │
                          ▼
                  Theme Selection Engine
                  (energy → mood → theme query)
                          │
                          ▼
                    SequencePlan
                  (section → theme → group → effects)
                          │
                          ▼
                  Effect Placement Engine
                  (timing tracks + duration_type + fades + value curves)
                          │
                          ▼
                    XSQ Writer
                  (XML serialization with deduplication)
                          │
                          ▼
                     song.xsq
```
