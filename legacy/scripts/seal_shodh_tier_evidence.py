#!/usr/bin/env python3
"""Seal and validate the two-repeat Shodh tier-admission negative."""

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

from scripts.validate_shodh_tier_experiment import (  # noqa: E402
    EXPECTED_SOURCE,
    EXPECTED_STATUS,
)

DEFAULT_ROOT = (
    PROJECT_ROOT / "data/results/shodh-tier-admission/2026-08-16-local-docker-v1"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "research/evidence/memory/shodh-tier-admission-negative-v1.json"
)
IMAGE_ID = "sha256:7afbe36f4023ca96beac46249aff049ccd4ae3b06a969fe1cd31eb6f7770ebc5"
STABLE_PROJECTION_SHA256 = (
    "1a9fc93172a6b682ec26fafb718259d17da7e7e041b7317d369abfcf288eb082"
)
RUNTIME_LANE = "local-arm64-docker-network-none"
SOURCE_NAMES = (
    "AUDIT-MEMORY-2026-08-06.md",
    "Cargo.lock",
    "Cargo.toml",
    "LICENSE",
    "memory-mod.rs",
    "memory-persistence-tests.rs",
    "memory-tiering-tests.rs",
    "memory-types.rs",
)
CODE_PATHS = {
    "Dockerfile": PROJECT_ROOT / "infra/memory-baselines/shodh/Dockerfile",
    "doctor.rs": PROJECT_ROOT / "infra/memory-baselines/shodh/doctor.rs",
    "run_shodh_tier_doctor.py": PROJECT_ROOT / "scripts/run_shodh_tier_doctor.py",
    "validate_shodh_tier_experiment.py": PROJECT_ROOT
    / "scripts/validate_shodh_tier_experiment.py",
}
EXPECTED_FILE_ROSTER = {
    *CODE_PATHS,
    "experiment.yaml",
    "image-inspect.json",
    "manifest.json",
    "report.json",
    *(f"source/{name}" for name in SOURCE_NAMES),
    *(f"repeat-{repeat}.{suffix}" for repeat in (1, 2) for suffix in ("json", "txt")),
}
EXPECTED_CHECKS = {
    "eligible_persisted_session_is_stranded_after_restart",
    "forget_all_return_overcounts_overlapping_tiers",
    "logical_forget_all_hides_record_after_restart",
    "new_working_record_already_in_long_term_storage",
    "plaintext_residue_not_observed_after_forget_all",
    "restart_drops_active_caches",
    "restart_preserves_stale_working_tier_label",
}


class EvidenceError(ValueError):
    """Raised when retained Shodh evidence is incomplete or drifts."""


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
        raise EvidenceError(f"expected regular Shodh evidence input: {path}")
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": _sha(data),
        "content_base64": base64.b64encode(data).decode("ascii"),
    }


def _decode_files(receipts: Any) -> dict[str, bytes]:
    if not isinstance(receipts, dict) or set(receipts) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Shodh evidence file roster drifted")
    decoded: dict[str, bytes] = {}
    for name, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise EvidenceError(f"invalid Shodh receipt for {name}")
        try:
            data = base64.b64decode(receipt.get("content_base64", ""), validate=True)
        except (TypeError, ValueError) as exc:
            raise EvidenceError(f"invalid base64 for {name}") from exc
        if receipt.get("bytes") != len(data) or receipt.get("sha256") != _sha(data):
            raise EvidenceError(f"embedded Shodh receipt drifted: {name}")
        decoded[name] = data
    return decoded


def _validate_source_semantics(files: dict[str, bytes]) -> None:
    module = files["source/memory-mod.rs"].decode("utf-8")
    required = (
        "working_memory_count: 0, // Working memory is in-memory only, starts empty",
        "session_memory_count: 0, // Session memory is in-memory only, starts empty",
        "self.long_term_memory.store(&memory)?;",
        "stats.long_term_memory_count += 1; // Always stored to long-term first",
        "let working = self.working_memory.read();",
        "let session = self.session_memory.read();",
        "stats.promotions_to_longterm += count;",
    )
    if any(marker not in module for marker in required):
        raise EvidenceError("Shodh tier source semantics drifted")
    ordered_write = """self.long_term_memory.store(&memory)?;
        self.logger.write().log_created(&memory, \"import\");

        self.working_memory"""
    if ordered_write not in module:
        raise EvidenceError("Shodh long-term-before-working semantics drifted")


