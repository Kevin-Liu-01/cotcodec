"""Deterministic study compiler for the ``memory-lifecycle-v1`` contract.

The study is intentionally a transport and mechanism doctor.  It creates
task-blind event streams whose expected state transitions are executable in
code; it does not manufacture a model-quality or native-system result.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.memory_trials.lifecycle import (
    LifecycleCheckpoint,
    LifecycleCommand,
    LifecycleEvent,
    LifecycleFeedback,
    LifecycleMaintenance,
    LifecycleOperationReceipt,
    LifecyclePhase,
    LifecyclePhaseCost,
    LifecyclePlan,
    LifecycleQuery,
    LifecycleTraceReceipt,
)
from harness.memory_trials.schema import canonical_json, sha256_text

LIFECYCLE_STUDY_VERSION = "memory-lifecycle-study-v1"
REFERENCE_LIFECYCLE_SYSTEM_ID = "reference-active-archive-lifecycle-v1"
LifecycleFamily = Literal[
    "active_archive",
    "update_delete",
    "consolidation",
    "feedback",
]
LIFECYCLE_FAMILIES: tuple[LifecycleFamily, ...] = (
    "active_archive",
    "update_delete",
    "consolidation",
    "feedback",
)


class MemoryLifecycleStudyError(RuntimeError):
    """Raised when a compiled lifecycle case fails its executable oracle."""


class LifecycleCaseOracle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    first_query_command_id: str
    second_query_command_id: str
    checkpoint_command_id: str
    expected_first_record_ids: tuple[str, ...]
    expected_second_record_ids: tuple[str, ...]
    expected_first_prior_residency: Literal["active", "archive"] | None = None
    expected_second_prior_residency: Literal["active", "archive"] | None = None
    required_second_lineage: tuple[str, ...] = ()
    deleted_record_id: str | None = None
    rewarded_record_id: str | None = None

    @model_validator(mode="after")
    def validate_oracle(self) -> LifecycleCaseOracle:
        if len(self.expected_first_record_ids) != len(set(self.expected_first_record_ids)):
            raise ValueError("first-query oracle record IDs must be unique")
        if len(self.expected_second_record_ids) != len(set(self.expected_second_record_ids)):
            raise ValueError("second-query oracle record IDs must be unique")
        if len(self.required_second_lineage) != len(set(self.required_second_lineage)):
            raise ValueError("oracle lineage event IDs must be unique")
        return self


class LifecycleStudyCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    study_version: Literal["memory-lifecycle-study-v1"] = LIFECYCLE_STUDY_VERSION
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    family: LifecycleFamily
    scenario_index: int = Field(ge=0)
    active_slots: int = Field(ge=1)
    seed: int
    plan: LifecyclePlan
    oracle: LifecycleCaseOracle

    @property
    def case_sha256(self) -> str:
        return sha256_text(canonical_json(self.model_dump(mode="json")))


def _command(
    case_id: str,
    ordinal: int,
    kind: str,
    *,
    step: int,
    scope: str,
    event: LifecycleEvent | None = None,
    query: LifecycleQuery | None = None,
    maintenance: LifecycleMaintenance | None = None,
    feedback: LifecycleFeedback | None = None,
    checkpoint: LifecycleCheckpoint | None = None,
) -> LifecycleCommand:
    return LifecycleCommand(
        command_id=f"{case_id}.c{ordinal:02d}.{kind}",
        idempotency_key=f"{case_id}.idempotency.{ordinal:02d}",
        session_scope=scope,
        step=step,
        kind=kind,
        event=event,
        query=query,
        maintenance=maintenance,
        feedback=feedback,
        checkpoint=checkpoint,
    )


def _event(
    case_id: str,
    ordinal: int,
    *,
    step: int,
    kind: str,
    record_id: str,
    entity_id: str,
    key: str,
    value: str | None,
) -> LifecycleEvent:
    return LifecycleEvent(
        event_id=f"{case_id}.event.{ordinal:02d}",
        step=step,
        kind=kind,
        record_id=record_id,
        entity_id=entity_id,
        key=key,
        value=value,
    )


def _query(
    case_id: str,
    ordinal: int,
    *,
    step: int,
    text: str,
    top_k: int,
    max_archive_reads: int = 1,
) -> LifecycleQuery:
    return LifecycleQuery(
        query_id=f"{case_id}.query.{ordinal:02d}",
        step=step,
        text=text,
        top_k=top_k,
        max_archive_reads=max_archive_reads,
        max_injected_tokens=256,
    )


def _compile_active_archive(
    case_id: str, scenario_index: int, active_slots: int, seed: int
) -> tuple[LifecyclePlan, LifecycleCaseOracle]:
    scope = f"lifecycle/{case_id}"
    entity = f"traveler-{seed}-{scenario_index:02d}"
    target_record = f"{case_id}-target"
    target_value = f"cedar-harbor-{seed}-{scenario_index:02d}"
    commands: list[LifecycleCommand] = [_command(case_id, 0, "begin", step=0, scope=scope)]
    target_event = _event(
        case_id,
        1,
        step=1,
        kind="write",
        record_id=target_record,
        entity_id=entity,
        key="destination",
        value=target_value,
    )
    commands.append(_command(case_id, 1, "apply", step=1, scope=scope, event=target_event))
    ordinal = 2
    for distractor_index in range(active_slots):
        step = ordinal
        event = _event(
            case_id,
            ordinal,
            step=step,
            kind="write",
            record_id=f"{case_id}-distractor-{distractor_index:02d}",
            entity_id=f"noise-{seed}-{scenario_index:02d}-{distractor_index:02d}",
            key="irrelevant",
            value=f"granite-{distractor_index:02d}",
        )
        commands.append(_command(case_id, ordinal, "apply", step=step, scope=scope, event=event))
        ordinal += 1
    first_query_id = f"{case_id}.c{ordinal:02d}.query"
    commands.append(
        _command(
            case_id,
            ordinal,
            "query",
            step=ordinal,
            scope=scope,
            query=_query(
                case_id,
                1,
                step=ordinal,
                text=f"Where is {entity} going: {target_value}?",
                top_k=1,
            ),
        )
    )
    ordinal += 1
    checkpoint_id = f"{case_id}.c{ordinal:02d}.checkpoint"
    commands.append(_command(case_id, ordinal, "checkpoint", step=ordinal, scope=scope))
    ordinal += 1
    second_query_id = f"{case_id}.c{ordinal:02d}.query"
    commands.append(
        _command(
            case_id,
            ordinal,
            "query",
            step=ordinal,
            scope=scope,
            query=_query(
                case_id,
                2,
                step=ordinal,
                text=f"Confirm {entity} destination {target_value}",
                top_k=1,
            ),
        )
    )
    ordinal += 1
    commands.append(_command(case_id, ordinal, "purge", step=ordinal, scope=scope))
    ordinal += 1
    commands.append(_command(case_id, ordinal, "inspect", step=ordinal, scope=scope))
    return (
        LifecyclePlan(
            plan_id=f"plan-{case_id}",
            expected_system_id=REFERENCE_LIFECYCLE_SYSTEM_ID,
            active_slots=active_slots,
            commands=tuple(commands),
        ),
        LifecycleCaseOracle(
            first_query_command_id=first_query_id,
            second_query_command_id=second_query_id,
            checkpoint_command_id=checkpoint_id,
            expected_first_record_ids=(target_record,),
            expected_second_record_ids=(target_record,),
            expected_first_prior_residency="archive",
            expected_second_prior_residency="active",
            required_second_lineage=(target_event.event_id,),
        ),
    )


def _compile_update_delete(
    case_id: str, scenario_index: int, active_slots: int, seed: int
) -> tuple[LifecyclePlan, LifecycleCaseOracle]:
    scope = f"lifecycle/{case_id}"
    entity = f"profile-{seed}-{scenario_index:02d}"
    record_id = f"{case_id}-preference"
    old_value = f"tea-{scenario_index:02d}"
    current_value = f"coffee-{seed}-{scenario_index:02d}"
    write = _event(
        case_id,
        1,
        step=1,
        kind="write",
        record_id=record_id,
        entity_id=entity,
        key="beverage",
        value=old_value,
    )
    update = _event(
        case_id,
        2,
        step=2,
        kind="update",
        record_id=record_id,
        entity_id=entity,
        key="beverage",
        value=current_value,
    )
    query_one = _query(
        case_id,
        1,
        step=3,
        text=f"What beverage does {entity} prefer: {current_value}?",
        top_k=1,
    )
    delete = _event(
        case_id,
        3,
        step=5,
        kind="delete",
        record_id=record_id,
        entity_id=entity,
        key="beverage",
        value=None,
    )
    query_two = _query(
        case_id,
        2,
        step=6,
        text=f"Find the deleted preference {entity} {current_value}",
        top_k=1,
    )
    commands = (
        _command(case_id, 0, "begin", step=0, scope=scope),
        _command(case_id, 1, "apply", step=1, scope=scope, event=write),
        _command(case_id, 2, "apply", step=2, scope=scope, event=update),
        _command(case_id, 3, "query", step=3, scope=scope, query=query_one),
        _command(case_id, 4, "checkpoint", step=4, scope=scope),
        _command(case_id, 5, "apply", step=5, scope=scope, event=delete),
        _command(case_id, 6, "query", step=6, scope=scope, query=query_two),
        _command(case_id, 7, "purge", step=7, scope=scope),
        _command(case_id, 8, "inspect", step=8, scope=scope),
    )
    return (
        LifecyclePlan(
            plan_id=f"plan-{case_id}",
            expected_system_id=REFERENCE_LIFECYCLE_SYSTEM_ID,
            active_slots=active_slots,
            commands=commands,
        ),
        LifecycleCaseOracle(
            first_query_command_id=commands[3].command_id,
            second_query_command_id=commands[6].command_id,
            checkpoint_command_id=commands[4].command_id,
            expected_first_record_ids=(record_id,),
            expected_second_record_ids=(),
            expected_first_prior_residency="active",
            required_second_lineage=(),
            deleted_record_id=record_id,
        ),
    )


def _compile_consolidation(
    case_id: str, scenario_index: int, active_slots: int, seed: int
) -> tuple[LifecyclePlan, LifecycleCaseOracle]:
    scope = f"lifecycle/{case_id}"
    entity = f"project-{seed}-{scenario_index:02d}"
    older_id = f"{case_id}-older"
    newer_id = f"{case_id}-newer"
    older = _event(
        case_id,
        1,
        step=1,
        kind="write",
        record_id=older_id,
        entity_id=entity,
        key="deadline",
        value=f"monday-{scenario_index:02d}",
    )
    newer = _event(
        case_id,
        2,
        step=2,
        kind="write",
        record_id=newer_id,
        entity_id=entity,
        key="deadline",
        value=f"friday-{seed}-{scenario_index:02d}",
    )
    query_one = _query(
        case_id,
        1,
        step=3,
        text=f"Show all {entity} deadline records",
        top_k=2,
    )
    maintenance = LifecycleMaintenance(
        maintenance_id=f"{case_id}.maintenance.01",
        step=5,
        trigger="fixed_interval",
    )
    query_two = _query(
        case_id,
        2,
        step=6,
        text=f"What is the current {entity} deadline friday?",
        top_k=1,
    )
    commands = (
        _command(case_id, 0, "begin", step=0, scope=scope),
        _command(case_id, 1, "apply", step=1, scope=scope, event=older),
        _command(case_id, 2, "apply", step=2, scope=scope, event=newer),
        _command(case_id, 3, "query", step=3, scope=scope, query=query_one),
        _command(case_id, 4, "checkpoint", step=4, scope=scope),
        _command(case_id, 5, "maintain", step=5, scope=scope, maintenance=maintenance),
        _command(case_id, 6, "query", step=6, scope=scope, query=query_two),
        _command(case_id, 7, "purge", step=7, scope=scope),
        _command(case_id, 8, "inspect", step=8, scope=scope),
    )
    return (
        LifecyclePlan(
            plan_id=f"plan-{case_id}",
            expected_system_id=REFERENCE_LIFECYCLE_SYSTEM_ID,
            active_slots=active_slots,
            commands=commands,
        ),
        LifecycleCaseOracle(
            first_query_command_id=commands[3].command_id,
            second_query_command_id=commands[6].command_id,
            checkpoint_command_id=commands[4].command_id,
            expected_first_record_ids=(newer_id, older_id),
            expected_second_record_ids=(newer_id,),
            expected_second_prior_residency="active",
            required_second_lineage=(older.event_id, newer.event_id),
        ),
    )


def _compile_feedback(
    case_id: str, scenario_index: int, active_slots: int, seed: int
) -> tuple[LifecyclePlan, LifecycleCaseOracle]:
    scope = f"lifecycle/{case_id}"
    entity = f"workflow-{seed}-{scenario_index:02d}"
    rewarded_id = f"{case_id}-rewarded"
    recent_id = f"{case_id}-recent"
    rewarded = _event(
        case_id,
        1,
        step=1,
        kind="write",
        record_id=rewarded_id,
        entity_id=entity,
        key="procedure",
        value="deploy blue service",
    )
    recent = _event(
        case_id,
        2,
        step=2,
        kind="write",
        record_id=recent_id,
        entity_id=entity,
        key="procedure",
        value="deploy green service",
    )
    query_one = _query(
        case_id,
        1,
        step=3,
        text=f"Retrieve both {entity} deploy service procedures",
        top_k=2,
    )
    feedback = LifecycleFeedback(
        feedback_id=f"{case_id}.feedback.01",
        step=5,
        outcome_receipt_sha256=sha256_text(f"executable-success:{case_id}"),
        used_record_ids=(rewarded_id,),
        reward=1.0,
    )
    query_two = _query(
        case_id,
        2,
        step=6,
        text=f"Choose the best {entity} deploy service procedure",
        top_k=1,
    )
    commands = (
        _command(case_id, 0, "begin", step=0, scope=scope),
        _command(case_id, 1, "apply", step=1, scope=scope, event=rewarded),
        _command(case_id, 2, "apply", step=2, scope=scope, event=recent),
        _command(case_id, 3, "query", step=3, scope=scope, query=query_one),
        _command(case_id, 4, "checkpoint", step=4, scope=scope),
        _command(case_id, 5, "feedback", step=5, scope=scope, feedback=feedback),
        _command(case_id, 6, "query", step=6, scope=scope, query=query_two),
        _command(case_id, 7, "purge", step=7, scope=scope),
        _command(case_id, 8, "inspect", step=8, scope=scope),
    )
    return (
        LifecyclePlan(
            plan_id=f"plan-{case_id}",
            expected_system_id=REFERENCE_LIFECYCLE_SYSTEM_ID,
            active_slots=active_slots,
            commands=commands,
        ),
        LifecycleCaseOracle(
            first_query_command_id=commands[3].command_id,
            second_query_command_id=commands[6].command_id,
            checkpoint_command_id=commands[4].command_id,
            expected_first_record_ids=(recent_id, rewarded_id),
            expected_second_record_ids=(rewarded_id,),
            expected_second_prior_residency="active",
            required_second_lineage=(rewarded.event_id,),
            rewarded_record_id=rewarded_id,
        ),
    )


_COMPILERS = {
    "active_archive": _compile_active_archive,
    "update_delete": _compile_update_delete,
    "consolidation": _compile_consolidation,
    "feedback": _compile_feedback,
}


def compile_lifecycle_case(
    family: LifecycleFamily,
    scenario_index: int,
    *,
    active_slots: int,
    seed: int,
) -> LifecycleStudyCase:
    """Compile one deterministic case and its executable oracle."""

    if family not in _COMPILERS:
        raise ValueError(f"unsupported lifecycle family: {family}")
    if scenario_index < 0:
        raise ValueError("scenario_index must be non-negative")
    if active_slots < 1:
        raise ValueError("active_slots must be positive")
    case_id = f"lifecycle-k{active_slots}-{family.replace('_', '-')}-{scenario_index:02d}"
    plan, oracle = _COMPILERS[family](case_id, scenario_index, active_slots, seed)
    return LifecycleStudyCase(
        case_id=case_id,
        family=family,
        scenario_index=scenario_index,
        active_slots=active_slots,
        seed=seed,
        plan=plan,
        oracle=oracle,
    )


def compile_lifecycle_matrix(
    *,
    episodes_per_slot_cell: int = 64,
    active_slot_cells: Sequence[int] = (4, 2, 8),
    seed: int = 42,
) -> tuple[LifecycleStudyCase, ...]:
    """Compile the registered equal-strata lifecycle matrix."""

    if episodes_per_slot_cell <= 0 or episodes_per_slot_cell % len(LIFECYCLE_FAMILIES):
        raise ValueError("episodes_per_slot_cell must be positive and divisible by four")
    if not active_slot_cells or len(active_slot_cells) != len(set(active_slot_cells)):
        raise ValueError("active-slot cells must be non-empty and unique")
    if any(value < 2 for value in active_slot_cells):
        raise ValueError("registered lifecycle cells require at least two active slots")
    cases_per_family = episodes_per_slot_cell // len(LIFECYCLE_FAMILIES)
    return tuple(
        compile_lifecycle_case(
            family,
            scenario_index,
            active_slots=active_slots,
            seed=seed,
        )
        for active_slots in active_slot_cells
        for family in LIFECYCLE_FAMILIES
        for scenario_index in range(cases_per_family)
    )


def checkpoint_for_case(
    case: LifecycleStudyCase, trace: LifecycleTraceReceipt
) -> tuple[int, LifecycleCheckpoint]:
    operations = {operation.command_id: operation for operation in trace.operations}
    checkpoint_operation = operations.get(case.oracle.checkpoint_command_id)
    if checkpoint_operation is None or checkpoint_operation.checkpoint is None:
        raise MemoryLifecycleStudyError(f"{case.case_id}: checkpoint artifact is missing")
    index = next(
        index
        for index, command in enumerate(case.plan.commands)
        if command.command_id == case.oracle.checkpoint_command_id
    )
    return index, checkpoint_operation.checkpoint


def compile_restore_plan(
    case: LifecycleStudyCase, trace: LifecycleTraceReceipt
) -> LifecyclePlan:
    """Compile a fresh-process restore followed by the original suffix."""

    checkpoint_index, checkpoint = checkpoint_for_case(case, trace)
    scope = checkpoint.session_scope
    restore_commands = (
        _command(case.case_id, 90, "begin", step=0, scope=scope),
        _command(
            case.case_id,
            91,
            "restore",
            step=case.plan.commands[checkpoint_index].step,
            scope=scope,
            checkpoint=checkpoint,
        ),
        *case.plan.commands[checkpoint_index + 1 :],
    )
    return LifecyclePlan(
        plan_id=f"restore-{case.case_id}",
        expected_system_id=case.plan.expected_system_id,
        active_slots=case.active_slots,
        commands=restore_commands,
    )


def compare_restored_suffix(
    case: LifecycleStudyCase,
    uninterrupted: LifecycleTraceReceipt,
    restored: LifecycleTraceReceipt,
) -> tuple[str, ...]:
    """Require byte-identical operation receipts after the restored boundary."""

    checkpoint_index, _ = checkpoint_for_case(case, uninterrupted)
    expected_commands = case.plan.commands[checkpoint_index + 1 :]
    uninterrupted_by_id = {item.command_id: item for item in uninterrupted.operations}
    restored_by_id = {item.command_id: item for item in restored.operations}
    mismatches: list[str] = []
    for command in expected_commands:
        left = uninterrupted_by_id.get(command.command_id)
        right = restored_by_id.get(command.command_id)
        if left is None or right is None or left.operation_sha256 != right.operation_sha256:
            mismatches.append(command.command_id)
    return tuple(mismatches)


def _operation_map(trace: LifecycleTraceReceipt) -> dict[str, LifecycleOperationReceipt]:
    return {operation.command_id: operation for operation in trace.operations}


def _phase_costs_match(trace: LifecycleTraceReceipt) -> bool:
    fields = (
        "writes",
        "reads",
        "serialized_input_bytes",
        "serialized_output_bytes",
        "injected_tokens_estimate",
        "embedding_calls",
        "llm_calls",
        "latency_ms",
    )
    totals: dict[LifecyclePhase, dict[str, int | float]] = {}
    for operation in trace.operations:
        bucket = totals.setdefault(operation.cost.phase, {field: 0 for field in fields})
        for field in fields:
            bucket[field] += getattr(operation.cost, field)
    expected = tuple(
        LifecyclePhaseCost(phase=phase, **totals[phase])
        for phase in LifecyclePhase
        if phase in totals
    )
    return expected == trace.phase_costs


def evaluate_lifecycle_case(
    case: LifecycleStudyCase,
    trace: LifecycleTraceReceipt,
    *,
    restored_trace: LifecycleTraceReceipt | None = None,
) -> dict[str, object]:
    """Evaluate every registered gate for one case and return a sealed row payload."""

    operations = _operation_map(trace)
    first = operations.get(case.oracle.first_query_command_id)
    second = operations.get(case.oracle.second_query_command_id)
    if first is None or second is None:
        raise MemoryLifecycleStudyError(f"{case.case_id}: query receipts are missing")
    first_ids = tuple(item.record_id for item in first.evidence)
    second_ids = tuple(item.record_id for item in second.evidence)
    query_count = sum(command.kind == "query" for command in case.plan.commands)
    gates = {
        "exactly_two_queries": query_count == 2,
        "state_chain_complete": trace.state_chain_complete,
        "lineage_complete": trace.lineage_complete,
        "purged": trace.purged,
        "phase_costs_exact": _phase_costs_match(trace),
        "first_query_oracle": first_ids == case.oracle.expected_first_record_ids,
        "second_query_oracle": second_ids == case.oracle.expected_second_record_ids,
        "first_residency_oracle": (
            case.oracle.expected_first_prior_residency is None
            or all(
                item.prior_residency == case.oracle.expected_first_prior_residency
                for item in first.evidence
            )
        ),
        "second_residency_oracle": (
            case.oracle.expected_second_prior_residency is None
            or all(
                item.prior_residency == case.oracle.expected_second_prior_residency
                for item in second.evidence
            )
        ),
        "second_lineage_oracle": (
            not case.oracle.required_second_lineage
            or (
                bool(second.evidence)
                and set(case.oracle.required_second_lineage).issubset(
                    set(second.evidence[0].source_event_ids)
                )
            )
        ),
        "final_state_empty": (
            not trace.operations[-1].summary.active_record_ids
            and not trace.operations[-1].summary.archive_record_ids
        ),
    }
    restore_mismatches: tuple[str, ...] = ()
    if restored_trace is not None:
        restore_mismatches = compare_restored_suffix(case, trace, restored_trace)
        gates["fresh_process_restore_exact"] = not restore_mismatches
    else:
        gates["fresh_process_restore_exact"] = False
    failed = tuple(sorted(name for name, passed in gates.items() if not passed))
    if failed:
        raise MemoryLifecycleStudyError(
            f"{case.case_id}: lifecycle gates failed: {', '.join(failed)}"
        )
    return {
        "case_id": case.case_id,
        "case_sha256": case.case_sha256,
        "family": case.family,
        "scenario_index": case.scenario_index,
        "active_slots": case.active_slots,
        "seed": case.seed,
        "plan_sha256": case.plan.plan_sha256,
        "trace_sha256": trace.trace_sha256,
        "restored_trace_sha256": restored_trace.trace_sha256,
        "restore_mismatches": list(restore_mismatches),
        "first_record_ids": list(first_ids),
        "second_record_ids": list(second_ids),
        "gates": gates,
    }


def ordered_root(values: Iterable[str]) -> str:
    """Hash an ordered identifier/digest sequence without set semantics."""

    return sha256_text(canonical_json(list(values)))
