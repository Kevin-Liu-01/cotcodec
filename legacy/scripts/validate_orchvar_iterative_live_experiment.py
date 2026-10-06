#!/usr/bin/env python3
"""Fail-closed validator for the first iterative live-model smoke."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.yaml_utils import load_yaml_file  # noqa: E402
from scripts.validate_orchvar_live_smoke_experiment import (  # noqa: E402
    IMAGE_ID,
    IMAGE_REGISTRY_DIGEST,
    MODEL_ARTIFACT_ROOT,
    MODEL_RECEIPT_SHA256,
    MODEL_REVISION,
    TASK_IDS,
)

DEFAULT_EXPERIMENT = PROJECT_ROOT / "experiments/orchvar_qwen35_iterative_live_smoke.yaml"
TASK_MANIFEST = (
    PROJECT_ROOT / "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml"
)
ADMISSION_EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/harness/orchvar-iterative-tool-result-cpu-admission-v2.json"
)
ADMISSION_SHA256 = "dd66f56ed1c58fb6e673a6b755eadf5cf2503ebfadd8b32048b6fa4820365706"
ADMISSION_ROOT = "7723d5da86dff2bc216bddb0e318f763867397a436c0271503692b65cd2c3ddd"
ADMISSION_PROJECTION = (
    "a59562811e5af0ba93c6793e339d69f43a26bb983f6c0676b17a5c462ad8ca83"
)
METRICS = [
    "task_success_rate",
    "tool_call_exact_match",
    "safety_failures",
    "model_decisions",
    "prompt_tokens",
    "completion_tokens",
    "wall_clock_latency_ms",
]


class IterativeLiveExperimentError(ValueError):
    """Raised when the iterative live experiment drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IterativeLiveExperimentError(f"iterative live {label} drifted")


def validate_experiment_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise IterativeLiveExperimentError("iterative live contract must be a mapping")
    _equal(
        set(payload),
        {
            "name",
            "description",
            "benchmark",
            "model",
            "conditions",
            "task_variant",
            "tasks",
            "seeds",
            "metrics",
            "actor",
            "tools",
            "task_manifest_sha256",
            "iterative_cpu_admission",
            "budgets",
            "execution",
            "containment",
            "claim_boundary",
        },
        "top-level fields",
    )
    _equal(
        {key: payload.get(key) for key in ("name", "benchmark", "model")},
        {
            "name": "orchvar_qwen35_iterative_live_smoke",
            "benchmark": "orchvar_canary",
            "model": "qwen3.5-4b",
        },
        "identity",
    )
    _equal(payload.get("conditions"), ["english_only"], "conditions")
    _equal(payload.get("task_variant"), "live_self_contained_v2", "task variant")
    _equal(payload.get("tasks"), TASK_IDS, "tasks")
    _equal(payload.get("seeds"), [42], "seeds")
    _equal(payload.get("metrics"), METRICS, "metrics")
    _equal(
        payload.get("actor"),
        {
            "type": "transformers_iterative_json_v1",
            "registry_model_id": "qwen3.5-4b",
            "registry_path": "models/registry.yaml",
            "repo_id": "Qwen/Qwen3.5-4B",
            "revision": MODEL_REVISION,
            "artifact_root_sha256": MODEL_ARTIFACT_ROOT,
            "model_receipt_sha256": MODEL_RECEIPT_SHA256,
            "max_new_tokens": 512,
            "dtype": "bfloat16",
            "device_map": "auto",
            "use_chat_template": True,
            "deterministic": True,
            "attention_implementation": "eager",
        },
        "actor",
    )
    _equal(
        payload.get("tools"),
        {"type": "sqlite_canary_v1", "persistence": "isolated_in_memory_per_task"},
        "tools",
    )
    _equal(
        payload.get("task_manifest_sha256"),
        hashlib.sha256(TASK_MANIFEST.read_bytes()).hexdigest(),
        "task manifest",
    )
    _equal(
        hashlib.sha256(ADMISSION_EVIDENCE.read_bytes()).hexdigest(),
        ADMISSION_SHA256,
        "CPU admission file",
    )
    _equal(
        payload.get("iterative_cpu_admission"),
        {
            "status": "ORCHVAR_ITERATIVE_TOOL_RESULT_CPU_ADMISSION_PASS",
            "evidence": (
                "research/evidence/harness/"
                "orchvar-iterative-tool-result-cpu-admission-v2.json"
            ),
            "evidence_sha256": ADMISSION_SHA256,
            "evidence_root_sha256": ADMISSION_ROOT,
            "projection_sha256": ADMISSION_PROJECTION,
            "external_model_calls": 0,
            "deterministic_task_successes": 6,
            "sqlite_tool_operations": 9,
            "actual_usr1_acknowledged_cells": 2,
            "safety_gate_passed": True,
        },
        "CPU admission",
    )
    _equal(
        payload.get("budgets"),
        {
            "max_decisions_per_task": 5,
            "max_steps_per_task": 12,
            "max_tool_calls_per_task": 4,
            "max_external_model_calls": 30,
            "max_local_tool_calls": 12,
            "max_cost_usd": 0,
            "max_gpu_hours": 0.5,
        },
        "budgets",
    )
    _equal(
        payload.get("execution"),
        {
            "run_id": "orchvar-qwen35-iterative-live-v1",
            "checkpoint_after_each_cell": True,
            "checkpoint_on_usr1": True,
        },
        "execution",
    )
    _equal(
        payload.get("containment"),
        {
            "scheduler": "slurm",
            "accelerator": "h100",
            "gpu_count": 1,
            "container_runtime": "docker",
            "image_id": IMAGE_ID,
            "image_registry_digest": IMAGE_REGISTRY_DIGEST,
            "network": "none",
            "root_filesystem": "read_only",
            "capabilities": "drop_all",
            "no_new_privileges": True,
            "source_mount": "read_only_content_addressed_capsule",
            "model_mount": "read_only_pinned_snapshot",
        },
        "containment",
    )
    claim = payload.get("claim_boundary")
    if (
        not isinstance(claim, dict)
        or set(claim)
        != {
            "scientific_claim",
            "publication_evidence",
            "language_effect_claim",
            "benchmark_validity_claim",
            "model_quality_claim",
            "purpose",
            "limitation",
        }
        or any(
            claim[key] is not False
            for key in (
                "scientific_claim",
                "publication_evidence",
                "language_effect_claim",
                "benchmark_validity_claim",
                "model_quality_claim",
            )
        )
        or claim.get("purpose")
        != "iterative_tool_result_conditioning_transport_and_safety_check_only"
        or not isinstance(claim.get("limitation"), str)
    ):
        raise IterativeLiveExperimentError("iterative live claim boundary drifted")
    return payload


def validate_experiment(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    return validate_experiment_payload(load_yaml_file(path))


def main() -> int:
    validate_experiment()
    print("Iterative live OrchVar experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
