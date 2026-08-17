from __future__ import annotations

import pytest

from scripts.compile_gaama_actor_job import EVIDENCE_SHA256, compile_manifest
from scripts.submit_docker_research_job import sbatch_argv, validate_manifest


def _compile(**overrides: object) -> dict:
    values = {
        "image_id": "sha256:" + "a" * 64,
        "run_root": "/shared/cotcodec/runs",
        "git_sha": "b" * 40,
        "source_sha256": "c" * 64,
        "model_cache_host": "/shared/cotcodec/hf-cache",
        "receipt_sha256": "d" * 64,
        "evidence_host_path": "/shared/cotcodec/inputs/gaama-natural-v5.json",
    }
    values.update(overrides)
    return compile_manifest(**values)  # type: ignore[arg-type]


def test_gaama_actor_compiler_binds_h100_model_artifact_and_input() -> None:
    raw = _compile()
    assert raw["resources"] == {
        "gpu_type": "h100",
        "gpus": 1,
        "cpus": 16,
        "memory_gb": 64,
        "minutes": 120,
    }
    assert raw["budget"] == {"max_gpu_hours": 2.0}
    manifest = validate_manifest(raw)
    assert manifest["randomness_contract"] == "deterministic-all-serve"
    assert manifest["seeds"] == []
    assert manifest["gpus"] == 1
    assert manifest["minutes"] == 120
    assert manifest["max_gpu_hours"] == 2.0
    assert manifest["model"]["model_id"] == "qwen3.5-4b"
    assert manifest["study_artifact"]["sha256"] == EVIDENCE_SHA256
    assert manifest["study_artifact"]["container_path"] == "/inputs/study-artifact.json"
    assert manifest["command"].count("--evidence") == 1
    assert manifest["command"].count("--expected-evidence-sha256") == 1
    assert manifest["memory_source_admission"]["sources"] == [
        {
            "source_id": "gaama",
            "revision": "2d992f7f7b97c802bfe4c799878a5477cac1b6ff",
        }
    ]
    export = next(
        value
        for value in sbatch_argv(manifest, test_only=True)
        if value.startswith("--export=")
    )
    assert "COTCODEC_STUDY_ARTIFACT_SHA256=" + EVIDENCE_SHA256 in export
    assert "COTCODEC_RANDOMNESS_CONTRACT=deterministic-all-serve" in export


def test_gaama_actor_compiler_rejects_input_or_resume_drift() -> None:
    with pytest.raises(ValueError, match="digest differs"):
        _compile(evidence_sha256="0" * 64)
    with pytest.raises(ValueError, match="size differs"):
        _compile(evidence_size=1)
    with pytest.raises(ValueError, match="supplied together"):
        _compile(resume_from_job_id="123")
    with pytest.raises(ValueError, match="only the gaama-actor subtree"):
        _compile(resume_from_job_id="123", resume_subpath="other")


def test_gaama_actor_compiler_binds_resume_subtree() -> None:
    manifest = _compile(resume_from_job_id="123", resume_subpath="gaama-actor")
    assert manifest["resume_from_job_id"] == "123"
    assert manifest["resume_subpath"] == "gaama-actor"
