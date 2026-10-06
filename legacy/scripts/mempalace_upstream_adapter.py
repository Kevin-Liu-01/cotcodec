#!/usr/bin/env python3
"""Production adapter from the MemPalace retrieval port to its pinned raw runner."""

from __future__ import annotations

import contextlib
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials.mempalace_control import (  # noqa: E402
    MEMPALACE_UPSTREAM_RETRIEVAL_LIMIT,
    MemPalaceRetrievalBatch,
    MemPalaceRuntimeIdentity,
    MemPalaceSessionDocument,
)
from scripts.run_mempalace_upstream_reproduction import (  # noqa: E402
    ReproductionExpectations,
    _load_runtime_receipt,
    _load_upstream_retriever,
)

RawRetriever = Callable[
    [dict[str, Any]], tuple[list[int], list[str], list[str], list[str]]
]


class PinnedUpstreamMemPalaceAdapter:
    """Execute the exact reviewed raw runner behind the task-blind retrieval port."""

    def __init__(
        self,
        *,
        source_root: Path,
        runtime_receipt_path: Path,
        expected_runtime_receipt_sha256: str,
        implementation_kind: str,
    ) -> None:
        expectations = ReproductionExpectations()
        runtime, runtime_sha256 = _load_runtime_receipt(
            runtime_receipt_path, expectations
        )
        if runtime_sha256 != expected_runtime_receipt_sha256:
            raise ValueError("MemPalace runtime receipt differs from the registered study")
        self.identity = MemPalaceRuntimeIdentity(
            model_artifact_root_sha256=runtime[
                "embedding_artifact_root_sha256"
            ],
            model_receipt_sha256=runtime["minilm_receipt_sha256"],
            image_digest=runtime["image_id"],
            implementation_kind=implementation_kind,
        )
        self._retrieve = _load_upstream_retriever(source_root, expectations)

    @classmethod
    def from_retriever(
        cls,
        *,
        identity: MemPalaceRuntimeIdentity,
        retrieve: RawRetriever,
    ) -> PinnedUpstreamMemPalaceAdapter:
        """Construct the production adapter around a deterministic test retriever."""

        instance = cls.__new__(cls)
        instance.identity = identity
        instance._retrieve = retrieve
        return instance

    def retrieve(
        self,
        *,
        query: str,
        documents: Sequence[MemPalaceSessionDocument],
        n_results: int,
    ) -> MemPalaceRetrievalBatch:
        if not query or not documents:
            raise ValueError("MemPalace retrieval requires a query and session documents")
        expected_n_results = min(MEMPALACE_UPSTREAM_RETRIEVAL_LIMIT, len(documents))
        if n_results != expected_n_results:
            raise ValueError("MemPalace retrieval count differs from the raw runner contract")
        document_ids = [document.document_id for document in documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("MemPalace session document IDs must be unique")
        entry = {
            "question": query,
            "haystack_sessions": [
                [{"role": "user", "content": document.text}]
                for document in documents
            ],
            "haystack_session_ids": document_ids,
            "haystack_dates": [str(document.last_step) for document in documents],
        }
        started = time.perf_counter()
        with contextlib.redirect_stdout(sys.stderr):
            rankings, corpus, corpus_ids, _timestamps = self._retrieve(entry)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if corpus != [document.text for document in documents] or corpus_ids != document_ids:
            raise ValueError("pinned MemPalace runner changed its session corpus")
        if len(rankings) != len(documents) or sorted(rankings) != list(
            range(len(documents))
        ):
            raise ValueError("pinned MemPalace runner returned an invalid ranking")
        ranked_ids = tuple(corpus_ids[index] for index in rankings[:n_results])
        return MemPalaceRetrievalBatch(
            ranked_document_ids=ranked_ids,
            # The reviewed runner exposes only order, not Chroma distances.
            distances=tuple(float(index) for index in range(len(ranked_ids))),
            embedding_input_count=len(documents) + 1,
            collection_write_count=len(documents),
            latency_ms=elapsed_ms,
        )
