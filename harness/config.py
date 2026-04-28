"""Shared configuration for the CoTCodec evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class MessageType(str, Enum):
    PLANNER_NOTE = "planner_note"
    SUBTASK_HANDOFF = "subtask_handoff"
    MEMORY_UPDATE = "memory_update"
    RETRY_DIAGNOSIS = "retry_diagnosis"
    COORDINATOR_MSG = "coordinator_msg"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    USER_RESPONSE = "user_response"

    @property
    def is_variable(self) -> bool:
        return self in {
            MessageType.PLANNER_NOTE,
            MessageType.SUBTASK_HANDOFF,
            MessageType.MEMORY_UPDATE,
            MessageType.RETRY_DIAGNOSIS,
            MessageType.COORDINATOR_MSG,
        }


class ConditionID(str, Enum):
    ENGLISH_ONLY = "english_only"
    INTERNAL_CHINESE = "internal_chinese"
    CONTROLLED_CHINESE = "controlled_chinese"
    ENGLISH_COMPRESSED = "english_compressed"
    STRUCTURED_ENGLISH = "structured_english"
    DYNAMIC_ROUTER = "dynamic_router"
    POLISH_STRESS = "polish_stress"


VARIABLE_MESSAGE_TYPES = frozenset(
    mt for mt in MessageType if mt.is_variable
)

FIXED_MESSAGE_TYPES = frozenset(
    mt for mt in MessageType if not mt.is_variable
)


@dataclass
class ExperimentConfig:
    name: str
    description: str
    benchmark: str
    conditions: list[ConditionID]
    model: str
    tasks: int | list[str] = 5
    seeds: list[int] = field(default_factory=lambda: [42, 43, 44])
    metrics: list[str] = field(default_factory=lambda: [
        "total_billed_tokens",
        "task_success_rate",
        "tool_call_exact_match",
        "wall_clock_latency_ms",
        "cost_usd",
    ])
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ExperimentConfig:
        with open(path) as f:
            raw = yaml.safe_load(f)
        conditions = [ConditionID(c) for c in raw.pop("conditions", [])]
        return cls(conditions=conditions, **raw)


@dataclass
class TraceMessage:
    step: int
    role: str
    message_type: MessageType
    language: str
    content: str
    token_count_input: int = 0
    token_count_output: int = 0
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "role": self.role,
            "type": self.message_type.value,
            "language": self.language,
            "content": self.content,
            "token_count_input": self.token_count_input,
            "token_count_output": self.token_count_output,
            "latency_ms": self.latency_ms,
        }


@dataclass
class TraceOutcome:
    success: bool
    tool_calls_correct: int = 0
    tool_calls_total: int = 0
    retries: int = 0
    safety_failures: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "tool_calls_correct": self.tool_calls_correct,
            "tool_calls_total": self.tool_calls_total,
            "retries": self.retries,
            "safety_failures": self.safety_failures,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "cost_usd": self.cost_usd,
        }


@dataclass
class ExperimentTrace:
    experiment_id: str
    benchmark: str
    condition: ConditionID
    model: str
    task_id: str
    seed: int
    messages: list[TraceMessage] = field(default_factory=list)
    outcome: TraceOutcome | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "benchmark": self.benchmark,
            "condition": self.condition.value,
            "model": self.model,
            "task_id": self.task_id,
            "seed": self.seed,
            "messages": [m.to_dict() for m in self.messages],
            "outcome": self.outcome.to_dict() if self.outcome else None,
        }
