"""SWE-bench Verified adapter — human-validated software engineering benchmark.

500 human-validated real GitHub issues. Code-heavy stress test where
internal language switching faces maximum friction from file paths,
stack traces, identifiers, and code context.

Repo: https://github.com/SWE-bench/SWE-bench
Top performers: GPT-5.5 (82.6%), Claude Opus 4.7 (82%).
"""

from __future__ import annotations

from typing import Any

from harness.benchmarks.base import BenchmarkAdapter, BenchmarkTask, TaskResult


class SWEBenchVerifiedAdapter(BenchmarkAdapter):
    """Adapter for SWE-bench Verified.

    The hardest test for language routing: code, stack traces, file paths,
    and domain-specific identifiers resist compression and translation.
    Expected to show the narrowest gap between language conditions.

    TODO: Clone SWE-bench, implement verified subset loading.
    """

    def __init__(self, data_dir: str = "raw/baselines/swe-bench"):
        self.data_dir = data_dir

    @property
    def name(self) -> str:
        return "swe_bench_verified"

    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        raise NotImplementedError(
            "SWE-bench Verified adapter not yet implemented. "
            "Clone https://github.com/SWE-bench/SWE-bench"
        )

    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        raise NotImplementedError("SWE-bench Verified evaluation not yet implemented.")

    def get_system_prompt(self) -> str:
        return (
            "You are a software engineer fixing a real bug in an open-source repository. "
            "Read the issue, understand the codebase, identify the root cause, and "
            "produce a minimal patch that resolves the issue."
        )
