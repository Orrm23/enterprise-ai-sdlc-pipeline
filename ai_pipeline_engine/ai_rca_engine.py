"""AI Root Cause Analysis (RCA) Engine for Build & Deployment Failures.
Triggered automatically on pipeline step failure to diagnose the issue and create Azure DevOps Bug items.
"""

import os
import sys
import subprocess
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ai_pipeline_engine.config import AIClientConfig


SYSTEM_PROMPT = """You are a Principal DevOps & Site Reliability Engineer performing Root Cause Analysis (RCA).
System Tag: RCA_ANALYZER

Analyze the provided build error logs, recent git commits, and failure context.
Generate a structured RCA Report:
1. 💥 Failure Summary (1-2 sentence executive overview)
2. 🔬 Root Cause Classification ([COMPILATION | DEPENDENCY_CONFLICT | LOGIC_REGRESSION | INFRA_NETWORK | PERMISSION])
3. 📍 Offending Source / Configuration (Specific filename, line number, or environment variable)
4. 🩺 Why it Happened (Mechanism of failure)
5. 🩹 Remediation Action Plan (Direct instructions and concrete code/config patch)

Write with high technical precision."""


def gather_build_context() -> dict:
    """Collects logs, git commits, and file changes."""
    context = {"git_log": "", "recent_changes": "", "error_logs": ""}

    try:
        context["git_log"] = subprocess.check_output(
            ["git", "log", "-n", "5", "--oneline"], stderr=subprocess.DEVNULL, text=True
        )
    except Exception:
        context["git_log"] = "Unable to fetch git log."

    try:
        context["recent_changes"] = subprocess.check_output(
            ["git", "status", "--short"], stderr=subprocess.DEVNULL, text=True
        )
    except Exception:
        context["recent_changes"] = "Unable to fetch git status."

    # Search for log files or read standard build error log if present
    log_candidates = ["build.log", "pytest_errors.log", "npm_debug.log"]
    collected_logs = []
    for log_path in log_candidates:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                collected_logs.append(f"=== {log_path} ===\n" + f.read()[-3000:])

    if not collected_logs:
        collected_logs.append("Standard CI step failure detected. Error captured from runner environment.")

    context["error_logs"] = "\n".join(collected_logs)
    return context


def create_azure_devops_bug(config: AIClientConfig, rca_text: str):
    """Automatically logs a Bug Work Item in Azure DevOps Boards with the RCA diagnosis."""
    if not (config.devops_token and config.collection_uri and config.project):
        print("[AI RCA Engine] Azure DevOps credentials/project not configured; skipping Work Item creation.")
        return None

    url = f"{config.collection_uri.rstrip('/')}/{config.project}/_apis/wit/workitems/$Bug?api-version=7.0"
    headers = {
        "Content-Type": "application/json-patch+json",
        "Authorization": f"Bearer {config.devops_token}",
    }

    # Extract first line for title
    summary_line = rca_text.splitlines()[0].replace("#", "").strip() if rca_text else "Pipeline Failure"
    title = f"[AI Bug] Build #{config.build_id or 'Unknown'} Failure: {summary_line[:80]}"

    payload = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/Microsoft.VSTS.TCM.ReproSteps", "value": f"<pre>{rca_text}</pre>"},
        {"op": "add", "path": "/fields/System.Tags", "value": "AI-AutoBug; CI-Failure; Pipeline-RCA"},
        {"op": "add", "path": "/fields/System.Reason", "value": "Build Failure"},
    ]

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code in [200, 201]:
            work_item = response.json()
            bug_id = work_item.get("id")
            print(f"[AI RCA Engine] Successfully created Azure DevOps Bug #{bug_id}: {title}")
            return bug_id
        else:
            print(f"[AI RCA Engine] Failed to create Work Item: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[AI RCA Engine] Exception creating Work Item: {e}")
    return None


def main():
    print("[AI RCA Engine] Initiating automated failure diagnosis...")
    config = AIClientConfig()
    context = gather_build_context()

    user_prompt = f"""Build ID: {config.build_id or 'Local'}
Branch: {config.branch_name or 'unknown'}
Commit: {config.commit_hash or 'HEAD'}

Recent Git Commits:
{context['git_log']}

Recent Changes / Git Status:
{context['recent_changes']}

Error Logs / Trace:
{context['error_logs']}
"""

    print("[AI RCA Engine] Synthesizing root cause analysis via LLM...")
    rca_output = config.complete_prompt(SYSTEM_PROMPT, user_prompt, max_tokens=1800)

    report_file = "ai_root_cause_analysis.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(rca_output)

    print(f"[AI RCA Engine] RCA diagnosis written to {report_file}")
    print("\n" + "=" * 60)
    print(rca_output)
    print("=" * 60 + "\n")

    # Create Azure DevOps Work Item Bug
    create_azure_devops_bug(config, rca_output)

    # Emit Azure DevOps error task notification
    print("##vso[task.logissue type=error]AI RCA Engine completed failure root cause analysis. See report.")


if __name__ == "__main__":
    main()
