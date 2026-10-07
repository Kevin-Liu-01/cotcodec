from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.submit_docker_research_job import (
    BATCH_SCRIPT,
    RUNTIME,
    prepare_run_root,
    sbatch_argv,
    validate_manifest,
)


def _manifest() -> dict:
    return {
        "runtime": RUNTIME,
        "name": "qwen-smoke",
        "image_id": "sha256:" + "a" * 64,
        "command": [
            "python",
            "scripts/run_translation_supervised_indexer_doctor.py",
            "--output",
            "/outputs/receipt.json",
        ],
        "run_root": "/home/kevin/cotcodec-runs/research",
        "git_sha": "b" * 40,
        "source_sha256": "c" * 64,
        "model": {
            "cache_host_path": "/home/kevin/cotcodec-runs/hf-cache",
            "model_id": "qwen3.5-4b",
            "revision": "d" * 40,
            "receipt_sha256": "e" * 64,
            "artifact_root_sha256": "f" * 64,
        },
        "seeds": [42, 43, 44],
        "resources": {
            "gpu_type": "h100",
            "gpus": 1,
            "cpus": 8,
            "memory_gb": 32,
            "minutes": 30,
        },
        "budget": {"max_gpu_hours": 0.5},
    }


def test_docker_manifest_builds_bounded_slurm_submission() -> None:
    manifest = validate_manifest(_manifest())
    argv = sbatch_argv(manifest, test_only=True)
    assert "--partition=research" in argv
    assert "--gres=gpu:h100:1" in argv
    assert "--time=00:30:00" in argv
    assert "--test-only" in argv
    export = next(argument for argument in argv if argument.startswith("--export="))
    assert "COTCODEC_IMAGE_ID=sha256:" + "a" * 64 in export
    assert "COTCODEC_RUN_ROOT_HEX=" in export
    assert "COTCODEC_MODEL_CACHE_HOST_HEX=" in export
    assert "/home/kevin" not in export
    assert "ALL" not in export


def test_submitter_direct_cli_resolves_project_imports() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/submit_docker_research_job.py", "--help"],
        cwd=BATCH_SCRIPT.parents[3],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "manifest" in completed.stdout


def test_submitter_can_seal_dry_run_without_shell_redirection(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    output_path = tmp_path / "dry-run.json"
    manifest_path.write_text(yaml.safe_dump(_manifest()), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/submit_docker_research_job.py",
            str(manifest_path),
            "--dry-run",
            "--dry-run-output",
            str(output_path),
        ],
        cwd=BATCH_SCRIPT.parents[3],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runtime"] == RUNTIME
    assert payload["gpu_hours"] == 0.5
    repeated = subprocess.run(
        [
            sys.executable,
            "scripts/submit_docker_research_job.py",
            str(manifest_path),
            "--dry-run",
            "--dry-run-output",
            str(output_path),
        ],
        cwd=BATCH_SCRIPT.parents[3],
        check=False,
        capture_output=True,
        text=True,
    )
    assert repeated.returncode != 0
    assert "already exists" in repeated.stderr


def test_submitter_precreates_only_a_nonsymlink_persistent_run_root(tmp_path: Path) -> None:
    base = tmp_path / "runs"
    base.mkdir()
    manifest = {"run_root": str(base / "nested" / "experiment")}
    created = prepare_run_root(manifest, allowed_roots=(base,))
    assert created.is_dir()
    assert not created.is_symlink()

    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="outside the dedicated"):
        prepare_run_root({"run_root": str(outside)}, allowed_roots=(base,))

    link = base / "link"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink component"):
        prepare_run_root({"run_root": str(link / "child")}, allowed_roots=(base,))


def test_docker_manifest_rejects_export_injection_and_paths() -> None:
    raw = _manifest()
    raw["image_id"] = "sha256:" + "a" * 63 + ","
    with pytest.raises(ValueError, match="exact local Docker"):
        validate_manifest(raw)
    raw = _manifest()
    raw["model"]["cache_host_path"] = "/home/kevin/cache,ALL"
    with pytest.raises(ValueError, match="simple absolute path"):
        validate_manifest(raw)


@pytest.mark.parametrize("ceiling", [float("nan"), float("inf"), 0, -1])
def test_docker_manifest_rejects_invalid_budget(ceiling: float) -> None:
    raw = _manifest()
    raw["budget"]["max_gpu_hours"] = ceiling
    with pytest.raises(ValueError, match="positive finite"):
        validate_manifest(raw)


def test_docker_manifest_rejects_allocation_above_budget() -> None:
    raw = _manifest()
    raw["resources"]["gpus"] = 8
    with pytest.raises(ValueError, match="above budget"):
        validate_manifest(raw)


