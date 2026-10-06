from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.run_astra_lifecycle_doctor import (
    BATCH_PATH,
    DOCTOR_ROOT,
    EXTRACTOR_PATH,
    PROJECT_ROOT,
    DoctorError,
    _execution_contract,
    _json_bytes,
    _semantic_projection,
    _sha,
    _sha_path,
    _validate_completed_report,
    _validate_repeat_checkpoint,
)
from scripts.validate_astra_lifecycle_experiment import (
    DEFAULT_EXPERIMENT,
    EXPECTED_STATUS,
    validate_experiment_contract,
)


def test_registered_astra_native_lifecycle_contract_is_valid() -> None:
    payload = validate_experiment_contract(DEFAULT_EXPERIMENT)
    assert payload["source"]["revision"] == (
        "644f9d4e65f4e725996025834c91531592ab6166"
    )
    assert payload["runtime"]["containment"] == "docker-under-slurm"
    assert payload["runtime"]["gpu_sku"] == "H100"
    assert payload["runtime"]["gpu_count"] == 1
    assert payload["runtime"]["app_image_acquisition"] == "preloaded-docker-save"
    assert payload["runtime"]["app_image_id"].startswith("sha256:")
    assert payload["expected_falsification"]["status"] == EXPECTED_STATUS
    assert payload["admission"]["active_inactive_h100_actor"] == (
        "forbidden-for-this-revision"
    )


