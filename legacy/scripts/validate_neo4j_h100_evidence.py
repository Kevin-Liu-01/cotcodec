#!/usr/bin/env python3
"""Validate the sealed Neo4j amd64 lifecycle confirmation from Slurm job 303."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

EXPECTED_SOURCE_SHA256 = (
    "723d7a653a3c1eebf35d8dacf55a032edd55a93a30dd88c95d79324f4dfc0499"
)
EXPECTED_SOURCE_RECEIPT_SHA256 = (
    "793fb5f91991d5f9b0a9f77584727bd9183ebac186927708b57e132f5dddb3e2"
)
EXPECTED_SOURCE_GIT_SHA = "581ded8df71564b0212d8af5dcd401257aa6a28f"
EXPECTED_SOURCE_GIT_TREE = "5a83330044fda59e998e09c18266ad6f99a84bce"
EXPECTED_BATCH_SHA256 = (
    "49698b006d2aa751fde42b9c689b09cad95e100083581da9db1f4a99023624c4"
)
EXPECTED_EXTRACTOR_SHA256 = (
    "ee565dbfb50f85c287e25d056b39b4f0d4a8cf36ec844810cdca108f03ea7359"
)
EXPECTED_INPUT_IMAGE_SHA256 = (
    "42f0b87c8c5ff2ca52757b16d8f75a8fc155d599b4624faeaf387cd64db12622"
)
EXPECTED_OCI_MANIFEST_DIGEST = (
    "sha256:59a02e177a32eed32ca4faf015fe91e17d936b9ef2e4cd94fce53268162ea0cb"
)
EXPECTED_CLUSTER_OCI_MANIFEST_DIGEST = (
    "sha256:86334d8a42e969b6ff9e9ea748881d23c4a390f46674a33df428752937672534"
)
EXPECTED_IMAGE_CONFIG_DIGEST = (
    "sha256:8ec19ef4a4acbbf81205e56148aadfa5e9798d2964175b5b4be8d8644436c382"
)
EXPECTED_NEO4J_IMAGE = (
    "neo4j:5.26.29-community@"
    "sha256:865213f53381e8d2ef3eec08b11741a6722d388a5e70b134135186a9b5cb27a6"
)
EXPECTED_NEO4J_IMAGE_ID = (
    "sha256:19dfa5a7e5c40fc28a7486616deeb21caac9a6a6350e1a34665392b65b6e1c59"
)
EXPECTED_ARTIFACT_ROOT = (
    "data/results/neo4j-preference-lifecycle/2026-08-15-h100-job303-v1"
)
EXPECTED_ARTIFACT_ROSTER = {
    "client-image-303.tar",
    "client-image-inspect-303.json",
    "gpu-inventory-303.txt",
    "job-303.receipt.json",
    "lifecycle-303.stdout.json",
    "lifecycle-303/experiment.yaml",
    "lifecycle-303/manifest.json",
    "lifecycle-303/report.json",
    "neo4j-image-inspect-303.json",
    "sbom-303/client.spdx.json",
    "slurm-298.out",
    "slurm-299.out",
    "slurm-300.out",
    "slurm-301.out",
    "slurm-302.out",
    "slurm-303.out",
    "submitted-job-id-v3.txt",
}
EXPECTED_PROJECTION = {
    "active_count": 1,
    "history_count": 2,
    "model_calls": 0,
    "node_semantics": [
        [
            "cotcodec-neo4j-a",
            "consultants",
            "Prefer junior consultants",
            True,
        ],
        [
            "cotcodec-neo4j-a",
            "consultants",
            "Prefer senior consultants",
            False,
        ],
        ["cotcodec-neo4j-b", "format", "Prefer concise output", False],
    ],
    "past_count": 1,
    "purge_edges": 0,
    "purge_nodes": 0,
    "restart_hash_preserved": True,
    "supersession_edge_count": 1,
}


class Neo4jH100EvidenceError(ValueError):
    """Raised when the Neo4j H100 confirmation evidence drifts."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _strict_json(data: bytes, *, owner: str) -> Any:
    def reject_constant(value: str) -> None:
        raise Neo4jH100EvidenceError(f"{owner}: non-finite constant {value}")

    try:
        return json.loads(data, parse_constant=reject_constant)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Neo4jH100EvidenceError(f"{owner}: invalid JSON") from exc


