#!/usr/bin/env python3
"""Seal evidence emitted by the pinned MemPalace SBOM Slurm batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.annotate_image_sbom import (
    SUBJECT_ID,
    _canonical,
    _load_raw,
    _sha256_file,
    _write_bytes_once,
    _write_once,
    annotate,
)

SYFT_IMAGE = (
    "anchore/syft@sha256:"
    "41f8289664101d6ebab30a97ac8df6b6f86b92d8343285ca90f428e2bc353106"
)
SYFT_IMAGE_ID = (
    "sha256:e6ff5da240b940ab010282f502ae688019379cdee51578f76374ed9b29ef03e6"
)
SYFT_VERSION = "1.51.0"
SCANNER_TARGET = "docker-archive:/input/image.tar"
REPO_DIGEST_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}"
)
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")


def _load_single_inspect(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} inspect must be a regular non-symlink file")
    encoded = path.read_bytes()
    try:
        payload = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} inspect is not valid JSON") from exc
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(
        payload[0], dict
    ):
        raise ValueError(f"{label} inspect must describe exactly one image")
    return payload[0], encoded


def _verify_image(
    image: dict[str, Any], *, expected_id: str, expected_repo_digest: str, label: str
) -> None:
    if image.get("Id") != expected_id:
        raise ValueError(f"{label} image ID drifted")
    repo_digests = image.get("RepoDigests")
    if not isinstance(repo_digests, list) or not all(
        isinstance(value, str) for value in repo_digests
    ):
        raise ValueError(f"{label} repository digest drifted")

    # Docker's live inspect drops the explicit Docker Hub registry prefix. The
    # acquisition receipt intentionally retains it. Accept only these two
    # spellings; never normalize a different registry or a mutable tag.
    expected_aliases = {expected_repo_digest}
    if expected_repo_digest.startswith("docker.io/"):
        expected_aliases.add(expected_repo_digest.removeprefix("docker.io/"))
    if expected_aliases.isdisjoint(repo_digests):
        raise ValueError(f"{label} repository digest drifted")


def _self_digest(payload: dict[str, Any], label: str) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    digest = hashlib.sha256(_canonical(unsigned)).hexdigest()
    if payload.get("receipt_sha256") != digest:
        raise ValueError(f"{label} self-digest is invalid")
    return digest


def _verify_docker_archive(
    path: Path, *, target_image_id: str, target_inspect: dict[str, Any]
) -> dict[str, Any]:
    """Bind the scanned docker-save archive to the inspected image config."""

    if not path.is_file() or path.is_symlink():
        raise ValueError("Docker image archive must be a regular non-symlink file")
    members: dict[str, tarfile.TarInfo] = {}
    member_rows: list[dict[str, Any]] = []
    file_sha256: dict[str, str] = {}
    small_json_contents: dict[str, bytes] = {}
    expected_oci_config_name = (
        f"blobs/sha256/{target_image_id.removeprefix('sha256:')}"
    )
    try:
        with tarfile.open(path, mode="r:") as archive:
            for member in archive:
                member_path = PurePosixPath(member.name)
                if (
                    member_path.is_absolute()
                    or ".." in member_path.parts
                    or member.name in members
                    or not (member.isfile() or member.isdir())
                ):
                    raise ValueError("Docker image archive contains an unsafe member")
                members[member.name] = member
                row: dict[str, Any] = {
                    "name": member.name,
                    "type": "file" if member.isfile() else "directory",
                    "mode": member.mode,
                    "size": member.size,
                }
                if member.isfile():
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise ValueError("Docker image archive contains an unreadable file")
                    digest = hashlib.sha256()
                    retained = bytearray()
                    retain_json = (
                        member.name.endswith(".json")
                        or member.name == expected_oci_config_name
                    ) and member.size <= 16 * 1024 * 1024
                    while chunk := extracted.read(1024 * 1024):
                        digest.update(chunk)
                        if retain_json:
                            retained.extend(chunk)
                    row["sha256"] = digest.hexdigest()
                    file_sha256[member.name] = row["sha256"]
                    if retain_json:
                        small_json_contents[member.name] = bytes(retained)
                member_rows.append(row)
    except (OSError, tarfile.TarError) as exc:
        raise ValueError("Docker image archive is not a valid docker-save tar") from exc

    manifest_bytes = small_json_contents.get("manifest.json")
    if manifest_bytes is None:
        raise ValueError("Docker image archive is missing manifest.json")
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Docker image archive manifest is invalid") from exc
    if not isinstance(manifest, list) or len(manifest) != 1 or not isinstance(
        manifest[0], dict
    ):
        raise ValueError("Docker image archive must contain exactly one image manifest")
    image_manifest = manifest[0]
    config_name = image_manifest.get("Config")
    layer_names = image_manifest.get("Layers")
    if (
        not isinstance(config_name, str)
        or not isinstance(layer_names, list)
        or not layer_names
        or any(not isinstance(name, str) or not name for name in layer_names)
    ):
        raise ValueError("Docker image archive config/layer roster is malformed")
    for name in (config_name, *layer_names):
        name_path = PurePosixPath(name)
        if name_path.is_absolute() or ".." in name_path.parts or name not in file_sha256:
            raise ValueError("Docker image archive references a missing or unsafe file")

    config_bytes = small_json_contents.get(config_name)
    if config_bytes is None:
        raise ValueError("Docker image archive config is missing or unreasonably large")
    expected_config_sha256 = target_image_id.removeprefix("sha256:")
    actual_config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    if actual_config_sha256 != expected_config_sha256:
        raise ValueError("Docker image archive config does not match target image ID")
    try:
        config = json.loads(config_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Docker image archive config is invalid") from exc
    if not isinstance(config, dict):
        raise ValueError("Docker image archive config must be one JSON object")
    inspect_layers = target_inspect.get("RootFS", {}).get("Layers")
    config_layers = config.get("rootfs", {}).get("diff_ids")
    archive_layer_diff_ids = [
        f"sha256:{file_sha256[name]}"
        for name in layer_names
    ]
    if (
        not isinstance(inspect_layers, list)
        or not inspect_layers
        or config_layers != inspect_layers
        or archive_layer_diff_ids != inspect_layers
    ):
        raise ValueError(
            "Docker image archive layer bytes differ from config or target inspect"
        )

    ordered_rows = sorted(member_rows, key=lambda row: row["name"].encode())
    return {
        "docker_archive_sha256": _sha256_file(path),
        "docker_archive_member_root_sha256": hashlib.sha256(
            _canonical(ordered_rows)
        ).hexdigest(),
        "docker_archive_config_sha256": actual_config_sha256,
        "docker_archive_layer_count": len(layer_names),
    }


def _seal_job_receipt(
    *,
    target_inspect_path: Path,
    syft_inspect_path: Path,
    publish_target_inspect_path: Path,
    publish_syft_inspect_path: Path,
    target_image_id: str,
    target_repo_digest: str,
    image_archive_path: Path,
    raw_sbom_path: Path,
    sealed_sbom_path: Path,
    annotation_receipt_path: Path,
    batch_script_path: Path,
    expected_batch_sha256: str,
    gpu_inventory_path: Path,
    slurm_job_id: int,
    slurm_job_name: str,
    slurm_partition: str,
    slurm_cpus_per_task: int,
    slurm_memory_mb: int,
    cuda_visible_devices: str,
    output_path: Path,
    expected_job_name: str,
    expected_cpus_per_task: int,
    expected_memory_mb: int,
    receipt_status: str,
    expected_target_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    if IMAGE_ID_RE.fullmatch(target_image_id) is None:
        raise ValueError("target image ID is malformed")
    if REPO_DIGEST_RE.fullmatch(target_repo_digest) is None:
        raise ValueError("target repository digest is malformed")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_batch_sha256):
        raise ValueError("batch SHA-256 is malformed")
    if (
        slurm_job_id <= 0
        or slurm_job_name != expected_job_name
        or slurm_partition != "research"
        or slurm_cpus_per_task != expected_cpus_per_task
        or slurm_memory_mb != expected_memory_mb
        or not re.fullmatch(r"[0-7]", cuda_visible_devices)
    ):
        raise ValueError("Slurm allocation differs from the registered SBOM cell")

    target, target_encoded = _load_single_inspect(
        target_inspect_path, "target image"
    )
    syft, syft_encoded = _load_single_inspect(syft_inspect_path, "Syft image")
    _verify_image(
        target,
        expected_id=target_image_id,
        expected_repo_digest=target_repo_digest,
        label="target",
    )
    target_labels = target.get("Config", {}).get("Labels", {})
    if not isinstance(target_labels, dict) or any(
        target_labels.get(key) != value
        for key, value in (expected_target_labels or {}).items()
    ):
        raise ValueError("target image labels differ from the registered contract")
    _verify_image(
        syft,
        expected_id=SYFT_IMAGE_ID,
        expected_repo_digest=SYFT_IMAGE,
        label="Syft",
    )
    if not batch_script_path.is_file() or batch_script_path.is_symlink():
        raise ValueError("batch script must be a regular non-symlink file")
    if _sha256_file(batch_script_path) != expected_batch_sha256:
        raise ValueError("running batch script differs from its registered digest")
    archive_evidence = _verify_docker_archive(
        image_archive_path,
        target_image_id=target_image_id,
        target_inspect=target,
    )

    raw = _load_raw(raw_sbom_path, SYFT_VERSION)
    expected_sealed = annotate(
        raw,
        image_id=target_image_id,
        repo_digest=target_repo_digest,
        syft_version=SYFT_VERSION,
        scanner_target=SCANNER_TARGET,
    )
    if not sealed_sbom_path.is_file() or sealed_sbom_path.is_symlink():
        raise ValueError("sealed SBOM must be a regular non-symlink file")
    try:
        actual_sealed = json.loads(sealed_sbom_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("sealed SBOM is not valid JSON") from exc
    if actual_sealed != expected_sealed:
        raise ValueError("sealed SBOM is not the exact annotation of raw Syft output")
    if actual_sealed.get("documentDescribes") != [SUBJECT_ID]:
        raise ValueError("sealed SBOM does not describe the target image subject")

    if not annotation_receipt_path.is_file() or annotation_receipt_path.is_symlink():
        raise ValueError("annotation receipt must be a regular non-symlink file")
    try:
        annotation = json.loads(annotation_receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("annotation receipt is not valid JSON") from exc
    if not isinstance(annotation, dict):
        raise ValueError("annotation receipt must contain one JSON object")
    annotation_sha256 = _self_digest(annotation, "annotation receipt")
    raw_packages = raw["packages"]
    expected_annotation = {
        "schema_version": 1,
        "status": "SEALED_SYFT_SBOM_SUBJECT_BINDING",
        "target_image_id": target_image_id,
        "target_repo_digest": target_repo_digest,
        "syft_image": SYFT_IMAGE,
        "syft_version": SYFT_VERSION,
        "raw_sbom_sha256": _sha256_file(raw_sbom_path),
        "sealed_sbom_sha256": _sha256_file(sealed_sbom_path),
        "raw_package_count": len(raw_packages),
        "sealed_package_count": len(actual_sealed["packages"]),
        "raw_package_root_sha256": hashlib.sha256(_canonical(raw_packages)).hexdigest(),
        "discovered_packages_unchanged": True,
        "synthetic_subject_spdx_id": SUBJECT_ID,
    }
    if {
        key: value for key, value in annotation.items() if key != "receipt_sha256"
    } != expected_annotation:
        raise ValueError("annotation receipt schema or evidence drifted")

    if not gpu_inventory_path.is_file() or gpu_inventory_path.is_symlink():
        raise ValueError("GPU inventory must be a regular non-symlink file")
    gpu_inventory = tuple(
        line.strip()
        for line in gpu_inventory_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    if not gpu_inventory or any("H100" not in line for line in gpu_inventory):
        raise ValueError("SBOM cell did not run on an H100 allocation")

    for output in (
        publish_target_inspect_path,
        publish_syft_inspect_path,
        output_path,
    ):
        if output.exists() or output.is_symlink():
            raise ValueError(f"refusing to overwrite job evidence: {output}")
    _write_bytes_once(publish_target_inspect_path, target_encoded)
    _write_bytes_once(publish_syft_inspect_path, syft_encoded)
    unsigned = {
        "schema_version": 1,
        "status": receipt_status,
        "scientific_result": False,
        "external_attestation": False,
        "slurm": {
            "job_id": slurm_job_id,
            "job_name": slurm_job_name,
            "partition": slurm_partition,
            "cpus_per_task": slurm_cpus_per_task,
            "memory_mb": slurm_memory_mb,
            "cuda_visible_devices": cuda_visible_devices,
            "gpu_inventory": list(gpu_inventory),
        },
        "batch_sha256": expected_batch_sha256,
        "target_image_id": target_image_id,
        "target_repo_digest": target_repo_digest,
        "target_image_inspect_sha256": hashlib.sha256(target_encoded).hexdigest(),
        "syft_image": SYFT_IMAGE,
        "syft_image_id": SYFT_IMAGE_ID,
        "syft_version": SYFT_VERSION,
        "syft_image_inspect_sha256": hashlib.sha256(syft_encoded).hexdigest(),
        **archive_evidence,
        "scan_argv": ["syft", SCANNER_TARGET, "--output", "spdx-json"],
        "scan_network": "none",
        "scanner_docker_socket_mounted": False,
        "raw_sbom_sha256": _sha256_file(raw_sbom_path),
        "sealed_sbom_sha256": _sha256_file(sealed_sbom_path),
        "annotation_receipt_sha256": annotation_sha256,
    }
    receipt = {
        **unsigned,
        "receipt_sha256": hashlib.sha256(_canonical(unsigned)).hexdigest(),
    }
    _write_once(output_path, receipt)
    return receipt


def seal_job_receipt(
    *,
    target_inspect_path: Path,
    syft_inspect_path: Path,
    publish_target_inspect_path: Path,
    publish_syft_inspect_path: Path,
    target_image_id: str,
    target_repo_digest: str,
    image_archive_path: Path,
    raw_sbom_path: Path,
    sealed_sbom_path: Path,
    annotation_receipt_path: Path,
    batch_script_path: Path,
    expected_batch_sha256: str,
    gpu_inventory_path: Path,
    slurm_job_id: int,
    slurm_job_name: str,
    slurm_partition: str,
    slurm_cpus_per_task: int,
    slurm_memory_mb: int,
    cuda_visible_devices: str,
    output_path: Path,
) -> dict[str, Any]:
    """Preserve the original MemPalace-specific public contract."""

    return _seal_job_receipt(
        target_inspect_path=target_inspect_path,
        syft_inspect_path=syft_inspect_path,
        publish_target_inspect_path=publish_target_inspect_path,
        publish_syft_inspect_path=publish_syft_inspect_path,
        target_image_id=target_image_id,
        target_repo_digest=target_repo_digest,
        image_archive_path=image_archive_path,
        raw_sbom_path=raw_sbom_path,
        sealed_sbom_path=sealed_sbom_path,
        annotation_receipt_path=annotation_receipt_path,
        batch_script_path=batch_script_path,
        expected_batch_sha256=expected_batch_sha256,
        gpu_inventory_path=gpu_inventory_path,
        slurm_job_id=slurm_job_id,
        slurm_job_name=slurm_job_name,
        slurm_partition=slurm_partition,
        slurm_cpus_per_task=slurm_cpus_per_task,
        slurm_memory_mb=slurm_memory_mb,
        cuda_visible_devices=cuda_visible_devices,
        output_path=output_path,
        expected_job_name="mempalace-sbom",
        expected_cpus_per_task=8,
        expected_memory_mb=32768,
        receipt_status="SELF_ATTESTED_DISCOVERY_MEMPALACE_SBOM_JOB",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-inspect", type=Path, required=True)
    parser.add_argument("--syft-inspect", type=Path, required=True)
    parser.add_argument("--publish-target-inspect", type=Path, required=True)
    parser.add_argument("--publish-syft-inspect", type=Path, required=True)
    parser.add_argument("--target-image-id", required=True)
    parser.add_argument("--target-repo-digest", required=True)
    parser.add_argument("--image-archive", type=Path, required=True)
    parser.add_argument("--raw-sbom", type=Path, required=True)
    parser.add_argument("--sealed-sbom", type=Path, required=True)
    parser.add_argument("--annotation-receipt", type=Path, required=True)
    parser.add_argument("--batch-script", type=Path, required=True)
    parser.add_argument("--expected-batch-sha256", required=True)
    parser.add_argument("--gpu-inventory", type=Path, required=True)
    parser.add_argument("--slurm-job-id", type=int, required=True)
    parser.add_argument("--slurm-job-name", required=True)
    parser.add_argument("--slurm-partition", required=True)
    parser.add_argument("--slurm-cpus-per-task", type=int, required=True)
    parser.add_argument("--slurm-memory-mb", type=int, required=True)
    parser.add_argument("--cuda-visible-devices", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = seal_job_receipt(
            target_inspect_path=args.target_inspect,
            syft_inspect_path=args.syft_inspect,
            publish_target_inspect_path=args.publish_target_inspect,
            publish_syft_inspect_path=args.publish_syft_inspect,
            target_image_id=args.target_image_id,
            target_repo_digest=args.target_repo_digest,
            image_archive_path=args.image_archive,
            raw_sbom_path=args.raw_sbom,
            sealed_sbom_path=args.sealed_sbom,
            annotation_receipt_path=args.annotation_receipt,
            batch_script_path=args.batch_script,
            expected_batch_sha256=args.expected_batch_sha256,
            gpu_inventory_path=args.gpu_inventory,
            slurm_job_id=args.slurm_job_id,
            slurm_job_name=args.slurm_job_name,
            slurm_partition=args.slurm_partition,
            slurm_cpus_per_task=args.slurm_cpus_per_task,
            slurm_memory_mb=args.slurm_memory_mb,
            cuda_visible_devices=args.cuda_visible_devices,
            output_path=args.output,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
