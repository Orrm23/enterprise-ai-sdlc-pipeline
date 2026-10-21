# Enterprise AI-Augmented SDLC Pipeline for Azure DevOps

This repository demonstrates how high-performing engineering organizations (e.g., Microsoft, Google, Meta, Stripe) systematically integrate Artificial Intelligence across every phase of the Software Development Life Cycle (SDLC):

$$\text{Planning} \longrightarrow \text{Coding} \longrightarrow \text{Testing} \longrightarrow \text{Debugging} \longrightarrow \text{Deployment}$$

---

## 🏗️ Architecture Overview

The pipeline implements an end-to-end, multi-stage Azure DevOps pipeline with deterministic AI governance gates:

```
[ Git Push / PR ]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│ Stage 1: Validate & Plan                               │
│ - Flake8 Linting & Clean Architecture Check            │
│ - Bandit Static Application Security Testing (SAST)   │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ Stage 2: Build & Automated Testing                     │
│ - Pytest execution with JUnit XML & Coverage artifacts │
│ - AI Test Failure Analyzer (ai_test_analyzer.py)       │
│ - Autonomous AI Root Cause Analysis on failure (RCA)   │
│ - Auto-creation of Azure Boards Bug Work Items         │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ Stage 3: AI PR Review & Threat Modeling (PR Trigger)   │
│ - Unified Git Diff extraction                          │
│ - OWASP Top 10 & Architectural evaluation              │
│ - Automated thread comment posted to Azure DevOps PR   │
│ - Optional merge blocking on CRITICAL findings         │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ Stage 4: Deploy Staging & AI Release Management        │
│ - Automated AI Release Notes & Risk Score              │
│ - Container build & Staging deployment                 │
│ - Post-deployment health verification                  │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ Stage 5: Canary Rollout & AI Telemetry Gate (Prod)     │
│ - Canary deployment (10% traffic routing)              │
│ - Real-time metrics comparison (Error rate, p95/p99)   │
│ - AI GO / NO-GO decision engine                        │
│ - Automated instant rollback if anomalies detected     │
└────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

- [`azure-pipelines.yml`](azure-pipelines.yml): Master multi-stage Azure DevOps pipeline orchestrator.
- [`.azure-devops/templates/`](.azure-devops/templates/):
  - [`stage-validate.yml`](.azure-devops/templates/stage-validate.yml): Linting, SAST, and spec validation.
  - [`stage-build-test.yml`](.azure-devops/templates/stage-build-test.yml): Test execution, AI diagnostics, and failure RCA.
  - [`stage-ai-pr-review.yml`](.azure-devops/templates/stage-ai-pr-review.yml): PR code reviewer posting to Azure DevOps PR threads.
  - [`stage-deploy-staging.yml`](.azure-devops/templates/stage-deploy-staging.yml): Staging release and AI change digest.
  - [`stage-canary-prod.yml`](.azure-devops/templates/stage-canary-prod.yml): Canary analysis and automated rollback decision gate.
- [`ai_pipeline_engine/`](ai_pipeline_engine/):
  - [`config.py`](ai_pipeline_engine/config.py): Unified client supporting Azure OpenAI Service and OpenAI with dry-run fallback.
  - [`ai_pr_reviewer.py`](ai_pipeline_engine/ai_pr_reviewer.py): Automated PR code reviewer via Azure DevOps REST API.
  - [`ai_test_analyzer.py`](ai_pipeline_engine/ai_test_analyzer.py): JUnit XML parser and automated test fix generator.
  - [`ai_rca_engine.py`](ai_pipeline_engine/ai_rca_engine.py): Autonomous Root Cause Analysis & Azure Boards Bug creator.
  - [`ai_deployment_verifier.py`](ai_pipeline_engine/ai_deployment_verifier.py): Canary telemetry evaluator with automated rollback triggers.
  - [`ai_release_notes.py`](ai_pipeline_engine/ai_release_notes.py): Commit log summarizer and blast-radius calculator.
- [`src/`](src/): Production FastAPI Order Processing Microservice.
- [`tests/`](tests/): Unit and integration tests.

---

## ⚙️ Azure DevOps Setup Guide

### 1. Configure Variable Group
In Azure DevOps, navigate to **Pipelines** > **Library** > **+ Variable group**:
- Name: `Enterprise-AI-DevOps-Secrets`
- Add the following variables:
  - `AZURE_OPENAI_ENDPOINT`: e.g. `https://<your-openai-resource>.openai.azure.com/`
  - `AZURE_OPENAI_API_KEY`: Secret value
  - `AZURE_OPENAI_DEPLOYMENT_NAME`: `gpt-4o` (or preferred deployment)
  - `AZURE_OPENAI_API_VERSION`: `2024-06-01`
  - `ENFORCE_AI_GATES`: `false` (set to `true` to fail builds on Critical AI findings)

### 2. Enable Build Service Permissions for PR Comments & Boards
To allow the pipeline to post comments on Pull Requests and create Bug Work Items:
1. Navigate to **Project Settings** > **Repositories** > Select your repository.
2. Under **Security**, find **Project Collection Build Service (<your-org>)**.
3. Set the following to **Allow**:
   - **Contribute to pull requests**: Allow
   - **Create work items**: Allow

---

## 🧪 Local Testing

```bash
# 1. Activate environment
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run test suite
pytest --junitxml=test-results.xml tests/

# 4. Run AI PR Reviewer locally
python -m ai_pipeline_engine.ai_pr_reviewer

# 5. Run AI Canary Gate verifier
python -m ai_pipeline_engine.ai_deployment_verifier
```
