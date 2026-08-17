#!/usr/bin/env python3
"""Validate the frozen Mnemon static-space H100 actor contract."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/memory/stage3-mnemon-static-space-h100-actor.yaml"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")


class MnemonActorExperimentError(ValueError):
    """Raised when the registered Mnemon actor contract drifts."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_experiment_contract(
    path: Path = DEFAULT_EXPERIMENT,
    *,
    panel_artifact_path: Path | None = None,
) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("name") != "stage3-mnemon-static-space-h100-actor"
        or payload.get("study_id") != "mnemon-static-space-h100-actor-v1"
    ):
        raise MnemonActorExperimentError("Mnemon actor experiment identity drifted")
    input_contract = payload.get("input")
    expected_input = {
        "panel_path": (
            "data/results/mnemon-static-space-panel/"
            "2026-08-16-local-docker-v1/panel.json"
        ),
        "panel_sha256": "43a416c62be619de641aa60ecefc83ad0efdd605f7f13fd8821936704acacee5",
        "panel_status": "MNEMON_STATIC_SPACE_PANEL_FROZEN",
        "admission_evidence_path": "research/evidence/memory/mnemon-active-space-admission-v1.json",
        "admission_evidence_sha256": (
            "27d7d55c664748bf7bc5fb6e1ad53d17cb35a50d9497329851dc1eaa4155debb"
        ),
        "admission_status": "ADMITTED_STATIC_ACTIVE_SPACE_CONTROL_WITH_SOFT_DELETE_BOUNDARY",
        "mnemon_revision": "88d2981edeb18a5ebe048af472f6f96527615454",
        "dsh_mnemon_revision": "1889c68400e52a391ee9a6eedf15bf44bc39dd06",
    }
    if input_contract != expected_input:
        raise MnemonActorExperimentError("Mnemon actor input contract drifted")
    for path_key, sha_key in (
        ("panel_path", "panel_sha256"),
        ("admission_evidence_path", "admission_evidence_sha256"),
    ):
        artifact = (
            panel_artifact_path
            if path_key == "panel_path" and panel_artifact_path is not None
            else PROJECT_ROOT / input_contract[path_key]
        )
        digest = input_contract[sha_key]
        if (
            not SHA256_RE.fullmatch(digest)
            or artifact.is_symlink()
            or not artifact.is_file()
            or _sha(artifact) != digest
        ):
            raise MnemonActorExperimentError("Mnemon actor input artifact drifted")
    if not all(
        GIT_RE.fullmatch(input_contract[key])
        for key in ("mnemon_revision", "dsh_mnemon_revision")
    ):
        raise MnemonActorExperimentError("Mnemon actor revision is not immutable")
    if payload.get("panel") != {
        "tasks": 32,
        "groups": 32,
        "arms": ["no_memory", "all_spaces", "lexical_router", "oracle_space"],
        "retrieval_top_k": 4,
        "fixed_slot_characters": 160,
        "aa_tasks": 8,
        "router_inputs": ["question"],
        "answer_labels_available_to_router": False,
    }:
        raise MnemonActorExperimentError("Mnemon actor panel contract drifted")
    model = payload.get("model")
    if model != {
        "model_id": "qwen3.5-4b",
        "revision": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
        "artifact_root_sha256": "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e",
        "dtype": "bfloat16",
        "max_new_tokens": 32,
        "use_chat_template": True,
        "do_sample": False,
        "deterministic_algorithms": True,
        "attention_implementation": "eager",
        "cublas_workspace_config": ":4096:8",
    }:
        raise MnemonActorExperimentError("Mnemon actor model contract drifted")
    if payload.get("gates") != {
        "actor_aa_exact": True,
        "completion_nonempty": True,
        "lexical_equals_oracle": True,
        "lexical_exact_minimum": 0.80,
        "lexical_minus_all_token_f1_minimum": 0.03,
        "lexical_minus_no_memory_token_f1_minimum": 0.20,
        "matched_nonempty_prompt_token_ratio": [0.85, 1.15],
        "valid_statuses": ["MNEMON_STATIC_ROUTING_PASS", "MNEMON_STATIC_ROUTING_KILLED"],
    }:
        raise MnemonActorExperimentError("Mnemon actor gates drifted")
    if payload.get("execution") != {
        "runtime": "docker-single-node-discovery-v1",
        "scheduler": "slurm",
        "gpu_type": "h100",
        "gpus": 1,
        "cpus": 16,
        "memory_gb": 64,
        "minutes": 60,
        "max_gpu_hours": 1,
        "network_mode": "none",
        "checkpoint_every_completed_case": True,
        "checkpoint_on_preemption": True,
        "prove_fresh_job_resume": True,
        "persistent_output_required": True,
        "login_node_compute_forbidden": True,
        "sudo_forbidden": True,
        "cluster_lane": "discovery-only-slurm21-cgroupv1",
    }:
        raise MnemonActorExperimentError("Mnemon actor execution contract drifted")
    claims = payload.get("claims")
    if (
        not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
        or claims.get("discovery_only") is not True
    ):
        raise MnemonActorExperimentError("Mnemon actor claim boundary drifted")
    payload["experiment_sha256"] = _sha(path)
    return payload


def main() -> int:
    payload = validate_experiment_contract()
    print(f"Mnemon H100 actor experiment PASS: {payload['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
