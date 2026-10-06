"""Frozen domain records for executable memory-to-action episodes."""

from __future__ import annotations

import hashlib
import json
import math
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class MemoryStratum(StrEnum):
    ACTIVE_CORE = "active_core"
    INACTIVE_ARCHIVE = "inactive_archive"
    TEMPORAL_GRAPH = "temporal_graph"
    PROACTIVE_TOOL = "proactive_tool"
    ORACLE_CONTEXT = "oracle_context"


class EventKind(StrEnum):
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    ACCESS = "access"
    DISTRACTOR = "distractor"
    OBSERVE = "observe"
    QUERY = "query"


class MemoryBudget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    active_slots: int = Field(default=4, ge=1)
    max_archive_reads: int = Field(default=1, ge=0)
    retrieval_top_k: int = Field(default=4, ge=1)
    max_injected_tokens: int = Field(default=256, ge=1)


class MemoryEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    step: int = Field(ge=0)
    kind: EventKind
    entity_id: str = Field(min_length=1)
    key: str = Field(min_length=1)
    value: str | None = None
    source_quality: float = Field(default=0.5, ge=0.0, le=1.0)
    contradiction_count: int = Field(default=0, ge=0)
    record_cost: int = Field(default=1, ge=1)
    graph_degree: int = Field(default=0, ge=0)
    proactive_hint: bool = False
    candidate: bool = False
    untrusted: bool = True
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_value(self) -> MemoryEvent:
        if (
            self.kind in {EventKind.WRITE, EventKind.UPDATE, EventKind.OBSERVE}
            and self.value is None
        ):
            raise ValueError(f"{self.kind.value} event requires a value")
        if not math.isfinite(self.source_quality):
            raise ValueError("source_quality must be finite")
        return self


class MemoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: str
    entity_id: str
    key: str
    value: str
    written_step: int = Field(ge=0)
    last_access_step: int = Field(ge=0)
    source_quality: float = Field(ge=0.0, le=1.0)
    contradiction_count: int = Field(ge=0)
    candidate: bool = False
    valid: bool = True
    untrusted: bool = True
    residency: Literal["active", "archive", "graph"]


class MemoryOracle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["answer", "tool"]
    lookup_key: str = Field(min_length=1)
    expected_value: str = Field(min_length=1)
    tool_name: str | None = None
    tool_arguments: dict[str, JsonValue] | None = None
    tool_input_schema: dict[str, JsonValue] | None = None
    safety_case: str | None = None
    forbidden_output_substrings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_mode(self) -> MemoryOracle:
        if self.mode == "tool" and (
            self.tool_name is None
            or self.tool_arguments is None
            or self.tool_input_schema is None
        ):
            raise ValueError(
                "tool oracle requires tool_name, tool_arguments, and tool_input_schema"
            )
        if self.mode == "answer" and (
            self.tool_name is not None
            or self.tool_arguments is not None
            or self.tool_input_schema is not None
        ):
            raise ValueError("answer oracle cannot define tool fields")
        if self.safety_case is None and self.forbidden_output_substrings:
            raise ValueError("forbidden output substrings require a safety_case")
        if self.safety_case is not None and not self.forbidden_output_substrings:
            raise ValueError("safety_case requires at least one forbidden output substring")
        return self


class MemoryTask(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    source_schema_version: str = Field(
        default="memory-events-v1", pattern=r"^[a-z0-9][a-z0-9._-]*$"
    )
    task_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    group_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    session_id: str = Field(min_length=1)
    stratum: MemoryStratum
    events: tuple[MemoryEvent, ...]
    candidate_id: str = Field(min_length=1)
    write_step: int = Field(ge=0)
    eligibility_step: int = Field(ge=1)
    total_steps: int = Field(ge=2)
    query: str = Field(min_length=1)
    oracle: MemoryOracle
    budget: MemoryBudget
    suffix_variant_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    task_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_task(self) -> MemoryTask:
        if self.write_step >= self.eligibility_step:
            raise ValueError("write_step must precede eligibility_step")
        if len(self.events) != self.total_steps:
            raise ValueError("events must contain exactly total_steps entries")
        steps = [event.step for event in self.events]
        if steps != list(range(self.total_steps)):
            raise ValueError("event steps must be contiguous from zero")
        candidates = [event for event in self.events if event.candidate]
        if len(candidates) != 1 or candidates[0].event_id != self.candidate_id:
            raise ValueError("task must contain exactly the registered candidate")
        if candidates[0].step != self.write_step:
            raise ValueError("candidate event must occur at write_step")
        if self.events[-1].kind is not EventKind.QUERY:
            raise ValueError("final event must be the query")
        payload = self.model_dump(mode="json", exclude={"task_sha256"})
        computed = sha256_text(canonical_json(payload))
        if computed != self.task_sha256:
            raise ValueError("task_sha256 does not bind the task")
        return self


def seal_task(payload: dict[str, Any]) -> MemoryTask:
    draft = dict(payload)
    draft["task_sha256"] = "0" * 64
    unsealed = MemoryTask.model_construct(**draft)
    serializable = unsealed.model_dump(mode="json", exclude={"task_sha256"})
    draft["task_sha256"] = sha256_text(canonical_json(serializable))
    return MemoryTask.model_validate(draft)
