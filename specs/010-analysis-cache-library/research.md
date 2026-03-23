# Research: Analysis Cache and Song Library

**Branch**: `010-analysis-cache-library` | **Date**: 2026-03-22
**Phase**: 0 — All NEEDS CLARIFICATION resolved before Phase 1 design

---

## Decision 1: Analysis Cache Storage — Reuse Existing Output File

**Decision**: Treat the existing `<stem>_analysis.json` output file as the cache. Add a `source_hash` (MD5) field to `AnalysisResult`. On `analyze`, check whether the output JSON already exists and its `source_hash` matches the current file. If so, return it as a cache hit.

**Rationale**:
- Zero new directory structure. The existing `_analysis.json` already sits next to the source file — that is the natural cache location.
- Any user who already ran `analyze` once will benefit after a tool update that adds `source_hash` — re-running produces a cached file that future runs can skip.
- Reuses the existing `export.read()` / `export.write()` paths unchanged.
- Simpler than a separate `.analysis/<hash>/` directory: no manifest files, no parallel hierarchy.

**Alternatives considered**:

| Approach | Reason Rejected |
|----------|----------------|
| `.analysis/<md5>/analysis.json` adjacent to source | Extra indirection; `_analysis.json` already serves as the output; two parallel files for the same analysis is confusing |
| `~/.xlight/cache/<md5>.json` central cache | Good for deduplication but breaks the "file lives next to the song" mental model; harder to move/clean up |
| Timestamp-based (skip if output file is newer than source) | Unreliable — file copy resets mtime; content hash is authoritative |

---

## Decision 2: Library Index Location — `~/.xlight/library.json`

**Decision**: Maintain a global library index at `~/.xlight/library.json`. Every successful `analyze` run upserts an entry keyed by `source_hash`. The review UI reads this file via a Flask endpoint to populate the library page.

**Rationale**:
- Songs can live anywhere on disk. A global index is the only way to list them all without scanning the filesystem.
- `~/.xlight/` follows the XDG-style convention (`~/.config` equivalent) for per-user tool state without requiring root.
- Simple flat JSON file — no database, no dependencies, O(n) reads are fast for ≤500 entries (SC-002).
- Consistent with how many CLI tools (e.g., `brew`, `pip`) maintain their own metadata in `~/.<tool>/`.

**Alternatives considered**:

| Approach | Reason Rejected |
|----------|----------------|
| Scan filesystem for `*_analysis.json` on every open | Slow for large music libraries; requires knowing which directories to scan |
| SQLite at `~/.xlight/library.db` | Overkill for 500 entries; adds a dependency |
| Library embedded in each `_analysis.json` | Doesn't solve discovery — still need to know where the files are |

---

## Decision 3: Library UI — Replaces Upload Home Page

**Decision**: When `xlight-analyze review` is run with no arguments, serve a library page that lists all previously analyzed songs. An "Analyze new file" button / drag-drop zone replaces the current upload-only home page. The library and upload form coexist on the same page.

**Rationale**:
- The current upload-only home page is useful only for first-time analysis. Once songs are in the library, landing on an upload form is the wrong default.
- Colocating library + upload on one page avoids navigation complexity for a single-user local tool.
- No separate route needed — the library is the home page, with upload as a secondary action.

**Alternatives considered**:

| Approach | Reason Rejected |
|----------|----------------|
| Library at `/library`, upload at `/` (separate routes) | Navigation overhead; this is a single-user local tool, not a multi-page app |
| CLI `xlight-analyze library` table | Less information density than a browser page; can't click to open review |

---

## Decision 4: Cache Key — MD5 of Source File Bytes

**Decision**: MD5 hex digest of the full source file content. Stored as `source_hash` on `AnalysisResult`. Same algorithm as the stem cache (feature 008) for consistency.

**Rationale**:
- Same reasoning as feature 008: faster than SHA-256 for file sizes up to 10 MB (< 50 ms), reliable against file copies that reset mtime.
- Using the same hash for both stem cache directory name and analysis cache validation means one MD5 computation per `analyze` run covers both.

---

## Decision 5: `review` Command with Audio File

**Decision**: When `review` receives a path that is not a `.json` file, treat it as an audio file, compute its MD5, look up the library index for a matching `source_hash`, and open that analysis. Fail with a clear error if not found.

**Rationale**:
- Minimal code change: just check file extension before the existing JSON-parsing path.
- Leverages the library index — no filesystem scanning needed.

---

## Decision 6: `--no-cache` Flag Behaviour

**Decision**: `--no-cache` re-runs all algorithms, overwrites the existing `_analysis.json`, and updates the library entry. It does **not** delete the stem cache — stems are expensive and independent of the analysis cache.

**Rationale**:
- Stems are correct for the same file regardless of analysis options. Invalidating them on `--no-cache` would force a 2-minute re-separation for no benefit.
- Overwriting the library entry (not appending) keeps the index clean — one entry per source file.

---

## Resolved: All Open Questions

| Question | Resolution |
|----------|-----------|
| Cache storage location | Reuse `_analysis.json`; add `source_hash` field |
| Library index location | `~/.xlight/library.json` |
| Library UI placement | Home page of review UI (replaces upload-only) |
| Cache key | MD5 of source file bytes (same as stems) |
| `--no-cache` scope | Re-runs analysis + updates library; keeps stem cache |
| Schema mismatch handling | Missing `source_hash` → treated as no cache; file re-analyzed |
