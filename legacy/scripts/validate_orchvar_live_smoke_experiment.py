#!/usr/bin/env python3
"""Fail-closed validator for the first live OrchVar-Canary smoke."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.yaml_utils import load_yaml_file  # noqa: E402

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/degradation_canary_qwen35_4b_live_smoke.yaml"
)
TASK_MANIFEST = PROJECT_ROOT / "harness/benchmarks/specs/orchvar_canary_tasks.yaml"
TASK_IDS = [
    "canary-reasoning-depth-01",
    "canary-context-recall-01",
    "canary-verbosity-sensitive-01",
    "canary-multi-turn-memory-01",
    "canary-tool-argument-precision-01",
    "canary-safety-01",
]
MODEL_REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
MODEL_ARTIFACT_ROOT = (
    "3b8a075149bffe4dea784db5b4b37bc0896688cba0b3de7d8d0f6e8ae6157b9e"
)
MODEL_RECEIPT_SHA256 = (
    "75ebfc531acdcbc0c39bbf83ee7bf5267a3ddf02c4fafdf6181624612a0d3082"
)
IMAGE_ID = "sha256:785f16e880d8c38acef02254adaccfb48dfd3a374af12115ec88590f036bf81a"
IMAGE_REGISTRY_DIGEST = (
    "127.0.0.1:5000/cotcodec-research@sha256:"
    "3f58e5256dff74ed3017a00af125e6ee2b6e4745208b9ea8a3668633760dfb00"
)


class LiveCanaryExperimentError(ValueError):
    """Raised when the preregistered live-smoke contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise LiveCanaryExperimentError(f"live canary {label} drifted")


def validate_experiment_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LiveCanaryExperimentError("live canary contract must be a mapping")
    _equal(
        set(payload),
        {
            "name",
            "description",
            "benchmark",
            "model",
            "conditions",
            "tasks",
            "seeds",
            "metrics",
            "actor",
            "tools",
            "task_manifest_sha256",
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
            "name": "degradation_canary_qwen35_4b_live_smoke",
            "benchmark": "orchvar_canary",
            "model": "qwen3.5-4b",
        },
        "identity",
    )
    _equal(payload.get("conditions"), ["english_only"], "conditions")
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
        {
            "type": "sqlite_canary_v1",
            "persistence": "isolated_in_memory_per_task",
        },
        "tool runtime",
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
            "run_id": "orchvar-qwen35-4b-live-smoke-v1",
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
            "purpose": "live_transport_and_execution_smoke_only",
            "limitation": (
                "The admitted spine uses one model plan per task. Tools execute for "
                "real, but no later model generation is conditioned on tool results "
                "in this version."
            ),
        },
        "claim boundary",
    )
    manifest_sha256 = hashlib.sha256(TASK_MANIFEST.read_bytes()).hexdigest()
    _equal(payload.get("task_manifest_sha256"), manifest_sha256, "task manifest")
    return payload


def validate_experiment(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    return validate_experiment_payload(load_yaml_file(path))


def main() -> int:
    path = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else DEFAULT_EXPERIMENT
    validate_experiment(path)
    print("Live OrchVar-Canary experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