def _validate_repeat(payload: dict[str, Any], repeat: int) -> None:
    if (
        payload.get("schema_version") != 1
        or payload.get("system_id") != "shodh-memory-98c6e48-tier-admission-v1"
        or payload.get("status") != EXPECTED_STATUS
        or payload.get("scientific_result") is not False
        or payload.get("publication_ready") is not False
        or payload.get("h100_actor_admission") is not False
        or set(payload.get("checks", {})) != EXPECTED_CHECKS
        or any(payload["checks"].get(name) is not True for name in EXPECTED_CHECKS)
    ):
        raise EvidenceError(f"Shodh repeat {repeat} identity drifted")
    observations = payload.get("observations", {})
    if (
        observations.get("before_restart")
        != {
            "long_term": 1,
            "session": 0,
            "storage_total": 1,
            "stored_tier": "Working",
            "total": 1,
            "working": 1,
        }
        or observations.get("after_restart")
        != {
            "long_term": 1,
            "session": 0,
            "storage_total": 1,
            "stored_tier": "Working",
            "total": 1,
            "working": 0,
        }
        or observations.get("stranded_before_maintenance")
        != {"long_term": 1, "session": 0, "stored_tier": "Session", "working": 0}
        or observations.get("stranded_after_maintenance")
        != {"promotions_to_longterm": 0, "stored_tier": "Session"}
        or observations.get("forget_all_returned") != 2
        or observations.get("post_forget_total") != 0
        or observations.get("plaintext_present_before_forget") is not False
        or observations.get("plaintext_residue") is not False
    ):
        raise EvidenceError(f"Shodh repeat {repeat} observations drifted")


