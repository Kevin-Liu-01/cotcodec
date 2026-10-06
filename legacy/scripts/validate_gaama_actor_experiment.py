#!/usr/bin/env python3
"""Validate the frozen GAAMA H100 actor-screen contract."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-gaama-h100-actor-screen.yaml"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")


class GaamaActorExperimentError(ValueError):
    """Raised when the registered actor screen drifts."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("name") != "stage3-gaama-h100-actor-screen"
        or payload.get("study_id") != "gaama-natural-h100-actor-screen-v1"
    ):
        raise GaamaActorExperimentError("GAAMA actor experiment identity drifted")
    input_contract = payload.get("input")
    if (
        not isinstance(input_contract, dict)
        or input_contract.get("evidence_path")
        != "research/evidence/memory/gaama-natural-graph-v5.json"
        or input_contract.get("cpu_study")
        != "gaama-natural-heldout-graph-retrieval-v1"
        or input_contract.get("cpu_status") != "GAAMA_NATURAL_GRAPH_PASS"
        or input_contract.get("gaama_source_id") != "gaama"
        or input_contract.get("gaama_revision")
        != "2d992f7f7b97c802bfe4c799878a5477cac1b6ff"
        or input_contract.get("locomo10_sha256")
        != "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
        or input_contract.get("locomo10_license") != "CC-BY-NC-4.0"
    ):
        raise GaamaActorExperimentError("GAAMA actor input contract drifted")
    evidence_digest = input_contract.get("evidence_sha256")
    evidence_path = PROJECT_ROOT / input_contract["evidence_path"]
    if (
        not isinstance(evidence_digest, str)
        or not SHA256_RE.fullmatch(evidence_digest)
        or not evidence_path.is_file()
        or evidence_path.is_symlink()
        or _sha(evidence_path) != evidence_digest
    ):
        raise GaamaActorExperimentError("GAAMA actor evidence bundle drifted")

    panel = payload.get("panel")
    if panel != {
        "seed": 20260815,
        "questions": 200,
        "categories": [1, 2, 3, 4],
        "questions_per_category": 50,
        "arms": [
            "flat",
            "true_graph",
            "shuffled_graph_seed_42",
            "shuffled_graph_seed_43",
            "shuffled_graph_seed_44",
        ],
        "retrieval_top_k": 10,
        "max_words_per_record": 80,
        "aa_questions": 20,
        "answer_metrics": ["normalized_exact_match", "token_f1"],
        "official_locomo_evaluation": False,
    }:
        raise GaamaActorExperimentError("GAAMA actor panel contract drifted")
    model = payload.get("model")
    if (
        not isinstance(model, dict)
        or model.get("model_id") != "qwen3.5-4b"
        or model.get("revision") != "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
        or not GIT_RE.fullmatch(str(model.get("revision", "")))
        or model.get("artifact_root_sha256")
        != "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e"
        or model.get("dtype") != "bfloat16"
        or model.get("max_new_tokens") != 64
        or model.get("use_chat_template") is not True
        or model.get("do_sample") is not False
        or model.get("deterministic_algorithms") is not True
        or model.get("attention_implementation") != "eager"
        or model.get("cublas_workspace_config") != ":4096:8"
    ):
        raise GaamaActorExperimentError("GAAMA actor model contract drifted")
    gates = payload.get("gates")
    if gates != {
        "actor_aa_exact": True,
        "completion_nonempty": True,
        "flat_actor_f1_minimum": 0.20,
        "true_f1_must_exceed_flat": True,
        "true_f1_must_exceed_mean_shuffled": True,
        "true_f1_must_exceed_at_least_n_shuffles": 2,
        "mean_prompt_token_ratio_maximum": 1.10,
        "valid_statuses": ["GAAMA_H100_ACTOR_PASS", "GAAMA_H100_ACTOR_KILLED"],
    }:
        raise GaamaActorExperimentError("GAAMA actor gates drifted")
    execution = payload.get("execution")
    if execution != {
        "runtime": "docker-single-node-discovery-v1",
        "scheduler": "slurm",
        "gpu_type": "h100",
        "gpus": 1,
        "cpus": 16,
        "memory_gb": 64,
        "minutes": 120,
        "max_gpu_hours": 2,
        "network_mode": "none",
        "checkpoint_every_completed_case": True,
        "checkpoint_on_preemption": True,
        "prove_fresh_job_resume": True,
        "persistent_output_required": True,
        "login_node_compute_forbidden": True,
        "sudo_forbidden": True,
        "cluster_lane": "discovery-only-slurm21-cgroupv1",
    }:
        raise GaamaActorExperimentError("GAAMA actor execution contract drifted")
    claims = payload.get("claims")
    if (
        not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
        or claims.get("discovery_only") is not True
    ):
        raise GaamaActorExperimentError("GAAMA actor claim boundary drifted")
    payload["experiment_sha256"] = _sha(path)
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(f"GAAMA H100 actor experiment PASS: {payload['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
