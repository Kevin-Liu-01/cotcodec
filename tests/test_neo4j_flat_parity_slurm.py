from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCH = PROJECT_ROOT / "infra/slurm/host-single-node/neo4j-flat-parity.sbatch"


def test_neo4j_flat_parity_batch_is_syntax_valid_and_gpu_is_not_forwarded() -> None:
    completed = subprocess.run(
        ["bash", "-n", str(BATCH)], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    source = BATCH.read_text(encoding="utf-8")
    assert "#SBATCH --gres=gpu:h100:1" in source
    assert "--gpus" not in source
    assert "COTCODEC_CLIENT_IMAGE_ID" in source
    assert "COTCODEC_CLIENT_SBOM_SHA256" in source
    assert "run_neo4j_flat_parity_doctor.py" in source
    assert "container_gpu_count\": 0" in source
    assert "sudo" not in source


def test_parity_runner_overrides_entrypoint_and_mounts_exact_sources() -> None:
    source = (
        PROJECT_ROOT / "scripts/run_neo4j_flat_parity_doctor.py"
    ).read_text(encoding="utf-8")
    assert '"--entrypoint"' in source
    assert "parity_doctor.py:ro" in source
    assert "neo4j_flat_parity.py:ro" in source
    assert '"--read-only"' in source
    assert '"--cap-drop"' in source
    assert '"no-new-privileges"' in source
    assert '"--gpus"' not in source
