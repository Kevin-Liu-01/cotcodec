from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.validate_memory_sources import (
    EVIDENCE_GRADES,
    GRAPH_SEMANTICS,
    RESIDENCY_TRANSITIONS,
)
from scripts.validate_past_bench_source import (
    DEFAULT_CONTRACT,
    PastBenchSourceError,
    inspect_checkout,
    load_contract,
    validate_checkout,
)


def _git(root: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _make_checkout(tmp_path: Path) -> Path:
    root = tmp_path / "PAST-Bench"
    root.mkdir()
    required = {
        "LICENSE": "Apache License 2.0 fixture\n",
        "README.md": "# PAST-Bench fixture\n",
        "pyproject.toml": "[project]\nname='past-bench'\nversion='1.0.0'\n",
        "requirements.txt": "pyyaml>=6\n",
        "Dockerfile.runtime": "FROM python:3.11-slim\n",
        "Dockerfile.agent": "FROM python:3.11-slim\n",
        "configs/agents.yaml": "agents: {}\n",
    }
    for relative, text in required.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    ids = {
        "memory_ability": "M01_fixture",
        "procedural_ability": "P01_fixture",
        "proactive_information_gathering": "G01_fixture",
        "update_ability": "U01_fixture",
    }
    for ability, family_id in ids.items():
        family_dir = root / "self-evolve-tasks-v2" / ability / family_id
        task_name = "control_case"
        _write_yaml(
            family_dir / "family.yaml",
            {
                "family_id": family_id,
                "ability_dir": ability,
                "primary_ability": ability,
                "instances_per_bucket": {"control": 1},
                "total_episodes": 1,
                "episode_order": [task_name],
            },
        )
        _write_yaml(
            family_dir / task_name / "task.yaml",
            {"task_id": f"{family_id}_TASK", "prompt": {"text": "fixture"}},
        )
        (family_dir / task_name / "fixtures").mkdir()
        (family_dir / task_name / "fixtures" / "input.txt").write_text(
            "fixture\n", encoding="utf-8"
        )
        _write_yaml(
            root
            / "configs"
            / "self_evolve_v2"
            / f"hermes_self_evolve_v2_{family_id.lower()}_only.yaml",
            {
                "episodes": [
                    {
                        "task": (
                            f"../../self-evolve-tasks-v2/{ability}/{family_id}/{task_name}"
                        ),
                        "family_id": family_id,
                        "bucket": "control",
                        "stage": "control",
                        "mechanism": "memory",
                        "expected_persistence_signal": "memory",
                        "requires_fresh_session": True,
                        "persistence_allowed": True,
                        "history_mode": "fresh",
                    }
                ]
            },
        )

    _git(root, "init")
    _git(root, "remote", "add", "origin", "https://github.com/Gen-Verse/PAST-Bench.git")
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.com",
        "commit",
        "-m",
        "fixture",
    )
    return root


def _contract_and_ledger(
    tmp_path: Path, observed: dict[str, object]
) -> tuple[Path, Path]:
    checkout = observed["checkout"]
    assert isinstance(checkout, dict)
    expected_fields = (
        "category_family_counts",
        "category_episode_counts",
        "family_count",
        "declared_episode_count",
        "unreferenced_task_count",
        "family_roster_sha256",
        "task_manifest_sha256",
        "unreferenced_task_manifest_sha256",
        "required_files_sha256",
        "dependency_lock_files",
    )
    contract = {
        "schema_version": 1,
        "source_id": "past-bench",
        "repository_role": "benchmark-agents-tasks-tests-and-containers",
        "url": "https://github.com/Gen-Verse/PAST-Bench",
        "revision": checkout["revision"],
        "tree_sha": checkout["tree_sha"],
        "source_archive_sha256": checkout["source_archive_sha256"],
        "license": "Apache-2.0",
        "scientific_result": False,
        "dependency_lock_status": "unresolved-upstream",
        "expected": {field: observed[field] for field in expected_fields},
    }
    contract_path = tmp_path / "contract.yaml"
    _write_yaml(contract_path, contract)
    ledger_path = tmp_path / "ledger.yaml"
    _write_yaml(
        ledger_path,
        {
            "schema_version": 1,
            "verified_at": "2026-08-14",
            "controlled_vocabulary": {
                "memory_layers": ["controller"],
                "evidence_grades": sorted(EVIDENCE_GRADES),
                "evidence_grade_definitions": {
                    grade: f"Fixture definition for {grade}."
                    for grade in sorted(EVIDENCE_GRADES)
                },
                "residency_transitions": sorted(RESIDENCY_TRANSITIONS),
                "graph_semantics": sorted(GRAPH_SEMANTICS),
            },
            "sources": {
                "past-bench": {
                    "kind": "benchmark",
                    "title": "PAST-Bench",
                    "observed_on": "2026-08-14",
                    "primary_sources": ["https://github.com/Gen-Verse/PAST-Bench"],
                    "repositories": [
                        {
                            "role": "benchmark-agents-tasks-tests-and-containers",
                            "url": "https://github.com/Gen-Verse/PAST-Bench",
                            "revision": checkout["revision"],
                            "license": "Apache-2.0",
                        }
                    ],
                    "memory_layers": ["controller"],
                    "mechanism": "Fixture longitudinal benchmark.",
                    "use_as": ["fixture"],
                    "evidence_grade": "open-harness-reported",
                    "limitations": ["Fixture only."],
                }
            },
        },
    )
    return contract_path, ledger_path


