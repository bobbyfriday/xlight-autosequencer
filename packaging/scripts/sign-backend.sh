#!/usr/bin/env bash
# T041 — iterate the onedir bundle and sign every .dylib / .so / main
# executable with the Developer ID identity stored in $SIGNING_IDENTITY.
#
# Usage: ./packaging/scripts/sign-backend.sh <aarch64|x86_64>
#
# Environment:
#   SIGNING_IDENTITY  e.g. "Developer ID Application: Name (TEAMID)"

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <aarch64|x86_64>" >&2
  exit 2
fi

ARCH="$1"
TRIPLE="$ARCH-apple-darwin"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ONEDIR="$REPO_ROOT/packaging/tauri/src-tauri/binaries/backend-$TRIPLE"
ENTITLEMENTS="$REPO_ROOT/packaging/tauri/src-tauri/entitlements.plist"

if [[ -z "${SIGNING_IDENTITY:-}" ]]; then
  echo "error: SIGNING_IDENTITY must be set" >&2
  echo "  example: export SIGNING_IDENTITY=\"Developer ID Application: You (TEAMID)\"" >&2
  exit 2
fi

if [[ ! -d "$ONEDIR" ]]; then
  echo "error: onedir not found at $ONEDIR — run build-backend.sh first" >&2
  exit 2
fi

echo "→ Signing every .dylib / .so under $ONEDIR (bottom-up)"
# Bottom-up ordering: deepest files first so nested dylibs are signed
# before anything that embeds them.
find "$ONEDIR" \( -name "*.dylib" -o -name "*.so" \) -print0 |
  while IFS= read -r -d '' binary; do
    codesign --force --options runtime \
      --entitlements "$ENTITLEMENTS" \
      --sign "$SIGNING_IDENTITY" \
      "$binary"
  done

echo "→ Signing main executable"
codesign --force --options runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$SIGNING_IDENTITY" \
  "$ONEDIR/backend-$TRIPLE"

echo "→ Verifying"
codesign --verify --deep --strict --verbose=2 "$ONEDIR"

echo "✓ Backend onedir signed and verified."
