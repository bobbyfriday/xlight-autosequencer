#!/usr/bin/env bash
# T044 + T045 — orchestrate a full release for one architecture:
#   1. Build frontend (Vite)
#   2. Build backend (PyInstaller)
#   3. Sign backend binaries
#   4. Generate packaging-manifest.json
#   5. Build .app / .dmg (cargo tauri build)
#   6. Notarize + staple
#
# Usage: ./packaging/scripts/release.sh <aarch64|x86_64>
#
# Required env vars:
#   SIGNING_IDENTITY   "Developer ID Application: Name (TEAMID)"
#   NOTARY_PROFILE     (optional, defaults to "XLIGHT_NOTARY")

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <aarch64|x86_64>" >&2
  exit 2
fi

ARCH="$1"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ "${SIGNING_IDENTITY:-}" == "" ]]; then
  echo "error: SIGNING_IDENTITY must be set" >&2
  exit 2
fi

echo "══ XLight release: $ARCH ══"

echo "[1/6] Building frontend"
(cd src/review/frontend && pnpm install --frozen-lockfile && pnpm run build)

echo "[2/6] Building backend sidecar"
./packaging/scripts/build-backend.sh "$ARCH"

echo "[3/6] Signing backend"
./packaging/scripts/sign-backend.sh "$ARCH"

echo "[4/6] Generating packaging-manifest.json"
APP_VERSION="$(grep -E '^version\s*=' pyproject.toml | head -1 | sed -E 's/.*"([^"]+)".*/\1/')"
BUILD_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FRONTEND_COMMIT="$(git log -n1 --format=%H -- src/review/frontend/)"
BACKEND_COMMIT="$(git log -n1 --format=%H -- src/)"
cat > packaging/tauri/src-tauri/packaging-manifest.json <<EOF
{
  "app_version": "$APP_VERSION",
  "build_timestamp": "$BUILD_TS",
  "target_arch": "$ARCH",
  "frontend_commit": "$FRONTEND_COMMIT",
  "backend_commit": "$BACKEND_COMMIT",
  "bundled_vamp_plugins": [
    "qm-vamp-plugins",
    "beatroot-vamp",
    "pyin",
    "nnls-chroma",
    "silvet"
  ],
  "download_model_manifest_url": "src/packaging/model_manifest.json"
}
EOF

echo "[5/6] Building .app and .dmg"
./packaging/scripts/build-app.sh "$ARCH"

echo "[6/6] Notarizing"
./packaging/scripts/notarize.sh "$ARCH"

TRIPLE="$ARCH-apple-darwin"
DMG="$(find "packaging/tauri/src-tauri/target/$TRIPLE/release/bundle/dmg" -maxdepth 1 -name '*.dmg' | head -1 || true)"
echo
echo "══ Release complete: $DMG"
