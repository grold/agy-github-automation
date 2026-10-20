#!/usr/bin/env bash
set -euo pipefail

PR_NUMBER="${PR_NUMBER:-}"
REPO="${GITHUB_REPOSITORY:-}"
PR_CONTEXT_DIR="${PR_CONTEXT_DIR:-/agy-context}"

if [ -z "$PR_NUMBER" ]; then
  echo "Error: PR_NUMBER is not set." >&2
  exit 1
fi

echo "=== Step 1: Restoring Antigravity Credentials ==="
if [ -n "${AGY_AUTH_BASE64:-}" ]; then
  mkdir -p "$HOME"
  echo "$AGY_AUTH_BASE64" | base64 -d | tar -xzf - -C "$HOME"
  echo "Antigravity credentials restored into $HOME/.gemini"
  unset AGY_AUTH_BASE64
else
  echo "Warning: AGY_AUTH_BASE64 is not set."
fi

# Ensure ~/.gemini/antigravity-cli/antigravity-oauth-token is present
mkdir -p "$HOME/.gemini/antigravity-cli"
if [ -f "$HOME/.gemini/keyring_token.json" ] && [ ! -f "$HOME/.gemini/antigravity-cli/antigravity-oauth-token" ]; then
  cp "$HOME/.gemini/keyring_token.json" "$HOME/.gemini/antigravity-cli/antigravity-oauth-token"
fi

# Start isolated D-Bus daemon and headless Secret Service
export ANTIGRAVITY_APP_DATA_DIR="$HOME/.gemini/antigravity-cli"
export ANTIGRAVITY_PROJECT_ID="default-cli-project"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$HOME/.gemini/keyring_token.json" ]; then
  echo "Starting headless Secret Service for Antigravity..."
  export DBUS_SESSION_BUS_ADDRESS=$(dbus-daemon --session --print-address --fork)
  echo "DBUS_SESSION_BUS_ADDRESS: $DBUS_SESSION_BUS_ADDRESS"
  if [ -f "/opt/agy-automation/scripts/mock-secret-service.py" ]; then
    python3 /opt/agy-automation/scripts/mock-secret-service.py "$HOME/.gemini/keyring_token.json" &
  elif [ -f "$SCRIPT_DIR/mock-secret-service.py" ]; then
    python3 "$SCRIPT_DIR/mock-secret-service.py" "$HOME/.gemini/keyring_token.json" &
  else
    python3 /workspace/.github/scripts/mock-secret-service.py "$HOME/.gemini/keyring_token.json" &
  fi
  MOCK_SECRET_PID=$!
  trap "kill $MOCK_SECRET_PID 2>/dev/null || true" EXIT

  echo "Waiting for Secret Service to be available on D-Bus..."
  READY=0
  for i in $(seq 1 30); do
    if secret-tool lookup service gemini username antigravity >/dev/null 2>&1; then
      READY=1
      echo "Secret Service is ready (attempt $i)."
      break
    fi
    sleep 0.5
  done
  if [ "$READY" -ne 1 ]; then
    echo "Error: Secret Service failed to become ready within 15 seconds." >&2
    exit 1
  fi
fi

echo "=== Step 2: Fetching PR Metadata and Diff ==="
DIFF_FILE="/tmp/pr_diff.patch"
PR_INFO_FILE="/tmp/pr_info.json"

if [ -f "${PR_CONTEXT_DIR}/pr_diff.patch" ]; then
  cp "${PR_CONTEXT_DIR}/pr_diff.patch" "$DIFF_FILE"
elif [ -n "${GH_TOKEN:-}" ]; then
  gh pr diff "$PR_NUMBER" > "$DIFF_FILE"
else
  echo "Warning: No diff file found in ${PR_CONTEXT_DIR} and no GH_TOKEN available to fetch diff."
  touch "$DIFF_FILE"
fi

PR_TITLE=""
PR_BODY=""
if [ -f "${PR_CONTEXT_DIR}/pr_info.json" ]; then
  PR_TITLE=$(jq -r '.title // ""' "${PR_CONTEXT_DIR}/pr_info.json")
  PR_BODY=$(jq -r '.body // ""' "${PR_CONTEXT_DIR}/pr_info.json")
elif [ -n "${GH_TOKEN:-}" ]; then
  PR_JSON=$(gh pr view "$PR_NUMBER" --json title,body)
  PR_TITLE=$(echo "$PR_JSON" | jq -r '.title // ""')
  PR_BODY=$(echo "$PR_JSON" | jq -r '.body // ""')
fi

echo "=== Step 3: Invoking Antigravity Reviewer Agent ==="
GUIDELINES=""
if [ -f "/opt/agy-automation/agents/reviewer.md" ]; then
  GUIDELINES=$(cat "/opt/agy-automation/agents/reviewer.md")
elif [ -f ".github/agents/reviewer.md" ]; then
  GUIDELINES=$(cat ".github/agents/reviewer.md")
