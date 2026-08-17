from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.audit_reasoningbank_source import (
    SOURCE_MARKERS,
    ReasoningBankSourceAuditError,
    _git_archive_sha256,
    _write_new,
    audit_source,
)
from scripts.validate_reasoningbank_source_experiment import (
    DEFAULT_EXPERIMENT,
    ReasoningBankSourceExperimentError,
    validate_experiment_contract,
)


def _run(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def _write_fixture_sources(root: Path) -> None:
    for relative, markers in SOURCE_MARKERS.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(markers) + "\n", encoding="utf-8")
    (root / "LICENSE").write_text("Apache-2.0 fixture\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")


def _commit(root: Path, message: str) -> None:
    _run(root, "add", ".")
    _run(root, "commit", "-m", message)


def _expected(root: Path) -> dict[str, object]:
    critical = {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in SOURCE_MARKERS
    }
    revision = _run(root, "rev-parse", "HEAD")
    return {
        "source_id": "reasoningbank",
        "repository": "https://example.test/reasoning-bank",
        "revision": revision,
        "tree": _run(root, "rev-parse", "HEAD^{tree}"),
        "git_archive_tar_sha256": _git_archive_sha256(root, revision),
        "license": "Apache-2.0",
        "license_sha256": hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest(),
        "pyproject_sha256": hashlib.sha256(
            (root / "pyproject.toml").read_bytes()
        ).hexdigest(),
        "uv_lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
        "critical_file_sha256s": critical,
    }


@pytest.fixture
def source_checkout(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    _run(root, "init", "-q")
    _run(root, "config", "user.email", "fixture@example.test")
    _run(root, "config", "user.name", "Fixture")
    _write_fixture_sources(root)
    _commit(root, "fixture")
    return root


def test_source_audit_binds_clean_checkout_and_findings(source_checkout: Path) -> None:
    report = audit_source(source_checkout, expected_source=_expected(source_checkout))
    assert report["status"] == "BLOCKED_MUTABLE_EVALUATION_AND_UNPINNED_RETRIEVAL"
    assert report["scientific_result"] is False
    assert report["publication_ready"] is False
    assert report["findings"]["scaling_reward_label_is_inverted"] is True


def test_source_audit_rejects_dirty_checkout(source_checkout: Path) -> None:
    path = source_checkout / "WebArena/memory_management.py"
    path.write_text(path.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
    with pytest.raises(ReasoningBankSourceAuditError, match="checkout is dirty"):
        audit_source(source_checkout, expected_source=_expected(source_checkout))


def test_source_audit_rejects_missing_registered_marker(source_checkout: Path) -> None:
    path = source_checkout / "WebArena/induce_scaling.py"
    path.write_text("if reward == 0:\nstatus = 'changed'\n", encoding="utf-8")
    _commit(source_checkout, "remove marker")
    with pytest.raises(ReasoningBankSourceAuditError, match="finding no longer holds"):
        audit_source(source_checkout, expected_source=_expected(source_checkout))


def test_source_report_writer_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    _write_new(output, {"status": "first"})
    with pytest.raises(FileExistsError):
        _write_new(output, {"status": "second"})
    assert json.loads(output.read_text(encoding="utf-8")) == {"status": "first"}


def test_experiment_contract_fails_closed_on_h100_upgrade(tmp_path: Path) -> None:
    payload = copy.deepcopy(yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8")))
    payload["admission"]["h100_admission"] = "allowed"
    path = tmp_path / DEFAULT_EXPERIMENT.name
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(ReasoningBankSourceExperimentError, match="admission drifted"):
        validate_experiment_contract(path)
