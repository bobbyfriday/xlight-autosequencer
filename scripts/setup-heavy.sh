#!/usr/bin/env bash
# On-demand heavy-stack installer for Claude Code on the web.
#
# The SessionStart hook (.claude/hooks/session-start.sh) installs only the
# light stack — enough for the Python tests, the CLI, and the fast
# `xlight-evaluate microscope` metrics loop. The two heavy stacks below are
# slow and large, so they are pulled on demand instead of on every session.
#
#   render    Visual-render loop deps: Xvfb + software-GL stack, ffmpeg, the
#             video MP4 extra, the xLights AppImage (~98 MB), and the CC0
#             corpus. Enables `tools/render_panel` (generate -> headless
#             xLights -> MP4 -> contact sheet).
#
#   analyzer  Full analysis sidecar (vamp plugins + madmom + demucs in
#             .venv-vamp). Delegates to scripts/install.sh, the canonical
#             installer. Needed for real section detection so the generator
#             produces *lit* sequences from a bare MP3 (vs. an empty one).
#
#   all       Both of the above.
#
# Usage: scripts/setup-heavy.sh [render|analyzer|all]   (default: render)
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "\n${YELLOW}▶ $*${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $*"; }
fail() { echo -e "  ${RED}✗${NC} $*"; }

# apt install that tolerates the blocked third-party PPAs (deadsnakes,
# ondrej/php) which 403 on `apt-get update`. Install off cached lists first;
# only if that fails do we drop the bad PPAs and update.
apt_install() {
  if sudo apt-get install -y -qq "$@" 2>/dev/null; then
    return 0
  fi
  sudo rm -f /etc/apt/sources.list.d/deadsnakes*.list \
             /etc/apt/sources.list.d/ondrej*.list 2>/dev/null || true
  sudo apt-get update -qq 2>/dev/null || true
  sudo apt-get install -y -qq "$@"
}

setup_render() {
  step "Render-loop system deps (Xvfb + software GL + ffmpeg)"
  if apt_install xvfb ffmpeg libgl1 libosmesa6 libgtk-3-0 libsdl2-2.0-0 \
                 libwebkit2gtk-4.1-0 libegl1 libgles2 squashfs-tools; then
    ok "system deps installed"
  else
    fail "apt install failed — render loop will not work"
    return 1
  fi

  step "Video MP4 extra (scipy + zstandard)"
  python3 -m pip install --quiet -e ".[video]" && ok "video extra installed" \
    || warn "video extra install failed"

  step "xLights AppImage (~98 MB, cached under tools/render/)"
  if python3 -m tools.render_panel.run setup; then
    ok "xLights ready"
  else
    fail "xLights setup failed"
  fi

  step "CC0 corpus (gitignored MP3s for the standing panel)"
  python3 -m tests.validation.download_fixtures && ok "CC0 songs ready" \
    || warn "corpus download failed"

  echo ""
  ok "Render loop ready. Run the standing panel with:"
  echo "    python3 -m tools.render_panel.run panel \\"
  echo "        --manifest tests/fixtures/render_panel/manifest.json"
  echo "  Output: render-out/panel_contact_sheet.jpg"
}

setup_analyzer() {
  step "Full analysis sidecar (delegating to scripts/install.sh)"
  if [ -x scripts/install.sh ]; then
    ./scripts/install.sh
  else
    fail "scripts/install.sh not found or not executable"
    return 1
  fi
}

TARGET="${1:-render}"
case "$TARGET" in
  render)   setup_render ;;
  analyzer) setup_analyzer ;;
  all)      setup_render; setup_analyzer ;;
  *)
    echo "Usage: scripts/setup-heavy.sh [render|analyzer|all]" >&2
    exit 2
    ;;
esac
