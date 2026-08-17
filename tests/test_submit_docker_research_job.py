from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.memory_job_admission import build_memory_job_admission
from scripts.submit_docker_research_job import (
    BATCH_SCRIPT,
    RUNTIME,
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
            "scripts/run_memory_model_screen.py",
            "--output-dir",
            "/outputs",
            "--assignment-seeds",
            "42",
            "43",
            "44",
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
        "memory_source_admission": build_memory_job_admission(),
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


def test_real_submitter_rejects_killed_memory_revision() -> None:
    raw = _manifest()
    admission = build_memory_job_admission()
    admission["scope"] = "external-sources"
    admission["sources"] = [
        {
            "source_id": "total-recall-oss",
            "revision": "a2630f671be9b12df8b8ac78df9d26f7053d2fa9",
        }
    ]
    raw["memory_source_admission"] = admission
    with pytest.raises(ValueError, match="BLOCKED_NATIVE_RESTART"):
        validate_manifest(raw)


def test_real_submitter_rejects_unbound_memory_workload() -> None:
    raw = _manifest()
    raw.pop("memory_source_admission")
    with pytest.raises(ValueError, match="requires memory_source_admission"):
        validate_manifest(raw)


def test_real_submitter_admits_registered_neo4j_revision() -> None:
    raw = _manifest()
    raw["memory_source_admission"] = build_memory_job_admission(
        [("neo4j-agent-memory", "231d60eac9401ab156ba194b519d89dd644dadb8")]
    )
    manifest = validate_manifest(raw)
    assert manifest["memory_source_admission"]["scope"] == "external-sources"


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


def test_docker_manifest_hash_binds_optional_inputs_and_resume() -> None:
    raw = _manifest()
    raw["memory_bundle"] = {
        "host_path": "/home/kevin/cotcodec-runs/frozen-memory.json",
        "sha256": "1" * 64,
    }
    raw["resume_from_job_id"] = 23
    raw["resume_subpath"] = "screen"
    manifest = validate_manifest(raw)
    argv = sbatch_argv(manifest, test_only=False)
    export = next(argument for argument in argv if argument.startswith("--export="))
    assert "COTCODEC_MEMORY_BUNDLE_HOST_HEX=" in export
    assert "COTCODEC_MEMORY_BUNDLE_SHA256=" + "1" * 64 in export
    assert "COTCODEC_PREDECESSOR_JOB_ID=23" in export
    assert "COTCODEC_RESUME_SUBPATH=screen" in export


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

def test_docker_manifest_rejects_decorative_seed_list() -> None:
    raw = _manifest()
    raw["command"] = [
        "python",
        "scripts/run_memory_model_screen.py",
        "--assignment-seed",
        "42",
    ]
    with pytest.raises(ValueError, match="execute every manifest seed"):
        validate_manifest(raw)

    raw["command"] = [
        "python",
        "scripts/run_memory_model_screen.py",
        "--assignment-seeds",
        "42",
        "43",
        "45",
    ]
    with pytest.raises(ValueError, match="do not match manifest seeds"):
        validate_manifest(raw)


def test_deterministic_all_serve_contract_forbids_assignment_seeds() -> None:
    raw = _manifest()
    raw["randomness_contract"] = "deterministic-all-serve"
    raw["seeds"] = []
    raw["command"] = [
        "python",
        "scripts/run_memory_model_screen.py",
        "--evaluation-mode",
        "all-serve-benchmark",
        "--output-dir",
        "/outputs",
    ]
    manifest = validate_manifest(raw)
    assert manifest["seeds"] == []
    assert manifest["randomness_contract"] == "deterministic-all-serve"
    export = next(
        value for value in sbatch_argv(manifest, test_only=True) if value.startswith("--export=")
    )
    assert "COTCODEC_RANDOMNESS_CONTRACT=deterministic-all-serve" in export
    assert "COTCODEC_SEEDS=none" in export

    raw["command"].extend(["--assignment-seeds", "42", "43", "44"])
    with pytest.raises(ValueError, match="cannot execute seed options"):
        validate_manifest(raw)

    raw = _manifest()
    raw["command"] = [
        "python",
        "scripts/run_memory_model_replay_doctor.py",
        "--seeds",
        "42",
        "43",
        "45",
    ]
    with pytest.raises(ValueError, match="do not match manifest seeds"):
        validate_manifest(raw)


def test_docker_batch_reverifies_and_read_only_mounts_public_benchmark() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert 'sha256sum "${public_benchmark_host}"' in content
    assert "stat -c '%s' \"${public_benchmark_host}\"" in content
    assert '"${public_benchmark_host}:/inputs/longmemeval_s_cleaned.json:ro"' in content
    assert "executed seeds do not exactly match declared seeds" in content
    assert 'echo "randomness_contract=${COTCODEC_RANDOMNESS_CONTRACT}"' in content


def _claim_manifest() -> dict:
    raw = _manifest()
    raw["randomness_contract"] = "deterministic-all-serve"
    raw["seeds"] = []
    raw["command"] = [
        "python",
        "scripts/run_memory_model_screen.py",
        "experiments/memory/stage1-longmemeval-screen.yaml",
        "--model-root",
        "/model-cache/cotcodec-models",
        "--receipt-root",
        "/model-cache/cotcodec-receipts",
        "--output-dir",
        "/outputs/screen",
        "--memory-bundle",
        "/inputs/memory-selection-bundle.json",
        "--memory-treatment-mode",
        "storage_and_service",
        "--expected-memory-system-id",
        "bm25-memory-v1",
        "--evaluation-mode",
        "all-serve-benchmark",
        "--public-benchmark-path",
        "/inputs/longmemeval_s_cleaned.json",
        "--require-gates",
        "--publication-capsule",
        "/inputs/publication-capsule.json",
        "--publication-capsule-attestation",
        "/inputs/publication-capsule-attestation.json",
        "--publication-trust-store",
        "/etc/cotcodec/trust/publication-attestors.json",
        "--expected-publication-trust-sha256",
        "a" * 64,
        "--control-matrix-manifest",
        "/inputs/control-matrix-manifest.json",
        "--publication-wave-contract",
        "/inputs/publication-wave-contract.json",
        "--expected-wave-sha256",
        "7" * 64,
        "--expected-control-id",
        "bm25",
        "--expected-system-id",
        "bm25-memory-v1",
    ]
    raw["memory_bundle"] = {
        "host_path": "/shared/matrix/bundles/bm25.json",
        "sha256": "1" * 64,
    }
    raw["public_benchmark"] = {
        "source_id": "longmemeval-s-cleaned",
        "revision": "2" * 40,
        "license": "MIT",
        "host_path": "/shared/inputs/longmemeval_s_cleaned.json",
        "sha256": "3" * 64,
        "size_bytes": 15_388_478,
    }
    raw["claim_admission"] = {
        "publication_capsule": {
            "host_path": "/shared/publication/capsule.json",
            "file_sha256": "4" * 64,
            "capsule_sha256": "5" * 64,
            "image_id": raw["image_id"],
            "git_sha": raw["git_sha"],
            "source_sha256": raw["source_sha256"],
        },
        "publication_attestation": {
            "host_path": "/shared/publication/capsule-attestation.json",
            "file_sha256": "b" * 64,
            "trust_store_host_path": ("/etc/cotcodec/trust/publication-attestors.json"),
            "trust_store_sha256": "a" * 64,
            "key_id": "publication-ci-1",
        },
        "control_matrix": {
            "host_path": "/shared/matrix/manifest.json",
            "file_sha256": "6" * 64,
            "matrix_sha256": "8" * 64,
            "task_manifest_sha256": "9" * 64,
        },
        "wave": {
            "host_path": "/shared/publication/wave-contract.json",
            "file_sha256": "c" * 64,
            "wave_sha256": "7" * 64,
            "control_id": "bm25",
            "system_id": "bm25-memory-v1",
            "eligible_for_primary": True,
            "bundle_file_sha256": "1" * 64,
            "bundle_semantic_sha256": "2" * 64,
        },
    }
    return raw


def test_claim_admission_binds_capsule_matrix_wave_and_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.submit_docker_research_job._verify_claim_admission_files",
        lambda _claim, _command: {"status": "verified"},
    )
    manifest = validate_manifest(_claim_manifest())
    claim = manifest["claim_admission"]
    assert claim["wave"]["control_id"] == "bm25"
    assert claim["publication_capsule"]["container_path"] == ("/inputs/publication-capsule.json")
    export = next(
        value for value in sbatch_argv(manifest, test_only=True) if value.startswith("--export=")
    )
    assert "COTCODEC_PUBLICATION_CAPSULE_HOST_HEX=" in export
    assert "COTCODEC_PUBLICATION_ATTESTATION_HOST_HEX=" in export
    assert "COTCODEC_CONTROL_MATRIX_HOST_HEX=" in export
    assert "COTCODEC_CLAIM_WAVE_SHA256=" + "7" * 64 in export
    assert "COTCODEC_MEMORY_CONTROL_ID=bm25" in export
    batch = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert 'sha256sum "${publication_capsule_host}"' in batch
    assert 'sha256sum "${control_matrix_host}"' in batch
    assert 'sha256sum "${publication_wave_host}"' in batch
    assert '"${publication_capsule_host}:/inputs/publication-capsule.json:ro"' in batch
    assert '"${control_matrix_host}:/inputs/control-matrix-manifest.json:ro"' in batch
    assert "control matrix semantic root is invalid" in batch
    assert "claim control identity or eligibility differs" in batch
    assert 'wave.get("batch_script_sha256")' in batch
    assert 'capsule.get("runtime", {}).get("batch_script_sha256")' in batch


def test_claim_admission_rejects_mislabeled_or_cherry_picked_cell() -> None:
    raw = _claim_manifest()
    raw["claim_admission"]["wave"]["eligible_for_primary"] = False
    with pytest.raises(ValueError, match="primary-eligible"):
        validate_manifest(raw)
    raw = _claim_manifest()
    raw["claim_admission"]["wave"]["bundle_file_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="file digest differs"):
        validate_manifest(raw)
    raw = _claim_manifest()
    option = raw["command"].index("--expected-control-id")
    raw["command"][option + 1] = "recency"
    with pytest.raises(ValueError, match="differs from the claim"):
        validate_manifest(raw)


@pytest.mark.parametrize(
    "extra",
    [
        ["--evaluation-mode", "matrix-cell"],
        ["--model-id", "qwen3.5-4b"],
    ],
)
def test_claim_admission_rejects_duplicate_or_unregistered_actor_options(
    extra: list[str],
) -> None:
    raw = _claim_manifest()
    raw["command"].extend(extra)
    with pytest.raises(ValueError, match="exact registered argv schema"):
        validate_manifest(raw)
