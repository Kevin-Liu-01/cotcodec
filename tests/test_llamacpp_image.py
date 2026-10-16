from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_DOCKERFILE = PROJECT_ROOT / "infra" / "research" / "Dockerfile.llamacpp"
OVERLAY_DOCKERFILE = PROJECT_ROOT / "infra" / "research" / "Dockerfile.llamacpp-overlay"
BASE_BUILDER = PROJECT_ROOT / "infra" / "slurm" / "host-single-node" / "build-llamacpp-image.sbatch"
OVERLAY_BUILDER = PROJECT_ROOT / "scripts" / "build_llamacpp_overlay_on_h100.sh"

LLAMA_COMMIT = "620d2225cc436ab0b001e3200e590e3b286ef9ab"
LLAMA_SOURCE_SHA256 = "622f13ebf8a733003c9ae70ffe96a55c5d09bf2e0e6212ed212efcaca71bf066"
DEVEL = (
    "docker.io/nvidia/cuda@sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43"
)
RUNTIME = (
    "docker.io/nvidia/cuda@sha256:828c4d878adcaa4265d80c95d8ec877149b49bb2419a4cf3bb6aa889bbb7ca2e"
)
BASE_REF = (
    "127.0.0.1:5000/cotcodec-llamacpp@sha256:"
    "d445e09f9f0167cbce65be9fecd0f38c539b243ea321ee281ebeea259e904131"
)
BASE_ID = "sha256:fb8600d96560412d65ec9c269b555c8db6ed4bcfd86a3556658b1c108073e848"


def test_base_image_is_stock_llamacpp_on_pinned_cuda_128_bases() -> None:
    content = BASE_DOCKERFILE.read_text(encoding="utf-8")
    assert f"ARG CUDA_DEVEL_IMAGE={DEVEL}" in content
    assert f"ARG CUDA_RUNTIME_IMAGE={RUNTIME}" in content
    assert f"ARG LLAMA_CPP_COMMIT={LLAMA_COMMIT}" in content
    assert f"ARG LLAMA_CPP_SOURCE_SHA256={LLAMA_SOURCE_SHA256}" in content
    assert "sha256sum -c -" in content
    for flag in (
        "-DGGML_CUDA=ON",
        "-DGGML_NATIVE=OFF",
        '-DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}"',
        "-DLLAMA_BUILD_UI=OFF",
        "-DLLAMA_USE_PREBUILT_UI=OFF",
    ):
        assert flag in content, flag
    assert "ARG CUDA_ARCHITECTURES=90" in content
    # Stock upstream: no instruction edits the source tree or fetches anything but apt packages.
    instructions = "\n".join(
        line for line in content.splitlines() if not line.lstrip().startswith("#")
    )
    for forbidden in ("patch ", "git apply", "sed -i", "curl ", "wget ", "pip install", "npm "):
        assert forbidden not in instructions, forbidden
    for tool in ("llama-server", "llama-cli", "llama-bench", "llama-perplexity"):
        assert tool in content
    assert "ENTRYPOINT []" in content


def test_base_builder_is_cpu_only_pinned_and_receipted() -> None:
    content = BASE_BUILDER.read_text(encoding="utf-8")
    for required in (
        "${SLURM_JOB_ID:?Run this build through sbatch}",
        f'llama_commit="{LLAMA_COMMIT}"',
        f'llama_source_sha256="{LLAMA_SOURCE_SHA256}"',
        f'devel_ref="{DEVEL}"',
        f'runtime_ref="{RUNTIME}"',
        "the image build must hold no GPU",
        "refusing to build",
        "--pull=false",
        "refusing to reuse build root",
        "build-receipt.json",
        "--network none --read-only",
        "CUDA_VERSION=12.8.1",
    ):
        assert required in content, required
    assert not re.search(r"^#SBATCH --gres", content, re.MULTILINE)
    assert "--gpus" not in content and "sudo" not in content
    subprocess.run(["bash", "-n", str(BASE_BUILDER)], check=True)


def test_overlay_pins_the_base_by_digest_and_adds_only_source_and_provenance() -> None:
    content = OVERLAY_DOCKERFILE.read_text(encoding="utf-8")
    assert f"ARG LLAMACPP_BASE_IMAGE={BASE_REF}" in content
    assert "FROM ${LLAMACPP_BASE_IMAGE}" in content
    assert "ENTRYPOINT []" in content and "WORKDIR /workspace/cotcodec" in content
    assert "COPY . /workspace/cotcodec" in content
    assert "write_provenance.py /etc/cotcodec-provenance.json" in content
    assert "run_lm1_smoke.py check-plan" in content
    assert "apt-get" not in content and "pip install" not in content
    builder = OVERLAY_BUILDER.read_text(encoding="utf-8")
    for required in (
        f'base_ref="{BASE_REF}"',
        f'base_id="{BASE_ID}"',
        f'llama_commit="{LLAMA_COMMIT}"',
        "--pull=false",
        "--network=none",
        "refusing to reuse llama.cpp overlay build root",
        "must hold no GPU",
        "verify_compute_provenance.py",
        "build-receipt.json",
    ):
        assert required in builder, required
    assert "--gpus" not in builder and "sudo" not in builder
    subprocess.run(["bash", "-n", str(OVERLAY_BUILDER)], check=True)


def test_overlay_builder_refuses_bad_provenance_before_docker(tmp_path: Path) -> None:
    env = {
        "PATH": "/usr/bin:/bin",
        "SLURM_JOB_ID": "1",
        "COTCODEC_SOURCE_ARCHIVE": "x",
        "COTCODEC_SOURCE_RECEIPT": "x",
        "COTCODEC_SOURCE_EXTRACTOR": "x",
        "COTCODEC_SOURCE_EXTRACTOR_SHA256": "0" * 64,
        "COTCODEC_SOURCE_BUILDER_SHA256": "0" * 64,
        "COTCODEC_SOURCE_SHA256": "0" * 64,
        "COTCODEC_GIT_SHA": "main",
        "COTCODEC_GIT_TREE": "0" * 40,
        "COTCODEC_BUILD_ROOT": str(tmp_path / "build"),
    }
    completed = subprocess.run(
        ["bash", str(OVERLAY_BUILDER)], env=env, capture_output=True, text=True
    )
    assert completed.returncode == 2 and "provenance digest" in completed.stderr
    assert not (tmp_path / "build").exists()
