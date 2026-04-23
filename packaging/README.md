# XLight packaging — macOS build handbook

This directory contains everything required to build, sign, notarize, and ship
the XLight desktop app on macOS.

> **Start here**: [../specs/052-tauri-desktop-packaging/quickstart.md](../specs/052-tauri-desktop-packaging/quickstart.md)
> — the full release-engineer walkthrough from prerequisites through notarization.

## Layout

| Path | Purpose |
|---|---|
| `tauri/` | Tauri 2 native shell (Rust + minimal JS). Wraps the React frontend in a WKWebView window and spawns the Python sidecar. |
| `tauri/src-tauri/Cargo.toml` | Rust dependencies. |
| `tauri/src-tauri/src/main.rs` | Shell entry: spawn sidecar, discover backend port, emit to webview, clean shutdown. |
| `tauri/src-tauri/tauri.conf.json` | Bundle identity, signing, icons, resources, sidecar binding. |
| `tauri/src-tauri/entitlements.plist` | Hardened-runtime entitlements (library-validation disabled for Vamp, JIT allowed for torch/numba). |
| `tauri/src-tauri/capabilities/main.json` | Tauri 2 permission capabilities (shell, dialog, event, narrow fs). |
| `pyinstaller/backend.spec` | PyInstaller onedir spec for the Flask backend. |
| `pyinstaller/hooks/` | Hidden imports + data collection for madmom, torch, librosa, demucs. |
| `pyinstaller/plugins/vamp/<arch>/` | Vamp plugin `.dylib` files bundled per architecture. |
| `scripts/build-backend.sh` | PyInstaller build entry (per arch). |
| `scripts/sign-backend.sh` | Iterates the onedir and signs every binary. |
| `scripts/build-app.sh` | Runs `cargo tauri build` and verifies signing. |
| `scripts/notarize.sh` | Submits the `.dmg` to `notarytool` and staples the ticket. |
| `scripts/release.sh` | Orchestrates all of the above end-to-end. |
| `scripts/fetch-vamp-plugins.sh` | Source/copy `.dylib`s for QM, BeatRoot, pYIN, Chordino/NNLS, Silvet. |

## Per-release checklist

See [quickstart.md](../specs/052-tauri-desktop-packaging/quickstart.md). In
brief:

```bash
export XLIGHT_TARGET_ARCH=aarch64   # or x86_64
./packaging/scripts/release.sh $XLIGHT_TARGET_ARCH
```

Produces a signed, notarized, stapled `.dmg` in
`packaging/tauri/src-tauri/target/$XLIGHT_TARGET_ARCH-apple-darwin/release/bundle/dmg/`.

## Dev vs packaged mode

The backend reads `XLIGHT_PACKAGED=1` to decide whether it's running inside the
bundle. Dev mode (`python -m src.review.cli` + `pnpm dev`) never sets it, so:

- Stem cache stays next to source audio (as today).
- `VAMP_PATH` is not overridden (uses the user's local plugin install).
- `TORCH_HOME` is not overridden (uses the user's default torch cache).

Packaged mode sets all three from the Rust launcher. See
`src/packaging/bundled_mode.py` for the detection helper.

## Vamp plugin source pinning

| Pack | Version | Upstream | Notes |
|---|---|---|---|
| QM Vamp Plugins | TBD | https://code.soundsoftware.ac.uk/projects/qm-vamp-plugins/ | Builds for macOS arm64 + x86_64. |
| BeatRoot | TBD | https://code.soundsoftware.ac.uk/projects/beatroot-vamp | |
| pYIN | TBD | https://code.soundsoftware.ac.uk/projects/pyin | |
| NNLS Chroma / Chordino | TBD | https://code.soundsoftware.ac.uk/projects/nnls-chroma | |
| Silvet | TBD | https://code.soundsoftware.ac.uk/projects/silvet | |

Record the exact version (or git SHA) and SHA256 of each `.dylib` after the
first successful release.

## FR-008 scope note

Partial-write safety for `~/.xlight/library.json` and the analysis cache
inherits existing dev-mode behavior — not hardened by this feature. If a
future incident shows corruption on forced shutdown, open a separate spec
for atomic-write (write-to-temp + `os.replace`). This feature's FR-008
scope is limited to clean process shutdown (signal handling in the Tauri
shell).
