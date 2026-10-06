from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from scripts.run_memgpt_letta_lifecycle_doctor import _decision_checks


def test_runner_can_launch_by_file_path_outside_repository() -> None:
    runner = Path("scripts/run_memgpt_letta_lifecycle_doctor.py").resolve()
    completed = subprocess.run(
        [sys.executable, str(runner), "--help"],
        cwd=runner.parent,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--source-root SOURCE_ROOT" in completed.stdout


def test_doctor_uses_versioned_admin_bootstrap_routes() -> None:
    source = Path("infra/memory-baselines/memgpt-letta/doctor.py").read_text(
        encoding="utf-8"
    )

    assert '"/v1/admin/orgs/"' in source
    assert '"/v1/admin/users/"' in source
    assert '"/v1/orgs/"' not in source
    assert '"/v1/users/"' not in source


def test_slurm_entrypoint_hash_binds_contract_validator() -> None:
    batch = Path(
        "infra/slurm/host-single-node/memgpt-letta-lifecycle.sbatch"
    ).read_text(encoding="utf-8")
    runner = Path("scripts/run_memgpt_letta_lifecycle_doctor.py").read_text(
        encoding="utf-8"
    )

    assert "COTCODEC_VALIDATOR_SHA256" in batch
    assert "validate_memgpt_letta_lifecycle_experiment.py" in batch
    assert 'args.output / "validator.py"' in runner
    assert '"validator": _sha256(VALIDATOR)' in runner


def test_doctor_direct_sql_uses_exact_orm_table_names() -> None:
    source = Path("infra/memory-baselines/memgpt-letta/doctor.py").read_text(
        encoding="utf-8"
    )

    assert 'FROM archival_passages' in source
    assert 'FROM messages' in source
    assert 'FROM "block"' in source
    assert 'FROM blocks ' not in source


def _load_doctor() -> ModuleType:
    path = Path("infra/memory-baselines/memgpt-letta/doctor.py")
    spec = importlib.util.spec_from_file_location("memgpt_letta_doctor", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stopped_state_scan_detects_only_real_plaintext(tmp_path: Path) -> None:
    doctor = _load_doctor()
    evidence = tmp_path / "evidence"
    scan = tmp_path / "scan"
    evidence.mkdir()
    scan.mkdir()
    state = {
        "repeat": 1,
        "canaries": {"deleted": "COTCODEC_DELETED_CANARY_123"},
    }
    (evidence / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (scan / "heap").write_bytes(b"prefix COTCODEC_DELETED_CANARY_123 suffix")

    assert doctor.phase_scan(evidence, 1, scan) == 0
    result = json.loads((evidence / "phase-scan.json").read_text(encoding="utf-8"))
    assert result["checks"]["stopped_postgres_plaintext_residue_present"] is True
    assert result["plaintext_hits"] == {"deleted": ["heap"]}


def test_stopped_state_scan_fails_closed_without_plaintext(tmp_path: Path) -> None:
    doctor = _load_doctor()
    evidence = tmp_path / "evidence"
    scan = tmp_path / "scan"
    evidence.mkdir()
    scan.mkdir()
    (evidence / "state.json").write_text(
        json.dumps({"repeat": 2, "canaries": {"deleted": "ABSENT_CANARY"}}),
        encoding="utf-8",
    )
    (scan / "heap").write_bytes(b"unrelated")

    assert doctor.phase_scan(evidence, 2, scan) == 3


def test_decision_checks_require_two_identical_true_projections() -> None:
    projection = {
        "provider_free_agent_creation_passes": True,
        "core_block_mutation_passes": True,
        "inactive_archive_write_and_read_passes": True,
        "cross_organization_isolation_passes": True,
        "normal_state_survives_fresh_process": True,
        "failed_core_update_returns_server_error_after_block_mutation": True,
        "failed_core_update_mutation_survives_fresh_process": True,
        "identical_archive_retry_creates_duplicate_rows": True,
        "duplicate_archive_rows_survive_fresh_process": True,
        "deleting_agent_retains_owner_archive_and_core_blocks": True,
        "explicit_archive_and_block_delete_is_logically_effective": True,
        "stopped_postgres_plaintext_residue_present": True,
    }
    repeats = [
        {"projection": dict(projection)},
        {"projection": dict(projection)},
    ]

    checks = _decision_checks(repeats, {"image_id": "sha256:test"})
    assert all(checks.values())

    repeats[1]["projection"]["core_block_mutation_passes"] = False
    checks = _decision_checks(repeats, {"image_id": "sha256:test"})
    assert checks["core_block_mutation_passes"] is False
    assert checks["reproduced_in_two_clean_states"] is False
