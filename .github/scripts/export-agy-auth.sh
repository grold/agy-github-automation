#!/usr/bin/env bash
set -euo pipefail

# This script packages your local Antigravity credentials into a base64 string
# suitable for storing as a GitHub Actions secret (AGY_AUTH_BASE64).

REPO="${1:-}"
GEMINI_DIR="${HOME}/.gemini"

if [ ! -d "$GEMINI_DIR" ]; then
  echo "Error: ~/.gemini directory not found. Please log in with 'agy' first." >&2
  exit 1
fi

echo "Packaging credentials from $GEMINI_DIR..."

# Check for Linux Secret Service keyring token
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

TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/.gemini/antigravity-cli"

if [ -n "$KEYRING_SECRET" ]; then
  echo "$KEYRING_SECRET" > "$TEMP_DIR/.gemini/keyring_token.json"
  python3 -c "
import json, urllib.request, urllib.parse, datetime, sys, os, glob, re

token_path = sys.argv[1]
temp_dir = sys.argv[2]

client_id = None
client_secret = None

search_dirs = [
    os.path.expanduser('~/.local/share/mise/installs/antigravity-cli/latest/antigravity'),
    '/opt/mise/installs/antigravity-cli/latest/antigravity',
]
for fpath in search_dirs:
    if os.path.isfile(fpath):
        try:
            with open(fpath, 'rb') as f:
                data = f.read()
            sec_match = re.search(rb'(GOCSPX-[a-zA-Z0-9_-]{28})', data)
            if sec_match:
                client_secret = sec_match.group(1).decode()
                for cid_match in re.finditer(rb'([0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com)', data):
                    c = cid_match.group(1).decode()
                    if '1071006060591' in c:
                        client_id = c
                        break
                if client_id and client_secret:
                    break
        except Exception:
            continue

if client_id and client_secret:
    with open(os.path.join(temp_dir, '.gemini', 'oauth_client.json'), 'w') as f:
        json.dump({'client_id': client_id, 'client_secret': client_secret}, f)

    try:
        with open(token_path, 'r') as f:
            data = json.load(f)
        refresh_token = data.get('token', {}).get('refresh_token')
        if refresh_token:
            body = urllib.parse.urlencode({
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            }).encode()
            req = urllib.request.Request('https://oauth2.googleapis.com/token', data=body)
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode())
            data['token']['access_token'] = res['access_token']
            if 'refresh_token' in res:
                data['token']['refresh_token'] = res['refresh_token']
            if 'id_token' in res:
                data['id_token'] = res['id_token']
            expires_in = res.get('expires_in', 3600)
            new_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)
            data['token']['expiry'] = new_expiry.isoformat()
            with open(token_path, 'w') as f:
                json.dump(data, f)
            print('Refreshed token before packaging.')
    except Exception as e:
        print(f'Token refresh check: {e}')
" "$TEMP_DIR/.gemini/keyring_token.json" "$TEMP_DIR" 2>/dev/null || true
  echo "Included Secret Service keyring token."
fi

for f in settings.json state.json oauth_creds.json google_accounts.json installation_id; do
  if [ -f "$HOME/.gemini/$f" ]; then
    cp "$HOME/.gemini/$f" "$TEMP_DIR/.gemini/"
  fi
done

for f in settings.json jetski_state.pbtxt installation_id; do
  if [ -f "$HOME/.gemini/antigravity-cli/$f" ]; then
    cp "$HOME/.gemini/antigravity-cli/$f" "$TEMP_DIR/.gemini/antigravity-cli/"
  fi
done

TEMP_TAR=$(mktemp)
tar -czf "$TEMP_TAR" -C "$TEMP_DIR" .gemini
rm -rf "$TEMP_DIR"

ENCODED=$(base64 -w 0 < "$TEMP_TAR")
rm -f "$TEMP_TAR"

if [ -n "$REPO" ]; then
  echo "Setting AGY_AUTH_BASE64 secret directly for $REPO..."
  echo "$ENCODED" | gh secret set AGY_AUTH_BASE64 -R "$REPO"
  echo "Secret successfully set for $REPO!"
else
  echo ""
  echo "=========================================================================="
  echo "Base64 credential payload created successfully!"
  echo "Add this as a Secret in your GitHub repository:"
  echo "  Name:  AGY_AUTH_BASE64"
  echo "=========================================================================="
  echo ""
  echo "Run this command to set it directly using the GitHub CLI (gh):"
  echo "  bash .github/scripts/export-agy-auth.sh <owner/repo>"
  echo ""
fi
