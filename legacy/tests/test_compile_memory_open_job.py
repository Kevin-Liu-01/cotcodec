from __future__ import annotations

import pytest

from scripts.compile_memory_open_job import compile_open_model_manifest


def _kwargs(model_id: str) -> dict:
    return {
        "model_id": model_id,
        "image": "registry.example/cotcodec@sha256:" + "a" * 64,
        "run_root": "/shared/cotcodec/runs",
        "git_sha": "b" * 40,
        "source_sha256": "c" * 64,
        "memory_bundle_path": "/shared/cotcodec/inputs/frozen-memory.json",
        "memory_bundle_sha256": "d" * 64,
    }


@pytest.mark.parametrize(
    ("model_id", "gpus"),
    [
        ("qwen3.5-4b", 1),
        ("qwen3.5-9b", 1),
        ("qwen3.6-35b-a3b", 2),
        ("gpt-oss-120b", 2),
    ],
)
def test_open_model_manifest_is_bounded(model_id: str, gpus: int) -> None:
    manifest = compile_open_model_manifest(**_kwargs(model_id))
    assert manifest["resources"]["gpus"] == gpus
    assert manifest["budget"]["max_gpu_hours"] <= 8
    assert manifest["memory_bundle"]["container_path"] == (
        "/inputs/memory-selection-bundle.json"
    )
    assert "/inputs/memory-selection-bundle.json" in manifest["command"]
    assert manifest["command"][-1] == "--require-gates"
    seed_index = manifest["command"].index("--assignment-seeds")
    executed_seeds = [int(value) for value in manifest["command"][seed_index + 1 : -1]]
    assert executed_seeds == manifest["seeds"] == [42, 43, 44]


def test_open_model_resume_uses_new_job_and_copies_screen() -> None:
    manifest = compile_open_model_manifest(
        **_kwargs("qwen3.5-9b"),
        predecessor_job_id=123,
    )
    assert manifest["resume_from_job_id"] == 123
    assert manifest["resume_subpath"] == "screen"
    assert manifest["command"][-1] == "--resume"


def test_unreviewed_kimi_linear_is_not_generic_job() -> None:
    with pytest.raises(ValueError, match="no reviewed open-model Slurm profile"):
        compile_open_model_manifest(**_kwargs("kimi-linear-48b-a3b-base"))


def test_open_model_manifest_rejects_decorative_or_duplicate_seeds() -> None:
    with pytest.raises(ValueError, match="three distinct"):
        compile_open_model_manifest(
            **_kwargs("qwen3.5-4b"),
            seeds=(42, 42, 42),
        )


def test_full_prefix_diagnostic_gets_a_separate_actor_contract() -> None:
    manifest = compile_open_model_manifest(
        **_kwargs("qwen3.6-35b-a3b"),
        memory_budget_profile="full-prefix-diagnostic",
    )
    assert manifest["memory_budget_profile"] == "full-prefix-diagnostic"
    assert manifest["name"].endswith("-fpdiag")
    profile_index = manifest["command"].index("--memory-budget-profile")
    assert manifest["command"][profile_index + 1] == "full-prefix-diagnostic"
    mode_index = manifest["command"].index("--evaluation-mode")
    assert manifest["command"][mode_index + 1] == "diagnostic-ceiling"