elif [ -f "$SCRIPT_DIR/../agents/reviewer.md" ]; then
  GUIDELINES=$(cat "$SCRIPT_DIR/../agents/reviewer.md")
fi

REVIEW_PROMPT=$(cat <<EOF
You are an autonomous Code Reviewer Agent operating in headless CI mode.

${GUIDELINES}

==================================================
TARGET PULL REQUEST:
PR #${PR_NUMBER}: ${PR_TITLE}

Description:
${PR_BODY}

The complete PR git diff is stored at: ${DIFF_FILE}
==================================================

Analyze the diff stored in ${DIFF_FILE} and inspect the repository code in /workspace as needed.
Output ONLY the strict JSON object specified in the instructions with no conversational preamble.
EOF
)

AI_MODEL_NAME="${AI_MODEL_NAME:-Gemini 3.8 Flash}"
AI_REASONING_EFFORT="${AI_REASONING_EFFORT:-Medium}"
EFFORT_LOWER=$(echo "$AI_REASONING_EFFORT" | tr '[:upper:]' '[:lower:]')

CLI_MODEL=""
if [[ "$AI_MODEL_NAME" =~ ^[a-z0-9.-]+$ ]] && [[ "$AI_MODEL_NAME" != *" "* ]]; then
  CLI_MODEL="$AI_MODEL_NAME"
else
  NORMALIZED=$(echo "$AI_MODEL_NAME" | tr '[:upper:]' '[:lower:]')
  if [[ "$NORMALIZED" == *"gemini"* && "$NORMALIZED" == *"flash"* ]]; then
    CLI_MODEL="gemini-3.8-flash-${EFFORT_LOWER}"
  elif [[ "$NORMALIZED" == *"gemini"* && "$NORMALIZED" == *"argon"* ]]; then
    CLI_MODEL="gemini-4-argon-${EFFORT_LOWER}"
  elif [[ "$NORMALIZED" == *"claude"* && "$NORMALIZED" == *"opus"* ]]; then
    CLI_MODEL="claude-opus-5-5-${EFFORT_LOWER}"
  elif [[ "$NORMALIZED" == *"claude"* && "$NORMALIZED" == *"sonnet"* ]]; then
    CLI_MODEL="claude-sonnet-5-5-${EFFORT_LOWER}"
  fi
fi

MODEL_ARGS=()
if [ -n "$CLI_MODEL" ]; then
  MODEL_ARGS=(--model "$CLI_MODEL")
elif [ -n "$EFFORT_LOWER" ]; then
  MODEL_ARGS=(--effort "$EFFORT_LOWER")
fi

AGENT_OUTPUT=$(agy -p "$REVIEW_PROMPT" "${MODEL_ARGS[@]}" --dangerously-skip-permissions)

echo "=== Step 4: Parsing and Saving Reviewer Output ==="
python3 -c '
import sys, re, json, os

raw = sys.stdin.read()
# Extract json block if wrapped in markdown code fence
fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
if fence_match:
    payload = fence_match.group(1)
else:
    brace_match = re.search(r"(\{.*\})", raw, re.DOTALL)
    payload = brace_match.group(1) if brace_match else ""

data = None
try:
    data = json.loads(payload)
except Exception:
    data = {
        "event": "COMMENT",
        "summary": "### Antigravity Code Review\n\n" + raw.strip(),
        "comments": []
    }

# Sanitize event
if data.get("event") not in ("APPROVE", "REQUEST_CHANGES", "COMMENT"):
    data["event"] = "COMMENT"

# Validate comments structure
validated_comments = []
for c in data.get("comments", []):
    if isinstance(c, dict) and "path" in c and "line" in c and "body" in c:
        try:
            line_int = int(c["line"])
            if line_int > 0 and str(c["path"]).strip() and str(c["body"]).strip():
                validated_comments.append({
                    "path": str(c["path"]).strip(),
                    "line": line_int,
                    "body": str(c["body"]).strip()
                })
        except (ValueError, TypeError):
            continue
data["comments"] = validated_comments

output_file = "/workspace/.agy-review.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print("Review JSON written to", output_file)
' <<< "$AGENT_OUTPUT"

# If GH_TOKEN is not provided, review posting is delegated to the host workflow
if [ -z "${GH_TOKEN:-}" ]; then
  echo "GH_TOKEN not set in container; review submission delegated to host workflow step."
  exit 0
fi

echo "=== Step 5: Submitting Review to GitHub (Standalone Mode) ==="
if [ -f "$SCRIPT_DIR/post-review.py" ]; then
  python3 "$SCRIPT_DIR/post-review.py" "/workspace/.agy-review.json" "$PR_NUMBER" "$REPO"
elif [ -f "/opt/agy-automation/scripts/post-review.py" ]; then
  python3 /opt/agy-automation/scripts/post-review.py "/workspace/.agy-review.json" "$PR_NUMBER" "$REPO"
fi

echo "Review submitted successfully!"
