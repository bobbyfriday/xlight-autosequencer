# CLI Contract: xlight-analyze

**Branch**: `001-audio-timing-tracks` | **Date**: 2026-03-22

The `xlight-analyze` command has three subcommands: `analyze`, `summary`, and `export`.

---

## Top-Level Usage

```
xlight-analyze [--help] <command> [args]
```

---

## Command: analyze

Runs all audio analysis algorithms on an MP3 file and writes a JSON result file.

```
xlight-analyze analyze <MP3_FILE> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `MP3_FILE` | yes | Path to the input MP3 file |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output PATH` | `<input_basename>_analysis.json` alongside the MP3 | Path for the output JSON file |
| `--algorithms TEXT` | `all` | Comma-separated algorithm names to run, or `all`. Example: `qm_beats,drums,bass` |
| `--no-vamp` | off | Skip all Vamp plugin algorithms. Useful if Vamp plugins are not installed. |
| `--no-madmom` | off | Skip madmom algorithms. |
| `--top INTEGER` | (off) | After analysis, automatically select and export the top N tracks by quality score, writing a `<basename>_top<N>.json` file alongside the full analysis output. |

### Stdout

Progress per algorithm, then the full scored summary table:

```
Analyzing: /path/to/song.mp3 (3:04) | BPM: ~120.5
  [ 1/22] qm_beats (Vamp: QM bar-beat tracker)        ... done (240 marks)
  [ 2/22] qm_bars (Vamp: QM bar-beat tracker)         ... done (60 marks)
  [ 3/22] qm_tempo_changes (Vamp: QM tempo tracker)   ... done (8 marks)
  [ 4/22] qm_onsets_complex (Vamp: QM onset)          ... done (612 marks)
  [ 5/22] qm_onsets_hfc (Vamp: QM onset HFC)          ... done (843 marks)
  [ 6/22] qm_onsets_phase (Vamp: QM onset phase)      ... done (731 marks)
  [ 7/22] qm_segments (Vamp: QM segmenter)            ... done (6 marks)
  [ 8/22] beatroot (Vamp: BeatRoot)                   ... done (238 marks)
  [ 9/22] pyin_notes (Vamp: pYIN)                     ... done (187 marks)
  [10/22] pyin_pitch_changes (Vamp: pYIN smooth)      ... done (312 marks)
  [11/22] chord_changes (Vamp: Chordino)              ... done (48 marks)
  [12/22] chroma_peaks (Vamp: NNLS chroma)            ... done (224 marks)
  [13/22] librosa_beats (librosa)                     ... done (241 marks)
  [14/22] librosa_bars (librosa)                      ... done (61 marks)
  [15/22] librosa_onsets (librosa)                    ... done (1842 marks)
  [16/22] bass (librosa)                              ... done (312 marks)
  [17/22] mid (librosa)                               ... done (428 marks)
  [18/22] treble (librosa)                            ... done (891 marks)
  [19/22] drums (librosa HPSS)                        ... done (487 marks)
  [20/22] harmonic_peaks (librosa HPSS)               ... done (203 marks)
  [21/22] madmom_beats (madmom RNN+DBN)               ... done (241 marks)
  [22/22] madmom_downbeats (madmom RNN)               ... done (60 marks)

Analysis complete. Output: song_analysis.json

Track Summary (sorted by quality score):
  SCORE  NAME               TYPE        MARKS   AVG INTERVAL
  0.91   qm_beats           beat          240        500 ms
  0.90   madmom_beats       beat          241        499 ms
  0.89   beatroot           beat          238        504 ms
  0.88   qm_bars            bar            60       2001 ms
  0.87   madmom_downbeats   bar            60       2001 ms
  0.85   librosa_beats      beat          241        499 ms
  0.84   chord_changes      harmonic       48       3750 ms
  0.83   drums              percussion    487        250 ms
  0.81   qm_segments        structure       6      30000 ms
  0.79   pyin_notes         melody        187        594 ms
  0.77   chroma_peaks       harmonic      224        500 ms
  0.75   bass               frequency     312        385 ms
  0.72   harmonic_peaks     harmonic      203        594 ms
  0.71   qm_onsets_complex  onset         612        196 ms
  0.70   mid                frequency     428        280 ms
  0.65   librosa_bars       bar            61       1984 ms
  0.63   pyin_pitch_changes melody        312        385 ms
  0.61   qm_onsets_phase    onset         731        165 ms  ** HIGH DENSITY
  0.55   qm_tempo_changes   tempo           8      22500 ms
  0.52   qm_onsets_hfc      onset         843        143 ms  ** HIGH DENSITY
  0.48   treble             frequency     891        135 ms  ** HIGH DENSITY
  0.22   librosa_onsets     onset        1842         98 ms  ** HIGH DENSITY

Use --top N or 'xlight-analyze export' to select tracks.
```

Tracks with average interval < 200ms are flagged `** HIGH DENSITY`.
The table is sorted by `quality_score` descending — the best tracks for lighting are at the top.