def _object(data: bytes, *, owner: str) -> dict[str, Any]:
    value = _strict_json(data, owner=owner)
    if not isinstance(value, dict):
        raise Neo4jH100EvidenceError(f"{owner}: expected one JSON object")
    return value


def _safe_file(project_root: Path, value: Any, *, owner: str) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise Neo4jH100EvidenceError(f"{owner}: unsafe path")
    path = project_root / value
    if not path.is_file() or path.is_symlink():
        raise Neo4jH100EvidenceError(f"{owner}: missing or non-regular file")
    return path


def _load_artifacts(bundle: dict[str, Any], project_root: Path) -> dict[str, bytes]:
    if bundle.get("artifact_root") != EXPECTED_ARTIFACT_ROOT:
        raise Neo4jH100EvidenceError("artifact root drifted")
    receipts = bundle.get("artifact_files")
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ARTIFACT_ROSTER:
        raise Neo4jH100EvidenceError("artifact roster drifted")
    root = project_root / EXPECTED_ARTIFACT_ROOT
    files: dict[str, bytes] = {}
    for name, expected in receipts.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or not path.is_file()
            or path.is_symlink()
        ):
            raise Neo4jH100EvidenceError(f"artifact {name} is invalid")
        data = path.read_bytes()
        if _sha256(data) != expected:
            raise Neo4jH100EvidenceError(f"artifact {name} drifted")
        files[name] = data
    return files


def _tar_member(archive: tarfile.TarFile, name: str, *, owner: str) -> bytes:
    try:
        member = archive.getmember(name)
    except KeyError as exc:
        raise Neo4jH100EvidenceError(f"{owner}: missing {name}") from exc
    if not member.isfile() or Path(name).is_absolute() or ".." in Path(name).parts:
        raise Neo4jH100EvidenceError(f"{owner}: unsafe member {name}")
    extracted = archive.extractfile(member)
    if extracted is None:
        raise Neo4jH100EvidenceError(f"{owner}: unreadable member {name}")
    return extracted.read()


def _validate_source(bundle: dict[str, Any], project_root: Path) -> None:
    archive_path = _safe_file(
        project_root, bundle.get("source_archive_path"), owner="source archive"
    )
    receipt_path = _safe_file(
        project_root, bundle.get("source_receipt_path"), owner="source receipt"
    )
    archive_bytes = archive_path.read_bytes()
    receipt_bytes = receipt_path.read_bytes()
    if (
        _sha256(archive_bytes) != EXPECTED_SOURCE_SHA256
        or _sha256(receipt_bytes) != EXPECTED_SOURCE_RECEIPT_SHA256
    ):
        raise Neo4jH100EvidenceError("source archive or receipt drifted")
    receipt = _object(receipt_bytes, owner="source receipt")
    if (
        receipt.get("schema_version") != 2
        or receipt.get("mode") != "discovery"
        or receipt.get("worktree_clean") is not False
        or receipt.get("archive_sha256") != EXPECTED_SOURCE_SHA256
        or receipt.get("git_sha") != EXPECTED_SOURCE_GIT_SHA
        or receipt.get("git_tree") != EXPECTED_SOURCE_GIT_TREE
    ):
        raise Neo4jH100EvidenceError("source receipt semantics drifted")
    try:
        normalized_tar = gzip.decompress(archive_bytes)
    except gzip.BadGzipFile as exc:
        raise Neo4jH100EvidenceError("source archive is not gzip") from exc
    with tarfile.open(fileobj=io.BytesIO(normalized_tar), mode="r:") as archive:
        batch = _tar_member(
            archive,
            "infra/slurm/host-single-node/neo4j-preference-lifecycle.sbatch",
            owner="source archive",
        )
        extractor = _tar_member(
            archive,
            "scripts/extract_discovery_source_archive.py",
            owner="source archive",
        )
        runner = _tar_member(
            archive,
            "scripts/run_neo4j_preference_lifecycle_doctor.py",
            owner="source archive",
        )
    if (
        _sha256(batch) != EXPECTED_BATCH_SHA256
        or _sha256(extractor) != EXPECTED_EXTRACTOR_SHA256
        or b'--prebuilt-client-image "$client_image"' not in batch
        or b'--expected-client-image-id "$expected_client_image_id"' not in batch
        or b"#SBATCH --gres=gpu:h100:1" not in batch
        or b"--gpus" in batch
        or b"prebuilt_client_image" not in runner
    ):
        raise Neo4jH100EvidenceError("archived batch, extractor, or runner drifted")


