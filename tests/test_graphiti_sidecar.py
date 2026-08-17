from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.memory_trials import SubprocessMemorySystem

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GRAPHITI_SIDECAR = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "graphiti_sidecar.py"
)
GRAPHITI_DOCKERFILE = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "graphiti" / "Dockerfile"
)


def test_graphiti_sidecar_handshake_is_bound_to_reviewed_source() -> None:
    system = SubprocessMemorySystem((sys.executable, str(GRAPHITI_SIDECAR)))
    assert system.identity == "graphiti-explicit-triplet-v1"
    assert (
        system.receipt.implementation_revision
        == "401c59a65bdeb22a44136901ff30231e6998a7fe"
    )
    assert system.receipt.backend_id == "falkordblite-0.10.0-ephemeral"
    assert system.receipt.publication_ready is False


def test_graphiti_image_installs_reviewed_source_context() -> None:
    dockerfile = GRAPHITI_DOCKERFILE.read_text()
    assert "ARG COTCODEC_IMAGE" in dockerfile
    assert "COPY --from=graphiti_source" in dockerfile
    assert "--extra memory-graphiti --no-install-package graphiti-core" in dockerfile
    assert "--no-deps /opt/graphiti-source" in dockerfile
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
    assert '"graphiti-core[falkordblite]==0.29.3"' in pyproject


def test_graphiti_publication_receipt_requires_source_context(tmp_path: Path) -> None:
    common = {
        "COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256": (
            "9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303"
        ),
        "COTCODEC_MEMORY_IMAGE_DIGEST": "sha256:" + "b" * 64,
        "COTCODEC_MEMORY_MODEL_RECEIPT_SHA256S": "a" * 64,
    }
    without_context = SubprocessMemorySystem(
        (sys.executable, str(GRAPHITI_SIDECAR)), environment=common
    )
    assert without_context.receipt.publication_ready is False

    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "system_id": "graphiti",
                "revision": "401c59a65bdeb22a44136901ff30231e6998a7fe",
                "source_archive_sha256": (
                    "9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303"
                ),
            }
        )
    )
    with_context = SubprocessMemorySystem(
        (sys.executable, str(GRAPHITI_SIDECAR)),
        environment={
            **common,
            "COTCODEC_MEMORY_SOURCE_CONTEXT_RECEIPT": str(context),
        },
    )
    assert with_context.receipt.publication_ready is True
