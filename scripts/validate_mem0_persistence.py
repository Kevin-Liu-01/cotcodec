#!/usr/bin/env python3
"""Prove Mem0 native state survives restart and is removed by scoped purge."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    GeneratedMemoryTaskSource,
    MemorySidecarError,
    PersistentSubprocessMemorySystem,
    build_memory_system_request,
)
from scripts.run_deterministic_embedding_server import EmbeddingServer  # noqa: E402


def main() -> int:
    sidecar = PROJECT_ROOT / "infra" / "memory-baselines" / "mem0_sidecar.py"
    server = EmbeddingServer(
        ("127.0.0.1", 0),
        model_id="cotcodec-deterministic-embedding-v1",
        dimensions=32,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    task = GeneratedMemoryTaskSource(seed=7, episode_count=1).load("memory-000000")
    request, _ = build_memory_system_request(
        task,
        visibility="serve",
        treatment_mode="storage_and_service",
    )
    try:
        with tempfile.TemporaryDirectory(prefix="cotcodec-mem0-persistence-") as root:
            environment = {
                "COTCODEC_MEMORY_STATE_ROOT": root,
                "COTCODEC_MEMORY_EMBEDDING_BASE_URL": f"http://{host}:{port}/v1",
                "COTCODEC_MEMORY_EMBEDDING_MODEL": (
                    "cotcodec-deterministic-embedding-v1"
                ),
                "COTCODEC_MEMORY_EMBEDDING_DIMENSIONS": "32",
            }
            with PersistentSubprocessMemorySystem(
                (sys.executable, str(sidecar)),
                timeout_seconds=30,
                environment=environment,
            ) as first_system:
                first = first_system.select(request)
                before_restart = first_system.inspect(task.session_id)

            with PersistentSubprocessMemorySystem(
                (sys.executable, str(sidecar)),
                timeout_seconds=30,
                environment=environment,
            ) as restarted_system:
                restarted = restarted_system.select(request)
                after_restart = restarted_system.inspect(task.session_id)

            with PersistentSubprocessMemorySystem(
                (sys.executable, str(sidecar)),
                timeout_seconds=30,
                environment=environment,
            ) as divergent_system:
                divergent = request.model_copy(
                    update={
                        "events": (
                            request.events[0].model_copy(
                                update={"value": "tampered"}
                            ),
                            *request.events[1:],
                        )
                    }
                )
                divergent_prefix_rejected = False
                try:
                    divergent_system.select(divergent)
                except MemorySidecarError as exc:
                    divergent_prefix_rejected = "different bytes" in str(exc)

            with PersistentSubprocessMemorySystem(
                (sys.executable, str(sidecar)),
                timeout_seconds=30,
                environment=environment,
            ) as purge_system:
                after_rejection = purge_system.inspect(task.session_id)
                purge_system.purge(task.session_id)
                after_purge = purge_system.inspect(task.session_id)

            with PersistentSubprocessMemorySystem(
                (sys.executable, str(sidecar)),
                timeout_seconds=30,
                environment=environment,
            ) as final_system:
                after_purge_restart = final_system.inspect(task.session_id)

        gates = {
            "native_state_created": before_restart["native_memory_count"] > 0,
            "all_prefix_events_committed": (
                before_restart["committed_event_count"] == len(request.events)
            ),
            "journal_unchanged_after_restart": (
                after_restart["journal_sha256"]
                == before_restart["journal_sha256"]
            ),
            "evidence_unchanged_after_restart": (
                [item.text for item in restarted.evidence]
                == [item.text for item in first.evidence]
            ),
            "divergent_committed_prefix_rejected": divergent_prefix_rejected,
            "rejection_left_journal_unchanged": (
                after_rejection["journal_sha256"]
                == before_restart["journal_sha256"]
            ),
            "purge_removed_live_state": after_purge["state_exists"] is False,
            "purge_survived_restart": after_purge_restart["state_exists"] is False,
        }
        status = "MEM0_PERSISTENCE_PASS" if all(gates.values()) else "FAIL"
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": status,
                    "scientific_result": False,
                    "scope": "native-lifecycle-conformance",
                    "backend": "mem0-qdrant-local-persistent",
                    "before_restart": before_restart,
                    "after_restart": after_restart,
                    "after_rejection": after_rejection,
                    "after_purge": after_purge,
                    "after_purge_restart": after_purge_restart,
                    "gates": gates,
                },
                sort_keys=True,
            )
        )
        return 0 if status.endswith("PASS") else 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
