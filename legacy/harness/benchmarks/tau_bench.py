"""τ-bench adapter — Tool-Agent-User interaction benchmark.

τ-bench evaluates tool-using agents on argument correctness and policy
compliance in realistic customer service scenarios.

Repo: https://github.com/sierra-research/tau-bench
"""

from __future__ import annotations

from typing import Any

from harness.benchmarks.base import BenchmarkAdapter, BenchmarkTask, TaskResult


class TauBenchAdapter(BenchmarkAdapter):
    """Adapter for τ-bench (tool-agent-user interaction benchmark).

    TODO: Implement once tau-bench is cloned and dependencies resolved.
    This stub defines the interface; implementation follows the benchmark's
    native evaluation protocol.
    """

    def __init__(self, data_dir: str = "raw/baselines/tau-bench"):
        self.data_dir = data_dir

    @property
    def name(self) -> str:
        return "tau_bench"

    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        raise NotImplementedError(
            "tau-bench adapter not yet implemented. "
            "Clone https://github.com/sierra-research/tau-bench to raw/baselines/tau-bench "
            "and implement task loading from their dataset format."
        )

    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        raise NotImplementedError("tau-bench evaluation not yet implemented.")

    def get_system_prompt(self) -> str:
        return (
            "You are a customer service agent. Follow company policies exactly. "
            "Use the provided tools to look up information and take actions. "
            "Be accurate with tool arguments — incorrect arguments cause real problems."
        )
