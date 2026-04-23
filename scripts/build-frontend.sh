#!/usr/bin/env bash
# Build the x-onset React frontend and stage the dist/ output for commit.
#
# Usage: ./scripts/build-frontend.sh
# Run from the workspace root.

set -euo pipefail

FRONTEND_DIR="$(dirname "$0")/../src/review/frontend"

echo "Building frontend..."
npm --prefix "$FRONTEND_DIR" run build

echo "Staging dist/ for commit..."
git add "$FRONTEND_DIR/dist"

echo "Done. Run 'git commit' to include the updated dist/ in your next commit."
