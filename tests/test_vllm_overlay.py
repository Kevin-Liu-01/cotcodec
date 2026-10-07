from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.fetch_open_model import load_registry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = PROJECT_ROOT / "infra" / "research" / "Dockerfile.vllm-overlay"
BUILDER = PROJECT_ROOT / "scripts" / "build_vllm_overlay_on_h100.sh"
FETCH = PROJECT_ROOT / "infra" / "slurm" / "host-single-node" / "fetch-model-metadata-in-docker.sh"
FETCH_SBATCH = PROJECT_ROOT / "infra" / "slurm" / "host-single-node" / "fetch-model-metadata.sbatch"
CU129 = "sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f"
CU129_ID = "sha256:423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b"


def test_overlay_is_pinned_by_digest_and_resets_the_vllm_entrypoint() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert f"ARG VLLM_BASE_IMAGE=docker.io/vllm/vllm-openai@{CU129}" in content
    assert "FROM ${VLLM_BASE_IMAGE}" in content
    assert "ENTRYPOINT []" in content
    assert 'CMD ["python", "scripts/check_harness_env.py"]' in content
    assert "WORKDIR /workspace/cotcodec" in content
    assert "COPY . /workspace/cotcodec" in content
    assert "ln -sf /usr/bin/python3 /usr/local/bin/python" in content
    assert "write_provenance.py /etc/cotcodec-provenance.json" in content
    assert 'org.opencontainers.image.revision="${GIT_SHA}"' in content
    assert 'org.opencontainers.image.source-tree-sha256="${SOURCE_TREE_SHA256}"' in content
    assert 'cotcodec-base-image-id="${BASE_IMAGE_ID}"' in content
    assert 'cotcodec-upstream-vllm-commit="${VLLM_COMMIT}"' in content
    assert 'test "${VLLM_BUILD_COMMIT}" = "${VLLM_COMMIT}"' in content
    assert "pip install" not in content and "apt-get" not in content
    assert content.index("ENTRYPOINT []") < content.index("CMD [")


def test_overlay_builder_is_offline_allowlisted_and_receipted() -> None:
    content = BUILDER.read_text(encoding="utf-8")
    for required in (
        "${SLURM_JOB_ID:?Run this build through Slurm}",
        "--pull=false",
        "--network=none",
        f"docker.io/vllm/vllm-openai@{CU129}",
        f'base_id="{CU129_ID}"',
        'base_id="sha256:c76d0e2225a4b1cb1e2109ace39639f55e714abd1a7a427acc8b0bbd7f6a83b3"',
        "refusing to reuse vLLM overlay build root",
        'chmod -R a+rX "${context}"',
        "ai.vllm.build.commit",
        "infra/research/Dockerfile.vllm-overlay",
        "verify_compute_provenance.py",
        "build-receipt.json",
        "--network none --read-only",
    ):
        assert required in content, required
    assert "sudo" not in content
    assert "--gpus" not in content
    subprocess.run(["bash", "-n", str(BUILDER)], check=True)


def test_builder_rejects_unknown_variants_before_touching_docker(tmp_path: Path) -> None:
    env = {
        "PATH": "/usr/bin:/bin",
        "SLURM_JOB_ID": "1",
        "COTCODEC_SOURCE_ARCHIVE": "x",
        "COTCODEC_SOURCE_RECEIPT": "x",
        "COTCODEC_SOURCE_EXTRACTOR": "x",
        "COTCODEC_SOURCE_EXTRACTOR_SHA256": "0" * 64,
        "COTCODEC_SOURCE_BUILDER_SHA256": "0" * 64,
        "COTCODEC_SOURCE_SHA256": "0" * 64,
        "COTCODEC_GIT_SHA": "0" * 40,
        "COTCODEC_GIT_TREE": "0" * 40,
        "COTCODEC_BUILD_ROOT": str(tmp_path / "build"),
        "COTCODEC_VLLM_VARIANT": "cu128",
    }
    completed = subprocess.run(["bash", str(BUILDER)], env=env, capture_output=True, text=True)
    assert completed.returncode == 2
    assert "cu129 or cu130" in completed.stderr
    env["COTCODEC_VLLM_VARIANT"] = "cu129"
    env["COTCODEC_GIT_SHA"] = "main"
    completed = subprocess.run(["bash", str(BUILDER)], env=env, capture_output=True, text=True)
    assert completed.returncode == 2 and "provenance digest" in completed.stderr
    assert not (tmp_path / "build").exists()


