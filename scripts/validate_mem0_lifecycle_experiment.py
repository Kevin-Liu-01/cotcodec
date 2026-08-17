#!/usr/bin/env python3
"""Validate the immutable Mem0 native lifecycle doctor contract."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import yaml

EXPECTED_SHA256 = "f9e77ea6997f1bc716240c0ec6416e54cb026a9ae78d5f8ecf479fcef25d5b42"
EXPECTED_ARTIFACTS = [
    "dockerfile",
    "experiment.yaml",
    "harness/memory_trials/lifecycle.py",
    "image-inspect.json",
    "infra/memory-baselines/mem0_lifecycle_sidecar.py",
    "infra/memory-baselines/mem0_sidecar.py",
    "run-1/manifest.json",
    "run-1/report.json",
    "run-1/stderr.txt",
    "run-1/stdout.txt",
    "run-2/manifest.json",
    "run-2/report.json",
    "run-2/stderr.txt",
    "run-2/stdout.txt",
    "scripts/run_mem0_lifecycle_doctor.py",
    "scripts/validate_mem0_lifecycle_experiment.py",
    "source-context.json",
]


def validate_experiment_contract(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Mem0 lifecycle experiment must be a regular YAML file")
    encoded = path.read_bytes()
    digest = hashlib.sha256(encoded).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Mem0 lifecycle experiment scientific contract drifted")
    payload = yaml.safe_load(encoded)
    if not isinstance(payload, dict):
        raise ValueError("Mem0 lifecycle experiment must be a mapping")
    if payload.get("schema_version") != 1:
        raise ValueError("Mem0 lifecycle experiment schema drifted")
    if payload.get("name") != "stage3-mem0-native-lifecycle-doctor":
        raise ValueError("Mem0 lifecycle experiment identity drifted")
    if payload.get("scientific_result") is not False:
        raise ValueError("Mem0 lifecycle doctor cannot claim a scientific result")
    if payload.get("execution", {}).get("h100_admission") != (
        "blocked-until-all-gates-crash-recovery-and-residue-clearance-pass"
    ):
        raise ValueError("Mem0 lifecycle H100 admission gate drifted")
    if payload.get("artifacts") != EXPECTED_ARTIFACTS:
        raise ValueError("Mem0 lifecycle artifact roster drifted")
    return digest


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "experiments/memory/stage3-mem0-native-lifecycle-doctor.yaml"
    )
    digest = validate_experiment_contract(path)
    print(f"Mem0 lifecycle experiment PASS: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
