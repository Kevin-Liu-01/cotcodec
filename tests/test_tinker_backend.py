from __future__ import annotations

from pathlib import Path

import pytest

from harness.training.tinker_backend import TinkerExperimentContract, load_tinker_contract

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = PROJECT_ROOT / "experiments" / "tinker" / "capsule-policy-kimi.yaml"


def test_registered_kimi_contract_is_bounded_and_honest() -> None:
    contract = load_tinker_contract(CONTRACT)
    assert contract.execution.enabled is False
    assert contract.cost_ceiling_usd() <= contract.budget.max_usd
    assert {stage.tinker_id for stage in contract.stages} == {
        "Qwen/Qwen3.5-4B",
        "moonshotai/Kimi-K2.6",
    }
    assert contract.portability_claim.startswith("Only the external capsule")


def test_contract_rejects_understated_cost_ceiling() -> None:
    payload = load_tinker_contract(CONTRACT).model_dump(mode="json")
    payload["budget"]["max_usd"] = 1.0
    with pytest.raises(ValueError, match="above max_usd"):
        TinkerExperimentContract.model_validate(payload)


def test_enabled_contract_requires_data_and_execution_receipts() -> None:
    payload = load_tinker_contract(CONTRACT).model_dump(mode="json")
    payload["execution"]["enabled"] = True
    payload["execution"]["blocked_by"] = []
    with pytest.raises(ValueError, match="digest-pinned container"):
        TinkerExperimentContract.model_validate(payload)


def test_contract_forbids_secret_material() -> None:
    payload = load_tinker_contract(CONTRACT).model_dump(mode="json")
    payload["execution"]["api_key"] = "must-never-be-in-a-contract"
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        TinkerExperimentContract.model_validate(payload)