def _validate_image_archive(
    data: bytes,
    *,
    expected_sha256: str,
    expected_manifest_digest: str,
    owner: str,
) -> None:
    if _sha256(data) != expected_sha256:
        raise Neo4jH100EvidenceError(f"{owner}: archive digest drifted")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        manifest = _strict_json(
            _tar_member(archive, "manifest.json", owner=owner), owner=f"{owner} manifest"
        )
        index = _object(
            _tar_member(archive, "index.json", owner=owner), owner=f"{owner} index"
        )
        if not isinstance(manifest, list) or len(manifest) != 1:
            raise Neo4jH100EvidenceError(f"{owner}: manifest roster drifted")
        row = manifest[0]
        manifests = index.get("manifests")
        if not isinstance(row, dict) or not isinstance(manifests, list) or len(manifests) != 1:
            raise Neo4jH100EvidenceError(f"{owner}: OCI roster drifted")
        config_name = EXPECTED_IMAGE_CONFIG_DIGEST.removeprefix("sha256:")
        manifest_name = expected_manifest_digest.removeprefix("sha256:")
        if (
            row.get("Config") != f"blobs/sha256/{config_name}"
            or manifests[0].get("digest") != expected_manifest_digest
        ):
            raise Neo4jH100EvidenceError(f"{owner}: image identity drifted")
        oci_manifest = _object(
            _tar_member(archive, f"blobs/sha256/{manifest_name}", owner=owner),
            owner=f"{owner} OCI manifest",
        )
        config_bytes = _tar_member(
            archive, f"blobs/sha256/{config_name}", owner=owner
        )
    if (
        _sha256(config_bytes) != config_name
        or oci_manifest.get("config", {}).get("digest")
        != EXPECTED_IMAGE_CONFIG_DIGEST
    ):
        raise Neo4jH100EvidenceError(f"{owner}: config binding drifted")
    config = _object(config_bytes, owner=f"{owner} config")
    if config.get("architecture") != "amd64" or config.get("os") != "linux":
        raise Neo4jH100EvidenceError(f"{owner}: platform drifted")


