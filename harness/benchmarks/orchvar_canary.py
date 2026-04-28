"""OrchVar-Canary — custom benchmark for detecting orchestration regressions.

A small (50-100 tasks), fast-running benchmark specifically designed to be
sensitive to orchestration variable changes. Each task category targets a
specific variable, inspired by the Anthropic April 23 postmortem.

This is a NOVEL contribution of the CoTCodec project — no prior work
builds benchmarks specifically to catch harness-level regressions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harness.benchmarks.base import BenchmarkAdapter, BenchmarkTask, TaskResult
from harness.metrics.degradation import CANARY_CATEGORIES


@dataclass
class CanaryTask(BenchmarkTask):
    """A canary task targeting a specific orchestration variable."""

    category: str = ""
    target_variable: int = 0
    expected_failure_mode: str = ""


class OrchVarCanaryAdapter(BenchmarkAdapter):
    """Custom benchmark for detecting orchestration-level quality regressions.

    Design principles:
    - Small (50-100 tasks) for fast CI-like execution
    - Each task category targets a specific orchestration variable
    - Tasks PASS under good orchestration and FAIL under known-bad changes
    - If the canary dies, you know exactly which variable regressed

    Categories (from degradation.py CANARY_CATEGORIES):
    - reasoning_depth: fails when thinking is too short (V2)
    - context_recall: fails when prior context is lost (V3/V9)
    - verbosity_sensitive: fails when output is too brief (V4)
    - multi_turn_memory: fails when memory is cleared (V3)
    - tool_argument_precision: fails when args drift (V1/V2)
    - safety_canary: fails when refusal is inconsistent (V12)
    """

    def __init__(self, data_dir: str = "raw/baselines/orchvar-canary"):
        self.data_dir = data_dir
        self.categories = CANARY_CATEGORIES

    @property
    def name(self) -> str:
        return "orchvar_canary"

    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        """Load canary tasks.

        TODO: Build the actual task set. For now, return category definitions.
        Task construction should follow these principles:
        1. Each task has a clear pass/fail criterion
        2. Each task targets exactly one orchestration variable
        3. Tasks are fast (single tool call or short trajectory)
        4. Tasks are deterministic (same input → same expected output)
        """
        raise NotImplementedError(
            "OrchVar-Canary tasks not yet built. "
            "See harness/metrics/degradation.py CANARY_CATEGORIES for the spec."
        )

    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        raise NotImplementedError("OrchVar-Canary evaluation not yet implemented.")

    def get_system_prompt(self) -> str:
        return (
            "You are an AI assistant completing a task. Follow instructions precisely, "
            "use tools accurately, and maintain context across multiple steps."
        )
