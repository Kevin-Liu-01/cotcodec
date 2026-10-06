from __future__ import annotations

import sys
from pathlib import Path

import pytest

from harness.memory_trials import (
    LifecycleCapability,
    LifecycleCommand,
    LifecycleEvent,
    LifecycleFeedback,
    LifecycleMaintenance,
    LifecycleOperationReceipt,
    LifecyclePlan,
    LifecycleQuery,
    LifecycleSystemReceipt,
    MemoryLifecycleError,
    ReferenceLifecyclePort,
    SubprocessLifecyclePort,
    run_lifecycle_plan,
)
from harness.memory_trials.schema import canonical_json, sha256_text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SIDECAR = PROJECT_ROOT / "scripts" / "run_reference_memory_lifecycle_sidecar.py"
SYSTEM_ID = "reference-active-archive-lifecycle-v1"


def _command(
    index: int,
    kind: str,
    *,
    step: int,
    scope: str = "session-lifecycle-a",
    event: LifecycleEvent | None = None,
    query: LifecycleQuery | None = None,
    maintenance: LifecycleMaintenance | None = None,
    feedback: LifecycleFeedback | None = None,
    checkpoint=None,
) -> LifecycleCommand:
    return LifecycleCommand(
        command_id=f"command-{index:02d}-{kind}",
        idempotency_key=f"idempotency-{index:02d}",
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
    index: int,
    kind: str,
    record_id: str,
    entity_id: str,
    key: str,
    value: str | None,
) -> LifecycleEvent:
    return LifecycleEvent(
        event_id=f"event-{index:02d}",
        step=index,
        kind=kind,
        record_id=record_id,
        entity_id=entity_id,
        key=key,
        value=value,
    )


def _full_commands(*, scope: str = "session-lifecycle-a") -> tuple[LifecycleCommand, ...]:
    return (
        _command(0, "begin", step=0, scope=scope),
        _command(
            1,
            "apply",
            step=1,
            scope=scope,
            event=_event(1, "write", "record-city-a", "user", "city", "Kyoto"),
        ),
        _command(
            2,
            "apply",
            step=2,
            scope=scope,
            event=_event(2, "write", "record-food", "user", "food", "udon"),
        ),
        _command(
            3,
            "apply",
            step=3,
            scope=scope,
            event=_event(3, "write", "record-city-b", "user", "city", "Osaka"),
        ),
        _command(
            4,
            "query",
            step=4,
            scope=scope,
            query=LifecycleQuery(
                query_id="query-archive-promotion",
                step=4,
                text="What is the user city Kyoto?",
                top_k=1,
                max_archive_reads=1,
                max_injected_tokens=256,
            ),
        ),
        _command(
            5,
            "apply",
            step=5,
            scope=scope,
            event=_event(5, "update", "record-city-a", "user", "city", "Nara"),
        ),
        _command(
            6,
            "feedback",
            step=6,
            scope=scope,
            feedback=LifecycleFeedback(
                feedback_id="feedback-01",
                step=6,
                outcome_receipt_sha256=sha256_text("outcome-01"),
                used_record_ids=("record-city-a",),
                reward=0.5,
            ),
        ),
        _command(7, "checkpoint", step=7, scope=scope),
        _command(
            8,
            "maintain",
            step=8,
            scope=scope,
            maintenance=LifecycleMaintenance(
                maintenance_id="maintenance-01",
                step=8,
                trigger="fixed_interval",
            ),
        ),
        _command(
            9,
            "apply",
            step=9,
            scope=scope,
            event=_event(9, "delete", "record-food", "user", "food", None),
        ),
        _command(
            10,
            "query",
            step=10,
            scope=scope,
            query=LifecycleQuery(
                query_id="query-after-maintenance",
                step=10,
                text="What is the user city Nara?",
                top_k=1,
                max_archive_reads=1,
                max_injected_tokens=256,
            ),
        ),
        _command(11, "purge", step=11, scope=scope),
        _command(12, "inspect", step=12, scope=scope),
    )


def _full_plan(*, scope: str = "session-lifecycle-a") -> LifecyclePlan:
    return LifecyclePlan(
        plan_id=f"full-lifecycle-{scope}",
        expected_system_id=SYSTEM_ID,
        active_slots=2,
        commands=_full_commands(scope=scope),
    )


def _reseal_operation(
    receipt: LifecycleOperationReceipt, **updates: object
) -> LifecycleOperationReceipt:
    payload = receipt.model_dump(mode="json", exclude={"operation_sha256"})
    payload.update(updates)
    payload["operation_sha256"] = sha256_text(canonical_json(payload))
    return LifecycleOperationReceipt.model_validate(payload)


