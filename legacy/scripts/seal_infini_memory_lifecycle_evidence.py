#!/usr/bin/env python3
"""Seal and validate Infini Memory's exact-source lifecycle negative."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_infini_memory_lifecycle_experiment import (  # noqa: E402
    EXPECTED_STATUS,
    validate_experiment_contract,
)

DEFAULT_ROOT = (
    PROJECT_ROOT / "data/results/infini-memory-lifecycle/2026-08-26-local-docker-v1"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/memory/infini-memory-lifecycle-negative-v1.json"
)
REVISION = "ddac08ec468e0382e4f14239d94991ab19ae981a"
TREE = "6cb81be142780eaf7cce36bcd8a64e20ca582042"
ARCHIVE_SHA256 = "9da66f63e1c60230d74c2da320fa711c1afe759bbd28058032c8fc78b51bb506"
ARCHIVE_BYTES = 10536960
IMAGE_ID = "sha256:3ea8425e290ab28cd322a0baff102e40643722dff4a6bff96ea4a9a6610f19f6"
STABLE_PROJECTION_SHA256 = (
    "a431ee72891d0d107360b34f62108174cf0d05fa3bd2749aa0d5414db6ca9027"
)
REPORT_SHA256 = "b18bb5eccb9500de18ec24f98a217d5bc8ebc235d46a378e3c4073daa5c74cd5"
MANIFEST_SHA256 = "38b7e55d3750eab2be85d29c99b9aa0a26619f479f1f4de94c19c71b3b521fc2"
CLAIM_BOUNDARY = (
    "Exact pinned Infini Memory public add/search/CRUD/user lifecycle, deterministic "
    "LLM rewrite accounting, BM25 and direct-Markdown diagnostics, fresh-process "
    "restart, user-path and recursive-delete confinement, injected Markdown/index "
    "interruption, truncated-index handling, and bounded retained-current-file "
    "plaintext scans; not extraction quality, topic-rewrite quality, semantic "
    "retrieval quality, secure filesystem erasure, sustained throughput, concurrent "
    "multi-process correctness, H100 actor quality, or publication evidence."
)
ARTIFACT_NAMES = {
    "Dockerfile",
    "docker-build.txt",
    "doctor-image-inspect.json",
    "doctor.py",
    "experiment.yaml",
    "manifest.json",
    "pip-freeze.txt",
    "repeat-1-phase-1.txt",
    "repeat-1-phase-2.txt",
    "repeat-1-phase-3.txt",
    "repeat-1-phase-4.txt",
    "repeat-1.json",
    "repeat-2-phase-1.txt",
    "repeat-2-phase-2.txt",
    "repeat-2-phase-3.txt",
    "repeat-2-phase-4.txt",
    "repeat-2.json",
    "report.json",
    "source-receipt.json",
}
MANIFEST_FILE_NAMES = (ARTIFACT_NAMES - {"manifest.json"}) | {"source.tar"}
CODE_PATHS = {
    "experiments/memory/stage3-infini-memory-lifecycle-provenance-doctor.yaml",
    "infra/memory-baselines/infini-memory/Dockerfile",
    "infra/memory-baselines/infini-memory/doctor.py",
    "scripts/run_infini_memory_lifecycle_doctor.py",
    "scripts/seal_infini_memory_lifecycle_evidence.py",
    "scripts/validate_infini_memory_lifecycle_experiment.py",
}
PHASE_CHECKS = [
    {
        "absolute_user_id_overrides_data_root",
        "alias_equivalent_user_ids_share_storage",
        "escaped_delete_target_created_outside_data_root",
        "fault_fixtures_created",
        "public_add_and_get_complete",
        "relative_user_id_escapes_data_root",
    },
    {
        "escaped_delete_user_removes_path_outside_data_root",
        "interrupted_delete_exception_observed",
        "interrupted_update_exception_observed",
        "normal_document_delete_completed",
        "normal_user_delete_completed",
        "normal_user_survives_first_restart",
        "public_bm25_search_finds_normal_user",
        "public_update_completed",
        "truncated_index_written_with_markdown_present",
    },
    {
        "interrupted_delete_exposes_dangling_index_entry",
        "interrupted_update_exposes_markdown_index_mismatch",
        "normal_crud_survives_second_restart",
        "normal_document_delete_survives_restart",
        "normal_user_delete_survives_restart",
        "post_delete_current_file_plaintext_scan_completed",
        "post_delete_plaintext_residue_not_observed",
        "rewrite_and_retrieval_accounting_completed",
        "truncated_index_silently_loads_empty_with_markdown_present",
    },
    {
        "absolute_escape_artifact_survives_restart",
        "alias_collision_artifact_survives_restart",
        "dangling_index_entry_survives_third_restart",
        "interrupted_update_mismatch_survives_third_restart",
        "relative_escape_artifact_survives_restart",
        "truncated_index_empty_view_survives_third_restart",
    },
]
STATIC_FINDINGS = {
    "delete_unlinks_markdown_before_index",
    "invalid_index_silently_loads_empty",
    "manager_joins_unvalidated_user_id",
    "recursive_user_delete_joins_unvalidated_user_id",
    "update_writes_markdown_before_index",
}
EXPECTED_FINDINGS = set().union(*PHASE_CHECKS, STATIC_FINDINGS)
DIRECT_REQUIREMENTS = {
    "langchain==1.2.0",
    "langfuse==3.11.1",
    "numpy==2.4.1",
    "openai==2.14.0",
    "pydantic==2.12.5",
}


class InfiniMemoryLifecycleEvidenceError(ValueError):
    """Raised when retained Infini Memory evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise InfiniMemoryLifecycleEvidenceError(
            f"{owner} contains non-finite JSON {value}"
        )

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InfiniMemoryLifecycleEvidenceError(f"{owner} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise InfiniMemoryLifecycleEvidenceError(f"{owner} must be an object")
    return payload


def _capture(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise InfiniMemoryLifecycleEvidenceError(
            f"expected regular evidence input: {path}"
        )
    raw = path.read_bytes()
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    return {
        "compression": "gzip-mtime-0",
        "raw_size": len(raw),
        "raw_sha256": _sha(raw),
        "compressed_size": len(compressed),
        "compressed_sha256": _sha(compressed),
        "content_gzip_base64": base64.b64encode(compressed).decode(),
    }


def _decode(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != ARTIFACT_NAMES:
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory lifecycle artifact roster drifted"
        )
    expected_fields = {
        "compression",
        "raw_size",
        "raw_sha256",
        "compressed_size",
        "compressed_sha256",
        "content_gzip_base64",
    }
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict) or set(receipt) != expected_fields:
            raise InfiniMemoryLifecycleEvidenceError(
                f"invalid artifact receipt: {name}"
            )
        try:
            compressed = base64.b64decode(
                receipt["content_gzip_base64"], validate=True
            )
            raw = gzip.decompress(compressed)
        except (TypeError, ValueError, OSError) as exc:
            raise InfiniMemoryLifecycleEvidenceError(
                f"cannot decode artifact: {name}"
            ) from exc
        if (
            receipt["compression"] != "gzip-mtime-0"
            or receipt["compressed_size"] != len(compressed)
            or receipt["compressed_sha256"] != _sha(compressed)
            or receipt["raw_size"] != len(raw)
            or receipt["raw_sha256"] != _sha(raw)
        ):
            raise InfiniMemoryLifecycleEvidenceError(
                f"artifact receipt drifted: {name}"
            )
        decoded[name] = raw
    return decoded


def _validate_code(bundle: dict[str, Any], project_root: Path) -> None:
    receipts = bundle.get("code_files")
    if not isinstance(receipts, dict) or set(receipts) != CODE_PATHS:
        raise InfiniMemoryLifecycleEvidenceError("Infini Memory code roster drifted")
    for name, expected in receipts.items():
        path = project_root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or path.is_symlink()
            or not path.is_file()
            or _sha(path.read_bytes()) != expected
        ):
            raise InfiniMemoryLifecycleEvidenceError(
                f"Infini Memory code drifted: {name}"
            )


