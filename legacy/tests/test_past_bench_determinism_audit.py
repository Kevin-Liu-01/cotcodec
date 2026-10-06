from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DOCTOR = _load(
    "sm01_job_doctor",
    ROOT / "infra/research/past-bench/sm01_job_doctor.py",
)
AUDIT = _load(
    "audit_sm01_determinism_failure",
    ROOT / "infra/research/past-bench/audit_sm01_determinism_failure.py",
)
BATCH = ROOT / "infra/slurm/host-single-node/past-sm01-determinism-audit.sbatch"


def test_primary_comparison_exposes_score_pass_and_semantic_drift() -> None:
    left = [
        {
            "task_id": "SM01_LEARN_B_001",
            "task_score": 0.76,
            "passed": False,
            "final_response_text": "continuous",
        }
    ]
    right = [
        {
            "task_id": "SM01_LEARN_B_001",
            "task_score": 1.0,
            "passed": True,
            "final_response_text": "resumed",
        }
    ]

    row = AUDIT._compare_primary(left, right)[0]

    assert row["score_equal"] is False
    assert row["passed_equal"] is False
    assert row["normalized_episode_equal"] is False


def test_determinism_audit_batch_is_cpu_only_and_contained() -> None:
    content = BATCH.read_text(encoding="utf-8")
    assert "#SBATCH --gres" not in content
    assert "--network none" in content
    assert "--pull=never" in content
    assert "--continuous-root /continuous" in content
    assert "--resumed-root /resumed" in content
    assert "sudo" not in content
    assert "/var/run/docker.sock" not in content
