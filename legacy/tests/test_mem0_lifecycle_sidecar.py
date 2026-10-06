from __future__ import annotations

import importlib.util
import json
import sys
import threading
from pathlib import Path

import pytest

from harness.memory_trials.lifecycle import (
    LifecycleCapability,
    LifecycleCommand,
    LifecycleEvent,
    LifecycleMaintenance,
    LifecyclePlan,
    LifecycleQuery,
    MemoryLifecycleError,
    SubprocessLifecyclePort,
    run_lifecycle_plan,
)
from scripts.run_deterministic_embedding_server import EmbeddingServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIDECAR = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "mem0_lifecycle_sidecar.py"
)


def _load_sidecar_module():
    spec = importlib.util.spec_from_file_location("mem0_lifecycle_sidecar_test", SIDECAR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _command(
    command_id: str,
    *,
    scope: str,
    step: int,
    kind: str,
    event: LifecycleEvent | None = None,
    query: LifecycleQuery | None = None,
    checkpoint=None,
) -> LifecycleCommand:
    return LifecycleCommand(
        command_id=command_id,
        idempotency_key=f"{command_id}.idempotency",
        session_scope=scope,
        step=step,
        kind=kind,
        event=event,
        query=query,
        checkpoint=checkpoint,
    )


def _event(
    event_id: str,
    *,
    step: int,
    kind: str,
    value: str | None,
    record_id: str = "record-1",
) -> LifecycleEvent:
    return LifecycleEvent(
        event_id=event_id,
        step=step,
        kind=kind,
        record_id=record_id,
        entity_id="traveler-1",
        key="destination",
        value=value,
    )


@pytest.fixture
def embedding_environment(tmp_path: Path):
    server = EmbeddingServer(("127.0.0.1", 0), model_id="test-embedding", dimensions=16)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    environment = {
        "COTCODEC_MEMORY_STATE_ROOT": str(tmp_path / "state"),
        "COTCODEC_MEMORY_EMBEDDING_BASE_URL": f"http://{host}:{port}/v1",
        "COTCODEC_MEMORY_EMBEDDING_MODEL": "test-embedding",
        "COTCODEC_MEMORY_EMBEDDING_DIMENSIONS": "16",
    }
    try:
        yield environment, tmp_path / "state"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_mem0_lifecycle_restart_update_delete_and_purge(embedding_environment) -> None:
    environment, state_root = embedding_environment
    scope = "mem0-lifecycle/restart"
    begin = _command("restart.begin", scope=scope, step=0, kind="begin")
    write = _command(
        "restart.write",
        scope=scope,
        step=1,
        kind="apply",
        event=_event("restart.event.write", step=1, kind="write", value="cedar harbor"),
    )
    checkpoint_command = _command(
        "restart.checkpoint", scope=scope, step=3, kind="checkpoint"
    )
    with SubprocessLifecyclePort(
        (sys.executable, str(SIDECAR)), timeout_seconds=30, environment=environment
    ) as first:
        assert first.receipt.system_id == "mem0-native-lifecycle-v1"
        assert set(first.receipt.capabilities) == {
            LifecycleCapability.APPLY,
            LifecycleCapability.QUERY,
            LifecycleCapability.CHECKPOINT,
            LifecycleCapability.RESTORE,
            LifecycleCapability.INSPECT,
            LifecycleCapability.PURGE,
        }
        first.execute(begin)
        written = first.execute(write)
        queried = first.execute(
            _command(
                "restart.query",
                scope=scope,
                step=2,
                kind="query",
                query=LifecycleQuery(
                    query_id="restart.query.payload",
                    step=2,
                    text="traveler destination cedar harbor",
                    top_k=1,
                    max_archive_reads=1,
                ),
            )
        )
        checkpoint = first.execute(checkpoint_command).checkpoint
        assert checkpoint is not None
        assert written.summary.active_record_ids == ()
        assert written.summary.archive_record_ids == ("record-1",)
        assert [item.record_id for item in queried.evidence] == ["record-1"]

    resumed_begin = _command("restart.resume", scope=scope, step=0, kind="begin")
    restore = _command(
        "restart.restore",
        scope=scope,
        step=0,
        kind="restore",
        checkpoint=checkpoint,
    )
    update = _command(
        "restart.update",
        scope=scope,
        step=2,
        kind="apply",
        event=_event(
            "restart.event.update", step=2, kind="update", value="amber harbor"
        ),
    )
    delete = _command(
        "restart.delete",
        scope=scope,
        step=3,
        kind="apply",
        event=_event("restart.event.delete", step=3, kind="delete", value=None),
    )
    purge = _command("restart.purge", scope=scope, step=4, kind="purge")
    inspect = _command("restart.inspect", scope=scope, step=5, kind="inspect")
    with SubprocessLifecyclePort(
        (sys.executable, str(SIDECAR)), timeout_seconds=30, environment=environment
    ) as restarted:
        with pytest.raises(MemoryLifecycleError, match="begin cannot reuse"):
            restarted.execute(resumed_begin)
        restored = restarted.execute(restore)
        assert restored.post_durable_state_sha256 == written.post_durable_state_sha256
        resumed_query = restarted.execute(
            _command(
                "restart.query-resumed",
                scope=scope,
                step=2,
                kind="query",
                query=LifecycleQuery(
                    query_id="restart.query-resumed.payload",
                    step=2,
                    text="traveler destination cedar harbor",
                    top_k=1,
                    max_archive_reads=1,
                ),
            )
        )
        first_identity = queried.evidence[0].model_dump(mode="json")
        resumed_identity = resumed_query.evidence[0].model_dump(mode="json")
        first_score = first_identity.pop("score")
        resumed_score = resumed_identity.pop("score")
        assert first_identity == resumed_identity
        assert abs(first_score - resumed_score) <= 1e-6
        updated = restarted.execute(update)
        assert updated.summary.lineage == (
            ("record-1", ("restart.event.write", "restart.event.update")),
        )
        deleted = restarted.execute(delete)
        assert deleted.summary.archive_record_ids == ()
        restarted.execute(purge)
        purged = restarted.execute(inspect)
        assert purged.summary.archive_record_ids == ()

    canary = b"amber harbor"
    assert not any(
        canary in path.read_bytes()
        for path in state_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def test_mem0_lifecycle_branches_have_equal_prefix_roots_and_isolate_mutation(
    embedding_environment,
) -> None:
    environment, _ = embedding_environment
    with SubprocessLifecyclePort(
        (sys.executable, str(SIDECAR)), timeout_seconds=30, environment=environment
    ) as port:
        roots = {}
        for suffix in ("a", "b"):
            scope = f"mem0-lifecycle/branch-{suffix}"
            port.execute(_command(f"{suffix}.begin", scope=scope, step=0, kind="begin"))
            receipt = port.execute(
                _command(
                    f"{suffix}.write",
                    scope=scope,
                    step=1,
                    kind="apply",
                    event=_event(
                        "branch.shared.write",
                        step=1,
                        kind="write",
                        value="saffron echo",
                    ),
                )
            )
            roots[suffix] = (
                receipt.post_logical_state_sha256,
                receipt.post_durable_state_sha256,
            )
        assert roots["a"] == roots["b"]

        before_b = port.execute(
            _command("b.inspect-before", scope="mem0-lifecycle/branch-b", step=2, kind="inspect")
        )
        port.execute(
            _command(
                "a.update",
                scope="mem0-lifecycle/branch-a",
                step=2,
                kind="apply",
                event=_event(
                    "branch.a.update", step=2, kind="update", value="indigo echo"
                ),
            )
        )
        after_b = port.execute(
            _command("b.inspect-after", scope="mem0-lifecycle/branch-b", step=3, kind="inspect")
        )
        assert before_b.post_logical_state_sha256 == after_b.post_logical_state_sha256
        assert before_b.post_durable_state_sha256 == after_b.post_durable_state_sha256


def test_mem0_lifecycle_rejects_duplicate_native_ids_hiding_missing_record() -> None:
    module = _load_sidecar_module()
    port = object.__new__(module.Mem0LifecyclePort)
    logical_rows = [
        {
            "record_id": record_id,
            "entity_id": "traveler-1",
            "key": "destination",
            "value": value,
            "untrusted": False,
            "source_event_ids": [f"event-{record_id}"],
        }
        for record_id, value in (("record-a", "cedar"), ("record-b", "amber"))
    ]
    duplicate_native = {
        "memory": "irrelevant-before-id-set-check",
        "metadata": {
            "lifecycle_record_id": "record-a",
            "entity_id": "traveler-1",
            "key": "destination",
            "source_event_ids_json": json.dumps(["event-record-a"]),
        },
    }

    class StubState:
        @staticmethod
        def _open(scope):
            return object(), None

        @staticmethod
        def _all_records(memory, scope):
            return [duplicate_native, duplicate_native]

    port.state = StubState()
    port._logical_rows = lambda journal: logical_rows
    with pytest.raises(MemoryLifecycleError, match="record IDs differ"):
        port._native_rows("scope", {"records": logical_rows})


def test_mem0_lifecycle_idempotency_and_capability_refusal(embedding_environment) -> None:
    environment, _ = embedding_environment
    scope = "mem0-lifecycle/idempotency"
    begin = _command("idem.begin", scope=scope, step=0, kind="begin")
    write = _command(
        "idem.write",
        scope=scope,
        step=1,
        kind="apply",
        event=_event("idem.event", step=1, kind="write", value="violet delta"),
    )
    with SubprocessLifecyclePort(
        (sys.executable, str(SIDECAR)), timeout_seconds=30, environment=environment
    ) as port:
        port.execute(begin)
        first = port.execute(write)
        assert port.execute(write) == first
        drifted = write.model_copy(
            update={
                "event": write.event.model_copy(update={"value": "tampered"})
                if write.event
                else None
            }
        )
        with pytest.raises(MemoryLifecycleError, match="different bytes"):
            port.execute(drifted)

        port.execute(_command("idem.purge", scope=scope, step=2, kind="purge"))
        with pytest.raises(MemoryLifecycleError, match="requires begin"):
            port.execute(write)

        maintain = LifecycleCommand(
            command_id="unsupported.maintain",
            idempotency_key="unsupported.maintain.idempotency",
            session_scope="mem0-lifecycle/unsupported",
            step=1,
            kind="maintain",
            maintenance=LifecycleMaintenance(
                maintenance_id="unsupported-maintenance",
                step=1,
                trigger="manual",
            ),
        )
        plan = LifecyclePlan(
            plan_id="unsupported-plan",
            expected_system_id="mem0-native-lifecycle-v1",
            active_slots=4,
            commands=(
                _command(
                    "unsupported.begin",
                    scope="mem0-lifecycle/unsupported",
                    step=0,
                    kind="begin",
                ),
                maintain,
                _command(
                    "unsupported.inspect",
                    scope="mem0-lifecycle/unsupported",
                    step=2,
                    kind="inspect",
                ),
            ),
        )
        with pytest.raises(MemoryLifecycleError, match="lacks required capabilities"):
            run_lifecycle_plan(port, plan)
