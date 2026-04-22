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

# Require Python 3.11 specifically.
#   - madmom has no wheels for 3.12+ and its source build against 3.12/3.13
#     is unreliable.
#   - torch wheels for 3.14 (released Oct 2025) were still sparse at release
#     time of this script.
# Override with PY311=/path/to/python3.11 if your installation is elsewhere.
PY311="${PY311:-python3.11}"
if ! command -v "$PY311" >/dev/null 2>&1; then
  echo "error: python3.11 not found on PATH." >&2
  echo "       Install via:  brew install python@3.11" >&2
  echo "       Or set PY311=/full/path/to/python3.11 and re-run." >&2
  exit 2
fi
PY311_VERSION="$("$PY311" --version 2>&1)"
case "$PY311_VERSION" in
  "Python 3.11."*) ;;
  *)
    echo "error: $PY311 reports '$PY311_VERSION' — expected Python 3.11.x" >&2
    exit 2
    ;;
esac
echo "→ Using $PY311 ($PY311_VERSION)"

echo "→ Preparing venv at $VENV_DIR"
"$PY311" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "→ Installing backend dependencies"
pip install --upgrade pip wheel setuptools
pip install -e ".[stems]"
pip install "pyinstaller>=6,<7"

# madmom builds Cython extensions at install time and imports Cython
# directly in its setup.py — the implicit PEP 517 isolated build env
# doesn't include Cython/numpy unless we pre-install them outside it
# (or add them to madmom's declared build deps, which we don't own).
pip install --upgrade "cython>=3" "numpy<2"

# madmom, vamp are optional — try but don't fail the build if they
# refuse to install on this arch.
pip install "madmom>=0.16" --no-build-isolation || \
  echo "warn: madmom install failed — beats-only analysis will be unavailable in the bundle"
pip install "vamp>=1.1" || \
  echo "warn: vamp install failed — vamp plugins will be unavailable in the bundle"

mkdir -p "$DIST_DIR" "$WORK_DIR"

# --target-arch is only valid with PyInstaller's CLI when invoked against
# a script, not a .spec. The spec owns architecture selection. For host-
# arch builds (which this is) we let PyInstaller default to host. For a
# cross-arch build (e.g. x86_64 on an arm64 Mac), run this script under
# `arch -x86_64` with an x86_64 python3.11 installed, and set the venv
# via PY311=/path/to/x86_64-python3.11.
echo "→ Running PyInstaller (host-arch build targeting $ARCH)"
pyinstaller packaging/pyinstaller/backend.spec \
  --distpath "$DIST_DIR" \
  --workpath "$WORK_DIR" \
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
