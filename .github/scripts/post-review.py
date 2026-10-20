#!/usr/bin/env python3
"""
Submits a review to a GitHub Pull Request using the GitHub CLI (gh).
Handles bot self-review restrictions (forcing COMMENT), line comment validation,
AI attribution footer appending, and fallbacks.
"""

import json
import os
import subprocess
import sys

def run_cmd(cmd, input_data=None):
    res = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True,
        text=True
    )
    return res.returncode, res.stdout, res.stderr

def main():
    if len(sys.argv) < 4:
        print("Usage: post-review.py <review_json_path> <pr_number> <repo> [pr_info_json_path]", file=sys.stderr)
        sys.exit(1)

    review_path = sys.argv[1]
    pr_number = sys.argv[2]
    repo = sys.argv[3]
    pr_info_path = sys.argv[4] if len(sys.argv) > 4 else None

    if not os.path.exists(review_path):
        print(f"Error: Review JSON not found at {review_path}", file=sys.stderr)
        sys.exit(1)

    with open(review_path, "r", encoding="utf-8") as f:
        review_data = json.load(f)

    # Fetch PR details if not provided
    head_sha = ""
    pr_author = ""
    if pr_info_path and os.path.exists(pr_info_path):
        with open(pr_info_path, "r", encoding="utf-8") as f:
            pr_info = json.load(f)
            head_sha = pr_info.get("headRefOid", "")
            pr_author = pr_info.get("author", {}).get("login", "")

    if not head_sha:
        code, out, _ = run_cmd(["gh", "pr", "view", pr_number, "--repo", repo, "--json", "headRefOid,author"])
        if code == 0:
            try:
                data = json.loads(out)
                head_sha = data.get("headRefOid", "")
                pr_author = data.get("author", {}).get("login", "")
            except Exception:
                pass

    event = review_data.get("event", "COMMENT")
    summary = review_data.get("summary", "Review completed.")
    comments = review_data.get("comments", [])

    # Check bot self-review constraint: GitHub forbids APPROVE or REQUEST_CHANGES on own PR
    bot_name = os.environ.get("BOT_NAME", "")
    if pr_author and (pr_author == bot_name or pr_author.endswith("[bot]")):
        if event in ("APPROVE", "REQUEST_CHANGES"):
            print(f"PR #{pr_number} was created by bot '{pr_author}'. Forcing review event to COMMENT.")
            event = "COMMENT"

    # Attribution footer
    model_name = os.environ.get("AI_MODEL_NAME", "Gemini 3.8 Flash")
    reasoning_effort = os.environ.get("AI_REASONING_EFFORT", "Medium")
    attribution = f"\n\n---\n*Assisted by {model_name} (Reasoning: {reasoning_effort})*"

    if attribution.strip() not in summary:
        summary = summary.rstrip() + attribution

    payload = {
        "body": summary,
        "event": event,
    }
    if head_sha:
        payload["commit_id"] = head_sha
    if comments:
        payload["comments"] = comments

    print(f"Submitting review for PR #{pr_number} ({event}) with {len(comments)} inline comments...")
    
    # Attempt 1: Direct line-by-line review submission
    code, stdout, stderr = run_cmd(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}/reviews", "-H", "Accept: application/vnd.github+json", "--input", "-"],
        input_data=json.dumps(payload)
    )

    if code == 0:
        print("Review submitted successfully!")
        return

    print(f"Notice: Initial review submission returned status {code}:\n{stderr}")

    # Attempt 2: If event was APPROVE or REQUEST_CHANGES, retry with COMMENT
    if event != "COMMENT":
        print("Retrying review submission with event 'COMMENT'...")
        payload["event"] = "COMMENT"
        code, stdout, stderr = run_cmd(
            ["gh", "api", f"repos/{repo}/pulls/{pr_number}/reviews", "-H", "Accept: application/vnd.github+json", "--input", "-"],
            input_data=json.dumps(payload)
        )
        if code == 0:
            print("Review submitted successfully as COMMENT!")
            return

    # Attempt 3: Line comments failed (e.g. line numbers outside diff hunks). Format inline comments into summary.
    print("Formatting line comments into summary body to prevent feedback loss...")
    formatted_comments = []
    for c in comments:
        formatted_comments.append(f"- **`{c.get('path')}:{c.get('line')}`**: {c.get('body')}")
    
    fallback_body = summary
    if formatted_comments:
        fallback_body += "\n\n### Line Feedback\n" + "\n".join(formatted_comments)

    code, stdout, stderr = run_cmd(
        ["gh", "pr", "review", pr_number, "--repo", repo, "--comment", "--body", fallback_body]
    )
    if code == 0:
        print("Review fallback posted successfully as general comment!")
    else:
        print(f"Failed to post fallback review comment:\n{stderr}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