def test_docker_manifest_binds_public_benchmark_provenance_and_mount() -> None:
    raw = _manifest()
    raw["command"][4:4] = [
        "--public-benchmark-path",
        "/inputs/longmemeval_s_cleaned.json",
    ]
    raw["public_benchmark"] = {
        "source_id": "longmemeval-s-cleaned",
        "revision": "2" * 40,
        "license": "MIT",
        "host_path": "/home/kevin/cotcodec-runs/inputs/longmemeval_s_cleaned.json",
        "sha256": "3" * 64,
        "size_bytes": 15_388_478,
    }
    manifest = validate_manifest(raw)
    assert manifest["public_benchmark"]["container_path"] == ("/inputs/longmemeval_s_cleaned.json")
    argv = sbatch_argv(manifest, test_only=False)
    export = next(argument for argument in argv if argument.startswith("--export="))
    assert "COTCODEC_PUBLIC_BENCHMARK_HOST_HEX=" in export
    assert "COTCODEC_PUBLIC_BENCHMARK_SHA256=" + "3" * 64 in export
    assert "COTCODEC_PUBLIC_BENCHMARK_SIZE=15388478" in export
    assert "/home/kevin" not in export


def test_docker_manifest_rejects_unmounted_or_drifting_public_benchmark() -> None:
    raw = _manifest()
    raw["command"][4:4] = [
        "--public-benchmark-path",
        "/inputs/longmemeval_s_cleaned.json",
    ]
    with pytest.raises(ValueError, match="without a hash-bound mount"):
        validate_manifest(raw)

    raw["public_benchmark"] = {
        "source_id": "longmemeval-s-cleaned",
        "revision": "2" * 40,
        "license": "MIT",
        "host_path": "/home/kevin/inputs/longmemeval.json",
        "sha256": "3" * 64,
        "size_bytes": 0,
    }
    with pytest.raises(ValueError, match="positive bounded integer"):
        validate_manifest(raw)

    raw["public_benchmark"]["size_bytes"] = 15_388_478
    raw["public_benchmark"]["container_path"] = "/inputs/other.json"
    with pytest.raises(ValueError, match="container_path is fixed"):
        validate_manifest(raw)


def test_docker_manifest_binds_generic_study_artifact_read_only() -> None:
    raw = _manifest()
    raw["command"][4:4] = [
        "--evidence",
        "/inputs/study-artifact.json",
        "--expected-evidence-sha256",
        "4" * 64,
    ]
    raw["study_artifact"] = {
        "source_id": "gaama-natural-v5",
        "revision": "2" * 40,
        "license": "CC-BY-NC-4.0",
        "host_path": "/shared/inputs/gaama-natural-v5.json",
        "sha256": "4" * 64,
        "size_bytes": 2_100_000,
    }
    manifest = validate_manifest(raw)
    assert manifest["study_artifact"]["container_path"] == "/inputs/study-artifact.json"
    export = next(
        value
        for value in sbatch_argv(manifest, test_only=True)
        if value.startswith("--export=")
    )
    assert "COTCODEC_STUDY_ARTIFACT_HOST_HEX=" in export
    assert "COTCODEC_STUDY_ARTIFACT_SHA256=" + "4" * 64 in export
    assert "/shared/inputs" not in export
    batch = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert 'sha256sum "${study_artifact_host}"' in batch
    assert '"${study_artifact_host}:/inputs/study-artifact.json:ro"' in batch


def test_docker_manifest_rejects_unbound_or_mislabeled_study_artifact() -> None:
    raw = _manifest()
    raw["command"][4:4] = [
        "--evidence",
        "/inputs/study-artifact.json",
        "--expected-evidence-sha256",
        "4" * 64,
    ]
    with pytest.raises(ValueError, match="without a hash-bound mount"):
        validate_manifest(raw)

    raw["study_artifact"] = {
        "source_id": "gaama-natural-v5",
        "revision": "2" * 40,
        "license": "CC-BY-NC-4.0",
        "host_path": "/shared/inputs/gaama-natural-v5.json",
        "sha256": "5" * 64,
        "size_bytes": 2_100_000,
    }
    with pytest.raises(ValueError, match="differs from the claim admission contract"):
        validate_manifest(raw)


def test_docker_batch_reverifies_and_read_only_mounts_public_benchmark() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert 'sha256sum "${public_benchmark_host}"' in content
    assert "stat -c '%s' \"${public_benchmark_host}\"" in content
    assert '"${public_benchmark_host}:/inputs/longmemeval_s_cleaned.json:ro"' in content
    assert "executed seeds do not exactly match declared seeds" in content
    assert 'echo "randomness_contract=${COTCODEC_RANDOMNESS_CONTRACT}"' in content


def test_archived_memory_workloads_fail_closed() -> None:
    raw = _manifest()
    raw["command"] = ["python", "scripts/run_memory_model_screen.py", "--output-dir", "/outputs"]
    with pytest.raises(ValueError, match="archived under legacy"):
        validate_manifest(raw)


def test_memory_admission_block_fails_closed_even_for_other_commands() -> None:
    raw = _manifest()
    raw["memory_source_admission"] = {"scope": "external-sources"}
    with pytest.raises(ValueError, match="archived under legacy"):
        validate_manifest(raw)
