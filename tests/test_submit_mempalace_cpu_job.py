from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.submit_mempalace_cpu_job import (
    BATCH_SCRIPT,
    RUNTIME,
    CpuJobExpectations,
    sbatch_argv,
    validate_manifest,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[dict, CpuJobExpectations]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    dataset = tmp_path / "longmemeval.json"
    dataset.write_text("[]\n", encoding="utf-8")
    run_root = tmp_path / "runs"
    run_root.mkdir()
    image_id = "sha256:" + "a" * 64
    repo_digest = "registry.invalid/mempalace@sha256:" + "e" * 64
    minilm = "c" * 64
    base = "registry.invalid/cotcodec@sha256:" + "d" * 64
    sbom_path = tmp_path / "sbom.spdx.json"
    sbom_path.write_text(
        json.dumps(
            {
                "spdxVersion": "SPDX-2.3",
                "documentDescribes": ["SPDXRef-container"],
                "creationInfo": {
                    "creators": [
                        "Organization: Anchore, Inc",
                        "Tool: syft-1.20.0",
                    ]
                },
                "cotcodecScan": {
                    "scanner": "syft",
                    "scanner_version": "1.20.0",
                    "target_repo_digest": repo_digest,
                    "target_image_id": image_id,
                    "argv": ["syft", repo_digest, "--output", "spdx-json"],
                },
                "packages": [
                    {
                        "SPDXID": "SPDXRef-container",
                        "name": image_id,
                        "externalRefs": [
                            {
                                "referenceCategory": "PACKAGE-MANAGER",
                                "referenceType": "purl",
                                "referenceLocator": f"pkg:oci/{repo_digest}",
                            }
                        ],
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    sbom = _sha(sbom_path)
    runtime = tmp_path / "runtime.json"
    runtime.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "VERIFIED_OFFLINE_MEMPALACE_RUNTIME",
                "repository_revision": (
                    "906b918a7c6ebb2a9198a6bf5a78f30a173fea56"
                ),
                "repository_tree": "98789ad017781f52550b511fcedd9e00c3346761",
                "source_archive_sha256": (
                    "efbc106cb344a1c5031268909adc2fb5c11cc783ec61adccbe3da0867b4d25c7"
                ),
                "runner_sha256": (
                    "c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d"
                ),
                "uv_lock_sha256": (
                    "9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da"
                ),
                "chromadb_version": "1.5.7",
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_archive_sha256": (
                    "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
                ),
                "execution_provider": "CPUExecutionProvider",
                "network_policy": "none",
                "image_id": image_id,
                "image_repo_digest": repo_digest,
                "image_sbom_sha256": sbom,
                "cotcodec_base_image_reference": base,
                "embedding_artifact_root_sha256": minilm,
                "minilm_receipt_sha256": "f" * 64,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    expectations = CpuJobExpectations(
        dataset_sha256=_sha(dataset),
        dataset_size=dataset.stat().st_size,
        dataset_revision="fixture-revision",
    )
    raw = {
        "schema_version": 1,
        "runtime": RUNTIME,
        "name": "mempalace-repro",
        "study_id": "mempalace-current-lock",
        "image": {
            "id": image_id,
            "repo_digest": repo_digest,
            "sbom": {"host_path": str(sbom_path), "sha256": sbom},
            "cotcodec_base_image_reference": base,
            "minilm_artifact_root_sha256": minilm,
        },
        "dataset": {
            "host_path": str(dataset),
            "sha256": _sha(dataset),
            "revision": "fixture-revision",
        },
        "runtime_receipt": {"host_path": str(runtime), "sha256": _sha(runtime)},
        "resources": {"cpus": 16, "memory_gb": 32, "minutes": 240},
        "budget": {"max_cpu_hours": 64, "max_wall_minutes": 240},
        "run_root": str(run_root),
    }
    return raw, expectations


def test_cpu_manifest_and_sbatch_are_gpu_free_and_fixed(tmp_path: Path) -> None:
    raw, expectations = _fixture(tmp_path)
    manifest = validate_manifest(raw, expectations=expectations)
    argv = sbatch_argv(manifest, test_only=True)

    assert manifest["gpu_count"] == 0
    assert manifest["network_policy"] == "none"
    assert "--partition=research" in argv
    assert "--cpus-per-task=16" in argv
    assert "--mem=32G" in argv
    assert f"--chdir={manifest['run_root']}" in argv
    assert not any("--gres" in argument for argument in argv)
    assert "--test-only" in argv
    assert argv[-1] == str(BATCH_SCRIPT)


def test_cpu_manifest_rejects_budget_identity_and_input_drift(tmp_path: Path) -> None:
    raw, expectations = _fixture(tmp_path)
    raw["budget"]["max_cpu_hours"] = float("nan")
    with pytest.raises(ValueError, match="finite and positive"):
        validate_manifest(raw, expectations=expectations)

    raw, expectations = _fixture(tmp_path / "mutable")
    raw["image"]["cotcodec_base_image_reference"] = "cotcodec:latest"
    with pytest.raises(ValueError, match="immutable"):
        validate_manifest(raw, expectations=expectations)

    raw, expectations = _fixture(tmp_path / "receipt")
    raw["image"]["id"] = "sha256:" + "e" * 64
    with pytest.raises(ValueError, match="SBOM scanner|image_id"):
        validate_manifest(raw, expectations=expectations)

    raw, expectations = _fixture(tmp_path / "dataset")
    Path(raw["dataset"]["host_path"]).write_text("drift\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dataset digest mismatch"):
        validate_manifest(raw, expectations=expectations)

    raw, expectations = _fixture(tmp_path / "sbom")
    sbom_path = Path(raw["image"]["sbom"]["host_path"])
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    sbom["cotcodecScan"]["target_image_id"] = "sha256:" + "f" * 64
    sbom_path.write_text(json.dumps(sbom), encoding="utf-8")
    raw["image"]["sbom"]["sha256"] = _sha(sbom_path)
    with pytest.raises(ValueError, match="scanner invocation"):
        validate_manifest(raw, expectations=expectations)


def test_cpu_batch_is_syntax_valid_and_has_no_gpu_or_network() -> None:
    subprocess.run(["bash", "-n", str(BATCH_SCRIPT)], check=True)
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert "--network none" in content
    assert "--read-only" in content
    assert "--cap-drop ALL" in content
    assert "--security-opt no-new-privileges" in content
    assert "--gpus" not in content
    assert "#SBATCH --gres" not in content
    assert "COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready" in content
    assert 'docker wait "${container_name}"' in content
    assert 'docker start "${container_name}"' in content
    assert "Docker failed to start the workload container" in content
    assert 'termination_reason="container_start_failed"' in content
    assert content.count('termination_reason="container_wait_failed"') == 2
    assert 'docker start --attach "${container_name}"' not in content
    assert "local exit_waited=0" in content
    assert '"${exit_waited}" -lt 30' in content
    assert (
        'docker kill --signal "${signal_name}" "${container_name}" '
        ">/dev/null 2>&1 || true"
    ) in content
    assert "flock -n" in content
    assert "image-sbom.spdx.json" in content
    assert "SBOM subject does not bind" in content
    assert "trap write_preflight_termination EXIT" in content
    assert 'scontrol show job "${SLURM_JOB_ID}"' in content
    assert "manifest budget differs from the Slurm allocation" in content


def test_submitter_surfaces_sbatch_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw, expectations = _fixture(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(raw), encoding="utf-8")

    monkeypatch.setattr(
        "scripts.submit_mempalace_cpu_job.validate_manifest",
        lambda _raw: validate_manifest(_raw, expectations=expectations),
    )
    monkeypatch.setattr(
        "scripts.submit_mempalace_cpu_job.subprocess.run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["sbatch"], returncode=1, stdout="", stderr="controller rejected job"
        ),
    )
    monkeypatch.setattr(sys, "argv", ["submit_mempalace_cpu_job.py", str(manifest_path)])

    from scripts.submit_mempalace_cpu_job import main

    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert "sbatch failed: controller rejected job" in capsys.readouterr().err
