from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

from harness.memory_trials import (
    GeneratedMemoryTaskSource,
    MemorySidecarError,
    PersistentSubprocessMemorySystem,
    SubprocessMemorySystem,
    build_memory_system_request,
)
from scripts.run_deterministic_embedding_server import EmbeddingServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEM0_SIDECAR = PROJECT_ROOT / "infra" / "memory-baselines" / "mem0_sidecar.py"
MEM0_DOCKERFILE = PROJECT_ROOT / "infra" / "memory-baselines" / "mem0" / "Dockerfile"


def test_mem0_sidecar_handshake_is_bound_to_reviewed_source() -> None:
    system = SubprocessMemorySystem((sys.executable, str(MEM0_SIDECAR)))
    assert system.identity == "mem0-raw-retrieval-v2"
    assert (
        system.receipt.implementation_revision
        == "71f2ebefa3494da21550fb525216818776cde67f"
    )
    assert system.receipt.publication_ready is False
    assert system.receipt.source_archive_sha256 is None


def test_mem0_image_uses_named_reviewed_source_not_pypi_code() -> None:
    dockerfile = MEM0_DOCKERFILE.read_text()
    assert "ARG COTCODEC_IMAGE" in dockerfile
    assert "FROM ${COTCODEC_IMAGE}" in dockerfile
    assert "COPY --from=mem0_source" in dockerfile
    assert "--extra memory-mem0 --no-install-package mem0ai" in dockerfile
    assert "--no-deps /opt/mem0-source" in dockerfile
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
    assert '"mem0ai==2.0.18"' in pyproject


def test_mem0_publication_receipt_requires_verified_source_context(tmp_path: Path) -> None:
    common = {
        "COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256": (
            "c577ecf9a460b0fa581032037ccbfd887f7a7d0afa0fc091d13fd8b692089b12"
        ),
        "COTCODEC_MEMORY_IMAGE_DIGEST": "sha256:" + "b" * 64,
        "COTCODEC_MEMORY_MODEL_RECEIPT_SHA256S": "a" * 64,
    }
    without_context = SubprocessMemorySystem(
        (sys.executable, str(MEM0_SIDECAR)), environment=common
    )
    assert without_context.receipt.publication_ready is False

    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "system_id": "mem0",
                "revision": "71f2ebefa3494da21550fb525216818776cde67f",
                "source_archive_sha256": (
                    "c577ecf9a460b0fa581032037ccbfd887f7a7d0afa0fc091d13fd8b692089b12"
                ),
            }
        )
    )
    with_context = SubprocessMemorySystem(
        (sys.executable, str(MEM0_SIDECAR)),
        environment={
            **common,
            "COTCODEC_MEMORY_SOURCE_CONTEXT_RECEIPT": str(context),
        },
    )
    assert with_context.receipt.publication_ready is True


def test_mem0_persists_across_restart_and_purges_native_state(tmp_path: Path) -> None:
    server = EmbeddingServer(
        ("127.0.0.1", 0), model_id="test-embedding", dimensions=16
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    environment = {
        "COTCODEC_MEMORY_STATE_ROOT": str(tmp_path / "state"),
        "COTCODEC_MEMORY_EMBEDDING_BASE_URL": f"http://{host}:{port}/v1",
        "COTCODEC_MEMORY_EMBEDDING_MODEL": "test-embedding",
        "COTCODEC_MEMORY_EMBEDDING_DIMENSIONS": "16",
    }
    task = GeneratedMemoryTaskSource(seed=7, episode_count=1).load("memory-000000")
    request, _ = build_memory_system_request(
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    try:
        with PersistentSubprocessMemorySystem(
            (sys.executable, str(MEM0_SIDECAR)),
            timeout_seconds=30,
            environment=environment,
        ) as first_system:
            first = first_system.select(request)
            first_inspection = first_system.inspect(task.session_id)
            assert first_inspection["state_exists"] is True
            assert first_inspection["native_memory_count"] > 0
            assert first_inspection["committed_event_count"] == len(request.events)

        with PersistentSubprocessMemorySystem(
            (sys.executable, str(MEM0_SIDECAR)),
            timeout_seconds=30,
            environment=environment,
        ) as restarted_system:
            restarted = restarted_system.select(request)
            restarted_inspection = restarted_system.inspect(task.session_id)
            assert [item.text for item in restarted.evidence] == [
                item.text for item in first.evidence
            ]
            assert restarted_inspection["journal_sha256"] == first_inspection[
                "journal_sha256"
            ]

        with PersistentSubprocessMemorySystem(
            (sys.executable, str(MEM0_SIDECAR)),
            timeout_seconds=30,
            environment=environment,
        ) as divergent_system:
            divergent = request.model_copy(
                update={
                    "events": (
                        request.events[0].model_copy(update={"value": "tampered"}),
                        *request.events[1:],
                    )
                }
            )
            with pytest.raises(MemorySidecarError, match="different bytes"):
                divergent_system.select(divergent)

        with PersistentSubprocessMemorySystem(
            (sys.executable, str(MEM0_SIDECAR)),
            timeout_seconds=30,
            environment=environment,
        ) as purge_system:
            assert purge_system.inspect(task.session_id)["journal_sha256"] == (
                first_inspection["journal_sha256"]
            )
            purge_system.purge(task.session_id)
            assert purge_system.inspect(task.session_id) == {
                "scope_sha256": first_inspection["scope_sha256"],
                "state_exists": False,
                "native_memory_count": 0,
                "committed_event_count": 0,
            }

        with PersistentSubprocessMemorySystem(
            (sys.executable, str(MEM0_SIDECAR)),
            timeout_seconds=30,
            environment=environment,
        ) as after_purge_system:
            assert after_purge_system.inspect(task.session_id)["state_exists"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
