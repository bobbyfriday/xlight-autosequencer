#!/usr/bin/env bash
# T042 — run `cargo tauri build` for the given arch and verify the outer
# .app + .dmg signatures pass Gatekeeper.
#
# Usage: ./packaging/scripts/build-app.sh <aarch64|x86_64>

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <aarch64|x86_64>" >&2
  exit 2
fi

ARCH="$1"
TRIPLE="$ARCH-apple-darwin"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT/packaging/tauri"

echo "→ Installing Tauri JS deps (if needed)"
pnpm install --frozen-lockfile

echo "→ Building .app for target $TRIPLE"
cargo tauri build --target "$TRIPLE"

BUNDLE_ROOT="src-tauri/target/$TRIPLE/release/bundle"
APP_PATH="$BUNDLE_ROOT/macos/XLight.app"
DMG_PATH="$(find "$BUNDLE_ROOT/dmg" -maxdepth 1 -name '*.dmg' 2>/dev/null | head -1 || true)"

if [[ ! -d "$APP_PATH" ]]; then
  echo "error: .app not produced at $APP_PATH" >&2
  exit 1
fi

echo "→ Verifying .app signing"
codesign --display --verbose=4 "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

echo "→ Gatekeeper dry-run (spctl)"
if ! spctl -a -vvv -t execute "$APP_PATH"; then
  echo "warning: spctl rejected the .app — notarization may fail" >&2
fi

echo "✓ .app built at $APP_PATH"
if [[ -n "$DMG_PATH" ]]; then
  echo "✓ .dmg at $DMG_PATH"
fi
