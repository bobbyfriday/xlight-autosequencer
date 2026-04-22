# Contract: Native File Dialog IPC

**Feature**: 052-tauri-desktop-packaging
**Status**: Stable contract for v1

The packaged app replaces browser `<input type="file">` pickers and browser download behavior with native macOS Open and Save dialogs, exposed through Tauri's `dialog` plugin. This contract defines how the existing React UI calls into these native dialogs without coupling its core logic to Tauri.

## Principles

- Dev mode (running under Vite + Flask) must continue to work using existing browser file inputs and download behavior.
- Production (bundled) mode uses Tauri dialogs.
- The UI code calls a single `nativeDialog` abstraction; the abstraction is a Tauri wrapper in production and a fallback-to-browser wrapper in dev.

## Operations

### Open audio file(s)

**Frontend (TypeScript)**:
```typescript
const paths: string[] = await nativeDialog.openAudio({
  multiple: true,
  title: "Choose audio files to analyze"
});
```

**Production behavior (Tauri)**:
- Calls `tauri::plugin::dialog::open` with filters `[{ name: "Audio", extensions: ["mp3", "wav", "flac", "m4a", "aiff"] }]`.
- Returns absolute file paths selected by the user.
- User cancels → returns `[]`.

**Dev behavior**:
- Triggers a hidden `<input type="file" accept="audio/*" multiple>` click.
- Returns browser `File` objects wrapped to expose a `.path`-like interface. In dev, path is a synthetic placeholder — the dev flow uses the browser upload endpoint (which the current code already supports). Production flow uses file paths directly against a new/existing `/api/v1/import?path=...` endpoint.

**Contract invariant**: if the frontend received a path, the backend can read that path directly without re-uploading bytes. This is the whole reason to use native dialogs — avoid the round-trip of a multi-megabyte MP3 through an HTTP POST.

### Save generated sequence (.xsq)

**Frontend**:
```typescript
const savePath: string | null = await nativeDialog.saveSequence({
  defaultName: `${songTitle}.xsq`,
  title: "Save xLights sequence"
});
if (savePath) {
  await api.exportSequenceTo(songId, savePath);
}
```

**Production behavior (Tauri)**:
- Calls `tauri::plugin::dialog::save` with filter `[{ name: "xLights Sequence", extensions: ["xsq"] }]`.
- Returns absolute path or `null` on cancel.

**Dev behavior**:
- Falls back to a browser `<a download>` trigger pointing at the backend's existing export endpoint. `savePath` returned as a synthetic marker.

**Backend addition**:
- New endpoint `POST /api/v1/sequence/<song_id>/export-to-path` accepting `{ "path": "<absolute-path>" }` — writes the `.xsq` directly to that path on disk. Only available when `XLIGHT_PACKAGED=1`.

### Relocate missing file

**Frontend**:
```typescript
const newPath: string | null = await nativeDialog.relocateAudio({
  originalPath: "/previous/path/that/no/longer/exists.mp3",
  expectedHash: "abc123..."
});
```

**Production behavior**:
- Same as `openAudio` but single-select, with the dialog starting in the parent directory of `originalPath` if it still exists (otherwise user's home).
- Backend re-associates the library entry with the new path and re-verifies the MD5 matches the stored `source_hash`. Mismatch surfaces a warning in the UI.

**Dev behavior**: same fallback as `openAudio`.

## Tauri plugin capabilities

`src-tauri/capabilities/main.json` must include:

```json
{
  "identifier": "main",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-execute",
    "dialog:allow-open",
    "dialog:allow-save",
    "event:default",
    "fs:allow-read-file",
    "fs:allow-exists"
  ]
}
```

Notably **NOT** granted: `fs:allow-write-*` (backend does writes via Python, not via the Tauri fs bridge) and any broad shell execution beyond the specific sidecar binary.

## Drag-and-drop

macOS drag-and-drop from Finder onto the app window is handled by Tauri's built-in file-drop event (`tauri://file-drop`). The frontend listens for this event and treats the dropped paths the same as paths returned from the Open dialog — they flow through the same import pipeline.

Dev-mode drag-and-drop uses the existing browser drop handler. The abstraction `nativeDialog.onDrop(callback)` dispatches to whichever source is active.

## Out of scope for v1

- "Open With..." integration (double-click an `.mp3` in Finder to launch the app). This is a document-type registration in `tauri.conf.json` and is a straightforward follow-up but not required for v1.
- Recent files menu.
- Custom file icons for `.xsq` and `.xtiming`.
