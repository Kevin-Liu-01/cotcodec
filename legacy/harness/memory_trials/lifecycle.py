"""Deep, task-blind lifecycle contract for stateful memory experiments.

``memory-system-v1`` intentionally compares one final request-to-selection
snapshot.  This module owns the additional ordering and provenance required to
study residency transitions, maintenance, outcome feedback, restart, and purge
without teaching callers how to sequence those operations safely.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import selectors
import signal
import subprocess
import tempfile
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from harness.memory_trials.schema import canonical_json, sha256_text

LIFECYCLE_PROTOCOL_VERSION = "memory-lifecycle-v1"
# Private compatibility alias for the sidecar implementation.  The package
# root exports the domain-specific name so it cannot collide with another
# protocol module as the harness grows.
PROTOCOL_VERSION = LIFECYCLE_PROTOCOL_VERSION
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_TOKEN_RE = re.compile(r"[a-z0-9]+")


class MemoryLifecycleError(RuntimeError):
    """Raised when a lifecycle plan or adapter violates the study contract."""


class LifecyclePhase(StrEnum):
    CONTROL = "control"
    CONSTRUCTION = "construction"
    MAINTENANCE = "maintenance"
    RETRIEVAL = "retrieval"
    FEEDBACK = "feedback"


class LifecycleCapability(StrEnum):
    APPLY = "apply"
    QUERY = "query"
    MAINTAIN = "maintain"
    FEEDBACK = "feedback"
    CHECKPOINT = "checkpoint"
    RESTORE = "restore"
    INSPECT = "inspect"
    PURGE = "purge"


class LifecycleSystemReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    protocol_version: Literal["memory-lifecycle-v1"] = PROTOCOL_VERSION
    system_id: str = Field(min_length=1)
    implementation_kind: Literal[
        "in_process_reference", "subprocess_reference", "oci_sidecar"
    ]
    implementation_revision: str = Field(min_length=1)
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capabilities: tuple[LifecycleCapability, ...]
    publication_ready: bool = False

    @model_validator(mode="after")
    def validate_capabilities(self) -> LifecycleSystemReceipt:
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("lifecycle capabilities must be unique")
        return self


class LifecycleEvent(BaseModel):
    """One task-blind write-path event; no oracle, suffix, or outcome fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    step: int = Field(ge=0)
    kind: Literal["write", "update", "delete", "access", "observe"]
    record_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    key: str = Field(min_length=1)
    value: str | None = None
    untrusted: bool = True

    @model_validator(mode="after")
    def validate_value(self) -> LifecycleEvent:
        if self.kind in {"write", "update", "observe"} and not self.value:
            raise ValueError(f"{self.kind} requires a non-empty value")
        if self.kind in {"delete", "access"} and self.value is not None:
            raise ValueError(f"{self.kind} cannot carry a value")
        return self


class LifecycleQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query_id: str = Field(min_length=1)
    step: int = Field(ge=0)
    text: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1)
    max_archive_reads: int = Field(default=1, ge=0)
    max_injected_tokens: int = Field(default=256, ge=1)


class LifecycleMaintenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    maintenance_id: str = Field(min_length=1)
    step: int = Field(ge=0)
    trigger: Literal["fixed_interval", "capacity", "manual"]


