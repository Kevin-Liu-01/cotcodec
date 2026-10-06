"""API-Bank adapter — tool planning and API usage benchmark.

Repo: https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/api-bank
"""

from __future__ import annotations

from typing import Any

from harness.benchmarks.base import BenchmarkAdapter, BenchmarkTask, TaskResult


class APIBankAdapter(BenchmarkAdapter):
    """Adapter for API-Bank (tool-augmented LLM benchmark).

    TODO: Implement once API-Bank dataset is downloaded.
    """

    def __init__(self, data_dir: str = "raw/baselines/api-bank"):
        self.data_dir = data_dir

    @property
    def name(self) -> str:
        return "api_bank"

    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        raise NotImplementedError(
            "API-Bank adapter not yet implemented. "
            "Clone the dataset to raw/baselines/api-bank."
        )

    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        raise NotImplementedError("API-Bank evaluation not yet implemented.")

    def get_system_prompt(self) -> str:
        return (
            "You are an AI assistant with access to various APIs. "
            "Plan your API calls carefully, use correct arguments, "
            "and combine results to answer the user's question."
        )
