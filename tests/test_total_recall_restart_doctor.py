from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_total_recall_restart_doctor import (
    DOCTOR_ROOT,
    EXPECTED_GIT_SHA,
    EXPECTED_SOURCE_ARCHIVE_SHA256,
    PROJECT_ROOT,
    _prepare_context,
    _verify_source,
)
from scripts.validate_total_recall_experiment import (
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)


def test_registered_total_recall_negative_contract_is_valid() -> None:
    payload = validate_experiment_contract(DEFAULT_EXPERIMENT)
    assert payload["source"]["revision"] == EXPECTED_GIT_SHA
    assert payload["execution"]["runtime_network"] == "none"
    assert payload["execution"]["gpus"] == 0
    assert payload["next_gate"]["required_before_h100"] is True


def test_pinned_total_recall_source_is_clean_and_exact() -> None:
    receipt = _verify_source()
    assert receipt["git_sha"] == EXPECTED_GIT_SHA
    assert receipt["git_archive_sha256"] == EXPECTED_SOURCE_ARCHIVE_SHA256
    assert receipt["worktree_clean"] is True


def test_build_context_contains_only_pinned_source_plus_doctor(tmp_path: Path) -> None:
    receipt = _verify_source()
    inputs = _prepare_context(receipt, tmp_path)
    assert set(inputs) == {
        "Dockerfile",
        "doctor/Program.cs",
        "doctor/TotalRecall.RestartDoctor.csproj",
        "doctor/packages.lock.json",
        "global.json",
        "package-lock.json",
    }
    dockerfile = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "@sha256:" in dockerfile
    assert "USER 65532:65532" in dockerfile
    program = (tmp_path / "doctor" / "Program.cs").read_text(encoding="utf-8")
    assert "HotTierCompactor.Compact" in program
    assert "MoveHelpers.MoveAndReEmbed" in program
    assert "new SqliteStore(dbPath)" in program
    assert not (tmp_path / ".git").exists()


def test_validator_rejects_h100_admission_drift(tmp_path: Path) -> None:
    payload = DEFAULT_EXPERIMENT.read_text(encoding="utf-8").replace(
        "required_before_h100: true", "required_before_h100: false"
    )
    path = tmp_path / "experiment.yaml"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="H100 admission gate"):
        validate_experiment_contract(path)


def test_doctor_sources_are_regular_files() -> None:
    for relative in (
        "Dockerfile.restart-doctor",
        "doctor/Program.cs",
        "doctor/TotalRecall.RestartDoctor.csproj",
        "doctor/packages.lock.json",
    ):
        path = DOCTOR_ROOT / relative
        assert path.is_file()
        assert not path.is_symlink()


def test_direct_script_entrypoint_loads_without_package_install() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(
                PROJECT_ROOT
                / "scripts"
                / "run_total_recall_restart_doctor.py"
            ),
            "--help",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--output-dir" in completed.stdout