def _validate_manifest(files: dict[str, bytes]) -> None:
    manifest = _object(files["manifest.json"], "Infini Memory manifest")
    declared = manifest.get("files")
    if (
        _sha(files["manifest.json"]) != MANIFEST_SHA256
        or manifest.get("schema_version") != 1
        or manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != len(MANIFEST_FILE_NAMES)
        or not isinstance(declared, dict)
        or set(declared) != MANIFEST_FILE_NAMES
        or declared.get("source.tar") != ARCHIVE_SHA256
    ):
        raise InfiniMemoryLifecycleEvidenceError("Infini Memory manifest drifted")
    for name in ARTIFACT_NAMES - {"manifest.json"}:
        if declared.get(name) != _sha(files[name]):
            raise InfiniMemoryLifecycleEvidenceError(
                f"manifest hash drifted: {name}"
            )


def _validate_source(files: dict[str, bytes]) -> dict[str, Any]:
    receipt = _object(files["source-receipt.json"], "Infini Memory source receipt")
    if (
        receipt.get("revision") != REVISION
        or receipt.get("tree") != TREE
        or receipt.get("archive_sha256") != ARCHIVE_SHA256
        or receipt.get("archive_bytes") != ARCHIVE_BYTES
        or receipt.get("static_source_checks")
        != {finding: True for finding in sorted(STATIC_FINDINGS)}
    ):
        raise InfiniMemoryLifecycleEvidenceError("Infini Memory source receipt drifted")
    return receipt


