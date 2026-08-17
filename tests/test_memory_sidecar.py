from __future__ import annotations

import sys
from pathlib import Path

import pytest

from harness.memory_trials import (
    GeneratedMemoryTaskSource,
    MemorySidecarError,
    PersistentSubprocessMemorySystem,
    SubprocessMemorySystem,
    build_memory_system_request,
    run_memory_system,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SIDECAR = PROJECT_ROOT / "scripts" / "run_reference_memory_sidecar.py"


def test_reference_sidecar_runs_task_blind_contract_across_process() -> None:
    system = SubprocessMemorySystem((sys.executable, str(REFERENCE_SIDECAR)))
    task = GeneratedMemoryTaskSource(seed=7, episode_count=4).load("memory-000002")
    run = run_memory_system(
        system,
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    assert system.identity == "reference-memory-system-v2"
    assert run.receipt == system.receipt
    assert run.candidate_available_to_system is True
    assert run.candidate_served_to_actor is True
    assert run.costs.latency_ms > 0
    system.purge(task.session_id)


def test_sidecar_rejects_non_json_output(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.py"
    invalid.write_text("print('not-json')\n")
    with pytest.raises(MemorySidecarError, match="malformed JSON"):
        SubprocessMemorySystem((sys.executable, str(invalid)))


def test_persistent_reference_sidecar_reuses_one_process_and_closes() -> None:
    task = GeneratedMemoryTaskSource(seed=7, episode_count=4).load("memory-000002")
    system = PersistentSubprocessMemorySystem(
        (sys.executable, str(REFERENCE_SIDECAR)), timeout_seconds=10
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
    assert system.process_id == process_id
    assert system.is_running is True
    assert [item.text for item in first.evidence] == [
        item.text for item in repeated.evidence
    ]
    system.purge(task.session_id)
    system.close()
    assert system.is_running is False
    with pytest.raises(MemorySidecarError, match="closed"):
        system.select(
            build_memory_system_request(
                task,
                visibility="serve",
                treatment_mode="storage_and_service",
            )[0]
        )
