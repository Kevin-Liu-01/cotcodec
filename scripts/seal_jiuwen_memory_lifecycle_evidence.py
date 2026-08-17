#!/usr/bin/env python3
"""Seal and validate JiuwenMemory's exact-source lifecycle negative."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import TypeAlias

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_jiuwen_memory_lifecycle_experiment import EXPECTED_STATUS  # noqa: E402

DEFAULT_ROOT = PROJECT_ROOT / "data/results/jiuwen-memory-lifecycle/2026-08-17-local-docker-v3"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "research/evidence/memory/jiuwen-memory-file-lifecycle-negative-v1.json"
)
REVISION = "600432b55e480bec5948ee40089884ccf15a7c5d"
REPOSITORY = "https://github.com/openJiuwen-ai/agent-memory"
TREE = "1b6518ba4f0d89d99cb7febd3e3d7a27b2e8347c"
ARCHIVE_SHA256 = "38c6868fe7a707d1912c0b10a64a5661571b0ed6e341464fea65463d83842c3e"
IMAGE_ID = "sha256:c5ca75c1f299fde9efc0097d941d9e2c12973649aa8b91c6ecc76f00e2d54eae"
STABLE_PROJECTION_SHA256 = "a9c6e7fdf059275048ec911961956ff707e554b247cfa6ffc68a0a277c402aac"
CLAIM_BOUNDARY = (
    "Exact pinned FileMemoryIndex CRUD, duplicate-ID tenancy, index migration under "
    "two fixed process hash seeds, fresh-process restart, native user-scope deletion, "
    "committed-lock conformance, and SQLite plaintext residue; not extraction, dreaming, "
    "graph, semantic retrieval quality, model effects, H100 actor quality, or publication "
    "evidence."
)
GENERATED_NAMES = {
    "Dockerfile",
    "docker-build.txt",
    "doctor-image-inspect.json",
    "experiment.yaml",
    "lifecycle_doctor.py",
    "repeat-1-phase-1.txt",
    "repeat-1-phase-2.txt",
    "repeat-1.json",
    "repeat-2-phase-1.txt",
    "repeat-2-phase-2.txt",
    "repeat-2.json",
    "report.json",
    "source-receipt.json",
    "uv-file-index-extra.txt",
    "uv-frozen-base-import.txt",
    "uv-frozen-base-sync.txt",
    "uv-lock-check.txt",
}
CODE_PATHS = {
    "code/scripts/run_jiuwen_memory_lifecycle_doctor.py": PROJECT_ROOT
    / "scripts/run_jiuwen_memory_lifecycle_doctor.py",
    "code/scripts/validate_jiuwen_memory_lifecycle_experiment.py": PROJECT_ROOT
    / "scripts/validate_jiuwen_memory_lifecycle_experiment.py",
}
EXPECTED_ROSTER = {
    *(f"artifact/{name}" for name in GENERATED_NAMES | {"manifest.json"}),
    *CODE_PATHS,
}
REQUIRED_FINDINGS = {
    "committed_lock_fails_uv_check",
    "committed_lock_omits_declared_file_index_extra",
    "deleted_markdown_sources_are_absent",
    "duplicate_id_defect_survives_restart",
    "duplicate_id_overwrites_sibling_tenant_index_row",
    "duplicate_markdown_copies_survive_migration",
    "file_index_does_not_enable_sqlite_secure_delete",
    "file_index_exposes_native_user_scope_delete",
    "file_index_migration_version_is_process_local",
    "file_index_upsert_overwrites_on_global_memory_id",
    "file_index_uses_global_memory_id_primary_key",
    "frozen_base_environment_cannot_import_declared_package",
    "migration_index_owner_depends_on_process_hash_order",
    "migration_preserves_exactly_one_duplicate_index_owner",
    "migration_replays_after_restart",
    "migration_version_resets_on_restart",
    "migration_version_set_before_restart",
    "native_scoped_delete_is_logically_effective",
    "post_delete_plaintext_residue_scan_completed",
    "sibling_scope_delete_preserves_other_markdown_copy",
    "sibling_scope_delete_preserves_unique_control",
    "tenant_a_markdown_survives_index_collision",
    "tenant_b_duplicate_id_is_visible",
    "unique_id_controls_survive_restart",
    "unique_id_controls_visible_before_restart",
}
JSONPrimitive: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]


class JiuwenEvidenceError(ValueError):
    """Raised when retained JiuwenMemory evidence is incomplete or drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: JSONValue) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _object(data: bytes, owner: str) -> JSONObject:
    def reject(value: str) -> None:
        raise JiuwenEvidenceError(f"{owner} contains non-finite JSON {value}")

    try:
        payload = json.loads(data, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JiuwenEvidenceError(f"{owner} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise JiuwenEvidenceError(f"{owner} must be a JSON object")
    return payload


def _capture(path: Path) -> JSONObject:
    if path.is_symlink() or not path.is_file():
        raise JiuwenEvidenceError(f"expected regular evidence input: {path}")
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": _sha(data),
        "content_base64": base64.b64encode(data).decode(),
    }


def _decode(receipts: JSONValue) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_ROSTER:
        raise JiuwenEvidenceError("JiuwenMemory evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise JiuwenEvidenceError(f"invalid JiuwenMemory receipt: {name}")
        encoded = receipt.get("content_base64")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (TypeError, ValueError) as exc:
            raise JiuwenEvidenceError(f"invalid JiuwenMemory base64: {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise JiuwenEvidenceError(f"JiuwenMemory embedded file drifted: {name}")
        decoded[name] = data
    return decoded


def _require_true_checks(payload: JSONObject, owner: str) -> None:
    checks = payload.get("checks")
    if (
        not isinstance(checks, dict)
        or not checks
        or not all(value is True for value in checks.values())
    ):
        raise JiuwenEvidenceError(f"{owner} checks drifted")


def _validate_repeat(files: dict[str, bytes], repeat: int, seed: int, owner: str) -> JSONObject:
    payload = _object(files[f"artifact/repeat-{repeat}.json"], f"repeat {repeat}")
    phases = payload.get("phases")
    if (
        payload.get("repeat") != repeat
        or payload.get("python_hash_seed") != seed
        or payload.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or not isinstance(phases, list)
        or len(phases) != 2
        or payload.get("stable_projection") != phases_to_projection(phases)
    ):
        raise JiuwenEvidenceError(f"JiuwenMemory repeat {repeat} identity drifted")
    if _sha(_canonical(payload["stable_projection"])) != STABLE_PROJECTION_SHA256:
        raise JiuwenEvidenceError(f"JiuwenMemory repeat {repeat} projection drifted")
    for phase_number, phase in enumerate(phases, start=1):
        if not isinstance(phase, dict) or phase.get("phase") != phase_number:
            raise JiuwenEvidenceError(f"JiuwenMemory repeat {repeat} phase roster drifted")
        _require_true_checks(phase, f"repeat {repeat} phase {phase_number}")
        raw = files[f"artifact/repeat-{repeat}-phase-{phase_number}.txt"]
        marker = b"COTCODEC_JIUWEN_PHASE="
        rows = [line.split(marker, 1)[1] for line in raw.splitlines() if marker in line]
        if len(rows) != 1 or _object(rows[0], "phase marker") != phase:
            raise JiuwenEvidenceError(f"JiuwenMemory repeat {repeat} phase receipt drifted")
    phase_one = phases[0]
    phase_two = phases[1]
    metrics_one = phase_one.get("metrics")
    metrics_two = phase_two.get("metrics")
    if not isinstance(metrics_one, dict) or not isinstance(metrics_two, dict):
        raise JiuwenEvidenceError(f"JiuwenMemory repeat {repeat} metrics missing")
    row = metrics_one.get("migrated_chunk_row")
    if (
        metrics_one.get("sqlite_secure_delete") != 1
        or not isinstance(row, list)
        or row[:1] != [owner]
        or metrics_two.get("indexed_owner_before_restart") != owner
        or metrics_two.get("proof_window_count") != 0
        or metrics_two.get("residue_canaries") != []
    ):
        raise JiuwenEvidenceError(f"JiuwenMemory repeat {repeat} outcome drifted")
    return payload


def phases_to_projection(phases: list[JSONValue]) -> list[JSONValue]:
    projection: list[JSONValue] = []
    for phase in phases:
        if not isinstance(phase, dict):
            raise JiuwenEvidenceError("JiuwenMemory phase projection drifted")
        row: JSONObject = {"phase": phase.get("phase"), "checks": phase.get("checks")}
        metrics = phase.get("metrics")
        if isinstance(metrics, dict):
            row["residue_canaries"] = metrics.get("residue_canaries")
        projection.append(row)
    return projection


def validate_files(files: dict[str, bytes]) -> JSONObject:
    if set(files) != EXPECTED_ROSTER:
        raise JiuwenEvidenceError("JiuwenMemory evidence file roster drifted")
    manifest = _object(files["artifact/manifest.json"], "manifest")
    manifest_files = manifest.get("files")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != EXPECTED_STATUS
        or manifest.get("file_count") != 18
        or not isinstance(manifest_files, dict)
        or set(manifest_files) != GENERATED_NAMES | {"source.tar"}
        or manifest_files.get("source.tar") != ARCHIVE_SHA256
    ):
        raise JiuwenEvidenceError("JiuwenMemory manifest drifted")
    for name in GENERATED_NAMES:
        if manifest_files.get(name) != _sha(files[f"artifact/{name}"]):
            raise JiuwenEvidenceError(f"JiuwenMemory manifest hash drifted: {name}")

    report = _object(files["artifact/report.json"], "report")
    findings = report.get("findings")
    source = report.get("source")
    image = report.get("doctor_image")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("run_count") != 2
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("claim_boundary") != CLAIM_BOUNDARY
        or not isinstance(findings, dict)
        or set(findings) != REQUIRED_FINDINGS
        or not all(value is True for value in findings.values())
        or not isinstance(source, dict)
        or source.get("revision") != REVISION
        or source.get("tree") != TREE
        or source.get("archive_sha256") != ARCHIVE_SHA256
        or not isinstance(image, dict)
        or image.get("image_id") != IMAGE_ID
        or image.get("architecture") != "arm64"
        or image.get("os") != "linux"
        or image.get("user") != "65532:65532"
    ):
        raise JiuwenEvidenceError("JiuwenMemory report drifted")
    if _object(files["artifact/source-receipt.json"], "source receipt") != source:
        raise JiuwenEvidenceError("JiuwenMemory source receipt drifted")

    first = _validate_repeat(files, 1, 1, "user-a")
    second = _validate_repeat(files, 2, 7, "user-b")
    if first.get("stable_projection") != second.get("stable_projection"):
        raise JiuwenEvidenceError("JiuwenMemory clean-state projections diverged")
    experiment = yaml.safe_load(files["artifact/experiment.yaml"])
    if (
        not isinstance(experiment, dict)
        or experiment.get("expected_falsification", {}).get("status") != EXPECTED_STATUS
        or experiment.get("runtime", {}).get("python_hash_seeds") != [1, 7]
    ):
        raise JiuwenEvidenceError("JiuwenMemory embedded experiment drifted")
    packaging = {
        "uv-lock-check.txt": "lockfile at `uv.lock` needs to be updated",
        "uv-file-index-extra.txt": "Extra `file-index` is not defined",
        "uv-frozen-base-import.txt": "No module named 'gmssl'",
    }
    for name, needle in packaging.items():
        if needle not in files[f"artifact/{name}"].decode(errors="replace"):
            raise JiuwenEvidenceError(f"JiuwenMemory packaging receipt drifted: {name}")
    return {
        "findings": findings,
        "report_sha256": _sha(files["artifact/report.json"]),
        "manifest_sha256": _sha(files["artifact/manifest.json"]),
        "stable_projection": first["stable_projection"],
    }


def validate_evidence(source: Path | JSONObject = DEFAULT_OUTPUT) -> JSONObject:
    if isinstance(source, Path):
        if source.is_symlink() or not source.is_file():
            raise JiuwenEvidenceError(f"expected regular evidence bundle: {source}")
        bundle = _object(source.read_bytes(), "JiuwenMemory evidence bundle")
    else:
        bundle = source
    if (
        bundle.get("schema_version") != 1
        or bundle.get("evidence_kind") != "native-negative-reproduction"
        or bundle.get("source_id") != "jiuwen-memory"
        or bundle.get("source_revisions") != {REPOSITORY: REVISION}
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("h100_admission") != "forbidden-for-this-revision"
        or bundle.get("runtime_lane") != "local-arm64-docker-network-none"
        or bundle.get("run_count") != 2
        or bundle.get("python_hash_seeds") != [1, 7]
        or bundle.get("shared_image_id") != IMAGE_ID
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
    ):
        raise JiuwenEvidenceError("JiuwenMemory top-level evidence contract drifted")
    verified = validate_files(_decode(bundle.get("files")))
    if (
        bundle.get("findings") != verified["findings"]
        or bundle.get("report_sha256") != verified["report_sha256"]
        or bundle.get("manifest_sha256") != verified["manifest_sha256"]
        or bundle.get("stable_projection") != verified["stable_projection"]
        or bundle.get("claim_boundary") != CLAIM_BOUNDARY
    ):
        raise JiuwenEvidenceError("JiuwenMemory evidence receipt drifted")
    return bundle


def seal(root: Path) -> JSONObject:
    paths = {
        **{f"artifact/{name}": root / name for name in GENERATED_NAMES | {"manifest.json"}},
        **CODE_PATHS,
    }
    files = {name: path.read_bytes() for name, path in paths.items()}
    verified = validate_files(files)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "jiuwen-memory",
        "source_revisions": {REPOSITORY: REVISION},
        "evidence_grade": "local-negative-reproduced",
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "forbidden-for-this-revision",
        "runtime_lane": "local-arm64-docker-network-none",
        "run_count": 2,
        "python_hash_seeds": [1, 7],
        "shared_image_id": IMAGE_ID,
        "stable_projection": verified["stable_projection"],
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "findings": verified["findings"],
        "report_sha256": verified["report_sha256"],
        "manifest_sha256": verified["manifest_sha256"],
        "claim_boundary": CLAIM_BOUNDARY,
        "files": {name: _capture(path) for name, path in paths.items()},
    }


def _write_no_replace(path: Path, data: bytes) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if arguments.validate_only:
        bundle = validate_evidence(output)
    else:
        bundle = seal(arguments.root.resolve())
        _write_no_replace(output, _canonical(bundle) + b"\n")
        bundle = validate_evidence(output)
    print(f"JiuwenMemory lifecycle evidence PASS: {bundle['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
