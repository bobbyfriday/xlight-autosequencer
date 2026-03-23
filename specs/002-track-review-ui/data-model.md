# Data Model: Timing Track Review UI

**Feature**: 002-track-review-ui
**Date**: 2026-03-22

---

## Entities

### ReviewSession

The runtime state of the review UI for one loaded song + analysis pair.

| Field | Type | Description |
|-------|------|-------------|
| `analysis_path` | `str` | Absolute path to the loaded `_analysis.json` file |
| `audio_path` | `str` | Absolute path to the MP3 file (from analysis JSON or manually located) |
| `duration_ms` | `int` | Total song duration in milliseconds |
| `tracks` | `list[TrackLane]` | All timing tracks, sorted by quality_score descending |
| `focus_index` | `int \| None` | Index into `tracks` of the currently focused track; `None` = no focus |

**State transitions**:
- Created when user loads analysis JSON and audio file resolves
- `focus_index` cycles via Next/Prev; set directly via Solo; cleared via Clear Focus
- `tracks[i].selected` toggled independently of `focus_index`

---

### TrackLane

The client-side representation of one timing track, derived from a `TimingTrack` in the analysis JSON.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Track name (e.g., `"qm_beats"`) |
| `algorithm_name` | `str` | Source algorithm identifier |
| `element_type` | `str` | Category: `"beat"`, `"onset"`, `"harmonic"`, `"structural"`, etc. |
| `quality_score` | `float` | 0.0–1.0; higher is better for lighting use |
| `mark_count` | `int` | Number of timing marks in this track |
| `avg_interval_ms` | `int \| None` | Average gap between consecutive marks in ms; `None` if < 2 marks |
| `marks_ms` | `list[int]` | Sorted list of mark timestamps in milliseconds |
| `selected` | `bool` | Whether this track is included in the export selection (default: `True`) |
| `is_high_density` | `bool` | `True` if `avg_interval_ms < 200` or `quality_score == 0.0` |

**Derivation rules**:
- `avg_interval_ms`: computed from `marks_ms` differences; `None` if `len(marks_ms) < 2`
- `is_high_density`: `quality_score == 0.0 or (avg_interval_ms is not None and avg_interval_ms < 200)`
- `selected`: initialized to `True` for all tracks on load

---

### Playhead

The current audio position, maintained by the client during playback.

| Field | Type | Description |
|-------|------|-------------|
| `position_ms` | `int` | Current audio position in milliseconds |
| `is_playing` | `bool` | Whether audio is actively playing |

**Update rules**:
- While playing: `position_ms` is derived from `AudioContext.currentTime` on each animation frame (60fps target)
- On seek: `position_ms` is set immediately when the user clicks the timeline
- On pause: `position_ms` is frozen at the last known position
- On end: `position_ms` is set to `duration_ms`; `is_playing` → `False`

---

### ExportSelection

The filtered view written to disk when the user clicks Export Selection.

| Field | Type | Description |
|-------|------|-------------|
| `source_path` | `str` | Path of the source analysis JSON |
| `output_path` | `str` | Default: `<source_basename>_selected.json` alongside source |
| `selected_tracks` | `list[TimingTrack]` | Only the tracks where `TrackLane.selected == True` |

**Schema**: The exported JSON MUST use the same `AnalysisResult` schema as the source analysis file (same top-level keys: `song_path`, `duration_ms`, `analyzed_at`, `tracks`). Only the `tracks` array is filtered; all other fields are copied verbatim from the source.

**Validation**:
- `len(selected_tracks) == 0` → error; do not write file
- Output path already exists → warn user before overwriting

---

## Relationships

```
ReviewSession
  └── tracks: list[TrackLane]   (1 session → N lanes, derived from AnalysisResult.tracks)
  └── focus_index → TrackLane   (points into the tracks list; None = no focus)

ExportSelection
  └── selected_tracks: subset of ReviewSession.tracks where selected == True
```

---

## Mapping to Analysis JSON Schema

The analysis JSON produced by `xlight-analyze analyze` has this structure:

```json
{
  "song_path": "...",
  "duration_ms": 289000,
  "analyzed_at": "2026-03-22T10:00:00",
  "tracks": [
    {
      "name": "qm_beats",
      "algorithm_name": "qm_beats",
      "element_type": "beat",
      "quality_score": 0.87,
      "marks": [
        {"time_ms": 512, "confidence": null},
        ...
      ]
    }
  ]
}
```

`TrackLane` is derived from each element of `tracks`. `ReviewSession.duration_ms` comes from the top-level `duration_ms`. All fields needed for export are already in this schema — no new schema design required.
