from __future__ import annotations

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
    PROJECT_ROOT / "infra" / "memory-baselines" / "graphiti_lifecycle_sidecar.py"
)


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
    state_root = tmp_path / "state"
    environment = {
        "COTCODEC_MEMORY_STATE_ROOT": str(state_root),
        "COTCODEC_MEMORY_EMBEDDING_BASE_URL": f"http://{host}:{port}/v1",
        "COTCODEC_MEMORY_EMBEDDING_MODEL": "test-embedding",
        "COTCODEC_MEMORY_EMBEDDING_REVISION": "test-token-hash-v1",
        "COTCODEC_MEMORY_EMBEDDING_DIMENSIONS": "16",
    }
    try:
        yield environment, state_root
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_graphiti_lifecycle_restart_update_delete_and_purge(
    embedding_environment,
) -> None:
    environment, state_root = embedding_environment
    scope = "graphiti-lifecycle/restart"
    with SubprocessLifecyclePort(
        (sys.executable, str(SIDECAR)), timeout_seconds=45, environment=environment
    ) as first:
        assert first.receipt.system_id == "graphiti-explicit-triplet-lifecycle-v1"
        assert set(first.receipt.capabilities) == {
            LifecycleCapability.APPLY,
            LifecycleCapability.QUERY,
            LifecycleCapability.CHECKPOINT,
            LifecycleCapability.RESTORE,
            LifecycleCapability.INSPECT,
            LifecycleCapability.PURGE,
        }
        first.execute(_command("restart.begin", scope=scope, step=0, kind="begin"))
        written = first.execute(
            _command(
                "restart.write",
                scope=scope,
                step=1,
                kind="apply",
                event=_event(
                    "restart.event.write",
                    step=1,
                    kind="write",
                    value="cedar harbor",
                ),
            )
        )
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
        checkpoint = first.execute(
            _command("restart.checkpoint", scope=scope, step=3, kind="checkpoint")
        ).checkpoint
        assert checkpoint is not None
        assert written.summary.archive_record_ids == ("record-1",)
        assert [item.record_id for item in queried.evidence] == ["record-1"]

    with SubprocessLifecyclePort(
        (sys.executable, str(SIDECAR)), timeout_seconds=45, environment=environment
    ) as restarted:
        restored = restarted.execute(
            _command(
                "restart.restore",
                scope=scope,
                step=0,
                kind="restore",
                checkpoint=checkpoint,
            )
        )
        assert restored.post_durable_state_sha256 == written.post_durable_state_sha256
        resumed = restarted.execute(
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
        assert resumed.evidence[0].record_id == queried.evidence[0].record_id
        updated = restarted.execute(
            _command(
                "restart.update",
                scope=scope,
                step=4,
                kind="apply",
                event=_event(
                    "restart.event.update",
                    step=4,
                    kind="update",
                    value="amber harbor",
                ),
            )
        )
        assert updated.summary.lineage == (
            ("record-1", ("restart.event.write", "restart.event.update")),
        )
        restarted.execute(
            _command(
                "restart.delete",
                scope=scope,
                step=5,
                kind="apply",
                event=_event(
                    "restart.event.delete", step=5, kind="delete", value=None
                ),
            )
        )
        restarted.execute(
            _command("restart.purge", scope=scope, step=6, kind="purge")
        )
        purged = restarted.execute(
            _command("restart.inspect", scope=scope, step=7, kind="inspect")
        )
        assert purged.summary.archive_record_ids == ()

    assert not any(
        b"amber harbor" in path.read_bytes()
        for path in state_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def test_graphiti_lifecycle_branch_isolation_idempotency_and_capability_refusal(
    embedding_environment,
) -> None:
    environment, _ = embedding_environment
    with SubprocessLifecyclePort(
        (sys.executable, str(SIDECAR)), timeout_seconds=45, environment=environment
    ) as port:
        roots = {}
        for suffix in ("a", "b"):
            scope = f"graphiti-lifecycle/branch-{suffix}"
            port.execute(_command(f"{suffix}.begin", scope=scope, step=0, kind="begin"))
            command = _command(
                f"{suffix}.write",
                scope=scope,
                step=1,
                kind="apply",
                event=_event(
                    "branch.shared.write", step=1, kind="write", value="saffron echo"
                ),
            )
            receipt = port.execute(command)
            assert port.execute(command) == receipt
            roots[suffix] = (
                receipt.post_logical_state_sha256,
                receipt.post_durable_state_sha256,
            )
        assert roots["a"] == roots["b"]

        before = port.execute(
            _command(
                "b.inspect-before",
                scope="graphiti-lifecycle/branch-b",
                step=2,
                kind="inspect",
            )
        )
        port.execute(
            _command(
                "a.update",
                scope="graphiti-lifecycle/branch-a",
                step=2,
                kind="apply",
                event=_event(
                    "branch.a.update", step=2, kind="update", value="indigo echo"
                ),
            )
        )
        after = port.execute(
            _command(
                "b.inspect-after",
                scope="graphiti-lifecycle/branch-b",
                step=3,
                kind="inspect",
            )
        )
        assert before.post_durable_state_sha256 == after.post_durable_state_sha256

        maintain = LifecycleCommand(
            command_id="unsupported.maintain",
            idempotency_key="unsupported.maintain.idempotency",
            session_scope="graphiti-lifecycle/unsupported",
            step=1,
            kind="maintain",
            maintenance=LifecycleMaintenance(
                maintenance_id="unsupported-maintenance", step=1, trigger="manual"
            ),
        )
        plan = LifecyclePlan(
            plan_id="unsupported-plan",
            expected_system_id="graphiti-explicit-triplet-lifecycle-v1",
            active_slots=4,
            commands=(
                _command(
                    "unsupported.begin",
                    scope="graphiti-lifecycle/unsupported",
                    step=0,
                    kind="begin",
                ),
                maintain,
                _command(
                    "unsupported.inspect",
                    scope="graphiti-lifecycle/unsupported",
                    step=2,
                    kind="inspect",
                ),
            ),
        )
        with pytest.raises(MemoryLifecycleError, match="lacks required capabilities"):
            run_lifecycle_plan(port, plan)
