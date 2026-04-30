"""OrchVar-Canary — custom benchmark for detecting orchestration regressions.

A small (50-100 tasks), fast-running benchmark specifically designed to be
sensitive to orchestration variable changes. Each task category targets a
specific variable, inspired by the Anthropic April 23 postmortem.

This is a NOVEL contribution of the CoTCodec project — no prior work
builds benchmarks specifically to catch harness-level regressions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.benchmarks.base import BenchmarkAdapter, BenchmarkTask, TaskResult
from harness.metrics.degradation import CANARY_CATEGORIES
from harness.yaml_utils import load_yaml_file


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

    def __init__(self, data_dir: str = "harness/benchmarks/specs"):
        self.data_dir = data_dir
        self.categories = CANARY_CATEGORIES

    @property
    def name(self) -> str:
        return "orchvar_canary"

    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        """Load canary tasks from the repo-local task spec."""
        task_path = Path(self.data_dir) / "orchvar_canary_tasks.yaml"
        if not task_path.exists():
            raise FileNotFoundError(
                f"OrchVar-Canary task spec missing: {task_path}. "
                "Create harness/benchmarks/specs/orchvar_canary_tasks.yaml first."
            )

        raw = load_yaml_file(task_path) or {}

        tasks = [
            CanaryTask(
                task_id=task["task_id"],
                instruction=task["instruction"],
                tools=task.get("tools", []),
                expected_outcome=task.get("expected_outcome"),
                metadata=task.get("metadata", {}),
                category=task["category"],
                target_variable=task["target_variable"],
                expected_failure_mode=task["expected_failure_mode"],
            )
            for task in raw.get("tasks", [])
        ]

        if count is None or count < 0:
            return tasks
        return tasks[:count]

    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        metadata = task.metadata or {}
        return {
            "success": result.success,
            "tool_correctness": (
                result.tool_calls_correct / max(1, result.tool_calls_total)
            ),
            "details": {
                "category": metadata.get("category"),
                "target_variable": metadata.get("target_variable"),
                "expected_failure_mode": metadata.get("expected_failure_mode"),
            },
        }

    def get_system_prompt(self) -> str:
        return (
            "You are an AI assistant completing a task. Follow instructions precisely, "
            "use tools accurately, and maintain context across multiple steps."
        )
