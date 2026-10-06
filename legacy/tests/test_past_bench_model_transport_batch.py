from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "infra/slurm/host-single-node/past-bench-model-transport.sbatch"


def test_transport_batch_is_two_h100_slurm_and_no_runtime_pull() -> None:
    text = BATCH.read_text(encoding="utf-8")
    assert "#SBATCH --gres=gpu:h100:2" in text
    assert "${SLURM_JOB_ID:?" in text
    assert "${CUDA_VISIBLE_DEVICES:?" in text
    assert "${SLURM_JOB_GPUS:?" in text
    assert "${SLURM_GPUS_ON_NODE:-} != 2" in text
    assert "docker pull" not in text
    assert text.count("--pull=never") >= 2
    assert "torch.cuda.device_count() == 2" in text
    assert "allocated_gpu_uuid_csv" in text
    assert 'host.get("DeviceRequests")' in text
    assert "runtime_uid=$(id -u)" in text
    assert "runtime_gid=$(id -g)" in text
    assert "PAST model transport requires a non-root Slurm identity" in text
    assert "model server configured user is not the registered non-root identity" in text
    assert 'sha256sum "${registered_batch}"' in text
    assert 'sha256sum "$0"' in text
    assert 'realpath "$0"' not in text


def test_transport_batch_loads_bound_images_and_serves_private_model_snapshot() -> None:
    text = BATCH.read_text(encoding="utf-8")
    assert "verify_docker_archive" in text
    assert 'docker load --input "${past_image_archive}"' in text
    assert 'docker load --input "${vllm_image_archive}"' in text
    assert "RepoDigests" not in text
    assert '("PAST", past, expected_past)' in text
    assert '("vLLM", vllm, expected_vllm)' in text
    assert '("model", model, expected_model)' in text
    assert "sha256:f26809eb13339cbc59c3d0cc972f8c4997830dc8d2121cf18089cb122834e10d" in text
    assert (
        "docker.io/vllm/vllm-openai@"
        "sha256:f0b9a0dc75a9fca3b6811e3279367b2d6a448055a000bfd13859587d74cef268"
        in text
    )
    assert "aecb8b90cd6378c1440c60efd3eef1d98d189e47110539350858dfde2ec9d0f4" in text
    assert "PRIVATE_MODEL_SNAPSHOT_VERIFIED" in text
    assert '--volume "${model_root}:/source-model:ro"' in text
    assert '--volume "${private_model_root}:/models/${model_id}:ro"' in text
    assert "running-server-model-verification.json" in text
    assert "running-server-gpu-verification.json" in text
    assert "--env USER=cotcodec" in text
    assert "--env LOGNAME=cotcodec" in text
    assert "--tmpfs /tmp:rw,exec,nosuid,nodev,size=16g" in text
    assert "model server executable scratch tmpfs contract drifted" in text
    assert "model server identity/cache environment drifted" in text


def test_transport_batch_uses_internal_network_without_host_port() -> None:
    text = BATCH.read_text(encoding="utf-8")
    assert "docker network create --internal" in text
    assert 'network.get("Internal") is not True' in text
    assert "--network-alias past-qwen" in text
    assert "--publish" not in text
    assert "-p 8000" not in text
    assert "external egress unexpectedly reached" in text


def test_transport_batch_binds_native_qwen_tool_parser_and_receipts() -> None:
    text = BATCH.read_text(encoding="utf-8")
    assert "--enable-auto-tool-choice" in text
    assert "qwen3_xml" in text
    assert "--trust-remote-code" in text
    assert '"--trust-remote-code" in argv' in text
    assert "full-model-verification.json" in text
    assert "model-transport-doctor.json" in text
    assert "native_nonstream_tool_call" in text
    assert "native_stream_tool_call" in text
    assert "scientific_result\": False" in text
