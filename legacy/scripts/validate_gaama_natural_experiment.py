#!/usr/bin/env python3
"""Validate the frozen natural held-out GAAMA graph contract."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-gaama-natural-graph-doctor.yaml"
)
VALID_STATUSES = {"GAAMA_NATURAL_GRAPH_PASS", "GAAMA_NATURAL_GRAPH_KILLED"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GaamaNaturalExperimentError(ValueError):
    """Raised when the registered natural graph contract drifts."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise GaamaNaturalExperimentError("GAAMA natural experiment must be schema 1")
    if payload.get("name") != "stage3-gaama-natural-graph-doctor":
        raise GaamaNaturalExperimentError("GAAMA natural experiment name drifted")
    if payload.get("study_id") != "gaama-natural-heldout-graph-retrieval-v1":
        raise GaamaNaturalExperimentError("GAAMA natural study_id drifted")
    source = payload.get("source")
    if (
        not isinstance(source, dict)
        or source.get("repository") != "https://github.com/swarna-kpaul/gaama"
        or source.get("revision")
        != "2d992f7f7b97c802bfe4c799878a5477cac1b6ff"
        or source.get("tree") != "0227970b58617696afd53d27f920a10e3c401ece"
        or source.get("locomo10_license") != "CC-BY-NC-4.0"
    ):
        raise GaamaNaturalExperimentError("GAAMA natural source identity drifted")
    for field in (
        "git_archive_tar_sha256",
        "license_sha256",
        "pagerank_sha256",
        "retriever_sha256",
        "locomo10_sha256",
    ):
        if not isinstance(source.get(field), str) or not SHA256_RE.fullmatch(source[field]):
            raise GaamaNaturalExperimentError(f"GAAMA natural {field} is not SHA-256")
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
        or runtime.get("timeout_seconds") != 900
    ):
        raise GaamaNaturalExperimentError("GAAMA natural containment drifted")
    contract = payload.get("contract")
    if (
        not isinstance(contract, dict)
        or contract.get("dev_sample_ids") != ["conv-26", "conv-30", "conv-41"]
        or contract.get("test_sample_ids")
        != ["conv-42", "conv-43", "conv-44", "conv-47", "conv-48", "conv-49", "conv-50"]
        or contract.get("categories") != [1, 2, 3, 4]
        or contract.get("expected_dev_questions") != 382
        or contract.get("expected_test_questions") != 1146
        or contract.get("expected_dialogue_nodes") != 5882
        or contract.get("candidate_node_kind") != "dialogue-turn"
        or contract.get("indexed_fields") != ["session-date", "speaker", "text"]
        or contract.get("graph_edges") != ["in-session", "next-turn"]
        or contract.get("ppr_weights") != [0.0, 0.05, 0.1, 0.25, 0.5, 1.0]
        or contract.get("ppr_alpha") != 0.6
        or contract.get("shuffle_seeds") != [42, 43, 44]
        or contract.get("bm25_k1") != 1.2
        or contract.get("bm25_b") != 0.75
        or contract.get("primary_metric") != "evidence-recall-all-at-10"
        or contract.get("bootstrap_seed") != 20260814
        or contract.get("bootstrap_draws") != 10_000
        or contract.get("model_calls") != 0
        or contract.get("embedding_calls") != 0
        or contract.get("require_dev_only_weight_selection") is not True
        or contract.get("require_identical_output_candidate_pool") is not True
        or contract.get("require_graph_degree_and_candidate_receipt") is not True
        or contract.get("require_ppr_zero_equal_flat") is not True
        or contract.get("require_no_answer_or_evidence_in_features") is not True
    ):
        raise GaamaNaturalExperimentError("GAAMA natural retrieval contract drifted")
    gates = payload.get("gates")
    if (
        not isinstance(gates, dict)
        or gates.get("valid_statuses")
        != ["GAAMA_NATURAL_GRAPH_PASS", "GAAMA_NATURAL_GRAPH_KILLED"]
        or gates.get("integrity_gates_must_all_pass") is not True
        or gates.get("pass_true_minus_flat_minimum") != 0.01
        or gates.get("pass_true_minus_mean_shuffled_minimum") != 0.01
        or gates.get("pass_clustered_ci_lower_must_exceed") != 0.0
        or gates.get("pass_sign_randomization_p_maximum") != 0.05
        or gates.get("pass_shuffled_clustered_ci_lower_must_exceed") != 0.0
        or gates.get("pass_shuffled_sign_randomization_p_maximum") != 0.05
        or gates.get("h100_admission") != "separate-design-review-only-after-pass"
    ):
        raise GaamaNaturalExperimentError("GAAMA natural gates drifted")
    claims = payload.get("claims")
    if (
        not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
    ):
        raise GaamaNaturalExperimentError("GAAMA natural claim boundary drifted")
    payload["experiment_sha256"] = _sha(path)
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(f"GAAMA natural graph experiment PASS: {payload['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
