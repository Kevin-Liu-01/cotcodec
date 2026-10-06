#!/usr/bin/env python3
"""Contained lifecycle falsifier for TokenMizer's checkpoint manager."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

EXPECTED_REVISION = "131e3d1569de3e8f70c198ade4e791b47f63dc41"
EXPECTED_STATUS = "TOKENMIZER_ACTIVE_INACTIVE_ADMISSION_KILLED"


def _sha(value: Any) -> str:
    data = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def _install_source(source_root: Path) -> None:
    required = {
        "LICENSE",
        "pyproject.toml",
        "tokenmizer/checkpoints/manager.py",
        "tokenmizer/graph_memory/graph.py",
    }
    if source_root.is_symlink() or not source_root.is_dir():
        raise RuntimeError("source root is invalid")
    missing = sorted(name for name in required if not (source_root / name).is_file())
    if missing:
        raise RuntimeError(f"TokenMizer source is incomplete: {missing}")
    sys.path.insert(0, str(source_root))


def _node_labels(checkpoint: Any) -> list[str]:
    return sorted(node["label"] for node in checkpoint.graph_snapshot["nodes"])


def _added_labels(checkpoint: Any) -> list[str]:
    return sorted(node["label"] for node in checkpoint.graph_diff["added"])


def _build_graph(root: Path, session_id: str, labels: list[str]) -> Any:
    from tokenmizer.graph_memory.graph import GraphMemory, NodeStatus, NodeType

    graph = GraphMemory(session_id, storage_dir=str(root))
    for index, label in enumerate(labels):
        node_type = NodeType.GOAL if index == 0 else NodeType.TASK
        status = NodeStatus.IN_PROGRESS
        node_id = graph.add_node(node_type, label, status=status, importance=0.9)
        if not node_id:
            raise RuntimeError(f"TokenMizer rejected doctor node: {label}")
    graph._persist(force=True)
    return graph


def _continuous_diff(root: Path) -> dict[str, Any]:
    from tokenmizer.checkpoints.manager import CheckpointManager

    root.mkdir(parents=True, exist_ok=False)
    session = "continuous-session"
    manager = CheckpointManager(storage_dir=str(root))
    graph = _build_graph(root, session, ["Preserve checkpoint continuity"])
    first = manager.create(session, [], graph, 0.50, trigger="manual")
    graph = _build_graph(
        root,
        session,
        ["Add the second checkpoint fact"],
    )
    second = manager.create(session, [], graph, 0.75, trigger="manual")
    return {
        "first_snapshot": _node_labels(first),
        "second_snapshot": _node_labels(second),
        "second_added": _added_labels(second),
    }


def _restart_diff(root: Path) -> dict[str, Any]:
    from tokenmizer.checkpoints.manager import CheckpointManager

    root.mkdir(parents=True, exist_ok=False)
    session = "restart-session"
    manager = CheckpointManager(storage_dir=str(root))
    graph = _build_graph(root, session, ["Preserve checkpoint continuity"])
    first = manager.create(session, [], graph, 0.50, trigger="manual")

    # A fresh manager loads checkpoints but not its prior graph snapshot. The
    # next diff therefore relabels the entire old snapshot as newly added.
    manager = CheckpointManager(storage_dir=str(root))
    graph = _build_graph(root, session, ["Add the second checkpoint fact"])
    second = manager.create(session, [], graph, 0.75, trigger="manual")
    isolated = _build_graph(root, "isolated-session", [])
    latest = CheckpointManager(storage_dir=str(root)).get_latest(session)
    return {
        "first_snapshot": _node_labels(first),
        "second_snapshot": _node_labels(second),
        "second_added": _added_labels(second),
        "fresh_process_latest_matches": latest is not None
        and latest.resume_standard == second.resume_standard,
        "isolated_session_empty": len(isolated._nodes) == 0,
    }


def _retry_and_corruption(root: Path) -> dict[str, Any]:
    from tokenmizer.checkpoints.manager import CheckpointManager

    root.mkdir(parents=True, exist_ok=False)
    manager = CheckpointManager(storage_dir=str(root))
    graph = _build_graph(root, "retry-canary", ["Retain retry canary state"])
    manager.create("retry-canary", [], graph, 0.80, trigger="manual")
    manager.create("retry-canary", [], graph, 0.80, trigger="manual")
    duplicate_rows = len(manager.list_checkpoints("retry-canary"))
    has_native_purge = any(
        callable(getattr(manager, name, None))
        for name in ("purge", "delete_session", "clear_session")
    )

    db_path = root / "checkpoints.db"
    with sqlite3.connect(db_path) as connection:
        before_corruption = connection.execute(
            "SELECT COUNT(*) FROM checkpoints"
        ).fetchone()[0]
    db_path.write_bytes(b"TOKENMIZER_CORRUPTED_CHECKPOINT_DB")
    recovered = CheckpointManager(storage_dir=str(root))
    after_recovery = len(recovered.list_checkpoints("retry-canary"))
    return {
        "duplicate_rows": duplicate_rows,
        "has_native_purge": has_native_purge,
        "rows_before_corruption": before_corruption,
        "rows_after_corrupt_recovery": after_recovery,
    }


def run(state_root: Path) -> dict[str, Any]:
    if state_root.exists():
        raise RuntimeError("state root must not already exist")
    state_root.mkdir(parents=True)
    continuous = _continuous_diff(state_root / "continuous")
    restarted = _restart_diff(state_root / "restart")
    failure = _retry_and_corruption(state_root / "failure")

    checks = {
        "continuous_diff_tracks_only_new_node": len(continuous["second_added"]) == 1,
        "restart_diff_relabels_old_node_as_added": len(restarted["second_added"]) == 2,
        "restart_snapshot_content_preserved": restarted["second_snapshot"]
        == continuous["second_snapshot"],
        "fresh_process_resume_text_preserved": restarted[
            "fresh_process_latest_matches"
        ],
        "session_isolation_preserved": restarted["isolated_session_empty"],
        "manual_retry_creates_duplicate_checkpoint": failure["duplicate_rows"] == 2,
        "corrupt_recovery_deletes_all_checkpoints": failure[
            "rows_before_corruption"
        ]
        == 2
        and failure["rows_after_corrupt_recovery"] == 0,
        "native_scoped_purge_absent": failure["has_native_purge"] is False,
    }
    if not all(checks.values()):
        raise RuntimeError(f"TokenMizer lifecycle semantics drifted: {checks}")
    projection = {
        "checks": checks,
        "continuous_second_added": continuous["second_added"],
        "restart_second_added": restarted["second_added"],
        "snapshot_labels": restarted["second_snapshot"],
        "duplicate_checkpoint_rows": failure["duplicate_rows"],
        "post_corruption_checkpoint_rows": failure["rows_after_corrupt_recovery"],
    }
    return {
        "schema_version": 1,
        "source_revision": EXPECTED_REVISION,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "active_inactive_h100_admission": False,
        "context_compaction_quality_evaluated": False,
        "provider_calls": 0,
        "model_backend_calls": 0,
        "projection": projection,
        "projection_sha256": _sha(projection),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    _install_source(args.source_root)
    report = run(args.state_root)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
