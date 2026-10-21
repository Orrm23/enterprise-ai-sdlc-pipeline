"""AI Test Failure Analyzer for Azure DevOps Pipelines.
Parses JUnit test XMLs, identifies failure root causes, and generates remediation patches.
"""

import os
import sys
import glob
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

# Ensure UTF-8 output encoding across Windows / Linux runners
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ai_pipeline_engine.config import AIClientConfig


SYSTEM_PROMPT = """You are an automated Site Reliability & Software QA Test Architect.
System Tag: TEST_ANALYSIS

Analyze the following failed unit/integration test results.
For each failed test case:
1. 🔍 Diagnose the exact root cause of failure (e.g. Logic error, contract drift, unhandled None/null, broken mock).
2. ⚡ Classify the failure type: [DETERMINISTIC_BUG | REGRESSION | FLAKY_ENVIRONMENT | SCHEMA_DRIFT].
3. 🛠️ Provide the exact code fix or test fixture correction as a unified diff.

Be concise, technical, and accurate."""


def parse_junit_xml(file_path: str) -> List[Dict[str, Any]]:
    """Extracts failed test cases from a standard JUnit XML report."""
    failures = []
    if not os.path.exists(file_path):
        return failures

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Handle both <testsuites><testsuite> and root <testsuite>
        testcases = root.iter("testcase")
        for tc in testcases:
            failure = tc.find("failure")
            error = tc.find("error")
            node = failure if failure is not None else error
            if node is not None:
                failures.append({
                    "name": tc.attrib.get("name", "UnknownTest"),
                    "classname": tc.attrib.get("classname", ""),
                    "file": tc.attrib.get("file", ""),
                    "message": node.attrib.get("message", ""),
                    "trace": node.text or "",
                })
    except Exception as e:
        print(f"[AI Test Analyzer] Error parsing XML {file_path}: {e}")

    return failures


def main():
    print("[AI Test Analyzer] Scanning workspace for JUnit test reports...")
    config = AIClientConfig()

    xml_files = glob.glob("**/test-*.xml", recursive=True) + glob.glob("**/junit*.xml", recursive=True)
    all_failures: List[Dict[str, Any]] = []

    for xml_file in xml_files:
        print(f"[AI Test Analyzer] Reading report: {xml_file}")
        all_failures.extend(parse_junit_xml(xml_file))

    if not all_failures:
        print("[AI Test Analyzer] All test cases passed or no failures detected!")
        summary = (
            "### ✅ AI Test Suite Verification\n\n"
            "- **Status**: 100% Passed\n"
            "- **Analysis**: No test failures or assertion exceptions observed in execution reports."
        )
        with open("ai_test_analysis_report.md", "w", encoding="utf-8") as f:
            f.write(summary)
        return

    print(f"[AI Test Analyzer] Found {len(all_failures)} failing test cases. Generating AI analysis...")

    # Build prompt context
    failures_summary = []
    for idx, f in enumerate(all_failures[:5], 1):  # Cap at top 5 to keep context focused
        failures_summary.append(
            f"Test Case #{idx}: {f['classname']}::{f['name']}\n"
            f"File: {f['file']}\n"
            f"Error Message: {f['message']}\n"
            f"Stack Trace:\n{f['trace'][-800:]}\n"
        )

    user_prompt = "Failed Test Cases:\n\n" + "\n---\n".join(failures_summary)

    analysis_output = config.complete_prompt(SYSTEM_PROMPT, user_prompt, max_tokens=1800)

    report_content = (
        f"## 🚨 AI Test Failure Diagnostic Report\n\n"
        f"**Failed Tests Detected**: {len(all_failures)}\n\n"
        f"{analysis_output}\n"
    )

    output_file = "ai_test_analysis_report.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"[AI Test Analyzer] Diagnostic report written to {output_file}")
    print("\n" + "=" * 60)
    print(report_content)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