class LifecycleFeedback(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    feedback_id: str = Field(min_length=1)
    step: int = Field(ge=0)
    outcome_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    used_record_ids: tuple[str, ...]
    reward: float = Field(allow_inf_nan=False, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def validate_used_records(self) -> LifecycleFeedback:
        if not self.used_record_ids:
            raise ValueError("feedback must cite at least one used record")
        if len(self.used_record_ids) != len(set(self.used_record_ids)):
            raise ValueError("feedback used_record_ids must be unique")
        return self


class LifecycleCheckpointRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: str
    entity_id: str
    key: str
    value: str
    written_step: int = Field(ge=0)
    last_access_step: int = Field(ge=0)
    residency: Literal["active", "archive"]
    source_event_ids: tuple[str, ...] = Field(min_length=1)
    utility: float = Field(allow_inf_nan=False)
    untrusted: bool


class LifecycleCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_scope: str = Field(min_length=1)
    records: tuple[LifecycleCheckpointRecord, ...]
    state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_digest(self) -> LifecycleCheckpoint:
        record_ids = [record.record_id for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("checkpoint record IDs must be unique")
        for record in self.records:
            if len(record.source_event_ids) != len(set(record.source_event_ids)):
                raise ValueError("checkpoint source event IDs must be unique per record")
        expected_state = sha256_text(
            canonical_json([record.model_dump(mode="json") for record in self.records])
        )
        if expected_state != self.state_sha256:
            raise ValueError("state_sha256 does not bind the checkpoint records")
        payload = self.model_dump(mode="json", exclude={"checkpoint_sha256"})
        if sha256_text(canonical_json(payload)) != self.checkpoint_sha256:
            raise ValueError("checkpoint_sha256 does not bind the checkpoint")
        return self


class LifecycleCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    command_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    idempotency_key: str = Field(min_length=1)
    session_scope: str = Field(min_length=1)
    step: int = Field(ge=0)
    kind: Literal[
        "begin",
        "apply",
        "query",
        "maintain",
        "feedback",
        "checkpoint",
        "restore",
        "inspect",
        "purge",
    ]
    event: LifecycleEvent | None = None
    query: LifecycleQuery | None = None
    maintenance: LifecycleMaintenance | None = None
    feedback: LifecycleFeedback | None = None
    checkpoint: LifecycleCheckpoint | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> LifecycleCommand:
        fields = {
            "event": self.event,
            "query": self.query,
            "maintenance": self.maintenance,
            "feedback": self.feedback,
            "checkpoint": self.checkpoint,
        }
        required = {
            "apply": "event",
            "query": "query",
            "maintain": "maintenance",
            "feedback": "feedback",
            "restore": "checkpoint",
        }.get(self.kind)
        populated = {name for name, value in fields.items() if value is not None}
        expected = {required} if required else set()
        if populated != expected:
            raise ValueError(f"{self.kind} payload must contain exactly {sorted(expected)}")
        payload_step = next(
            (
                value.step
                for value in (self.event, self.query, self.maintenance, self.feedback)
                if value is not None
            ),
            self.step,
        )
        if payload_step != self.step:
            raise ValueError("command and payload steps must match")
        if self.checkpoint is not None and self.checkpoint.session_scope != self.session_scope:
            raise ValueError("restore checkpoint session does not match command session")
        return self

    @property
    def command_sha256(self) -> str:
        return sha256_text(canonical_json(self.model_dump(mode="json")))


class LifecycleEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_event_ids: tuple[str, ...] = Field(min_length=1)
    prior_residency: Literal["active", "archive"]
    score: float = Field(allow_inf_nan=False)


class LifecycleStateSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    active_record_ids: tuple[str, ...]
    archive_record_ids: tuple[str, ...]
    active_bytes: int = Field(ge=0)
    archive_bytes: int = Field(ge=0)
    lineage: tuple[tuple[str, tuple[str, ...]], ...]

    @model_validator(mode="after")
    def validate_roster_and_lineage(self) -> LifecycleStateSummary:
        active = set(self.active_record_ids)
        archive = set(self.archive_record_ids)
        if len(active) != len(self.active_record_ids):
            raise ValueError("active record IDs must be unique")
        if len(archive) != len(self.archive_record_ids):
            raise ValueError("archive record IDs must be unique")
        if active & archive:
            raise ValueError("one record cannot be both active and archived")
        lineage_ids = [record_id for record_id, _ in self.lineage]
        if len(lineage_ids) != len(set(lineage_ids)):
            raise ValueError("lineage record IDs must be unique")
        if set(lineage_ids) != active | archive:
            raise ValueError("lineage must cover exactly the resident records")
        for _, source_event_ids in self.lineage:
            if not source_event_ids:
                raise ValueError("resident records require source lineage")
            if len(source_event_ids) != len(set(source_event_ids)):
                raise ValueError("source event IDs must be unique per record")
        return self


class LifecyclePhaseCost(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    phase: LifecyclePhase
    writes: int = Field(default=0, ge=0)
    reads: int = Field(default=0, ge=0)
    serialized_input_bytes: int = Field(default=0, ge=0)
    serialized_output_bytes: int = Field(default=0, ge=0)
    injected_tokens_estimate: int = Field(default=0, ge=0)
    embedding_calls: int = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)


class LifecycleOperationReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    command_id: str
    command_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pre_logical_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    post_logical_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pre_durable_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    post_durable_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence: tuple[LifecycleEvidence, ...] = ()
    summary: LifecycleStateSummary
    checkpoint: LifecycleCheckpoint | None = None
    cost: LifecyclePhaseCost
    operation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_digest(self) -> LifecycleOperationReceipt:
        payload = self.model_dump(mode="json", exclude={"operation_sha256"})
        if sha256_text(canonical_json(payload)) != self.operation_sha256:
            raise ValueError("operation_sha256 does not bind the receipt")
        return self


class LifecyclePlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    plan_id: str = Field(min_length=1)
    expected_system_id: str = Field(min_length=1)
    active_slots: int = Field(default=4, ge=1)
    commands: tuple[LifecycleCommand, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_order(self) -> LifecyclePlan:
        begin_indexes = [i for i, command in enumerate(self.commands) if command.kind == "begin"]
        if begin_indexes != [0]:
            raise ValueError("lifecycle plan must contain exactly one leading begin")
        if self.commands[-1].kind != "inspect":
            raise ValueError("lifecycle plan must end with inspect")
        scopes = {command.session_scope for command in self.commands}
        if len(scopes) != 1:
            raise ValueError("one lifecycle plan must own exactly one session")
        command_ids = [command.command_id for command in self.commands]
        if len(command_ids) != len(set(command_ids)):
            raise ValueError("lifecycle command IDs must be unique")
        keys = [command.idempotency_key for command in self.commands]
        if len(keys) != len(set(keys)):
            raise ValueError("lifecycle idempotency keys must be unique")
        event_ids = [
            command.event.event_id for command in self.commands if command.event is not None
        ]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("lifecycle source event IDs must be unique")
        payload_ids = [
            payload_id
            for command in self.commands
            for payload_id in (
                command.query.query_id if command.query is not None else None,
                command.maintenance.maintenance_id
                if command.maintenance is not None
                else None,
                command.feedback.feedback_id if command.feedback is not None else None,
            )
            if payload_id is not None
        ]
        if len(payload_ids) != len(set(payload_ids)):
            raise ValueError("lifecycle query, maintenance, and feedback IDs must be unique")
        steps = [command.step for command in self.commands]
        if steps != sorted(steps):
            raise ValueError("lifecycle command steps must be monotonic")
        purge_indexes = [i for i, command in enumerate(self.commands) if command.kind == "purge"]
        if purge_indexes and purge_indexes != [len(self.commands) - 2]:
            raise ValueError("purge, when present, must be followed only by final inspect")
        return self

    @property
    def plan_sha256(self) -> str:
        return sha256_text(canonical_json(self.model_dump(mode="json")))


class LifecycleTraceReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    system_receipt: LifecycleSystemReceipt
    operations: tuple[LifecycleOperationReceipt, ...]
    phase_costs: tuple[LifecyclePhaseCost, ...]
    lineage_complete: bool
    state_chain_complete: bool
    purged: bool
    trace_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_digest(self) -> LifecycleTraceReceipt:
        payload = self.model_dump(mode="json", exclude={"trace_sha256"})
        if sha256_text(canonical_json(payload)) != self.trace_sha256:
            raise ValueError("trace_sha256 does not bind the lifecycle trace")
        return self


class LifecyclePort(Protocol):
    receipt: LifecycleSystemReceipt

    def execute(self, command: LifecycleCommand) -> LifecycleOperationReceipt: ...

    def close(self) -> None: ...


def _seal_operation(payload: dict[str, Any]) -> LifecycleOperationReceipt:
    payload = dict(payload)
    payload["operation_sha256"] = sha256_text(canonical_json(payload))
    return LifecycleOperationReceipt.model_validate(payload)


def _phase_for(kind: str) -> LifecyclePhase:
    return {
        "apply": LifecyclePhase.CONSTRUCTION,
        "query": LifecyclePhase.RETRIEVAL,
        "maintain": LifecyclePhase.MAINTENANCE,
        "feedback": LifecyclePhase.FEEDBACK,
    }.get(kind, LifecyclePhase.CONTROL)


def _token_estimate(text: str) -> int:
    return (len(text.encode()) + 3) // 4


def run_lifecycle_plan(port: LifecyclePort, plan: LifecyclePlan) -> LifecycleTraceReceipt:
    """Execute a complete plan while enforcing state, lineage, and budget invariants."""

    if port.receipt.system_id != plan.expected_system_id:
        raise MemoryLifecycleError("lifecycle system identity differs from the plan")
    capabilities = set(port.receipt.capabilities)
    required = {
        LifecycleCapability(command.kind)
        for command in plan.commands
        if command.kind in {item.value for item in LifecycleCapability}
    }
    missing = sorted(item.value for item in required - capabilities)
    if missing:
        raise MemoryLifecycleError(f"lifecycle system lacks required capabilities: {missing}")

    seen_source_events: set[str] = set()
    operations: list[LifecycleOperationReceipt] = []
    previous_logical_root: str | None = None
    previous_durable_root: str | None = None
    totals: dict[LifecyclePhase, dict[str, int | float]] = {}
    lineage_complete = True
    state_chain_complete = True

    for command in plan.commands:
        operation = port.execute(command)
        if operation.command_id != command.command_id:
            raise MemoryLifecycleError("lifecycle adapter changed command_id")
        if operation.command_sha256 != command.command_sha256:
            raise MemoryLifecycleError("lifecycle adapter changed command bytes")
        if (
            previous_logical_root is not None
            and operation.pre_logical_state_sha256 != previous_logical_root
        ):
            state_chain_complete = False
            raise MemoryLifecycleError("lifecycle logical state chain diverged")
        if (
            previous_durable_root is not None
            and operation.pre_durable_state_sha256 != previous_durable_root
        ):
            state_chain_complete = False
            raise MemoryLifecycleError("lifecycle durable state chain diverged")
        previous_logical_root = operation.post_logical_state_sha256
        previous_durable_root = operation.post_durable_state_sha256
        if command.event is not None:
            seen_source_events.add(command.event.event_id)
        if command.kind == "restore" and command.checkpoint is not None:
            for record in command.checkpoint.records:
                seen_source_events.update(record.source_event_ids)
        summary_lineage = {
            source_event_id
            for _, source_event_ids in operation.summary.lineage
            for source_event_id in source_event_ids
        }
        if not summary_lineage.issubset(seen_source_events):
            lineage_complete = False
            raise MemoryLifecycleError("state summary cites future or unknown source events")
        for evidence in operation.evidence:
            if not set(evidence.source_event_ids).issubset(seen_source_events):
                lineage_complete = False
                raise MemoryLifecycleError("evidence cites future or unknown source events")
        if command.query is not None:
            evidence_ids = [item.evidence_id for item in operation.evidence]
            record_ids = [item.record_id for item in operation.evidence]
            if len(evidence_ids) != len(set(evidence_ids)) or len(record_ids) != len(
                set(record_ids)
            ):
                raise MemoryLifecycleError("lifecycle query returned duplicate evidence")
            if len(operation.evidence) > command.query.top_k:
                raise MemoryLifecycleError("lifecycle query exceeded top-k")
            if (
                sum(item.prior_residency == "archive" for item in operation.evidence)
                > command.query.max_archive_reads
            ):
                raise MemoryLifecycleError("lifecycle query exceeded archive-read budget")
            rendered = canonical_json(
                [item.model_dump(mode="json") for item in operation.evidence]
            )
            injected_tokens = _token_estimate(rendered) if operation.evidence else 0
            if injected_tokens > command.query.max_injected_tokens:
                raise MemoryLifecycleError("lifecycle query exceeded injection budget")
            if operation.cost.injected_tokens_estimate != injected_tokens:
                raise MemoryLifecycleError("lifecycle adapter misstated injected-token cost")
        elif operation.evidence:
            raise MemoryLifecycleError("only query operations may return evidence")
        if operation.cost.phase != _phase_for(command.kind):
            raise MemoryLifecycleError("lifecycle adapter misstated operation phase")
        if len(operation.summary.active_record_ids) > plan.active_slots:
            raise MemoryLifecycleError("lifecycle system exceeded active-slot budget")
        bucket = totals.setdefault(
            operation.cost.phase,
            {
                "writes": 0,
                "reads": 0,
                "serialized_input_bytes": 0,
                "serialized_output_bytes": 0,
                "injected_tokens_estimate": 0,
                "embedding_calls": 0,
                "llm_calls": 0,
                "latency_ms": 0.0,
            },
        )
        for field_name in bucket:
            bucket[field_name] += getattr(operation.cost, field_name)
        operations.append(operation)

    phase_costs = tuple(
        LifecyclePhaseCost(phase=phase, **totals[phase])
        for phase in LifecyclePhase
        if phase in totals
    )
    final = operations[-1]
    purge_requested = any(command.kind == "purge" for command in plan.commands)
    purged = (
        purge_requested
        and not final.summary.active_record_ids
        and not final.summary.archive_record_ids
    )
    payload = {
        "plan_id": plan.plan_id,
        "plan_sha256": plan.plan_sha256,
        "system_receipt": port.receipt.model_dump(mode="json"),
        "operations": [item.model_dump(mode="json") for item in operations],
        "phase_costs": [item.model_dump(mode="json") for item in phase_costs],
        "lineage_complete": lineage_complete,
        "state_chain_complete": state_chain_complete,
        "purged": purged,
    }
    return LifecycleTraceReceipt(
        **payload,
        trace_sha256=sha256_text(canonical_json(payload)),
    )


@dataclass
class _Record:
    record_id: str
    entity_id: str
    key: str
    value: str
    written_step: int
    last_access_step: int
    residency: Literal["active", "archive"]
    source_event_ids: set[str] = field(default_factory=set)
    utility: float = 0.0
    untrusted: bool = True


class ReferenceLifecyclePort:
    """Deterministic active/archive reference used to prove the lifecycle spine."""

    def __init__(
        self,
        *,
        active_slots: int = 4,
        maintenance_mode: Literal["none", "dedupe"] = "dedupe",
        implementation_kind: Literal[
            "in_process_reference", "subprocess_reference", "oci_sidecar"
        ] = "in_process_reference",
    ) -> None:
        if active_slots < 1:
            raise ValueError("active_slots must be positive")
        self.active_slots = active_slots
        self.maintenance_mode = maintenance_mode
        self._sessions: dict[str, dict[str, _Record]] = {}
        self._begun_sessions: set[str] = set()
        self._purged_scope_digests: set[str] = set()
        self._idempotency: dict[
            str, tuple[str, str, LifecycleOperationReceipt]
        ] = {}
        configuration = {
            "active_slots": active_slots,
            "maintenance_mode": maintenance_mode,
            "ranking": "lexical-overlap-plus-utility-plus-recency-v1",
            "residency": "query-promotes-lru-demotes-v1",
        }
        self.receipt = LifecycleSystemReceipt(
            system_id="reference-active-archive-lifecycle-v1",
            implementation_kind=implementation_kind,
            implementation_revision="reference-lifecycle-1",
            configuration_sha256=sha256_text(canonical_json(configuration)),
            capabilities=tuple(LifecycleCapability),
            publication_ready=False,
        )

    def close(self) -> None:
        self._sessions.clear()
        self._begun_sessions.clear()
        self._purged_scope_digests.clear()
        self._idempotency.clear()

    @staticmethod
    def _records_payload(records: Mapping[str, _Record]) -> list[dict[str, JsonValue]]:
        return [
            {
                "record_id": record.record_id,
                "entity_id": record.entity_id,
                "key": record.key,
                "value": record.value,
                "written_step": record.written_step,
                "last_access_step": record.last_access_step,
                "residency": record.residency,
                "source_event_ids": sorted(record.source_event_ids),
                "utility": record.utility,
                "untrusted": record.untrusted,
            }
            for record in sorted(records.values(), key=lambda item: item.record_id)
        ]

    def _state_root(self, session_scope: str) -> str:
        return sha256_text(
            canonical_json(self._records_payload(self._sessions.get(session_scope, {})))
        )

    def _summary(self, session_scope: str) -> LifecycleStateSummary:
        records = self._sessions.get(session_scope, {})
        active = tuple(sorted(r.record_id for r in records.values() if r.residency == "active"))
        archive = tuple(
            sorted(r.record_id for r in records.values() if r.residency == "archive")
        )
        active_bytes = sum(
            len(canonical_json(row).encode())
            for row in self._records_payload(records)
            if row["residency"] == "active"
        )
        archive_bytes = sum(
            len(canonical_json(row).encode())
            for row in self._records_payload(records)
            if row["residency"] == "archive"
        )
        lineage = tuple(
            (record.record_id, tuple(sorted(record.source_event_ids)))
            for record in sorted(records.values(), key=lambda item: item.record_id)
        )
        return LifecycleStateSummary(
            active_record_ids=active,
            archive_record_ids=archive,
            active_bytes=active_bytes,
            archive_bytes=archive_bytes,
            lineage=lineage,
        )

    def _enforce_capacity(self, records: dict[str, _Record]) -> None:
        active = [record for record in records.values() if record.residency == "active"]
        while len(active) > self.active_slots:
            victim = min(
                active,
                key=lambda item: (item.last_access_step, item.written_step, item.record_id),
            )
            victim.residency = "archive"
            active.remove(victim)

    def _promote(self, records: dict[str, _Record], record: _Record, step: int) -> None:
        record.residency = "active"
        record.last_access_step = step
        self._enforce_capacity(records)

    @staticmethod
    def _checkpoint(session_scope: str, records: Mapping[str, _Record]) -> LifecycleCheckpoint:
        checkpoint_records = tuple(
            LifecycleCheckpointRecord.model_validate(row)
            for row in ReferenceLifecyclePort._records_payload(records)
        )
        state_sha256 = sha256_text(
            canonical_json([item.model_dump(mode="json") for item in checkpoint_records])
        )
        payload = {
            "session_scope": session_scope,
            "records": [item.model_dump(mode="json") for item in checkpoint_records],
            "state_sha256": state_sha256,
        }
        return LifecycleCheckpoint(
            **payload,
            checkpoint_sha256=sha256_text(canonical_json(payload)),
        )

    @staticmethod
    def _restore_records(checkpoint: LifecycleCheckpoint) -> dict[str, _Record]:
        return {
            item.record_id: _Record(
                record_id=item.record_id,
                entity_id=item.entity_id,
                key=item.key,
                value=item.value,
                written_step=item.written_step,
                last_access_step=item.last_access_step,
                residency=item.residency,
                source_event_ids=set(item.source_event_ids),
                utility=item.utility,
                untrusted=item.untrusted,
            )
            for item in checkpoint.records
        }

    def execute(self, command: LifecycleCommand) -> LifecycleOperationReceipt:
        scope_digest = sha256_text(command.session_scope)
        identity = sha256_text(
            canonical_json([command.session_scope, command.idempotency_key])
        )
        prior = self._idempotency.get(identity)
        if prior is not None:
            _, prior_sha, prior_receipt = prior
            if prior_sha != command.command_sha256:
                raise MemoryLifecycleError("idempotency key reused with different command bytes")
            return prior_receipt

        pre_root = self._state_root(command.session_scope)
        if command.kind == "begin":
            if (
                command.session_scope in self._begun_sessions
                or scope_digest in self._purged_scope_digests
                or command.session_scope in self._sessions
            ):
                raise MemoryLifecycleError("begin cannot reuse a lifecycle session")
            self._sessions[command.session_scope] = {}
            self._begun_sessions.add(command.session_scope)
            records = self._sessions[command.session_scope]
        elif command.kind == "inspect" and scope_digest in self._purged_scope_digests:
            records = {}
        else:
            if command.session_scope not in self._begun_sessions:
                raise MemoryLifecycleError("lifecycle command requires a begun session")
            records = self._sessions[command.session_scope]
        evidence: tuple[LifecycleEvidence, ...] = ()
        checkpoint: LifecycleCheckpoint | None = None
        writes = 0
        reads = 0

        if command.kind == "begin":
            pass
        elif command.kind == "apply":
            assert command.event is not None
            event = command.event
            if event.kind in {"write", "observe"}:
                if event.record_id in records:
                    raise MemoryLifecycleError("write cannot replace an existing record")
                records[event.record_id] = _Record(
                    record_id=event.record_id,
                    entity_id=event.entity_id,
                    key=event.key,
                    value=event.value or "",
                    written_step=event.step,
                    last_access_step=event.step,
                    residency="active",
                    source_event_ids={event.event_id},
                    untrusted=event.untrusted,
                )
                writes = 1
                self._enforce_capacity(records)
            elif event.kind == "update":
                record = records.get(event.record_id)
                if record is None:
                    raise MemoryLifecycleError("update requires an existing record")
                if (record.entity_id, record.key) != (event.entity_id, event.key):
                    raise MemoryLifecycleError(
                        "update entity/key must match the existing record"
                    )
                record.value = event.value or ""
                record.written_step = event.step
                record.source_event_ids.add(event.event_id)
                self._promote(records, record, event.step)
                writes = 1
            elif event.kind == "delete":
                record = records.get(event.record_id)
                if record is None:
                    raise MemoryLifecycleError("delete requires an existing record")
                if (record.entity_id, record.key) != (event.entity_id, event.key):
                    raise MemoryLifecycleError(
                        "delete entity/key must match the existing record"
                    )
                del records[event.record_id]
                writes = 1
            else:
                record = records.get(event.record_id)
                if record is None:
                    raise MemoryLifecycleError("access requires an existing record")
                if (record.entity_id, record.key) != (event.entity_id, event.key):
                    raise MemoryLifecycleError(
                        "access entity/key must match the existing record"
                    )
                self._promote(records, record, event.step)
                reads = 1
        elif command.kind == "query":
            assert command.query is not None
            query = command.query
            query_tokens = set(_TOKEN_RE.findall(query.text.casefold()))
            ranked = sorted(
                records.values(),
                key=lambda record: (
                    -len(
                        query_tokens
                        & set(
                            _TOKEN_RE.findall(
                                f"{record.entity_id} {record.key} {record.value}".casefold()
                            )
                        )
                    ),
                    -record.utility,
                    -record.last_access_step,
                    record.record_id,
                ),
            )
            selected: list[LifecycleEvidence] = []
            archive_reads = 0
            for record in ranked:
                overlap = len(
                    query_tokens
                    & set(
                        _TOKEN_RE.findall(
                            f"{record.entity_id} {record.key} {record.value}".casefold()
                        )
                    )
                )
                if overlap == 0:
                    continue
                if record.residency == "archive":
                    if archive_reads >= query.max_archive_reads:
                        continue
                    archive_reads += 1
                text = canonical_json(
                    {
                        "entity": record.entity_id,
                        "key": record.key,
                        "value": record.value,
                        "untrusted": record.untrusted,
                    }
                )
                candidate = LifecycleEvidence(
                    evidence_id=f"record:{record.record_id}",
                    record_id=record.record_id,
                    text=text,
                    source_event_ids=tuple(sorted(record.source_event_ids)),
                    prior_residency=record.residency,
                    score=float(overlap * 10 + record.utility),
                )
                projected = canonical_json(
                    [item.model_dump(mode="json") for item in (*selected, candidate)]
                )
                if _token_estimate(projected) > query.max_injected_tokens:
                    continue
                selected.append(candidate)
                if len(selected) >= query.top_k:
                    break
            for item in selected:
                self._promote(records, records[item.record_id], query.step)
            evidence = tuple(selected)
            reads = len(selected)
        elif command.kind == "maintain":
            if self.maintenance_mode == "dedupe":
                groups: dict[tuple[str, str], list[_Record]] = {}
                for record in records.values():
                    groups.setdefault((record.entity_id, record.key), []).append(record)
                for group in groups.values():
                    if len(group) < 2:
                        continue
                    winner = max(group, key=lambda item: (item.written_step, item.record_id))
                    for duplicate in group:
                        if duplicate is winner:
                            continue
                        winner.source_event_ids.update(duplicate.source_event_ids)
                        del records[duplicate.record_id]
                        writes += 1
                self._enforce_capacity(records)
        elif command.kind == "feedback":
            assert command.feedback is not None
            for record_id in command.feedback.used_record_ids:
                record = records.get(record_id)
                if record is None:
                    raise MemoryLifecycleError("feedback cites an unknown record")
                record.utility += command.feedback.reward
                writes += 1
        elif command.kind == "checkpoint":
            checkpoint = self._checkpoint(command.session_scope, records)
        elif command.kind == "restore":
            assert command.checkpoint is not None
            if records:
                raise MemoryLifecycleError("restore requires an empty begun session")
            self._sessions[command.session_scope] = self._restore_records(command.checkpoint)
            records = self._sessions[command.session_scope]
        elif command.kind == "purge":
            self._sessions.pop(command.session_scope, None)
            self._begun_sessions.remove(command.session_scope)
            self._purged_scope_digests.add(scope_digest)
            records = {}
        elif command.kind != "inspect":
            raise MemoryLifecycleError(f"unsupported lifecycle command {command.kind}")

        post_root = self._state_root(command.session_scope)
        summary = self._summary(command.session_scope)
        input_bytes = len(canonical_json(command.model_dump(mode="json")).encode())
        output_bytes = len(
            canonical_json(
                {
                    "evidence": [item.model_dump(mode="json") for item in evidence],
                    "summary": summary.model_dump(mode="json"),
                    "checkpoint": checkpoint.model_dump(mode="json") if checkpoint else None,
                }
            ).encode()
        )
        cost = LifecyclePhaseCost(
            phase=_phase_for(command.kind),
            writes=writes,
            reads=reads,
            serialized_input_bytes=input_bytes,
            serialized_output_bytes=output_bytes,
            injected_tokens_estimate=(
                _token_estimate(
                    canonical_json([item.model_dump(mode="json") for item in evidence])
                )
                if evidence
                else 0
            ),
        )
        payload = {
            "command_id": command.command_id,
            "command_sha256": command.command_sha256,
            "pre_logical_state_sha256": pre_root,
            "post_logical_state_sha256": post_root,
            "pre_durable_state_sha256": pre_root,
            "post_durable_state_sha256": post_root,
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "summary": summary.model_dump(mode="json"),
            "checkpoint": checkpoint.model_dump(mode="json") if checkpoint else None,
            "cost": cost.model_dump(mode="json"),
        }
        receipt = _seal_operation(payload)
        if command.kind == "purge":
            self._idempotency = {
                key: value
                for key, value in self._idempotency.items()
                if value[0] != scope_digest
            }
        self._idempotency[identity] = (scope_digest, command.command_sha256, receipt)
        return receipt


class SubprocessLifecyclePort:
    """Line-framed subprocess adapter for digest-pinned lifecycle containers."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float = 120.0,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ValueError("lifecycle sidecar command must contain non-empty argv strings")
        if timeout_seconds <= 0:
            raise ValueError("lifecycle sidecar timeout must be positive")
        self._timeout_seconds = timeout_seconds
        self._closed = False
        self._lock = threading.Lock()
        self._stderr = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")  # noqa: SIM115
        process_environment = {
            "PATH": os.environ.get("PATH", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            **dict(environment or {}),
        }
        self._process = subprocess.Popen(
            tuple(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr,
            text=True,
            bufsize=1,
            env=process_environment,
            start_new_session=True,
        )
        try:
            result = self._call("handshake", {})
            self.receipt = LifecycleSystemReceipt.model_validate(result["receipt"])
        except Exception:
            self.close()
            raise

    @property
    def process_id(self) -> int:
        return self._process.pid

    @property
    def is_running(self) -> bool:
        return not self._closed and self._process.poll() is None

    def _stderr_tail(self) -> str:
        if self._process.poll() is None:
            return ""
        self._stderr.flush()
        self._stderr.seek(0)
        return self._stderr.read()[-2000:]

    def _terminate(self) -> None:
        if self._process.poll() is not None:
            return
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self._process.pid, signal.SIGTERM)
        try:
            self._process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self._process.pid, signal.SIGKILL)
            self._process.wait(timeout=2.0)

    def _readline(self, operation: str) -> str:
        if self._process.stdout is None:
            raise MemoryLifecycleError("lifecycle sidecar stdout is unavailable")
        selector = selectors.DefaultSelector()
        try:
            selector.register(self._process.stdout, selectors.EVENT_READ)
            ready = selector.select(self._timeout_seconds)
        finally:
            selector.close()
        if not ready:
            self._terminate()
            raise MemoryLifecycleError(f"lifecycle sidecar timed out during {operation}")
        line = self._process.stdout.readline(MAX_RESPONSE_BYTES + 2)
        if not line:
            raise MemoryLifecycleError(
                f"lifecycle sidecar exited during {operation}: {self._stderr_tail()}"
            )
        if not line.endswith("\n") or len(line.encode()) > MAX_RESPONSE_BYTES:
            self._terminate()
            raise MemoryLifecycleError("lifecycle sidecar response exceeds line limit")
        return line

    def _call(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        envelope = canonical_json(
            {"protocol": PROTOCOL_VERSION, "operation": operation, "payload": dict(payload)}
        )
        with self._lock:
            if self._closed:
                raise MemoryLifecycleError("lifecycle sidecar is closed")
            if self._process.poll() is not None or self._process.stdin is None:
                raise MemoryLifecycleError("lifecycle sidecar is not running")
            self._process.stdin.write(envelope + "\n")
            self._process.stdin.flush()
            line = self._readline(operation)
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MemoryLifecycleError("lifecycle sidecar returned malformed JSON") from exc
        if not isinstance(response, dict):
            raise MemoryLifecycleError("lifecycle sidecar response must be an object")
        if response.get("protocol") != PROTOCOL_VERSION:
            raise MemoryLifecycleError("lifecycle sidecar changed protocol")
        if response.get("operation") != operation:
            raise MemoryLifecycleError("lifecycle sidecar operation mismatch")
        result = response.get("result")
        if response.get("ok") is not True:
            detail = result.get("error") if isinstance(result, dict) else None
            raise MemoryLifecycleError(f"lifecycle sidecar rejected {operation}: {detail}")
        if not isinstance(result, dict):
            raise MemoryLifecycleError("lifecycle sidecar result must be an object")
        return result

    def execute(self, command: LifecycleCommand) -> LifecycleOperationReceipt:
        result = self._call("execute", {"command": command.model_dump(mode="json")})
        try:
            return LifecycleOperationReceipt.model_validate(result["receipt"])
        except (KeyError, ValueError) as exc:
            raise MemoryLifecycleError("lifecycle sidecar returned an invalid receipt") from exc

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._process.poll() is None:
                with contextlib.suppress(MemoryLifecycleError):
                    self._call("shutdown", {})
                try:
                    self._process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._terminate()
        finally:
            self._closed = True
            if self._process.stdin is not None:
                self._process.stdin.close()
            if self._process.stdout is not None:
                self._process.stdout.close()
            self._stderr.close()

    def __enter__(self) -> SubprocessLifecyclePort:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
