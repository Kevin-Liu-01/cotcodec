#!/usr/bin/env python3
"""Deterministic lifecycle falsifier for the pinned RecMem core."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_REVISION = "a84252f6e5587fd4a8caac03ec9f6c732b7a7f35"
EXPECTED_STATUS = "BLOCKED_NON_IDEMPOTENT_WRITE_MERGE_DATA_LOSS_AND_INCOMPLETE_LINEAGE"


def _topic(text: str) -> int:
    lowered = text.lower()
    if "alpha" in lowered:
        return 0
    if "beta" in lowered:
        return 1
    return 2


def _vector(text: str) -> list[float]:
    vector = [0.0] * 1536
    vector[_topic(text)] = 1.0
    return vector


def _sha(value: Any) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _install_source(source_root: Path) -> None:
    if not source_root.is_dir() or source_root.is_symlink():
        raise RuntimeError("source root must be a regular directory")
    required = {
        "LICENSE",
        "uv.lock",
        "recmem/rec_mem.py",
        "recmem/episodic_memory.py",
        "recmem/vector_store/qdrant.py",
    }
    missing = [name for name in sorted(required) if not (source_root / name).is_file()]
    if missing:
        raise RuntimeError(f"RecMem source is incomplete: {missing}")
    sys.path.insert(0, str(source_root))


def _runtime_types() -> tuple[type[Any], ...]:
    from recmem.embedding import Embedding
    from recmem.llm import LLMClient, LLMResponse

    class DeterministicEmbedding(Embedding):
        fail_merged = False

        def embed(self, text: str) -> list[float]:
            if self.fail_merged and text.startswith("MERGED_ALPHA"):
                raise RuntimeError("injected replacement-embedding failure")
            return _vector(text)

        def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [self.embed(text) for text in texts]

        @property
        def dim(self) -> int:
            return 1536

    class DeterministicLLM(LLMClient):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def chat_completion(
            self,
            *,
            model: str,
            messages: list[Any],
            temperature: float = 0.0,
            json_mode: bool = False,
            monitor: Any = None,
            op_type: Any = None,
            max_retries: int = 3,
            retry_delay: float = 1.0,
        ) -> Any:
            del model, temperature, json_mode, monitor, max_retries, retry_delay
            name = getattr(op_type, "name", "UNKNOWN")
            self.calls.append(name)
            prompt = messages[0].content if messages else ""
            topic = "ALPHA" if "alpha" in prompt.lower() else "BETA"
            if name == "EPISODIC_GENERATION":
                payload = {"episodes": [f"EPISODE_{topic}"]}
            elif name == "EPISODIC_MERGE":
                payload = {
                    "should_merge": "yes",
                    "merged_memory": f"MERGED_{topic}",
                }
            elif name in {
                "SEMANTIC_EXTRACTION",
                "SEMANTIC_EXTRACTION_DURING_MERGE",
            }:
                payload = {"facts": [f"FACT_{topic}"]}
            else:
                payload = {}
            return LLMResponse(
                content=json.dumps(payload, sort_keys=True),
                finish_reason="stop",
                usage=None,
            )

    return DeterministicEmbedding, DeterministicLLM


def _config(root: Path) -> Any:
    from recmem.rec_mem import RecMemConfig

    return RecMemConfig(
        min_consolidation_cnt=3,
        min_relevant_score=0.99,
        merge_with_epi_thresh=0.99,
        retrieve_raw_topk=10,
        retrieve_epi_topk=5,
        semantic_memory_topk=10,
        semantic_memory_threshold=0.0,
        semantic_store=str(root / "semantic"),
        subconscious_store=str(root / "subconscious"),
        episodic_store=str(root / "episodic"),
    )


def _new_system(root: Path, embedder: Any, llm: Any) -> Any:
    from recmem.rec_mem import RecMem

    return RecMem(_config(root), embedder=embedder, llm_client=llm)


def _close(system: Any) -> None:
    for store in (
        system.subconscious_memory.vec_store,
        system.episodic_mem.vec_store,
        system.semantic_memory.vec_store,
    ):
        close = getattr(store.client, "close", None)
        if callable(close):
            close()


def _memories(system: Any, layer: str, conv_id: str) -> list[str]:
    owner = {
        "subconscious": system.subconscious_memory,
        "episodic": system.episodic_mem,
        "semantic": system.semantic_memory,
    }[layer]
    return sorted(owner.vec_store.list_memories(conv_id))


def _run_once(state_root: Path) -> dict[str, Any]:
    DeterministicEmbedding, DeterministicLLM = _runtime_types()
    state_root.mkdir(parents=True, exist_ok=False)
    embedder = DeterministicEmbedding()
    llm = DeterministicLLM()
    system = _new_system(state_root, embedder, llm)

    # One retry of the exact same write creates a second record because the API
    # has no idempotency key or caller-owned record identity.
    retry_conv = "retry-conversation"
    system.add_memory("alpha retry canary", "2026-08-16T00:00:00Z", retry_conv)
    system.add_memory("alpha retry canary", "2026-08-16T00:00:00Z", retry_conv)
    duplicate_retry_count = len(_memories(system, "subconscious", retry_conv))

    # Three recurrent messages trigger one episode. The trigger is included in
    # rendered text but its ID is absent from the native raw_ids provenance.
    lineage_conv = "lineage-conversation"
    for index in range(3):
        system.add_memory(
            f"alpha lineage canary {index}",
            f"2026-08-16T00:0{index}:00Z",
            lineage_conv,
        )
    hits = system.episodic_mem.vec_store.search(
        q_embedding=_vector("alpha"),
        top_k=5,
        collection_name=lineage_conv,
    )
    if len(hits) != 1:
        raise RuntimeError(f"expected one lineage episode, found {len(hits)}")
    lineage = hits[0].extra_payload
    recorded_raw_ids = lineage.get("raw_ids")
    conversation = lineage.get("conversation")
    if not isinstance(recorded_raw_ids, list) or not isinstance(conversation, str):
        raise RuntimeError("episodic lineage payload drifted")

    # A replacement merge removes the old episode before embedding the new one.
    # Injecting an embedding failure proves the old durable record is lost.
    merge_conv = "merge-conversation"
    for index in range(3):
        system.add_memory(
            f"alpha merge canary {index}",
            f"2026-08-16T01:0{index}:00Z",
            merge_conv,
        )
    before_merge = _memories(system, "episodic", merge_conv)
    embedder.fail_merged = True
    system.add_memory(
        "alpha merge canary update",
        "2026-08-16T01:03:00Z",
        merge_conv,
    )
    after_failed_merge = _memories(system, "episodic", merge_conv)
    raw_after_failed_merge = _memories(system, "subconscious", merge_conv)

    # Conversation collections must still isolate unrelated tenants.
    isolated = system.search_memories(
        "alpha", "unseen-conversation", question_embedding=_vector("alpha")
    )
    isolation_ok = not (
        isolated.subconscious or isolated.episodic or isolated.semantic
    )

    _close(system)
    restarted_embedder = DeterministicEmbedding()
    restarted_llm = DeterministicLLM()
    restarted = _new_system(state_root, restarted_embedder, restarted_llm)
    restart_episode = _memories(restarted, "episodic", lineage_conv)
    restart_semantic = _memories(restarted, "semantic", lineage_conv)
    restart_ok = restart_episode == ["EPISODE_ALPHA"] and restart_semantic == [
        "FACT_ALPHA"
    ]
    _close(restarted)

    checks = {
        "duplicate_retry_created_two_records": duplicate_retry_count == 2,
        "recurrence_created_episode": hits[0].content == "EPISODE_ALPHA",
        "trigger_present_in_episode_text": "alpha lineage canary 2" in conversation,
        "trigger_missing_from_raw_id_lineage": len(recorded_raw_ids) == 2,
        "failed_merge_deleted_prior_episode": before_merge == ["EPISODE_ALPHA"]
        and after_failed_merge == [],
        "failed_merge_fell_back_to_raw_write": len(raw_after_failed_merge) == 1,
        "conversation_isolation_preserved": isolation_ok,
        "fresh_process_preserved_successful_consolidation": restart_ok,
        "no_provider_or_model_backend_used": set(llm.calls).issubset(
            {
                "EPISODIC_GENERATION",
                "EPISODIC_MERGE",
                "SEMANTIC_EXTRACTION",
                "SEMANTIC_EXTRACTION_DURING_MERGE",
            }
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"RecMem falsification checks drifted: {checks}")

    projection = {
        "checks": checks,
        "duplicate_retry_count": duplicate_retry_count,
        "lineage_recorded_raw_id_count": len(recorded_raw_ids),
        "lineage_rendered_message_count": conversation.count("[Message Timestamp]"),
        "llm_operation_counts": {
            name: llm.calls.count(name) for name in sorted(set(llm.calls))
        },
        "merge_before_count": len(before_merge),
        "merge_after_failure_count": len(after_failed_merge),
        "merge_raw_fallback_count": len(raw_after_failed_merge),
    }
    return {
        "schema_version": 1,
        "system_id": "recmem-a84252f-recurrence-lifecycle-v1",
        "source_revision": EXPECTED_REVISION,
        "status": EXPECTED_STATUS,
        "scientific_result": False,
        "publication_ready": False,
        "h100_actor_admission": False,
        "provider_calls": 0,
        "model_backend_calls": 0,
        "projection": projection,
        "projection_sha256": _sha(projection),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--repeat", type=int, required=True, choices=(1, 2))
    args = parser.parse_args()
    _install_source(args.source_root.resolve())
    report = _run_once(args.state_root.resolve() / f"repeat-{args.repeat}")
    print("COTCODEC_RECMEM_REPORT=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