@pytest.mark.parametrize(
    ("section", "field", "replacement", "message"),
    [
        ("source", "revision", "0" * 40, "source contract drifted"),
        ("runtime", "platform", "linux/arm64", "runtime contract drifted"),
        ("runtime", "gpu_count", 0, "runtime contract drifted"),
        ("intervention", "model_calls", 1, "intervention contract drifted"),
        (
            "admission",
            "active_inactive_h100_actor",
            "allowed",
            "H100 actor admission",
        ),
    ],
)
def test_astra_contract_drift_fails_closed(
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


def test_astra_doctor_sources_encode_h100_containment_and_falsifiers() -> None:
    dockerfile = (DOCTOR_ROOT / "Dockerfile").read_text(encoding="utf-8")
    doctor = (DOCTOR_ROOT / "doctor.ts").read_text(encoding="utf-8")
    runner = (PROJECT_ROOT / "scripts/run_astra_lifecycle_doctor.py").read_text(
        encoding="utf-8"
    )
    batch = (
        PROJECT_ROOT / "infra/slurm/host-single-node/astra-lifecycle.sbatch"
    ).read_text(encoding="utf-8")
    assert "npm ci --ignore-scripts" in dockerfile
    assert "USER 65532:65532" in dockerfile
    assert "COPY doctor.ts /opt/astra/cotcodec-doctor.ts" in dockerfile
    assert '"/opt/astra/cotcodec-doctor.ts"' in dockerfile
    assert "/opt/cotcodec/doctor.ts" not in dockerfile
    assert "all_pinned_window_exceeds_capacity" in doctor
    assert "soft_deleted_plaintext_row_remains" in doctor
    assert "duplicate_write_creates_distinct_rows" in doctor
    assert 'f"container:{database_name}"' in runner
    assert '"--entrypoint"' in runner
    assert '"/cockroach/cockroach"' in runner
    assert '"--listen-addr=127.0.0.1:26257"' in runner
    assert "dst=/opt/astra/cotcodec-doctor.ts,readonly" in runner
    assert '"/opt/astra/cotcodec-doctor.ts"' in runner
    assert '"--import"' in runner
    assert '"tsx"' in runner
    assert '"--read-only"' in runner
    assert '"--cap-drop"' in runner
    assert '"no-new-privileges"' in runner
    assert '"docker", "kill", "--signal=KILL"' in runner
    assert "signal.SIGUSR1" in runner
    assert "execution_contract_sha256" in runner
    assert '"docker", "load"' in runner
    assert "#SBATCH --gres=gpu:h100:1" in batch
    assert "COTCODEC_BATCH_SHA256" in batch
    assert "COTCODEC_APP_IMAGE_ARCHIVE" in batch
    assert "sudo" not in batch


def test_astra_script_entrypoint_loads_without_execution() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/run_astra_lifecycle_doctor.py"),
            "--help",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--output" in completed.stdout


def test_astra_batch_script_has_valid_shell_syntax() -> None:
    completed = subprocess.run(
        [
            "bash",
            "-n",
            str(PROJECT_ROOT / "infra/slurm/host-single-node/astra-lifecycle.sbatch"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def _bind_execution_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, str]:
    monkeypatch.setenv("COTCODEC_SOURCE_SHA256", "1" * 64)
    monkeypatch.setenv("COTCODEC_GIT_SHA", "2" * 40)
    monkeypatch.setenv("COTCODEC_GIT_TREE", "3" * 40)
    monkeypatch.setenv("COTCODEC_BATCH_SHA256", _sha_path(BATCH_PATH))
    monkeypatch.setenv("COTCODEC_SOURCE_EXTRACTOR_SHA256", _sha_path(EXTRACTOR_PATH))
    app_image_archive = tmp_path / "astra-image.tar.gz"
    app_image_archive.write_bytes(b"sealed-test-image")
    return app_image_archive, _sha_path(app_image_archive)


def _fake_repeat(index: int, execution_contract_sha256: str) -> dict[str, object]:
    return {
        "repeat": index,
        "execution_contract_sha256": execution_contract_sha256,
        "prepare": {
            "result": {
                "bounded_unpinned_window": True,
                "evicted_memory_remains_durable": True,
                "retrieval_driven_readmission": True,
                "user_isolation": True,
                "duplicate_write_creates_distinct_rows": True,
                "all_pinned_window_size": 13,
                "all_pinned_window_exceeds_capacity": True,
                "projection": {"prepare": "stable"},
            }
        },
        "restart": {
            "result": {
                "terminal_status": EXPECTED_STATUS,
                "forced_restart_preserves_acknowledged_state": True,
                "retrieval_driven_readmission": True,
                "user_isolation": True,
                "soft_deleted_plaintext_row_remains": True,
                "session_state_retains_soft_deleted_reference": True,
                "native_physical_user_purge_available": False,
                "native_idempotency_key_available": False,
                "projection": {"restart": "stable"},
            }
        },
    }


def _write_completed_fixture(
    output: Path, execution_contract: dict[str, object]
) -> None:
    output.mkdir()
    runs = [
        _fake_repeat(index, str(execution_contract["sha256"])) for index in range(2)
    ]
    for index, run in enumerate(runs):
        (output / f"repeat-{index}.json").write_bytes(_json_bytes(run))
    projection = _semantic_projection(runs[0])
    report = {
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "experiment_sha256": _sha_path(DEFAULT_EXPERIMENT),
        "execution_contract": execution_contract,
        "semantic_projection": projection,
        "semantic_projection_sha256": _sha(_json_bytes(projection)),
        "repeat_files": [
            {
                "path": f"repeat-{index}.json",
                "sha256": _sha_path(output / f"repeat-{index}.json"),
            }
            for index in range(2)
        ],
    }
    (output / "report.json").write_bytes(_json_bytes(report))


def test_astra_completed_resume_is_bound_to_exact_execution_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_image_archive, app_image_archive_sha256 = _bind_execution_environment(
        monkeypatch, tmp_path
    )
    contract = _execution_contract(
        DEFAULT_EXPERIMENT,
        app_image_archive,
        app_image_archive_sha256,
    )
    output = tmp_path / "output"
    _write_completed_fixture(output, contract)
    assert (
        _validate_completed_report(
            output=output,
            experiment_path=DEFAULT_EXPERIMENT,
            execution_contract=contract,
        )["status"]
        == EXPECTED_STATUS
    )

    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    report["execution_contract"]["payload"]["source_archive_sha256"] = "f" * 64
    report["execution_contract"]["sha256"] = _sha(
        _json_bytes(report["execution_contract"]["payload"])
    )
    for index in range(2):
        repeat_path = output / f"repeat-{index}.json"
        repeat = json.loads(repeat_path.read_text(encoding="utf-8"))
        repeat["execution_contract_sha256"] = report["execution_contract"]["sha256"]
        repeat_path.write_bytes(_json_bytes(repeat))
        report["repeat_files"][index]["sha256"] = _sha_path(repeat_path)
    (output / "report.json").write_bytes(_json_bytes(report))
    with pytest.raises(DoctorError, match="completed ASTRA report drifted"):
        _validate_completed_report(
            output=output,
            experiment_path=DEFAULT_EXPERIMENT,
            execution_contract=contract,
        )


def test_astra_partial_repeat_rejects_execution_contract_drift(tmp_path: Path) -> None:
    repeat = _fake_repeat(0, "a" * 64)
    path = tmp_path / "repeat-0.json"
    path.write_bytes(_json_bytes(repeat))
    with pytest.raises(DoctorError, match="checkpoint drifted"):
        _validate_repeat_checkpoint(
            path=path,
            index=0,
            execution_contract_sha256="b" * 64,
        )
