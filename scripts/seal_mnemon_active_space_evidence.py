#!/usr/bin/env python3
"""Seal and validate the two-repeat Mnemon active-space admission evidence."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validate_mnemon_active_space_experiment import (  # noqa: E402
    EXPECTED_SOURCES,
    EXPECTED_STATUS,
)

DEFAULT_ROOT = (
    PROJECT_ROOT / "data/results/mnemon-active-space/2026-08-16-local-docker-v1"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "research/evidence/memory/mnemon-active-space-admission-v1.json"
)
IMAGE_ID = "sha256:758216ed7cf9fa7794ab4e63efac2a08b4af92a78b99ae378ab6b512e6d9db5f"
STABLE_PROJECTION_SHA256 = (
    "34ace60034308da2e72669ed06f8bb6ca378b35a3e32fa807d4c732fe71b1e48"
)
RUNTIME_LANE = "local-arm64-docker-network-none"
SOURCE_NAMES = (
    "dsh-mnemon/LICENSE",
    "dsh-mnemon/memory-bodies.ts",
    "dsh-mnemon/package.json",
    "dsh-mnemon/pnpm-lock.yaml",
    "dsh-mnemon/runner.ts",
    "dsh-mnemon/service.ts",
    "mnemon/LICENSE",
    "mnemon/forget.go",
    "mnemon/go.mod",
    "mnemon/go.sum",
    "mnemon/node.go",
    "mnemon/store.go",
)
CODE_PATHS = {
    "Dockerfile": PROJECT_ROOT / "infra/memory-baselines/mnemon/Dockerfile",
    "doctor.mjs": PROJECT_ROOT / "infra/memory-baselines/mnemon/doctor.mjs",
    "run_mnemon_active_space_doctor.py": PROJECT_ROOT
    / "scripts/run_mnemon_active_space_doctor.py",
    "validate_mnemon_active_space_experiment.py": PROJECT_ROOT
    / "scripts/validate_mnemon_active_space_experiment.py",
}
ROOT_NAMES = {
    "Dockerfile",
    "doctor.mjs",
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    *(f"repeat-{repeat}.{suffix}" for repeat in (1, 2) for suffix in ("json", "txt")),
    *(f"source/{name}" for name in SOURCE_NAMES),
}
EXPECTED_FILE_ROSTER = {*CODE_PATHS, *ROOT_NAMES}
EXPECTED_CHECKS = {
    "activation_registry_survives_restart",
    "core_named_stores_use_distinct_databases",
    "core_soft_forget_hides_but_preserves_row",
    "explicit_inactive_read_is_rejected",
    "last_native_store_delete_is_rejected",
    "plugin_active_set_limits_default_recall",
    "plugin_space_delete_removes_store_directory",
    "targeted_write_autoactivates_space",
}


class EvidenceError(ValueError):
    """Raised when retained Mnemon admission evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _strict_json(data: bytes, owner: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise EvidenceError(f"{owner} contains non-finite value {value}")

    try:
        value = json.loads(data, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{owner} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{owner} must be a JSON object")
    return value


def _capture(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular Mnemon evidence input: {path}")
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": _sha(data),
        "content_base64": base64.b64encode(data).decode("ascii"),
    }


def _decode_files(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Mnemon evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise EvidenceError(f"invalid Mnemon receipt for {name}")
        try:
            data = base64.b64decode(receipt.get("content_base64", ""), validate=True)
        except (TypeError, ValueError) as exc:
            raise EvidenceError(f"invalid base64 for {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise EvidenceError(f"embedded Mnemon receipt drifted: {name}")
        decoded[name] = data
    return decoded


def _validate_source_semantics(files: dict[str, bytes]) -> None:
    core_store = files["source/mnemon/store.go"].decode()
    core_forget = files["source/mnemon/forget.go"].decode()
    core_node = files["source/mnemon/node.go"].decode()
    bodies = files["source/dsh-mnemon/memory-bodies.ts"].decode()
    service = files["source/dsh-mnemon/service.ts"].decode()
    required_store = (
        "Create, list, switch, and remove isolated memory stores.",
        "os.RemoveAll(dir)",
        "cannot remove the active store",
    )
    required_bodies = (
        "return this.list().filter(body => body.active)",
        "setActive(id: string, active: boolean)",
        "this.registryPath = join(this.directory, '.dsh-memory-bodies.json')",
    )
    required_service = (
        "if (!body.active) throw new Error(`memory body is not active for reading: ${id}`)",
        "if (!body.active) this.memoryBodies.setActive(body.id, true)",
    )
    if any(value not in core_store for value in required_store):
        raise EvidenceError("Mnemon named-store source semantics drifted")
    if (
        "Mark an insight as deleted (soft delete). The data is preserved" not in core_forget
        or "db.SoftDeleteInsight(id)" not in core_forget
        or "UPDATE insights SET deleted_at = ?" not in core_node
    ):
        raise EvidenceError("Mnemon soft-delete source semantics drifted")
    if any(value not in bodies for value in required_bodies):
        raise EvidenceError("dsh-mnemon active registry semantics drifted")
    if any(value not in service for value in required_service):
        raise EvidenceError("dsh-mnemon active read semantics drifted")


def _validate_repeat(payload: dict[str, Any], repeat: int) -> None:
    if (
        payload.get("schema_version") != 1
        or payload.get("system_id") != "mnemon-dsh-static-active-space-admission-v1"
        or payload.get("status") != EXPECTED_STATUS
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("h100_actor_admission") is not True
        or set(payload.get("checks", {})) != EXPECTED_CHECKS
        or any(payload["checks"].get(name) is not True for name in EXPECTED_CHECKS)
    ):
        raise EvidenceError(f"Mnemon repeat {repeat} identity drifted")
    if payload.get("observations") != {
        "access_control": False,
        "active_count_after_restart": 1,
        "active_selection_owner": "dsh-mnemon-plugin",
        "learned_promotion_or_demotion": False,
        "memory_space_count_after_delete": 1,
        "memory_space_count_before_delete": 2,
        "native_store_owner": "mnemon-core",
        "physical_item_erasure_proven": False,
        "soft_delete_preserved_plaintext": True,
    }:
        raise EvidenceError(f"Mnemon repeat {repeat} observations drifted")


def validate_files(files: dict[str, bytes]) -> dict[str, Any]:
    if set(files) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Mnemon evidence file roster drifted")
    experiment = yaml.safe_load(files["experiment.yaml"])
    if (
        not isinstance(experiment, dict)
        or experiment.get("name") != "stage3-mnemon-active-space-admission-doctor"
        or experiment.get("sources") != EXPECTED_SOURCES
        or experiment.get("admission_gates", {}).get("expected_status")
        != EXPECTED_STATUS
    ):
        raise EvidenceError("embedded Mnemon experiment drifted")
    _validate_source_semantics(files)

    report = _strict_json(files["report.json"], "report.json")
    manifest = _strict_json(files["manifest.json"], "manifest.json")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") is not True
        or report.get("experiment_sha256") != _sha(files["experiment.yaml"])
        or report.get("dockerfile_sha256") != _sha(files["Dockerfile"])
        or report.get("doctor_sha256") != _sha(files["doctor.mjs"])
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("run_count") != 2
    ):
        raise EvidenceError("Mnemon report contract drifted")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != EXPECTED_STATUS
        or not isinstance(manifest.get("files"), dict)
    ):
        raise EvidenceError("Mnemon manifest contract drifted")
    expected_manifest_names = ROOT_NAMES - {"manifest.json"}
    if set(manifest["files"]) != expected_manifest_names:
        raise EvidenceError("Mnemon manifest file roster drifted")
    for name, receipt in manifest["files"].items():
        data = files[name]
        if receipt != {"bytes": len(data), "sha256": _sha(data)}:
            raise EvidenceError(f"Mnemon manifest receipt drifted: {name}")

    source_digests = {name: _sha(files[f"source/{name}"]) for name in SOURCE_NAMES}
    if source_digests != report.get("source_file_sha256"):
        raise EvidenceError("Mnemon source file receipt drifted")
    image_rows = json.loads(files["image-inspect.json"])
    if not isinstance(image_rows, list) or len(image_rows) != 1:
        raise EvidenceError("Mnemon image inspection roster drifted")
    image = image_rows[0]
    config = image.get("Config", {})
    labels = config.get("Labels", {})
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or config.get("Entrypoint") != ["node", "/opt/cotcodec/doctor.mjs"]
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.opencontainers.image.revision")
        != EXPECTED_SOURCES["mnemon"]["revision"]
        or labels.get("org.cotcodec.dsh-mnemon-revision")
        != EXPECTED_SOURCES["dsh_mnemon"]["revision"]
        or report.get("image", {}).get("image_id") != IMAGE_ID
        or report.get("image", {}).get("inspect_sha256")
        != _sha(files["image-inspect.json"])
    ):
        raise EvidenceError("Mnemon image provenance drifted")

    repeats: list[dict[str, Any]] = []
    for repeat in (1, 2):
        payload = _strict_json(files[f"repeat-{repeat}.json"], f"repeat-{repeat}.json")
        _validate_repeat(payload, repeat)
        raw = files[f"repeat-{repeat}.txt"]
        rows = [
            line.split(b"=", 1)[1]
            for line in raw.splitlines()
            if line.startswith(b"COTCODEC_MNEMON_REPORT=")
        ]
        if len(rows) != 1 or _strict_json(rows[0], f"repeat-{repeat} raw marker") != payload:
            raise EvidenceError(f"Mnemon repeat {repeat} raw receipt drifted")
        repeats.append(payload)
    if repeats[0] != repeats[1] or repeats[0] != report.get("stable_projection"):
        raise EvidenceError("Mnemon clean-state projections drifted")
    if _sha(_canonical(repeats[0])) != STABLE_PROJECTION_SHA256:
        raise EvidenceError("Mnemon stable projection digest drifted")
    return {
        "projection": repeats[0],
        "report_sha256": _sha(files["report.json"]),
        "manifest_sha256": _sha(files["manifest.json"]),
    }


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular Mnemon evidence bundle: {path}")
    bundle = _strict_json(path.read_bytes(), "Mnemon evidence bundle")
    if (
        bundle.get("schema_version") != 1
        or bundle.get("evidence_kind") != "native-control-admission"
        or bundle.get("source_id") != "mnemon"
        or bundle.get("companion_source_id") != "dsh-mnemon"
        or bundle.get("evidence_grade") != "local-conformance-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("h100_admission") != "bounded-static-selection-cell-only"
        or bundle.get("runtime_lane") != RUNTIME_LANE
        or bundle.get("run_count") != 2
        or bundle.get("source_revisions")
        != {
            EXPECTED_SOURCES["mnemon"]["repository"]: EXPECTED_SOURCES["mnemon"]["revision"],
            EXPECTED_SOURCES["dsh_mnemon"]["repository"]: EXPECTED_SOURCES[
                "dsh_mnemon"
            ]["revision"],
        }
    ):
        raise EvidenceError("Mnemon top-level evidence contract drifted")
    verified = validate_files(_decode_files(bundle.get("files")))
    boundary = {
        "access_control_demonstrated": False,
        "active_selection_owner": "dsh-mnemon-plugin",
        "core_named_store_isolation_demonstrated": True,
        "h100_actor_admission": "bounded-static-selection-cell-only",
        "item_physical_erasure_demonstrated": False,
        "learned_bidirectional_paging_demonstrated": False,
        "memory_quality_measured": False,
        "soft_delete_retains_plaintext": True,
        "whole_space_delete_demonstrated": True,
    }
    if (
        bundle.get("shared_image_id") != IMAGE_ID
        or bundle.get("stable_projection") != verified["projection"]
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or bundle.get("report_sha256") != verified["report_sha256"]
        or bundle.get("manifest_sha256") != verified["manifest_sha256"]
        or bundle.get("claim_boundary") != boundary
    ):
        raise EvidenceError("Mnemon evidence receipt drifted")
    return bundle


def seal(root: Path) -> dict[str, Any]:
    paths = {
        **CODE_PATHS,
        **{name: root / name for name in ROOT_NAMES},
    }
    files = {name: path.read_bytes() for name, path in paths.items()}
    verified = validate_files(files)
    return {
        "schema_version": 1,
        "evidence_kind": "native-control-admission",
        "source_id": "mnemon",
        "companion_source_id": "dsh-mnemon",
        "source_revisions": {
            EXPECTED_SOURCES["mnemon"]["repository"]: EXPECTED_SOURCES["mnemon"]["revision"],
            EXPECTED_SOURCES["dsh_mnemon"]["repository"]: EXPECTED_SOURCES[
                "dsh_mnemon"
            ]["revision"],
        },
        "evidence_grade": "local-conformance-reproduced",
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "bounded-static-selection-cell-only",
        "runtime_lane": RUNTIME_LANE,
        "run_count": 2,
        "shared_image_id": IMAGE_ID,
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "stable_projection": verified["projection"],
        "report_sha256": verified["report_sha256"],
        "manifest_sha256": verified["manifest_sha256"],
        "claim_boundary": {
            "access_control_demonstrated": False,
            "active_selection_owner": "dsh-mnemon-plugin",
            "core_named_store_isolation_demonstrated": True,
            "h100_actor_admission": "bounded-static-selection-cell-only",
            "item_physical_erasure_demonstrated": False,
            "learned_bidirectional_paging_demonstrated": False,
            "memory_quality_measured": False,
            "soft_delete_retains_plaintext": True,
            "whole_space_delete_demonstrated": True,
        },
        "files": {name: _capture(path) for name, path in paths.items()},
    }


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        result = validate_evidence(args.output)
    else:
        result = seal(args.root)
        data = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
        _write_once(args.output, data)
        validate_evidence(args.output)
    print(json.dumps({
        "status": result["status"],
        "evidence_sha256": _sha(args.output.read_bytes()),
        "stable_projection_sha256": result["stable_projection_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
