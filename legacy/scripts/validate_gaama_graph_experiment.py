#!/usr/bin/env python3
"""Validate the frozen GAAMA graph-component doctor contract."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-gaama-graph-component-doctor.yaml"
)
EXPECTED_STATUS = "GAAMA_COMPONENT_CONTRACT_PASS"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GaamaExperimentError(ValueError):
    """Raised when the registered GAAMA component contract drifts."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise GaamaExperimentError("GAAMA experiment must be schema_version 1")
    if payload.get("name") != "stage3-gaama-graph-component-doctor":
        raise GaamaExperimentError("GAAMA experiment name drifted")
    if payload.get("study_id") != "gaama-matched-graph-component-doctor-v1":
        raise GaamaExperimentError("GAAMA study_id drifted")
    source = payload.get("source")
    if not isinstance(source, dict) or source.get("revision") != (
        "2d992f7f7b97c802bfe4c799878a5477cac1b6ff"
    ):
        raise GaamaExperimentError("GAAMA source revision drifted")
    for field in (
        "git_archive_tar_sha256",
        "license_sha256",
        "pagerank_sha256",
        "retriever_sha256",
        "locomo10_sha256",
    ):
        if not isinstance(source.get(field), str) or not SHA256_RE.fullmatch(source[field]):
            raise GaamaExperimentError(f"GAAMA source {field} is not SHA-256")
    runtime = payload.get("runtime")
    if (
        not isinstance(runtime, dict)
        or runtime.get("network_mode") != "none"
        or runtime.get("read_only_root") is not True
        or runtime.get("cap_drop_all") is not True
        or runtime.get("no_new_privileges") is not True
        or runtime.get("user") != "65532:65532"
        or runtime.get("gpu_count") != 0
        or runtime.get("clean_repetitions") != 2
    ):
        raise GaamaExperimentError("GAAMA containment contract drifted")
    contract = payload.get("contract")
    if (
        not isinstance(contract, dict)
        or contract.get("case_count") != 24
        or contract.get("candidate_count_per_case") != 5
        or contract.get("top_k") != 3
        or contract.get("ppr_weight") != 0.1
        or contract.get("sim_weight") != 1.0
        or contract.get("model_calls") != 0
        or contract.get("embedding_calls") != 0
        or contract.get("graph_arms")
        != ["flat", "ppr-weight-zero", "true-graph", "degree-type-shuffled-graph"]
        or contract.get("require_identical_candidate_pool") is not True
        or contract.get("require_ppr_zero_equal_flat") is not True
        or contract.get("require_no_cross_task_edges") is not True
    ):
        raise GaamaExperimentError("GAAMA component contract drifted")
    if payload.get("gates", {}).get("required_status") != EXPECTED_STATUS:
        raise GaamaExperimentError("GAAMA terminal gate drifted")
    claims = payload.get("claims")
    if (
        not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
    ):
        raise GaamaExperimentError("GAAMA claim boundary drifted")
    payload["experiment_sha256"] = _sha(path)
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(f"GAAMA graph component experiment PASS: {payload['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
