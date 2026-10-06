from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

import scripts.seal_past_vllm_sbom_job_receipt as vllm_sealer
from scripts.annotate_image_sbom import seal_sbom
from scripts.seal_mempalace_sbom_job_receipt import (
    SYFT_IMAGE,
    SYFT_IMAGE_ID,
    _verify_image,
    seal_job_receipt,
)
from scripts.seal_past_bench_sbom_job_receipt import (
    EXPECTED_LABELS,
    seal_past_bench_sbom_job,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH_SCRIPT = (
    PROJECT_ROOT / "infra/slurm/host-single-node/mempalace-sbom.sbatch"
)
PAST_BATCH_SCRIPT = (
    PROJECT_ROOT / "infra/slurm/host-single-node/past-bench-sbom.sbatch"
)
VLLM_BATCH_SCRIPT = (
    PROJECT_ROOT / "infra/slurm/host-single-node/past-vllm-sbom.sbatch"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _docker_archive(
    tmp_path: Path,
    *,
    duplicate_layer_reference: bool = False,
    oci_layout_config: bool = False,
) -> tuple[Path, str, list[str]]:
    layer_name = "layer/layer.tar"
    layer_bytes = b"layer fixture"
    layer_digest = f"sha256:{hashlib.sha256(layer_bytes).hexdigest()}"
    rootfs_layers = [layer_digest, layer_digest] if duplicate_layer_reference else [layer_digest]
    manifest_layers = [layer_name, layer_name] if duplicate_layer_reference else [layer_name]
    config = {"architecture": "amd64", "os": "linux", "rootfs": {"diff_ids": rootfs_layers}}
    config_bytes = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    config_name = (
        f"blobs/sha256/{config_sha256}"
        if oci_layout_config
        else f"{config_sha256}.json"
    )
    manifest_bytes = json.dumps(
        [{"Config": config_name, "RepoTags": None, "Layers": manifest_layers}],
        separators=(",", ":"),
    ).encode()
    path = tmp_path / "image.tar"
    with tarfile.open(path, mode="w") as archive:
        for name, contents in (
            (config_name, config_bytes),
            (layer_name, layer_bytes),
            ("manifest.json", manifest_bytes),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(contents))
    return path, f"sha256:{config_sha256}", rootfs_layers


def _fixture(
    tmp_path: Path,
    *,
    duplicate_layer_reference: bool = False,
    oci_layout_config: bool = False,
) -> dict[str, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    archive, target_id, rootfs_layers = _docker_archive(
        tmp_path,
        duplicate_layer_reference=duplicate_layer_reference,
        oci_layout_config=oci_layout_config,
    )
    target_digest = "registry.invalid/mempalace@sha256:" + "2" * 64
    target_inspect = tmp_path / "target-inspect.json"
    target_inspect.write_text(
        json.dumps(
            [
                {
                    "Id": target_id,
                    "RepoDigests": [target_digest],
                    "RootFS": {"Layers": rootfs_layers},
                    "Config": {"Labels": EXPECTED_LABELS},
                }
            ]
        ),
        encoding="utf-8",
    )
    syft_inspect = tmp_path / "syft-inspect.json"
    syft_inspect.write_text(
        json.dumps([{"Id": SYFT_IMAGE_ID, "RepoDigests": [SYFT_IMAGE]}]),
        encoding="utf-8",
    )
    staged_raw = tmp_path / "staged-raw.json"
    staged_raw.write_text(
        json.dumps(
            {
                "SPDXID": "SPDXRef-DOCUMENT",
                "spdxVersion": "SPDX-2.3",
                "creationInfo": {
                    "creators": [
                        "Organization: Anchore, Inc",
                        "Tool: syft-1.51.0",
                    ]
                },
                "packages": [{"SPDXID": "SPDXRef-Package-a", "name": "a"}],
            }
        ),
        encoding="utf-8",
    )
    raw = tmp_path / "raw.json"
    sealed = tmp_path / "sealed.json"
    annotation = tmp_path / "annotation.json"
    seal_sbom(
        raw_path=staged_raw,
        published_raw_path=raw,
        output_path=sealed,
        receipt_path=annotation,
        image_id=target_id,
        repo_digest=target_digest,
        syft_version="1.51.0",
        syft_image=SYFT_IMAGE,
        scanner_target="docker-archive:/input/image.tar",
    )
    batch = tmp_path / "mempalace-sbom.sbatch"
    batch.write_text("#!/usr/bin/env bash\nset -euo pipefail\n", encoding="utf-8")
    gpu = tmp_path / "gpu.txt"
    gpu.write_text("NVIDIA H100 80GB HBM3, GPU-abc, 580.95\n", encoding="utf-8")
    return {
        "target_inspect_path": target_inspect,
        "syft_inspect_path": syft_inspect,
        "publish_target_inspect_path": tmp_path / "published-target.json",
        "publish_syft_inspect_path": tmp_path / "published-syft.json",
        "target_image_id": target_id,
        "target_repo_digest": target_digest,
        "image_archive_path": archive,
        "raw_sbom_path": raw,
        "sealed_sbom_path": sealed,
        "annotation_receipt_path": annotation,
        "batch_script_path": batch,
        "expected_batch_sha256": _sha(batch),
        "gpu_inventory_path": gpu,
        "slurm_job_id": 167,
        "slurm_job_name": "mempalace-sbom",
        "slurm_partition": "research",
        "slurm_cpus_per_task": 8,
        "slurm_memory_mb": 32768,
        "cuda_visible_devices": "0",
        "output_path": tmp_path / "job-receipt.json",
    }


def test_job_receipt_binds_pinned_scanner_batch_and_slurm_allocation(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    receipt = seal_job_receipt(**inputs)

    assert receipt["status"] == "SELF_ATTESTED_DISCOVERY_MEMPALACE_SBOM_JOB"
    assert receipt["external_attestation"] is False
    assert receipt["syft_image"] == SYFT_IMAGE
    assert receipt["scanner_docker_socket_mounted"] is False
    assert receipt["slurm"]["gpu_inventory"] == [
        "NVIDIA H100 80GB HBM3, GPU-abc, 580.95"
    ]
    assert receipt["batch_sha256"] == inputs["expected_batch_sha256"]
    assert receipt["docker_archive_config_sha256"] == str(
        inputs["target_image_id"]
    ).removeprefix("sha256:")
    assert json.loads(inputs["output_path"].read_text(encoding="utf-8")) == receipt


def test_job_receipt_accepts_repeated_empty_layer_reference(tmp_path: Path) -> None:
    inputs = _fixture(
        tmp_path,
        duplicate_layer_reference=True,
        oci_layout_config=True,
    )
    receipt = seal_job_receipt(**inputs)

    assert receipt["docker_archive_layer_count"] == 2


def test_live_inspect_accepts_only_docker_hub_prefix_normalization() -> None:
    image_id = "sha256:" + "1" * 64
    digest = "sha256:" + "2" * 64
    expected = f"docker.io/vllm/vllm-openai@{digest}"
    _verify_image(
        {"Id": image_id, "RepoDigests": [f"vllm/vllm-openai@{digest}"]},
        expected_id=image_id,
        expected_repo_digest=expected,
        label="target",
    )

    with pytest.raises(ValueError, match="repository digest drifted"):
        _verify_image(
            {
                "Id": image_id,
                "RepoDigests": [f"mirror.invalid/vllm/vllm-openai@{digest}"],
            },
            expected_id=image_id,
            expected_repo_digest=expected,
            label="target",
        )


def test_past_job_receipt_binds_candidate_labels_and_allocation(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    inputs.update(
        slurm_job_name="past-bench-sbom",
        slurm_cpus_per_task=8,
        slurm_memory_mb=32768,
    )
    receipt = seal_past_bench_sbom_job(**inputs)

    assert receipt["status"] == "SELF_ATTESTED_DISCOVERY_PAST_BENCH_SBOM_JOB"
    assert receipt["target_image_id"] == inputs["target_image_id"]

    drift = _fixture(tmp_path / "drift")
    target = json.loads(drift["target_inspect_path"].read_text(encoding="utf-8"))
    target[0]["Config"]["Labels"][
        "org.opencontainers.image.cotcodec-publication-ready"
    ] = "true"
    drift["target_inspect_path"].write_text(json.dumps(target), encoding="utf-8")
    drift["slurm_job_name"] = "past-bench-sbom"
    with pytest.raises(ValueError, match="labels"):
        seal_past_bench_sbom_job(**drift)


def test_past_vllm_job_receipt_pins_exact_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_sealer(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": str(kwargs["receipt_status"])}

    monkeypatch.setattr(vllm_sealer, "_seal_job_receipt", fake_sealer)
    with pytest.raises(ValueError, match="image ID"):
        vllm_sealer.seal_past_vllm_sbom_job(
            target_image_id="sha256:" + "0" * 64,
            target_repo_digest=vllm_sealer.TARGET_REPO_DIGEST,
        )
    with pytest.raises(ValueError, match="repository digest"):
        vllm_sealer.seal_past_vllm_sbom_job(
            target_image_id=vllm_sealer.TARGET_IMAGE_ID,
            target_repo_digest="registry.invalid/x@sha256:" + "0" * 64,
        )
    receipt = vllm_sealer.seal_past_vllm_sbom_job(
        target_image_id=vllm_sealer.TARGET_IMAGE_ID,
        target_repo_digest=vllm_sealer.TARGET_REPO_DIGEST,
    )
    assert receipt["status"] == "SELF_ATTESTED_DISCOVERY_PAST_VLLM_SBOM_JOB"
    assert captured["expected_job_name"] == "past-vllm-sbom"


def test_job_receipt_rejects_noncanonical_sealed_sbom_and_batch_drift(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path / "sbom")
    sealed = json.loads(inputs["sealed_sbom_path"].read_text(encoding="utf-8"))
    sealed["packages"][0]["name"] = "fabricated"
    inputs["sealed_sbom_path"].write_text(json.dumps(sealed), encoding="utf-8")
    with pytest.raises(ValueError, match="exact annotation"):
        seal_job_receipt(**inputs)

    inputs = _fixture(tmp_path / "batch")
    inputs["batch_script_path"].write_text("#!/bin/false\n", encoding="utf-8")
    with pytest.raises(ValueError, match="batch script"):
        seal_job_receipt(**inputs)

    inputs = _fixture(tmp_path / "archive")
    inputs["image_archive_path"].write_bytes(b"not a docker archive")
    with pytest.raises(ValueError, match="docker-save tar"):
        seal_job_receipt(**inputs)

    inputs = _fixture(tmp_path / "layer")
    archive_path = inputs["image_archive_path"]
    with tarfile.open(archive_path, mode="r:") as archive:
        rows = [
            (member.name, archive.extractfile(member).read())
            for member in archive
            if member.isfile()
        ]
    archive_path.unlink()
    with tarfile.open(archive_path, mode="w") as archive:
        for name, contents in rows:
            if name == "layer/layer.tar":
                contents = b"substituted layer"
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(contents))
    with pytest.raises(ValueError, match="layer bytes"):
        seal_job_receipt(**inputs)


def test_sbom_batch_is_socket_free_pinned_offline_and_fail_closed() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert SYFT_IMAGE in content
    assert SYFT_IMAGE_ID in content
    assert "/var/run/docker.sock" not in content
    assert "docker image save" in content
    assert "docker-archive:/input/image.tar" in content
    assert content.count("--pull=never") == 3
    assert content.count("--network none") == 3
    assert content.count("--entrypoint /opt/mempalace/source/.venv/bin/python") == 2
    assert "/workspace/cotcodec/scripts/annotate_image_sbom.py" in content
    assert "/workspace/cotcodec/scripts/seal_mempalace_sbom_job_receipt.py" in content
    assert 'chmod 0700 -- "$work_dir"' in content
    assert content.count('--user "$(id -u):$(id -g)"') == 3


def test_past_sbom_batch_is_socket_free_pinned_and_offline() -> None:
    content = PAST_BATCH_SCRIPT.read_text(encoding="utf-8")
    assert SYFT_IMAGE in content
    assert SYFT_IMAGE_ID in content
    assert "/var/run/docker.sock" not in content
    assert "docker push" in content
    assert "^127[.]0[.]0[.]1:5000/cotcodec-past:" in content
    assert "docker-archive:/input/image.tar" in content
    assert content.count("--pull=never") == 2
    assert content.count("--network none") == 2
    assert content.count("mode=1777") == 2
    assert content.count("--pids-limit 4096") == 1
    assert content.count("--pids-limit 512") == 1
    assert "--env GOMAXPROCS=8" in content
    assert "seal_past_bench_sbom_job_receipt.py" in content
    assert "PAST_DISCOVERY_SBOM_PASS_NOT_PUBLICATION_ATTESTATION" in content


def test_past_vllm_sbom_batch_is_archive_scoped_and_offline() -> None:
    content = VLLM_BATCH_SCRIPT.read_text(encoding="utf-8")
    assert SYFT_IMAGE in content
    assert SYFT_IMAGE_ID in content
    assert "/var/run/docker.sock" not in content
    assert 'docker load --input "${verifier_archive}"' in content
    assert "docker push" not in content
    assert "docker-archive:/input/image.tar" in content
    assert content.count("--pull=never") == 2
    assert content.count("--network none") == 2
    assert "seal_past_vllm_sbom_job_receipt.py" in content
    assert "PAST_VLLM_DISCOVERY_SBOM_PASS_NOT_PUBLICATION_ATTESTATION" in content
    assert "SLURM_JOB_GPUS" in content
    assert 'target_repo_digest=${expected_upstream_digest}' in content
    assert content.count('"${verifier_image_id}" /tools/scripts/') == 2
    assert "unregistered vLLM SBOM tool" in content
    assert "vLLM SBOM tool bundle roster is incomplete" in content
    assert 'TMPDIR=/output/syft-tmp' in content
