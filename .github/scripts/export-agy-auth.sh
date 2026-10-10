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

# Check for Linux Secret Service keyring token
KEYRING_FILE="${HOME}/.gemini/keyring_token.json"
KEYRING_SECRET=""
if command -v secret-tool >/dev/null 2>&1; then
  KEYRING_SECRET=$(secret-tool lookup service gemini username antigravity 2>/dev/null || true)
fi

if [ -z "$KEYRING_SECRET" ]; then
  KEYRING_SECRET=$(python3 -c '
import secretstorage
try:
    bus = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(bus)
    for item in collection.get_all_items():
        if item.get_attributes().get("service") == "gemini":
            print(item.get_secret().decode("utf-8"))
            break
except Exception:
    pass
' 2>/dev/null || true)
fi

if [ -n "$KEYRING_SECRET" ]; then
  echo "$KEYRING_SECRET" > "$KEYRING_FILE"
fi

# Archive auth credentials, essential settings, and keyring token
TEMP_TAR=$(mktemp)
tar -czf "$TEMP_TAR" -C "$HOME" \
    $( [ -f "$KEYRING_FILE" ] && echo ".gemini/keyring_token.json" ) \
    .gemini/oauth_creds.json \
    .gemini/google_accounts.json \
    .gemini/installation_id \
    .gemini/settings.json \
    .gemini/state.json \
    .gemini/antigravity-cli/installation_id \
    .gemini/antigravity-cli/settings.json \
    .gemini/antigravity-cli/jetski_state.pbtxt

rm -f "$KEYRING_FILE"
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
