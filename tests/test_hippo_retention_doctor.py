from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.run_hippo_retention_doctor import (
    DOCTOR_ROOT,
    PROJECT_ROOT,
    _stable_projection,
)
from scripts.validate_hippo_retention_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)


def test_registered_hippo_falsification_contract_is_valid() -> None:
    payload = validate_experiment_contract(DEFAULT_EXPERIMENT)
    assert payload["source"]["revision"] == (
        "4aeb04c68ff079ff1713c977ac4d2a96757cff44"
    )
    assert payload["runtime"]["runtime_network"] == "none"
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["expected_falsification"]["status"] == EXPECTED_STATUS
    assert payload["admission"]["active_inactive_h100"] == (
        "forbidden-for-this-revision"
    )


@pytest.mark.parametrize(
    ("section", "field", "replacement", "message"),
    [
        ("source", "revision", "0" * 40, "source contract drifted"),
        ("runtime", "runtime_network", "bridge", "runtime field runtime_network drifted"),
        ("intervention", "model_calls", 1, "intervention field model_calls drifted"),
        ("admission", "active_inactive_h100", "allowed", "H100 admission"),
    ],
)
def test_hippo_contract_drift_fails_closed(
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


def test_doctor_sources_encode_falsification_and_containment() -> None:
    dockerfile = (DOCTOR_ROOT / "Dockerfile").read_text(encoding="utf-8")
    doctor = (DOCTOR_ROOT / "doctor.mjs").read_text(encoding="utf-8")
    runner = (PROJECT_ROOT / "scripts/run_hippo_retention_doctor.py").read_text(
        encoding="utf-8"
    )
    assert "npm ci --ignore-scripts" in dockerfile
    assert "USER 65532:65532" in dockerfile
    assert "ANTHROPIC_API_KEY" in doctor
    assert "mixed_semantic_created" in doctor
    assert "plaintext_residue_reproduced" in doctor
    assert "working_memory_flush_to_archive" in doctor
    assert '"--network",\n        "none"' in runner
    assert '"--read-only"' in runner
    assert '"--cap-drop",\n        "ALL"' in runner
    assert '"no-new-privileges"' in runner
    assert '["sudo"' not in runner


def test_stable_projection_drops_process_specific_fields() -> None:
    run = {
        "prepare": {
            "result": {
                "forbidden_capabilities": {"active_inactive_paging": True},
                "sleep": {"merged": 3},
                "cross_tenant": {"mixed_semantic_created": True},
                "retention": {"positive_outcome_extends_retention": True},
                "projection": {"row_count": 5},
            }
        },
        "purge": {
            "result": {
                "working_memory_flush_count": 20,
                "working_memory_flush_archived": False,
                "logical_record_count": 0,
                "native_scoped_purge_available": False,
                "plaintext_residue_reproduced": True,
                "physical_hits": [{"file": "hippo.db", "canary_sha256": "a" * 64}],
            }
        },
    }
    projection = _stable_projection(run)
    assert projection["sleep"] == {"merged": 3}
    assert projection["purge"]["logical_record_count"] == 0


def test_direct_script_entrypoint_loads_without_package_install() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_hippo_retention_doctor.py"),
            "--help",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--output" in completed.stdout
