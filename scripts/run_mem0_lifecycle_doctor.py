#!/usr/bin/env python3
"""Run one clean-state Mem0 ``memory-lifecycle-v1`` CPU doctor."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.lifecycle import (  # noqa: E402
    LifecycleCapability,
    LifecycleCommand,
    LifecycleEvent,
    LifecycleQuery,
    MemoryLifecycleError,
    SubprocessLifecyclePort,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.run_deterministic_embedding_server import (  # noqa: E402
    EmbeddingServer,
)
from scripts.validate_mem0_lifecycle_experiment import (  # noqa: E402
    validate_experiment_contract,
)

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage3-mem0-native-lifecycle-doctor.yaml"
)
SIDECAR = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "mem0_lifecycle_sidecar.py"
)
MEM0_REVISION = "71f2ebefa3494da21550fb525216818776cde67f"
MEM0_ARCHIVE_SHA256 = "c577ecf9a460b0fa581032037ccbfd887f7a7d0afa0fc091d13fd8b692089b12"
MEM0_SOURCE_CONTEXT = Path("/opt/mem0-source/.cotcodec-source-context.json")
STATUS = "BLOCKED_ADAPTER_CRASH_RECOVERY"


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _source_receipt() -> dict[str, Any]:
    if not MEM0_SOURCE_CONTEXT.is_file() or MEM0_SOURCE_CONTEXT.is_symlink():
        raise RuntimeError("Mem0 source-context receipt is absent from the image")
    receipt = json.loads(MEM0_SOURCE_CONTEXT.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise RuntimeError("Mem0 source-context receipt is invalid")
    payload = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    expected_receipt = sha256_text(canonical_json(payload))
    if (
        receipt.get("schema_version") != "1.0"
        or receipt.get("system_id") != "mem0"
        or receipt.get("revision") != MEM0_REVISION
        or receipt.get("source_archive_sha256") != MEM0_ARCHIVE_SHA256
        or receipt.get("receipt_sha256") != expected_receipt
    ):
        raise RuntimeError("Mem0 source-context receipt drifted")
    return receipt


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


def _query(command_id: str, *, scope: str, step: int, text: str) -> LifecycleCommand:
    return _command(
        command_id,
        scope=scope,
        step=step,
        kind="query",
        query=LifecycleQuery(
            query_id=f"{command_id}.payload",
            step=step,
            text=text,
            top_k=1,
            max_archive_reads=1,
            max_injected_tokens=256,
        ),
    )


def _environment(root: Path, base_url: str) -> dict[str, str]:
    return {
        "COTCODEC_MEMORY_STATE_ROOT": str(root),
        "COTCODEC_MEMORY_EMBEDDING_BASE_URL": base_url,
        "COTCODEC_MEMORY_EMBEDDING_MODEL": "cotcodec-deterministic-embedding-v1",
        "COTCODEC_MEMORY_EMBEDDING_REVISION": "cotcodec-loopback-token-hash-v1",
        "COTCODEC_MEMORY_EMBEDDING_DIMENSIONS": "32",
    }


def _file_hits(root: Path, needles: tuple[bytes, ...]) -> list[str]:
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if any(needle in data for needle in needles):
            hits.append(path.relative_to(root).as_posix())
    return hits


def _file_hit_proofs(
    root: Path, needles: tuple[bytes, ...]
) -> dict[str, list[dict[str, Any]]]:
    """Capture bounded byte windows proving each reported plaintext hit.

    The native state lives in a temporary directory and is deliberately removed
    after the doctor.  Persist a small, self-verifying window around the first
    occurrence of every canary in every hit file so the evidence sealer can
    validate the negative without retaining the full backend database.
    """

    proofs: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        entries: list[dict[str, Any]] = []
        for needle in needles:
            offset = data.find(needle)
            if offset < 0:
                continue
            window_start = max(0, offset - 64)
            window_end = min(len(data), offset + len(needle) + 64)
            window = data[window_start:window_end]
            entries.append(
                {
                    "file_bytes": len(data),
                    "file_sha256": hashlib.sha256(data).hexdigest(),
                    "needle_sha256": hashlib.sha256(needle).hexdigest(),
                    "offset": offset,
                    "window_base64": base64.b64encode(window).decode("ascii"),
                    "window_sha256": hashlib.sha256(window).hexdigest(),
                    "window_start": window_start,
                }
            )
        if entries:
            proofs[path.relative_to(root).as_posix()] = entries
    return proofs


def _evidence_identity(value: Any) -> dict[str, Any]:
    payload = value.model_dump(mode="json")
    payload.pop("score")
    return payload


def _run_doctor(state_root: Path, base_url: str) -> dict[str, Any]:
    environment = _environment(state_root, base_url)
    command = (sys.executable, str(SIDECAR))
    costs: list[dict[str, Any]] = []

    restart_scope = "mem0-doctor/restart"
    with SubprocessLifecyclePort(command, timeout_seconds=30, environment=environment) as port:
        system_receipt = port.receipt.model_dump(mode="json")
        begin = port.execute(
            _command("restart.begin", scope=restart_scope, step=0, kind="begin")
        )
        write = port.execute(
            _command(
                "restart.write",
                scope=restart_scope,
                step=1,
                kind="apply",
                event=_event(
                    "restart.event.write",
                    step=1,
                    kind="write",
                    value="cedar-harbor-canary-731",
                ),
            )
        )
        first_query = port.execute(
            _query(
                "restart.query-first",
                scope=restart_scope,
                step=2,
                text="traveler destination cedar harbor canary",
            )
        )
        checkpoint_receipt = port.execute(
            _command(
                "restart.checkpoint", scope=restart_scope, step=3, kind="checkpoint"
            )
        )
        checkpoint = checkpoint_receipt.checkpoint
        if checkpoint is None:
            raise RuntimeError("Mem0 checkpoint operation returned no checkpoint")
        costs.extend(
            entry.cost.model_dump(mode="json")
            for entry in (begin, write, first_query, checkpoint_receipt)
        )

    with SubprocessLifecyclePort(command, timeout_seconds=30, environment=environment) as port:
        restored = port.execute(
            _command(
                "restart.restore",
                scope=restart_scope,
                step=0,
                kind="restore",
                checkpoint=checkpoint,
            )
        )
        resumed_query = port.execute(
            _query(
                "restart.query-resumed",
                scope=restart_scope,
                step=2,
                text="traveler destination cedar harbor canary",
            )
        )
        update = port.execute(
            _command(
                "restart.update",
                scope=restart_scope,
                step=3,
                kind="apply",
                event=_event(
                    "restart.event.update",
                    step=3,
                    kind="update",
                    value="amber-harbor-canary-947",
                ),
            )
        )
        updated_query = port.execute(
            _query(
                "restart.query-updated",
                scope=restart_scope,
                step=4,
                text="traveler destination amber harbor canary",
            )
        )
        delete = port.execute(
            _command(
                "restart.delete",
                scope=restart_scope,
                step=5,
                kind="apply",
                event=_event(
                    "restart.event.delete", step=5, kind="delete", value=None
                ),
            )
        )
        empty_query = port.execute(
            _query(
                "restart.query-deleted",
                scope=restart_scope,
                step=6,
                text="traveler destination amber harbor canary",
            )
        )
        port.execute(
            _command("restart.purge", scope=restart_scope, step=7, kind="purge")
        )
        purged = port.execute(
            _command("restart.inspect", scope=restart_scope, step=8, kind="inspect")
        )
        costs.extend(
            entry.cost.model_dump(mode="json")
            for entry in (
                restored,
                resumed_query,
                update,
                updated_query,
                delete,
                empty_query,
                purged,
            )
        )

    branch_roots: dict[str, tuple[str, str]] = {}
    with SubprocessLifecyclePort(command, timeout_seconds=30, environment=environment) as port:
        for suffix in ("a", "b"):
            scope = f"mem0-doctor/branch-{suffix}"
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
                        value="saffron-branch-canary-221",
                    ),
                )
            )
            branch_roots[suffix] = (
                receipt.post_logical_state_sha256,
                receipt.post_durable_state_sha256,
            )
        before_b = port.execute(
            _command(
                "b.inspect-before",
                scope="mem0-doctor/branch-b",
                step=2,
                kind="inspect",
            )
        )
        port.execute(
            _command(
                "a.update",
                scope="mem0-doctor/branch-a",
                step=2,
                kind="apply",
                event=_event(
                    "branch.a.update",
                    step=2,
                    kind="update",
                    value="indigo-branch-canary-442",
                ),
            )
        )
        after_b = port.execute(
            _command(
                "b.inspect-after",
                scope="mem0-doctor/branch-b",
                step=3,
                kind="inspect",
            )
        )
        for suffix in ("a", "b"):
            scope = f"mem0-doctor/branch-{suffix}"
            port.execute(
                _command(f"{suffix}.purge", scope=scope, step=4, kind="purge")
            )
            port.execute(
                _command(f"{suffix}.inspect", scope=scope, step=5, kind="inspect")
            )

    idempotency_scope = "mem0-doctor/idempotency"
    with SubprocessLifecyclePort(command, timeout_seconds=30, environment=environment) as port:
        port.execute(
            _command("idempotency.begin", scope=idempotency_scope, step=0, kind="begin")
        )
        idempotent_command = _command(
            "idempotency.write",
            scope=idempotency_scope,
            step=1,
            kind="apply",
            event=_event(
                "idempotency.event.write",
                step=1,
                kind="write",
                value="violet-idempotency-canary-661",
            ),
        )
        first_idempotent = port.execute(idempotent_command)
        repeated_idempotent = port.execute(idempotent_command)
        divergent_rejected = False
        assert idempotent_command.event is not None
        drifted = idempotent_command.model_copy(
            update={
                "event": idempotent_command.event.model_copy(
                    update={"value": "tampered-idempotency"}
                )
            }
        )
        try:
            port.execute(drifted)
        except MemoryLifecycleError as exc:
            divergent_rejected = "different bytes" in str(exc)
        port.execute(
            _command(
                "idempotency.purge", scope=idempotency_scope, step=2, kind="purge"
            )
        )
        port.execute(
            _command(
                "idempotency.inspect", scope=idempotency_scope, step=3, kind="inspect"
            )
        )

    crash_scope = "mem0-doctor/crash"
    crash_environment = {
        **environment,
        "COTCODEC_MEM0_LIFECYCLE_CRASH_HOOK": "crash.write:after-native",
    }
    crash_observed = False
    with SubprocessLifecyclePort(
        command, timeout_seconds=30, environment=crash_environment
    ) as port:
        port.execute(_command("crash.begin", scope=crash_scope, step=0, kind="begin"))
        try:
            port.execute(
                _command(
                    "crash.write",
                    scope=crash_scope,
                    step=1,
                    kind="apply",
                    event=_event(
                        "crash.event.write",
                        step=1,
                        kind="write",
                        value="crash-window-canary-883",
                    ),
                )
            )
        except MemoryLifecycleError as exc:
            crash_observed = "exited during execute" in str(exc)
    pending_fail_closed = False
    with SubprocessLifecyclePort(command, timeout_seconds=30, environment=environment) as port:
        try:
            port.execute(
                _command("crash.resume", scope=crash_scope, step=0, kind="begin")
            )
        except MemoryLifecycleError as exc:
            pending_fail_closed = "ambiguous interrupted operation" in str(exc)

    purged_scope_hits = _file_hits(
        state_root,
        (
            b"cedar-harbor-canary-731",
            b"amber-harbor-canary-947",
            b"saffron-branch-canary-221",
            b"indigo-branch-canary-442",
            b"violet-idempotency-canary-661",
        ),
    )
    crash_scope_needle = b"crash-window-canary-883"
    crash_scope_hits = _file_hits(state_root, (crash_scope_needle,))
    crash_scope_proofs = _file_hit_proofs(state_root, (crash_scope_needle,))
    capabilities = set(system_receipt["capabilities"])
    first_evidence = list(first_query.evidence)
    resumed_evidence = list(resumed_query.evidence)
    restart_score_delta = (
        abs(first_evidence[0].score - resumed_evidence[0].score)
        if len(first_evidence) == len(resumed_evidence) == 1
        else float("inf")
    )
    gates = {
        "source_and_adapter_receipts_exact": (
            system_receipt["system_id"] == "mem0-native-lifecycle-v1"
            and system_receipt["implementation_revision"] == MEM0_REVISION
        ),
        "all_resident_records_are_archive": (
            write.summary.active_record_ids == ()
            and write.summary.archive_record_ids == ("record-1",)
        ),
        "checkpoint_verifies_persisted_state": (
            restored.post_logical_state_sha256 == write.post_logical_state_sha256
            and restored.post_durable_state_sha256 == write.post_durable_state_sha256
        ),
        "restart_evidence_identity_exact_and_score_delta_le_1e-6": (
            [_evidence_identity(entry) for entry in first_evidence]
            == [_evidence_identity(entry) for entry in resumed_evidence]
            and restart_score_delta <= 1e-6
        ),
        "update_preserves_transitive_lineage": update.summary.lineage
        == (("record-1", ("restart.event.write", "restart.event.update")),),
        "updated_value_retrievable": bool(updated_query.evidence)
        and "amber-harbor-canary-947" in updated_query.evidence[0].text,
        "delete_removes_record": (
            delete.summary.archive_record_ids == () and not empty_query.evidence
        ),
        "purge_removes_logical_state": (
            purged.summary.active_record_ids == ()
            and purged.summary.archive_record_ids == ()
        ),
        "purged_scopes_remove_plaintext_canaries": not purged_scope_hits,
        "equal_prefix_branch_roots_match": branch_roots["a"] == branch_roots["b"],
        "branch_mutation_does_not_change_sibling": (
            before_b.post_logical_state_sha256 == after_b.post_logical_state_sha256
            and before_b.post_durable_state_sha256 == after_b.post_durable_state_sha256
        ),
        "idempotent_retry_receipt_exact": first_idempotent == repeated_idempotent,
        "divergent_retry_rejected": divergent_rejected,
        "maintain_and_feedback_capabilities_absent": (
            LifecycleCapability.MAINTAIN.value not in capabilities
            and LifecycleCapability.FEEDBACK.value not in capabilities
        ),
        "post_native_crash_observed": crash_observed,
        "interrupted_operation_fail_closed": pending_fail_closed,
        "crash_scope_plaintext_proofs_capture_all_hits": (
            set(crash_scope_proofs) == set(crash_scope_hits)
            and all(crash_scope_proofs.values())
        ),
    }
    if not all(gates.values()):
        failed = sorted(name for name, passed in gates.items() if not passed)
        raise RuntimeError(f"Mem0 lifecycle conformance gates failed: {failed}")
    stable_projection = {
        "system_receipt": system_receipt,
        "restart": {
            "write_logical_root": write.post_logical_state_sha256,
            "write_durable_root": write.post_durable_state_sha256,
            "first_evidence": [entry.model_dump(mode="json") for entry in first_query.evidence],
            "resumed_evidence": [
                entry.model_dump(mode="json") for entry in resumed_query.evidence
            ],
            "restart_score_delta": restart_score_delta,
            "updated_lineage": [list(item) for item in update.summary.lineage],
            "deleted_evidence_count": len(empty_query.evidence),
        },
        "branch_roots": {key: list(value) for key, value in sorted(branch_roots.items())},
        "gates": gates,
        "crash_recovery": {
            "fail_closed": pending_fail_closed,
            "continuation_recovered": False,
            "plaintext_residue_cleared": not crash_scope_hits,
            "plaintext_residue_file_count": len(crash_scope_hits),
        },
    }
    return {
        "stable_projection": stable_projection,
        "stable_projection_sha256": sha256_text(canonical_json(stable_projection)),
        "costs": costs,
        "purged_scope_plaintext_hits": purged_scope_hits,
        "crash_scope_plaintext_hits": crash_scope_hits,
        "crash_scope_plaintext_proofs": crash_scope_proofs,
        "embedding_server": {
            "loopback_only": True,
            "model": "cotcodec-deterministic-embedding-v1",
            "dimensions": 32,
        },
    }


def run(experiment: Path, output: Path) -> dict[str, Any]:
    experiment_sha = validate_experiment_contract(experiment)
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    source_receipt = _source_receipt()
    server = EmbeddingServer(
        ("127.0.0.1", 0),
        model_id="cotcodec-deterministic-embedding-v1",
        dimensions=32,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with tempfile.TemporaryDirectory(prefix="cotcodec-mem0-lifecycle-") as root:
            result = _run_doctor(Path(root), f"http://{host}:{port}/v1")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    code_receipt = {
        str(path.relative_to(PROJECT_ROOT)): {
            "sha256": _sha256_path(path),
            "bytes": path.stat().st_size,
        }
        for path in (
            SIDECAR,
            PROJECT_ROOT / "infra" / "memory-baselines" / "mem0_sidecar.py",
            PROJECT_ROOT / "harness" / "memory_trials" / "lifecycle.py",
            PROJECT_ROOT / "scripts" / "run_mem0_lifecycle_doctor.py",
            PROJECT_ROOT / "scripts" / "validate_mem0_lifecycle_experiment.py",
        )
    }
    runtime = {
        "container_image_id": os.environ.get("COTCODEC_CONTAINER_IMAGE_ID"),
        "containerized": os.environ.get("COTCODEC_CONTAINERIZED") == "1",
        "network_mode": os.environ.get("COTCODEC_CONTAINER_NETWORK_MODE", "host"),
        "platform_machine": platform.machine(),
        "platform_system": platform.system(),
        "python_version": platform.python_version(),
        "scheduler_job_id": os.environ.get("SLURM_JOB_ID"),
        "sudo_used": False,
    }
    report = {
        "schema_version": 1,
        "study": "mem0-native-lifecycle-doctor-v1",
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "blocked",
        "reason": (
            "native CRUD, restart verification, branch isolation, idempotency, and "
            "purge pass, but a crash after native mutation leaves an ambiguous "
            "pending journal that cannot resume and whose residue is reported "
            "separately"
        ),
        "experiment_sha256": experiment_sha,
        "source_receipt": source_receipt,
        "runtime": runtime,
        "code_receipt": code_receipt,
        **result,
    }
    output.mkdir(parents=True)
    _write_once(output / "report.json", report)
    artifacts = {
        "report.json": {
            "sha256": _sha256_path(output / "report.json"),
            "bytes": (output / "report.json").stat().st_size,
        }
    }
    manifest = {
        "schema_version": 1,
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "experiment_sha256": experiment_sha,
        "artifacts": artifacts,
        "artifact_root_sha256": sha256_text(canonical_json(artifacts)),
    }
    _write_once(output / "manifest.json", manifest)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.experiment, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
