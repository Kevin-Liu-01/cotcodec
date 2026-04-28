"""Toolathlon adapter — multi-system workflow orchestration benchmark.

108 tasks across real software systems (Google Calendar, Notion, WooCommerce,
BigQuery, Kubernetes). Each task requires ~20 tool interactions across
multiple systems. Measures complex workflow execution.

Repo/Docs: https://www.bracai.eu/post/toolathlon-benchmark
Top performer: GPT-5.4 at 54.6%.
"""

from __future__ import annotations

from typing import Any

from harness.benchmarks.base import BenchmarkAdapter, BenchmarkTask, TaskResult


class ToolathlonAdapter(BenchmarkAdapter):
    """Adapter for Toolathlon (Tool Decathlon).

    Tests complex multi-system workflows — the kind of real-world agent
    tasks where orchestration variables have the biggest impact.

    TODO: Clone dataset, implement task loading and evaluation.
    """

    def __init__(self, data_dir: str = "raw/baselines/toolathlon"):
        self.data_dir = data_dir

    @property
    def name(self) -> str:
        return "toolathlon"

    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        raise NotImplementedError(
            "Toolathlon adapter not yet implemented. "
            "See https://www.bracai.eu/post/toolathlon-benchmark for dataset."
        )

    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        raise NotImplementedError("Toolathlon evaluation not yet implemented.")

    def get_system_prompt(self) -> str:
        return (
            "You are an AI agent orchestrating tasks across multiple software systems. "
            "Plan your workflow, use the correct tools in sequence, handle errors, "
            "and complete multi-step operations accurately."
        )
