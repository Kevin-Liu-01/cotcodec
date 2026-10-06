#!/usr/bin/env python3
"""Run the protocol-v2 structural JSON CPU admission."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.run_state import canonical_json  # noqa: E402
from scripts import run_orchvar_iterative_cpu_admission as base  # noqa: E402

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/results/orchvar-iterative/2026-08-26-cpu-structural-json-v2"
)
STATUS = "ORCHVAR_ITERATIVE_STRUCTURAL_JSON_V2_CPU_ADMISSION_PASS"


def run_proof(output: Path = DEFAULT_OUTPUT):
    previous = os.environ.get(base.STRUCTURAL_PROTOCOL_ENV)
    os.environ[base.STRUCTURAL_PROTOCOL_ENV] = "structural-json-v2"
    try:
        manifest = base.run_proof(output)
    finally:
        if previous is None:
            os.environ.pop(base.STRUCTURAL_PROTOCOL_ENV, None)
        else:
            os.environ[base.STRUCTURAL_PROTOCOL_ENV] = previous
    if manifest["status"] != STATUS:
        raise RuntimeError("structural CPU admission status drifted")
    return manifest


def main() -> int:
    manifest = run_proof()
    print(
        canonical_json(
            {
                "status": manifest["status"],
                "report_sha256": manifest["report_sha256"],
                "journal_root_sha256": manifest["journal_root_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
