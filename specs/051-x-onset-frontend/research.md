# Phase 0 Research: x-onset Frontend Redo

All items in the Technical Context are resolved. Each decision records rationale and the alternatives considered.

---

## 1. Framework selection

**Decision**: React 18 with TypeScript.

**Rationale**:
- The design handoff ships as 10 JSX files plus a single state hook (see [design_handoff_xonset/prototype/](../../design_handoff_xonset/prototype/)). Porting to React is strictly less code than porting to any other framework.
- Deep ecosystem for the specific demands of this UI: waveform (WaveSurfer.js bindings, react-audio-visualizer), drag-and-drop (react-dnd), virtualization for large libraries (react-virtuoso).
- Largest long-term hiring pool; every subsequent contributor will already know React.
- TypeScript is load-bearing — the state shape carries Section, Beat, Boundary, ParameterOverride; runtime-only typing has bitten the current vanilla-JS codebase multiple times.

**Alternatives considered**:
- **Svelte / SvelteKit** — elegant and compact, but would require re-authoring the entire handoff and we'd pay the ecosystem-thinness tax on audio libraries.
- **Solid** — compelling reactivity model, thinnest ecosystem of the three. Rejected for audio/timeline tooling scarcity.
- **Vanilla JS + Web Components** — matches current stack but the current stack is the problem. 21K lines of hand-rolled state + DOM manipulation already exists and is the reason for this feature.
- **Preact** — 95% of React with a fraction of the bundle. Rejected because the bundle-size win is ~30KB on a local-only app nobody loads from a CDN.

---

## 2. Build tooling

**Decision**: Vite 5+.

**Rationale**:
- Instant dev server start; HMR is fast enough that state survives component edits during development.
- Native TypeScript support, zero config.
- Trivial Flask integration: Vite dev server on `:5173` proxies `/api/*` to Flask on `:5000` during development; production build emits static files to `dist/` that Flask serves as static assets.
- Output is a single `index.html` plus code-split ES modules — ideal for a Flask-static-served app.

**Alternatives considered**:
- **Next.js / Remix** — both assume SSR / app-router features we don't need (no URLs, no SEO, no server components). Adds conceptual weight we never cash in.
- **Create React App** — unmaintained as of 2023.
- **esbuild / Parcel** — usable, but Vite has the richer plugin ecosystem and better DX for this use case.
- **Webpack** — slower DX, more config, no upside for greenfield.

---

## 3. State management

**Decision**: Zustand 4+.

**Rationale**:
- The handoff uses a single hook (`useAppStateImpl`) — Zustand is the minimal direct port: one store, `set`/`get`, no providers.
- First-class TypeScript; zero action/reducer boilerplate.
- Store slicing keeps domain areas (playback, library, assignments) separate while letting components select just what they need.
- Tiny bundle (~1KB).

**Alternatives considered**:
- **Redux Toolkit** — overkill for this scale; the boilerplate cost outweighs any debugging benefit.
- **Jotai** — atomic reactivity is nice for fine-grained updates but adds a new mental model (atoms-as-state) without payoff here.
- **useContext + useReducer** — would require provider trees for each domain slice; re-render behavior is less efficient than Zustand's selector-based subscriptions.
- **MobX / Valtio** — proxy-based reactivity is powerful but less TypeScript-ergonomic and a heavier mental model.

---

## 4. Styling

**Decision**: CSS Modules + design tokens exposed as CSS custom properties.

**Rationale**:
- The design handoff ships a token object (`PALETTE.dark`, `PALETTE.light`). The direct idiom is `:root { --bg0: #111114; ... }` and `[data-mode="light"] { --bg0: #f4f4ef; ... }`. Dark/light switch is then a single `data-mode` attribute on `<body>`.
- CSS Modules scope class names per component, preventing the global-selector bleed that the current stack suffers from.
- No runtime CSS-in-JS overhead, no vendored theming library, no CSS framework to fight.
- The design explicitly rejects rounded-SaaS idioms — so adopting a utility framework would cost more effort than writing correct CSS directly.

**Alternatives considered**:
- **Tailwind CSS** — every class in the design handoff is custom (4px grid, sharp corners, tabular numerals). Tailwind's opinions point the wrong direction; we'd write mostly `[...]` arbitrary values.
- **shadcn/ui / Radix + Tailwind** — assumes the "modern SaaS" design idiom the handoff explicitly rejects.
- **Styled-components / Emotion** — runtime CSS-in-JS pays a perf cost and duplicates what CSS custom properties already do natively for theming.
- **Vanilla Extract / Panda CSS** — compelling static-extraction models but adds a build step for no gain given CSS Modules already work with Vite out of the box.

---

## 5. Waveform rendering

**Decision**: Inline SVG with server-computed peaks.

**Rationale**:
- Backend pre-computes peak arrays once per song at analysis time, stored in the song's `_analysis.json`. The API returns `peaks: number[]` (length = rendered-width px).
- Rendering a waveform is then a single `<svg><path d="M0,0 ..."/></svg>` — zero JS dependency cost, reacts to CSS variables for color/theming, trivially unit-testable.
- Per-section tint overlays are just `<rect>` elements.
- Playhead is a `<line>` with `x` updated by RAF.

