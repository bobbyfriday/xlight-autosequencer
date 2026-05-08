#!/usr/bin/env bash
# sidebyside_mp4.sh — combine two FSEQ-rendered MP4s into a labeled side-by-side
# comparison MP4 for visual review.
#
# Usage:
#   scripts/sidebyside_mp4.sh <baseline.mp4> <treatment.mp4> [out.mp4]
#
# Outputs the side-by-side MP4 with text labels burned in (left = "BASELINE",
# right = "TREATMENT"). Audio comes from the LEFT (baseline) — both inputs
# should have the same source audio so they're frame-aligned.
set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <baseline.mp4> <treatment.mp4> [out.mp4]" >&2
    exit 2
fi

BASELINE="$1"
TREATMENT="$2"
OUT="${3:-${BASELINE%.mp4}__vs__$(basename "${TREATMENT%.mp4}").mp4}"

if [ ! -f "$BASELINE" ]; then
    echo "Not a file: $BASELINE" >&2
    exit 2
fi
if [ ! -f "$TREATMENT" ]; then
    echo "Not a file: $TREATMENT" >&2
    exit 2
fi

# hstack both video tracks; drawtext labels in top-left of each side.
# Audio from the left (baseline) — matches whichever .mp4 was first.
ffmpeg -y -hide_banner -loglevel warning \
    -i "$BASELINE" -i "$TREATMENT" \
    -filter_complex "
        [0:v]drawtext=text='BASELINE':x=20:y=20:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=8[left];
        [1:v]drawtext=text='TREATMENT':x=20:y=20:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=8[right];
        [left][right]hstack[v]
    " \
    -map "[v]" -map 0:a \
    -c:v libx264 -preset veryfast -crf 22 \
    -c:a aac -b:a 128k \
    "$OUT"

echo "Wrote: $OUT"
