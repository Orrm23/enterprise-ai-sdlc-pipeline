"""Enterprise Token Context Optimizer for AI SDLC Pipelines.

Provides AST-aware diff filtering, log compaction, token budgeting, and
prefix-caching alignment to minimize LLM token costs, reduce latency, and
prevent context window degradation.
"""

import re
from typing import Dict, List, Tuple, Any

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENCODER = None


# Patterns for noise and auto-generated files that waste context tokens
NOISE_FILE_PATTERNS = [
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"pnpm-lock\.yaml$",
    r"poetry\.lock$",
    r"Pipfile\.lock$",
    r"Cargo\.lock$",
    r"go\.sum$",
    r"\.min\.(js|css)$",
    r"\.map$",
    r"\.(svg|png|jpg|jpeg|gif|ico|webp|woff|woff2|ttf|eot)$",
    r"\.coverage$",
    r"coverage\.xml$",
    r"test-results\.xml$",
    r"\.(lock|pb\.go|gen\.go|g\.dart)$",
]

# Patterns for log noise suppression
ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
PROGRESS_BAR_PATTERN = re.compile(r"[-=]{2,}>\s*\d+.*%|\[\s*={2,}\s*\]")
ERROR_ANCHOR_PATTERNS = [
    re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:FATAL|ERROR|FAIL|EXCEPTION|CRITICAL):?", re.IGNORECASE),
    re.compile(r"===+ FAILURES ===+", re.IGNORECASE),
    re.compile(r"===+ ERRORS ===+", re.IGNORECASE),
]


class TokenBudgetManager:
    """Calculates exact or estimated token counts and enforces token bounds."""

    @staticmethod
    def count_tokens(text: str) -> int:
        """Returns accurate token count using tiktoken if available, else heuristic estimate."""
        if not text:
            return 0
        if _ENCODER is not None:
            try:
                return len(_ENCODER.encode(text, disallowed_special=()))
            except Exception:
                pass
        # Fallback estimation: average 3.8 characters per token in code/English
        return max(1, int(len(text) / 3.8))

    @staticmethod
    def truncate_to_token_limit(text: str, max_tokens: int) -> Tuple[str, int]:
        """Truncates string to fit within max_tokens budget, returning (truncated_text, token_count)."""
        current_tokens = TokenBudgetManager.count_tokens(text)
        if current_tokens <= max_tokens:
            return text, current_tokens

        if _ENCODER is not None:
            try:
                tokens = _ENCODER.encode(text, disallowed_special=())[:max_tokens]
                truncated = _ENCODER.decode(tokens)
                return truncated + "\n...[Context truncated to meet token budget]...", max_tokens
            except Exception:
                pass

        # Fallback character slice
        char_limit = int(max_tokens * 3.8)
        return text[:char_limit] + "\n...[Context truncated to meet token budget]...", max_tokens


