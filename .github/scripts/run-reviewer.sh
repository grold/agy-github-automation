#!/usr/bin/env bash
set -euo pipefail

PR_NUMBER="${PR_NUMBER:-}"
REPO="${GITHUB_REPOSITORY:-}"

if [ -z "$PR_NUMBER" ]; then
  echo "Error: PR_NUMBER is not set." >&2
  exit 1
fi

echo "=== Step 1: Restoring Antigravity Credentials ==="
if [ -n "${AGY_AUTH_BASE64:-}" ]; then
  mkdir -p "$HOME"
  echo "$AGY_AUTH_BASE64" | base64 -d | tar -xzf - -C "$HOME"
  echo "Antigravity credentials restored into $HOME/.gemini"
else
  echo "Warning: AGY_AUTH_BASE64 is not set."
fi

# Start isolated D-Bus daemon and headless Secret Service
if [ -f "$HOME/.gemini/keyring_token.json" ]; then
  echo "Starting headless Secret Service for Antigravity..."
  export DBUS_SESSION_BUS_ADDRESS=$(dbus-daemon --session --print-address --fork)
  python3 /workspace/.github/scripts/mock-secret-service.py "$HOME/.gemini/keyring_token.json" &
  MOCK_SECRET_PID=$!
  sleep 1
  trap "kill $MOCK_SECRET_PID 2>/dev/null || true" EXIT
fi

echo "=== Step 2: Fetching PR Metadata and Diff ==="
PR_JSON=$(gh pr view "$PR_NUMBER" --json title,body,headRefOid,baseRefName)
PR_TITLE=$(echo "$PR_JSON" | jq -r '.title')
PR_BODY=$(echo "$PR_JSON" | jq -r '.body')
HEAD_SHA=$(echo "$PR_JSON" | jq -r '.headRefOid')
PR_DIFF=$(gh pr diff "$PR_NUMBER")

echo "=== Step 3: Invoking Antigravity Reviewer Agent ==="
PROMPT_FILE=".github/agents/reviewer.md"
GUIDELINES=""
if [ -f "$PROMPT_FILE" ]; then
  GUIDELINES=$(cat "$PROMPT_FILE")
fi

REVIEW_PROMPT=$(cat <<EOF
You are an autonomous Code Reviewer Agent operating in headless CI mode.

${GUIDELINES}

==================================================
TARGET PULL REQUEST:
PR #${PR_NUMBER}: ${PR_TITLE}

Description:
${PR_BODY}

DIFF:
${PR_DIFF}
==================================================

Analyze the diff and overall changes. Output ONLY the strict JSON object specified in the instructions with no conversational preamble.
EOF
)

AGENT_OUTPUT=$(agy -p "$REVIEW_PROMPT" --dangerously-skip-permissions)

echo "=== Step 4: Parsing Reviewer Output ==="
# Extract json block if wrapped in markdown code fence
PARSED_JSON=$(python3 -c '
import sys, re, json

raw = sys.stdin.read()
# Match ```json ... ``` or first {...}
fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
if fence_match:
    payload = fence_match.group(1)
else:
    brace_match = re.search(r"(\{.*\})", raw, re.DOTALL)
    payload = brace_match.group(1) if brace_match else ""

try:
    data = json.loads(payload)
    print(json.dumps(data))
except Exception as e:
    fallback = {
        "event": "COMMENT",
        "summary": "### Antigravity Code Review\n\n" + raw,
        "comments": []
    }
    print(json.dumps(fallback))
' <<< "$AGENT_OUTPUT")

EVENT=$(echo "$PARSED_JSON" | jq -r '.event // "COMMENT"')
# Validate event is one of APPROVE, REQUEST_CHANGES, COMMENT
if [[ "$EVENT" != "APPROVE" && "$EVENT" != "REQUEST_CHANGES" && "$EVENT" != "COMMENT" ]]; then
  EVENT="COMMENT"
fi

SUMMARY=$(echo "$PARSED_JSON" | jq -r '.summary // "Review completed."')
COMMENTS=$(echo "$PARSED_JSON" | jq '.comments // []')

echo "Review decision: $EVENT"

echo "=== Step 5: Submitting Review to GitHub ==="
REVIEW_PAYLOAD=$(jq -n \
  --arg commit_id "$HEAD_SHA" \
  --arg body "$SUMMARY" \
  --arg event "$EVENT" \
  --argjson comments "$COMMENTS" \
  '{commit_id: $commit_id, body: $body, event: $event, comments: $comments}')

# Submit using gh api
gh api "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
  -H "Accept: application/vnd.github+json" \
  --input - <<< "$REVIEW_PAYLOAD" || {
    echo "Warning: Direct line-review failed (possibly line numbers mismatched diff). Falling back to general review comment."
    gh pr review "$PR_NUMBER" --comment --body "$SUMMARY"
}

echo "Review submitted successfully!"
