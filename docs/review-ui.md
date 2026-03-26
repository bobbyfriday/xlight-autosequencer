# Review UI

[< Back to Index](README.md) | See also: [Pipeline](pipeline.md) · [Data Structures](data-structures.md)

The review UI is a Flask-served web application for visualizing analysis results, reviewing timing tracks, comparing sweep results, and editing phoneme timing.

---

## Launching

```bash
# Open a specific analysis
xlight-analyze review song_hierarchy.json

# Open a song (looks up cached analysis)
xlight-analyze review song.mp3

# Scan a directory for analyzed songs
xlight-analyze review /path/to/songs/

# Start in upload mode (drag-and-drop)
xlight-analyze review
```

Opens a browser at **http://localhost:5173**.

---

## Three Modes

### 1. Upload / Library Mode

When launched without arguments, shows a home page with:

```
┌──────────────────────────────────────────────────────────┐
│  XLight AutoSequencer                                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │                                                    │  │
│  │         Drag & drop MP3 here                       │  │
│  │              or click to browse                    │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Options:  [x] Vamp  [x] madmom  [x] Stems  [x] Phonemes│
│                                                          │
│  ─────────────────────────────────────────────────────── │
│  Previously Analyzed:                                    │
│                                                          │
│  Song                  Duration  BPM  Tracks  Analyzed   │
│  Highway to Hell       3:28      116  34      2h ago     │
│  Jingle Bell Rock      2:05      120  34      1d ago     │
│  ...                                                     │
└──────────────────────────────────────────────────────────┘
```

**Features:**
- Drag-and-drop MP3 upload with progress bar
- Toggle algorithm families (vamp, madmom) and features (stems, phonemes)
- Library of previously analyzed songs — click to open
- SSE progress stream during analysis (per-algorithm status)
- Auto-navigates to timeline when analysis completes

### 2. Library Scanning Mode

When launched with a directory, shows scored hierarchy entries:

```
┌──────────────────────────────────────────────────────────┐
│  Song Library: /Users/rob/mp3/                           │
│                                                          │
│  Song              Duration  BPM  Overall  Bars  Beats   │
│  Highway to Hell   3:28      116  0.92     0.95  0.98    │
│  Jingle Bell Rock  2:05      120  0.88     0.90  0.94    │
│  Silent Night      3:15       72  0.71     0.68  0.82    │
│                                                          │
│  Click a song to open its timeline                       │
└──────────────────────────────────────────────────────────┘
```

Scores come from hierarchy validation — bars, beats, sections, L4 transient rate.

### 3. Timeline Review Mode

The main analysis visualization:

```
┌──────────────────────────────────────────────────────────────────────┐
│ [▶] 1:23.4 / 3:28.1    [◀ Prev] [Next ▶]    Zoom: [−] 100% [+]    │
├──────┬───────────────────────────────────────────────────────────────┤
│      │ 0:00    0:30    1:00    1:30    2:00    2:30    3:00         │
│      │  │intro  │  verse 1  │ chorus │ verse 2│chorus │bridge│outro│
│      ├──┼───────┼───────────┼────────┼────────┼───────┼──────┼─────┤
│ [x]  │  madmom_beats (0.98) drums                                   │
│ beat │  | | | | | | | | | | | | | | | | | | | | | | | | | | | | | │
│      ├──┼───────────────────────────────────────────────────────────┤
│ [x]  │  qm_bars (0.95) drums                                       │
│ bar  │  |       |       |       |       |       |       |       |   │
│      ├──┼───────────────────────────────────────────────────────────┤
│ [ ]  │  librosa_onsets (0.82) full_mix                              │
│onset │  ||| || |||| ||| || |||| ||| || |||| ||| || |||| ||| || |||| │
│      ├──┼───────────────────────────────────────────────────────────┤
│ [ ]  │  bbc_energy (0.90) full_mix                                  │
│curve │  ~~~╱‾‾‾╲__╱‾‾‾‾‾╲___╱‾‾‾‾‾‾‾╲__╱‾‾╲___╱‾‾‾‾╲__~~~        │
│      ├──┼───────────────────────────────────────────────────────────┤
│ [ ]  │  chordino_chords (0.88) piano                                │
│harm  │  C    Am    F     G     C     Am    F     G     C            │
└──────┴──┴───────────────────────────────────────────────────────────┘
```

---

## Timeline Features

### Track Lanes

Each algorithm result is shown as a horizontal lane:
- **Vertical lines** for timing marks
- **Continuous curves** for value curves
- **Colored labels** for chord/structure tracks
- **Stem badge** showing which stem was analyzed (drums, vocals, etc.)
- **Quality score** displayed next to the track name

### Color Coding

