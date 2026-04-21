# Phase 1 Data Model: x-onset Frontend Redo

Defines every entity that crosses the `/api/v1` boundary or is persisted to disk, with field-level validation rules traceable to the spec's FR-NNN identifiers.

**Conventions**
- Time values are **integers in milliseconds** unless otherwise noted (matches the backend invariant in [CLAUDE.md](../../CLAUDE.md)).
- Colors are CSS hex strings (`"#RRGGBB"`).
- IDs are opaque strings; no embedded semantics the frontend parses.
- All JSON uses snake_case field names; TypeScript types transform to camelCase at the API-client boundary.
- Every persisted JSON file carries `schema_version: <int>`.

---

## Song

The central library entity. One Song per unique piece of audio.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `song_id` | string (16 hex) | Identity. First 16 hex chars of SHA-256 of audio bytes. | FR-001a |
| `title` | string | Extracted from ID3 tag on import; falls back to filename stem. | FR-001 |
| `artist` | string or null | ID3 tag; may be null. | FR-001 |
| `duration_ms` | int | Computed at import from audio decode. > 0. | FR-001 |
| `bpm` | float or null | From analysis; null until analysis completes. | FR-019 |
| `key` | string or null | From analysis; e.g., `"A major"`. | FR-019 |
| `time_signature` | [int, int] or null | From analysis; default `[4, 4]` when detected. | FR-019 |
| `status` | enum | One of `"draft" \| "analyzed" \| "themed" \| "source_missing"`. | FR-001, FR-012a, FR-029a |
| `source_paths` | string[] | Absolute paths seen on this machine (1+). Same audio reachable from multiple paths is deduped on `song_id`. | FR-001a |
| `folder_id` | string | FK to Folder. Defaults to the well-known `"unfiled"` folder. | FR-004 |
| `imported_at` | string (ISO-8601) | First-import timestamp. | — |
| `last_opened_at` | string (ISO-8601) or null | For "last active song" restore. | SC-004 |

**Status transitions**

```
draft ─▶ analyzed           (analysis completes successfully, FR-012a auto-populates defaults)
analyzed ─▶ themed          (user visits theme screen and confirms assignments per FR-029a)
themed ─▶ analyzed          (user triggers re-analysis; FR-013a review dialog adjudicates before commit)
any ─▶ source_missing       (audio source file not found on disk; playback/preview/export blocked, edits allowed)
source_missing ─▶ prior     (user successfully locates the audio again; status restored)
draft ─▶ draft              (analysis interrupted; partial run discarded per FR-011a)
```

