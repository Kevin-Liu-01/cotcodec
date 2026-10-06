from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "infra/research/past-bench/checkpoint_runtime.py"
SPEC = importlib.util.spec_from_file_location("past_bench_checkpoint_runtime", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CheckpointStore = MODULE.CheckpointStore
PastCheckpointError = MODULE.PastCheckpointError


def _identity() -> dict[str, object]:
    return {
        "source_revision": "a" * 40,
        "source_receipt_sha256": "b" * 64,
        "runtime_receipt_sha256": "c" * 64,
        "image_id": f"sha256:{'d' * 64}",
        "sealed_sbom_sha256": "e" * 64,
        "model_receipt_sha256": "f" * 64,
        "experiment_sha256": "1" * 64,
        "argv": ["past-bench", "evolve", "--family", "memory_ability/SM01_preference_adoption"],
    }


def _store(tmp_path: Path, *, trace_name: str = "trace", identity=None) -> object:
    trace = tmp_path / trace_name
    trace.mkdir()
    return CheckpointStore(
        checkpoint_root=tmp_path / "checkpoints",
        trace_root=trace,
        identity=identity or _identity(),
        marker=tmp_path / "checkpoint.marker",
    )


def test_checkpoint_round_trip_and_two_generation_retention(tmp_path: Path) -> None:
    store = _store(tmp_path)
    trace = tmp_path / "trace"
    (trace / "family_homes").mkdir()
    (trace / "family_homes/state.json").write_text('{"step":1}\n', encoding="utf-8")
    first = store.commit(
        stage="episode-complete",
        variant="with_persistence",
        completed_episode=1,
        episode_results=[{"index": 1, "score": 0.5}],
    )
    (trace / "family_homes/state.json").write_text('{"step":2}\n', encoding="utf-8")
    second = store.commit(
        stage="episode-complete",
        variant="with_persistence",
        completed_episode=2,
        episode_results=[{"index": 1}, {"index": 2}],
    )
    (trace / "family_homes/state.json").write_text('{"step":3}\n', encoding="utf-8")
    third = store.commit(
        stage="variant-complete",
        variant="with_persistence",
        completed_episode=2,
        episode_results=[{"index": 1}, {"index": 2}],
    )

    assert first["receipt_sha256"] != second["receipt_sha256"] != third["receipt_sha256"]
    generations = sorted((tmp_path / "checkpoints").glob("generation-*"))
    assert len(generations) == 2
    marker = json.loads((tmp_path / "checkpoint.marker").read_text())
    assert marker["receipt_sha256"] == third["receipt_sha256"]
    in_place = store.restore_latest()
    assert in_place["receipt"]["receipt_sha256"] == third["receipt_sha256"]

    fresh_trace = tmp_path / "resumed-trace"
    resumed = CheckpointStore(
        checkpoint_root=tmp_path / "checkpoints",
        trace_root=fresh_trace,
        identity=_identity(),
    ).restore_latest()
    assert resumed["state"]["stage"] == "variant-complete"
    assert (fresh_trace / "family_homes/state.json").read_text() == '{"step":3}\n'


def test_checkpoint_rejects_identity_and_payload_drift(tmp_path: Path) -> None:
    store = _store(tmp_path)
    trace = tmp_path / "trace"
    (trace / "result.json").write_text("{}\n", encoding="utf-8")
    store.commit(
        stage="episode-complete",
        variant="with_persistence",
        completed_episode=1,
        episode_results=[{"index": 1}],
    )

    drift = _identity()
    drift["model_receipt_sha256"] = "9" * 64
    with pytest.raises(PastCheckpointError, match="identity drifted"):
        CheckpointStore(
            checkpoint_root=tmp_path / "checkpoints",
            trace_root=tmp_path / "new-trace",
            identity=drift,
        ).restore_latest()

    latest = json.loads((tmp_path / "checkpoints/LATEST").read_text())
    generation = tmp_path / "checkpoints" / latest["generation"]
    (generation / "payload/result.json").write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(PastCheckpointError, match="payload differs"):
        CheckpointStore(
            checkpoint_root=tmp_path / "checkpoints",
            trace_root=tmp_path / "another-trace",
            identity=_identity(),
        ).restore_latest()


def test_checkpoint_rejects_symlinks_and_drifted_restore(tmp_path: Path) -> None:
    store = _store(tmp_path)
    trace = tmp_path / "trace"
    target = trace / "target.txt"
    target.write_text("state", encoding="utf-8")
    (trace / "link.txt").symlink_to(target)
    with pytest.raises(PastCheckpointError, match="symlink"):
        store.commit(
            stage="episode-complete",
            variant="with_persistence",
            completed_episode=1,
            episode_results=[],
        )

    (trace / "link.txt").unlink()
    store.commit(
        stage="episode-complete",
        variant="with_persistence",
        completed_episode=1,
        episode_results=[],
    )
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "foreign").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(PastCheckpointError, match="differs from the latest"):
        CheckpointStore(
            checkpoint_root=tmp_path / "checkpoints",
            trace_root=occupied,
            identity=_identity(),
        ).restore_latest()


def test_checkpoint_identity_has_exact_roster(tmp_path: Path) -> None:
    identity = _identity()
    identity["unexpected"] = True
    with pytest.raises(PastCheckpointError, match="field roster"):
        _store(tmp_path, identity=identity)
