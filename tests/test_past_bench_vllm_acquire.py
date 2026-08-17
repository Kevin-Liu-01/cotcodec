from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "infra/slurm/host-single-node/past-bench-vllm-acquire.sbatch"


def test_vllm_acquisition_is_slurm_h100_and_digest_pinned() -> None:
    text = BATCH.read_text(encoding="utf-8")
    assert "#SBATCH --gres=gpu:h100:1" in text
    assert "${SLURM_JOB_ID:?" in text
    assert "${CUDA_VISIBLE_DEVICES:?" in text
    assert "${SLURM_JOB_GPUS:?" in text
    assert "vllm/vllm-openai@sha256" in text
    assert "docker pull --platform linux/amd64" in text
    assert "docker image inspect" in text
    assert ".RepoDigests" in text
    assert 'removeprefix("docker.io/")' in text
    assert "--pull=never" in text


def test_vllm_acquisition_doctors_tool_transport_surface() -> None:
    text = BATCH.read_text(encoding="utf-8")
    for flag in (
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "--served-model-name",
        "--tensor-parallel-size",
        "--default-chat-template-kwargs",
    ):
        assert flag in text
    assert "torch.cuda.device_count() == 1" in text
    assert "COTCODEC_EXPECTED_GPU_UUID" in text
    assert 'nvidia-smi","--query-gpu=uuid' in text
    assert 'docker_gpu_request="device=${allocated_gpu_uuid}"' in text
    assert text.count('--gpus "${docker_gpu_request}"') == 2
    assert "serve --help=all" in text
    assert "docker save" in text
    assert "scientific_result\": False" in text
    assert "publication_ready\": False" in text
