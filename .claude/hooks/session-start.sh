#!/bin/bash
# SessionStart hook — light bootstrap for Claude Code on the web.
#
# Brings a fresh, bare web container to the point where the Python test suite,
# the CLI entry points, and the fast generator/microscope iteration loop all
# run, without any manual setup. The heavy analyzer + visual-render stacks are
# NOT installed here — pull those on demand with `scripts/setup-heavy.sh`.
#
# Encodes three traps that bite a bare container (see docs/web-iteration.md):
#   1. Debian ships `blinker` with no RECORD file, so `pip install -e .`
#      aborts trying to uninstall it. Force-replace it first.
#   2. `apt-get update` 403s on two blocked third-party PPAs, but
#      `apt-get install` works off the cached package lists.
#   3. A uv-isolated `pytest` shadows the project's on PATH — always invoke
#      tests as `python3 -m pytest`.
#
# Idempotent and non-interactive. Never blocks session start: every step is
# best-effort and the script always exits 0, printing a status summary so a
# partial environment is visible rather than fatal.
set -uo pipefail

# Only run in the remote (web) environment. Local dev uses scripts/install.sh.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

log() { echo "[session-start] $*"; }
ffmpeg_ok=skip; pip_ok=skip; frontend_ok=skip

# ── 1. ffmpeg (MP3 loading; required by audio import + stem cache) ───────────
if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg_ok=present
else
  log "installing ffmpeg..."
  if sudo apt-get install -y -qq ffmpeg >/tmp/session-start-apt.log 2>&1; then
    ffmpeg_ok=installed
  else
    # Drop the blocked PPAs that make `apt-get update` 403, then retry.
    sudo rm -f /etc/apt/sources.list.d/deadsnakes*.list \
               /etc/apt/sources.list.d/ondrej*.list 2>/dev/null || true
    if sudo apt-get update -qq >>/tmp/session-start-apt.log 2>&1 \
       && sudo apt-get install -y -qq ffmpeg >>/tmp/session-start-apt.log 2>&1; then
      ffmpeg_ok=installed
    else
      ffmpeg_ok=FAILED
    fi
  fi
fi

# ── 2. Python package + dev/test extras ──────────────────────────────────────
# Force-replace the Debian blinker (no RECORD) so the editable install can
# resolve Flask's dependency tree.
python3 -m pip install --quiet --ignore-installed blinker >/tmp/session-start-pip.log 2>&1 || true
log "installing python package + dev/ui-test extras..."
if python3 -m pip install --quiet -e ".[dev,ui-tests]" >>/tmp/session-start-pip.log 2>&1; then
  pip_ok=installed
else
  pip_ok=FAILED
  log "pip install failed — see /tmp/session-start-pip.log"
  tail -5 /tmp/session-start-pip.log || true
fi

# ── 3. Frontend bundle (Flask serves dist/; UI tests need it present) ────────
FRONTEND_DIR="src/review/frontend"
if [ -d "$FRONTEND_DIR" ] && command -v npm >/dev/null 2>&1; then
  if [ -d "$FRONTEND_DIR/dist" ]; then
    frontend_ok=present
  else
    log "building frontend bundle (npm install + build)..."
    if ( cd "$FRONTEND_DIR" && npm install --silent && npm run build --silent ) \
         >/tmp/session-start-npm.log 2>&1; then
      frontend_ok=built
    else
      frontend_ok=FAILED
      log "frontend build failed (non-fatal) — see /tmp/session-start-npm.log"
    fi
  fi
fi

log "bootstrap done — ffmpeg=$ffmpeg_ok python=$pip_ok frontend=$frontend_ok"
log "run tests with: python3 -m pytest tests/ -m 'not ui and not content and not slow'"
log "heavy stacks (analyzer / visual render) on demand: scripts/setup-heavy.sh"
exit 0
