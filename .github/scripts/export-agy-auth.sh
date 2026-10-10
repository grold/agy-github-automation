#!/usr/bin/env bash
set -euo pipefail

# This script packages your local Antigravity credentials into a base64 string
# suitable for storing as a GitHub Actions secret (AGY_AUTH_BASE64).

GEMINI_DIR="${HOME}/.gemini"

if [ ! -d "$GEMINI_DIR" ]; then
  echo "Error: ~/.gemini directory not found. Please log in with 'agy' first." >&2
  exit 1
fi

echo "Packaging credentials from $GEMINI_DIR..."

# Archive ~/.gemini excluding unnecessary caches/logs/tmp
TEMP_TAR=$(mktemp)
tar --exclude="tmp" \
    --exclude="history" \
    --exclude="antigravity-cli/brain" \
    --exclude="antigravity-cli/logs" \
    -czf "$TEMP_TAR" -C "$HOME" .gemini

ENCODED=$(base64 -w 0 < "$TEMP_TAR")
rm -f "$TEMP_TAR"

echo ""
echo "=========================================================================="
echo "Base64 credential payload created successfully!"
echo "Add this as a Secret in your GitHub repository:"
echo "  Name:  AGY_AUTH_BASE64"
echo "=========================================================================="
echo ""
echo "Run this command to set it directly using the GitHub CLI (gh):"
echo "  gh secret set AGY_AUTH_BASE64 --body \"$ENCODED\""
echo ""
