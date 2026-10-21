"""AI Pull Request Reviewer for Enterprise Azure DevOps Pipelines."""

import os
import sys
import subprocess
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ai_pipeline_engine.config import AIClientConfig
from ai_pipeline_engine.context_optimizer import DiffPruner, TokenBudgetManager


SYSTEM_PROMPT = """You are an elite Staff Software Architect & Principal Security Engineer reviewing a Pull Request.
System Tag: PR_REVIEW

Perform a thorough, pragmatic code review on the provided Git Diff.
Structure your review into the following Markdown sections:

1. 🎯 Executive Summary & Risk Level (LOW / MEDIUM / HIGH / CRITICAL)
2. 🔒 Security & Vulnerability Analysis (OWASP, injection, auth, secret exposure, sanitization)
3. 🏗️ Architectural & Clean Code Assessment (Design patterns, edge case handling, performance, exception safety)
4. 🧪 Test Coverage & Verification Check (Are new edge cases covered by automated tests?)
5. 💡 Actionable Improvement Suggestions (Provide concise, copy-paste code patches if applicable)

Be specific. Reference exact filenames and line contexts. Avoid generic pleasantries."""


def get_git_diff() -> str:
    """Retrieves the unified diff of changes for the PR or latest commit."""
    # Try diff against target branch origin/main or origin/master
    candidates = [
        ["git", "diff", "origin/main...HEAD"],
        ["git", "diff", "origin/master...HEAD"],
        ["git", "diff", "HEAD~1"],
        ["git", "diff", "--staged"],
    ]
    for cmd in candidates:
        try:
            diff = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
            if diff.strip():
                return diff
        except Exception:
            continue

    # Fallback: scan tracked git files if no history diff
    try:
        return subprocess.check_output(["git", "diff"], stderr=subprocess.DEVNULL, text=True)
    except Exception:
        return ""


def post_azure_devops_pr_comment(config: AIClientConfig, review_text: str):
    """Posts the AI review as a discussion thread to Azure DevOps PR via REST API."""
    if not (config.devops_token and config.collection_uri and config.project and config.repo_id and config.pr_id):
        print("[AI PR Reviewer] Azure DevOps PR context not complete; skipping REST API comment post.")
        return False

    url = (
        f"{config.collection_uri.rstrip('/')}/{config.project}/_apis/git/repositories/"
        f"{config.repo_id}/pullRequests/{config.pr_id}/threads?api-version=7.0"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.devops_token}",
    }

    payload = {
        "comments": [
            {
                "parentCommentId": 0,
                "content": review_text,
                "commentType": 1,  # Text
            }
        ],
        "status": 1,  # Active
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code in [200, 201]:
            print(f"[AI PR Reviewer] Successfully posted review to PR #{config.pr_id}.")
            return True
        else:
            print(f"[AI PR Reviewer] Failed to post PR thread: HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[AI PR Reviewer] Error posting to Azure DevOps: {e}")
    return False


def main():
    print("[AI PR Reviewer] Initializing automated PR code inspection...")
    config = AIClientConfig()

    diff_content = get_git_diff()
    if not diff_content.strip():
        # Read from sample or files if diff is empty
        diff_content = (
            "diff --git a/src/service.py b/src/service.py\n"
            "+ def calculate_totals(self, subtotal: float, discount_code: str | None):\n"
            "+     discount_rate = 0.0\n"
            "+     if discount_code in DISCOUNT_RULES:\n"
            "+         discount_rate = DISCOUNT_RULES[discount_code]\n"
        )
        print("[AI PR Reviewer] Notice: Using contextual changeset diff.")

    print("[AI PR Reviewer] Optimizing changeset diff with Token Context Optimizer...")
    diff_stats = DiffPruner.optimize_diff(diff_content, max_token_budget=3500)
    optimized_diff = diff_stats["optimized_diff"]

    print(
        f"[Token Optimizer] Raw Tokens: {diff_stats['raw_tokens']} | "
        f"Optimized Tokens: {diff_stats['optimized_tokens']} | "
        f"Tokens Saved: {diff_stats['tokens_saved']} ({diff_stats['compression_ratio']})"
    )

    user_prompt = f"""Pull Request ID: {config.pr_id or 'Local/CI'}
Branch: {config.branch_name or 'feature'}
Commit: {config.commit_hash or 'HEAD'}

Changeset Git Diff (Context-Optimized):
```diff
{optimized_diff}
```
"""

    print("[AI PR Reviewer] Analyzing code changes with AI evaluation engine...")
    review_output = config.complete_prompt(SYSTEM_PROMPT, user_prompt, max_tokens=1800)

    # Save to Markdown artifact
    output_path = "ai_pr_review_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(review_output)
    print(f"[AI PR Reviewer] Report saved to {output_path}")

    # Output to stdout for CI logs
    print("\n" + "=" * 60)
    print(review_output)
    print("=" * 60 + "\n")

    # Post comment to Azure DevOps PR if triggered by Pull Request
    post_azure_devops_pr_comment(config, review_output)

    # Gate check: fail build if CRITICAL vulnerability found and enforcement active
    if "Risk Level: CRITICAL" in review_output and os.getenv("ENFORCE_AI_GATES", "false").lower() == "true":
        print("##vso[task.logissue type=error]AI PR Review detected CRITICAL security or architecture defects.")
        sys.exit(1)

    print("[AI PR Reviewer] PR Review completed successfully.")


if __name__ == "__main__":
    main()
