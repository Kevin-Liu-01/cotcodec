"""Amazing Agent Race adapter — DAG puzzle navigation benchmark.

1,400 directed acyclic graph puzzle instances. Key finding: navigation
errors (27-52% of trials) dominate agent failures, while tool-use
errors stay below 17%. Decomposes failure into navigation vs. tool use.

Paper: arXiv 2604.10261
"""

from __future__ import annotations

from typing import Any

from harness.benchmarks.base import BenchmarkAdapter, BenchmarkTask, TaskResult


class AgentRaceAdapter(BenchmarkAdapter):
    """Adapter for The Amazing Agent Race.

    Uniquely useful for CoTCodec because it decomposes failure modes:
    navigation (planning, memory) vs. tool use (execution). This maps
    directly to our orchestration variables: planning depth (V6),
    memory policy (V3) vs. tool scheduling (V10), verification (V8).

    TODO: Clone dataset from paper supplementary material.
    """

    def __init__(self, data_dir: str = "raw/baselines/agent-race"):
        self.data_dir = data_dir

    @property
    def name(self) -> str:
        return "agent_race"

    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        raise NotImplementedError(
            "Agent Race adapter not yet implemented. "
            "See arXiv 2604.10261 for dataset."
        )

    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        raise NotImplementedError("Agent Race evaluation not yet implemented.")

    def get_system_prompt(self) -> str:
        return (
            "You are navigating a complex task graph. At each node, choose the "
            "correct action and navigate to the next step. Use available tools "
            "to gather information and make decisions."
        )