def test_metadata_fetch_never_gets_a_gpu_or_overwrites_a_receipt() -> None:
    content = FETCH.read_text(encoding="utf-8")
    assert 'fetch "${model_id}" --metadata-only' in content
    assert "--gpus" not in content
    assert "refusing to overwrite an existing receipt or snapshot" in content
    assert "would swallow the fetch command" in content
    assert "--read-only" in content and "--cap-drop ALL" in content
    assert "publication-eligible" in content
    assert "sudo" not in content
    sbatch = FETCH_SBATCH.read_text(encoding="utf-8")
    assert "fetch-model-metadata-in-docker.sh" in sbatch
    assert "#SBATCH --time=00:10:00" in sbatch
    assert "refusing the shared ~/cotcodec checkout" in sbatch
    assert "COTCODEC_REPO:?" in sbatch
    for path in (FETCH, FETCH_SBATCH):
        subprocess.run(["bash", "-n", str(path)], check=True)


def _bash_major(env: dict[str, str]) -> int:
    version = subprocess.run(
        ["bash", "-c", "echo ${BASH_VERSINFO[0]}"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return int(version.stdout.strip())


def test_metadata_fetch_validates_inputs_before_docker(tmp_path: Path) -> None:
    env = {
        "PATH": "/usr/bin:/bin",
        "COTCODEC_IMAGE_ID": "sha256:" + "a" * 64,
        "COTCODEC_MODEL_CACHE_ROOT": str(tmp_path),
    }
    if _bash_major(env) < 4:
        # macOS ships bash 3.2, whose regex engine rejects the cache-root bound
        # {1,511} (above RE_DUP_MAX 255); the lane host runs bash 5.
        pytest.skip("bash < 4 cannot compile the script's cache-root regex")
    unsafe = subprocess.run(["bash", str(FETCH), "../etc"], env=env, capture_output=True, text=True)
    assert unsafe.returncode == 2 and "unsafe" in unsafe.stderr
    no_slurm = subprocess.run(
        ["bash", str(FETCH), "qwen3-8b"], env=env, capture_output=True, text=True
    )
    assert no_slurm.returncode == 2 and "Slurm job step" in no_slurm.stderr


@pytest.mark.parametrize("model_id", ["qwen3-8b", "qwen3.5-27b-fp8", "qwen3.5-35b-a3b-fp8"])
def test_registry_entries_carry_what_vllm_dummy_loading_needs(model_id: str) -> None:
    entry = load_registry()["models"][model_id]
    assert entry["license"] == "apache-2.0" and entry["trust_remote_code"] is False
    metadata = set(entry["metadata_files"])
    assert {"LICENSE", "config.json", "tokenizer.json", "tokenizer_config.json"} <= metadata
    assert not any(name.endswith(".safetensors") for name in metadata)
    if model_id.startswith("qwen3.5"):
        assert {
            "preprocessor_config.json",
            "video_preprocessor_config.json",
            "chat_template.jinja",
        } <= metadata


def _fixups():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "vllm_overlay_fixups", PROJECT_ROOT / "infra" / "research" / "vllm_overlay_fixups.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixups_remove_torchcodec_only_when_its_import_raises_oserror() -> None:
    fixups = _fixups()
    imported: list[str] = []
    commands: list[list[str]] = []

    def broken(module: str) -> None:
        imported.append(module)
        if module == "torchcodec":
            raise OSError("libnvrtc.so.13: cannot open shared object file")

    record = fixups.run_fixups(
        importer=broken,
        runner=lambda argv, check: commands.append(argv),
        version_of=lambda package: "0.17.0",
    )
    assert record["actions"] == [
        {
            "package": "torchcodec",
            "version": "0.17.0",
            "action": "uninstalled",
            "reason": "OSError: libnvrtc.so.13: cannot open shared object file",
        }
    ]
    assert commands and commands[0][-1] == "torchcodec" and "uninstall" in commands[0]
    assert imported[1:] == list(fixups.REQUIRED_IMPORTS)

    commands.clear()
    clean = fixups.run_fixups(
        importer=lambda module: None, runner=lambda argv, check: commands.append(argv)
    )
    assert clean["actions"] == [] and commands == []

    def missing(module: str) -> None:
        if module == "torchcodec":
            raise ImportError("not installed")

    assert (
        fixups.run_fixups(importer=missing, runner=lambda argv, check: commands.append(argv))[
            "actions"
        ]
        == []
    )

    def serving_broken(module: str) -> None:
        if module == "vllm.engine.arg_utils":
            raise OSError("still broken")

    with pytest.raises(OSError, match="still broken"):
        fixups.run_fixups(importer=serving_broken, runner=lambda argv, check: None)


def test_overlay_records_its_fixups_in_the_build_receipt() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert (
        "python infra/research/vllm_overlay_fixups.py /etc/cotcodec-vllm-overlay-fixups.json"
        in dockerfile
    )
    assert dockerfile.index("vllm_overlay_fixups.py") < dockerfile.index("write_provenance.py")
    builder = BUILDER.read_text(encoding="utf-8")
    assert "cat /etc/cotcodec-vllm-overlay-fixups.json" in builder
    assert "run_vllm_throughput_probe.py vllm-args-doctor" in builder
    assert '"vllm-args-doctor.json"' in builder
    assert '"overlay_fixups"' in builder