**Invariants**
- `song_id` is immutable across the song's lifetime.
- If `status == "themed"`, every section has a non-null `theme_id` in its assignment (FR-029a, FR-035).
- `source_paths` has ≥ 1 entry; the first entry is the most-recently-seen path.
- If `status == "source_missing"`: theme-assignment edits and section edits are allowed (read-only from audio's perspective); playback, live lights preview, and export are blocked. The UI renders all audio-dependent controls in a disabled state with a "source file missing — click to locate" affordance (FR-001a).
- `source_missing` is not a terminal state: once the user locates the audio, status reverts to its prior value (`draft`, `analyzed`, or `themed`).

---

## Section

A labeled time range within a song.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `index` | int | 0-based ordinal in section list; used for stable references. | FR-014 |
| `start_ms` | int | ≥ 0, < `end_ms`. | FR-014 |
| `end_ms` | int | ≤ `song.duration_ms`. | FR-014 |
| `kind` | enum | One of `"intro" \| "verse" \| "chorus" \| "solo" \| "bridge" \| "outro" \| "unknown"`. | FR-014 |
| `label` | string | User-facing display name; default auto-generated (`"Chorus 1"`). Length 1–64; trimmed. | FR-024 |

**Invariants**
- Sections are contiguous: `sections[i].end_ms == sections[i+1].start_ms` for all `i`.
- `sections[0].start_ms == 0`; `sections[-1].end_ms == song.duration_ms`.
- At least one Section always exists (FR-023).
- Two adjacent sections MUST NOT have `end_ms - start_ms < 500` in either section after a split (FR-021).

---

## Boundary

Analyzer-detected section divider, either active ("real") or latent ("ghost").

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `at_ms` | int | 0 < `at_ms` < `song.duration_ms`. | FR-025 |
| `kind` | enum | `"real" \| "ghost"`. | FR-025 |
| `confidence` | float | 0.0–1.0. | — |
| `promoted_by_user` | bool | True if a ghost was promoted to a real boundary by the user. | FR-025 |

**Invariants**
- Real boundaries correspond 1:1 to the edges between consecutive Sections.
- A ghost boundary can only be promoted if doing so does not create a sub-500ms section (FR-021).
- `reset_to_detected` restores the analyzer's original boundaries (all user splits/merges reverted, no ghosts promoted) (FR-026).

---

## Theme

A named lighting behavior. Built-in for v0 (FR-028); user-authored themes are explicitly out of scope.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `theme_id` | string | Stable across versions (built-in IDs only in v0). | assumption "built-in theme set is stable" |
| `name` | string | Display name. | FR-028 |
| `description` | string | Short paragraph shown on theme cards. | FR-028 |
| `accent` | string | CSS hex color — card border/selection highlight color. | FR-028 |
| `swatches` | string[4] | Four CSS hex colors rendered as the card's top bar and in previews. | FR-028 |
| `default_for_kinds` | string[] | List of Section kinds this theme is the analyzer's default for (used by FR-012a auto-population). | FR-012a |

**Invariants**
- `theme_id` values never change between releases during v0.
- Each Section kind has at least one built-in Theme with that kind in `default_for_kinds` (so FR-012a always resolves).

---

## ThemeAssignment

The per-section mapping from section → theme, plus parameter overrides. One object per Section.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `section_index` | int | FK to Section.index within the same Song. | FR-029 |
| `theme_id` | string or null | FK to Theme.theme_id. null only transiently (e.g., immediately after re-analysis orphan). | FR-029, FR-035 |
| `overrides` | ParameterOverride | Per-theme tuning; see below. | FR-032 |
| `user_confirmed` | bool | True once the user has either explicitly assigned or clicked "accept all defaults". Required for status to be `"themed"`. | FR-029a |

**Invariants**
- When `theme_id` changes, `overrides` resets to the new theme's defaults (FR-032a).
- `theme_id == null` ⇒ `user_confirmed == false` and `song.status != "themed"`.

---

## ParameterOverride

Per-section slider values that adjust a theme's behavior without changing the theme.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `brightness` | float | 0.0–1.0, default 1.0. | FR-032 |
| `hit_strength` | float | 0.0–1.0, default 0.5. | FR-032 |
| `dwell_time` | float | 0.25–4.0, default 1.0 (multiplier on the theme's own dwell). | FR-032 |
| `color_shift` | float | −1.0 to +1.0, default 0.0 (hue shift in normalized units). | FR-032 |

**Invariants**
- All four fields always present; defaults applied on theme assignment or theme change (FR-032a).

---

## AnalysisResult

The full output of the backend analysis pipeline for a song. Cached by `song_id`; immutable until replaced by a fresh run.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `song_id` | string | FK to Song. | FR-013 |
| `detected_sections` | Section[] | Immutable — the analyzer's original output (FR-026 reset target). | FR-026 |
| `alt_boundaries` | Boundary[] | Ghost boundaries the analyzer found but did not promote. | FR-025 |
| `beats` | Beat[] | `[{t_ms: int, bar: int, beat: int}]`. | FR-019 |
| `bars` | int[] | Bar start times, ms. | FR-019 |
| `impacts` | {t_ms: int, conf: float}[] | Impact events. | FR-009 |
| `drops` | {t_ms: int, conf: float}[] | Drop events. | FR-009 |
| `peaks` | float[] | Pre-computed waveform peak array for inline-SVG rendering. | research §5 |
| `detectors` | DetectorRun[] | Per-detector status + confidence, for the ANALYZE screen. | FR-009 |
| `completed_at` | string (ISO-8601) | When the run finished. | FR-013 |
| `pipeline_version` | string | Git short SHA of the analyzer code that produced this result. | — |

### DetectorRun (embedded)

| Field | Type | Constraints |
| --- | --- | --- |
| `name` | string | e.g., `"beats"`, `"onsets"`, `"chords"`, `"impacts"`. |
| `library` | string | e.g., `"librosa"`, `"madmom"`, `"qm-vamp"`. |
| `status` | enum | `"queued" \| "running" \| "done" \| "failed"`. |
| `confidence` | float or null | 0.0–1.0 when applicable. |
| `error` | string or null | Present if `status == "failed"`. |

**Invariants**
- An `AnalysisResult` is only persisted when every listed detector reached `"done"` (or `"failed"` — partial-failure results are still persisted, but interrupted runs are not, per FR-011a).

---

## Layout

The imported xLights prop layout. One Layout is active at a time.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `layout_id` | string | Hash of the imported `xlights_rgbeffects.xml` contents; changes on re-import. | FR-036a |
| `display_name` | string | From the xLights file's `<layoutGroup>` or user-provided. | FR-036a |
| `imported_at` | string (ISO-8601) | When the user imported this layout. | FR-036a |
| `props` | Prop[] | Full list extracted from the xLights XML. | FR-036 |
| `total_pixels` | int | Sum across all props. | FR-036 |

### Prop (embedded)

| Field | Type | Constraints |
| --- | --- | --- |
| `name` | string | xLights model/group name. |
| `display_type` | enum | `"SingleLine" \| "Matrix" \| "Tree" \| "Custom" \| ...`. |
| `pixel_count` | int | > 0. |
| `pixel_range` | [int, int] | Start and end indices in the global pixel space. |

---

## Preferences

Per-user machine-local settings.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `mode` | enum | `"dark" \| "light"`. Default `"dark"`. | FR-043 |
| `density` | enum | `"compact" \| "comfortable"`. Default `"comfortable"`. | FR-044 |
| `inspector_open` | bool | Default true. | FR-045 |
| `tweaks_open` | bool | Default false. | FR-043 |
| `last_song_id` | string or null | For session restore. | SC-004 |
| `last_screen` | enum | `"library" \| "drop" \| "analyze" \| "timeline" \| "theme" \| "export"`. Default `"library"`. | SC-004 |
| `last_playhead_ms_by_song` | {[song_id: string]: int} | Per-song playhead memory. | SC-004 |
| `layout_id` | string or null | Currently active layout; null if never imported. | FR-036b |
| `library_state_version` | int | Bumped on every library mutation for import-merge conflict resolution. | FR-049c |

**Persistence cadence**: every meaningful change writes durably (FR-049a). High-frequency values (`last_playhead_ms_by_song`) debounce to 1s (FR-049b).

---

## Folder

User-created library grouping.

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `folder_id` | string | UUID; reserved `"unfiled"` ID for the default folder. | FR-004 |
| `name` | string | Length 1–64. | FR-004 |
| `collapsed` | bool | Rail display state. | FR-004 |
| `order` | int | Display order within the rail. | FR-004 |

**Invariants**
- The `"unfiled"` folder is always present and cannot be deleted or renamed.
- Deleting a non-empty user folder moves its songs to `"unfiled"` (FR-004).

---

## Bundle

Library export/import package (the `.xonset-bundle` zip contents).

| Field | Type | Constraints | Source |
| --- | --- | --- | --- |
| `schema_version` | int | Bundle format version; currently `1`. | — |
| `exported_at` | string (ISO-8601) | When the bundle was produced. | FR-049c |
| `exported_by` | string | Hostname or user-provided label. | FR-049c |
| `library` | Library | The same Library structure as persisted on disk. | FR-049c |
| `sessions` | {[song_id]: Session} | Per-song edits (sections, assignments, overrides). | FR-049c |

**Invariants**
- Audio files are NOT included (FR-049c). On import, each bundle-referenced `song_id` without a matching audio file on disk lands as `status == "source_missing"` (FR-001a + source-missing edge case).

---

## Session (persisted per song)

The on-disk sidecar file that holds per-song editable state, written to `~/.xlight/library/songs/<song_id>/session.json`.

| Field | Type | Constraints |
| --- | --- | --- |
| `schema_version` | int | Session file format version. |
| `song_id` | string | For sanity-check on read. |
| `sections` | Section[] | The user's edited section list (initially the analyzer's detected_sections; diverges via FR-021, FR-022, FR-023, FR-024, FR-025, FR-026). |
| `assignments` | ThemeAssignment[] | Indexed by `section_index`; same length as `sections`. |

**Invariants**
- `sections.length == assignments.length` always.
- Opening a song in read-only mode (source-missing) loads this file but blocks writes until audio is relocated.

---

## Library (persisted index)

The on-disk `~/.xlight/library/library.json` file.

| Field | Type | Constraints |
| --- | --- | --- |
| `schema_version` | int | Library file format version. |
| `songs` | Song[] | All imported songs. |
| `folders` | Folder[] | All folders (always includes the `"unfiled"` reserved folder). |
| `preferences` | Preferences | Embedded, not a separate file. |
| `layout` | Layout or null | Currently imported xLights layout, if any. |

---

## Summary field-reference table

Mapping Spec FR → Entity/field:

| FR | Entity field(s) |
| --- | --- |
| FR-001 | Song.{title, artist, duration_ms, status} |
| FR-001a | Song.song_id, Song.source_paths |
| FR-002 | — (filter state is transient UI, not persisted) |
| FR-003 | Preferences.last_screen routing rule |
| FR-004 | Folder, Song.folder_id |
| FR-005 / FR-005a / FR-005b / FR-005c | Library, Session, delete actions |
| FR-011a | AnalysisResult (only persisted when complete) |
| FR-012a | ThemeAssignment.theme_id auto-populated from Theme.default_for_kinds |
| FR-013a | Bundle-like mapping not persisted; used in re-analysis review dialog |
| FR-019 | Song.{bpm, key, time_signature}, AnalysisResult.{beats, bars} |
| FR-021 / FR-022 / FR-025 | Section operations + ThemeAssignment inheritance |
| FR-029 / FR-029a | ThemeAssignment.{theme_id, user_confirmed} |
| FR-032 / FR-032a | ParameterOverride |
| FR-036a / FR-036b | Layout, Preferences.layout_id |
| FR-043 – FR-046 | Preferences.{mode, density, inspector_open, tweaks_open} |
| FR-049 / FR-049a / FR-049b / FR-049c | Library, Session, Bundle |
