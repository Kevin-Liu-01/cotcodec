from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.seal_lightmem2_context_paging_evidence import (
    DEFAULT_OUTPUT,
    EvidenceError,
    validate_evidence,
)
from scripts.validate_lightmem2_context_paging_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = PROJECT_ROOT / "infra/memory-baselines/lightmem2"


def test_registered_lightmem2_contract_is_cpu_only_and_falsifying() -> None:
    payload = validate_experiment_contract()
    assert payload["source"]["revision"] == (
        "dfc67e8bc9373ca5b31bb412298565c9d65b29b6"
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
            "native_scoped_purge_api_available",
            True,
            "falsification gates drifted",
        ),
        ("admission", "h100_actor", "allowed", "H100 admission drifted"),
    ],
)
def test_lightmem2_contract_drift_fails_closed(
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


def test_lightmem2_container_and_runner_are_locked_down() -> None:
    dockerfile = (BASELINE_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runner = (
        PROJECT_ROOT / "scripts/run_lightmem2_context_paging_doctor.py"
    ).read_text(encoding="utf-8")
    assert "USER 65532:65532" in dockerfile
    assert "pnpm install --frozen-lockfile" in dockerfile
    assert '"--network"' in runner and '"none"' in runner
    assert '"--read-only"' in runner
    assert '"--cap-drop"' in runner and '"ALL"' in runner
    assert "no-new-privileges" in runner
    assert '"--gpus"' not in runner
    assert "sudo" not in runner


def test_lightmem2_doctor_encodes_the_three_hard_falsifiers() -> None:
    doctor = (BASELINE_ROOT / "doctor.ts").read_text(encoding="utf-8")
    assert "resolveArchivePathAcrossSessions" in doctor
    assert "archive_filename_collision_reused_path" in doctor
    assert "first_key_resolved_to_second_payload" in doctor
    assert "native_scoped_purge_api_available" in doctor
    assert "plaintext_a_remains" in doctor


def test_direct_lightmem2_entrypoints_load() -> None:
    commands = (
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/validate_lightmem2_context_paging_experiment.py"),
        ],
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_lightmem2_context_paging_doctor.py"),
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


def test_retained_lightmem2_negative_recomputes() -> None:
    evidence = validate_evidence()
    projection = evidence["stable_projection"]
    assert evidence["status"] == EXPECTED_STATUS
    assert evidence["run_count"] == 2
    assert projection["prepare"]["archive_before_stub_succeeded"] is True
    assert projection["prepare"]["first_key_resolved_to_second_payload"] is True
    assert (
        projection["restart"][
            "restart_unscoped_mcp_resolver_disclosed_b_to_any_caller"
        ]
        is True
    )
    assert projection["purge"]["native_scoped_purge_api_available"] is False
    assert evidence["h100_admission"] == "forbidden-for-this-revision"


def test_retained_lightmem2_negative_rejects_favorable_rewrite(
    tmp_path: Path,
) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    receipt = evidence["files"]["repeat-1/purge-probe.json"]
    purge = json.loads(base64.b64decode(receipt["content_base64"]))
    purge["native_scoped_purge_api_available"] = True
    purge["plaintext_a_remains"] = False
    rewritten = (json.dumps(purge, indent=2, sort_keys=True) + "\n").encode()
    receipt["content_base64"] = base64.b64encode(rewritten).decode("ascii")
    receipt["bytes"] = len(rewritten)
    receipt["sha256"] = hashlib.sha256(rewritten).hexdigest()
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(EvidenceError, match="artifact digest drifted"):
        validate_evidence(path)