def test_reference_lifecycle_exercises_residency_lineage_feedback_and_purge() -> None:
    port = ReferenceLifecyclePort(active_slots=2)
    trace = run_lifecycle_plan(port, _full_plan())
    operations = {item.command_id: item for item in trace.operations}

    promoted = operations["command-04-query"].evidence
    assert len(promoted) == 1
    assert promoted[0].record_id == "record-city-a"
    assert promoted[0].prior_residency == "archive"

    checkpoint_operation = operations["command-07-checkpoint"]
    assert checkpoint_operation.checkpoint is not None
    assert checkpoint_operation.checkpoint.state_sha256 == (
        checkpoint_operation.post_logical_state_sha256
    )

    maintained = operations["command-08-maintain"].summary
    assert "record-city-b" not in maintained.active_record_ids + maintained.archive_record_ids
    final_evidence = operations["command-10-query"].evidence[0]
    assert final_evidence.record_id == "record-city-a"
    assert set(final_evidence.source_event_ids) == {"event-01", "event-03", "event-05"}
    assert "Nara" in final_evidence.text

    assert trace.lineage_complete is True
    assert trace.state_chain_complete is True
    assert trace.purged is True
    assert trace.operations[-1].summary.active_record_ids == ()
    assert trace.operations[-1].summary.archive_record_ids == ()
    assert {item.phase.value for item in trace.phase_costs} == {
        "control",
        "construction",
        "maintenance",
        "retrieval",
        "feedback",
    }


def test_empty_unpurged_session_is_not_mislabeled_as_purged() -> None:
    plan = LifecyclePlan(
        plan_id="empty-session",
        expected_system_id=SYSTEM_ID,
        active_slots=2,
        commands=(
            _command(0, "begin", step=0),
            _command(1, "inspect", step=1),
        ),
    )
    trace = run_lifecycle_plan(ReferenceLifecyclePort(active_slots=2), plan)
    assert trace.purged is False


def test_idempotency_replays_exact_receipt_and_purge_discards_prior_cache() -> None:
    port = ReferenceLifecyclePort(active_slots=2)
    begin = _command(0, "begin", step=0)
    write = _full_commands()[1]
    port.execute(begin)
    first = port.execute(write)
    assert port.execute(write) == first

    changed = write.model_copy(
        update={
            "command_id": "changed-write",
            "event": write.event.model_copy(update={"value": "Tokyo"}) if write.event else None,
        }
    )
    with pytest.raises(MemoryLifecycleError, match="idempotency key reused"):
        port.execute(changed)

    port.execute(_command(11, "purge", step=11))
    with pytest.raises(MemoryLifecycleError, match="requires a begun session"):
        port.execute(write)
    with pytest.raises(MemoryLifecycleError, match="cannot reuse"):
        port.execute(_command(13, "begin", step=13))


def test_subprocess_contract_matches_in_process_reference() -> None:
    plan = _full_plan(scope="session-subprocess")
    expected = run_lifecycle_plan(ReferenceLifecyclePort(active_slots=2), plan)
    with SubprocessLifecyclePort(
        (sys.executable, str(REFERENCE_SIDECAR)),
        timeout_seconds=10,
        environment={"COTCODEC_LIFECYCLE_ACTIVE_SLOTS": "2"},
    ) as port:
        process_id = port.process_id
        actual = run_lifecycle_plan(port, plan)
        assert port.process_id == process_id
        assert port.is_running is True
        assert [item.operation_sha256 for item in actual.operations] == [
            item.operation_sha256 for item in expected.operations
        ]
    assert port.is_running is False


def test_checkpoint_restores_byte_identical_suffix_in_fresh_process() -> None:
    full = run_lifecycle_plan(ReferenceLifecyclePort(active_slots=2), _full_plan())
    full_by_id = {item.command_id: item for item in full.operations}

    prefix_commands = _full_commands()[:8] + (_command(13, "inspect", step=7),)
    prefix_plan = LifecyclePlan(
        plan_id="checkpoint-prefix",
        expected_system_id=SYSTEM_ID,
        active_slots=2,
        commands=prefix_commands,
    )
    prefix = run_lifecycle_plan(ReferenceLifecyclePort(active_slots=2), prefix_plan)
    checkpoint = prefix.operations[-2].checkpoint
    assert checkpoint is not None

    restored_commands = (
        _command(20, "begin", step=0),
        _command(21, "restore", step=7, checkpoint=checkpoint),
        *_full_commands()[8:],
    )
    restored_plan = LifecyclePlan(
        plan_id="checkpoint-restored-suffix",
        expected_system_id=SYSTEM_ID,
        active_slots=2,
        commands=restored_commands,
    )
    with SubprocessLifecyclePort(
        (sys.executable, str(REFERENCE_SIDECAR)),
        timeout_seconds=10,
        environment={"COTCODEC_LIFECYCLE_ACTIVE_SLOTS": "2"},
    ) as fresh_port:
        restored = run_lifecycle_plan(fresh_port, restored_plan)
    restored_by_id = {item.command_id: item for item in restored.operations}

    for command_id in (
        "command-08-maintain",
        "command-09-apply",
        "command-10-query",
        "command-11-purge",
        "command-12-inspect",
    ):
        assert restored_by_id[command_id].post_logical_state_sha256 == (
            full_by_id[command_id].post_logical_state_sha256
        )
        assert restored_by_id[command_id].evidence == full_by_id[command_id].evidence


