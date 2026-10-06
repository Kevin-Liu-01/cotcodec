from __future__ import annotations

import pytest

from scripts.compile_memory_replay_doctor_job import (
    compile_replay_doctor_manifest,
)
from scripts.submit_docker_research_job import validate_manifest


def _kwargs(model_id: str = "qwen3.6-35b-a3b") -> dict:
    return {
        "model_id": model_id,
        "image_id": "sha256:" + "a" * 64,
        "run_root": "/home/kevin/cotcodec-runs/replay-doctors",
        "git_sha": "b" * 40,
        "source_sha256": "c" * 64,
        "model_cache_host": "/home/kevin/cotcodec-runs/hf-cache",
        "receipt_sha256": "d" * 64,
        "artifact_root_sha256": "e" * 64,
    }


def test_replay_doctor_manifest_executes_declared_seeds_and_known_failures() -> None:
    manifest = compile_replay_doctor_manifest(**_kwargs())
    assert manifest["resources"]["gpus"] == 2
    assert manifest["budget"]["max_gpu_hours"] == 4
    command = manifest["command"]
    seed_index = command.index("--seeds")
    assert [int(value) for value in command[seed_index + 1 :]] == manifest["seeds"]
    assert [
        command[index + 1]
        for index, value in enumerate(command[:-1])
        if value == "--task-id"
    ] == ["0", "4", "106", "180"]
    validate_manifest(manifest)


def test_replay_doctor_manifest_binds_optional_memory_bundle() -> None:
    manifest = compile_replay_doctor_manifest(
        **_kwargs("qwen3.5-4b"),
        memory_bundle_path="/home/kevin/cotcodec-runs/inputs/recency.json",
        memory_bundle_sha256="f" * 64,
    )
    assert manifest["resources"]["gpus"] == 1
    assert manifest["memory_bundle"]["sha256"] == "f" * 64
    assert "/inputs/memory-selection-bundle.json" in manifest["command"]
    validate_manifest(manifest)


def test_replay_doctor_manifest_binds_exact_resume_subtree() -> None:
    manifest = compile_replay_doctor_manifest(
        **_kwargs(),
        resume_from_job_id="134",
        resume_subpath="replay-doctor",
    )
    assert manifest["resume_from_job_id"] == "134"
    assert manifest["resume_subpath"] == "replay-doctor"
    validate_manifest(manifest)

    with pytest.raises(ValueError, match="supplied together"):
        compile_replay_doctor_manifest(
            **_kwargs(),
            resume_from_job_id="134",
        )
    with pytest.raises(ValueError, match="artifact subtree"):
        compile_replay_doctor_manifest(
            **_kwargs(),
            resume_from_job_id="134",
            resume_subpath="outputs",
        )


def test_replay_doctor_rejects_decorative_or_duplicate_seeds() -> None:
    with pytest.raises(ValueError, match="three distinct seeds"):
        compile_replay_doctor_manifest(**_kwargs(), seeds=(42, 42, 42))

    manifest = compile_replay_doctor_manifest(**_kwargs())
    manifest["command"][-1] = "45"
    with pytest.raises(ValueError, match="do not match manifest seeds"):
        validate_manifest(manifest)


def test_replay_doctor_rejects_unreviewed_checkpoint() -> None:
    with pytest.raises(ValueError, match="no reviewed replay-doctor"):
        compile_replay_doctor_manifest(**_kwargs("kimi-linear-48b-a3b-base"))
