# Data Model: In-Browser MP3 Upload and Analysis

**Feature**: 007-upload-and-analyze
**Date**: 2026-03-22

---

## Entities

### AnalysisJob

The server-side state object for a single upload-triggered analysis run. Lives in `app.config['CURRENT_JOB']` (or a module-level reference) for the duration of the analysis.

| Field | Type | Description |
|-------|------|-------------|
| `mp3_path` | `str` | Absolute path to the saved MP3 file |
| `include_vamp` | `bool` | Whether Vamp plugin algorithms are included |
| `include_madmom` | `bool` | Whether madmom algorithms are included |
| `status` | `str` | One of: `"running"`, `"done"`, `"error"` |
| `events` | `list[ProgressEvent]` | Ordered list of progress updates appended as algorithms complete |
| `total` | `int` | Total number of algorithms scheduled to run |
| `result_path` | `str \| None` | Absolute path to `_analysis.json` once written; `None` until complete |
| `error_message` | `str \| None` | Set if `status == "error"` (e.g., zero tracks produced, disk full) |
| `lock` | `threading.Lock` | Protects `events`, `status`, `result_path`, `error_message` from race conditions |

**State transitions**:
```
None → "running"  (on POST /upload, analysis thread starts)
"running" → "done"   (all algorithms complete, result written)
"running" → "error"  (zero tracks produced or write failure)
"done" / "error" → None  (cleared when a new upload is accepted)
```

---

### ProgressEvent

A single progress update produced by the analysis thread and consumed by the SSE stream.

| Field | Type | Description |
|-------|------|-------------|
| `idx` | `int` | 1-based index of this algorithm in the run order |
| `total` | `int` | Total number of algorithms in this run |
| `name` | `str` | Algorithm name (e.g., `"qm_beats"`, `"librosa_drums"`) |
| `mark_count` | `int` | Number of timing marks produced (0 if failed) |
| `ok` | `bool` | `True` if the algorithm succeeded; `False` if it raised an exception |

**SSE wire format** (one event per algorithm completion):
```
data: {"idx": 3, "total": 18, "name": "librosa_beats", "mark_count": 142, "ok": true}\n\n
```

**Terminal events** (sent once at the end):
```
data: {"done": true, "result_path": "/path/to/song_analysis.json"}\n\n
data: {"error": "All algorithms failed — no tracks produced"}\n\n
```

---

### UploadRequest

The data parsed from `POST /upload` before the job starts.

| Field | Type | Source | Validation |
|-------|------|--------|------------|
| `file` | `FileStorage` | `request.files['mp3']` | Must have `.mp3` extension and `audio/mpeg` content type |
| `include_vamp` | `bool` | `request.form.get('vamp', 'true')` | Defaults to `True` if absent |
| `include_madmom` | `bool` | `request.form.get('madmom', 'true')` | Defaults to `True` if absent |

---

## Relationships

```
AnalysisJob
  └── events: list[ProgressEvent]   (appended in order as algorithms complete)

POST /upload → creates AnalysisJob → starts analysis thread
GET /progress → reads AnalysisJob.events (SSE stream)
GET /job-status → reads AnalysisJob.{status, result_path, error_message}
```

---

## Mapping to Existing Pipeline

The analysis thread calls the existing `AnalysisRunner` with a custom `progress_callback`. The callback creates a `ProgressEvent` and appends it (under lock) to `AnalysisJob.events`. No changes to `AnalysisRunner`, `TimingTrack`, or `AnalysisResult` are needed.

```
AnalysisRunner.run(mp3_path, progress_callback=job.record_progress)
  → progress_callback(idx, total, name, mark_count) called per algorithm
  → appends ProgressEvent to job.events
  → SSE generator reads job.events and yields SSE data lines
```
