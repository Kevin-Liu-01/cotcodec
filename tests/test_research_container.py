from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = PROJECT_ROOT / "infra" / "research" / "Dockerfile"
SOURCE_OVERLAY_DOCKERFILE = (
    PROJECT_ROOT / "infra" / "research" / "Dockerfile.source-overlay"
)
SOURCE_OVERLAY_BUILDER = PROJECT_ROOT / "scripts" / "build_source_overlay_on_h100.sh"
MEM0_OVERLAY_BUILDER = PROJECT_ROOT / "scripts" / "build_mem0_overlay_on_h100.sh"


def test_research_image_accepts_normal_json_argv() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert 'ENTRYPOINT ["/bin/bash", "-lc"]' not in content
    assert 'CMD ["python", "scripts/check_harness_env.py"]' in content


def test_research_image_dev_dependencies_are_explicit_and_default_off() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert "ARG INCLUDE_DEV=false" in content
    assert 'org.opencontainers.image.cotcodec-dev-dependencies="${INCLUDE_DEV}"' in content
    assert 'if [ "${INCLUDE_DEV}" = "true" ]; then dev_flag="--dev"' in content


def test_source_overlay_records_profile_and_dev_dependency_contract() -> None:
    content = SOURCE_OVERLAY_DOCKERFILE.read_text(encoding="utf-8")
    assert "ARG UV_EXTRA=architecture" in content
    assert "ARG INCLUDE_DEV=false" in content
    assert "ARG GIT_TREE=unknown" in content
    assert 'cotcodec-git-sha="${GIT_SHA}"' in content
    assert 'cotcodec-git-tree="${GIT_TREE}"' in content
    assert 'cotcodec-runtime-profile="${UV_EXTRA}-source-overlay"' in content
    assert 'cotcodec-dev-dependencies="${INCLUDE_DEV}"' in content
    assert 'if [ "${INCLUDE_DEV}" = "true" ]; then dev_flag="--dev"' in content
    assert 'if [ "${UV_EXTRA}" = "none" ]; then' in content
    assert 'uv sync --frozen "${dev_flag}" --extra "${UV_EXTRA}"' in content
    assert "find /workspace/cotcodec -mindepth 1 -maxdepth 1" in content
    assert "! -name .venv -exec rm -rf -- {} +" in content
    assert "cotcodec-source-overlay-venv" not in content
    assert "COPY . /workspace/cotcodec" in content


def test_overlay_builders_make_normalized_archive_readable_to_container_uid() -> None:
    for path in (SOURCE_OVERLAY_BUILDER, MEM0_OVERLAY_BUILDER):
        content = path.read_text(encoding="utf-8")
        assert '${SLURM_JOB_ID:?Run this build through Slurm}' in content
        assert 'chmod -R a+rX "${context}"' in content
        assert "sudo" not in content


def test_source_overlay_builder_refuses_stale_context_and_validates_receipt() -> None:
    content = SOURCE_OVERLAY_BUILDER.read_text(encoding="utf-8")
    assert '${COTCODEC_SOURCE_RECEIPT:?Set the retained source receipt path}' in content
    assert '${COTCODEC_SOURCE_EXTRACTOR:?Set the retained source extractor path}' in content
    assert '${COTCODEC_SOURCE_EXTRACTOR_SHA256:?' in content
    assert '${COTCODEC_SOURCE_BUILDER_SHA256:?' in content
    assert "refusing to reuse source-overlay build root" in content
    assert 'python3 "${extractor_snapshot}"' in content
    assert 'BASE_IMAGE=${COTCODEC_BASE_IMAGE_TAG}' in content
    assert '@sha256:[0-9a-f]{64}' in content
    assert "--pull=false" in content
    assert 'tar -xzf "${COTCODEC_SOURCE_ARCHIVE}"' not in content


@pytest.mark.parametrize("drifted_input", ["builder", "extractor"])
def test_source_overlay_builder_rejects_unbound_helpers(
    tmp_path: Path, drifted_input: str
) -> None:
    extractor = tmp_path / "extractor.py"
    extractor.write_text("raise SystemExit(99)\n", encoding="utf-8")
    builder_sha256 = hashlib.sha256(SOURCE_OVERLAY_BUILDER.read_bytes()).hexdigest()
    extractor_sha256 = hashlib.sha256(extractor.read_bytes()).hexdigest()
    if drifted_input == "builder":
        builder_sha256 = "0" * 64
    else:
        extractor_sha256 = "0" * 64
    env = {
        **os.environ,
        "SLURM_JOB_ID": "123",
        "COTCODEC_SOURCE_ARCHIVE": str(tmp_path / "source.tar.gz"),
        "COTCODEC_SOURCE_RECEIPT": str(tmp_path / "source.json"),
        "COTCODEC_SOURCE_EXTRACTOR": str(extractor),
        "COTCODEC_SOURCE_EXTRACTOR_SHA256": extractor_sha256,
        "COTCODEC_SOURCE_BUILDER_SHA256": builder_sha256,
        "COTCODEC_SOURCE_SHA256": "1" * 64,
        "COTCODEC_GIT_SHA": "2" * 40,
        "COTCODEC_GIT_TREE": "3" * 40,
        "COTCODEC_BASE_IMAGE_TAG": "local.invalid/base@sha256:" + "5" * 64,
        "COTCODEC_BASE_IMAGE_ID": "sha256:" + "4" * 64,
        "COTCODEC_BUILD_ROOT": str(tmp_path / "build"),
    }
    result = subprocess.run(
        ["bash", str(SOURCE_OVERLAY_BUILDER)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "builder or extractor digest mismatch" in result.stderr
