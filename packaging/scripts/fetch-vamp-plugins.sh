#!/usr/bin/env bash
# T037 — obtain and lay out Vamp plugin .dylib files for macOS.
#
# This is a bootstrap helper: most Vamp plugin packs don't ship with
# stable download URLs, so a fully automated fetch isn't possible. The
# script verifies each expected .dylib is present and prints clear
# instructions for any that are missing. Run once per supported arch.
#
# Usage: ./packaging/scripts/fetch-vamp-plugins.sh <aarch64|x86_64>

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <aarch64|x86_64>" >&2
  exit 2
fi

ARCH="$1"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$REPO_ROOT/packaging/pyinstaller/plugins/vamp/$ARCH"
mkdir -p "$OUT"

# Expected plugin packs. `.dylib` suffix is the canonical macOS Vamp
# plugin extension. Names match what Python code requests via
# `vamp.load_plugin()` (see src/analyzer/algorithms/vamp_*.py).
#
# Format per entry: "<filename>|<source-url>"
# (Plain array instead of associative array so this runs on macOS's
# stock bash 3.2 — `declare -A` needs bash 4+.)
EXPECTED=(
  "qm-vamp-plugins.dylib|https://code.soundsoftware.ac.uk/projects/qm-vamp-plugins/"
  "beatroot-vamp.dylib|https://code.soundsoftware.ac.uk/projects/beatroot-vamp"
  "pyin.dylib|https://code.soundsoftware.ac.uk/projects/pyin"
  "nnls-chroma.dylib|https://code.soundsoftware.ac.uk/projects/nnls-chroma"
  "silvet.dylib|https://code.soundsoftware.ac.uk/projects/silvet"
)

MISSING=0
for entry in "${EXPECTED[@]}"; do
  name="${entry%%|*}"
  source_url="${entry##*|}"
  if [[ ! -f "$OUT/$name" ]]; then
    echo "✗ missing: $OUT/$name"
    echo "    source: $source_url"
    MISSING=1
  else
    echo "✓ present: $OUT/$name"
  fi
done

if (( MISSING )); then
  echo ""
  echo "Action required: download the missing plugin packs from the URLs"
  echo "listed above, unzip, and copy the $ARCH .dylib into:"
  echo "    $OUT/"
  echo ""
  echo "After placing the files, re-run this script to confirm all packs"
  echo "are present. Record SHA256 of each .dylib in packaging/README.md."
  exit 1
fi

echo ""
echo "✓ All Vamp plugins present for $ARCH."
