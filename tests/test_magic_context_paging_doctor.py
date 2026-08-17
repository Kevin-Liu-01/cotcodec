from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.run_magic_context_paging_doctor import _stable_projection
from scripts.validate_magic_context_paging_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCTOR_ROOT = PROJECT_ROOT / "infra" / "memory-baselines" / "magic-context"


def test_registered_magic_context_contract_is_valid() -> None:
    payload = validate_experiment_contract()
    assert payload["source"]["revision"] == (
        "13e1d4c3fa3803ba1f4595029d8c4750dc9bef98"
    )
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["expected_falsification"]["status"] == EXPECTED_STATUS
    assert payload["admission"]["semantic_memory_h100"] == (
        "forbidden-for-this-mechanism"
    )


@pytest.mark.parametrize(
    ("section", "field", "replacement", "message"),
    [
        ("source", "revision", "0" * 40, "source contract drifted"),
        ("runtime", "runtime_network", "bridge", "runtime field runtime_network drifted"),
        ("intervention", "model_calls", 1, "intervention model_calls drifted"),
        ("admission", "portable_lifecycle", "allowed", "admission contract drifted"),
    ],
)
def test_magic_context_contract_drift_fails_closed(
    tmp_path: Path,
    section: str,
    field: str,
    replacement: object,
    message: str,
) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload[section][field] = replacement
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        validate_experiment_contract(path)


def test_magic_context_doctor_encodes_projection_and_negative_boundaries() -> None:
    doctor = (DOCTOR_ROOT / "doctor.ts").read_text(encoding="utf-8")
    dockerfile = (DOCTOR_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "renderDecayedCompartments" in doctor
    assert "renderMessageByOrdinal" in doctor
    assert "reasoning_stripped" in doctor
    assert "same_session_id_cross_harness_alias_reproduced" in doctor
    assert "physical_zero_residue" in doctor
    assert "host_row_deletion_makes_expansion_unrecoverable" in doctor
    assert "bun install --frozen-lockfile --ignore-scripts" in dockerfile
    assert "USER 65532:65532" in dockerfile


def test_stable_projection_retains_paging_alias_and_residue_findings() -> None:
    run = {
        "prepare": {
            "result": {
                "projection": {
                    "paging": {"tight_omits_oldest": True},
                    "expansion": {"reasoning_stripped": True},
                    "raw_db_unchanged": True,
                }
            }
        },
        "alias": {"result": {"same_session_id_cross_harness_alias_reproduced": True}},
        "purge": {
            "result": {
                "plugin_logical_session_a_rows": 0,
                "session_b_rows": 1,
                "host_row_deletion_makes_expansion_unrecoverable": True,
                "native_secure_purge_supported": False,
                "physical_zero_residue": False,
                "physical_hits": [{"file": "context.db", "canary_sha256": "a" * 64}],
            }
        },
    }
    projection = _stable_projection(run)
    assert projection["paging"] == {"tight_omits_oldest": True}
    assert projection["alias"]["same_session_id_cross_harness_alias_reproduced"] is True
    assert projection["purge"]["physical_zero_residue"] is False


def test_direct_validator_entrypoint_loads() -> None:
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts/validate_magic_context_paging_experiment.py")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "contract PASS" in completed.stdout


def test_direct_doctor_entrypoint_loads_without_package_install() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_magic_context_paging_doctor.py"),
            "--help",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--output" in completed.stdout
