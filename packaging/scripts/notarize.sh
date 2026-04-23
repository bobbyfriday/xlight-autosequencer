#!/usr/bin/env bash
# T043 — submit the produced .dmg to notarytool, wait for approval, then
# staple the ticket.
#
# Usage: ./packaging/scripts/notarize.sh <aarch64|x86_64>
#
# Prerequisite: a notarytool keychain profile named "XLIGHT_NOTARY" set
# up via:
#   xcrun notarytool store-credentials XLIGHT_NOTARY \
#     --apple-id you@example.com --team-id TEAMID --password <app-password>

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <aarch64|x86_64>" >&2
  exit 2
fi

ARCH="$1"
TRIPLE="$ARCH-apple-darwin"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DMG_DIR="$REPO_ROOT/packaging/tauri/src-tauri/target/$TRIPLE/release/bundle/dmg"
PROFILE="${NOTARY_PROFILE:-XLIGHT_NOTARY}"

DMG_PATH="$(find "$DMG_DIR" -maxdepth 1 -name '*.dmg' | head -1 || true)"
if [[ -z "$DMG_PATH" ]]; then
  echo "error: no .dmg found under $DMG_DIR" >&2
  exit 2
fi

echo "→ Submitting $(basename "$DMG_PATH") to notarytool"
SUBMIT_LOG="$(mktemp)"
if ! xcrun notarytool submit "$DMG_PATH" --keychain-profile "$PROFILE" --wait --output-format plist \
      | tee "$SUBMIT_LOG"; then
  echo "error: notarytool submission failed" >&2
  cat "$SUBMIT_LOG" >&2
  exit 1
fi

# Extract the status from the plist — grep for "status" and accept only
# the literal value "Accepted".
STATUS="$(xcrun notarytool info --keychain-profile "$PROFILE" --output-format plist \
  "$(plutil -extract id raw "$SUBMIT_LOG" 2>/dev/null || echo unknown)" 2>/dev/null \
  | grep -A1 "<key>status</key>" | tail -1 | sed -E 's/.*<string>([^<]+)<\/string>.*/\1/' || true)"

if [[ "$STATUS" != "Accepted" ]]; then
  echo "error: notarization status is $STATUS (not Accepted)" >&2
  echo "→ Retrieving detailed log"
  xcrun notarytool log --keychain-profile "$PROFILE" \
    "$(plutil -extract id raw "$SUBMIT_LOG" 2>/dev/null)" /dev/stdout || true
  exit 1
fi

echo "→ Stapling ticket to $DMG_PATH"
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"

echo "✓ Notarized and stapled."
