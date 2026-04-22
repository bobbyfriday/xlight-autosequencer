#!/usr/bin/env bash
# T036 — build the PyInstaller backend onedir sidecar for a given arch.
#
# Usage: ./packaging/scripts/build-backend.sh <aarch64|x86_64>
#
# Produces: packaging/tauri/src-tauri/binaries/backend-<arch>-apple-darwin/
#   (Tauri's externalBin mechanism expects the binary naming suffix.)

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <aarch64|x86_64>" >&2
  exit 2
fi

ARCH="$1"
case "$ARCH" in
  aarch64|x86_64) ;;
  *)
    echo "error: unknown arch '$ARCH' — expected aarch64 or x86_64" >&2
    exit 2
    ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR=".build-venv-$ARCH"
WORK_DIR=".build-pyinstaller/$ARCH"
DIST_DIR="packaging/tauri/src-tauri/binaries"
TRIPLE="$ARCH-apple-darwin"

echo "→ Preparing venv at $VENV_DIR"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "→ Installing backend dependencies"
pip install --upgrade pip wheel setuptools
pip install -e ".[stems]"
pip install "pyinstaller>=6,<7"

# madmom, vamp are optional extras — try but don't fail the build if they
# refuse to install on this arch.
pip install "madmom>=0.16" || echo "warn: madmom install failed — beats-only analysis will be unavailable in the bundle"
pip install "vamp>=1.1" || echo "warn: vamp install failed — vamp plugins will be unavailable in the bundle"

mkdir -p "$DIST_DIR" "$WORK_DIR"

echo "→ Running PyInstaller (target-arch=$ARCH)"
pyinstaller packaging/pyinstaller/backend.spec \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
  --target-arch "$ARCH" \
  --clean --noconfirm

# PyInstaller onedir outputs `<distpath>/backend/`. Tauri expects a named
# executable at `binaries/backend-<triple>`, and the onedir's internal
# layout is preserved in the app bundle. Rename the folder.
if [[ -d "$DIST_DIR/backend-$TRIPLE" ]]; then
  rm -rf "$DIST_DIR/backend-$TRIPLE"
fi
mv "$DIST_DIR/backend" "$DIST_DIR/backend-$TRIPLE"

# The main executable inside onedir is also named `backend` — rename it
# so Tauri's sidecar resolution matches the target triple suffix.
mv "$DIST_DIR/backend-$TRIPLE/backend" "$DIST_DIR/backend-$TRIPLE/backend-$TRIPLE"

echo "→ Running self-test against bundled executable"
"$DIST_DIR/backend-$TRIPLE/backend-$TRIPLE" --self-test

echo "✓ Backend built: $DIST_DIR/backend-$TRIPLE/"