If `--top N` was specified:
```
Auto-selecting top 5 tracks by quality score...
Output: song_top5.json
```

### Stderr

```
WARNING: pyin plugin not found at ~/Library/Audio/Plug-Ins/Vamp/. pyin_notes, pyin_pitch_changes skipped.
WARNING: madmom_beats failed: [error]. Track omitted.
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success — output file written |
| 1 | Input file not found or not a valid MP3 |
| 2 | All algorithms failed — no output written |
| 3 | Output path not writable |

---

## Command: summary

Prints the scored summary table from an existing analysis JSON. Does not re-analyze.

```
xlight-analyze summary <ANALYSIS_JSON> [--top INTEGER]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `ANALYSIS_JSON` | yes | Path to an existing `_analysis.json` file |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--top INTEGER` | (off) | Show only the top N tracks by quality score |

### Stdout

```
Source: song.mp3 (3:04) | BPM: 120.5 | Analyzed: 2026-03-22T10:00:00Z | 22 tracks

Track Summary (sorted by quality score):
  SCORE  NAME               TYPE        MARKS   AVG INTERVAL
  0.91   qm_beats           beat          240        500 ms
  ...
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | File not found or not valid JSON |

---

## Command: export

Filters an existing analysis to a subset of tracks and writes a new JSON file.
Does NOT re-analyze.

```
xlight-analyze export <ANALYSIS_JSON> [--select TEXT | --top INTEGER] [OPTIONS]
```

Exactly one of `--select` or `--top` must be provided.

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `ANALYSIS_JSON` | yes | Path to an existing `_analysis.json` file |

### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--select TEXT` | one of | Comma-separated track names to keep (e.g., `qm_beats,drums,bass`) |
| `--top INTEGER` | one of | Automatically keep the top N tracks by quality score |
| `--output PATH` | no | Output path. Default: `<input_basename>_selected.json` |

### Stdout

```
Exporting top 5 of 22 tracks from song_analysis.json
  0.91   qm_beats           beat          240        500 ms
  0.90   madmom_beats       beat          241        499 ms
  0.89   beatroot           beat          238        504 ms
  0.88   qm_bars            bar            60       2001 ms
  0.83   drums              percussion    487        250 ms

Output: song_selected.json
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Input file not found or invalid |
| 4 | Track name(s) in `--select` not found (lists available names) |
| 5 | Neither `--select` nor `--top` provided |

---

## Full Algorithm Reference

| Name | Source | Element Type | Description |
|------|--------|--------------|-------------|
| `qm_beats` | Vamp: qm-barbeattracker | beat | QM bar-beat tracker — quarter-note beat positions |
| `qm_bars` | Vamp: qm-barbeattracker | bar | QM bar-beat tracker — bar/downbeat positions |
| `qm_tempo_changes` | Vamp: qm-tempotracker | tempo | Points where tempo shifts significantly |
| `qm_onsets_complex` | Vamp: qm-onsetdetector | onset | Complex-domain onset detection |
| `qm_onsets_hfc` | Vamp: qm-onsetdetector | onset | High-frequency content onset detection |
| `qm_onsets_phase` | Vamp: qm-onsetdetector | onset | Phase-deviation onset detection |
| `qm_segments` | Vamp: qm-segmenter | structure | Structural section boundaries |
| `beatroot` | Vamp: beatroot-vamp | beat | BeatRoot induction — robust on irregular rhythms |
| `pyin_notes` | Vamp: pyin | melody | Note onset events from pitch tracker |
| `pyin_pitch_changes` | Vamp: pyin | melody | Points where predominant pitch changes |
| `chord_changes` | Vamp: nnls-chroma/chordino | harmonic | Chord change boundaries |
| `chroma_peaks` | Vamp: nnls-chroma | harmonic | Chromagram energy peak events |
| `librosa_beats` | librosa | beat | librosa beat tracker |
| `librosa_bars` | librosa | bar | Bar markers derived from librosa beats |
| `librosa_onsets` | librosa | onset | librosa onset detection — all transients |
| `bass` | librosa | frequency | Low-frequency energy peaks (20–300 Hz) |
| `mid` | librosa | frequency | Mid-frequency energy peaks (300–4000 Hz) |
| `treble` | librosa | frequency | High-frequency energy peaks (4000 Hz+) |
| `drums` | librosa HPSS | percussion | Percussive component onsets |
| `harmonic_peaks` | librosa HPSS | harmonic | Harmonic component peaks |
| `madmom_beats` | madmom RNN+DBN | beat | Neural-net beat tracker (most accurate) |
| `madmom_downbeats` | madmom RNN | bar | Neural-net downbeat detector |

---

## Notes

- Track names in `--select` are case-sensitive and must match `summary` output exactly.
- The `export` command is non-destructive — the source JSON is never modified.
- All paths may be relative or absolute.
- Vamp plugin algorithms are skipped gracefully if the plugin is not installed.
