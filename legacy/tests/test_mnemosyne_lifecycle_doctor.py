from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from scripts.seal_mnemosyne_lifecycle_evidence import (
    DEFAULT_OUTPUT,
    EvidenceError,
    validate_evidence,
)
from scripts.validate_mnemosyne_lifecycle_experiment import (
    EXPECTED_STATUS,
    validate_experiment_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_mnemosyne_experiment_is_cpu_only_and_h100_forbidden() -> None:
    payload = validate_experiment_contract()
    assert payload["runtime"]["gpu_count"] == 0
    assert payload["runtime"]["runtime_network"] == "none"
    assert payload["admission"]["h100_actor"] == "forbidden-for-this-revision"


def test_mnemosyne_container_and_runner_are_locked_down() -> None:
    dockerfile = (
        PROJECT_ROOT / "infra/memory-baselines/mnemosyne/Dockerfile"
    ).read_text(encoding="utf-8")
    runner = (
        PROJECT_ROOT / "scripts/run_mnemosyne_lifecycle_doctor.py"
    ).read_text(encoding="utf-8")
    assert "USER 65532:65532" in dockerfile
    assert "--network" in runner and '"none"' in runner
    assert "--read-only" in runner
    assert '"--cap-drop"' in runner and '"ALL"' in runner
    assert "no-new-privileges" in runner
    assert "--gpus" not in runner
    assert "sudo" not in runner


def test_retained_mnemosyne_negative_recomputes() -> None:
    evidence = validate_evidence()
    assert evidence["status"] == EXPECTED_STATUS
    assert evidence["run_count"] == 2
    assert evidence["claim_boundary"]["one_way_consolidation_reproduced"] is True
    assert evidence["claim_boundary"]["bidirectional_paging_demonstrated"] is False
    assert evidence["h100_admission"] == "forbidden-for-this-revision"


def test_retained_mnemosyne_negative_rejects_favorable_rewrite(
    tmp_path: Path,
) -> None:
    evidence = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    receipt = evidence["files"]["repeat-1/purge.json"]
    purge = json.loads(base64.b64decode(receipt["content_base64"]))
    purge["episodic_forget_results"] = [True]
    rewritten = (json.dumps(purge, indent=2, sort_keys=True) + "\n").encode()
    receipt["content_base64"] = base64.b64encode(rewritten).decode("ascii")
    receipt["bytes"] = len(rewritten)
    import hashlib

    receipt["sha256"] = hashlib.sha256(rewritten).hexdigest()
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(EvidenceError, match="phase digest drifted"):
        validate_evidence(path)
