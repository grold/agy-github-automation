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

# Archive only auth credentials and essential settings
TEMP_TAR=$(mktemp)
tar -czf "$TEMP_TAR" -C "$HOME" \
    .gemini/oauth_creds.json \
    .gemini/google_accounts.json \
    .gemini/installation_id \
    .gemini/settings.json \
    .gemini/state.json \
    .gemini/antigravity-cli/installation_id \
    .gemini/antigravity-cli/settings.json

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
