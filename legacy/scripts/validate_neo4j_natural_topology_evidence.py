#!/usr/bin/env python3
"""Validate the retained natural-session topology retrieval negative."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/memory/longmemeval-natural-session-topology-negative-v1.json"
)
STATUS = "NATURAL_SESSION_TOPOLOGY_RETRIEVAL_KILLED"


class EvidenceError(ValueError):
    """Raised when retained natural-topology evidence drifts."""


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_any(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"expected regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"invalid JSON: {path}") from exc
    return value


def _load(path: Path) -> dict[str, Any]:
    value = _load_any(path)
    if not isinstance(value, dict):
        raise EvidenceError(f"expected JSON object: {path}")
    return value


def validate_evidence(path: Path = DEFAULT_EVIDENCE) -> dict[str, Any]:
    evidence = _load(path)
    if (
        evidence.get("schema_version") != 1
        or evidence.get("source_id") != "longmemeval-natural-session-topology"
        or evidence.get("study")
        != "longmemeval-natural-session-topology-retrieval-v1"
        or evidence.get("status") != STATUS
        or evidence.get("evidence_grade") != "local-negative-reproduced"
        or evidence.get("evidence_kind") != "natural-session-topology-negative"
        or evidence.get("source_revisions") != {}
        or evidence.get("run_count") != 2
        or evidence.get("scientific_result") is not False
        or evidence.get("publication_ready") is not False
        or evidence.get("h100_actor_admission") != "forbidden"
    ):
        raise EvidenceError("top-level evidence contract drifted")
    root = PROJECT_ROOT / evidence["artifact_root"]
    if root.is_symlink() or not root.is_dir():
        raise EvidenceError("artifact root is missing or unsafe")
    for relative, expected in evidence["artifact_sha256"].items():
        if _sha(root / relative) != expected:
            raise EvidenceError(f"artifact digest drifted: {relative}")
    source = evidence["source"]
    source_path = PROJECT_ROOT / source["path"]
    if source_path.stat().st_size != source["size_bytes"] or _sha(source_path) != source["sha256"]:
        raise EvidenceError("LongMemEval source bytes drifted")
    for relative, expected in evidence["code_sha256"].items():
        if _sha(PROJECT_ROOT / relative) != expected:
            raise EvidenceError(f"screen code drifted: {relative}")
    first_report = _load(root / "repeat-1/report.json")
    second_report = _load(root / "repeat-2/report.json")
    first_panel = (root / "repeat-1/panel.json").read_bytes()
    second_panel = (root / "repeat-2/panel.json").read_bytes()
    if first_report != second_report or first_panel != second_panel:
        raise EvidenceError("clean repetitions drifted")
    result = evidence["result"]
    metrics = first_report.get("metrics")
    gates = first_report.get("gates")
    if (
        first_report.get("status") != STATUS
        or first_report.get("model_calls") != 0
        or first_report.get("embedding_model_calls") != 0
        or first_report.get("scientific_result") is not False
        or first_report.get("publication_ready") is not False
        or first_report.get("panel") != {
            "questions": 64,
            "questions_per_type": 32,
            "question_types": ["knowledge-update", "temporal-reasoning"],
            "shuffle_seeds": [42, 43, 44],
            "top_k": 4,
        }
        or not isinstance(metrics, dict)
        or metrics.get("recall_all_at_4") != result["recall_all_at_4"]
        or metrics.get("true_minus_flat") != result["true_minus_flat"]
        or metrics.get("true_minus_flat_bootstrap_95_ci")
        != result["true_minus_flat_bootstrap_95_ci"]
        or metrics.get("true_minus_mean_shuffle") != result["true_minus_mean_shuffle"]
        or not isinstance(gates, dict)
    ):
        raise EvidenceError("report result binding drifted")
    integrity_keys = {
        "exact_registered_dataset",
        "balanced_frozen_panel",
        "top_k_unique_roster",
        "node_degree_preserved_in_shuffles",
    }
    if not all(gates.get(key) is True for key in integrity_keys) or any(
        gates.get(key) is not False for key in set(gates) - integrity_keys
    ):
        raise EvidenceError("negative gate pattern drifted")
    image = _load_any(root / "runtime-image-inspect.json")
    if (
        len(image) != 1
        or image[0].get("Id") != evidence["runtime"]["image_id"]
        or image[0].get("Architecture") != "arm64"
        or evidence["runtime"].get("runtime_source_binding") is not False
        or evidence["runtime"].get("container_gpu_count") != 0
    ):
        raise EvidenceError("runtime identity drifted")
    return evidence


def main() -> int:
    evidence = validate_evidence()
    print(f"natural-session topology evidence PASS: {evidence['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
