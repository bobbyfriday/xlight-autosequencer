# Contract: Sidecar Startup Handshake

**Feature**: 052-tauri-desktop-packaging
**Status**: Stable contract for v1

The Rust Tauri shell launches a PyInstaller-bundled Flask process as a sidecar. The shell must learn which port the backend bound to, then make that available to the frontend. This contract defines that exchange.

## Phases

### Phase 1 — Spawn

**Tauri (Rust)**:
- Spawn the sidecar via `tauri_plugin_shell::process::Command::new_sidecar("backend")` → `.envs(...)` → `.spawn()`.
- Required env vars set on spawn:
  - `VAMP_PATH` — absolute path to bundled Vamp plugin directory (`…/Contents/Resources/vamp`). Already honored by `src/analyzer/capabilities.py:97`.
  - `TORCH_HOME` — absolute path to `~/Library/Application Support/XLight/models/torch-hub` (created if missing).
  - `XLIGHT_PACKAGED` — `"1"`. Backend checks this to switch on bundled-mode behavior (stems fallback, manifest read path).
  - `PYTHONUNBUFFERED` — `"1"`. Required so the stdout handshake line is flushed immediately.

**Backend (Python)**:
- Receives env vars; no special startup action beyond what the Flask app normally does.

### Phase 2 — Bind and announce

**Backend (Python, in `src/review/cli.py` `review()` or new `src/review/bundled_entrypoint.py`)**:
1. Build Flask app via `create_app()` (existing).
2. Bind a socket on `127.0.0.1:0` using `socket.socket(AF_INET, SOCK_STREAM)` → `.bind(("127.0.0.1", 0))` → read `.getsockname()[1]` to learn the OS-assigned port.
3. Close the probe socket (accept the small race window — Flask reopens on the same port within milliseconds and nothing else is likely to snipe it on 127.0.0.1 in that instant).
4. Print exactly one line to stdout:
   ```
   XLIGHT_BACKEND_PORT=<port>
   ```
   Flush immediately (PYTHONUNBUFFERED handles this).
5. Call `app.run(host="127.0.0.1", port=<port>, debug=False, use_reloader=False)` (reloader explicitly off — it would fork and break the handshake).

### Phase 3 — Discover

**Tauri (Rust)**:
- Holds a `Receiver<CommandEvent>` from `spawn()`.
- Loops reading events. For each `CommandEvent::Stdout(line)`:
  - Parse `line` against the regex `^XLIGHT_BACKEND_PORT=(\d+)$`.
  - On match: extract port (u16), emit `app.emit("backend-ready", BackendReadyPayload { port })`, break out of the handshake loop.
  - On non-match: forward to the Tauri app's log sink (so backend log output surfaces in devtools / system log).
- Timeout: if no matching line arrives within 30 seconds, emit `backend-startup-failed` with any captured stdout/stderr and surface an error dialog.
- Continue reading events for the lifetime of the sidecar (to forward logs and detect exit).

### Phase 4 — Frontend wire-up

**Frontend (TypeScript, new `src/review/frontend/src/lib/backendPort.ts`)**:

```typescript
// Pseudocode — actual implementation in tasks phase
export async function resolveBackendBase(): Promise<string> {
  if (import.meta.env.DEV) {
    return "/api"; // Vite proxy handles dev
  }
  if (!window.__TAURI__) {
    throw new Error("Production build must run inside Tauri shell");
  }
  const { listen } = await import("@tauri-apps/api/event");
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Backend did not signal ready within 30s")), 30_000);
    listen<{ port: number }>("backend-ready", (event) => {
      clearTimeout(timer);
      resolve(`http://127.0.0.1:${event.payload.port}`);
    });
    // If the event was already emitted before this listener attached, request a replay
    // via an explicit invoke command that re-emits the cached value.
    invoke("get_backend_port").then((port) => {
      if (port) {
        clearTimeout(timer);
        resolve(`http://127.0.0.1:${port}`);
      }
    }).catch(() => { /* command unavailable in dev */ });
  });
}
```

- A small Rust `#[tauri::command] get_backend_port()` returns the cached port for clients that attach after the initial event fires (avoids race where the frontend loads faster than it listens — but also avoids races where it loads slower).
- A single Zustand store slice holds the resolved `apiBase`; every `fetch` in the frontend reads from it.

## Contract properties

- **Idempotent**: the backend-ready event can be received by multiple listeners without side effects.
- **One-shot**: the handshake completes exactly once per app launch. Subsequent sidecar restarts (e.g., after crash recovery — future work) repeat the handshake.
- **Ordering**: `XLIGHT_BACKEND_PORT=` is the **first** line emitted to stdout by the backend. Any prior stderr is allowed.
- **Stability**: the exact line format and prefix `XLIGHT_BACKEND_PORT=` is stable. Future additions (e.g., version, capability flags) must use separate lines with distinct prefixes.

## Failure modes and handling

| Failure | Detection | Handling |
|---|---|---|
| Sidecar binary missing or not executable | `Command::spawn()` returns error | Rust shows an error dialog with the bundled binary path; no retry (indicates broken install). |
| Sidecar exits before printing port line | `CommandEvent::Terminated` received while state is `waiting_for_port` | Rust emits `backend-startup-failed` with the full captured stdout+stderr; frontend shows a diagnostic screen. |
| Port line never arrives (hang) | 30s timeout in Rust handshake loop | Same as above — forced shutdown, error UI. |
| Frontend attaches listener after event fired | Listener never resolves naturally | Frontend also calls `get_backend_port` command as a fallback (implemented in Rust from cached state). |
| Sidecar crashes after `ready` | `CommandEvent::Terminated` while state is `ready` | Rust emits `backend-lost`; frontend surfaces a "Backend crashed — restart app" banner. No auto-restart in v1. |

## Testing

- **Unit (Python)**: `tests/packaging/test_port_discovery.py` — spawn the bundled entrypoint as a subprocess (not the final sidecar, but the same code path), assert the port line appears on stdout before the Flask server accepts connections.
- **Unit (Rust)**: parser for the port line handles whitespace, carriage returns, multi-line stdout with log output interleaved before/after the port line.
- **Smoke (end-to-end)**: Playwright/tauri-driver test launches the built `.app`, waits for `backend-ready`, hits `/api/v1/library/songs`, asserts a 200.