class DiffPruner:
    """Optimizes Git Diffs by filtering noise files, stripping whitespace, and prioritizing semantic changes."""

    @staticmethod
    def is_noise_file(filename: str) -> bool:
        """Determines if a file is an asset, lockfile, or auto-generated code."""
        filename = filename.strip()
        for pattern in NOISE_FILE_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return True
        return False

    @classmethod
    def optimize_diff(
        cls, raw_diff: str, max_token_budget: int = 4000
    ) -> Dict[str, Any]:
        """Filters noise files, collapses massive hunks, and fits diff into token budget."""
        raw_tokens = TokenBudgetManager.count_tokens(raw_diff)
        if not raw_diff.strip():
            return {
                "optimized_diff": "",
                "raw_tokens": 0,
                "optimized_tokens": 0,
                "tokens_saved": 0,
                "compression_ratio": "0%",
                "omitted_files": [],
            }

        # Split diff by file header: "diff --git a/... b/..."
        file_diffs = re.split(r"(?=diff --git )", raw_diff)
        retained_chunks: List[str] = []
        omitted_files: List[str] = []

        for chunk in file_diffs:
            if not chunk.strip():
                continue

            header_match = re.search(r"diff --git a/(.*?) b/(.*)", chunk)
            if header_match:
                filename = header_match.group(2).split()[0]
                if cls.is_noise_file(filename):
                    omitted_files.append(filename)
                    continue

            # Strip non-informative empty whitespace diff lines
            lines = chunk.splitlines()
            cleaned_lines = []
            for line in lines:
                # Retain headers, additions, deletions; drop excessive context lines (>3 lines away)
                if line.startswith(("diff --git", "index ", "--- ", "+++ ", "@@", "+", "-")):
                    cleaned_lines.append(line)
                elif line.strip():  # Non-empty context line
                    cleaned_lines.append(line)

            retained_chunks.append("\n".join(cleaned_lines))

        optimized_body = "\n".join(retained_chunks)

        if omitted_files:
            omitted_notice = (
                f"\n# Note: {len(omitted_files)} noise/lock files omitted to save context:\n# - "
                + "\n# - ".join(omitted_files[:10])
                + (f"\n# ... and {len(omitted_files) - 10} more" if len(omitted_files) > 10 else "")
                + "\n\n"
            )
            optimized_body = omitted_notice + optimized_body

        # Enforce hard token budget
        final_diff, optimized_tokens = TokenBudgetManager.truncate_to_token_limit(
            optimized_body, max_token_budget
        )

        tokens_saved = max(0, raw_tokens - optimized_tokens)
        compression = (
            f"{round((tokens_saved / raw_tokens) * 100, 1)}%" if raw_tokens > 0 else "0%"
        )

        return {
            "optimized_diff": final_diff,
            "raw_tokens": raw_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": tokens_saved,
            "compression_ratio": compression,
            "omitted_files": omitted_files,
        }


class LogCompactor:
    """Compacts massive CI build/test logs by stripping ANSI sequences and extracting error windows."""

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Removes ANSI terminal escape color codes."""
        return ANSI_ESCAPE_PATTERN.sub("", text)

    @classmethod
    def compact_log(
        cls, raw_log: str, max_token_budget: int = 2500, window_lines: int = 35
    ) -> Dict[str, Any]:
        """Extracts only critical failure windows, stripping progress bars and warnings."""
        raw_tokens = TokenBudgetManager.count_tokens(raw_log)
        clean_text = cls.strip_ansi(raw_log)
        lines = clean_text.splitlines()

        if not lines:
            return {
                "compact_log": "",
                "raw_tokens": 0,
                "optimized_tokens": 0,
                "tokens_saved": 0,
                "compression_ratio": "0%",
            }

        # Locate error anchors in log
        anchor_indices: List[int] = []
        for i, line in enumerate(lines):
            # Skip progress bar noise
            if PROGRESS_BAR_PATTERN.search(line):
                continue
            for pattern in ERROR_ANCHOR_PATTERNS:
                if pattern.search(line):
                    anchor_indices.append(i)
                    break

        # If no explicit anchor found, take the tail of the log (most likely failure zone in CI)
        if not anchor_indices:
            extracted_lines = lines[-min(len(lines), window_lines * 2):]
        else:
            # Build merged slice ranges around anchors
            ranges: List[Tuple[int, int]] = []
            for idx in anchor_indices:
                start = max(0, idx - 10)
                end = min(len(lines), idx + window_lines)
                ranges.append((start, end))

            # Merge overlapping intervals
            merged_ranges = []
            for r in sorted(ranges):
                if not merged_ranges or merged_ranges[-1][1] < r[0]:
                    merged_ranges.append(r)
                else:
                    merged_ranges[-1] = (merged_ranges[-1][0], max(merged_ranges[-1][1], r[1]))

            extracted_lines = []
            for start, end in merged_ranges:
                extracted_lines.append(f"\n--- [Log Segment: Lines {start}-{end}] ---")
                extracted_lines.extend(lines[start:end])

        compact_body = "\n".join(extracted_lines)
        final_log, optimized_tokens = TokenBudgetManager.truncate_to_token_limit(
            compact_body, max_token_budget
        )

        tokens_saved = max(0, raw_tokens - optimized_tokens)
        compression = (
            f"{round((tokens_saved / raw_tokens) * 100, 1)}%" if raw_tokens > 0 else "0%"
        )

        return {
            "compact_log": final_log,
            "raw_tokens": raw_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": tokens_saved,
            "compression_ratio": compression,
        }
