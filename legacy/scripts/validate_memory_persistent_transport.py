#!/usr/bin/env python3
"""Exercise the long-lived memory sidecar transport without native backends."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    GeneratedMemoryTaskSource,
    PersistentSubprocessMemorySystem,
    run_memory_system,
)


def main() -> int:
    sidecar = PROJECT_ROOT / "scripts" / "run_reference_memory_sidecar.py"
    task = GeneratedMemoryTaskSource(seed=7, episode_count=4).load("memory-000002")
    system = PersistentSubprocessMemorySystem(
        (sys.executable, str(sidecar)), timeout_seconds=10
    )
    process_id = system.process_id
    first = run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    repeated = run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    semantic_match = [item.text for item in first.evidence] == [
        item.text for item in repeated.evidence
    ]
    same_process = system.process_id == process_id and system.is_running
    system.purge(task.session_id)
    system.close()
    stopped = not system.is_running
    gates = {
        "same_process_across_selects": same_process,
        "semantic_repeat_match": semantic_match,
        "purge_round_trip": True,
        "shutdown_stopped_process": stopped,
    }
    status = "PERSISTENT_TRANSPORT_PASS" if all(gates.values()) else "FAIL"
    print(
        json.dumps(
            {
                "schema_version": 1,
                "status": status,
                "scientific_result": False,
                "scope": "reference-sidecar-transport-only",
                "native_backend_persistence_proven": False,
                "gates": gates,
            },
            sort_keys=True,
        )
    )
    return 0 if status.endswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
