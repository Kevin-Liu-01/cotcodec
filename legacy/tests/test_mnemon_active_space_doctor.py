from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.seal_mnemon_active_space_evidence import validate_evidence
from scripts.validate_mnemon_active_space_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = PROJECT_ROOT / "infra/memory-baselines/mnemon"


def test_registered_mnemon_contract_is_cpu_only_and_bounded() -> None:
    payload = validate_experiment_contract()
    assert payload["sources"]["mnemon"]["revision"] == (
        "88d2981edeb18a5ebe048af472f6f96527615454"
    )
    assert payload["sources"]["dsh_mnemon"]["revision"] == (
        "1889c68400e52a391ee9a6eedf15bf44bc39dd06"
    )
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["runtime"]["runtime_network"] == "none"
    assert payload["admission_gates"]["expected_status"] == EXPECTED_STATUS
    assert payload["admission_gates"]["learned_bidirectional_paging_claim"] == (
        "forbidden"
    )


@pytest.mark.parametrize(
    ("section", "field", "replacement", "message"),
    [
        ("sources", "mnemon", {}, "source contract drifted"),
        ("runtime", "gpu_count", 1, "runtime contract drifted"),
        (
            "admission_gates",
            "physical_item_erasure_claim",
            "allowed",
            "admission gates drifted",
        ),
        ("admission", "scientific_claim", "allowed", "admission boundary drifted"),
    ],
)
def test_mnemon_contract_drift_fails_closed(
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


def test_mnemon_container_and_doctor_are_locked_down() -> None:
    dockerfile = (BASELINE_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runner = (PROJECT_ROOT / "scripts/run_mnemon_active_space_doctor.py").read_text(
        encoding="utf-8"
    )
    doctor = (BASELINE_ROOT / "doctor.mjs").read_text(encoding="utf-8")
    assert "USER 65532:65532" in dockerfile
    assert "go build -mod=readonly" in dockerfile
    assert "pnpm install --frozen-lockfile" in dockerfile
    assert '"--network"' in runner and '"none"' in runner
    assert '"--read-only"' in runner
    assert '"--cap-drop"' in runner and '"ALL"' in runner
    assert "no-new-privileges" in runner
    assert '"--gpus"' not in runner
    assert "sudo" not in runner
    assert "plugin_active_set_limits_default_recall" in doctor
    assert "core_soft_forget_hides_but_preserves_row" in doctor


def test_direct_mnemon_entrypoints_load() -> None:
    for command in (
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/validate_mnemon_active_space_experiment.py"),
        ],
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_mnemon_active_space_doctor.py"),
            "--help",
        ],
    ):
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr


def test_retained_mnemon_admission_recomputes() -> None:
    evidence = validate_evidence()
    assert evidence["status"] == EXPECTED_STATUS
    assert evidence["run_count"] == 2
    assert evidence["stable_projection"]["checks"][
        "plugin_active_set_limits_default_recall"
    ]
    assert evidence["claim_boundary"]["soft_delete_retains_plaintext"]
    assert evidence["claim_boundary"]["item_physical_erasure_demonstrated"] is False
    assert evidence["h100_admission"] == "bounded-static-selection-cell-only"
