#!/usr/bin/env python3
"""Validate the frozen MemoryBank H100 discovery contract."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT
    / "experiments/memory/stage3-memorybank-corrected-decay-h100-screen.yaml"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class MemoryBankH100ExperimentError(ValueError):
    """Raised when the registered MemoryBank H100 contract drifts."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_experiment_contract(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("name") != "stage3-memorybank-corrected-decay-h100-screen"
    ):
        raise MemoryBankH100ExperimentError("MemoryBank H100 identity drifted")
    input_contract = payload.get("input")
    if not isinstance(input_contract, dict):
        raise MemoryBankH100ExperimentError("MemoryBank H100 input is missing")
    if (
        input_contract.get("evidence_status")
        != "MEMORYBANK_CORRECTED_DECAY_CONTROL_ADMITTED"
        or input_contract.get("upstream_revision")
        != "cf61c4196e4cfdb0f2b7a0316249fa40312dc3a9"
        or input_contract.get("task_count") != 200
        or input_contract.get("task_source_seed") != 7
        or input_contract.get("task_manifest_sha256")
        != "b4f6ebc040b8d83ca75ceaf9118abbcefc38083a6a6b402665cc6859dd6a1463"
        or input_contract.get("treatment_mode") != "storage_and_service"
    ):
        raise MemoryBankH100ExperimentError("MemoryBank H100 input contract drifted")
    evidence_path = PROJECT_ROOT / str(input_contract.get("evidence_path"))
    if (
        evidence_path.is_symlink()
        or not evidence_path.is_file()
        or _sha(evidence_path) != input_contract.get("evidence_sha256")
    ):
        raise MemoryBankH100ExperimentError("MemoryBank H100 evidence drifted")
    expected_bundles = {
        "corrected": (
            "corrected.json",
            "8a8cdd3ff0fe33e4b9fc0fdbbee1a001b935ae29bf6decad0e31a4535f44a500",
            "468540a3e8bcb44d223ce1aee8abd4c06726d450d2e9af6e03632eb689b3f2f8",
            "memorybank-corrected-decay-v1",
            "corrected-primary",
        ),
        "upstream_precedence": (
            "upstream-precedence.json",
            "fe9b7ab3588c26d29006c2107606b054fc17d5266da9f8ee7214d2c3fa9a70e0",
            "02ff175501ff0ee28f0ee9e5c723a32299f16d400bfe636d3a8771477cec040f",
            "memorybank-upstream-precedence-v1",
            "implementation-bug-negative",
        ),
        "no_decay": (
            "no-decay.json",
            "fddb26029d68de646a8ef766a411ac843537e75c0119586c563e428919952333",
            "6bf74611d01fe3cdf9a6cf139a01a9285ce766da844003bf84c5977b05ac4664",
            "memorybank-no-decay-v1",
            "no-forgetting-upper-control",
        ),
    }
    bundles = input_contract.get("bundles")
    if not isinstance(bundles, dict) or set(bundles) != set(expected_bundles):
        raise MemoryBankH100ExperimentError("MemoryBank H100 bundle roster drifted")
    for arm, (filename, file_sha, semantic_sha, system_id, role) in expected_bundles.items():
        row = bundles[arm]
        bundle_path = PROJECT_ROOT / str(row.get("path"))
        if (
            Path(str(row.get("path"))).name != filename
            or row.get("file_sha256") != file_sha
            or row.get("semantic_sha256") != semantic_sha
            or row.get("system_id") != system_id
            or row.get("role") != role
            or bundle_path.is_symlink()
            or not bundle_path.is_file()
            or _sha(bundle_path) != file_sha
        ):
            raise MemoryBankH100ExperimentError(f"MemoryBank H100 bundle drifted: {arm}")
        parsed = json.loads(bundle_path.read_text(encoding="utf-8"))
        if parsed.get("bundle_sha256") != semantic_sha:
            raise MemoryBankH100ExperimentError(
                f"MemoryBank H100 semantic bundle drifted: {arm}"
            )
    if payload.get("model") != {
        "model_id": "qwen3.5-4b",
        "revision": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a",
        "artifact_root_sha256": (
            "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e"
        ),
        "dtype": "bfloat16",
        "max_new_tokens": 128,
        "do_sample": False,
        "deterministic_algorithms": True,
        "attention_implementation": "eager",
        "cublas_workspace_config": ":4096:8",
    }:
        raise MemoryBankH100ExperimentError("MemoryBank H100 model contract drifted")
    design = payload.get("design")
    if (
        not isinstance(design, dict)
        or design.get("assignment_seeds") != [42, 43, 44]
        or design.get("serve_propensity") != 0.5
        or design.get("paired_replay_fraction") != 0.25
        or design.get("memory_budget")
        != {
            "active_slots": 4,
            "max_archive_reads": 1,
            "retrieval_top_k": 4,
            "max_injected_tokens": 256,
        }
        or design.get("primary_contrast")
        != "corrected-minus-upstream-precedence-executable-success"
        or design.get("minimum_corrected_minus_upstream_points") != 3.0
    ):
        raise MemoryBankH100ExperimentError("MemoryBank H100 design drifted")
    execution = payload.get("execution")
    if execution != {
        "runtime": "docker-single-node-discovery-v1",
        "scheduler": "slurm",
        "gpu_type": "h100",
        "gpus_per_arm": 1,
        "cpus_per_arm": 16,
        "memory_gb_per_arm": 64,
        "minutes_per_arm": 45,
        "max_gpu_hours_per_arm": 0.75,
        "max_total_gpu_hours": 2.25,
        "network_mode": "none",
        "checkpoint_every_trial": True,
        "checkpoint_on_preemption": True,
        "prove_fresh_job_resume": True,
        "login_node_compute_forbidden": True,
        "sudo_forbidden": True,
        "cluster_lane": "discovery-only-slurm21-cgroupv1",
    }:
        raise MemoryBankH100ExperimentError("MemoryBank H100 execution drifted")
    claims = payload.get("claims")
    if (
        not isinstance(claims, dict)
        or claims.get("scientific_result") is not False
        or claims.get("publication_ready") is not False
        or claims.get("discovery_only") is not True
    ):
        raise MemoryBankH100ExperimentError("MemoryBank H100 claim boundary drifted")
    if not SHA256_RE.fullmatch(str(input_contract.get("evidence_sha256"))):
        raise MemoryBankH100ExperimentError("MemoryBank H100 evidence digest is invalid")
    payload["experiment_sha256"] = _sha(path)
    return payload


def main() -> int:
    result = validate_experiment_contract()
    print(f"MemoryBank H100 experiment PASS: {result['experiment_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
