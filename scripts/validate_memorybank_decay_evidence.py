#!/usr/bin/env python3
"""Validate the retained clean-room MemoryBank control evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_STATUS = "MEMORYBANK_CORRECTED_DECAY_CONTROL_ADMITTED"
EXPECTED_REVISION = "cf61c4196e4cfdb0f2b7a0316249fa40312dc3a9"
EXPECTED_IMAGE_ID = (
    "sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7"
)
EXPECTED_BUNDLE_SHA256S = {
    "corrected.json": "468540a3e8bcb44d223ce1aee8abd4c06726d450d2e9af6e03632eb689b3f2f8",
    "no-decay.json": "6bf74611d01fe3cdf9a6cf139a01a9285ce766da844003bf84c5977b05ac4664",
    "upstream-precedence.json": (
        "02ff175501ff0ee28f0ee9e5c723a32299f16d400bfe636d3a8771477cec040f"
    ),
}


class MemoryBankEvidenceError(ValueError):
    """Raised when retained MemoryBank evidence drifts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(data: bytes, owner: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MemoryBankEvidenceError(f"{owner}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise MemoryBankEvidenceError(f"{owner}: expected object")
    return value


def _load_bound_files(
    root: Path, artifact_root: str, receipts: Any, expected_names: set[str]
) -> dict[str, bytes]:
    directory = root / artifact_root
    if directory.is_symlink() or not directory.is_dir() or not isinstance(receipts, dict):
        raise MemoryBankEvidenceError("artifact root or receipt roster is invalid")
    if set(receipts) != expected_names:
        raise MemoryBankEvidenceError("artifact roster drifted")
    loaded: dict[str, bytes] = {}
    for name, digest in receipts.items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise MemoryBankEvidenceError(f"artifact missing: {name}")
        loaded[name] = path.read_bytes()
        if _sha(loaded[name]) != digest:
            raise MemoryBankEvidenceError(f"artifact drifted: {name}")
    return loaded


def validate_memorybank_decay_evidence(
    bundle_or_path: dict[str, Any] | Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_or_path, Path):
        bundle = _object(bundle_or_path.read_bytes(), "MemoryBank evidence")
        root = project_root or bundle_or_path.resolve().parents[3]
    else:
        bundle = bundle_or_path
        if project_root is None:
            raise MemoryBankEvidenceError("project_root is required")
        root = project_root
    if (
        bundle.get("schema_version") != 1
        or bundle.get("source_id") != "memorybank-siliconfriend"
        or bundle.get("source_revisions")
        != {
            "https://github.com/zhongwanjun/MemoryBank-SiliconFriend": (
                EXPECTED_REVISION
            )
        }
        or bundle.get("evidence_kind")
        != "clean-room-mechanism-control-conformance"
        or bundle.get("evidence_grade") != "local-conformance-reproduced"
        or bundle.get("status") != EXPECTED_STATUS
        or bundle.get("scientific_result") is not False
        or bundle.get("publication_ready") is not False
        or bundle.get("upstream_code_imported") is not False
        or bundle.get("h100_actor_admission") != "bounded-discovery-screen"
    ):
        raise MemoryBankEvidenceError("evidence identity drifted")

    code_files = bundle.get("code_files")
    if not isinstance(code_files, dict) or not code_files:
        raise MemoryBankEvidenceError("code receipt roster is missing")
    for name, digest in code_files.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != digest:
            raise MemoryBankEvidenceError(f"code receipt drifted: {name}")

    cpu = bundle.get("cpu_doctor")
    frozen = bundle.get("frozen_controls")
    if not isinstance(cpu, dict) or not isinstance(frozen, dict):
        raise MemoryBankEvidenceError("CPU/frozen evidence sections are missing")
    cpu_files = _load_bound_files(
        root,
        cpu.get("artifact_root", ""),
        cpu.get("files"),
        {
            "doctor.py",
            "experiment.yaml",
            "image-inspect.json",
            "manifest.json",
            "memorybank_decay.py",
            "repeat-1.json",
            "repeat-2.json",
            "report.json",
        },
    )
    report = _object(cpu_files["report.json"], "CPU report")
    repeat_1 = _object(cpu_files["repeat-1.json"], "CPU repeat 1")
    repeat_2 = _object(cpu_files["repeat-2.json"], "CPU repeat 2")
    if (
        report.get("status") != "MEMORYBANK_CORRECTED_DECAY_CONTRACT_PASS"
        or report.get("run_count") != 2
        or report.get("image_id") != EXPECTED_IMAGE_ID
        or report.get("report_sha256") != _sha(cpu_files["repeat-1.json"])
        or cpu_files["repeat-1.json"] != cpu_files["repeat-2.json"]
        or repeat_1 != repeat_2
        or not all(repeat_1.get("checks", {}).values())
        or repeat_1.get("source", {}).get("upstream_code_imported") is not False
    ):
        raise MemoryBankEvidenceError("CPU doctor semantics drifted")
    inspected = json.loads(cpu_files["image-inspect.json"])
    image = inspected[0] if isinstance(inspected, list) and len(inspected) == 1 else {}
    if (
        image.get("Id") != EXPECTED_IMAGE_ID
        or image.get("Architecture") != "arm64"
        or image.get("Os") != "linux"
    ):
        raise MemoryBankEvidenceError("CPU image provenance drifted")

    frozen_files = _load_bound_files(
        root,
        frozen.get("artifact_root", ""),
        frozen.get("files"),
        {"corrected.json", "no-decay.json", "upstream-precedence.json", "contrast-report.json"},
    )
    for name, expected in EXPECTED_BUNDLE_SHA256S.items():
        payload = _object(frozen_files[name], name)
        if payload.get("bundle_sha256") != expected:
            raise MemoryBankEvidenceError(f"frozen semantic digest drifted: {name}")
    contrast = _object(frozen_files["contrast-report.json"], "contrast report")
    if (
        contrast.get("status") != "MEMORYBANK_FROZEN_CONTROL_CONTRAST_PASS"
        or contrast.get("task_count") != 200
        or contrast.get("candidate_served_on_all_serve_storage_and_service")
        != {"corrected": 22, "no_decay": 200, "upstream_precedence": 0}
        or not all(contrast.get("gates", {}).values())
    ):
        raise MemoryBankEvidenceError("frozen contrast semantics drifted")
    return bundle


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    evidence = validate_memorybank_decay_evidence(
        root / "research/evidence/memory/memorybank-corrected-decay-v1.json",
        project_root=root,
    )
    print(evidence["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