def _validate_report(files: dict[str, bytes]) -> None:
    report = _object(files["lifecycle-303/report.json"], owner="Neo4j report")
    runtime = report.get("runtime")
    if (
        report.get("status") != "NEO4J_PREFERENCE_LIFECYCLE_CONFORMANCE_PASS"
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("runtime_lane") != "cluster-amd64-slurm"
        or report.get("confirmation_required") is not False
        or report.get("gpu_hours") != 0
        or report.get("semantic_projection") != EXPECTED_PROJECTION
        or not isinstance(runtime, dict)
        or runtime.get("client_image_id") != EXPECTED_IMAGE_CONFIG_DIGEST
        or runtime.get("client_image_source") != "prebuilt-verified"
        or runtime.get("neo4j_image_id") != EXPECTED_NEO4J_IMAGE_ID
        or runtime.get("platform") != "linux/amd64"
        or runtime.get("network") != "private-internal-only"
        or runtime.get("sudo_used") is not False
    ):
        raise Neo4jH100EvidenceError("Neo4j report identity drifted")
    repeats = report.get("repeats")
    if not isinstance(repeats, list) or [row.get("repeat") for row in repeats] != [1, 2]:
        raise Neo4jH100EvidenceError("Neo4j repeat roster drifted")
    state_roots: set[str] = set()
    for repeat in repeats:
        if not isinstance(repeat, dict) or repeat.get("semantic_projection") != EXPECTED_PROJECTION:
            raise Neo4jH100EvidenceError("Neo4j repeat projection drifted")
        establish = repeat.get("establish")
        verify = repeat.get("verify_purge")
        empty = repeat.get("verify_empty")
        if not all(isinstance(row, dict) for row in (establish, verify, empty)):
            raise Neo4jH100EvidenceError("Neo4j phase receipt is missing")
        state = establish.get("state")
        if (
            not isinstance(state, dict)
            or verify.get("state_sha256") != state.get("state_sha256")
            or empty.get("nodes") != 0
            or empty.get("edges") != 0
            or any(row.get("model_calls") != 0 for row in (establish, verify, empty))
        ):
            raise Neo4jH100EvidenceError("restart, purge, or model-call gate drifted")
        state_roots.add(state["state_sha256"])
    if len(state_roots) != 2:
        raise Neo4jH100EvidenceError("clean repeats need distinct execution roots")

    manifest = _object(files["lifecycle-303/manifest.json"], owner="manifest")
    root = manifest.get("manifest_sha256")
    unhashed = dict(manifest)
    unhashed.pop("manifest_sha256", None)
    artifacts = manifest.get("artifacts")
    if (
        root != _sha256(_canonical_bytes(unhashed))
        or not isinstance(artifacts, dict)
        or set(artifacts) != {"experiment.yaml", "report.json"}
    ):
        raise Neo4jH100EvidenceError("output manifest drifted")
    for name in artifacts:
        qualified = f"lifecycle-303/{name}"
        if artifacts[name] != {
            "bytes": len(files[qualified]),
            "sha256": _sha256(files[qualified]),
        }:
            raise Neo4jH100EvidenceError("output manifest content drifted")


def _validate_runtime(bundle: dict[str, Any], files: dict[str, bytes]) -> None:
    receipt = _object(files["job-303.receipt.json"], owner="job receipt")
    bindings = {
        "client_image_inspect_sha256": "client-image-inspect-303.json",
        "client_sbom_sha256": "sbom-303/client.spdx.json",
        "gpu_inventory_sha256": "gpu-inventory-303.txt",
        "manifest_sha256": "lifecycle-303/manifest.json",
        "neo4j_image_inspect_sha256": "neo4j-image-inspect-303.json",
        "report_sha256": "lifecycle-303/report.json",
    }
    if any(receipt.get(key) != _sha256(files[name]) for key, name in bindings.items()):
        raise Neo4jH100EvidenceError("job artifact binding drifted")
    if (
        receipt.get("schema_version") != 1
        or receipt.get("slurm_job_id") != 303
        or receipt.get("slurm_job_name") != "cotcodec-neo4j-preference-lifecycle"
        or receipt.get("batch_sha256") != EXPECTED_BATCH_SHA256
        or receipt.get("client_image_id") != EXPECTED_IMAGE_CONFIG_DIGEST
        or receipt.get("neo4j_image") != EXPECTED_NEO4J_IMAGE
        or receipt.get("neo4j_image_id") != EXPECTED_NEO4J_IMAGE_ID
        or receipt.get("client_image_archive_sha256")
        != bundle.get("cluster_resaved_image_sha256")
        or files["submitted-job-id-v3.txt"] != b"303\n"
    ):
        raise Neo4jH100EvidenceError("job identity drifted")

    inventory = files["gpu-inventory-303.txt"].decode("utf-8").splitlines()
    if len(inventory) != 1 or "H100" not in inventory[0]:
        raise Neo4jH100EvidenceError("H100 allocation receipt drifted")
    sbom = _object(files["sbom-303/client.spdx.json"], owner="client SBOM")
    creators = sbom.get("creationInfo", {}).get("creators")
    packages = sbom.get("packages")
    if (
        sbom.get("spdxVersion") != "SPDX-2.3"
        or not isinstance(creators, list)
        or "Tool: syft-1.51.0" not in creators
        or not isinstance(packages, list)
        or len(packages) < 100
    ):
        raise Neo4jH100EvidenceError("client SBOM contract drifted")

    attempts = bundle.get("preflight_attempts")
    expected_attempts = [
        {"job_id": 298, "terminal_reason": "configured-python-unavailable"},
        {"job_id": 299, "terminal_reason": "operator-cancelled-prematurely"},
        {"job_id": 300, "terminal_reason": "docker-build-dns-failure"},
        {"job_id": 301, "terminal_reason": "docker-image-identity-convention"},
        {"job_id": 302, "terminal_reason": "redundant-docker-build-dns-failure"},
    ]
    logs = {job: files[f"slurm-{job}.out"] for job in range(298, 304)}
    if (
        attempts != expected_attempts
        or b"configured Python is unavailable" not in logs[298]
        or b"CANCELLED" not in logs[299]
        or b"dns error" not in logs[300]
        or b"prebuilt client image identity drifted" not in logs[301]
        or b"dns error" not in logs[302]
        or b"VALIDATED_DISCOVERY_SOURCE" not in logs[303]
        or b"ERROR" in logs[303]
    ):
        raise Neo4jH100EvidenceError("preflight/final Slurm history drifted")


