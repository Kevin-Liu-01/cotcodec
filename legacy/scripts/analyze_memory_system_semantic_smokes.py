#!/usr/bin/env python3
"""Seal a matched four-system semantic-embedding interface matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median
from typing import Any

from harness.memory_trials.schema import canonical_json, sha256_text

EXPECTED_SYSTEMS = {"mem0", "graphiti", "langmem", "hindsight"}
EXPECTED_CELLS = {
    ("serve_only", "serve"),
    ("serve_only", "holdout"),
    ("storage_and_service", "serve"),
    ("storage_and_service", "holdout"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("percentile requires observations")
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def load_artifact(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: artifact must be an object")
    artifact_sha256 = payload.pop("artifact_sha256", None)
    if artifact_sha256 != sha256_text(canonical_json(payload)):
        raise ValueError(f"{path}: internal artifact hash mismatch")
    return {**payload, "artifact_sha256": artifact_sha256}


def analyze(artifacts: dict[str, tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    if set(artifacts) != EXPECTED_SYSTEMS:
        raise ValueError("semantic matrix requires exactly four registered systems")
    task_identities: set[tuple[str, str]] = set()
    embedding_identities: set[tuple[str, str, str, int, int, str, str]] = set()
    receipt_hashes: set[str] = set()
    component_receipts: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}

    for system_name, (path, artifact) in sorted(artifacts.items()):
        if artifact.get("status") != "NATIVE_INTERFACE_SMOKE_PASS":
            raise ValueError(f"{system_name}: interface smoke did not pass")
        if artifact.get("scientific_evidence") is not False:
            raise ValueError(f"{system_name}: interface artifact overclaims evidence")
        gates = artifact.get("gates")
        if not isinstance(gates, dict) or any(
            gates.get(gate) is not True
            for gate in (
                "semantic_aa_replay",
                "source_attribution_nonempty",
                "within_injected_token_budget",
            )
        ):
            raise ValueError(f"{system_name}: interface gate failed")
        task_identities.add((artifact["task_id"], artifact["task_sha256"]))

        embedding = artifact.get("embedding")
        provenance = embedding.get("provenance") if isinstance(embedding, dict) else None
        health = provenance.get("health") if isinstance(provenance, dict) else None
        receipt = provenance.get("receipt") if isinstance(provenance, dict) else None
        receipt_sha256 = (
            provenance.get("receipt_sha256") if isinstance(provenance, dict) else None
        )
        if (
            not isinstance(health, dict)
            or not isinstance(receipt, dict)
            or provenance.get("publication_eligible") is not True
            or not isinstance(receipt_sha256, str)
        ):
            raise ValueError(f"{system_name}: semantic embedding receipt is incomplete")
        embedding_identities.add(
            (
                health["registry_model_id"],
                health["revision"],
                health["artifact_root_sha256"],
                health["dimensions"],
                health["maximum_tokens"],
                health["pooling_strategy"],
                health["model_receipt_sha256"],
            )
        )
        receipt_hashes.add(receipt_sha256)
        system_receipt = artifact.get("system")
        if (
            not isinstance(system_receipt, dict)
            or receipt_sha256 not in system_receipt.get("model_receipt_sha256s", [])
        ):
            raise ValueError(f"{system_name}: system receipt omits embedding receipt")

        cells = artifact.get("cells")
        if not isinstance(cells, list) or {
            (cell.get("treatment_mode"), cell.get("visibility")) for cell in cells
        } != EXPECTED_CELLS:
            raise ValueError(f"{system_name}: treatment cell matrix drifted")
        runs = [cell[repeat] for cell in cells for repeat in ("first", "repeat")]
        candidate_serve_cells = [
            cell["first"]
            for cell in cells
            if cell["visibility"] == "serve"
        ]
        if not all(run.get("candidate_served_to_actor") for run in candidate_serve_cells):
            raise ValueError(f"{system_name}: served candidate was not retrieved")
        latencies = [float(run["costs"]["latency_ms"]) for run in runs]
        embeddings = [int(run["costs"]["embedding_calls"]) for run in runs]
        injected_tokens = [int(run["costs"]["injected_tokens_estimate"]) for run in runs]
        summaries[system_name] = {
            "executions": len(runs),
            "candidate_served_cells": len(candidate_serve_cells),
            "candidate_served_rate": 1.0,
            "embedding_calls_total": sum(embeddings),
            "embedding_calls_median": median(embeddings),
            "latency_ms_median": median(latencies),
            "latency_ms_p95_nearest_rank": percentile(latencies, 0.95),
            "injected_tokens_median": median(injected_tokens),
        }
        component_receipts.append(
            {
                "system": system_name,
                "path": path.as_posix(),
                "file_sha256": sha256_file(path),
                "artifact_sha256": artifact["artifact_sha256"],
            }
        )

    if len(task_identities) != 1:
        raise ValueError("semantic matrix task identity drifted")
    if len(embedding_identities) != 1 or len(receipt_hashes) != 1:
        raise ValueError("semantic matrix embedding identity drifted")
    task_id, task_sha256 = task_identities.pop()
    (
        model_id,
        revision,
        artifact_root,
        dimensions,
        maximum_tokens,
        pooling_strategy,
        service_receipt_sha256,
    ) = embedding_identities.pop()
    receipt_sha256 = next(iter(receipt_hashes))
    if service_receipt_sha256 != receipt_sha256:
        raise ValueError("semantic matrix service receipt binding drifted")
    payload = {
        "schema_version": "1.0",
        "status": "SEMANTIC_INTERFACE_MATRIX_PASS",
        "scientific_evidence": False,
        "reason": (
            "one synthetic task proves matched native retrieval transport only; "
            "no actor outcome, digest-pinned memory image, Slurm receipt, or benchmark effect"
        ),
        "task_id": task_id,
        "task_sha256": task_sha256,
        "embedding": {
            "registry_model_id": model_id,
            "revision": revision,
            "artifact_root_sha256": artifact_root,
            "dimensions": dimensions,
            "maximum_tokens": maximum_tokens,
            "pooling_strategy": pooling_strategy,
            "receipt_sha256": receipt_sha256,
        },
        "components": component_receipts,
        "systems": summaries,
        "interpretation_limits": {
            "retrieval_quality_comparison": False,
            "memory_policy_effect": False,
            "model_scale_effect": False,
            "latency_is_isolated_fresh_process_cpu": True,
        },
    }
    return {**payload, "artifact_sha256": sha256_text(canonical_json(payload))}


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError(f"refusing to overwrite matrix artifact: {path}")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        action="append",
        required=True,
        metavar="SYSTEM=PATH",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifacts: dict[str, tuple[Path, dict[str, Any]]] = {}
    for item in args.artifact:
        system, separator, raw_path = item.partition("=")
        if not separator or system in artifacts:
            raise ValueError(f"invalid or duplicate --artifact: {item!r}")
        path = Path(raw_path).resolve()
        artifacts[system] = (path, load_artifact(path))
    report = analyze(artifacts)
    atomic_write(args.output.resolve(), report)
    print(
        f"{report['status']}: artifact={report['artifact_sha256']} "
        f"output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