def test_live_contract_binds_the_registered_204_episode_surface() -> None:
    contract = load_contract(DEFAULT_CONTRACT)
    assert contract["expected"]["declared_episode_count"] == 204
    assert contract["expected"]["unreferenced_task_count"] == 7
    assert contract["dependency_lock_status"] == "unresolved-upstream"
    assert contract["scientific_result"] is False


def test_synthetic_checkout_validates_without_executing_upstream(tmp_path: Path) -> None:
    checkout = _make_checkout(tmp_path)
    observed = inspect_checkout(checkout)
    contract, ledger = _contract_and_ledger(tmp_path, observed)
    receipt = validate_checkout(checkout, contract_path=contract, ledger_path=ledger)
    assert receipt["status"] == "VALIDATED_SOURCE_CONTRACT_NOT_EXECUTION"
    assert receipt["declared_episode_count"] == 4
    assert receipt["scientific_result"] is False


def test_checkout_drift_is_rejected_before_admission(tmp_path: Path) -> None:
    checkout = _make_checkout(tmp_path)
    observed = inspect_checkout(checkout)
    contract, ledger = _contract_and_ledger(tmp_path, observed)
    (checkout / "README.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(PastBenchSourceError, match="clean"):
        validate_checkout(checkout, contract_path=contract, ledger_path=ledger)


def test_reference_evaluation_cannot_disable_fresh_session(tmp_path: Path) -> None:
    checkout = _make_checkout(tmp_path)
    manifest = next(
        (checkout / "configs" / "self_evolve_v2").glob("*m01_fixture_only.yaml")
    )
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    payload["episodes"][0]["requires_fresh_session"] = False
    _write_yaml(manifest, payload)
    _git(checkout, "add", ".")
    _git(
        checkout,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.com",
        "commit",
        "-m",
        "break fresh session",
    )
    with pytest.raises(PastBenchSourceError, match="fresh session"):
        inspect_checkout(checkout)


def test_unreferenced_task_directories_are_sealed_separately(tmp_path: Path) -> None:
    checkout = _make_checkout(tmp_path)
    family = checkout / "self-evolve-tasks-v2" / "update_ability" / "U01_fixture"
    _write_yaml(family / "retired_task" / "task.yaml", {"task_id": "RETIRED"})
    _git(checkout, "add", ".")
    _git(
        checkout,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.com",
        "commit",
        "-m",
        "retain excluded task",
    )
    observed = inspect_checkout(checkout)
    assert observed["declared_episode_count"] == 4
    assert observed["unreferenced_task_count"] == 1
    assert observed["unreferenced_tasks"][0]["directory"] == "retired_task"


def test_tracked_task_symlink_is_rejected_before_manifest_read(tmp_path: Path) -> None:
    checkout = _make_checkout(tmp_path)
    task_dir = (
        checkout
        / "self-evolve-tasks-v2"
        / "memory_ability"
        / "M01_fixture"
        / "control_case"
    )
    task_file = task_dir / "task.yaml"
    task_file.unlink()
    task_file.symlink_to("/etc/passwd")
    _git(checkout, "add", ".")
    _git(
        checkout,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.com",
        "commit",
        "-m",
        "add malicious source link",
    )
    with pytest.raises(PastBenchSourceError, match="tracked symlinks"):
        inspect_checkout(checkout)
