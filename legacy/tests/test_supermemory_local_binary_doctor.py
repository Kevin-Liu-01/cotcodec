from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.run_supermemory_local_doctor import DOCTOR_ROOT, PROJECT_ROOT, _stable_projection
from scripts.validate_supermemory_local_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)


def test_registered_supermemory_binary_contract_is_valid() -> None:
    payload = validate_experiment_contract(DEFAULT_EXPERIMENT)
    assert payload["source"]["release_tag"] == "server-v0.0.3"
    assert payload["source"]["local_server_source_in_release_tree"] is False
    assert payload["runtime"]["runtime_network"] == "none"
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["expected_outcome"]["status"] == EXPECTED_STATUS
    assert payload["admission"]["memory_lifecycle_h100"] == (
        "forbidden-for-this-release"
    )


@pytest.mark.parametrize(
    ("section", "field", "replacement", "message"),
    [
        ("source", "release_revision", "0" * 40, "source contract drifted"),
        ("runtime", "runtime_network", "bridge", "runtime field runtime_network"),
        (
            "runtime",
            "local_base_image",
            "python@sha256:" + "1" * 64,
            "base image drifted",
        ),
        ("intervention", "model_calls", 1, "intervention drifted"),
        ("admission", "memory_lifecycle_h100", "allowed", "admission contract"),
    ],
)
def test_supermemory_contract_drift_fails_closed(
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


def test_supermemory_doctor_encodes_binary_only_containment() -> None:
    dockerfile = (DOCTOR_ROOT / "Dockerfile.binary-doctor").read_text(encoding="utf-8")
    doctor = (DOCTOR_ROOT / "doctor.py").read_text(encoding="utf-8")
    runner = (PROJECT_ROOT / "scripts/run_supermemory_local_doctor.py").read_text(
        encoding="utf-8"
    )
    assert 'org.cotcodec.evidence-role="binary-only-cpu-lifecycle-doctor"' in dockerfile
    assert "USER 65532:65532" in dockerfile
    assert '"OPENAI_BASE_URL": "http://127.0.0.1:1/v1"' in doctor
    assert "process.kill()" in doctor
    assert "native_tenant_scoped_physical_purge_available" in doctor
    assert '"--network",\n        "none"' in runner
    assert '"--read-only"' in runner
    assert '"--cap-drop",\n        "ALL"' in runner
    assert '"no-new-privileges"' in runner
    assert '["sudo"' not in runner
    assert 'not path.startswith("apps/docs/")' in runner


def test_stable_projection_ignores_random_receipt_fields() -> None:
    run = {
        "prepare": {"result": {"checks": {"direct_create": True}}},
        "restart": {
            "result": {
                "checks": {"crash_restart_exact_latest_state": True},
                "counts": {
                    "tenant_a_latest_after_sigkill": 0,
                    "tenant_b_latest_after_sigkill": 0,
                },
            }
        },
        "forget": {
            "result": {
                "checks": {"soft_forget_excludes_normal_search": True},
                "plaintext_hits": [],
                "response_sha256": "a" * 64,
                "state_manifest_sha256": "b" * 64,
            }
        },
    }
    assert _stable_projection(run) == {
        "prepare": {"direct_create": True},
        "restart": {
            "checks": {"crash_restart_exact_latest_state": True},
            "counts": {
                "tenant_a_latest_after_sigkill": 0,
                "tenant_b_latest_after_sigkill": 0,
            },
        },
        "forget": {
            "checks": {"soft_forget_excludes_normal_search": True},
            "plaintext_hits": [],
        },
    }


def test_direct_supermemory_runner_entrypoint_loads() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_supermemory_local_doctor.py"),
            "--help",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--server-binary" in completed.stdout
    assert "--model-cache" in completed.stdout
