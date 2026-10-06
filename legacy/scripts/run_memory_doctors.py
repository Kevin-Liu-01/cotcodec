#!/usr/bin/env python3
"""Run the offline memory research doctors in one fixed, auditable process tree."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    commands = (
        (sys.executable, "-m", "compileall", "-q", "harness", "scripts", "tests"),
        (sys.executable, "scripts/validate_memory_sources.py"),
        (sys.executable, "scripts/validate_memory_experiments.py"),
        (sys.executable, "scripts/validate_provider_models.py"),
        (sys.executable, "scripts/validate_memory_source_contract.py"),
        (sys.executable, "scripts/validate_memory_persistent_transport.py"),
    )
    receipts: list[dict[str, object]] = []
    environment = os.environ.copy()
    environment["PYTHONPYCACHEPREFIX"] = "/tmp/cotcodec-pyc"
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        receipt = {
            "argv": list(command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        receipts.append(receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)
        if completed.returncode != 0:
            print(
                json.dumps(
                    {"schema_version": 1, "status": "FAIL", "commands": receipts},
                    sort_keys=True,
                ),
                flush=True,
            )
            return completed.returncode
    print(
        json.dumps(
            {"schema_version": 1, "status": "PASS", "commands": receipts},
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