def _validate_image(files: dict[str, bytes]) -> None:
    try:
        rows = json.loads(files["doctor-image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory image inspection is invalid"
        ) from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory image inspection roster drifted"
        )
    image = rows[0]
    config = image.get("Config") or {}
    labels = config.get("Labels") or {}
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or set(config.get("Volumes") or {}) != {"/state"}
        or labels.get("org.opencontainers.image.revision") != REVISION
        or labels.get("org.cotcodec.source-tree") != TREE
        or labels.get("org.cotcodec.source-archive-sha256") != ARCHIVE_SHA256
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.py"])
        or labels.get("org.cotcodec.discovery-only") != "true"
    ):
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory doctor image provenance drifted"
        )


def _validate_diagnostic(phase: dict[str, Any]) -> None:
    diagnostic = phase["metrics"].get("write_path_diagnostic")
    if not isinstance(diagnostic, dict):
        raise InfiniMemoryLifecycleEvidenceError("Infini Memory diagnostic missing")
    exact = {
        "documents": 4,
        "queries": 3,
        "bm25_query_calls": 3,
        "bm25_candidate_documents": 12,
        "direct_markdown_query_calls": 3,
        "direct_markdown_files_read": 12,
        "rewrite_processed": 1,
        "deterministic_llm_calls": 1,
        "deterministic_llm_calls_by_kind": {
            "extract": 0,
            "other": 0,
            "rewrite": 1,
        },
    }
    if any(diagnostic.get(key) != value for key, value in exact.items()):
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory diagnostic counts drifted"
        )
    for lane, work_key in (("bm25", "candidate_documents"), ("direct_markdown", "files_read")):
        rows = diagnostic.get(lane)
        if not isinstance(rows, list) or len(rows) != 3:
            raise InfiniMemoryLifecycleEvidenceError(
                f"Infini Memory {lane} diagnostic roster drifted"
            )
        for row in rows:
            if (
                not isinstance(row, dict)
                or row.get("target_present") is not True
                or row.get("result_count") != 1
                or row.get(work_key) != 4
                or not isinstance(row.get("elapsed_ns"), int)
                or isinstance(row.get("elapsed_ns"), bool)
                or row["elapsed_ns"] <= 0
            ):
                raise InfiniMemoryLifecycleEvidenceError(
                    f"Infini Memory {lane} diagnostic row drifted"
                )


