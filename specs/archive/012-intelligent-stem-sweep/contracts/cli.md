# CLI Contract: Intelligent Stem Analysis Pipeline

**Feature**: 012-intelligent-stem-sweep

## New Commands

### `xlight-analyze pipeline <audio_file>`

Full automated pipeline: inspection → selection → parameter init → sweep → interaction → conditioning → export.

```
Usage: xlight-analyze pipeline [OPTIONS] AUDIO_FILE

Options:
  --interactive        Pause after stem inspection for user review
  --stem-dir PATH      Custom stem directory (default: .stems/<md5>/)
  --output-dir PATH    Export directory (default: analysis/)
  --fps INTEGER        Target frame rate for export (default: 20)
  --top INTEGER        Select top N tracks per algorithm from sweep (default: 3)
  --scoring-config PATH  Custom scoring config file
  --no-sweep           Skip parameter sweep, use default parameters only
  --help               Show this message and exit.

Output:
  analysis/
  ├── *_beats.xtiming          # Beat timing tracks
  ├── *_onsets.xtiming         # Onset timing tracks
  ├── *_structure.xtiming      # Structure boundary timing track
  ├── *_leader.xtiming         # Leader transition timing track
  ├── *_handoffs.xtiming       # Handoff event timing track
  ├── *_energy.xvc             # Per-segment energy value curves
  ├── *_brightness.xvc         # Per-segment brightness value curves
  ├── *_sidechain.xvc          # Sidechained vocal curves
  ├── *_macro_energy.xvc       # Full-song energy value curve (reduced resolution)
  └── export_manifest.json     # Complete export manifest
```

**Exit codes**: 0 = success, 1 = error, 2 = no usable stems and no full mix available.

---

### `xlight-analyze stem-review <audio_file>` (new)

Interactive stem quality review with override capability.

```
Usage: xlight-analyze stem-review [OPTIONS] AUDIO_FILE

Options:
  --stem-dir PATH      Custom stem directory
  --help               Show this message and exit.

Interactive Output:
  ┌─ Stem Review ─────────────────────────────────────────┐
  │ drums    KEEP    RMS: -12.3 dB  Coverage: 98%         │
  │          Full-energy rhythmic stem; high crest factor  │
  │          [K]eep  [S]kip  [Enter = accept]             │
  │                                                       │
  │ vocals   REVIEW  RMS: -18.1 dB  Coverage: 62%         │
  │          Active less than 70% of track                 │
  │          [K]eep  [S]kip  [Enter = accept]             │
  │                                                       │
  │ other    SKIP    RMS: -42.0 dB  Coverage: 8%           │
  │          Near-silent stem; energy below threshold      │
  │          [K]eep  [S]kip  [Enter = accept]             │
  └───────────────────────────────────────────────────────┘

  Final selection: drums (KEEP), bass (KEEP), vocals (KEEP →override), ...
```

---

### `xlight-analyze condition <analysis_json>` (new)

Standalone data conditioning (downsample + smooth + normalize).

```
Usage: xlight-analyze condition [OPTIONS] ANALYSIS_JSON

Options:
  --fps INTEGER        Target frame rate (default: 20)
  --output-dir PATH    Output directory for conditioned data
  --help               Show this message and exit.
```

---

### `xlight-analyze export-xlights <analysis_json>` (new)

Export conditioned analysis as xLights timing tracks and value curves.

```
Usage: xlight-analyze export-xlights [OPTIONS] ANALYSIS_JSON

Options:
  --output-dir PATH    Export directory (default: analysis/)
  --fps INTEGER        Frame rate for value curves (default: 20)
  --macro-only         Export only full-song macro curves, no per-segment
  --help               Show this message and exit.
```

## Extended Commands

### `xlight-analyze stem-inspect` (existing — no changes)

Already exists. Displays non-interactive verdict summary.

### `xlight-analyze sweep-init` (existing — no changes)

Already exists. Generates intelligent sweep configs from stem properties.

## Output File Naming Convention

```
{stem}_{feature}_{qualifier}.{ext}

Examples:
  drums_beats_qm.xtiming
  vocals_energy_verse1.xvc
  vocals_sidechain_chorus1.xvc
  full_mix_energy_macro.xvc
  leader_transitions.xtiming
  kickbass_handoffs.xtiming
```
