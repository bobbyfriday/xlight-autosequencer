# Export Formats

[< Back to Index](README.md) | See also: [Data Structures](data-structures.md) · [Pipeline](pipeline.md)

The system exports analysis results in three formats for different consumers.

---

## JSON (Primary Cache Format)

### _analysis.json (Schema 1.0)

The full analysis result with all timing tracks in a flat list. Used by the sweep system and older pipeline commands.

```json
{
  "schema_version": "1.0",
  "source_file": "/path/to/song.mp3",
  "source_hash": "d17796b2cd4fea69532abb045d2fc155",
  "filename": "song.mp3",
  "duration_ms": 208110,
  "sample_rate": 44100,
  "estimated_tempo_bpm": 116.0,
  "run_timestamp": "2026-03-25T04:26:40.319041+00:00",
  "stem_separation": true,

  "algorithms": [
    {
      "name": "madmom_beats",
      "element_type": "beat",
      "library": "madmom",
      "plugin_key": null,
      "parameters": {},
      "preferred_stem": "drums"
    }
  ],

  "timing_tracks": [
    {
      "name": "madmom_beats",
      "algorithm_name": "madmom_beats",
      "element_type": "beat",
      "stem_source": "drums",
      "quality_score": 0.96,
      "marks": [
        {"time_ms": 510, "confidence": null, "label": null},
        {"time_ms": 1020, "confidence": null, "label": null}
      ],
      "score_breakdown": { ... },
      "value_curve": null
    }
  ]
}
```

### _hierarchy.json (Schema 2.0.0)

The structured hierarchy result. Used by the orchestrator and review UI.

```json
{
  "schema_version": "2.0.0",
  "source_file": "/path/to/song.mp3",
  "source_hash": "d17796b2cd4fea69532abb045d2fc155",
  "filename": "song.mp3",
  "duration_ms": 208110,
  "estimated_bpm": 116.0,
  "capabilities": {"vamp": true, "madmom": true, "demucs": true},
  "stems_available": ["drums", "bass", "vocals", "guitar", "piano", "other"],

  "energy_impacts": [{"time_ms": 15230, "confidence": 0.88}],
  "energy_drops": [{"time_ms": 45100, "confidence": 0.75}],
  "gaps": [],

  "sections": [
    {"label": "intro", "start_ms": 0, "end_ms": 15000},
    {"label": "verse", "start_ms": 15000, "end_ms": 45000}
  ],

  "bars": {
    "name": "madmom_downbeats",
    "marks": [{"time_ms": 0}, {"time_ms": 2040}, ...],
    "quality_score": 0.95
  },

  "beats": {
    "name": "madmom_beats",
    "marks": [{"time_ms": 510}, {"time_ms": 1020}, ...],
    "quality_score": 0.98
  },

  "events": {
    "full_mix": {"name": "librosa_onsets", "marks": [...]},
    "drums": {"name": "aubio_onset", "marks": [...]},
    "bass": {"name": "aubio_onset", "marks": [...]},
    "vocals": {"name": "aubio_onset", "marks": [...]},
    "guitar": {"name": "aubio_onset", "marks": [...]},
    "piano": {"name": "aubio_onset", "marks": [...]}
  },

  "chords": {
    "name": "chordino_chords",
    "marks": [
      {"time_ms": 230, "label": "C"},
      {"time_ms": 2500, "label": "Am"}
    ]
  },

  "key_changes": {
    "name": "qm_key",
    "marks": [{"time_ms": 0, "label": "C major"}]
  }
}
```

---

## .xtiming (xLights Timing Import)

XML format that xLights imports as a timing track. Each timing track becomes a row in the xLights sequencer where you can attach effects.

**Module:** `src/analyzer/xtiming.py`

### Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<timings>
  <timing name="song_name" SourceVersion="2024.01">
    <EffectLayer>
      <Effect label="" starttime="510" endtime="1020" />
      <Effect label="" starttime="1020" endtime="1530" />
      <Effect label="" starttime="1530" endtime="2040" />
    </EffectLayer>
  </timing>
</timings>
```

Each `<Effect>` element spans from one timing mark to the next. The `label` field is empty for beat/onset marks but contains text for chord marks or lyrics.

### Multi-Layer Export (Phonemes)

When phoneme data is available, the .xtiming file contains 3 layers:

```xml
<timings>
  <timing name="song_name" SourceVersion="2024.01">
    <!-- Layer 1: Full lyrics block -->
    <EffectLayer>
      <Effect label="I was made for lovin you baby..."
              starttime="0" endtime="180000" />
    </EffectLayer>

    <!-- Layer 2: Word-level timing -->
    <EffectLayer>
      <Effect label="I"     starttime="15230" endtime="15680" />
      <Effect label="WAS"   starttime="15680" endtime="16100" />
      <Effect label="MADE"  starttime="16100" endtime="16800" />
    </EffectLayer>

    <!-- Layer 3: Phoneme-level timing (Papagayo alphabet) -->
    <EffectLayer>
      <Effect label="AI"  starttime="15230" endtime="15680" />
      <Effect label="WQ"  starttime="15680" endtime="15850" />
      <Effect label="AI"  starttime="15850" endtime="15950" />
      <Effect label="E"   starttime="15950" endtime="16100" />
      <Effect label="MBP" starttime="16100" endtime="16300" />
      <Effect label="AI"  starttime="16300" endtime="16500" />
      <Effect label="etc" starttime="16500" endtime="16800" />
    </EffectLayer>
  </timing>
