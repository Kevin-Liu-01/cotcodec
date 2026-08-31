#!/usr/bin/env python3
"""Seal the protocol-v2 structural JSON CPU admission."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.run_state import canonical_json  # noqa: E402
from scripts import run_orchvar_iterative_structural_cpu_admission as admission  # noqa: E402
from scripts import seal_orchvar_iterative_cpu_admission as base  # noqa: E402

DEFAULT_RUN_ROOT = admission.DEFAULT_OUTPUT
STATUS = admission.STATUS
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-iterative-structural-json-v2-cpu-admission.json"
)


def seal_evidence(
    root: Path = DEFAULT_RUN_ROOT, output: Path = DEFAULT_OUTPUT
) -> dict[str, Any]:
    previous = base.STATUS
    base.STATUS = STATUS
    try:
        return base.seal_evidence(root, output)
    finally:
        base.STATUS = previous


def validate_evidence(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    previous = base.STATUS
    base.STATUS = STATUS
    try:
        return base.validate_evidence(path)
    finally:
        base.STATUS = previous


def main() -> int:
    evidence = seal_evidence()
    validate_evidence()
    print(
        canonical_json(
            {
                "status": evidence["status"],
                "projection_sha256": evidence["projection_sha256"],
                "evidence_root_sha256": evidence["evidence_root_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
