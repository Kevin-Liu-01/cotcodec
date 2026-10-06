#!/usr/bin/env python3
"""Run one contained Graphiti/FalkorDBLite lifecycle doctor."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import sys
import threading
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.lifecycle import (  # noqa: E402
    LifecycleCommand,
    LifecycleEvent,
    LifecycleQuery,
    SubprocessLifecyclePort,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.run_deterministic_embedding_server import EmbeddingServer  # noqa: E402
from scripts.validate_graphiti_lifecycle_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)

SIDECAR = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "graphiti_lifecycle_sidecar.py"
)
_SIDECAR_SPEC = importlib.util.spec_from_file_location(
    "cotcodec_graphiti_lifecycle_sidecar", SIDECAR
)
if _SIDECAR_SPEC is None or _SIDECAR_SPEC.loader is None:
    raise RuntimeError("cannot load Graphiti lifecycle sidecar")
_SIDECAR_MODULE = importlib.util.module_from_spec(_SIDECAR_SPEC)
_SIDECAR_SPEC.loader.exec_module(_SIDECAR_MODULE)
GRAPHITI_REVISION = _SIDECAR_MODULE.GRAPHITI_REVISION
GRAPHITI_SOURCE_ARCHIVE_SHA256 = _SIDECAR_MODULE.GRAPHITI_SOURCE_ARCHIVE_SHA256
GraphitiLifecyclePort = _SIDECAR_MODULE.GraphitiLifecyclePort
SOURCE_CONTEXT = Path("/opt/graphiti-source/.cotcodec-source-context.json")
STATUS = "BLOCKED_FALKORDBLITE_GROUP_FILTER_AND_CRASH_RECOVERY"


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
    if not SOURCE_CONTEXT.is_file() or SOURCE_CONTEXT.is_symlink():
        raise RuntimeError("Graphiti source-context receipt is absent")
    receipt = json.loads(SOURCE_CONTEXT.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise RuntimeError("Graphiti source-context receipt is invalid")
    payload = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if (
        receipt.get("schema_version") != "1.0"
        or receipt.get("system_id") != "graphiti"
        or receipt.get("revision") != GRAPHITI_REVISION
        or receipt.get("source_archive_sha256") != GRAPHITI_SOURCE_ARCHIVE_SHA256
        or receipt.get("receipt_sha256") != sha256_text(canonical_json(payload))
    ):
        raise RuntimeError("Graphiti source-context receipt drifted")
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
        "HOME": str(root.parent),
        "XDG_CACHE_HOME": str(root.parent / ".cache"),
        "COTCODEC_MEMORY_STATE_ROOT": str(root),
        "COTCODEC_MEMORY_EMBEDDING_BASE_URL": base_url,
        "COTCODEC_MEMORY_EMBEDDING_MODEL": "cotcodec-deterministic-embedding-v1",
        "COTCODEC_MEMORY_EMBEDDING_REVISION": "cotcodec-loopback-token-hash-v1",
        "COTCODEC_MEMORY_EMBEDDING_DIMENSIONS": "32",
    }


def _file_hits(root: Path, needles: tuple[bytes, ...]) -> list[str]:
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if any(needle in data for needle in needles):
                hits.append(path.relative_to(root).as_posix())
    return hits


def _identity(evidence) -> dict[str, Any]:
    value = evidence.model_dump(mode="json")
    value.pop("score")
    return value


def _run(state_root: Path, base_url: str) -> dict[str, Any]:
    environment = _environment(state_root, base_url)
    command = (sys.executable, str(SIDECAR))
    costs: list[dict[str, Any]] = []
    scope = "graphiti-doctor/restart"

    with SubprocessLifecyclePort(
        command, timeout_seconds=60, environment=environment
    ) as first:
        system_receipt = first.receipt.model_dump(mode="json")
        begin = first.execute(_command("restart.begin", scope=scope, step=0, kind="begin"))
        write_command = _command(
            "restart.write",
            scope=scope,
            step=1,
            kind="apply",
            event=_event(
                "restart.event.write",
                step=1,
                kind="write",
                value="cedar-harbor-graphiti-canary-731",
            ),
        )
        write = first.execute(write_command)
        idempotent = first.execute(write_command)
        first_query = first.execute(
            _query(
                "restart.query-first",
                scope=scope,
                step=2,
                text="traveler destination cedar harbor graphiti",
            )
        )
        checkpoint_receipt = first.execute(
            _command("restart.checkpoint", scope=scope, step=3, kind="checkpoint")
        )
        checkpoint = checkpoint_receipt.checkpoint
        if checkpoint is None:
            raise RuntimeError("Graphiti checkpoint returned no checkpoint")
        costs.extend(
            item.cost.model_dump(mode="json")
            for item in (begin, write, first_query, checkpoint_receipt)
        )

    probe_port = GraphitiLifecyclePort(state_root)
    group_filter_probe = probe_port.group_filter_probe(scope)

    with SubprocessLifecyclePort(
        command, timeout_seconds=60, environment=environment
    ) as restarted:
        restore = restarted.execute(
            _command(
                "restart.restore",
                scope=scope,
                step=0,
                kind="restore",
                checkpoint=checkpoint,
            )
        )
        resumed_query = restarted.execute(
            _query(
                "restart.query-resumed",
                scope=scope,
                step=2,
                text="traveler destination cedar harbor graphiti",
            )
        )
        update = restarted.execute(
            _command(
                "restart.update",
                scope=scope,
                step=4,
                kind="apply",
                event=_event(
                    "restart.event.update",
                    step=4,
                    kind="update",
                    value="amber-harbor-graphiti-canary-914",
                ),
            )
        )
        updated_query = restarted.execute(
            _query(
                "restart.query-updated",
                scope=scope,
                step=5,
                text="traveler destination amber harbor graphiti",
            )
        )
        delete = restarted.execute(
            _command(
                "restart.delete",
                scope=scope,
                step=6,
                kind="apply",
                event=_event(
                    "restart.event.delete", step=6, kind="delete", value=None
                ),
            )
        )
        purge = restarted.execute(
            _command("restart.purge", scope=scope, step=7, kind="purge")
        )
        purged = restarted.execute(
            _command("restart.inspect", scope=scope, step=8, kind="inspect")
        )
        costs.extend(
            item.cost.model_dump(mode="json")
            for item in (
                restore,
                resumed_query,
                update,
                updated_query,
                delete,
                purge,
                purged,
            )
        )

    branch_roots: dict[str, tuple[str, str]] = {}
    with SubprocessLifecyclePort(
        command, timeout_seconds=60, environment=environment
    ) as branches:
        for suffix in ("a", "b"):
            branch_scope = f"graphiti-doctor/branch-{suffix}"
            branches.execute(
                _command(f"{suffix}.begin", scope=branch_scope, step=0, kind="begin")
            )
            receipt = branches.execute(
                _command(
                    f"{suffix}.write",
                    scope=branch_scope,
                    step=1,
                    kind="apply",
                    event=_event(
                        "branch.shared.write",
                        step=1,
                        kind="write",
                        value="saffron-graphiti-branch-canary-218",
                    ),
                )
            )
            branch_roots[suffix] = (
                receipt.post_logical_state_sha256,
                receipt.post_durable_state_sha256,
            )
        before_b = branches.execute(
            _command(
                "b.inspect-before",
                scope="graphiti-doctor/branch-b",
                step=2,
                kind="inspect",
            )
        )
        branches.execute(
            _command(
                "a.update",
                scope="graphiti-doctor/branch-a",
                step=2,
                kind="apply",
                event=_event(
                    "branch.a.update",
                    step=2,
                    kind="update",
                    value="indigo-graphiti-branch-canary-441",
                ),
            )
        )
        after_b = branches.execute(
            _command(
                "b.inspect-after",
                scope="graphiti-doctor/branch-b",
                step=3,
                kind="inspect",
            )
        )
        for suffix in ("a", "b"):
            branches.execute(
                _command(
                    f"{suffix}.purge",
                    scope=f"graphiti-doctor/branch-{suffix}",
                    step=4,
                    kind="purge",
                )
            )

    first_identity = _identity(first_query.evidence[0]) if first_query.evidence else None
    resumed_identity = (
        _identity(resumed_query.evidence[0]) if resumed_query.evidence else None
    )
    checks = {
        "system_identity_exact": (
            system_receipt["system_id"] == "graphiti-explicit-triplet-lifecycle-v1"
            and system_receipt["implementation_revision"] == GRAPHITI_REVISION
        ),
        "capabilities_exact": set(system_receipt["capabilities"])
        == {"apply", "query", "checkpoint", "restore", "inspect", "purge"},
        "all_records_archive_only": write.summary.active_record_ids == ()
        and write.summary.archive_record_ids == ("record-1",),
        "idempotent_retry_exact": idempotent == write,
        "first_query_retrieves_record": first_identity is not None,
        "fresh_process_restart_exact": (
            restore.post_durable_state_sha256 == write.post_durable_state_sha256
            and resumed_identity == first_identity
        ),
        "update_lineage_transitive": update.summary.lineage
        == (("record-1", ("restart.event.write", "restart.event.update")),),
        "updated_query_retrieves_record": bool(updated_query.evidence)
        and updated_query.evidence[0].record_id == "record-1",
        "delete_removes_record": delete.summary.archive_record_ids == (),
        "equal_branch_prefix_roots": branch_roots["a"] == branch_roots["b"],
        "branch_b_unchanged": (
            before_b.post_logical_state_sha256 == after_b.post_logical_state_sha256
            and before_b.post_durable_state_sha256
            == after_b.post_durable_state_sha256
        ),
        "purge_removes_all_scoped_state": purged.summary.archive_record_ids == ()
        and not _file_hits(
            state_root,
            (
                b"cedar-harbor-graphiti-canary-731",
                b"amber-harbor-graphiti-canary-914",
                b"saffron-graphiti-branch-canary-218",
                b"indigo-graphiti-branch-canary-441",
            ),
        ),
        "group_filter_defect_reproduced": (
            group_filter_probe["unfiltered"] == 1
            and group_filter_probe["literal_group_filter"] == 0
        ),
        "no_model_or_provider_calls": all(item["llm_calls"] == 0 for item in costs),
    }
    required_lifecycle = {
        key: value
        for key, value in checks.items()
        if key != "group_filter_defect_reproduced"
    }
    return {
        "schema_version": "1.0",
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "forbidden",
        "checks": checks,
        "lifecycle_checks_pass": all(required_lifecycle.values()),
        "group_filter_probe": group_filter_probe,
        "system_receipt": system_receipt,
        "costs": costs,
        "residue_hits": _file_hits(state_root, (b"graphiti-canary",)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_experiment_contract(args.experiment)
    source = _source_receipt()
    if not args.state_root.is_absolute() or not args.output_dir.is_absolute():
        raise SystemExit("state and output roots must be absolute")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit("output directory must be absent or empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.state_root.mkdir(parents=True, exist_ok=True)

    server = EmbeddingServer(
        ("127.0.0.1", 0),
        model_id="cotcodec-deterministic-embedding-v1",
        dimensions=32,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        report = _run(args.state_root, f"http://{host}:{port}/v1")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    report.update(
        {
            "experiment_sha256": _sha256_path(args.experiment),
            "source_context": source,
            "system": {
                "machine": platform.machine(),
                "platform": platform.platform(),
                "python": sys.version,
            },
        }
    )
    report_path = args.output_dir / "report.json"
    _write_once(report_path, report)
    manifest = {
        "schema_version": "1.0",
        "status": report["status"],
        "report_sha256": _sha256_path(report_path),
        "experiment_sha256": report["experiment_sha256"],
        "source_context_receipt_sha256": source["receipt_sha256"],
        "sidecar_sha256": _sha256_path(SIDECAR),
        "runner_sha256": _sha256_path(Path(__file__)),
    }
    manifest["manifest_sha256"] = sha256_text(canonical_json(manifest))
    _write_once(args.output_dir / "manifest.json", manifest)
    print(canonical_json({"status": report["status"], "checks": report["checks"]}))
    return 0 if report["lifecycle_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
