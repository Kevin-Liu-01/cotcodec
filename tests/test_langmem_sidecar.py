from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.memory_trials import SubprocessMemorySystem

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LANGMEM_SIDECAR = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "langmem_sidecar.py"
)
LANGMEM_DOCKERFILE = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "langmem" / "Dockerfile"
)


def test_langmem_sidecar_handshake_is_bound_to_reviewed_source() -> None:
    system = SubprocessMemorySystem((sys.executable, str(LANGMEM_SIDECAR)))
    assert system.identity == "langmem-tools-store-v1"
    assert (
        system.receipt.implementation_revision
        == "29cbe41e58528f92e9efa773c12e15c47be3808c"
    )
    assert system.receipt.backend_id == "langgraph-in-memory-store-1.2.11"
    assert system.receipt.publication_ready is False


def test_langmem_image_installs_reviewed_source_context() -> None:
    dockerfile = LANGMEM_DOCKERFILE.read_text()
    assert "ARG COTCODEC_IMAGE" in dockerfile
    assert "COPY --from=langmem_source" in dockerfile
    assert "--extra memory-langmem --no-install-package langmem" in dockerfile
    assert "--no-deps /opt/langmem-source" in dockerfile
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
    assert '"langmem==0.0.30"' in pyproject


def test_langmem_publication_receipt_requires_source_context(tmp_path: Path) -> None:
    common = {
        "COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256": (
            "24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521"
        ),
        "COTCODEC_MEMORY_IMAGE_DIGEST": "sha256:" + "b" * 64,
        "COTCODEC_MEMORY_MODEL_RECEIPT_SHA256S": "a" * 64,
    }
    without_context = SubprocessMemorySystem(
        (sys.executable, str(LANGMEM_SIDECAR)), environment=common
    )
    assert without_context.receipt.publication_ready is False

    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "system_id": "langmem",
                "revision": "29cbe41e58528f92e9efa773c12e15c47be3808c",
                "source_archive_sha256": (
                    "24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521"
                ),
            }
        )
    )
    with_context = SubprocessMemorySystem(
        (sys.executable, str(LANGMEM_SIDECAR)),
        environment={
            **common,
            "COTCODEC_MEMORY_SOURCE_CONTEXT_RECEIPT": str(context),
        },
    )
    assert with_context.receipt.publication_ready is True
