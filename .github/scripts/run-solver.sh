#!/usr/bin/env bash
set -euo pipefail

ISSUE_NUMBER="${ISSUE_NUMBER:-}"
BASE_BRANCH="${BASE_BRANCH:-main}"
ISSUE_CONTEXT_FILE="${ISSUE_CONTEXT_FILE:-}"

if [ -z "$ISSUE_NUMBER" ]; then
  echo "Error: ISSUE_NUMBER is not set." >&2
  exit 1
fi

echo "=== Step 1: Restoring Antigravity Credentials ==="
if [ -n "${AGY_AUTH_BASE64:-}" ]; then
  mkdir -p "$HOME"
  echo "$AGY_AUTH_BASE64" | base64 -d | tar -xzf - -C "$HOME"
  echo "Antigravity credentials restored into $HOME/.gemini"
  unset AGY_AUTH_BASE64
else
  echo "Warning: AGY_AUTH_BASE64 is not set. Assuming ~/.gemini is already mounted."
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

BRANCH_NAME="agent/issue-${ISSUE_NUMBER}"

echo "=== Step 2: Preparing Branch '${BRANCH_NAME}' ==="
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
if [ "$CURRENT_BRANCH" != "$BRANCH_NAME" ]; then
  git checkout -B "$BRANCH_NAME" "origin/${BASE_BRANCH}" 2>/dev/null || git checkout -B "$BRANCH_NAME" "${BASE_BRANCH}" 2>/dev/null || true
fi

echo "=== Step 3: Invoking Antigravity Agent ==="
GUIDELINES=""
if [ -f "/opt/agy-automation/agents/solver.md" ]; then
  GUIDELINES=$(cat "/opt/agy-automation/agents/solver.md")
elif [ -f ".github/agents/solver.md" ]; then
  GUIDELINES=$(cat ".github/agents/solver.md")
elif [ -f "$SCRIPT_DIR/../agents/solver.md" ]; then
  GUIDELINES=$(cat "$SCRIPT_DIR/../agents/solver.md")
fi

ISSUE_INFO=""
if [ -n "$ISSUE_CONTEXT_FILE" ] && [ -f "$ISSUE_CONTEXT_FILE" ]; then
  ISSUE_INFO=$(cat "$ISSUE_CONTEXT_FILE")
else
  ISSUE_TITLE="${ISSUE_TITLE:-Issue #${ISSUE_NUMBER}}"
  ISSUE_BODY="${ISSUE_BODY:-}"
  ISSUE_INFO="Issue #${ISSUE_NUMBER}: ${ISSUE_TITLE}

${ISSUE_BODY}"
fi

SOLVER_PROMPT=$(cat <<EOF
You are an autonomous Issue Solver Agent operating in headless CI mode.

${GUIDELINES}

==================================================
TARGET ISSUE:
${ISSUE_INFO}
==================================================

Inspect the codebase, locate the source of the issue, implement the fix, run any available tests/checks, and ensure working tree contains clean modifications.
Do NOT run git commit or git push; leave changes in the working directory for the pipeline to commit.
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

# Run agy in headless non-interactive print mode with auto-approved permissions
agy -p "$SOLVER_PROMPT" "${MODEL_ARGS[@]}" --dangerously-skip-permissions

echo "=== Step 4: Checking Working Tree Changes ==="
if [ -z "$(git status --porcelain)" ]; then
  echo "No changes were made by the agent."
  if [ -n "${GH_TOKEN:-}" ]; then
    gh issue comment "$ISSUE_NUMBER" --body "🤖 **Antigravity Issue Solver** examined this issue but did not make any code changes. Please review the issue details or run manual investigation."
  fi
  exit 0
fi

# If GH_TOKEN is not provided, git commit, push and PR creation are handled by the host workflow
if [ -z "${GH_TOKEN:-}" ]; then
  echo "GH_TOKEN not set in container; skipping commit and push (delegated to host workflow step)."
  exit 0
fi

echo "=== Step 5: Committing and Pushing Changes (Standalone Mode) ==="
git config --global user.name "${BOT_NAME:-antigravity-bot[bot]}"
git config --global user.email "${BOT_EMAIL:-antigravity-bot[bot]@users.noreply.github.com}"
git add -A
COMMIT_MSG=$(cat <<EOF
fix(issue-${ISSUE_NUMBER}): Automated fix

Automated fix generated by Antigravity Agent.
Fixes #${ISSUE_NUMBER}
EOF
)
git commit -m "$COMMIT_MSG"
git push -u origin "$BRANCH_NAME" --force-with-lease

echo "=== Step 6: Creating Pull Request (Standalone Mode) ==="
EXISTING_PR=$(gh pr list --head "$BRANCH_NAME" --json number --jq '.[0].number' 2>/dev/null || true)

PR_BODY=$(cat <<EOF
Closes #${ISSUE_NUMBER}

### Automated Solution
This pull request was automatically generated by the Antigravity Issue Solver Agent.

- **Issue:** #${ISSUE_NUMBER}
- **Branch:** \`${BRANCH_NAME}\`

Please review the code changes and test results.

---
*Assisted by ${AI_MODEL_NAME} (Reasoning: ${AI_REASONING_EFFORT})*
EOF
)

if [ -n "$EXISTING_PR" ]; then
  echo "Pull request already exists: #${EXISTING_PR}. Updating..."
  gh pr edit "$EXISTING_PR" --body "$PR_BODY"
  PR_NUMBER="$EXISTING_PR"
else
  PR_URL=$(gh pr create --base "$BASE_BRANCH" --head "$BRANCH_NAME" \
    --title "fix: automated solution for #${ISSUE_NUMBER}" \
    --body "$PR_BODY")
  echo "Created PR: $PR_URL"
  PR_NUMBER=$(gh pr view "$BRANCH_NAME" --json number --jq '.number')
fi

gh issue comment "$ISSUE_NUMBER" --body "$(cat <<EOF
🤖 **Antigravity Issue Solver** has prepared a pull request for this issue: #${PR_NUMBER}

---
*Assisted by ${AI_MODEL_NAME} (Reasoning: ${AI_REASONING_EFFORT})*
EOF
)"
echo "Completed successfully!"
