#!/usr/bin/env python3
"""Dependency-free in-image self-test for the PAST checkpoint primitive."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from checkpoint_runtime import CheckpointStore, PastCheckpointError


def _identity() -> dict[str, object]:
    return {
        "source_revision": "a" * 40,
        "source_receipt_sha256": "b" * 64,
        "runtime_receipt_sha256": "c" * 64,
        "image_id": f"sha256:{'d' * 64}",
        "sealed_sbom_sha256": "e" * 64,
        "model_receipt_sha256": "f" * 64,
        "experiment_sha256": "1" * 64,
        "argv": ["past-bench", "evolve", "--family", "memory_ability/SM01"],
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="past-checkpoint-selftest-") as value:
        root = Path(value)
        trace = root / "trace"
        trace.mkdir()
        (trace / "state").mkdir()
        (trace / "state/memory.md").write_text("durable preference\n", encoding="utf-8")
        store = CheckpointStore(
            checkpoint_root=root / "checkpoints",
            trace_root=trace,
            identity=_identity(),
            marker=root / "marker.json",
        )
        receipt = store.commit(
            stage="episode-complete",
            variant="with_persistence",
            completed_episode=1,
            episode_results=[{"index": 1, "passed": True}],
        )
        resumed_trace = root / "resumed"
        resumed = CheckpointStore(
            checkpoint_root=root / "checkpoints",
            trace_root=resumed_trace,
            identity=_identity(),
        ).restore_latest()
        if (resumed_trace / "state/memory.md").read_text() != "durable preference\n":
            raise RuntimeError("checkpoint restore changed payload bytes")
        if resumed["receipt"]["receipt_sha256"] != receipt["receipt_sha256"]:
            raise RuntimeError("checkpoint restore changed receipt identity")
        marker = json.loads((root / "marker.json").read_text())
        if marker["receipt_sha256"] != receipt["receipt_sha256"]:
            raise RuntimeError("checkpoint marker differs from committed generation")

        (resumed_trace / "state/memory.md").write_text("tampered\n", encoding="utf-8")
        try:
            CheckpointStore(
                checkpoint_root=root / "checkpoints",
                trace_root=resumed_trace,
                identity=_identity(),
            ).restore_latest()
        except PastCheckpointError:
            pass
        else:
            raise RuntimeError("checkpoint self-test admitted a drifted resume tree")
    print("PAST_CHECKPOINT_RUNTIME_SELFTEST_PASS")


if __name__ == "__main__":
    main()
