#!/usr/bin/env bash
# render_compare_mp4.sh — end-to-end iteration helper.
# Generate baseline + treatment .xsq, render to .fseq, render each .fseq
# to .mp4, then combine side-by-side for visual review.
#
# Assumes you're on a feature branch and main is the baseline. Switches
# branches twice (main → feature) so commit your work first.
#
# Usage:
#   scripts/render_compare_mp4.sh <song.mp3>
#
# Env overrides:
#   SHOW_DIR=/home/node/xlights
#   LAYOUT=$SHOW_DIR/xlights_rgbeffects.xml
#   NETWORKS=$SHOW_DIR/xlights_networks.xml
#   FEATURE_BRANCH=$(git branch --show-current)  # the treatment branch
#   BASELINE_BRANCH=main
#   CANVAS_W=960  CANVAS_H=540
set -euo pipefail

SONG="${1:?song mp3 path required}"
SHOW_DIR="${SHOW_DIR:-/home/node/xlights}"
LAYOUT="${LAYOUT:-$SHOW_DIR/xlights_rgbeffects.xml}"
NETWORKS="${NETWORKS:-$SHOW_DIR/xlights_networks.xml}"
FEATURE_BRANCH="${FEATURE_BRANCH:-$(git branch --show-current)}"
BASELINE_BRANCH="${BASELINE_BRANCH:-main}"
CANVAS_W="${CANVAS_W:-960}"
CANVAS_H="${CANVAS_H:-540}"
SLUG=$(basename "$SONG" .mp3)

# PR-number suffix for record-keeping. Caller can pass via PR_NUMBER env var,
# else we try to auto-detect from the current branch's open PR via gh CLI.
# Empty means no suffix — files are named without a PR tag.
PR_NUMBER="${PR_NUMBER:-}"
if [ -z "$PR_NUMBER" ] && command -v gh >/dev/null 2>&1; then
    PR_NUMBER=$(gh pr view "$FEATURE_BRANCH" --json number -q .number 2>/dev/null || true)
fi
if [ -n "$PR_NUMBER" ]; then
    PR_TAG="__pr${PR_NUMBER}"
else
    PR_TAG=""
fi

if [ -n "$(git status --porcelain | grep -v '^?? ')" ]; then
    echo "Error: working tree has uncommitted tracked changes. Commit or stash first." >&2
    exit 1
fi

render_branch() {
    local branch="$1" suffix="$2"
    echo
    echo "=== [$suffix] regenerate + render on '$branch' ==="
    git switch "$branch"
    ./scripts/render_song_for_review.sh "$SONG" "${suffix}${PR_TAG}"
    python3 -c "
from src.video.renderer import render_video
from pathlib import Path
render_video(
    fseq_path=Path('$SHOW_DIR/${SLUG}__${suffix}${PR_TAG}.fseq'),
    rgbeffects_path=Path('$LAYOUT'),
    networks_path=Path('$NETWORKS'),
    audio_path=Path('$SHOW_DIR/${SLUG}.mp3'),
    output_path=Path('$SHOW_DIR/${SLUG}__${suffix}${PR_TAG}.mp4'),
    canvas_w=$CANVAS_W, canvas_h=$CANVAS_H,
)
" 2>&1 | tail -3
}

render_branch "$BASELINE_BRANCH" "baseline"
render_branch "$FEATURE_BRANCH" "treatment"

echo
echo "=== combine side-by-side ==="
./scripts/sidebyside_mp4.sh \
    "$SHOW_DIR/${SLUG}__baseline${PR_TAG}.mp4" \
    "$SHOW_DIR/${SLUG}__treatment${PR_TAG}.mp4" \
    "$SHOW_DIR/${SLUG}__SBS${PR_TAG}.mp4"

echo
echo "Done. Compare side-by-side video at:"
echo "  $SHOW_DIR/${SLUG}__SBS${PR_TAG}.mp4"
if [ -n "$PR_NUMBER" ]; then
    echo "  (tagged for PR #${PR_NUMBER})"
fi
