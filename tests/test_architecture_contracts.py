from __future__ import annotations

import copy
from pathlib import Path

import yaml

from scripts.fetch_open_model import DEFAULT_REGISTRY, load_registry
from scripts.validate_architecture_experiments import validate_contract

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = PROJECT_ROOT / "experiments" / "architectures"


def load_contract(name: str) -> dict:
    return yaml.safe_load((CONTRACT_ROOT / name).read_text(encoding="utf-8"))


def known_models() -> set[str]:
    return set(load_registry(DEFAULT_REGISTRY)["models"])


def test_all_architecture_contracts_validate() -> None:
    paths = sorted(CONTRACT_ROOT.glob("*.yaml"))
    assert paths
    for path in paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert validate_contract(payload, known_models()) == [], path


def test_causal_claim_requires_matched_from_scratch_arm() -> None:
    payload = copy.deepcopy(load_contract("coded-delta-memory.yaml"))
    payload["starting_point"]["arms"] = [
        arm
        for arm in payload["starting_point"]["arms"]
        if arm["mode"] != "matched-from-scratch"
    ]
    errors = validate_contract(payload, known_models())
    assert "architecture-causal claims require a matched-from-scratch arm" in errors


def test_disabled_contract_cannot_masquerade_as_runnable() -> None:
    payload = copy.deepcopy(load_contract("portable-sidecar-update.yaml"))
    payload["readiness"] = "pilot-ready"
    payload["execution"]["enabled"] = True
    errors = validate_contract(payload, known_models())
    assert any("digest-pinned container_image" in error for error in errors)
    assert any("require command_argv" in error for error in errors)
    assert any("require model receipts" in error for error in errors)


def test_reference_doctor_must_bind_real_implementation_and_command() -> None:
    payload = copy.deepcopy(load_contract("translation-equivariant-byte-patches.yaml"))
    payload["reference_doctor"]["implementation"] = "harness/does-not-exist.py"
    payload["reference_doctor"]["command_argv"] = []
    errors = validate_contract(payload, known_models())
    assert "reference_doctor.implementation must exist in the repo" in errors
    assert "reference_doctor.command_argv must be a non-empty argv list" in errors


def test_stage0_reference_command_script_must_exist() -> None:
    payload = copy.deepcopy(load_contract("causal-memory-holdout.yaml"))
    payload["stage0_reference"]["command_argv"][3] = "scripts/missing.py"
    errors = validate_contract(payload, known_models())
    assert "stage0_reference.command_argv script must exist" in errors
