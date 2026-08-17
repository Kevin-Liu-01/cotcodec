#!/usr/bin/env python3
"""Seal and validate the retained LangMem/PostgreSQL lifecycle negative."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "data/results/langmem-native-lifecycle/2026-08-17-local-docker-v1"
DEFAULT_OUTPUT = PROJECT_ROOT / "research/evidence/memory/langmem-native-lifecycle-negative-v1.json"
STATUS = "BLOCKED_NO_FIRST_CLASS_SCOPED_PURGE_AND_POSTGRES_PLAINTEXT_RESIDUE"
REVISION = "29cbe41e58528f92e9efa773c12e15c47be3808c"
TREE = "d85d1f815fb2b54bbc0a85c18453b7a7953ca38c"
SOURCE_ARCHIVE = "24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521"
IMAGE_ID = "sha256:2571173b00e1774bb3d4a0ac3f8f945d6b6d044840cf6951e35d77fc0c08520f"
PROJECTION_SHA256 = "96602010adaf5b90c706c9be759d4790464ccd7a2ee4eea302011ce76cbdac61"
CLAIM_BOUNDARY = (
    "Exact pinned LangMem public tool, deterministic background-manager transport, "
    "official PostgresStore lifecycle, logical deletion, namespace-purge surface, "
    "and physical plaintext residue; not extraction quality, semantic retrieval, "
    "procedural prompt quality, model effect, managed LangGraph service behavior, "
    "H100 actor quality, or publication evidence."
)
ARTIFACTS = {
    "Dockerfile.lifecycle-doctor",
    "experiment.yaml",
    "image-inspect.json",
    "lifecycle_doctor.py",
    "manifest.json",
    "repeat-1-prepare.txt",
    "repeat-1-purge.txt",
    "repeat-1-restart.txt",
    "repeat-1.json",
    "repeat-2-prepare.txt",
    "repeat-2-purge.txt",
    "repeat-2-restart.txt",
    "repeat-2.json",
    "report.json",
    "source-receipt.json",
}
CODE_PATHS = {
    "experiments/memory/stage3-langmem-native-lifecycle-doctor.yaml",
    "infra/memory-baselines/langmem/Dockerfile.lifecycle-doctor",
    "infra/memory-baselines/langmem/lifecycle_doctor.py",
    "pyproject.toml",
    "scripts/run_langmem_lifecycle_doctor.py",
    "scripts/seal_langmem_native_lifecycle_evidence.py",
    "uv.lock",
}
FINDINGS = {
    "database_and_fresh_process_restart_passed": True,
    "enumerate_then_delete_logical_fallback_passed": True,
    "exact_source_background_manager_transport_executed": True,
    "first_class_namespace_purge_absent": True,
    "hot_path_public_tool_crud_passed": True,
    "logical_record_delete_passed": True,
    "purged_plaintext_remains_in_postgresql_heap": True,
    "purged_plaintext_remains_in_postgresql_wal": True,
    "user_namespace_isolation_passed": True,
}
PROJECTION = {
    "prepare": {
        "background_manager_persisted_deterministic_extraction": True,
        "hot_path_create_update_uses_public_tool": True,
        "phase": "prepare",
        "user_namespace_isolation": True,
    },
    "purge": {
        "deleted_records": 2,
        "enumerate_then_delete_logically_clears_scopes": True,
        "first_class_namespace_purge_available": False,
        "phase": "purge",
    },
    "residue": {
        "all_four_canaries_have_bounded_proof_windows": True,
        "plaintext_residue_after_logical_purge_and_clean_shutdown": True,
        "plaintext_residue_in_postgresql_heap": True,
        "plaintext_residue_in_postgresql_wal": True,
    },
    "restart": {
        "database_and_fresh_process_restart_preserve_acknowledged_state": True,
        "phase": "restart",
        "public_tool_logical_delete_succeeds": True,
    },
}


class LangMemEvidenceError(ValueError):
    """Raised when retained LangMem evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise LangMemEvidenceError(f"{owner}: non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LangMemEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise LangMemEvidenceError(f"{owner}: expected object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise LangMemEvidenceError(f"expected regular artifact: {path}")
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": _sha(data),
        "content_base64": base64.b64encode(data).decode(),
    }


