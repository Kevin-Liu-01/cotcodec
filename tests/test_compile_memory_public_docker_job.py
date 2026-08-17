from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.compile_memory_public_docker_job import (
    ACTOR_CONTROL_SYSTEMS,
    CONTROL_SYSTEMS,
    compile_public_docker_manifest,
)
from scripts.submit_docker_research_job import validate_manifest


def _kwargs() -> dict:
    return {
        "image_id": "sha256:" + "a" * 64,
        "run_root": "/home/kevin/cotcodec-runs/docker-research",
        "git_sha": "b" * 40,
        "source_sha256": "c" * 64,
        "model_cache_host": "/home/kevin/cotcodec-runs/hf-cache",
        "model_receipt_sha256": "d" * 64,
        "model_artifact_root": "e" * 64,
        "public_benchmark_path": (
            "/home/kevin/cotcodec-runs/inputs/longmemeval_s_cleaned.json"
        ),
    }


def test_public_control_freezer_is_hash_bound_and_container_only() -> None:
    raw = compile_public_docker_manifest(stage="freeze-controls", **_kwargs())
    manifest = validate_manifest(raw)
    assert manifest["gpus"] == 1
    assert manifest["max_gpu_hours"] == 0.5
    assert manifest["model"]["model_id"] == "bge-small-en-v1.5"
    assert manifest["public_benchmark"] == {
        "source_id": "longmemeval-s-cleaned",
        "revision": "98d7416c24c778c2fee6e6f3006e7a073259d48f",
        "license": "MIT",
        "host_path": (
            "/home/kevin/cotcodec-runs/inputs/longmemeval_s_cleaned.json"
        ),
        "sha256": "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442",
        "size_bytes": 277_383_467,
        "container_path": "/inputs/longmemeval_s_cleaned.json",
    }
    command = manifest["command"]
    assert command[1] == "scripts/freeze_memory_control_matrix.py"
    assert command[command.index("--episodes") + 1] == "32"
    assert command[command.index("--candidate-seed") + 1] == "42"
    assert command[command.index("--model-root") + 1] == (
        "/model-cache/cotcodec-models"
    )
    assert command[command.index("--receipt-root") + 1] == (
        "/model-cache/cotcodec-receipts"
    )
    system_index = command.index("--systems") + 1
    assert tuple(command[system_index:]) == CONTROL_SYSTEMS


def test_public_actor_screen_executes_all_seeds_and_one_bundle() -> None:
    raw = compile_public_docker_manifest(
        stage="actor-screen",
        memory_bundle_path="/home/kevin/cotcodec-runs/inputs/bm25.json",
        memory_bundle_sha256="f" * 64,
        memory_control_id="bm25",
        **_kwargs(),
    )
    manifest = validate_manifest(raw)
    assert manifest["gpus"] == 2
    assert manifest["model"]["model_id"] == "qwen3.6-35b-a3b"
    assert manifest["max_gpu_hours"] == 8
    assert manifest["memory_bundle"]["sha256"] == "f" * 64
    assert manifest["name"] == "memory-lme-q36-bm25"
    command = manifest["command"]
    assert command[command.index("--evaluation-mode") + 1] == "matrix-cell"
    seed_index = command.index("--assignment-seeds") + 1
    require_index = command.index("--require-gates")
    assert command[seed_index:require_index] == ["42", "43", "44"]
    assert command[command.index("--public-benchmark-path") + 1] == (
        "/inputs/longmemeval_s_cleaned.json"
    )
    assert command[command.index("--memory-bundle") + 1] == (
        "/inputs/memory-selection-bundle.json"
    )


def test_full_freeze_and_all_serve_actor_are_seedless() -> None:
    freeze = validate_manifest(
        compile_public_docker_manifest(stage="freeze-controls-full", **_kwargs())
    )
    assert freeze["randomness_contract"] == "deterministic-all-serve"
    assert freeze["seeds"] == []
    assert "--episodes" not in freeze["command"]

    actor = validate_manifest(
        compile_public_docker_manifest(
            stage="actor-all-serve",
            memory_bundle_path="/home/kevin/cotcodec-runs/inputs/bm25-full.json",
            memory_bundle_sha256="f" * 64,
            memory_control_id="bm25",
            **_kwargs(),
        )
    )
    assert actor["randomness_contract"] == "deterministic-all-serve"
    assert actor["seeds"] == []
    command = actor["command"]
    assert command[command.index("--evaluation-mode") + 1] == (
        "all-serve-benchmark"
    )
    assert "--assignment-seeds" not in command
    assert command[command.index("--expected-memory-system-id") + 1] == (
        "bm25-memory-v1"
    )


def test_mempalace_is_an_actor_only_discovery_control() -> None:
    assert "mempalace-raw-session" not in CONTROL_SYSTEMS
    assert "mempalace-raw-session" in ACTOR_CONTROL_SYSTEMS
    actor = validate_manifest(
        compile_public_docker_manifest(
            stage="actor-all-serve",
            memory_bundle_path="/home/kevin/cotcodec-runs/inputs/mempalace.json",
            memory_bundle_sha256="f" * 64,
            memory_control_id="mempalace-raw-session",
            memory_admission_sha256="9" * 64,
            **_kwargs(),
        )
    )
    assert actor["name"] == "memory-lme-quality-q36-mempalace-raw"
    command = actor["command"]
    assert command[command.index("--expected-memory-system-id") + 1] == (
        "mempalace-raw-user-session-minilm-port-v1"
    )
    assert command[command.index("--expected-memory-admission-sha256") + 1] == (
        "9" * 64
    )
    with pytest.raises(ValueError, match="registered admission-evidence"):
        compile_public_docker_manifest(
            stage="actor-all-serve",
            memory_bundle_path="/home/kevin/cotcodec-runs/inputs/mempalace.json",
            memory_bundle_sha256="f" * 64,
            memory_control_id="mempalace-raw-session",
            **_kwargs(),
        )


def test_public_actor_rejects_missing_bundle() -> None:
    with pytest.raises(ValueError, match="requires one frozen"):
        compile_public_docker_manifest(stage="actor-screen", **_kwargs())


def test_public_actor_rejects_unbound_control_id() -> None:
    with pytest.raises(ValueError, match="registered memory control id"):
        compile_public_docker_manifest(
            stage="actor-screen",
            memory_bundle_path="/home/kevin/cotcodec-runs/inputs/bm25.json",
            memory_bundle_sha256="f" * 64,
            **_kwargs(),
        )


def test_public_compiler_rejects_registered_seed_drift(tmp_path: Path) -> None:
    source = Path("experiments/memory/stage1-longmemeval-screen.yaml")
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["execution"]["seeds"] = [42, 42, 42]
    drifted = tmp_path / "experiment.yaml"
    drifted.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="seed matrix drifted"):
        compile_public_docker_manifest(
            stage="freeze-controls",
            experiment_path=drifted,
            **_kwargs(),
        )
