#!/usr/bin/env bash
# Start the xlight-analyze review UI (upload + analysis + story pipeline).
# Performs a full dependency pre-flight check before launching the server.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Colour helpers ─────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
fail() { echo -e "  ${RED}✗${NC} $*"; PREFLIGHT_FAILED=1; }

# ── Load .env (sets VAMP_PATH etc.) ───────────────────────────────────────────
if [[ -f "$REPO_ROOT/.env" ]]; then
  # shellcheck source=/dev/null
  source "$REPO_ROOT/.env"
fi

# Fallback: probe standard Vamp plugin directories
if [[ -z "${VAMP_PATH:-}" ]]; then
  for d in "/usr/local/lib/vamp" "$HOME/Library/Audio/Plug-Ins/Vamp" "/usr/lib/vamp"; do
    if [[ -d "$d" ]]; then
      export VAMP_PATH="$d"
      break
    fi
  done
fi

# ── Activate virtualenv ────────────────────────────────────────────────────────
if [[ -z "${VIRTUAL_ENV:-}" && -f "$REPO_ROOT/venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$REPO_ROOT/venv/bin/activate"
fi

# ── Ensure editable install matches checked-out code ──────────────────────────
# Clear stale bytecache and re-install so branch switches take effect immediately
find "$REPO_ROOT/src" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
pip install --quiet --no-deps -e "$REPO_ROOT" 2>/dev/null || true

# ── Pre-flight checks ──────────────────────────────────────────────────────────
echo ""
echo "Pre-flight checks"
echo "-----------------"
PREFLIGHT_FAILED=0

# 1. Python CLI entry point
if command -v xlight-analyze &>/dev/null; then
  ok "xlight-analyze CLI"
else
  fail "xlight-analyze not found (run: pip install -e .)"
fi

# 2. ffmpeg
if command -v ffmpeg &>/dev/null; then
  ok "ffmpeg"
else
  fail "ffmpeg not found (macOS: brew install ffmpeg  |  Linux: apt install ffmpeg)"
fi

# 3. Python capabilities (vamp Python binding, madmom, demucs)
# vamp/madmom/demucs are installed in .venv-vamp, not the main venv — check there.
VAMP_PYTHON="$REPO_ROOT/.venv-vamp/bin/python"
CAPS_JSON=$("$VAMP_PYTHON" -c "
import sys, os, json
os.environ['VAMP_PATH'] = '${VAMP_PATH:-}'
sys.path.insert(0, '$REPO_ROOT')
from src.analyzer.capabilities import detect_capabilities
print(json.dumps(detect_capabilities()))
" 2>/dev/null || echo '{}')

check_cap() {
  local key="$1" label="$2"
  if echo "$CAPS_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('$key') else 1)" 2>/dev/null; then
    ok "$label"
  else
    fail "$label (run ./scripts/install.sh)"
  fi
}

check_cap_optional() {
  local key="$1" label="$2"
  if echo "$CAPS_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('$key') else 1)" 2>/dev/null; then
    ok "$label"
  else
    warn "$label not available (run ./scripts/install.sh to enable)"
  fi
}

check_cap vamp    "vamp Python binding"
check_cap madmom  "madmom beat tracking"
check_cap demucs  "Demucs stem separation"
check_cap_optional whisperx "WhisperX lyric alignment"
check_cap_optional genius   "Genius API lyrics"

# 4. Required Vamp plugin libraries
if [[ -z "${VAMP_PATH:-}" ]]; then
  fail "VAMP_PATH not set — Vamp plugins cannot be located"
else
  LIB_EXT="so"
  [[ "$(uname -s)" == "Darwin" ]] && LIB_EXT="dylib"

  REQUIRED_PLUGINS=(
    "segmentino:segmentino (L1 song structure)"
    "qm-vamp-plugins:QM Vamp plugins (bars, beats, key, onsets)"
    "bbc-vamp-plugins:BBC Vamp plugins (energy curves)"
    "beatroot-vamp:BeatRoot (beat tracking)"
    "pyin:pYIN (pitch / note events)"
    "nnls-chroma:NNLS Chroma / Chordino (harmony)"
    "vamp-aubio|vamp-aubio-plugins:Vamp Aubio (onset detection)"
  )

  for entry in "${REQUIRED_PLUGINS[@]}"; do
    libs="${entry%%:*}"   # may be "name|alias"
    label="${entry#*:}"
    found=0
    for lib in $(echo "$libs" | tr '|' ' '); do
      [[ -f "$VAMP_PATH/${lib}.${LIB_EXT}" ]] && found=1 && break
    done
    if [[ $found -eq 1 ]]; then
      ok "$label"
    else
      fail "$label — missing from $VAMP_PATH (run ./scripts/install.sh)"
    fi
  done
fi

# 5. .venv-vamp (subprocess environment for Vamp/madmom algorithms)
VAMP_PYTHON="$REPO_ROOT/.venv-vamp/bin/python"
if [[ -f "$VAMP_PYTHON" ]]; then
  if "$VAMP_PYTHON" -c "import vamp, madmom" &>/dev/null 2>&1; then
    ok ".venv-vamp (vamp + madmom subprocess environment)"
  else
    fail ".venv-vamp exists but vamp/madmom not importable (run ./scripts/install.sh)"
  fi
else
  fail ".venv-vamp not found (run ./scripts/install.sh)"
fi

echo ""

# ── Abort if anything failed ───────────────────────────────────────────────────
if [[ "$PREFLIGHT_FAILED" -ne 0 ]]; then
  echo -e "${RED}Pre-flight failed. Fix the issues above, then re-run:${NC}"
  echo ""
  echo "  ./scripts/install.sh"
  echo ""
  exit 1
fi

echo -e "${GREEN}All checks passed.${NC}"
echo ""
echo "Starting xlight-analyze review UI at http://127.0.0.1:5173/"
echo "Press Ctrl-C to stop."
exec xlight-analyze review
