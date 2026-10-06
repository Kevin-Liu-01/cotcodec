from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from scripts.verify_memory_baseline_sources import (
    DEFAULT_CONTRACT,
    BaselineSourceError,
    load_contract,
)


def test_stage2_contract_matches_registered_source_pins() -> None:
    contract = load_contract(DEFAULT_CONTRACT)
    assert set(contract["systems"]) == {"mem0", "graphiti", "langmem", "hindsight"}
    assert contract["estimands"]["never_pool_modes"] is True
    assert "gpt-oss-120b" in contract["actor_matrix"]["large_open_confirmation"]
    assert "kimi-k2.6" in contract["actor_matrix"]["frontier_confirmation"]
    assert contract["actor_matrix"]["maximum_secondary"] == ["claude-fable-5"]
    assert contract["analysis"]["model_by_memory_policy_interaction"] is True
    assert contract["protocol"]["native_request_fields"] == [
        "session_scope",
        "ordered_prefix_events",
        "query",
        "budget",
    ]
    assert contract["implementation_status"]["scientific_result"] is False
    assert contract["implementation_status"]["transport_status"] == {
        "memory_system_v1_persistent_reference_process": "implemented",
        "memory_lifecycle_v1_reference_contract": "implemented",
        "contained_cpu_reference_matrix": "pass-development-evidence",
        "cross_runtime_semantic_equivalence": "pass-development-evidence",
        "native_systems_migrated": False,
        "backend_state_verified": False,
    }
    assert (
        "backend_verified_purge_and_residue_inspection"
        in contract["implementation_status"]["blockers"]
    )
    lifecycle = contract["implementation_status"]["reference_lifecycle_evidence"]
    assert lifecycle["cases"] == 192
    assert lifecycle["capacity_cells"] == [2, 4, 8]
    assert lifecycle["publication_attested"] is False
    assert contract["lifecycle_protocol"]["fail_closed_on_missing_capability"] is True


def test_contract_refuses_revision_drift(tmp_path: Path) -> None:
    payload = copy.deepcopy(yaml.safe_load(DEFAULT_CONTRACT.read_text()))
    payload["systems"]["mem0"]["revision"] = "0" * 40
    contract = tmp_path / "contract.yaml"
    contract.write_text(yaml.safe_dump(payload, sort_keys=False))
    with pytest.raises(BaselineSourceError, match="differs from the source ledger"):
        load_contract(contract)


def test_contract_refuses_benchmark_stratum_on_native_wire(tmp_path: Path) -> None:
    payload = copy.deepcopy(yaml.safe_load(DEFAULT_CONTRACT.read_text()))
    payload["protocol"]["native_request_fields"].insert(1, "stratum")
    contract = tmp_path / "contract.yaml"
    contract.write_text(yaml.safe_dump(payload, sort_keys=False))
    with pytest.raises(BaselineSourceError, match="exclude benchmark stratum"):
        load_contract(contract)


def test_contract_cannot_promote_ephemeral_smokes_to_science(tmp_path: Path) -> None:
    payload = copy.deepcopy(yaml.safe_load(DEFAULT_CONTRACT.read_text()))
    payload["implementation_status"]["scientific_result"] = True
    contract = tmp_path / "contract.yaml"
    contract.write_text(yaml.safe_dump(payload, sort_keys=False))
    with pytest.raises(BaselineSourceError, match="cannot be labeled"):
        load_contract(contract)


def test_contract_refuses_reference_lifecycle_evidence_drift(tmp_path: Path) -> None:
    payload = copy.deepcopy(yaml.safe_load(DEFAULT_CONTRACT.read_text()))
    payload["implementation_status"]["reference_lifecycle_evidence"]["comparison_sha256"] = "0" * 64
    contract = tmp_path / "contract.yaml"
    contract.write_text(yaml.safe_dump(payload, sort_keys=False))
    with pytest.raises(BaselineSourceError, match="lifecycle evidence drifted"):
        load_contract(contract)
