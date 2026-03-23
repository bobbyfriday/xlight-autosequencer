# Quickstart: Analysis Cache and Song Library

**Branch**: `010-analysis-cache-library` | **Date**: 2026-03-22

---

## Analysis Caching

After this feature, every `analyze` run saves a cache key (`source_hash`) inside
the output JSON. The next run on the same file is instant.

```bash
# First run — full analysis (1-5 minutes)
xlight-analyze analyze song.mp3

# Second run — cache hit (< 3 seconds)
xlight-analyze analyze song.mp3

# Force re-analysis (ignores cache, overwrites output)
xlight-analyze analyze song.mp3 --no-cache
```

---

## Song Library

Every analyzed song is registered in a library at `~/.xlight/library.json`.

```bash
# Open the review UI home page — shows library of all analyzed songs
xlight-analyze review

# Open the review timeline directly from an audio file path
xlight-analyze review song.mp3

# Open the review timeline from the analysis JSON (existing behaviour unchanged)
xlight-analyze review song_analysis.json
```

---

## Library Location

```
~/.xlight/
└── library.json        ← global song registry (auto-created)
```

To clear the library, delete `~/.xlight/library.json`. The analysis cache
files (`*_analysis.json`) are unaffected — re-running `analyze` re-registers
them in the library.

---

## New Modules for Implementers

### `src/cache.py` — AnalysisCache

```python
class AnalysisCache:
    def __init__(self, audio_path: Path, output_path: Path) -> None: ...
    def is_valid(self) -> bool: ...   # MD5 matches source_hash in output JSON
    def load(self) -> AnalysisResult: ...
    def save(self, result: AnalysisResult) -> None: ...
```

### `src/library.py` — Library

```python
class Library:
    def __init__(self, index_path: Path = DEFAULT_LIBRARY_PATH) -> None: ...
    def upsert(self, entry: LibraryEntry) -> None: ...
    def all_entries(self) -> list[LibraryEntry]: ...   # sorted newest-first
    def find_by_hash(self, source_hash: str) -> LibraryEntry | None: ...
```

---

## Review UI — Library Page

When `xlight-analyze review` is opened with no arguments, the home page shows:

- A list of all previously analyzed songs (sorted most recent first)
- Each row: filename, duration, BPM, tracks, stem flag, analysis date
- Clicking a row loads that song's analysis in the timeline (no re-analysis)
- Songs whose source file is missing are shown with a ⚠ badge
- An "Analyze new file" section (drag-drop upload) is still present below the library

---

## Running Tests

```bash
pytest tests/unit/test_cache.py -v        # AnalysisCache unit tests
pytest tests/unit/test_library.py -v      # Library unit tests
pytest tests/integration/test_cache_pipeline.py -v  # End-to-end cache pipeline
pytest tests/ -v                          # All tests
```
