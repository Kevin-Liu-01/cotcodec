#!/usr/bin/env python3
"""Compare two sealed lifecycle runs and bind cross-runtime semantic equivalence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.run_memory_lifecycle_contract import (  # noqa: E402
    LifecycleRunError,
    load_and_validate_output,
)

SEMANTIC_FILENAMES = (
    "experiment.yaml",
    "plans.jsonl",
    "traces.jsonl",
    "restore-traces.jsonl",
    "case-results.jsonl",
    "checkpoint-audit.json",
    "isolation-purge-audit.json",
    "costs-by-phase.json",
)


def _sha256_bytes(encoded: bytes) -> str:
    return hashlib.sha256(encoded).hexdigest()


def _read_report(root: Path) -> dict[str, Any]:
    try:
        report = json.loads((root / "report.json").read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleRunError(f"cannot read validated lifecycle report: {root}") from exc
    if not isinstance(report, dict):
        raise LifecycleRunError("validated lifecycle report must be an object")
    return report


def compare_lifecycle_outputs(left: Path, right: Path) -> dict[str, Any]:
    left_manifest = load_and_validate_output(left)
    right_manifest = load_and_validate_output(right)
    left_report = _read_report(left)
    right_report = _read_report(right)
    files: dict[str, dict[str, str | int | bool]] = {}
    for filename in SEMANTIC_FILENAMES:
        left_bytes = (left / filename).read_bytes()
        right_bytes = (right / filename).read_bytes()
        files[filename] = {
            "left_sha256": _sha256_bytes(left_bytes),
            "right_sha256": _sha256_bytes(right_bytes),
            "left_size": len(left_bytes),
            "right_size": len(right_bytes),
            "byte_equal": left_bytes == right_bytes,
        }
    gates = {
        "experiment_identity_equal": (
            left_manifest["experiment_sha256"] == right_manifest["experiment_sha256"]
        ),
        "code_identity_equal": (
            left_manifest["code_root_sha256"] == right_manifest["code_root_sha256"]
        ),
        "semantic_artifacts_byte_equal": all(
            bool(receipt["byte_equal"]) for receipt in files.values()
        ),
        "case_and_trace_roots_equal": left_report.get("roots") == right_report.get("roots"),
        "aggregate_gates_equal": left_report.get("gates") == right_report.get("gates"),
        "runtime_profiles_distinct": (
            left_report.get("runtime") != right_report.get("runtime")
        ),
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "PASS" if all(gates.values()) else "FAIL",
        "scientific_result": False,
        "publication_ready": False,
        "reason": (
            "cross-runtime determinism evidence for the reference lifecycle contract; "
            "not native-system or model-quality evidence"
        ),
        "left": {
            "path": str(left),
            "manifest_sha256": left_manifest["manifest_sha256"],
            "runtime_receipt": left_report.get("runtime_receipt"),
        },
        "right": {
            "path": str(right),
            "manifest_sha256": right_manifest["manifest_sha256"],
            "runtime_receipt": right_report.get("runtime_receipt"),
        },
        "semantic_files": files,
        "gates": gates,
        "comparator_code_sha256": _sha256_bytes(Path(__file__).read_bytes()),
    }
    payload["comparison_sha256"] = sha256_text(canonical_json(payload))
    return payload


def _write_once(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(encoded)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise LifecycleRunError("short write while sealing lifecycle comparison")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    result = compare_lifecycle_outputs(args.left.resolve(), args.right.resolve())
    _write_once(args.output.expanduser(), result)
    print(json.dumps(result, sort_keys=True))
    return 2 if args.require_gates and result["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