def validate_neo4j_h100_evidence(
    bundle: dict[str, Any], *, project_root: Path
) -> dict[str, Any]:
    """Validate the complete cluster confirmation and return stable semantics."""

    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "neo4j-agent-memory"
        or bundle.get("evidence_kind") != "cluster-amd64-lifecycle-confirmation"
        or bundle.get("evidence_grade") != "local-conformance-reproduced"
        or bundle.get("status") != "NEO4J_PREFERENCE_LIFECYCLE_CONFORMANCE_PASS"
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane")
        != "docker-under-slurm-h100-allocation-no-container-gpu"
        or bundle.get("slurm_job_id") != 303
        or bundle.get("h100_allocation_count") != 1
        or bundle.get("container_gpu_count") != 0
        or bundle.get("scheduler_accounting") != "sacct-disabled-on-host"
        or bundle.get("source_revisions")
        != {
            "https://github.com/neo4j-labs/agent-memory": (
                "231d60eac9401ab156ba194b519d89dd644dadb8"
            )
        }
        or bundle.get("claim_boundary")
        != {
            "graph_efficacy_evaluated": False,
            "h100_actor_admission": "blocked-pending-identical-tuple-flat-parity",
            "native_lifecycle_confirmed": True,
            "publication_claim": False,
        }
    ):
        raise Neo4jH100EvidenceError("top-level evidence contract drifted")
    files = _load_artifacts(bundle, project_root)
    _validate_source(bundle, project_root)
    image_path = _safe_file(
        project_root,
        bundle.get("input_client_image_archive_path"),
        owner="input client image archive",
    )
    _validate_image_archive(
        image_path.read_bytes(),
        expected_sha256=EXPECTED_INPUT_IMAGE_SHA256,
        expected_manifest_digest=EXPECTED_OCI_MANIFEST_DIGEST,
        owner="input client image",
    )
    _validate_image_archive(
        files["client-image-303.tar"],
        expected_sha256=bundle.get("cluster_resaved_image_sha256"),
        expected_manifest_digest=EXPECTED_CLUSTER_OCI_MANIFEST_DIGEST,
        owner="cluster-resaved client image",
    )
    if (
        bundle.get("input_client_image_sha256") != EXPECTED_INPUT_IMAGE_SHA256
        or bundle.get("oci_manifest_digest") != EXPECTED_OCI_MANIFEST_DIGEST
        or bundle.get("cluster_resaved_oci_manifest_digest")
        != EXPECTED_CLUSTER_OCI_MANIFEST_DIGEST
        or bundle.get("image_config_digest") != EXPECTED_IMAGE_CONFIG_DIGEST
    ):
        raise Neo4jH100EvidenceError("input image receipt drifted")
    _validate_report(files)
    _validate_runtime(bundle, files)
    return {
        "client_image_id": EXPECTED_IMAGE_CONFIG_DIGEST,
        "job_id": 303,
        "semantic_projection": EXPECTED_PROJECTION,
    }