def validate_files(files: dict[str, bytes]) -> dict[str, Any]:
    if set(files) != EXPECTED_FILE_ROSTER:
        raise EvidenceError("Shodh evidence file roster drifted")
    experiment = yaml.safe_load(files["experiment.yaml"])
    if (
        not isinstance(experiment, dict)
        or experiment.get("name") != "stage3-shodh-tier-admission-doctor"
        or experiment.get("source") != EXPECTED_SOURCE
        or experiment.get("expected_falsification", {}).get("status") != EXPECTED_STATUS
        or experiment.get("admission", {}).get("h100_actor")
        != "forbidden-for-this-revision"
    ):
        raise EvidenceError("embedded Shodh experiment drifted")
    _validate_source_semantics(files)

    report = _strict_json(files["report.json"], "report.json")
    manifest = _strict_json(files["manifest.json"], "manifest.json")
    if (
        report.get("status") != EXPECTED_STATUS
        or report.get("scientific_result") is not False
        or report.get("publication_ready") is not False
        or report.get("h100_actor_admission") != "forbidden-for-this-revision"
        or report.get("source") != EXPECTED_SOURCE
        or report.get("runtime") != experiment.get("runtime")
        or report.get("experiment_sha256") != _sha(files["experiment.yaml"])
        or report.get("dockerfile_sha256") != _sha(files["Dockerfile"])
        or report.get("doctor_sha256") != _sha(files["doctor.rs"])
        or report.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or report.get("reproduced_in_two_clean_states") is not True
    ):
        raise EvidenceError("Shodh report contract drifted")
    if manifest != {
        "artifact_count": 18,
        "image_id": IMAGE_ID,
        "report": "report.json",
        "report_sha256": _sha(files["report.json"]),
        "schema_version": 1,
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "status": "SEALED_DISCOVERY_NEGATIVE",
    }:
        raise EvidenceError("Shodh manifest contract drifted")

    source_digests = {name: _sha(files[f"source/{name}"]) for name in SOURCE_NAMES}
    if source_digests != report.get("source_file_sha256"):
        raise EvidenceError("Shodh source file receipt drifted")

    try:
        image_rows = json.loads(files["image-inspect.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("Shodh image inspection is invalid JSON") from exc
    if not isinstance(image_rows, list) or len(image_rows) != 1:
        raise EvidenceError("Shodh image inspection roster drifted")
    image = image_rows[0]
    config = image.get("Config", {})
    labels = config.get("Labels", {})
    if (
        image.get("Id") != IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
        or config.get("User") != "65532:65532"
        or config.get("Entrypoint") != ["/bin/sh", "-c"]
        or labels.get("org.cotcodec.discovery-only") != "true"
        or labels.get("org.opencontainers.image.revision") != EXPECTED_SOURCE["revision"]
        or labels.get("org.cotcodec.source-tree") != EXPECTED_SOURCE["tree"]
        or labels.get("org.cotcodec.source-archive-sha256")
        != EXPECTED_SOURCE["git_archive_tar_sha256"]
        or labels.get("org.cotcodec.doctor-sha256") != _sha(files["doctor.rs"])
        or report.get("image", {}).get("image_id") != IMAGE_ID
        or report.get("image", {}).get("inspect_sha256")
        != _sha(files["image-inspect.json"])
    ):
        raise EvidenceError("Shodh image provenance drifted")

    repeats: list[dict[str, Any]] = []
    for repeat in (1, 2):
        payload = _strict_json(files[f"repeat-{repeat}.json"], f"repeat-{repeat}.json")
        _validate_repeat(payload, repeat)
        raw = files[f"repeat-{repeat}.txt"]
        marker = b"COTCODEC_SHODH_REPORT=" + _canonical(payload)
        if raw.count(b"COTCODEC_SHODH_REPORT=") != 1 or marker not in raw:
            raise EvidenceError(f"Shodh repeat {repeat} raw receipt drifted")
        repeats.append(payload)
    if repeats[0] != repeats[1] or repeats[0] != report.get("projection"):
        raise EvidenceError("Shodh clean-state projections drifted")
    if _sha(_canonical(repeats[0])) != STABLE_PROJECTION_SHA256:
        raise EvidenceError("Shodh stable projection digest drifted")
    return {
        "image_id": IMAGE_ID,
        "projection": repeats[0],
        "report_sha256": _sha(files["report.json"]),
        "manifest_sha256": _sha(files["manifest.json"]),
    }


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular Shodh evidence bundle: {path}")
    bundle = _strict_json(path.read_bytes(), "Shodh evidence bundle")
    if (
        bundle.get("schema_version") != 1
        or bundle.get("evidence_kind") != "native-negative-reproduction"
        or bundle.get("source_id") != "shodh-memory"
        or bundle.get("evidence_grade") != "local-negative-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("h100_admission") != "forbidden-for-this-revision"
        or bundle.get("runtime_lane") != RUNTIME_LANE
        or bundle.get("run_count") != 2
        or bundle.get("source_revisions")
        != {
            "https://github.com/varun29ankuS/shodh-memory": EXPECTED_SOURCE[
                "revision"
            ]
        }
    ):
        raise EvidenceError("Shodh top-level evidence contract drifted")
    verified = validate_files(_decode_files(bundle.get("files")))
    expected_boundary = {
        "active_caches_survive_restart": False,
        "disjoint_residency_demonstrated": False,
        "h100_actor_admission": "forbidden-for-this-revision",
        "memory_quality_measured": False,
        "offline_aged_session_promotion": False,
        "physical_erasure_proven": False,
        "unique_forget_count": False,
    }
    if (
        bundle.get("shared_image_id") != verified["image_id"]
        or bundle.get("stable_projection") != verified["projection"]
        or bundle.get("stable_projection_sha256") != STABLE_PROJECTION_SHA256
        or bundle.get("report_sha256") != verified["report_sha256"]
        or bundle.get("manifest_sha256") != verified["manifest_sha256"]
        or bundle.get("claim_boundary") != expected_boundary
    ):
        raise EvidenceError("Shodh evidence receipt drifted")
    return bundle


def seal(root: Path) -> dict[str, Any]:
    paths = {
        **CODE_PATHS,
        "experiment.yaml": root / "experiment.yaml",
        "image-inspect.json": root / "image-inspect.json",
        "manifest.json": root / "manifest.json",
        "report.json": root / "report.json",
        **{f"source/{name}": root / "source" / name for name in SOURCE_NAMES},
        **{
            f"repeat-{repeat}.{suffix}": root / f"repeat-{repeat}.{suffix}"
            for repeat in (1, 2)
            for suffix in ("json", "txt")
        },
    }
    files = {name: path.read_bytes() for name, path in paths.items()}
    verified = validate_files(files)
    return {
        "schema_version": 1,
        "evidence_kind": "native-negative-reproduction",
        "source_id": "shodh-memory",
        "source_revisions": {
            "https://github.com/varun29ankuS/shodh-memory": EXPECTED_SOURCE["revision"]
        },
        "evidence_grade": "local-negative-reproduced",
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_admission": "forbidden-for-this-revision",
        "runtime_lane": RUNTIME_LANE,
        "run_count": 2,
        "shared_image_id": verified["image_id"],
        "stable_projection": verified["projection"],
        "stable_projection_sha256": STABLE_PROJECTION_SHA256,
        "report_sha256": verified["report_sha256"],
        "manifest_sha256": verified["manifest_sha256"],
        "claim_boundary": {
            "active_caches_survive_restart": False,
            "disjoint_residency_demonstrated": False,
            "h100_actor_admission": "forbidden-for-this-revision",
            "memory_quality_measured": False,
            "offline_aged_session_promotion": False,
            "physical_erasure_proven": False,
            "unique_forget_count": False,
        },
        "files": {name: _capture(path) for name, path in paths.items()},
    }


def _write_no_replace(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise EvidenceError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        bundle = validate_evidence(args.output.resolve())
    else:
        bundle = seal(args.root.resolve())
        _write_no_replace(args.output.resolve(), _canonical(bundle) + b"\n")
        bundle = validate_evidence(args.output.resolve())
    print(f"Shodh tier-admission evidence PASS: {bundle['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
