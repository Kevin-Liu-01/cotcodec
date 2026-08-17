from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest

from scripts.annotate_image_sbom import seal_sbom
from scripts.run_mempalace_upstream_reproduction import ReproductionExpectations
from scripts.seal_mempalace_runtime_receipt import seal_runtime_receipt
from scripts.seal_mempalace_sbom_job_receipt import (
    SYFT_IMAGE,
    SYFT_IMAGE_ID,
    seal_job_receipt,
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _self_seal(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "receipt_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
    }


def _source_archive(tmp_path: Path) -> tuple[Path, Path]:
    archive_path = tmp_path / "cotcodec-source.tar.gz"
    members = {"runner.py": b"print('run')\n", "uv.lock": b"version = 1\n"}
    with (
        archive_path.open("xb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped,
        tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive,
    ):
        for name, contents in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            info.mode = 0o644
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(contents))
    manifest = list(members)
    receipt = {
        "schema_version": 2,
        "mode": "discovery",
        "archive": str(archive_path),
        "archive_sha256": _sha(archive_path),
        "archive_format": "normalized-worktree-tar+gzip-mtime-zero",
        "file_count": len(manifest),
        "file_manifest_sha256": hashlib.sha256(
            json.dumps(manifest, separators=(",", ":")).encode()
        ).hexdigest(),
        "file_manifest": manifest,
        "git_sha": "7" * 40,
        "git_tree": "8" * 40,
        "selected_ref": "HEAD",
        "uv_lock_sha256": hashlib.sha256(members["uv.lock"]).hexdigest(),
        "worktree_clean": False,
        "data_excluded": True,
        "metadata_normalized": True,
    }
    return archive_path, _write(tmp_path / "cotcodec-source.json", receipt)


def _docker_archive(
    tmp_path: Path, labels: dict[str, str]
) -> tuple[Path, str, list[str]]:
    layer_name = "layer/layer.tar"
    layer_bytes = b"layer fixture"
    layer_digest = f"sha256:{hashlib.sha256(layer_bytes).hexdigest()}"
    config = {
        "architecture": "amd64",
        "os": "linux",
        "config": {"Labels": labels},
        "rootfs": {"diff_ids": [layer_digest]},
    }
    config_bytes = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    config_name = f"{config_sha256}.json"
    manifest_bytes = json.dumps(
        [{"Config": config_name, "RepoTags": None, "Layers": [layer_name]}],
        separators=(",", ":"),
    ).encode()
    archive_path = tmp_path / "image.tar"
    with tarfile.open(archive_path, mode="w") as archive:
        for name, contents in (
            (config_name, config_bytes),
            (layer_name, layer_bytes),
            ("manifest.json", manifest_bytes),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(contents))
    return archive_path, f"sha256:{config_sha256}", [layer_digest]


def _fixture(tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    expected = ReproductionExpectations()
    repo_digest = "registry.invalid/mempalace@sha256:" + "2" * 64
    base_reference = "registry.invalid/cotcodec@sha256:" + "3" * 64
    source_context = _write(
        tmp_path / "source-context.json",
        _self_seal(
            {
                "schema_version": 1,
                "status": "VERIFIED_MEMPALACE_SOURCE_CONTEXT",
                "revision": "906b918a7c6ebb2a9198a6bf5a78f30a173fea56",
                "tree": "98789ad017781f52550b511fcedd9e00c3346761",
                "source_archive_sha256": expected.source_archive_sha256,
                "file_manifest": [],
            }
        ),
    )
    minilm = _write(
        tmp_path / "minilm.json",
        _self_seal(
            {
                "schema_version": 1,
                "status": "VERIFIED_CHROMA_MINILM_ARTIFACT",
                "model": "all-MiniLM-L6-v2",
                "archive_sha256": (
                    "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
                ),
                "artifact_root_sha256": "5" * 64,
            }
        ),
    )
    cotcodec_archive, cotcodec_source = _source_archive(tmp_path)
    cotcodec_source_payload = json.loads(cotcodec_source.read_text(encoding="utf-8"))
    labels = {
        "org.opencontainers.image.revision": (
            "906b918a7c6ebb2a9198a6bf5a78f30a173fea56"
        ),
        "org.opencontainers.image.mempalace-tree": (
            "98789ad017781f52550b511fcedd9e00c3346761"
        ),
        "org.opencontainers.image.mempalace-source-archive-sha256": (
            expected.source_archive_sha256
        ),
        "org.opencontainers.image.mempalace-runner-sha256": expected.runner_sha256,
        "org.opencontainers.image.mempalace-uv-lock-sha256": expected.lock_sha256,
        "org.opencontainers.image.minilm-archive-sha256": (
            "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
        ),
        "org.opencontainers.image.minilm-artifact-root-sha256": "5" * 64,
        "org.opencontainers.image.cotcodec-base-reference": base_reference,
        "org.opencontainers.image.source-tree-sha256": cotcodec_source_payload[
            "archive_sha256"
        ],
        "org.opencontainers.image.cotcodec-git-sha": "7" * 40,
        "org.opencontainers.image.cotcodec-git-tree": "8" * 40,
        "org.opencontainers.image.cotcodec-publication-ready": "false",
    }
    image_archive, image_id, rootfs_layers = _docker_archive(tmp_path, labels)
    staged_target_inspect = _write(
        tmp_path / "staged-target-inspect.json",
        [
            {
                "Id": image_id,
                "RepoDigests": [repo_digest],
                "Config": {"Labels": labels},
                "RootFS": {"Layers": rootfs_layers},
            }
        ],
    )
    syft_inspect = _write(
        tmp_path / "syft-inspect.json",
        [{"Id": SYFT_IMAGE_ID, "RepoDigests": [SYFT_IMAGE]}],
    )
    staged_raw = _write(
        tmp_path / "staged-raw.json",
        {
            "SPDXID": "SPDXRef-DOCUMENT",
            "spdxVersion": "SPDX-2.3",
            "creationInfo": {
                "creators": ["Organization: Anchore, Inc", "Tool: syft-1.51.0"]
            },
            "packages": [{"SPDXID": "SPDXRef-Package-a", "name": "a"}],
        },
    )
    raw_sbom = tmp_path / "raw-sbom.json"
    sealed_sbom = tmp_path / "sealed-sbom.json"
    annotation = tmp_path / "annotation.json"
    seal_sbom(
        raw_path=staged_raw,
        published_raw_path=raw_sbom,
        output_path=sealed_sbom,
        receipt_path=annotation,
        image_id=image_id,
        repo_digest=repo_digest,
        syft_version="1.51.0",
        syft_image=SYFT_IMAGE,
        scanner_target="docker-archive:/input/image.tar",
    )
    batch = tmp_path / "batch.sbatch"
    batch.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    gpu = tmp_path / "gpu.txt"
    gpu.write_text("NVIDIA H100 80GB HBM3, GPU-abc, 580.95\n", encoding="utf-8")
    image_inspect = tmp_path / "target-inspect.json"
    published_syft_inspect = tmp_path / "published-syft-inspect.json"
    job_receipt_path = tmp_path / "job-receipt.json"
    seal_job_receipt(
        target_inspect_path=staged_target_inspect,
        syft_inspect_path=syft_inspect,
        publish_target_inspect_path=image_inspect,
        publish_syft_inspect_path=published_syft_inspect,
        target_image_id=image_id,
        target_repo_digest=repo_digest,
        image_archive_path=image_archive,
        raw_sbom_path=raw_sbom,
        sealed_sbom_path=sealed_sbom,
        annotation_receipt_path=annotation,
        batch_script_path=batch,
        expected_batch_sha256=_sha(batch),
        gpu_inventory_path=gpu,
        slurm_job_id=167,
        slurm_job_name="mempalace-sbom",
        slurm_partition="research",
        slurm_cpus_per_task=8,
        slurm_memory_mb=32768,
        cuda_visible_devices="0",
        output_path=job_receipt_path,
    )
    return {
        "image_inspect_path": image_inspect,
        "expected_image_id": image_id,
        "expected_repo_digest": repo_digest,
        "expected_cotcodec_base_reference": base_reference,
        "source_context_receipt_path": source_context,
        "minilm_receipt_path": minilm,
        "cotcodec_source_receipt_path": cotcodec_source,
        "cotcodec_source_archive_path": cotcodec_archive,
        "raw_sbom_path": raw_sbom,
        "sealed_sbom_path": sealed_sbom,
        "sbom_annotation_receipt_path": annotation,
        "sbom_job_receipt_path": job_receipt_path,
        "sbom_batch_path": batch,
        "syft_image_inspect_path": published_syft_inspect,
        "syft_image": SYFT_IMAGE,
        "syft_version": "1.51.0",
        "output_path": tmp_path / "runtime.json",
    }


def test_seal_runtime_receipt_binds_all_runtime_evidence(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    receipt = seal_runtime_receipt(**inputs)

    assert receipt["status"] == "SELF_ATTESTED_DISCOVERY_MEMPALACE_RUNTIME"
    assert receipt["external_attestation"] is False
    assert receipt["publication_ready"] is False
    assert receipt["image_id"] == inputs["expected_image_id"]
    assert receipt["image_repo_digest"] == inputs["expected_repo_digest"]
    assert receipt["sbom_batch_sha256"] == _sha(inputs["sbom_batch_path"])
    assert receipt["sbom_slurm_job_id"] == 167
    assert json.loads(inputs["output_path"].read_text(encoding="utf-8")) == receipt


def test_seal_runtime_receipt_rejects_label_source_and_job_drift(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path / "label")
    inspect = json.loads(inputs["image_inspect_path"].read_text(encoding="utf-8"))
    inspect[0]["Config"]["Labels"][
        "org.opencontainers.image.source-tree-sha256"
    ] = "0" * 64
    _write(inputs["image_inspect_path"], inspect)
    with pytest.raises(ValueError, match="labels|job receipt"):
        seal_runtime_receipt(**inputs)

    inputs = _fixture(tmp_path / "source")
    inputs["cotcodec_source_archive_path"].write_bytes(b"fabricated archive")
    with pytest.raises(ValueError, match="source receipt|source archive"):
        seal_runtime_receipt(**inputs)

    inputs = _fixture(tmp_path / "job")
    job = json.loads(inputs["sbom_job_receipt_path"].read_text(encoding="utf-8"))
    job["scanner_docker_socket_mounted"] = True
    _write(inputs["sbom_job_receipt_path"], job)
    with pytest.raises(ValueError, match="self-digest"):
        seal_runtime_receipt(**inputs)


def test_seal_runtime_receipt_refuses_overwrite(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    seal_runtime_receipt(**inputs)
    before = inputs["output_path"].read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        seal_runtime_receipt(**inputs)
    assert inputs["output_path"].read_bytes() == before
