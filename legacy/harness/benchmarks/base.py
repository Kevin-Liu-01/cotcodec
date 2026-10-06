"""Abstract benchmark adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class BenchmarkTask:
    """A single task from a benchmark suite."""

    task_id: str
    instruction: str
    tools: list[dict[str, Any]]
    expected_outcome: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class TaskResult:
    """Result of executing a single task."""

    task_id: str
    success: bool
    tool_calls: list[dict[str, Any]]
    tool_calls_correct: int
    tool_calls_total: int
    final_response: str
    retries: int = 0
    safety_failures: int = 0
    metadata: dict[str, Any] | None = None


class BenchmarkAdapter(ABC):
    """Adapter for a benchmark suite.

    Each benchmark adapter must:
    1. Load tasks from the benchmark's native format
    2. Provide tool definitions in a standard format
    3. Evaluate task outcomes against expected results
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def load_tasks(self, count: int | None = None) -> list[BenchmarkTask]:
        """Load tasks from the benchmark. If count is None, load all."""
        ...

    @abstractmethod
    async def evaluate(self, task: BenchmarkTask, result: TaskResult) -> dict[str, Any]:
        """Evaluate a task result against the expected outcome.

        Returns a dict with at minimum:
        - success: bool
        - tool_correctness: float (0-1)
        - details: dict with benchmark-specific evaluation details
        """
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the benchmark's standard system prompt."""
        ...