</timings>
```

### Papagayo Phoneme Alphabet

The phoneme layer uses the Papagayo lip-sync alphabet that xLights expects:

| Phoneme | Mouth Shape | Example Words |
|---------|-------------|---------------|
| AI | Wide open | "I", "my", "sky" |
| E | Slightly open | "bed", "said" |
| O | Round | "go", "show" |
| U | Pursed | "you", "blue" |
| MBP | Closed | "map", "bat", "put" |
| FV | Teeth on lip | "five", "van" |
| L | Tongue up | "love", "let" |
| WQ | Tight round | "want", "quick" |
| etc | Neutral | Filler between words |
| rest | Closed | Silence |

---

## .xvc (xLights Value Curve)

XML format for importing continuous dimmer/intensity data into xLights. Value curves control smooth effects like brightness, color intensity, or speed parameters.

**Module:** `src/analyzer/xvc_export.py`

### Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<valuecurve data="Active=TRUE|Id=ID_VALUECURVE_XVC|Type=Custom|Min=0.00|Max=100.00|Values=0.000:45.12;0.005:52.30;0.010:61.10;0.015:55.80;..." />
```

### Data Attribute Format

The `data` attribute is a pipe-delimited string of key=value pairs:

| Key | Value | Description |
|-----|-------|-------------|
| Active | TRUE | Always TRUE |
| Id | ID_VALUECURVE_XVC | Fixed identifier |
| Type | Custom | Always Custom (point-to-point curve) |
| Min | 0.00 | Minimum value |
| Max | 100.00 | Maximum value |
| Values | x:y;x:y;... | Semicolon-delimited point list |

### Values Format

Each point is `x:y` where:
- **x** ∈ [0.00, 1.00] — normalized position within the song (0 = start, 1 = end)
- **y** ∈ [0.00, 100.00] — intensity value

For full-song export, the curve is **downsampled to ≤100 points** uniformly to keep the xLights file manageable:

```
Original (20 fps × 208s = 4,160 frames):
  0.00:12; 0.00:15; 0.00:23; 0.01:45; ...  (4,160 points)

Downsampled (100 points):
  0.000:12; 0.010:23; 0.020:52; 0.030:67; ...  (100 points)
```

### Typical Value Curves

| Curve | Source | xLights Use |
|-------|--------|-------------|
| `bbc_energy_full_mix.xvc` | Overall RMS energy | Master brightness |
| `bbc_energy_drums.xvc` | Drums RMS energy | Drum-group brightness |
| `bbc_spectral_flux.xvc` | Spectral change rate | Effect speed modulation |
| `bbc_peaks_drums.xvc` | Drum amplitude peaks | Strobe intensity |
| `amplitude_follower.xvc` | Smoothed amplitude | Smooth fade effects |
| `tempogram_drums.xvc` | Tempo stability | Beat-sync confidence |

---

## Export Commands

```bash
# Export top N timing tracks as .xtiming
xlight-analyze export analysis.json --top 5 --output export/

# Export all tracks from hierarchy
xlight-analyze export-xlights song_hierarchy.json --output-dir export/

# Full pipeline with auto-export
xlight-analyze pipeline song.mp3 --top 5 --output-dir export/

# Sweep winners with export
xlight-analyze sweep-results sweep_report.json --best --export
```

---

## Output Directory Layout

After a full pipeline run:

```
Song Name/
  ├── stems/
  │   ├── manifest.json
  │   ├── drums.mp3
  │   ├── bass.mp3
  │   ├── vocals.mp3
  │   ├── guitar.mp3
  │   ├── piano.mp3
  │   └── other.mp3
  │
  ├── sweep/
  │   ├── sweep_report.json
  │   ├── sweep_qm_beats.json
  │   ├── sweep_librosa_beats.json
  │   ├── ...
  │   └── winners/
  │       ├── winners.json
  │       ├── qm_beats_drums.xtiming
  │       ├── bbc_energy_full_mix.xvc
  │       └── ...
  │
  ├── song_hierarchy.json       ← Main analysis result
  ├── song.xtiming              ← Timing marks for xLights
  └── export_manifest.json      ← What was exported and when
```

---

## Related Docs

- [Data Structures](data-structures.md) — In-memory data models
- [Pipeline](pipeline.md) — How exports are generated
- [Review UI](review-ui.md) — Viewing exports in the browser
