# API v1 Contracts — x-onset Frontend Redo

One file per resource group. All endpoints live under `/api/v1/`.

## Conventions

- **Versioning**: URL-versioned at `/api/v1/`. Breaking changes cut a new version; old versions retire on cutover.
- **Content type**: Requests and responses are `application/json; charset=utf-8` unless specified (file uploads use `multipart/form-data`; progress streams use `text/event-stream`; audio uses `audio/mpeg` / `audio/wav` / `audio/flac` / `audio/aiff`).
- **Time**: All time values in request and response bodies are **integer milliseconds**. Never seconds, never floats (matches [CLAUDE.md](../../../CLAUDE.md) invariant: "Timestamps are always stored as integers (milliseconds) — never floats").
- **Song identifiers in URLs**: `<song_id>` is the 16-character hex prefix of SHA-256(audio_bytes) per FR-001a.
- **Errors**:
  ```json
  { "error": { "code": "string", "message": "string", "details": {} } }
  ```
  Stable `code` values listed per endpoint. Status codes follow convention: 400 validation, 404 not-found, 409 conflict, 422 unprocessable, 500 server.
- **Idempotency**: All mutations that could be retried safely (layout import, library import, export) are idempotent on identical input.
- **Case**: JSON fields are `snake_case` on the wire. The TypeScript API client transforms to `camelCase` at the boundary.
- **Authentication**: none in v0. Backend binds to `127.0.0.1` only (local-only assumption).

## Endpoint map

| Group | File | Covers |
| --- | --- | --- |
| Library | [library.md](./library.md) | `GET /library`, folder CRUD, `DELETE /songs/<id>`, `POST /songs/<id>/purge` |
| Import | [import.md](./import.md) | `POST /import` (multipart) |
| Analysis | [analysis.md](./analysis.md) | `POST /songs/<id>/analyze`, `GET /songs/<id>/analyze/status` (SSE), `GET /songs/<id>/analysis` |
| Sections | [sections.md](./sections.md) | section list + split/merge/rename/delete/promote-ghost/reset |
| Themes | [themes.md](./themes.md) | `GET /themes` (built-in catalog) |
| Assignments | [assignments.md](./assignments.md) | theme + parameter overrides per section, with `user_confirmed` flip |
| Export | [export.md](./export.md) | `POST /songs/<id>/export`, `GET /songs/<id>/export/status` |
| Layout | [layout.md](./layout.md) | `POST /layout`, `GET /layout` |
| Preferences | [preferences.md](./preferences.md) | `GET /preferences`, `PUT /preferences`, library export / import bundle |

## Non-API routes (served by the same Flask process)

| Path | Purpose |
| --- | --- |
| `GET /` | Serves the built SPA (`src/review/frontend/dist/index.html`). |
| `GET /assets/*` | Serves SPA static assets (`src/review/frontend/dist/assets/`). |
| `GET /audio/<song_id>` | Streams audio from the song's first resolvable `source_path`, with `Accept-Ranges: bytes` support. Returns 404 with `{"error": {"code": "source_file_missing"}}` if no path resolves. |

## Cross-cutting acceptance rules

Derived from spec FRs; every implementing endpoint test asserts the relevant ones:

- A request that would push a song into `"themed"` status without satisfying FR-029a (user confirmation) MUST return 409 `status_transition_forbidden`.
- Any mutation on a song while `status == "source_missing"` that requires audio (playback, preview, export — FR-035a, edge case "MP3 moved or deleted after import") MUST return 409 `source_file_missing`.
- Writes to section structure or theme assignments MUST be durable before the response returns 200 (FR-049a).
- Section operations that would produce a sub-500ms section (FR-021) MUST return 422 `section_too_short`.
- Deleting the only remaining section (FR-023) MUST return 422 `last_section_required`.
- An export request against a song with any section where `theme_id == null` OR `user_confirmed == false` (FR-035, FR-029a) MUST return 409 `incomplete_theming` with a `details.missing_sections` array of section indexes.
- An export request when `preferences.layout_id == null` (FR-036b) MUST return 409 `layout_required`.