def _validate_repeat(files: dict[str, bytes], repeat: int) -> dict[str, Any]:
    payload = _object(files[f"repeat-{repeat}.json"], f"Infini Memory repeat {repeat}")
    phases = payload.get("phases")
    if (
        payload.get("repeat") != repeat
        or payload.get("phase_count") != 4
        or payload.get("fresh_process_restart_count") != 3
        or payload.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or not isinstance(phases, list)
        or len(phases) != 4
    ):
        raise InfiniMemoryLifecycleEvidenceError(
            f"Infini Memory repeat {repeat} identity drifted"
        )
    stable: list[dict[str, bool]] = []
    for index, phase in enumerate(phases, start=1):
        checks = phase.get("checks") if isinstance(phase, dict) else None
        if (
            not isinstance(phase, dict)
            or phase.get("phase") != index
            or not isinstance(checks, dict)
            or set(checks) != PHASE_CHECKS[index - 1]
            or not all(value is True for value in checks.values())
            or not isinstance(phase.get("metrics"), dict)
        ):
            raise InfiniMemoryLifecycleEvidenceError(
                f"Infini Memory repeat {repeat} phase {index} drifted"
            )
        stable.append(checks)
        raw = files[f"repeat-{repeat}-phase-{index}.txt"]
        marker = b"COTCODEC_INFINI_MEMORY_PHASE="
        markers = [
            line.split(marker, 1)[1] for line in raw.splitlines() if marker in line
        ]
        if len(markers) != 1 or _object(markers[0], "phase marker") != phase:
            raise InfiniMemoryLifecycleEvidenceError(
                f"Infini Memory repeat {repeat} phase marker drifted"
            )
    if (
        payload.get("stable_projection") != stable
        or _sha(json.dumps(stable, separators=(",", ":"), sort_keys=True).encode())
        != STABLE_PROJECTION_SHA256
    ):
        raise InfiniMemoryLifecycleEvidenceError(
            f"Infini Memory repeat {repeat} stable projection drifted"
        )
    _validate_diagnostic(phases[2])
    residue = phases[2]["metrics"].get("post_delete_plaintext_residue_paths")
    if (
        not isinstance(residue, dict)
        or len(residue) != 3
        or not all(
            re.fullmatch(
                r"COTIM_(DELETE_DOC|DELETE_USER|ESCAPED_DELETE)_[0-9A-F]{16}",
                key,
            )
            for key in residue
        )
        or any(value != [] for value in residue.values())
    ):
        raise InfiniMemoryLifecycleEvidenceError(
            f"Infini Memory repeat {repeat} deletion residue drifted"
        )
    return payload


def _validate_report(
    files: dict[str, bytes], repeats: list[dict[str, Any]]
) -> dict[str, Any]:
    report = _object(files["report.json"], "Infini Memory lifecycle report")
    if (
        _sha(files["report.json"]) != REPORT_SHA256
        or report.get("schema_version") != 1
        or report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("run_count") != 2
        or report.get("fresh_process_restart_count_per_run") != 3
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("claim_boundary") != CLAIM_BOUNDARY
        or report.get("findings")
        != {finding: True for finding in sorted(EXPECTED_FINDINGS)}
    ):
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory lifecycle report drifted"
        )
    expected_diagnostics = [
        repeat["phases"][2]["metrics"]["write_path_diagnostic"]
        for repeat in repeats
    ]
    expected_residue = [
        repeat["phases"][2]["metrics"]["post_delete_plaintext_residue_paths"]
        for repeat in repeats
    ]
    if (
        report.get("write_path_diagnostics") != expected_diagnostics
        or report.get("post_delete_plaintext_residue_paths") != expected_residue
    ):
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory report projections drifted"
        )
    return report


