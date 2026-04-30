"""Shared configuration for the CoTCodec evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from harness.yaml_utils import load_yaml_file


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
    ENGLISH_ONLY_LOW_EFFORT = "english_only_low_effort"
    ENGLISH_ONLY_NO_THINKING_CACHE = "english_only_no_thinking_cache"
    ENGLISH_ONLY_25WORD_LIMIT = "english_only_25word_limit"
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


@dataclass(frozen=True)
class ExperimentRunSpec:
    """A concrete run slice expanded from an experiment config."""

    group: str
    model: str
    conditions: list[ConditionID]


@dataclass
class ExperimentConfig:
    name: str
    description: str
    benchmark: str
    conditions: list[ConditionID] = field(default_factory=list)
    model: str | None = None
    models: list[str] = field(default_factory=list)
    run_specs: list[ExperimentRunSpec] = field(default_factory=list)
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
        raw = load_yaml_file(path)

        known_fields = {
            "name",
            "description",
            "benchmark",
            "model",
            "tasks",
            "seeds",
            "metrics",
        }

        raw_conditions = raw.pop("conditions", [])
        raw_models = raw.pop("models", None)
        raw_run_groups = raw.pop("run_groups", None)

        condition_groups = cls._parse_conditions(raw_conditions)
        run_specs = cls._build_run_specs(
            model=raw.get("model"),
            models=raw_models,
            condition_groups=condition_groups,
            raw_run_groups=raw_run_groups,
        )

        raw["conditions"] = condition_groups.get("default", [])
        raw["models"] = (
            list(raw_models)
            if isinstance(raw_models, list)
            else [raw["model"]] if raw.get("model") else []
        )
        raw["run_specs"] = run_specs

        extra = {
            key: value
            for key, value in raw.items()
            if key not in known_fields | {"conditions", "models", "run_specs"}
        }

        filtered = {key: raw[key] for key in raw if key in known_fields | {"conditions", "models", "run_specs"}}
        filtered["extra"] = extra
        return cls(**filtered)

    @staticmethod
    def _parse_conditions(
        raw_conditions: list[str] | dict[str, list[str]]
    ) -> dict[str, list[ConditionID]]:
        if isinstance(raw_conditions, dict):
            return {
                name: [ConditionID(condition) for condition in values]
                for name, values in raw_conditions.items()
            }
        return {
            "default": [ConditionID(condition) for condition in raw_conditions]
        }

    @classmethod
    def _build_run_specs(
        cls,
        model: str | None,
        models: list[str] | dict[str, list[str]] | None,
        condition_groups: dict[str, list[ConditionID]],
        raw_run_groups: list[dict[str, Any]] | None,
    ) -> list[ExperimentRunSpec]:
        if raw_run_groups:
            return [
                ExperimentRunSpec(
                    group=group["name"],
                    model=model_name,
                    conditions=[ConditionID(c) for c in group["conditions"]],
                )
                for group in raw_run_groups
                for model_name in group["models"]
            ]

        if isinstance(models, dict):
            run_specs: list[ExperimentRunSpec] = []
            for group_name, group_models in models.items():
                condition_key = cls._match_condition_group(group_name, condition_groups)
                for model_name in group_models:
                    run_specs.append(
                        ExperimentRunSpec(
                            group=group_name,
                            model=model_name,
                            conditions=condition_groups[condition_key],
                        )
                    )
            return run_specs

        if isinstance(models, list):
            return [
                ExperimentRunSpec(
                    group="default",
                    model=model_name,
                    conditions=condition_groups["default"],
                )
                for model_name in models
            ]

        if model is not None:
            return [
                ExperimentRunSpec(
                    group="default",
                    model=model,
                    conditions=condition_groups["default"],
                )
            ]

        raise ValueError("Experiment config must define `model`, `models`, or `run_groups`.")

    @staticmethod
    def _match_condition_group(
        model_group: str,
        condition_groups: dict[str, list[ConditionID]],
    ) -> str:
        if model_group in condition_groups:
            return model_group

        matches = [
            name
            for name in condition_groups
            if model_group == name or model_group.endswith(f"_{name}")
        ]
        if len(matches) == 1:
            return matches[0]

        raise ValueError(
            f"Could not infer condition group for model group `{model_group}`. "
            f"Available condition groups: {sorted(condition_groups)}"
        )

    def iter_run_specs(self) -> list[ExperimentRunSpec]:
        """Return concrete (group, model, conditions) slices for execution."""
        return list(self.run_specs)


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
    run_group: str | None = None
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
            "run_group": self.run_group,
            "messages": [m.to_dict() for m in self.messages],
            "outcome": self.outcome.to_dict() if self.outcome else None,
        }
