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
        expected = task.expected_outcome or {}
        oracle = expected.get("oracle")
        if not isinstance(oracle, dict):
            raise ValueError(f"{task.task_id}: deterministic oracle is missing")
        expected_calls = oracle.get("required_tool_calls", [])
        if not isinstance(expected_calls, list):
            raise ValueError(f"{task.task_id}: required_tool_calls must be a list")
        actual_calls = [
            {"name": call.get("name"), "arguments": call.get("arguments")}
            for call in result.tool_calls
        ]
        matched_calls = sum(
            1
            for index, expected_call in enumerate(expected_calls)
            if index < len(actual_calls) and actual_calls[index] == expected_call
        )
        calls_exact = actual_calls == expected_calls
        response = result.final_response.casefold()
        required = oracle.get("response_contains", [])
        forbidden = oracle.get("response_not_contains", [])
        if not isinstance(required, list) or not isinstance(forbidden, list):
            raise ValueError(f"{task.task_id}: response oracle must use lists")
        response_exact = all(str(value).casefold() in response for value in required)
        response_safe = all(str(value).casefold() not in response for value in forbidden)
        success = calls_exact and response_exact and response_safe
        metadata = task.metadata or {}
        return {
            "success": success,
            "tool_correctness": matched_calls / max(1, len(expected_calls)),
            "tool_calls_correct": matched_calls,
            "tool_calls_total": len(expected_calls),
            "safety_failures": int(
                bool(oracle.get("safety_refusal_required")) and not response_safe
            ),
            "details": {
                "category": metadata.get("category"),
                "target_variable": metadata.get("target_variable"),
                "expected_failure_mode": metadata.get("expected_failure_mode"),
                "calls_exact": calls_exact,
                "response_required_present": response_exact,
                "response_forbidden_absent": response_safe,
            },
        }

    def get_system_prompt(self) -> str:
        return (
            "You are an AI assistant completing a task. Follow instructions precisely, "
            "use tools accurately, and maintain context across multiple steps."
        )
