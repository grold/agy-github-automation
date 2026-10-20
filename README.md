# Antigravity GitHub Automation Template

Autonomous issue-solving and PR-reviewing workflows powered by **Antigravity CLI (`agy`)** inside isolated Docker containers on GitHub Actions, fully attributed to a dedicated bot (**`[bot]`**).

---

## 🚀 Architecture Overview

```
 [ GitHub Issue Opened / Labeled ]
              │ (Verified collaborator or 'agent:solve' label)
              ▼
   ┌─────────────────────────────────────────────────────────┐
   │ GitHub Actions: agy-issue-solver.yml                    │
   │                                                         │
   │  1. Generates GitHub App Token (e.g., your-bot[bot])    │
   │  2. Restores ~/.gemini credentials from secret          │
   │  3. Spawns isolated Docker runner container             │
   │  4. Runs headless Secret Service for agy authentication │
   │  5. agy analyzes codebase, writes fix & unit tests      │
   │  6. Commits changes under bot identity: your-bot[bot]   │
   │  7. Opens Pull Request via GitHub App                   │
   └─────────────────────────────────────────────────────────┘
              │
              ▼ (PR Opened event triggers next workflow)
   ┌─────────────────────────────────────────────────────────┐
   │ GitHub Actions: agy-pr-reviewer.yml                     │
   │                                                         │
   │  1. Generates GitHub App Token                          │
   │  2. Spawns isolated Docker runner container             │
   │  3. Fetches diff and PR metadata                        │
   │  4. agy reviews code against reviewer guidelines        │
   │  5. Submits line-by-line comments & formal review       │
   │     assessment posted by your-bot[bot]                  │
   └─────────────────────────────────────────────────────────┘
```

---

## ✨ Features

- **Reusable Workflows (`workflow_call`)**: Use `grold/agy-github-automation` as a central hub. Any other repository can run the solver and reviewer with a simple 10-line YAML file—no files or scripts to copy!
- **Prebuilt Container on GHCR**: Ships as `ghcr.io/grold/agy-runner:latest`, eliminating `docker build` overhead and booting in ~5 seconds.
- **Autonomous End-to-End Resolution**: Automatically resolves issues, writes tests, creates PRs, and submits reviews.
- **Dedicated Bot Attribution**: Commits, PRs, and review comments are posted under a dedicated bot identity (e.g. `grold-agy-bot [bot]`), keeping your personal profile clean.
- **Chained Workflow Execution**: Uses GitHub App authentication so that opening a PR seamlessly triggers the downstream PR Reviewer workflow (which standard `GITHUB_TOKEN` suppresses).
- **Headless Secret Service Integration**: Runs a lightweight mock D-Bus Secret Service inside Docker so `agy` seamlessly unlocks stored subscription credentials.
- **Quota & Security Guardrails**: Restricted to repository owners, members, and collaborators. External issues are ignored unless explicitly labeled `agent:solve`.

---

## 📁 Directory Structure

```
.github/
├── agents/
│   ├── solver.md             # Custom prompt & guidelines for Issue Solver Agent
│   └── reviewer.md           # Custom checklist & structured schema for PR Reviewer Agent
├── docker/
│   └── Dockerfile            # Isolated Ubuntu runner with mise, agy, gh CLI, git, jq, dbus
├── scripts/
│   ├── export-agy-auth.sh    # Exports your local ~/.gemini credentials to base64
│   ├── setup-github-app.py   # Automated 1-click GitHub App registration & secret configuration
│   ├── mock-secret-service.py# Headless D-Bus Secret Service for containerized agy
│   ├── run-solver.sh         # Headless solver execution script
│   └── run-reviewer.sh       # Headless reviewer execution script with JSON parser
└── workflows/
    ├── agy-issue-solver.yml  # GitHub Actions workflow triggered on issues
    └── agy-pr-reviewer.yml   # GitHub Actions workflow triggered on pull requests
```

---

## 🛠️ Setup Instructions

### Option A: Use as a Reusable Workflow in Another Repository (Recommended)

You don't need to copy any Dockerfiles or scripts! In any of your target repositories:

1. **Grant the GitHub App Access**:
   Go to [GitHub App Installations](https://github.com/settings/apps/grold-agy-bot/installations) and add your target repository.
2. **Add Repository Secrets**:
   Set `APP_ID`, `APP_PRIVATE_KEY`, and `AGY_AUTH_BASE64` in the target repository's **Settings → Secrets and variables → Actions**.
3. **Create Caller Workflows**:
   Create `.github/workflows/solve.yml` in the target repository:
   ```yaml
   name: Antigravity Solver
   on:
     issues:
       types: [opened, labeled]

   jobs:
     solve:
       if: >
         (github.event.action == 'opened' && contains(fromJSON('["OWNER", "MEMBER", "COLLABORATOR"]'), github.event.issue.author_association)) ||
         (github.event.action == 'labeled' && github.event.label.name == 'agent:solve')
       uses: grold/agy-github-automation/.github/workflows/agy-issue-solver.yml@main
       secrets: inherit
   ```
   And `.github/workflows/review.yml`:
   ```yaml
   name: Antigravity Reviewer
   on:
     pull_request:
       types: [opened, synchronize, reopened]

   jobs:
     review:
       uses: grold/agy-github-automation/.github/workflows/agy-pr-reviewer.yml@main
       secrets: inherit
   ```

---

### Option B: Standalone Repository Setup

If you want to maintain a standalone clone with custom container modifications:

#### 1. Copy Template Files to Your Target Repository
Copy the `.github` directory into your target git repository:
```bash
cp -r .github /path/to/your-repo/
```

### 2. Export Your Antigravity Credentials
Run the export helper from your workstation where `agy` is already logged in with your subscription:
```bash
bash .github/scripts/export-agy-auth.sh
```
This generates a base64 string of your active `~/.gemini` session.

Add it as a repository secret:
- Go to your repository on GitHub: **Settings** → **Secrets and variables** → **Actions**.
- Click **New repository secret**.
- Name: `AGY_AUTH_BASE64`
- Value: paste the base64 string output by the export script.

*(Or run `gh secret set AGY_AUTH_BASE64 --body "<base64_string>"` using GitHub CLI)*

### 3. Register GitHub App for Bot Identity (Recommended)
Using a GitHub App allows all solver and reviewer actions to be attributed to a dedicated bot (e.g. `your-repo-bot [bot]`) and enables chained workflow triggers.

Run the automated setup helper:
```bash
python3 .github/scripts/setup-github-app.py <owner>/<repo> [bot-name]
```
1. Open the local link prompted in your browser (`http://localhost:3000`).
2. Click **Create GitHub App**.
3. Install the app on your repository.
4. The script automatically stores `APP_ID` and `APP_PRIVATE_KEY` directly in your repository secrets!

*(Alternative: You can provide a Personal Access Token stored as `BOT_GITHUB_TOKEN`, but actions will appear under that user account rather than a `[bot]` identity).*

### 4. Enable Workflow Permissions
In your GitHub repository:
- Go to **Settings** → **Actions** → **General**.
- Under **Workflow permissions**, select **Read and write permissions**.
- Check **Allow GitHub Actions to create and approve pull requests**.

---

## 💡 How It Works

### Opening an Issue
When an issue is opened by a repository maintainer (or when a maintainer applies the label `agent:solve` to an external issue):
1. `agy-issue-solver.yml` triggers.
2. The agent reads the issue title and description, analyzes project structure, and creates a fix branch `agent/issue-<number>`.
3. The agent implements the changes and adds unit tests.
4. Commits are signed with `your-bot[bot]`.
5. A pull request is submitted referencing the issue.

### Pull Request Review
When the pull request is opened or updated:
1. `agy-pr-reviewer.yml` triggers automatically.
2. The agent fetches the git diff, checks the changes against [`.github/agents/reviewer.md`](.github/agents/reviewer.md), and validates code quality and test coverage.
3. The bot posts line-by-line feedback and a formal review assessment.

---

## ⚙️ Customization

### Modifying Agent Behavior
- Edit [`.github/agents/solver.md`](.github/agents/solver.md) to adjust how the solver explores, tests, and modifies code.
- Edit [`.github/agents/reviewer.md`](.github/agents/reviewer.md) to customize review criteria, required checks, and feedback tone.

### Adding Project Tooling to the Container
Edit [`.github/docker/Dockerfile`](.github/docker/Dockerfile) to add any compilers, language runtimes, linters, or test runners your project requires (e.g., Python, Rust, Go, Node, etc.).

---

## 🔒 Security & Guardrails

- **Collaborator Filtering:** The solver workflow will only execute for issues created by repository collaborators, members, or owners (`OWNER`, `MEMBER`, `COLLABORATOR`). External or untrusted user issues will not consume your Antigravity quota unless explicitly labeled with `agent:solve` by a maintainer.
- **Isolated Execution & Token Segregation:** GitHub tokens (`GH_TOKEN` / `GITHUB_TOKEN`) are strictly withheld from the agent's Docker container. The agent executes in an isolated environment and only modifies repository files. Git commits, pushes, and GitHub API interactions are executed by trusted host runner steps after the agent finishes.
- **Credential Protection:** `persist-credentials: false` ensures no tokens are ever saved to `.git/config`. Antigravity credentials (`AGY_AUTH_BASE64`) are decoded into `~/.gemini` and immediately scrubbed from process environment variables.
- **Concurrency & Deduplication:** Concurrency controls ensure only one solver or reviewer run executes per issue or PR at any time, canceling redundant in-progress runs when new commits or duplicate events arrive.
