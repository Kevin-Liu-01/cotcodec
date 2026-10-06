from __future__ import annotations

import json

import pytest

from scripts.run_infini_memory_lifecycle_doctor import (
    DEFAULT_SOURCE,
    InfiniMemoryLifecycleRunnerError,
    _parse_phase,
    _source_contract,
)
from scripts.validate_infini_memory_lifecycle_experiment import (
    validate_experiment_contract,
)


def test_infini_memory_source_contract_binds_registered_exact_source() -> None:
    receipt = _source_contract(DEFAULT_SOURCE, validate_experiment_contract())
    assert receipt["revision"].startswith("ddac08e")
    assert all(receipt["static_source_checks"].values())


def test_infini_memory_phase_parser_rejects_false_check() -> None:
    payload = {
        "phase": 2,
        "checks": {"expected_falsifier": False},
        "metrics": {},
    }
    raw = (
        b"COTCODEC_INFINI_MEMORY_PHASE="
        + json.dumps(payload, separators=(",", ":")).encode()
        + b"\n"
    )
    with pytest.raises(InfiniMemoryLifecycleRunnerError, match="report drifted"):
        _parse_phase(raw, 2)
