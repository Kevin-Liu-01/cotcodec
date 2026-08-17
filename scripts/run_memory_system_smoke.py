#!/usr/bin/env python3
"""Run and seal a CPU-only memory-system-v1 integration smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory_trials import (  # noqa: E402
    GeneratedMemoryTaskSource,
    ReferenceMemorySystem,
    SubprocessMemorySystem,
    run_memory_system,
)
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402

DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data" / "results" / "memory-baselines" / "native-smoke.json"
)
MEM0_SOURCE_ARCHIVE_SHA256 = "c577ecf9a460b0fa581032037ccbfd887f7a7d0afa0fc091d13fd8b692089b12"
GRAPHITI_SOURCE_ARCHIVE_SHA256 = (
    "9cfbc01e90f4e6dfbf61fefe86e7f04b15c57c08a7ff8298f873d6f5696d0303"
)
LANGMEM_SOURCE_ARCHIVE_SHA256 = (
    "24c85c514c80bb263a16626971e8ef53978fd1bc7f9319e47d8a5a0bf4956521"
)
HINDSIGHT_SOURCE_ARCHIVE_SHA256 = (
    "993a015782322ab0fd336b6ab457d895d74d941390e36ebfd562dec9790bdf9c"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError(f"refusing to overwrite smoke artifact: {path}")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    encoded = (canonical_json(payload) + "\n").encode()
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _semantic_evidence(run: Any) -> list[dict[str, Any]]:
    return [
        {
            "evidence_id": evidence.evidence_id,
            "text": evidence.text,
            "source_record_ids": list(evidence.source_record_ids),
            "kind": evidence.kind,
        }
        for evidence in run.evidence
    ]


def _maximum_score_delta(first: Any, repeated: Any) -> float | None:
    if len(first.evidence) != len(repeated.evidence):
        return None
    return max(
        (
            abs(left.score - right.score)
            for left, right in zip(first.evidence, repeated.evidence, strict=True)
        ),
        default=0.0,
    )


def _embedding_provenance(
    *,
    base_url: str | None,
    model: str,
    dimensions: int,
    receipt_path: Path | None,
) -> dict[str, Any] | None:
    if base_url is None:
        if receipt_path is not None:
            raise ValueError("embedding receipt requires an embedding service")
        return None
    health_url = base_url.removesuffix("/v1").rstrip("/") + "/health"
    response = httpx.get(health_url, timeout=30.0)
    response.raise_for_status()
    health = response.json()
    if not isinstance(health, dict):
        raise ValueError("embedding health response must be an object")
    if health.get("status") != "ok":
        raise ValueError("embedding service is not healthy")
    if health.get("model") != model or health.get("dimensions") != dimensions:
        raise ValueError("embedding service identity differs from the requested model")
    if model == "BAAI/bge-small-en-v1.5" and (
        health.get("maximum_tokens") != 512
        or health.get("pooling_strategy") != "cls-l2-normalized-v1"
    ):
        raise ValueError("BGE embedding runtime policy differs from the model contract")
    provenance: dict[str, Any] = {"health": health, "health_url": health_url}
    if receipt_path is None:
        if health.get("publication_eligible"):
            raise ValueError("publication-eligible embedding service requires a receipt")
        provenance["publication_eligible"] = False
        return provenance

    receipt_path = receipt_path.resolve()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise ValueError("embedding receipt must be an object")
    expected = {
        "model_id": health.get("registry_model_id"),
        "revision": health.get("revision"),
        "artifact_root_sha256": health.get("artifact_root_sha256"),
        "mode": "full",
        "publication_eligible": True,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("embedding receipt differs from the running service")
    receipt_sha256 = _sha256_file(receipt_path)
    if health.get("model_receipt_sha256") != receipt_sha256:
        raise ValueError("embedding service receipt digest differs from the supplied receipt")
    provenance.update(
        {
            "receipt": receipt,
            "receipt_sha256": receipt_sha256,
            "publication_eligible": True,
        }
    )
    return provenance


def run_smoke(
    *,
    system_id: str,
    task_id: str,
    embedding_base_url: str | None,
    embedding_model: str,
    embedding_dimensions: int,
    embedding_receipt_path: Path | None = None,
) -> dict[str, Any]:
    embedding_provenance = _embedding_provenance(
        base_url=embedding_base_url,
        model=embedding_model,
        dimensions=embedding_dimensions,
        receipt_path=embedding_receipt_path,
    )
    embedding_revision = (
        embedding_provenance["health"].get("revision")
        if embedding_provenance is not None
        else None
    )
    embedding_receipt_sha256 = (
        embedding_provenance.get("receipt_sha256")
        if embedding_provenance is not None
        else None
    )
    common_embedding_environment = {
        "COTCODEC_MEMORY_EMBEDDING_MODEL": embedding_model,
        "COTCODEC_MEMORY_EMBEDDING_DIMENSIONS": str(embedding_dimensions),
        **(
            {"COTCODEC_MEMORY_EMBEDDING_REVISION": embedding_revision}
            if isinstance(embedding_revision, str)
            else {}
        ),
        **(
            {"COTCODEC_MEMORY_MODEL_RECEIPT_SHA256S": embedding_receipt_sha256}
            if isinstance(embedding_receipt_sha256, str)
            else {}
        ),
    }
    if system_id == "reference":
        system: Any = ReferenceMemorySystem()
    elif system_id == "mem0":
        if not embedding_base_url:
            raise ValueError("Mem0 smoke requires --embedding-base-url")
        sidecar = PROJECT_ROOT / "infra" / "memory-baselines" / "mem0_sidecar.py"
        system = SubprocessMemorySystem(
            (sys.executable, str(sidecar)),
            timeout_seconds=300,
            environment={
                **common_embedding_environment,
                "COTCODEC_MEMORY_EMBEDDING_BASE_URL": embedding_base_url,
                "COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256": MEM0_SOURCE_ARCHIVE_SHA256,
            },
        )
    elif system_id == "graphiti":
        if not embedding_base_url:
            raise ValueError("Graphiti smoke requires --embedding-base-url")
        sidecar = PROJECT_ROOT / "infra" / "memory-baselines" / "graphiti_sidecar.py"
        system = SubprocessMemorySystem(
            (sys.executable, str(sidecar)),
            timeout_seconds=300,
            environment={
                **common_embedding_environment,
                "COTCODEC_MEMORY_EMBEDDING_BASE_URL": embedding_base_url,
                "COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256": (
                    GRAPHITI_SOURCE_ARCHIVE_SHA256
                ),
                "EMBEDDING_DIM": str(embedding_dimensions),
            },
        )
    elif system_id == "langmem":
        if not embedding_base_url:
            raise ValueError("LangMem smoke requires --embedding-base-url")
        sidecar = PROJECT_ROOT / "infra" / "memory-baselines" / "langmem_sidecar.py"
        system = SubprocessMemorySystem(
            (sys.executable, str(sidecar)),
            timeout_seconds=300,
            environment={
                **common_embedding_environment,
                "COTCODEC_MEMORY_EMBEDDING_BASE_URL": embedding_base_url,
                "COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256": (
                    LANGMEM_SOURCE_ARCHIVE_SHA256
                ),
            },
        )
    elif system_id == "hindsight":
        if not embedding_base_url:
            raise ValueError("Hindsight smoke requires --embedding-base-url")
        sidecar = PROJECT_ROOT / "infra" / "memory-baselines" / "hindsight_sidecar.py"
        hindsight_python = PROJECT_ROOT / ".venv-hindsight" / "bin" / "python"
        if not hindsight_python.is_file():
            raise ValueError(
                "Hindsight smoke requires the isolated .venv-hindsight runtime"
            )
        stats_url = embedding_base_url.removesuffix("/v1").rstrip("/") + "/stats"
        system = SubprocessMemorySystem(
            (str(hindsight_python), str(sidecar)),
            timeout_seconds=300,
            environment={
                **common_embedding_environment,
                "COTCODEC_MEMORY_EMBEDDING_BASE_URL": embedding_base_url,
                "COTCODEC_MEMORY_EMBEDDING_STATS_URL": stats_url,
                "COTCODEC_MEMORY_SOURCE_ARCHIVE_SHA256": (
                    HINDSIGHT_SOURCE_ARCHIVE_SHA256
                ),
            },
        )
    else:
        raise ValueError(f"unknown memory system: {system_id}")

    source = GeneratedMemoryTaskSource(seed=7, episode_count=4)
    task = source.load(task_id)
    cells: list[dict[str, Any]] = []
    aa_semantic_replay = True
    score_drift_threshold = 1e-5
    for treatment_mode in ("serve_only", "storage_and_service"):
        for visibility in ("serve", "holdout"):
            first = run_memory_system(
                system,
                task,
                visibility=visibility,
                treatment_mode=treatment_mode,
            )
            repeated = run_memory_system(
                system,
                task,
                visibility=visibility,
                treatment_mode=treatment_mode,
            )
            semantic_match = _semantic_evidence(first) == _semantic_evidence(repeated)
            receipt_match = first.receipt == repeated.receipt
            maximum_score_delta = _maximum_score_delta(first, repeated)
            score_drift_ok = (
                maximum_score_delta is not None
                and maximum_score_delta <= score_drift_threshold
            )
            aa_semantic_replay &= semantic_match and receipt_match and score_drift_ok
            cells.append(
                {
                    "treatment_mode": treatment_mode,
                    "visibility": visibility,
                    "first": first.model_dump(mode="json"),
                    "repeat": repeated.model_dump(mode="json"),
                    "semantic_evidence_match": semantic_match,
                    "receipt_match": receipt_match,
                    "maximum_score_delta": maximum_score_delta,
                    "score_drift_within_threshold": score_drift_ok,
                    "latency_excluded_from_aa_equality": True,
                }
            )
    source_preflight = (
        PROJECT_ROOT
        / "data"
        / "results"
        / "memory-baselines"
        / "source-preflight.json"
    )
    first_evidence = [
        evidence
        for cell in cells
        for evidence in cell["first"]["evidence"]
    ]
    payload = {
        "schema_version": "1.0",
        "status": "NATIVE_INTERFACE_SMOKE_PASS" if aa_semantic_replay else "FAIL",
        "scientific_evidence": False,
        "reason": (
            "native interface smoke; no digest-pinned memory-system image or Slurm receipt"
        ),
        "system": system.receipt.model_dump(mode="json"),
        "task_id": task.task_id,
        "task_sha256": task.task_sha256,
        "source_preflight_sha256": (
            _sha256_file(source_preflight) if source_preflight.is_file() else None
        ),
        "embedding": {
            "base_url": embedding_base_url,
            "model": embedding_model,
            "dimensions": embedding_dimensions,
            "provenance": embedding_provenance,
            "scientific_evidence": False,
        },
        "aa_score_drift_threshold": score_drift_threshold,
        "gates": {
            "semantic_aa_replay": aa_semantic_replay,
            "source_attribution_nonempty": bool(first_evidence)
            and all(evidence["source_record_ids"] for evidence in first_evidence),
            "within_injected_token_budget": all(
                cell["first"]["costs"]["injected_tokens_estimate"]
                <= task.budget.max_injected_tokens
                for cell in cells
            ),
            "publication_provenance": system.receipt.publication_ready,
        },
        "cells": cells,
    }
    return {
        **payload,
        "artifact_sha256": sha256_text(canonical_json(payload)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--system",
        choices=("reference", "mem0", "graphiti", "langmem", "hindsight"),
        required=True,
    )
    parser.add_argument("--task-id", default="memory-000001")
    parser.add_argument("--embedding-base-url")
    parser.add_argument(
        "--embedding-model", default="cotcodec-deterministic-embedding-v1"
    )
    parser.add_argument("--embedding-dimensions", type=int, default=384)
    parser.add_argument("--embedding-receipt", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    artifact = run_smoke(
        system_id=args.system,
        task_id=args.task_id,
        embedding_base_url=args.embedding_base_url,
        embedding_model=args.embedding_model,
        embedding_dimensions=args.embedding_dimensions,
        embedding_receipt_path=args.embedding_receipt,
    )
    _atomic_write(args.output.resolve(), artifact)
    print(
        f"{artifact['status']}: system={args.system} "
        f"artifact={artifact['artifact_sha256']} output={args.output.resolve()}"
    )
    return 0 if artifact["status"].endswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