**Alternatives considered**:
- **WaveSurfer.js** — heavy (~150KB), loads audio on the client and re-computes peaks, non-trivial to style, brings its own interaction model that fights with ours.
- **Canvas 2D** — fastest for very long waveforms, but testing and accessibility are harder, and SVG is sufficient at our song lengths (3–5 min).
- **WebGL** — massively overkill; nothing about the visual complexity of a single waveform justifies a GPU pipeline.

---

## 6. Audio playback

**Decision**: A single HTMLAudioElement held in a ref, driven by a RAF loop that copies `audio.currentTime` into the Zustand store each frame.

**Rationale**:
- Matches exactly what the handoff does (see [design_handoff_xonset/prototype/state.jsx](../../design_handoff_xonset/prototype/state.jsx)).
- No Web Audio graph needed at v0 — we're not doing client-side analysis. The backend produces all metering and section data.
- The `<audio>` element handles codec decoding natively (MP3/WAV/FLAC/AIFF coverage comes free via the browser).
- Audio source URL is `/audio/<song_id>` served by Flask from the on-disk path.

**Alternatives considered**:
- **Web Audio API `AudioContext`** — needed only if we want client-side FFT, gain nodes, or mixing. Feature-creep for v0; can be added later without changing consumers.
- **Tone.js** — a toolkit for synthesis, not playback. Wrong layer.

---

## 7. Analysis progress transport

**Decision**: Server-Sent Events (SSE) from `GET /api/v1/songs/<id>/analyze/status`.

**Rationale**:
- One-way server→client push is exactly what progress events are.
- SSE is HTTP/1.1 with `text/event-stream`; works through any proxy; no websocket upgrade handshake.
- Trivial to fall back to polling if SSE breaks.
- Per-detector events stream as `data: {"detector": "beats", "status": "done", "conf": 0.93}\n\n`.

**Alternatives considered**:
- **WebSocket** — bi-directional, but we don't need client→server messages mid-analysis. Extra machinery for nothing.
- **Polling** — every 500ms of the 2–3 minute analysis would be ~500 round trips. Wasteful, and the progress feels laggier.
- **long-polling** — strictly worse than SSE for this use case.

---

## 8. Library persistence format

**Decision**: Two-layer JSON on disk under `~/.xlight/library/`.

Layout:
```
~/.xlight/library/
├── library.json                  # index: songs, folders, preferences, layout path
└── songs/
    └── <song_id>/
        └── session.json          # sections, assignments, parameter overrides for this song
```

**Rationale**:
- JSON is human-inspectable and diff-friendly (useful for debug + future "I lost my library" support).
- Two-layer split means a single song's edits don't rewrite the whole library file; safer against partial writes.
- Atomic writes via write-to-temp-then-rename, cheap enough for per-edit durability (FR-049a).
- Schema evolution is easier with JSON + a `schema_version` field than SQLite migrations at this scale.

**Alternatives considered**:
- **SQLite** — proper concurrency, smaller on-disk size at large library sizes, but a single-user app with < 200 songs doesn't benefit and it makes bundle export/import harder (need to `.dump`).
- **IndexedDB** — only works when the browser is the source of truth. Would leak state into the browser profile (lost on browser reset); we need it server-side so the Python side can read it.
- **One giant JSON file** — every edit rewrites the whole file; on a 100-song library that's wasteful and increases crash-window risk.

---

## 9. Audio delivery to the browser

**Decision**: `GET /audio/<song_id>` streams audio bytes from the on-disk source path with `Accept-Ranges: bytes` support.

**Rationale**:
- Audio source files already live on the user's disk; re-uploading for each play session would double disk usage.
- Range support gives the browser native seek behavior — the `<audio>` element requests specific byte ranges on seek.
- If the source path is missing, endpoint returns 404 with a body including `{"error": {"code": "source_file_missing"}}` — the frontend surfaces this as the "locate file" state (FR-001a, edge case "MP3 moved or deleted after import").

**Alternatives considered**:
- **Serve via absolute path URL** — requires the browser to have filesystem access; not portable; fails behind CORS.
- **Upload audio to the Flask server on import** — doubles disk usage, breaks the offline-from-day-one mental model where audio lives where the user put it.
- **Client-side `File` handle via File System Access API** — not in Firefox, behind a permission prompt, and wouldn't survive app restart.

---

## 10. Re-analysis section-mapping algorithm

**Decision**: Maximum time overlap with a fallback to orphan handling.

Per FR-013a, when re-analysis produces a new section list, map each new section to the old section it overlaps with the most (intersection duration / new section duration ≥ 0.3 threshold). Old sections with no matching new section are orphans (their assignments are "dropped" in the review dialog); new sections with no matching old section need themes (the analyzer-suggested default-theme applies).

