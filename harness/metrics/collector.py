"""Per-step metric collection during experiment runs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness.config import (
    ConditionID,
    ExperimentTrace,
    MessageType,
    TraceMessage,
    TraceOutcome,
)


@dataclass
class StepMetrics:
    """Metrics captured at each step of an agent trace."""

    step: int
    message_type: MessageType
    language: str
    token_count_input: int
    token_count_output: int
    latency_ms: float
    tool_call_correct: bool | None = None


class MetricCollector:
    """Collects metrics during an experiment run and writes traces to disk.

    Usage:
        collector = MetricCollector(experiment_id, benchmark, condition, model)
        collector.start_task(task_id, seed)
        collector.record_message(step, role, message_type, language, content, ...)
        collector.end_task(success, ...)
        collector.flush(output_dir)
    """

    def __init__(
        self,
        experiment_id: str,
        benchmark: str,
        condition: ConditionID,
        model: str,
    ):
        self.experiment_id = experiment_id
        self.benchmark = benchmark
        self.condition = condition
        self.model = model
        self._current_trace: ExperimentTrace | None = None
        self._traces: list[ExperimentTrace] = []
        self._task_start_time: float = 0.0

    def start_task(self, task_id: str, seed: int) -> None:
        self._current_trace = ExperimentTrace(
            experiment_id=self.experiment_id,
            benchmark=self.benchmark,
            condition=self.condition,
            model=self.model,
            task_id=task_id,
            seed=seed,
        )
        self._task_start_time = time.monotonic()

    def record_message(
        self,
        step: int,
        role: str,
        message_type: MessageType,
        language: str,
        content: str,
        token_count_input: int = 0,
        token_count_output: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        if self._current_trace is None:
            raise RuntimeError("Call start_task() before recording messages")

        msg = TraceMessage(
            step=step,
            role=role,
            message_type=message_type,
            language=language,
            content=content,
            token_count_input=token_count_input,
            token_count_output=token_count_output,
            latency_ms=latency_ms,
        )
        self._current_trace.messages.append(msg)

    def end_task(
        self,
        success: bool,
        tool_calls_correct: int = 0,
        tool_calls_total: int = 0,
        retries: int = 0,
        safety_failures: int = 0,
    ) -> ExperimentTrace:
        if self._current_trace is None:
            raise RuntimeError("Call start_task() before end_task()")

        total_tokens = sum(
            m.token_count_input + m.token_count_output
            for m in self._current_trace.messages
        )
        total_latency = time.monotonic() - self._task_start_time

        self._current_trace.outcome = TraceOutcome(
            success=success,
            tool_calls_correct=tool_calls_correct,
            tool_calls_total=tool_calls_total,
            retries=retries,
            safety_failures=safety_failures,
            total_tokens=total_tokens,
            total_latency_ms=total_latency * 1000,
        )

        trace = self._current_trace
        self._traces.append(trace)
        self._current_trace = None
        return trace

    def flush(self, output_dir: str | Path) -> Path:
        """Write all collected traces to a JSONL file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = (
            output_dir
            / self.benchmark
            / self.condition.value
            / f"{self.experiment_id}.jsonl"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            for trace in self._traces:
                f.write(json.dumps(trace.to_dict()) + "\n")

        return output_path

    def summary(self) -> dict[str, Any]:
        """Generate summary statistics across all collected traces."""
        if not self._traces:
            return {"error": "No traces collected"}

        outcomes = [t.outcome for t in self._traces if t.outcome]
        return {
            "experiment_id": self.experiment_id,
            "benchmark": self.benchmark,
            "condition": self.condition.value,
            "model": self.model,
            "task_count": len(self._traces),
            "success_rate": sum(1 for o in outcomes if o.success) / max(1, len(outcomes)),
            "avg_tokens": sum(o.total_tokens for o in outcomes) / max(1, len(outcomes)),
            "avg_latency_ms": sum(o.total_latency_ms for o in outcomes) / max(1, len(outcomes)),
            "total_retries": sum(o.retries for o in outcomes),
            "total_safety_failures": sum(o.safety_failures for o in outcomes),
            "tool_correctness": (
                sum(o.tool_calls_correct for o in outcomes)
                / max(1, sum(o.tool_calls_total for o in outcomes))
            ),
        }