def test_sessions_are_isolated_and_purge_leaves_no_cross_session_visibility() -> None:
    port = ReferenceLifecyclePort(active_slots=2)
    port.execute(_command(0, "begin", step=0, scope="session-a"))
    port.execute(
        _command(
            1,
            "apply",
            step=1,
            scope="session-a",
            event=_event(1, "write", "secret", "user", "secret", "canary-value"),
        )
    )
    port.execute(_command(2, "begin", step=0, scope="session-b"))
    query = _command(
        3,
        "query",
        step=1,
        scope="session-b",
        query=LifecycleQuery(
            query_id="cross-session-probe",
            step=1,
            text="user secret canary value",
            top_k=2,
            max_archive_reads=1,
            max_injected_tokens=128,
        ),
    )
    assert port.execute(query).evidence == ()
    port.execute(_command(4, "purge", step=2, scope="session-a"))
    inspected = port.execute(_command(5, "inspect", step=3, scope="session-a"))
    assert inspected.summary.active_record_ids == ()
    assert inspected.summary.archive_record_ids == ()


def test_plan_rejects_unknown_lineage_even_when_adapter_receipt_rehashes() -> None:
    base = ReferenceLifecyclePort(active_slots=2)

    class FutureLineagePort:
        receipt = base.receipt

        def execute(self, command: LifecycleCommand) -> LifecycleOperationReceipt:
            result = base.execute(command)
            if command.kind != "query" or not result.evidence:
                return result
            evidence = result.evidence[0].model_copy(
                update={"source_event_ids": ("innocuously-named-future-field",)}
            )
            return _reseal_operation(result, evidence=[evidence.model_dump(mode="json")])

        def close(self) -> None:
            base.close()

    commands = _full_commands()[:5] + (_command(13, "inspect", step=4),)
    plan = LifecyclePlan(
        plan_id="future-lineage-negative",
        expected_system_id=SYSTEM_ID,
        active_slots=2,
        commands=commands,
    )
    with pytest.raises(MemoryLifecycleError, match="future or unknown"):
        run_lifecycle_plan(FutureLineagePort(), plan)


def test_plan_rejects_missing_capability_before_execution() -> None:
    class IncompletePort:
        receipt = LifecycleSystemReceipt(
            system_id=SYSTEM_ID,
            implementation_kind="in_process_reference",
            implementation_revision="incomplete-test",
            configuration_sha256=sha256_text("incomplete"),
            capabilities=(LifecycleCapability.INSPECT,),
        )

        def execute(self, command: LifecycleCommand) -> LifecycleOperationReceipt:
            raise AssertionError(f"must not execute {command.command_id}")

        def close(self) -> None:
            return None

    commands = _full_commands()[:2] + (_command(13, "inspect", step=1),)
    plan = LifecyclePlan(
        plan_id="missing-capability-negative",
        expected_system_id=SYSTEM_ID,
        active_slots=2,
        commands=commands,
    )
    with pytest.raises(MemoryLifecycleError, match="lacks required capabilities"):
        run_lifecycle_plan(IncompletePort(), plan)


def test_mutations_cannot_target_a_record_through_mismatched_entity_or_key() -> None:
    for kind, value in (("update", "Tokyo"), ("delete", None), ("access", None)):
        port = ReferenceLifecyclePort(active_slots=2)
        port.execute(_command(0, "begin", step=0))
        port.execute(_full_commands()[1])
        mismatched = _command(
            30,
            "apply",
            step=2,
            event=LifecycleEvent(
                event_id=f"mismatched-{kind}",
                step=2,
                kind=kind,
                record_id="record-city-a",
                entity_id="another-user",
                key="another-key",
                value=value,
            ),
        )
        with pytest.raises(MemoryLifecycleError, match="entity/key must match"):
            port.execute(mismatched)