def _decode(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != ARTIFACTS:
        raise LangMemEvidenceError("LangMem artifact roster drifted")
    files: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise LangMemEvidenceError(f"invalid artifact receipt: {name}")
        try:
            data = base64.b64decode(receipt.get("content_base64", ""), validate=True)
        except (TypeError, ValueError) as exc:
            raise LangMemEvidenceError(f"invalid artifact base64: {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise LangMemEvidenceError(f"artifact receipt drifted: {name}")
        files[name] = data
    return files


def _validate_manifest(files: dict[str, bytes]) -> None:
    manifest = _object(files["manifest.json"], "manifest")
    expected = {name: _sha(data) for name, data in files.items() if name != "manifest.json"}
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != STATUS
        or manifest.get("files") != expected
    ):
        raise LangMemEvidenceError("artifact manifest drifted")


def _validate_source_and_image(files: dict[str, bytes]) -> None:
    source = _object(files["source-receipt.json"], "source receipt")
    context = source.get("context_receipt")
    if (
        source.get("revision") != REVISION
        or source.get("tree") != TREE
        or source.get("archive_sha256") != SOURCE_ARCHIVE
        or source.get("license_sha256")
        != "98af1351ea856e008c835bc89a312905960a318072f950732bf346c741027c7d"
        or source.get("source_checks")
        != {
            "background_manager_applies_record_puts_and_deletes": True,
            "public_manage_tool_has_record_delete_only": True,
        }
        or not isinstance(context, dict)
        or context.get("system_id") != "langmem"
        or context.get("revision") != REVISION
        or context.get("source_tree_sha") != TREE
        or context.get("source_archive_sha256") != SOURCE_ARCHIVE
    ):
        raise LangMemEvidenceError("source provenance drifted")
    try:
        rows = json.loads(files["image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LangMemEvidenceError("image inspection is invalid") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise LangMemEvidenceError("image inspection roster drifted")
    image = rows[0]
    config = image.get("Config") or {}
    labels = config.get("Labels") or {}
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or labels.get("org.opencontainers.image.revision") != REVISION
        or labels.get("org.cotcodec.source-tree") != TREE
        or labels.get("org.cotcodec.source-archive-sha256") != SOURCE_ARCHIVE
        or labels.get("org.cotcodec.lifecycle-doctor-sha256") != _sha(files["lifecycle_doctor.py"])
        or labels.get("org.cotcodec.lifecycle-experiment-sha256") != _sha(files["experiment.yaml"])
        or labels.get("org.cotcodec.discovery-only") != "true"
    ):
        raise LangMemEvidenceError("image provenance drifted")


def _validate_proofs(repeat: dict[str, Any], index: int) -> None:
    proofs = repeat.get("proofs")
    expected_paths = {
        "pgdata/base/16384/16390",
        "pgdata/pg_wal/000000010000000000000001",
    }
    if not isinstance(proofs, dict) or set(proofs) != expected_paths:
        raise LangMemEvidenceError(f"repeat {index}: residue path roster drifted")
    expected_labels = {"original", "updated", "isolated", "background"}
    observed: dict[str, int] = {label: 0 for label in expected_labels}
    for path, hits in proofs.items():
        if not isinstance(hits, list) or len(hits) != 4:
            raise LangMemEvidenceError(f"repeat {index}: proof count drifted for {path}")
        for hit in hits:
            if not isinstance(hit, dict) or hit.get("canary") not in expected_labels:
                raise LangMemEvidenceError(f"repeat {index}: proof identity drifted")
            try:
                window = base64.b64decode(hit.get("window_base64", ""), validate=True)
            except (TypeError, ValueError) as exc:
                raise LangMemEvidenceError(f"repeat {index}: invalid proof window") from exc
            label = hit["canary"]
            pattern = rb"LANGMEM_" + label.upper().encode() + rb"_[0-9a-f]{32}"
            matches = re.findall(pattern, window)
            if (
                len(matches) != 1
                or _sha(matches[0]) != hit.get("needle_sha256")
                or _sha(window) != hit.get("window_sha256")
                or not isinstance(hit.get("offset"), int)
                or not isinstance(hit.get("window_start"), int)
            ):
                raise LangMemEvidenceError(f"repeat {index}: proof window drifted")
            observed[label] += 1
    if observed != {label: 2 for label in expected_labels}:
        raise LangMemEvidenceError(f"repeat {index}: canary coverage drifted")


def _validate_runs(files: dict[str, bytes]) -> None:
    runs = [_object(files[f"repeat-{index}.json"], f"repeat {index}") for index in (1, 2)]
    for index, repeat in enumerate(runs, 1):
        if (
            repeat.get("repeat") != index
            or repeat.get("projection") != PROJECTION
            or repeat.get("projection_sha256") != PROJECTION_SHA256
            or _sha(json.dumps(PROJECTION, separators=(",", ":"), sort_keys=True).encode())
            != PROJECTION_SHA256
        ):
            raise LangMemEvidenceError(f"repeat {index}: projection drifted")
        security = repeat.get("security")
        if (
            not isinstance(security, dict)
            or security.get("network_internal") is not True
            or security.get("app_read_only_nonroot_cap_drop_all") is not True
            or security.get("database_read_only_rootfs_uid_70_cap_drop_all") is not True
        ):
            raise LangMemEvidenceError(f"repeat {index}: confinement receipt drifted")
        _validate_proofs(repeat, index)
    report = _object(files["report.json"], "report")
    if (
        report.get("schema_version") != 1
        or report.get("status") != STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("run_count") != 2
        or report.get("fresh_database_restart_count_per_run") != 1
        or report.get("stable_projection_sha256") != PROJECTION_SHA256
        or report.get("findings") != FINDINGS
        or report.get("claim_boundary") != CLAIM_BOUNDARY
    ):
        raise LangMemEvidenceError("summary semantics drifted")


def validate_langmem_native_lifecycle_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "LangMem evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise LangMemEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "langmem"
        or bundle.get("source_revisions") != {"https://github.com/langchain-ai/langmem": REVISION}
        or bundle.get("evidence_kind") != "contained-native-postgres-lifecycle-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "local-arm64-docker-internal-bridge"
        or bundle.get("run_count") != 2
        or bundle.get("fresh_database_restart_count_per_run") != 1
        or bundle.get("stable_projection_sha256") != PROJECTION_SHA256
        or bundle.get("h100_actor_admission") != "forbidden-for-this-revision"
        or bundle.get("findings") != FINDINGS
        or bundle.get("claim_boundary") != CLAIM_BOUNDARY
    ):
        raise LangMemEvidenceError("LangMem evidence identity drifted")
    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or set(code_files) != CODE_PATHS:
        raise LangMemEvidenceError("LangMem code receipt roster drifted")
    for name, expected in code_files.items():
        path = root / name
        if (
            not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
            or not path.is_file()
            or path.is_symlink()
            or _sha(path.read_bytes()) != expected
        ):
            raise LangMemEvidenceError(f"LangMem code receipt drifted: {name}")
    files = _decode(bundle.get("files"))
    _validate_manifest(files)
    _validate_source_and_image(files)
    _validate_runs(files)
    return bundle


def seal(root: Path, output: Path) -> dict[str, Any]:
    if not root.is_dir() or root.is_symlink():
        raise LangMemEvidenceError("LangMem evidence input root is invalid")
    observed = {path.name for path in root.iterdir() if path.is_file()}
    if observed != ARTIFACTS:
        raise LangMemEvidenceError("LangMem input artifact roster drifted")
    bundle = {
        "schema_version": 1,
        "source_id": "langmem",
        "source_revisions": {"https://github.com/langchain-ai/langmem": REVISION},
        "evidence_kind": "contained-native-postgres-lifecycle-negative",
        "evidence_grade": "local-negative-reproduced",
        "status": STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-arm64-docker-internal-bridge",
        "run_count": 2,
        "fresh_database_restart_count_per_run": 1,
        "stable_projection_sha256": PROJECTION_SHA256,
        "h100_actor_admission": "forbidden-for-this-revision",
        "findings": FINDINGS,
        "claim_boundary": CLAIM_BOUNDARY,
        "code_files": {
            name: _sha((PROJECT_ROOT / name).read_bytes()) for name in sorted(CODE_PATHS)
        },
        "files": {name: _capture(root / name) for name in sorted(ARTIFACTS)},
    }
    validate_langmem_native_lifecycle_evidence(bundle, project_root=PROJECT_ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(bundle, indent=2, sort_keys=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(output, flags, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    validate_langmem_native_lifecycle_evidence(output, project_root=PROJECT_ROOT)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    seal(args.root, args.output)
    print(f"LangMem native lifecycle evidence PASS: {_sha(args.output.read_bytes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
