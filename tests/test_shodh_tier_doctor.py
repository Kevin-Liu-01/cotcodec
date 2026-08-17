from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.seal_shodh_tier_evidence import (
    DEFAULT_OUTPUT,
    EvidenceError,
    validate_evidence,
)
from scripts.validate_shodh_tier_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = PROJECT_ROOT / "infra/memory-baselines/shodh"


def test_registered_shodh_contract_is_cpu_only_and_falsifying() -> None:
    payload = validate_experiment_contract()
    assert payload["source"]["revision"] == (
        "98c6e4861847a76f75eb880acf9e145d30794a46"
    )
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["runtime"]["runtime_network"] == "none"
    assert payload["expected_falsification"]["status"] == EXPECTED_STATUS
    assert payload["admission"]["h100_actor"] == "forbidden-for-this-revision"


@pytest.mark.parametrize(
    ("section", "field", "replacement", "message"),
    [
        ("source", "revision", "0" * 40, "source contract drifted"),
        ("runtime", "gpu_count", 1, "runtime contract drifted"),
        (
            "expected_falsification",
            "plaintext_residue_after_forget_all",
            True,
            "falsification gates drifted",
        ),
        ("admission", "h100_actor", "allowed", "admission contract drifted"),
    ],
)
def test_shodh_contract_drift_fails_closed(
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


def test_shodh_container_runner_and_doctor_are_locked_down() -> None:
    dockerfile = (BASELINE_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runner = (PROJECT_ROOT / "scripts/run_shodh_tier_doctor.py").read_text(
        encoding="utf-8"
    )
    doctor = (BASELINE_ROOT / "doctor.rs").read_text(encoding="utf-8")
    assert "USER 65532:65532" in dockerfile
    assert "cargo build --locked" in dockerfile
    assert "CARGO_BUILD_JOBS=1" in dockerfile
    assert '"--network"' in runner and '"none"' in runner
    assert '"--read-only"' in runner
    assert '"--cap-drop"' in runner and '"ALL"' in runner
    assert "no-new-privileges" in runner
    assert '"--gpus"' not in runner
    assert "sudo" not in runner
    assert "new_working_record_already_in_long_term_storage" in doctor
    assert "eligible_persisted_session_is_stranded_after_restart" in doctor
    assert "plaintext_residue_not_observed_after_forget_all" in doctor


def test_direct_shodh_entrypoints_load() -> None:
    commands = (
        [sys.executable, str(PROJECT_ROOT / "scripts/validate_shodh_tier_experiment.py")],
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_shodh_tier_doctor.py"),
            "--help",
        ],
    )
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr


def test_retained_shodh_negative_recomputes() -> None:
    evidence = validate_evidence()
    projection = evidence["stable_projection"]
    assert evidence["status"] == EXPECTED_STATUS
    assert evidence["run_count"] == 2
    assert projection["checks"]["new_working_record_already_in_long_term_storage"]
    assert projection["checks"]["restart_drops_active_caches"]
    assert projection["checks"][
        "eligible_persisted_session_is_stranded_after_restart"
    ]
    assert projection["observations"]["forget_all_returned"] == 2
    assert projection["observations"]["plaintext_residue"] is False
    assert evidence["claim_boundary"]["physical_erasure_proven"] is False
    assert evidence["h100_admission"] == "forbidden-for-this-revision"


def test_retained_shodh_negative_rejects_favorable_source_rewrite(
    tmp_path: Path,
) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    receipt = evidence["files"]["source/memory-mod.rs"]
    source = base64.b64decode(receipt["content_base64"])
    source = source.replace(
        b"self.long_term_memory.store(&memory)?;",
        b"/* favorable rewrite: persist only after promotion */",
        1,
    )
    receipt["content_base64"] = base64.b64encode(source).decode("ascii")
    receipt["bytes"] = len(source)
    receipt["sha256"] = hashlib.sha256(source).hexdigest()
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(EvidenceError, match="semantics drifted"):
        validate_evidence(path)
