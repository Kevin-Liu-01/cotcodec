#!/usr/bin/env python3
"""Fail-closed validator for the post-repair OrchVar live-v2 smoke."""

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

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/degradation_canary_qwen35_4b_live_v2_smoke.yaml"
)
TASK_MANIFEST = (
    PROJECT_ROOT / "harness/benchmarks/specs/orchvar_canary_live_v2_tasks.yaml"
)
INTERFACE_EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/harness/orchvar-live-task-interface-v2-admission.json"
)
INTERFACE_EVIDENCE_SHA256 = (
    "c5c4c8f9e7f30e6b67f5da4ba86290fd39b62c66616637babca64da09b893dab"
)
INTERFACE_PROJECTION_SHA256 = (
    "c962287eb89b8bfbbde81f0143f126b832a8370d58cad7c72617f7eecccf2800"
)


class LiveV2ExperimentError(ValueError):
    """Raised when the post-repair live-v2 contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise LiveV2ExperimentError(f"live-v2 {label} drifted")


def validate_experiment_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LiveV2ExperimentError("live-v2 contract must be a mapping")
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
            "interface_admission",
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
            "name": "degradation_canary_qwen35_4b_live_v2_smoke",
            "benchmark": "orchvar_canary",
            "model": "qwen3.5-4b",
        },
        "identity",
    )
    _equal(payload.get("conditions"), ["english_only"], "conditions")
    _equal(payload.get("task_variant"), "live_self_contained_v2", "task variant")
    _equal(payload.get("tasks"), TASK_IDS, "task roster")
    _equal(payload.get("seeds"), [42], "seeds")
    _equal(
        payload.get("metrics"),
        [
            "task_success_rate",
            "tool_call_exact_match",
            "safety_failures",
            "prompt_tokens",
            "completion_tokens",
            "wall_clock_latency_ms",
        ],
        "metrics",
    )
    _equal(
        payload.get("actor"),
        {
            "type": "transformers_json_v1",
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
        "tool runtime",
    )
    manifest_sha256 = hashlib.sha256(TASK_MANIFEST.read_bytes()).hexdigest()
    _equal(payload.get("task_manifest_sha256"), manifest_sha256, "task manifest")
    evidence_sha256 = hashlib.sha256(INTERFACE_EVIDENCE.read_bytes()).hexdigest()
    _equal(evidence_sha256, INTERFACE_EVIDENCE_SHA256, "interface evidence file")
    _equal(
        payload.get("interface_admission"),
        {
            "status": "ORCHVAR_LIVE_TASK_INTERFACE_V2_CPU_ADMISSION_PASS",
            "evidence": (
                "research/evidence/harness/"
                "orchvar-live-task-interface-v2-admission.json"
            ),
            "evidence_sha256": INTERFACE_EVIDENCE_SHA256,
            "projection_sha256": INTERFACE_PROJECTION_SHA256,
            "external_model_calls": 0,
            "deterministic_task_successes": 6,
            "sqlite_tool_operations": 9,
        },
        "interface admission",
    )
    _equal(
        payload.get("budgets"),
        {
            "max_steps_per_task": 12,
            "max_tool_calls_per_task": 4,
            "external_model_calls": 6,
            "max_local_tool_calls": 12,
            "max_cost_usd": 0,
            "max_gpu_hours": 0.5,
        },
        "budgets",
    )
    _equal(
        payload.get("execution"),
        {
            "run_id": "orchvar-qwen35-4b-live-v2-smoke",
            "checkpoint_after_each_cell": True,
            "checkpoint_on_usr1": True,
            "one_completion_per_task": True,
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
    _equal(
        payload.get("claim_boundary"),
        {
            "scientific_claim": False,
            "publication_evidence": False,
            "language_effect_claim": False,
            "benchmark_validity_claim": False,
            "model_quality_claim": False,
            "purpose": "repaired_live_task_interface_transport_check_only",
            "post_negative_repair": (
                "visible_oracle_inputs_only_no_model_specific_targeting"
            ),
            "limitation": (
                "The admitted spine still uses one model plan per task. Tools "
                "execute for real, but no later model generation is conditioned on "
                "tool results; the explicit earlier-turn callback facts do not "
                "constitute a real multiturn run."
            ),
        },
        "claim boundary",
    )
    return payload


def validate_experiment(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    return validate_experiment_payload(load_yaml_file(path))


def main() -> int:
    validate_experiment()
    print("Live OrchVar-Canary v2 experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
