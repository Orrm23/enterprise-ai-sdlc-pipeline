"""Unit tests for Token Context Optimizer."""

import pytest
from ai_pipeline_engine.context_optimizer import (
    TokenBudgetManager,
    DiffPruner,
    LogCompactor,
)


def test_token_budget_manager_counting():
    text = "def calculate_totals(subtotal, discount): return subtotal - discount"
    tokens = TokenBudgetManager.count_tokens(text)
    assert tokens > 0
    assert tokens < 50


def test_diff_pruner_filters_noise_files():
    assert DiffPruner.is_noise_file("package-lock.json") is True
    assert DiffPruner.is_noise_file("poetry.lock") is True
    assert DiffPruner.is_noise_file("bundle.min.js") is True
    assert DiffPruner.is_noise_file("logo.svg") is True
    assert DiffPruner.is_noise_file("src/service.py") is False
    assert DiffPruner.is_noise_file("tests/test_main.py") is False


def test_diff_pruner_optimization():
    raw_diff = (
        "diff --git a/package-lock.json b/package-lock.json\n"
        "index 1111..2222 100644\n"
        "+ {\"name\": \"huge-lockfile-with-10000-tokens\"}\n"
        "diff --git a/src/service.py b/src/service.py\n"
        "index 3333..4444 100644\n"
        "@@ -1,5 +1,5 @@\n"
        "- tax = 0.05\n"
        "+ tax = 0.08\n"
    )
    result = DiffPruner.optimize_diff(raw_diff, max_token_budget=1000)
    assert "package-lock.json" in result["omitted_files"]
    assert "tax = 0.08" in result["optimized_diff"]
    assert result["optimized_tokens"] < result["raw_tokens"]
    assert result["tokens_saved"] > 0


def test_log_compactor_extracts_error_anchor():
    noisy_log = (
        "npm install\n"
        "Downloading [==========>               ] 40%\n"
        "Downloading [=========================>] 100%\n"
        "Running tests...\n"
        "Traceback (most recent call last):\n"
        "  File 'service.py', line 42, in process\n"
        "    raise ValueError('Calculation error')\n"
        "ValueError: Calculation error\n"
        "Build finished with error code 1.\n"
    )
    result = LogCompactor.compact_log(noisy_log, max_token_budget=500, window_lines=5)
    assert "ValueError: Calculation error" in result["compact_log"]
    assert result["optimized_tokens"] > 0
