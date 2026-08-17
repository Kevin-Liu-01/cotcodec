from __future__ import annotations

import copy
from pathlib import Path

import pytest

from harness.memory_trials.schema import canonical_json, sha256_text
from scripts.analyze_memory_system_semantic_smokes import analyze


def _artifact(system: str) -> dict:
    health = {
        "status": "ok",
        "model": "BAAI/bge-small-en-v1.5",
        "registry_model_id": "bge-small-en-v1.5",
        "revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
        "artifact_root_sha256": "a" * 64,
        "dimensions": 384,
        "maximum_tokens": 512,
        "pooling_strategy": "cls-l2-normalized-v1",
        "model_receipt_sha256": "c" * 64,
        "publication_eligible": True,
    }
    cells = []
    for treatment_mode in ("serve_only", "storage_and_service"):
        for visibility in ("serve", "holdout"):
            run = {
                "candidate_served_to_actor": visibility == "serve",
                "costs": {
                    "embedding_calls": 3,
                    "latency_ms": 10.0,
                    "injected_tokens_estimate": 20,
                },
            }
            cells.append(
                {
                    "treatment_mode": treatment_mode,
                    "visibility": visibility,
                    "first": run,
                    "repeat": copy.deepcopy(run),
                }
            )
    payload = {
        "status": "NATIVE_INTERFACE_SMOKE_PASS",
        "scientific_evidence": False,
        "task_id": "task-1",
        "task_sha256": "b" * 64,
        "embedding": {
            "provenance": {
                "health": health,
                "receipt": {
                    "model_id": "bge-small-en-v1.5",
                    "revision": health["revision"],
                    "artifact_root_sha256": health["artifact_root_sha256"],
                    "mode": "full",
                    "publication_eligible": True,
                },
                "receipt_sha256": "c" * 64,
                "publication_eligible": True,
            }
        },
        "system": {"model_receipt_sha256s": ["c" * 64]},
        "gates": {
            "semantic_aa_replay": True,
            "source_attribution_nonempty": True,
            "within_injected_token_budget": True,
        },
        "cells": cells,
    }
    return {**payload, "artifact_sha256": sha256_text(canonical_json(payload))}


def test_semantic_matrix_requires_matched_receipts_and_cells(tmp_path: Path) -> None:
    artifacts = {
        system: (tmp_path / f"{system}.json", _artifact(system))
        for system in ("mem0", "graphiti", "langmem", "hindsight")
    }
    for path, artifact in artifacts.values():
        path.write_text(canonical_json(artifact) + "\n")
    report = analyze(artifacts)
    assert report["status"] == "SEMANTIC_INTERFACE_MATRIX_PASS"
    assert report["scientific_evidence"] is False
    assert report["systems"]["graphiti"]["executions"] == 8


def test_semantic_matrix_rejects_embedding_drift(tmp_path: Path) -> None:
    artifacts = {
        system: (tmp_path / f"{system}.json", _artifact(system))
        for system in ("mem0", "graphiti", "langmem", "hindsight")
    }
    artifacts["hindsight"][1]["embedding"]["provenance"]["health"]["revision"] = "d" * 40
    for path, artifact in artifacts.values():
        path.write_text(canonical_json(artifact) + "\n")
    with pytest.raises(ValueError, match="embedding identity drifted"):
        analyze(artifacts)