**Rationale**:
- Handles the common case (a boundary shifted 200ms) cleanly — the new section is >99% overlap with the old.
- Handles structural changes honestly — if the analyzer now splits a section in two, both halves map to the old section's theme, which is the intent of the split FR (FR-021).
- Threshold of 0.3 prevents spurious matches when a new section is mostly new content (e.g., the chorus moved earlier into what was previously verse territory).

**Alternatives considered**:
- **Nearest-boundary matching** — failed the "split produces two sections from one" case.
- **Kind-based matching** — relies on the analyzer's `kind` field being stable, which it isn't across versions.
- **Always wipe on re-analysis** — already rejected in clarify session 1 (Option A rejected; Option B picked).

---

## 11. Keyboard shortcut architecture

**Decision**: Single global keydown listener on `document`, routed through a Zustand `keyboard` store slice that maps key combos to actions. Shortcuts suspend when a text input is focused.

**Rationale**:
- The handoff specifies 10+ shortcuts across screens and modes (FR-041, FR-042). A central registry makes "what's bound, where?" answerable in one file.
- Suspend-on-input is universally expected UX — typing in a section-rename field shouldn't trigger the `R` shortcut.
- Screen-scoped shortcuts (e.g., `S` only in sections edit mode) are controlled by the active screen registering/unregistering.

**Alternatives considered**:
- **react-hotkeys / react-hotkeys-hook** — fine libraries, but for a dozen bindings the direct approach is less code than configuring their hierarchy.
- **Per-component `onKeyDown`** — scatters the binding map across the codebase; conflicts become invisible.

---

## 12. Library export / import bundle format

**Decision**: A `.xonset-bundle` zip containing a single `library.json` (index, same schema as on-disk) and a `songs/` directory mirroring the per-song `session.json` files. No audio.

**Rationale**:
- A zip is one file the user can email, copy, or back up.
- The inner layout mirrors the on-disk layout so import is a simple unpack + merge.
- Schema-versioned for forward compatibility.
- Import offers merge (keep existing + add new) or replace (wipe existing); user chooses in the UI before committing.

**Alternatives considered**:
- **Plain folder** — forces the user to manage a tree; less portable than a single file.
- **SQLite file** — opaque to the user and harder to diff or hand-repair.
- **Include audio in the bundle** — breaks the "audio stays on user's disk" model and produces multi-hundred-megabyte bundles.

---

## 13. Test strategy

**Decision**: Three layers, test-first per constitution principle IV.

- **Pytest for the Python API** — one test module per contract file. Flask test client; hermetic temp library dir per test.
- **Vitest + React Testing Library for frontend** — store slices tested as pure functions; components tested with minimal DOM; tests co-located under `src/review/frontend/tests/`.
- **Playwright for one end-to-end happy-path** — US1 chain (drop → analyze → timeline → theme → export) against a running Flask + Vite dev server. One spec, because full e2e coverage is expensive and redundant with the lower-layer tests.

**Rationale**: Each layer catches what the others miss. Unit tests are fast and can TDD the design; integration-level Python tests catch JSON schema drift between frontend and backend; one e2e test catches wiring bugs that neither layer would see.

**Alternatives considered**:
- **Cypress** instead of Playwright — both viable; Playwright has better multi-browser support and the newer API.
- **Storybook** — useful for component development, but adds a parallel environment to maintain. Defer to a future polish phase if needed.
- **No frontend tests** — rejected on principle IV (Test-First Development).

---

## 14. Packaging & distribution

**Decision**: Commit built `dist/` assets to git; ship via `pip install -e .`. Add `xlight review` as a new console-script entry in `pyproject.toml` that boots Flask and opens the browser.

**Rationale**:
- Hobbyist audience must not need Node installed to run the app.
- Rebuilding `dist/` is an explicit step before each release (documented in quickstart).
- Single install path — `pip install` — matches every other user-facing command already in this repo (`xlight-analyze`, `xlight-evaluate`).

**Alternatives considered**:
- **Build at install time via a setuptools hook** — requires Node at install time; raises the onboarding bar for non-engineers.
- **Publish the frontend as an npm package** — solves a problem nobody has; this UI is not consumed by anything outside this repo.
- **Electron / Tauri wrap** — explicitly out of scope for v0 per assumption "Web-first, desktop-shell optional later." Revisit when the first hobbyist asks for a double-click installer.

---

## 15. Accessibility and keyboard-first operation

**Decision**: Keyboard-first path is binding (SC-006); basic WCAG 2.1 AA color contrast is required; screen-reader full parity is explicitly out of scope for v0.

**Rationale**:
- The hobbyist audience overwhelmingly operates by keyboard and sighted eye — SC-006 already commits to keyboard-only operation for US1. Color contrast compliance is free to check against the design tokens and blocks zero work.
- Full screen-reader support for a DAW-style UI (waveform, live light previews, section drag) is a significant body of work with uncertain demand in this audience. Defer; do not block v0 on it.
- Light mode exists (FR-043) for bright-environment use, which is an accessibility consideration even outside WCAG.

**Alternatives considered**:
- **WCAG AAA compliance** — unrealistic for a DAW-style interface on v0.
- **Zero accessibility concern** — violates even basic professional quality.
