#!/usr/bin/env python3
"""Seal one discovery-only MemPalace runtime from independently hashed evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from scripts.run_mempalace_upstream_reproduction import (
    MEMPALACE_CHROMADB_VERSION,
    MEMPALACE_MINILM_ARCHIVE_SHA256,
    MEMPALACE_MINILM_MODEL,
    MEMPALACE_REVISION,
    MEMPALACE_TREE,
    ReproductionExpectations,
)
from scripts.seal_mempalace_sbom_job_receipt import (
    SYFT_IMAGE,
    SYFT_IMAGE_ID,
    SYFT_VERSION,
)

SHA256_RE = re.compile(r"[0-9a-f]{64}")
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
REPO_DIGEST_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}"
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular non-symlink file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return payload


def _load_single_inspect(path: Path, label: str) -> list[dict[str, Any]]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular non-symlink file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if (
        not isinstance(payload, list)
        or len(payload) != 1
        or not isinstance(payload[0], dict)
    ):
        raise ValueError(f"{label} must describe exactly one image")
    return payload


def _require_self_digest(payload: dict[str, Any], label: str) -> str:
    receipt_sha256 = payload.get("receipt_sha256")
    unsigned = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    computed = hashlib.sha256(_canonical(unsigned)).hexdigest()
    if receipt_sha256 != computed:
        raise ValueError(f"{label} self-digest is invalid")
    return computed


def _write_once(path: Path, payload: dict[str, Any]) -> None:
    path = Path(os.path.abspath(os.fspath(path)))
    if any(component.is_symlink() for component in (path, *path.parents)):
        raise ValueError("runtime receipt output path cannot contain symbolic links")
    if path.exists():
        raise ValueError(f"refusing to overwrite runtime receipt: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical(payload) + b"\n"
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        temporary.write(encoded)
        temporary.flush()
        os.fsync(temporary.fileno())
    try:
        os.link(temporary_path, path)
    except FileExistsError as exc:
        raise ValueError(f"refusing to overwrite runtime receipt: {path}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_discovery_archive(
    archive_path: Path, receipt: dict[str, Any]
) -> tuple[str, str, str]:
    if not archive_path.is_file() or archive_path.is_symlink():
        raise ValueError("CoTCodec source archive must be a regular non-symlink file")
    archive_sha256 = _sha256_file(archive_path)
    expected_fields = {
        "schema_version": 2,
        "mode": "discovery",
        "archive_format": "normalized-worktree-tar+gzip-mtime-zero",
        "selected_ref": "HEAD",
        "worktree_clean": False,
        "data_excluded": True,
        "metadata_normalized": True,
        "archive_sha256": archive_sha256,
    }
    if any(receipt.get(key) != value for key, value in expected_fields.items()):
        raise ValueError("CoTCodec source receipt is not an honest discovery archive")
    expected_manifest = receipt.get("file_manifest")
    if not isinstance(expected_manifest, list) or not expected_manifest or any(
        not isinstance(path, str) or not path for path in expected_manifest
    ):
        raise ValueError("CoTCodec discovery file manifest is malformed")
    manifest_root = hashlib.sha256(
        json.dumps(expected_manifest, separators=(",", ":")).encode()
    ).hexdigest()
    if (
        receipt.get("file_count") != len(expected_manifest)
        or receipt.get("file_manifest_sha256") != manifest_root
    ):
        raise ValueError("CoTCodec discovery file manifest digest drifted")
    actual_manifest: list[str] = []
    uv_lock_sha256: str | None = None
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive.getmembers():
                if (
                    not member.isfile()
                    or member.name.startswith("/")
                    or ".." in Path(member.name).parts
                    or member.uid != 0
                    or member.gid != 0
                    or member.mtime != 0
                    or member.mode not in {0o644, 0o755}
                ):
                    raise ValueError("CoTCodec source archive member is unsafe")
                actual_manifest.append(member.name)
                if member.name == "uv.lock":
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise ValueError("CoTCodec source archive lost uv.lock")
                    uv_lock_sha256 = hashlib.sha256(extracted.read()).hexdigest()
    except (OSError, tarfile.TarError) as exc:
        raise ValueError("CoTCodec source archive is invalid") from exc
    if actual_manifest != expected_manifest:
        raise ValueError("CoTCodec source archive differs from its file manifest")
    if uv_lock_sha256 is None or receipt.get("uv_lock_sha256") != uv_lock_sha256:
        raise ValueError("CoTCodec source archive uv.lock drifted")
    git_sha = receipt.get("git_sha")
    git_tree = receipt.get("git_tree")
    if (
        not isinstance(git_sha, str)
        or re.fullmatch(r"[0-9a-f]{40}", git_sha) is None
        or not isinstance(git_tree, str)
        or re.fullmatch(r"[0-9a-f]{40}", git_tree) is None
    ):
        raise ValueError("CoTCodec Git identities are malformed")
    return archive_sha256, git_sha, git_tree


def seal_runtime_receipt(
    *,
    image_inspect_path: Path,
    expected_image_id: str,
    expected_repo_digest: str,
    expected_cotcodec_base_reference: str,
    source_context_receipt_path: Path,
    minilm_receipt_path: Path,
    cotcodec_source_receipt_path: Path,
    cotcodec_source_archive_path: Path,
    raw_sbom_path: Path,
    sealed_sbom_path: Path,
    sbom_annotation_receipt_path: Path,
    sbom_job_receipt_path: Path,
    sbom_batch_path: Path,
    syft_image_inspect_path: Path,
    syft_image: str,
    syft_version: str,
    output_path: Path,
) -> dict[str, Any]:
    if IMAGE_ID_RE.fullmatch(expected_image_id) is None:
        raise ValueError("expected image ID is not immutable")
    for label, reference in (
        ("image repository digest", expected_repo_digest),
        ("CoTCodec base reference", expected_cotcodec_base_reference),
        ("Syft image", syft_image),
    ):
        if REPO_DIGEST_RE.fullmatch(reference) is None:
            raise ValueError(f"{label} is not immutable")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", syft_version):
        raise ValueError("Syft version must be semantic x.y.z")
    if syft_image != SYFT_IMAGE or syft_version != SYFT_VERSION:
        raise ValueError("Syft identity differs from the reviewed discovery scanner")
    inspect_path = image_inspect_path
    if not inspect_path.is_file() or inspect_path.is_symlink():
        raise ValueError("image inspect must be a regular non-symlink file")
    try:
        inspect_payload = json.loads(inspect_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("image inspect is not valid JSON") from exc
    if not isinstance(inspect_payload, list) or len(inspect_payload) != 1:
        raise ValueError("image inspect must contain exactly one image")
    image = inspect_payload[0]
    if not isinstance(image, dict) or image.get("Id") != expected_image_id:
        raise ValueError("live image ID differs from the registered image")
    repo_digests = image.get("RepoDigests")
    if not isinstance(repo_digests, list) or expected_repo_digest not in repo_digests:
        raise ValueError("live image lacks the registered repository digest")
    labels = image.get("Config", {}).get("Labels", {})
    if not isinstance(labels, dict):
        raise ValueError("live image labels are malformed")

    expectations = ReproductionExpectations()
    source_context = _load_json(source_context_receipt_path, "source context receipt")
    source_context_sha256 = _require_self_digest(
        source_context, "source context receipt"
    )
    expected_source_context = {
        "schema_version": 1,
        "status": "VERIFIED_MEMPALACE_SOURCE_CONTEXT",
        "revision": MEMPALACE_REVISION,
        "tree": MEMPALACE_TREE,
        "source_archive_sha256": expectations.source_archive_sha256,
    }
    if any(source_context.get(key) != value for key, value in expected_source_context.items()):
        raise ValueError("MemPalace source context identity drifted")

    minilm = _load_json(minilm_receipt_path, "MiniLM receipt")
    minilm_receipt_sha256 = _require_self_digest(minilm, "MiniLM receipt")
    expected_minilm = {
        "schema_version": 1,
        "status": "VERIFIED_CHROMA_MINILM_ARTIFACT",
        "model": MEMPALACE_MINILM_MODEL,
        "archive_sha256": MEMPALACE_MINILM_ARCHIVE_SHA256,
    }
    if any(minilm.get(key) != value for key, value in expected_minilm.items()):
        raise ValueError("MiniLM artifact identity drifted")
    embedding_root = minilm.get("artifact_root_sha256")
    if not isinstance(embedding_root, str) or SHA256_RE.fullmatch(embedding_root) is None:
        raise ValueError("MiniLM artifact root is malformed")

    cotcodec_source = _load_json(
        cotcodec_source_receipt_path, "CoTCodec source receipt"
    )
    cotcodec_archive_sha256, cotcodec_git_sha, cotcodec_git_tree = (
        _validate_discovery_archive(cotcodec_source_archive_path, cotcodec_source)
    )

    expected_labels = {
        "org.opencontainers.image.revision": MEMPALACE_REVISION,
        "org.opencontainers.image.mempalace-tree": MEMPALACE_TREE,
        "org.opencontainers.image.mempalace-source-archive-sha256": (
            expectations.source_archive_sha256
        ),
        "org.opencontainers.image.mempalace-runner-sha256": (
            expectations.runner_sha256
        ),
        "org.opencontainers.image.mempalace-uv-lock-sha256": expectations.lock_sha256,
        "org.opencontainers.image.minilm-archive-sha256": (
            MEMPALACE_MINILM_ARCHIVE_SHA256
        ),
        "org.opencontainers.image.minilm-artifact-root-sha256": embedding_root,
        "org.opencontainers.image.cotcodec-base-reference": (
            expected_cotcodec_base_reference
        ),
        "org.opencontainers.image.source-tree-sha256": cotcodec_archive_sha256,
        "org.opencontainers.image.cotcodec-git-sha": cotcodec_git_sha,
        "org.opencontainers.image.cotcodec-git-tree": cotcodec_git_tree,
        "org.opencontainers.image.cotcodec-publication-ready": "false",
    }
    if any(labels.get(key) != value for key, value in expected_labels.items()):
        raise ValueError("live image labels differ from the sealed input receipts")

    for path, label in (
        (raw_sbom_path, "raw SBOM"),
        (sealed_sbom_path, "sealed SBOM"),
    ):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"{label} must be a regular non-symlink file")
    raw_sbom_sha256 = _sha256_file(raw_sbom_path)
    sealed_sbom_sha256 = _sha256_file(sealed_sbom_path)
    annotation = _load_json(
        sbom_annotation_receipt_path, "SBOM annotation receipt"
    )
    annotation_receipt_sha256 = _require_self_digest(
        annotation, "SBOM annotation receipt"
    )
    expected_annotation = {
        "status": "SEALED_SYFT_SBOM_SUBJECT_BINDING",
        "target_image_id": expected_image_id,
        "target_repo_digest": expected_repo_digest,
        "syft_image": syft_image,
        "syft_version": syft_version,
        "raw_sbom_sha256": raw_sbom_sha256,
        "sealed_sbom_sha256": sealed_sbom_sha256,
        "discovered_packages_unchanged": True,
    }
    if any(annotation.get(key) != value for key, value in expected_annotation.items()):
        raise ValueError("SBOM annotation receipt differs from its sealed artifacts")
    sealed_sbom = _load_json(sealed_sbom_path, "sealed SBOM")
    if sealed_sbom.get("cotcodecScan") != {
        "scanner": "syft",
        "scanner_version": syft_version,
        "target_repo_digest": expected_repo_digest,
        "target_image_id": expected_image_id,
        "argv": [
            "syft",
            "docker-archive:/input/image.tar",
            "--output",
            "spdx-json",
        ],
    }:
        raise ValueError("sealed SBOM subject binding drifted")
    if not sbom_batch_path.is_file() or sbom_batch_path.is_symlink():
        raise ValueError("SBOM batch script must be a regular non-symlink file")
    job_receipt = _load_json(sbom_job_receipt_path, "SBOM Slurm job receipt")
    job_receipt_sha256 = _require_self_digest(
        job_receipt, "SBOM Slurm job receipt"
    )
    raw_syft_inspect = _load_single_inspect(
        syft_image_inspect_path, "Syft image inspect"
    )
    if (
        not isinstance(raw_syft_inspect, list)
        or len(raw_syft_inspect) != 1
        or not isinstance(raw_syft_inspect[0], dict)
        or raw_syft_inspect[0].get("Id") != SYFT_IMAGE_ID
        or SYFT_IMAGE not in raw_syft_inspect[0].get("RepoDigests", [])
    ):
        raise ValueError("Syft image inspect differs from the reviewed scanner")
    slurm = job_receipt.get("slurm")
    if (
        not isinstance(slurm, dict)
        or set(slurm) != {
            "job_id",
            "job_name",
            "partition",
            "cpus_per_task",
            "memory_mb",
            "cuda_visible_devices",
            "gpu_inventory",
        }
        or not isinstance(slurm.get("job_id"), int)
        or slurm["job_id"] <= 0
        or slurm.get("job_name") != "mempalace-sbom"
        or slurm.get("partition") != "research"
        or slurm.get("cpus_per_task") != 8
        or slurm.get("memory_mb") != 32768
        or re.fullmatch(r"[0-7]", str(slurm.get("cuda_visible_devices", ""))) is None
        or not isinstance(slurm.get("gpu_inventory"), list)
        or not slurm["gpu_inventory"]
        or any("H100" not in value for value in slurm["gpu_inventory"])
    ):
        raise ValueError("SBOM Slurm allocation evidence is invalid")
    archive_fields = {
        "docker_archive_sha256": job_receipt.get("docker_archive_sha256"),
        "docker_archive_member_root_sha256": job_receipt.get(
            "docker_archive_member_root_sha256"
        ),
        "docker_archive_config_sha256": job_receipt.get(
            "docker_archive_config_sha256"
        ),
        "docker_archive_layer_count": job_receipt.get("docker_archive_layer_count"),
    }
    if (
        any(
            not isinstance(value, str) or SHA256_RE.fullmatch(value) is None
            for key, value in archive_fields.items()
            if key != "docker_archive_layer_count"
        )
        or archive_fields["docker_archive_config_sha256"]
        != expected_image_id.removeprefix("sha256:")
        or not isinstance(archive_fields["docker_archive_layer_count"], int)
        or archive_fields["docker_archive_layer_count"] <= 0
    ):
        raise ValueError("SBOM Docker archive evidence is invalid")
    expected_job_unsigned = {
        "schema_version": 1,
        "status": "SELF_ATTESTED_DISCOVERY_MEMPALACE_SBOM_JOB",
        "scientific_result": False,
        "external_attestation": False,
        "slurm": slurm,
        "batch_sha256": _sha256_file(sbom_batch_path),
        "target_image_id": expected_image_id,
        "target_repo_digest": expected_repo_digest,
        "target_image_inspect_sha256": _sha256_file(image_inspect_path),
        "syft_image": SYFT_IMAGE,
        "syft_image_id": SYFT_IMAGE_ID,
        "syft_version": SYFT_VERSION,
        "syft_image_inspect_sha256": _sha256_file(syft_image_inspect_path),
        **archive_fields,
        "scan_argv": [
            "syft",
            "docker-archive:/input/image.tar",
            "--output",
            "spdx-json",
        ],
        "scan_network": "none",
        "scanner_docker_socket_mounted": False,
        "raw_sbom_sha256": raw_sbom_sha256,
        "sealed_sbom_sha256": sealed_sbom_sha256,
        "annotation_receipt_sha256": annotation_receipt_sha256,
    }
    if {
        key: value for key, value in job_receipt.items() if key != "receipt_sha256"
    } != expected_job_unsigned:
        raise ValueError("SBOM Slurm job receipt schema or evidence drifted")

    receipt = {
        "schema_version": 1,
        "status": "SELF_ATTESTED_DISCOVERY_MEMPALACE_RUNTIME",
        "scientific_result": False,
        "publication_ready": False,
        "external_attestation": False,
        "repository_revision": MEMPALACE_REVISION,
        "repository_tree": MEMPALACE_TREE,
        "source_archive_sha256": expectations.source_archive_sha256,
        "runner_sha256": expectations.runner_sha256,
        "uv_lock_sha256": expectations.lock_sha256,
        "chromadb_version": MEMPALACE_CHROMADB_VERSION,
        "embedding_model": MEMPALACE_MINILM_MODEL,
        "embedding_archive_sha256": MEMPALACE_MINILM_ARCHIVE_SHA256,
        "embedding_artifact_root_sha256": embedding_root,
        "minilm_receipt_sha256": minilm_receipt_sha256,
        "mempalace_source_receipt_sha256": source_context_sha256,
        "execution_provider": "CPUExecutionProvider",
        "network_policy": "none",
        "image_id": expected_image_id,
        "image_repo_digest": expected_repo_digest,
        "image_inspect_sha256": _sha256_file(image_inspect_path),
        "image_sbom_sha256": sealed_sbom_sha256,
        "raw_sbom_sha256": raw_sbom_sha256,
        "sbom_annotation_receipt_sha256": annotation_receipt_sha256,
        "sbom_batch_sha256": _sha256_file(sbom_batch_path),
        "syft_image": syft_image,
        "syft_image_id": SYFT_IMAGE_ID,
        "syft_image_inspect_sha256": _sha256_file(syft_image_inspect_path),
        "syft_version": syft_version,
        "cotcodec_base_image_reference": expected_cotcodec_base_reference,
        "cotcodec_discovery_source_archive_sha256": cotcodec_archive_sha256,
        "cotcodec_source_receipt_sha256": _sha256_file(cotcodec_source_receipt_path),
        "cotcodec_git_sha": cotcodec_git_sha,
        "cotcodec_git_tree": cotcodec_git_tree,
        "cotcodec_worktree_clean": False,
        "sbom_slurm_job_id": slurm["job_id"],
        "sbom_slurm_job_receipt_sha256": job_receipt_sha256,
    }
    _write_once(output_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-inspect", type=Path, required=True)
    parser.add_argument("--expected-image-id", required=True)
    parser.add_argument("--expected-repo-digest", required=True)
    parser.add_argument("--expected-cotcodec-base-reference", required=True)
    parser.add_argument("--source-context-receipt", type=Path, required=True)
    parser.add_argument("--minilm-receipt", type=Path, required=True)
    parser.add_argument("--cotcodec-source-receipt", type=Path, required=True)
    parser.add_argument("--cotcodec-source-archive", type=Path, required=True)
    parser.add_argument("--raw-sbom", type=Path, required=True)
    parser.add_argument("--sealed-sbom", type=Path, required=True)
    parser.add_argument("--sbom-annotation-receipt", type=Path, required=True)
    parser.add_argument("--sbom-job-receipt", type=Path, required=True)
    parser.add_argument("--sbom-batch", type=Path, required=True)
    parser.add_argument("--syft-image-inspect", type=Path, required=True)
    parser.add_argument("--syft-image", required=True)
    parser.add_argument("--syft-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = seal_runtime_receipt(
            image_inspect_path=args.image_inspect,
            expected_image_id=args.expected_image_id,
            expected_repo_digest=args.expected_repo_digest,
            expected_cotcodec_base_reference=args.expected_cotcodec_base_reference,
            source_context_receipt_path=args.source_context_receipt,
            minilm_receipt_path=args.minilm_receipt,
            cotcodec_source_receipt_path=args.cotcodec_source_receipt,
            cotcodec_source_archive_path=args.cotcodec_source_archive,
            raw_sbom_path=args.raw_sbom,
            sealed_sbom_path=args.sealed_sbom,
            sbom_annotation_receipt_path=args.sbom_annotation_receipt,
            sbom_job_receipt_path=args.sbom_job_receipt,
            sbom_batch_path=args.sbom_batch,
            syft_image_inspect_path=args.syft_image_inspect,
            syft_image=args.syft_image,
            syft_version=args.syft_version,
            output_path=args.output,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