def validate_evidence(
    source: Path | dict[str, Any] = DEFAULT_OUTPUT,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate the self-contained evidence bundle against its exact code surface."""
    if isinstance(source, Path):
        if source.is_symlink() or not source.is_file():
            raise InfiniMemoryLifecycleEvidenceError(
                "Infini Memory lifecycle evidence is missing"
            )
        bundle = _object(source.read_bytes(), "Infini Memory lifecycle evidence")
    else:
        bundle = source
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "infini-memory"
        or bundle.get("source_revision") != REVISION
        or bundle.get("source_revisions")
        != {"https://github.com/infinigence/Infini-Memory": REVISION}
        or bundle.get("source_tree") != TREE
        or bundle.get("evidence_kind") != "contained-native-lifecycle-negative"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("runtime_lane") != "local-arm64-docker-network-none"
        or bundle.get("run_count") != 2
        or bundle.get("fresh_process_restart_count_per_run") != 3
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or bundle.get("report_sha256") != REPORT_SHA256
        or bundle.get("manifest_sha256") != MANIFEST_SHA256
        or bundle.get("claim_boundary") != CLAIM_BOUNDARY
        or bundle.get("h100_actor_admission") != "forbidden-for-this-revision"
        or bundle.get("findings")
        != {finding: True for finding in sorted(EXPECTED_FINDINGS)}
        or bundle.get("source_archive")
        != {"bytes": ARCHIVE_BYTES, "sha256": ARCHIVE_SHA256, "embedded": False}
    ):
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory lifecycle evidence identity drifted"
        )
    _validate_code(bundle, project_root)
    files = _decode(bundle.get("artifact_files"))
    _validate_manifest(files)
    source_receipt = _validate_source(files)
    _validate_image(files)
    if files["Dockerfile"] != (
        project_root / "infra/memory-baselines/infini-memory/Dockerfile"
    ).read_bytes():
        raise InfiniMemoryLifecycleEvidenceError("embedded Dockerfile drifted")
    if files["doctor.py"] != (
        project_root / "infra/memory-baselines/infini-memory/doctor.py"
    ).read_bytes():
        raise InfiniMemoryLifecycleEvidenceError("embedded doctor drifted")
    if not DIRECT_REQUIREMENTS.issubset(
        set(files["pip-freeze.txt"].decode().splitlines())
    ):
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory dependency receipt drifted"
        )
    experiment = yaml.safe_load(files["experiment.yaml"])
    if not isinstance(experiment, dict) or experiment != validate_experiment_contract():
        raise InfiniMemoryLifecycleEvidenceError(
            "embedded Infini Memory experiment drifted"
        )
    repeats = [_validate_repeat(files, repeat) for repeat in (1, 2)]
    if repeats[0]["stable_projection"] != repeats[1]["stable_projection"]:
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory clean-state projections diverged"
        )
    report = _validate_report(files, repeats)
    if report.get("source") != source_receipt:
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory report source receipt drifted"
        )
    return bundle


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def seal(root: Path = DEFAULT_ROOT, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Validate the retained directory and write one portable evidence bundle."""
    if root.is_symlink() or not root.is_dir():
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory lifecycle artifact root is missing"
        )
    actual = {path.name for path in root.iterdir() if path.is_file()}
    if actual != ARTIFACT_NAMES | {"source.tar"}:
        raise InfiniMemoryLifecycleEvidenceError(
            "Infini Memory lifecycle artifact directory drifted"
        )
    artifact_files = {name: _capture(root / name) for name in sorted(ARTIFACT_NAMES)}
    report = _object((root / "report.json").read_bytes(), "lifecycle report")
    bundle = {
        "schema_version": 1,
        "source_id": "infini-memory",
        "source_revision": REVISION,
        "source_revisions": {
            "https://github.com/infinigence/Infini-Memory": REVISION
        },
        "source_tree": TREE,
        "evidence_kind": "contained-native-lifecycle-negative",
        "evidence_grade": "local-negative-reproduced",
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "fresh_process_restart_count_per_run": 3,
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "report_sha256": REPORT_SHA256,
        "manifest_sha256": MANIFEST_SHA256,
        "claim_boundary": CLAIM_BOUNDARY,
        "h100_actor_admission": "forbidden-for-this-revision",
        "findings": {finding: True for finding in sorted(EXPECTED_FINDINGS)},
        "source_archive": {
            "bytes": ARCHIVE_BYTES,
            "sha256": ARCHIVE_SHA256,
            "embedded": False,
        },
        "code_files": {
            name: _sha((PROJECT_ROOT / name).read_bytes()) for name in CODE_PATHS
        },
        "artifact_files": artifact_files,
        "write_path_diagnostics": report["write_path_diagnostics"],
        "post_delete_plaintext_residue_paths": report[
            "post_delete_plaintext_residue_paths"
        ],
    }
    validate_evidence(bundle)
    _write_once(output, (json.dumps(bundle, indent=2, sort_keys=True) + "\n").encode())
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        validate_evidence(args.output)
        print("Infini Memory native lifecycle evidence PASS")
    else:
        bundle = seal(args.root, args.output)
        print(json.dumps({"output": str(args.output), "status": bundle["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
