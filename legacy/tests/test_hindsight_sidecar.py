from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.memory_trials import SubprocessMemorySystem

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HINDSIGHT_SIDECAR = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "hindsight_sidecar.py"
)
HINDSIGHT_DOCKERFILE = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "hindsight" / "Dockerfile"
)
HINDSIGHT_PROJECT = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "hindsight" / "pyproject.toml"
)
HINDSIGHT_LOCK = (
    PROJECT_ROOT / "infra" / "memory-baselines" / "hindsight" / "uv.lock"
)


def test_hindsight_sidecar_handshake_is_bound_to_reviewed_source() -> None:
    system = SubprocessMemorySystem((sys.executable, str(HINDSIGHT_SIDECAR)))
    assert system.identity == "hindsight-chunk-recall-v1"
    assert (
        system.receipt.implementation_revision
        == "5781d28d8fcc717a15818330b12250b311957000"
    )
    assert system.receipt.backend_id == "pg0-embedded-0.15.1"
    assert system.receipt.publication_ready is False


def test_hindsight_image_uses_an_isolated_reviewed_runtime() -> None:
    dockerfile = HINDSIGHT_DOCKERFILE.read_text()
    assert "ARG COTCODEC_IMAGE" in dockerfile
    assert "COPY --from=hindsight_source" in dockerfile
    assert "UV_PROJECT_ENVIRONMENT=/opt/hindsight-runtime" in dockerfile
    assert "--project infra/memory-baselines/hindsight" in dockerfile
    assert "--no-deps" in dockerfile
    assert "/opt/hindsight-source/hindsight-all" in dockerfile
    assert HINDSIGHT_LOCK.is_file()
    project = HINDSIGHT_PROJECT.read_text()
    assert '"hindsight-api-slim[embedded-db]==0.9.0"' in project
    assert '"hindsight-client==0.9.0"' in project


def test_hindsight_publication_receipt_requires_source_context(tmp_path: Path) -> None:
    common = {
        "COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256": (
            "993a015782322ab0fd336b6ab457d895d74d941390e36ebfd562dec9790bdf9c"
        ),
        "COTCODEC_MEMORY_IMAGE_DIGEST": "sha256:" + "b" * 64,
        "COTCODEC_MEMORY_MODEL_RECEIPT_SHA256S": "a" * 64,
    }
    without_context = SubprocessMemorySystem(
        (sys.executable, str(HINDSIGHT_SIDECAR)), environment=common
    )
    assert without_context.receipt.publication_ready is False

    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "system_id": "hindsight",
                "revision": "5781d28d8fcc717a15818330b12250b311957000",
                "source_archive_sha256": (
                    "993a015782322ab0fd336b6ab457d895d74d941390e36ebfd562dec9790bdf9c"
                ),
                "excluded_unsafe_archive_paths": [
                    "hindsight-integrations/coding-agents/node_modules"
                ],
            }
        )
    )
    with_context = SubprocessMemorySystem(
        (sys.executable, str(HINDSIGHT_SIDECAR)),
        environment={
            **common,
            "COTCODEC_MEMORY_SOURCE_CONTEXT_RECEIPT": str(context),
        },
    )
    assert with_context.receipt.publication_ready is True
