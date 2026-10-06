from __future__ import annotations

from pathlib import Path

import pytest

from scripts.memory_job_admission import build_memory_job_admission
from scripts.submit_research_job import sbatch_argv, validate_manifest

BATCH_SCRIPT = Path("infra/slurm/research.sbatch")


def _manifest() -> dict:
    return {
        "name": "coded-delta-contract",
        "image": "registry.example/cotcodec@sha256:" + "a" * 64,
        "command": ["uv", "run", "python", "-m", "harness.runner", "experiments/example.yaml"],
        "run_root": "/shared/cotcodec/runs",
        "git_sha": "a" * 40,
        "source_sha256": "b" * 64,
        "seeds": [42, 43, 44],
        "resources": {
            "gpu_type": "h100",
            "gpus": 1,
            "cpus": 16,
            "memory_gb": 64,
            "minutes": 120,
        },
        "budget": {"max_gpu_hours": 2},
    }


def test_manifest_builds_allowlisted_bounded_sbatch_command() -> None:
    manifest = validate_manifest(_manifest())
    argv = sbatch_argv(manifest, test_only=True)
    assert "--gres=gpu:h100:1" in argv
    assert "--time=02:00:00" in argv
    export_arg = next(argument for argument in argv if argument.startswith("--export="))
    assert "ALL" not in export_arg
    assert ".env" not in export_arg
    assert "--test-only" in argv


def test_manifest_rejects_allocation_above_gpu_hour_ceiling() -> None:
    raw = _manifest()
    raw["resources"]["gpus"] = 8
    with pytest.raises(ValueError, match="above budget"):
        validate_manifest(raw)


def test_manifest_requires_three_distinct_seeds() -> None:
    raw = _manifest()
    raw["seeds"] = [42, 42, 42]
    with pytest.raises(ValueError, match="three distinct"):
        validate_manifest(raw)


@pytest.mark.parametrize("ceiling", [float("nan"), float("inf"), 0, -1])
def test_manifest_rejects_nonfinite_or_nonpositive_budget(ceiling: float) -> None:
    raw = _manifest()
    raw["budget"]["max_gpu_hours"] = ceiling
    with pytest.raises(ValueError, match="positive finite"):
        validate_manifest(raw)


def test_manifest_rejects_budget_above_single_job_safety_ceiling() -> None:
    raw = _manifest()
    raw["budget"]["max_gpu_hours"] = 65
    with pytest.raises(ValueError, match="single-job safety ceiling"):
        validate_manifest(raw)


def test_manifest_rejects_slurm_export_delimiter_in_image() -> None:
    raw = _manifest()
    raw["image"] = "registry/x,BASH_ENV=/shared/payload@sha256:" + "a" * 64
    with pytest.raises(ValueError, match="immutable OCI digest"):
        validate_manifest(raw)


def test_manifest_rejects_slurm_export_delimiters_and_traversal_in_run_root() -> None:
    for run_root in ("/shared/runs,ALL", "/shared/runs\nBASH_ENV=x", "/shared/../root"):
        raw = _manifest()
        raw["run_root"] = run_root
        with pytest.raises(ValueError, match="simple absolute path"):
            validate_manifest(raw)


def test_resume_exports_bounded_predecessor_and_subpath() -> None:
    raw = _manifest()
    raw["resume_from_job_id"] = 12345
    raw["resume_subpath"] = "screen"
    manifest = validate_manifest(raw)
    argv = sbatch_argv(manifest, test_only=False)
    export_arg = next(argument for argument in argv if argument.startswith("--export="))
    assert "COTCODEC_PREDECESSOR_JOB_ID=12345" in export_arg
    assert "COTCODEC_RESUME_SUBPATH=screen" in export_arg


def test_memory_bundle_mount_is_hash_bound_and_hex_exported() -> None:
    raw = _manifest()
    raw["memory_bundle"] = {
        "host_path": "/shared/cotcodec/inputs/frozen-memory.json",
        "sha256": "c" * 64,
    }
    raw["memory_source_admission"] = build_memory_job_admission()
    manifest = validate_manifest(raw)
    assert manifest["memory_bundle"]["container_path"] == (
        "/inputs/memory-selection-bundle.json"
    )
    argv = sbatch_argv(manifest, test_only=False)
    export_arg = next(argument for argument in argv if argument.startswith("--export="))
    assert "COTCODEC_MEMORY_BUNDLE_HOST_HEX=" in export_arg
    assert "COTCODEC_MEMORY_BUNDLE_SHA256=" + "c" * 64 in export_arg


@pytest.mark.parametrize(
    "host_path",
    ["relative/file.json", "/shared/../secret", "/shared/file,ALL", "/shared/a:b"],
)
def test_memory_bundle_rejects_unsafe_host_path(host_path: str) -> None:
    raw = _manifest()
    raw["memory_bundle"] = {"host_path": host_path, "sha256": "c" * 64}
    with pytest.raises(ValueError, match="simple absolute path"):
        validate_manifest(raw)


@pytest.mark.parametrize("subpath", ["../screen", "/screen", "screen,ALL", "screen\nX"])
def test_resume_rejects_unsafe_subpath(subpath: str) -> None:
    raw = _manifest()
    raw["resume_from_job_id"] = 12345
    raw["resume_subpath"] = subpath
    with pytest.raises(ValueError, match="safe relative"):
        validate_manifest(raw)


def test_batch_rejects_resume_root_symlink_and_resolved_escape() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert "source_candidate.is_symlink()" in content
    assert "source_candidate.resolve()" in content
    assert "predecessor not in source.parents" in content
