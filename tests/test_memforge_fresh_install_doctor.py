from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.run_memforge_fresh_install_doctor import (
    MemForgeRunnerError,
    _classify_lane,
    _container_argv,
)
from scripts.validate_memforge_fresh_install_evidence import (
    EXPECTED_STATUS,
    MemForgeEvidenceError,
    validate_memforge_fresh_install_evidence,
)
from scripts.validate_memforge_fresh_install_experiment import (
    DEFAULT_EXPERIMENT,
    MemForgeExperimentError,
    validate_experiment_contract,
)


def test_registered_contract_forbids_h100_and_provider_calls() -> None:
    payload = validate_experiment_contract()
    assert payload["runtime"]["gpu_count_inside_containers"] == 0
    assert payload["intervention"]["provider_calls"] == 0
    assert payload["intervention"]["model_backend_calls"] == 0
    assert payload["admission"]["h100_actor"] == "forbidden-for-this-revision"


def test_registered_contract_drift_fails_closed(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text(encoding="utf-8"))
    payload["admission"]["h100_actor"] = "allowed"
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(MemForgeExperimentError, match="admission contract drifted"):
        validate_experiment_contract(path)


def test_container_argv_is_networkless_nonroot_and_has_no_gpu() -> None:
    argv = _container_argv(
        image="postgres@sha256:" + "1" * 64,
        schema=Path("/inputs/schema.sql"),
        name="doctor",
        uid=70,
    )
    assert argv[argv.index("--network") + 1] == "none"
    assert "--read-only" in argv
    assert argv[argv.index("--cap-drop") + 1] == "ALL"
    assert "no-new-privileges" in argv
    assert argv[argv.index("--user") + 1] == "70:70"
    assert "--gpus" not in argv
    assert "sudo" not in argv


@pytest.mark.parametrize(
    ("lane", "logs"),
    [
        (
            "official-compose-postgres",
            "psql:/docker-entrypoint-initdb.d/schema.sql:14: ERROR:  "
            'extension "vector" is not available\n'
            "Could not open extension control file "
            '"/usr/local/share/postgresql/extension/vector.control"\n',
        ),
        (
            "pgvector-enabled-control",
            "psql:/docker-entrypoint-initdb.d/schema.sql:57: ERROR:  "
            'relation "warm_tier" does not exist\n',
        ),
    ],
)
def test_lane_classifier_accepts_only_registered_failure(lane: str, logs: str) -> None:
    checks = _classify_lane(lane=lane, exit_code=3, logs=logs.encode())
    assert all(checks.values())
    with pytest.raises(MemForgeRunnerError, match="failure semantics drifted"):
        _classify_lane(lane=lane, exit_code=0, logs=logs.encode())


def test_retained_negative_evidence_is_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    evidence = validate_memforge_fresh_install_evidence(
        root / "research/evidence/memory/memforge-fresh-install-negative-v1.json",
        project_root=root,
    )
    assert evidence["status"] == EXPECTED_STATUS


def test_retained_negative_rejects_claim_upgrade() -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    path = root / "research/evidence/memory/memforge-fresh-install-negative-v1.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    evidence["claim_boundary"]["memory_quality_evaluated"] = True
    with pytest.raises(MemForgeEvidenceError, match="identity drifted"):
        validate_memforge_fresh_install_evidence(evidence, project_root=root)
