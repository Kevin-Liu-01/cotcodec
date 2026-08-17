from __future__ import annotations

import io
import runpy
import tarfile
from pathlib import Path

import pytest
import yaml

from scripts.prepare_hermes_observational_memory_context import (
    ContextError,
    _validated_members,
)
from scripts.validate_hermes_observational_memory_experiment import (
    DEFAULT_EXPERIMENT,
    HermesObservationalMemoryExperimentError,
    validate_experiment_contract,
)

ROOT = Path(__file__).resolve().parents[1]
BATCH = (
    ROOT
    / "infra/slurm/host-single-node/hermes-observational-memory-lifecycle.sbatch"
)
DOCKERFILE = (
    ROOT / "infra/memory-baselines/hermes-observational-memory/Dockerfile"
)
DOCTOR = ROOT / "infra/memory-baselines/hermes-observational-memory/doctor.py"
RUNNER = ROOT / "scripts/run_hermes_observational_memory_doctor.py"


def test_registered_contract_is_one_h100_zero_model_calls() -> None:
    payload = validate_experiment_contract()
    runtime = payload["runtime"]
    assert runtime["scheduler"] == "slurm"
    assert runtime["partition"] == "research"
    assert runtime["gpu_sku"] == "H100"
    assert runtime["gpu_count"] == 1
    assert runtime["max_gpu_hours"] == 0.5
    assert runtime["container_gpu_passthrough"] is False
    assert runtime["model_calls"] == 0


def test_contract_rejects_cpu_substitution(tmp_path: Path) -> None:
    payload = yaml.safe_load(DEFAULT_EXPERIMENT.read_text())
    payload["runtime"]["gpu_count"] = 0
    changed = tmp_path / "experiment.yaml"
    changed.write_text(yaml.safe_dump(payload, sort_keys=False))
    with pytest.raises(
        HermesObservationalMemoryExperimentError,
        match="containment contract drifted",
    ):
        validate_experiment_contract(changed)


def test_batch_allocates_h100_but_never_passes_it_to_docker() -> None:
    content = BATCH.read_text()
    assert "#SBATCH --gres=gpu:h100:1" in content
    assert "#SBATCH --time=00:30:00" in content
    assert "nvidia-smi" in content
    assert "grep -qv H100" in content
    assert 'mkdir -m 700 "$source_root"' in content
    assert "sha256:ba360ea13ea50e77e4900cb258c4dc73156060295abd381899f90f9991cedd10" in content
    assert "--network none" in content
    assert "--read-only" in content
    assert "--cap-drop ALL" in content
    assert "--security-opt no-new-privileges" in content
    assert 'syft_tmp="$run_root/syft-tmp-${SLURM_JOB_ID}"' in content
    assert '--volume "$syft_tmp:/tmp:rw"' in content
    assert "--gpus" not in content
    assert "docker pull" not in content
    assert "sudo" not in content


def test_image_and_doctor_bind_exact_offline_components() -> None:
    dockerfile = DOCKERFILE.read_text()
    doctor = DOCTOR.read_text()
    runner = RUNNER.read_text()
    assert "ARG BASE_IMAGE=cotcodec-research:8c51687b-architecture" in dockerfile
    assert "observational_memory-0.10.0-py3-none-any.whl" in dockerfile
    assert "rank_bm25-0.2.2-py3-none-any.whl" in dockerfile
    assert "numpy-2.4.3-cp312-cp312-manylinux_2_27_x86_64" in dockerfile
    assert "pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64" in dockerfile
    assert "uv sync" not in dockerfile
    assert "UV_PYTHON_DOWNLOADS=never" in dockerfile
    assert "assert sys.version_info[:2] == (3, 12)" in dockerfile
    assert "uv pip install --python /workspace/cotcodec/.venv/bin/python --no-deps" in dockerfile
    assert 'ENTRYPOINT ["/workspace/cotcodec/.venv/bin/python"' in dockerfile
    assert "chmod -R a+rX" in dockerfile
    assert 'TOOLS = ["om_context", "om_search", "om_remember"]' in doctor
    assert "get_backend(provider._config.search_backend" in doctor
    assert 'allow_empty=phase in {"prepare", "isolated"}' in doctor
    assert 'allow_empty=phase == "isolated"' in doctor
    assert "BudgetExceededError" in doctor
    assert '"--network",\n        "none"' in runner
    assert '"--pull=never"' in runner
    assert '"--gpus"' not in runner


def test_context_visibility_ignores_the_startup_query_echo() -> None:
    contains = runpy.run_path(str(DOCTOR))["_context_recall_contains"]
    canary = "COTCODEC_ISOLATION_CANARY"
    echoed_only = (
        "## Startup Routing\n\n"
        f"- Task: {canary}\n\n"
        "## Recall\n\n"
        f'- Search deeper memory: `om recall --query "{canary}" --limit 8`\n'
    )
    assert not contains(echoed_only, canary)
    assert contains(
        echoed_only + f"\n## Relevant Memory\n\n- observations: {canary}\n",
        canary,
    )


def test_context_preparer_rejects_archive_links(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("safe.txt")
        data = b"safe"
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
        link = tarfile.TarInfo("escape")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../outside"
        tar.addfile(link)
    with pytest.raises(ContextError, match="links/special files forbidden"):
        _validated_members(archive)
