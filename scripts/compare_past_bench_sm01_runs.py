#!/usr/bin/env python3
"""Compare one uninterrupted and one fresh-resume PAST SM01 discovery run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_STATUS = {
    "uninterrupted": {"PAST_SM01_UNINTERRUPTED_PASS"},
    "fresh-job-resume": {
        "PAST_SM01_FRESH_RESUME_PASS",
        "PAST_SM01_FRESH_RESUME_RECOVERED_AFTER_DOCTOR_FIX",
    },
}


class ComparisonError(ValueError):
    """Raised when a PAST recovery artifact is absent, unsafe, or inconsistent."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _root(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ComparisonError(f"artifact must be a regular non-symlink file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ComparisonError(f"{label} must be a regular non-symlink file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ComparisonError(f"{label} must contain one JSON object")
    return value


def _raw_trace_manifest(trace_root: Path) -> list[dict[str, Any]]:
    if not trace_root.is_dir() or trace_root.is_symlink():
        raise ComparisonError("trace root must be a regular directory")
    rows: list[dict[str, Any]] = []
    for path in sorted(trace_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ComparisonError("trace tree contains a symlink")
        if not path.is_file():
            continue
        relative = PurePosixPath(path.relative_to(trace_root).as_posix())
        if relative.is_absolute() or any(
            part in {"", ".", ".."} for part in relative.parts
        ):
            raise ComparisonError("trace tree contains an unsafe path")
        rows.append(
            {
                "path": relative.as_posix(),
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    if not rows:
        raise ComparisonError("trace tree is empty")
    return rows


def _load_cell(root: Path, mode: str) -> dict[str, Any]:
    if not root.is_dir() or root.is_symlink():
        raise ComparisonError(f"{mode} root must be a regular directory")
    root = root.resolve()
    evidence = root / "evidence"
    run = root / "run"
    if (
        not evidence.is_dir()
        or evidence.is_symlink()
        or not run.is_dir()
        or run.is_symlink()
    ):
        raise ComparisonError(f"{mode} evidence or run directory is unsafe")
    receipt = _read_object(
        evidence / f"run-receipt-{mode}.json", f"{mode} run receipt"
    )
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if (
        receipt.get("receipt_sha256") != _root(unsigned)
        or receipt.get("mode") != mode
        or receipt.get("status") not in EXPECTED_STATUS[mode]
        or receipt.get("scientific_result") is not False
        or receipt.get("publication_ready") is not False
        or receipt.get("external_attestation") is not False
    ):
        raise ComparisonError(f"{mode} run receipt drifted")
    if receipt.get("status") == "PAST_SM01_FRESH_RESUME_RECOVERED_AFTER_DOCTOR_FIX" and (
        not isinstance(receipt.get("validation_slurm_job_id"), int)
        or isinstance(receipt.get("validation_slurm_job_id"), bool)
        or receipt["validation_slurm_job_id"] <= 0
        or receipt["validation_slurm_job_id"] == receipt.get("slurm_job_id")
        or receipt.get("recovery_reason")
        != "validator-counted-registered-reflection-as-primary-episode"
    ):
        raise ComparisonError("fresh-job-resume recovery receipt drifted")
    identity = _read_object(evidence / "execution-identity.json", f"{mode} identity")
    preflight = _read_object(
        evidence / f"preflight-{mode}.json", f"{mode} preflight"
    )
    if (
        preflight.get("mode") != mode
        or preflight.get("slurm_job_id") != receipt.get("slurm_job_id")
        or preflight.get("execution_identity_sha256") != _root(identity)
    ):
        raise ComparisonError(f"{mode} preflight and final receipt differ")
    projection = _read_object(
        evidence / f"trace-projection-{mode}.json", f"{mode} trace projection"
    )
    if (
        projection.get("projection_root_sha256")
        != receipt.get("trace_projection_root_sha256")
        or projection.get("trace_count") != receipt.get("trace_count")
    ):
        raise ComparisonError(f"{mode} trace projection drifted")
    result_roots = receipt.get("sequence_result_sha256")
    if not isinstance(result_roots, dict) or set(result_roots) != {
        "with_persistence",
        "without_persistence",
    }:
        raise ComparisonError(f"{mode} sequence-result roster drifted")
    for variant, expected in result_roots.items():
        path = run / "traces" / variant / "sequence_results.json"
        if _sha256(path) != expected:
            raise ComparisonError(f"{mode} {variant} result bytes drifted")
    raw_manifest = _raw_trace_manifest(run / "traces")
    return {
        "root": str(root),
        "identity": identity,
        "identity_sha256": _root(identity),
        "receipt": receipt,
        "receipt_file_sha256": _sha256(
            evidence / f"run-receipt-{mode}.json"
        ),
        "projection_root_sha256": projection["projection_root_sha256"],
        "sequence_result_sha256": result_roots,
        "raw_trace_manifest": raw_manifest,
        "raw_trace_root_sha256": _root(raw_manifest),
    }


def compare_runs(*, uninterrupted: Path, resumed: Path) -> dict[str, Any]:
    left = _load_cell(uninterrupted, "uninterrupted")
    right = _load_cell(resumed, "fresh-job-resume")
    gates = {
        "execution_identity_equal": left["identity"] == right["identity"],
        "fresh_slurm_job": left["receipt"]["slurm_job_id"]
        != right["receipt"]["slurm_job_id"],
        "deterministic_projection_equal": left["projection_root_sha256"]
        == right["projection_root_sha256"],
        "sequence_result_bytes_equal": left["sequence_result_sha256"]
        == right["sequence_result_sha256"],
    }
    raw_equal = left["raw_trace_manifest"] == right["raw_trace_manifest"]
    if not all(gates.values()):
        raise ComparisonError(f"PAST SM01 recovery equivalence failed: {gates}")
    report = {
        "schema_version": 1,
        "status": "PAST_SM01_RECOVERY_EQUIVALENCE_PASS",
        "scientific_result": False,
        "publication_ready": False,
        "gates": gates,
        "raw_trace_byte_equality": raw_equal,
        "raw_trace_byte_equality_required": False,
        "uninterrupted": {
            key: left[key]
            for key in (
                "root",
                "identity_sha256",
                "receipt_file_sha256",
                "projection_root_sha256",
                "sequence_result_sha256",
                "raw_trace_root_sha256",
            )
        },
        "fresh_job_resume": {
            key: right[key]
            for key in (
                "root",
                "identity_sha256",
                "receipt_file_sha256",
                "projection_root_sha256",
                "sequence_result_sha256",
                "raw_trace_root_sha256",
            )
        },
        "external_attestation": False,
    }
    report["report_sha256"] = _root(report)
    return report


def _write_once(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    payload = _canonical(value) + b"\n"
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uninterrupted", type=Path, required=True)
    parser.add_argument("--resumed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = compare_runs(
            uninterrupted=args.uninterrupted, resumed=args.resumed
        )
        _write_once(args.output.resolve(), report)
    except ComparisonError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