- **Track lanes:** Color varies by element_type
- **High-density warning:** Tracks with avg_interval < 200ms are highlighted red
- **Song sections:** Colored background bands (intro=blue, verse=green, chorus=orange, bridge=purple, outro=gray)
- **Phoneme layers:** Words in teal, phonemes in amber

### Playback

- **Web Audio API** plays the source MP3
- **Playhead** (vertical red line) moves in real-time
- **Click-to-seek** anywhere on the timeline
- **Beat flash** indicator on the toolbar pulses on each beat

### Navigation

- **Prev/Next buttons** cycle through tracks
- **Focused track** is outlined in blue; others are dimmed
- **Zoom:** Ctrl+/− or mouse wheel+Ctrl (range: 20–500 px/sec)
- **Scroll:** Horizontal scroll follows playback or manual drag

### Track Selection & Export

The left panel has checkboxes for selecting tracks:

1. Check tracks you want to export
2. Selected tracks move to the top ("export queue")
3. Drag to reorder within the queue
4. Click **Export** to download a filtered JSON with only selected tracks

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| Ctrl + | Zoom in |
| Ctrl - | Zoom out |
| Ctrl 0 | Reset zoom to 100% |

---

## Sweep Results View

Accessible from the sweep tab when a sweep report exists:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Sweep Results: Highway to Hell                                       │
│                                                                      │
│ Filter: [All algorithms ▼]  [All stems ▼]  Sort: [Score ▼]          │
│                                                                      │
│ [x] #1  0.95  qm_beats        drums   inputtempo=140                │
│ [x] #2  0.93  madmom_beats    drums   (default)                     │
│ [ ] #3  0.91  qm_onsets_hfc   drums   dftype=0                      │
│ [ ] #4  0.89  librosa_beats   drums   hop=512                       │
│ [ ] #5  0.88  chordino        piano   (default)                     │
│ ...                                                                  │
│                                                                      │
│ Timeline: (selected results overlaid)                                │
│ ┌────────────────────────────────────────────────────────────────┐   │
│ │ qm_beats/drums:    | | | | | | | | | | | | | | | | | | | | | │   │
│ │ madmom_beats/drums: | | | | | | | | | | | | | | | | | | | |  │   │
│ └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

**Features:**
- Filter by algorithm name or stem
- Sort by any column (score, name, mark count)
- Select up to 2 results for side-by-side timeline comparison
- Export selected results as .xtiming/.xvc

---

## Phoneme Editor

Accessible at `/phonemes-view` when phoneme data exists:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Phoneme Editor: Highway to Hell                                      │
│                                                                      │
│ Waveform (vocals stem):                                              │
│ ┌────────────────────────────────────────────────────────────────┐   │
│ │▁▂▅▇█▇▅▂▁▁▁▂▃▅▇█▇▅▃▁▁▁▁▂▄▆█▇▅▃▁▁▂▃▅▇█▇▅▃▂▁▁▁▁▁▂▃▅▇█▇▅▃▁│   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Word         Start      End        Phonemes                         │
│  I            15.23s     15.68s     AI                               │
│  WAS          15.68s     16.10s     WQ AI E                          │
│  MADE         16.10s     16.80s     MBP AI etc                       │
│  FOR          16.80s     17.20s     FV O                             │
│  LOVIN        17.20s     17.90s     L AI FV etc                      │
│  ...                                                                 │
│                                                                      │
│  [Save Changes]                     [Re-phonemize Word]              │
└──────────────────────────────────────────────────────────────────────┘
```

**Features:**
- Vocal waveform display (from vocals stem)
- Drag word boundaries to adjust timing
- Drag phoneme boundaries within words
- Re-phonemize individual words via CMUdict
- Save edits back to the analysis JSON

---

## Flask API Endpoints

Key endpoints the UI calls:

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/` | GET | HTML page (upload, library, or timeline) |
| `/analysis` | GET | Analysis JSON (flattened for UI) |
| `/audio` | GET | MP3 audio stream (with range requests) |
| `/stem-audio?stem=drums` | GET | Stem MP3 stream |
| `/waveform?stem=vocals` | GET | Downsampled amplitude data |
| `/progress` | GET | SSE stream during analysis |
| `/export` | POST | Export selected tracks to JSON |
| `/library` | GET | Library entries list |
| `/hierarchy-library` | GET | Scored hierarchy entries |
| `/sweep-report` | GET | Sweep results JSON |
| `/sweep-winners` | GET | Full-song winner marks |
| `/phonemes` | GET | Phoneme timing data |
| `/phonemize` | POST | Generate phonemes for a word |
| `/save-words` | POST | Save edited word/phoneme timing |

---

## Related Docs

- [Pipeline](pipeline.md) — How analysis data is generated
- [Data Structures](data-structures.md) — What the UI renders
- [Export Formats](export-formats.md) — What gets exported
- [Sweep System](sweep-system.md) — Sweep results displayed in the UI
