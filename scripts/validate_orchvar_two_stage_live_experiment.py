#!/usr/bin/env python3
"""Fail-closed validator for the two-stage live smoke contract."""

from __future__ import annotations

import hashlib
import json
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

DEFAULT_EXPERIMENT = PROJECT_ROOT / "experiments/orchvar_qwen35_two_stage_live_smoke.yaml"
AUDIT = (
    PROJECT_ROOT
    / "research/evidence/harness/orchvar-message-action-transport-audit-v1.json"
)
CPU = (
    PROJECT_ROOT
    / "research/evidence/harness/orchvar-two-stage-message-action-cpu-admission-v3.json"
)
AUDIT_SHA = "d22f4434f6fa15c7010cee6a4517d3492c41a0a4c7773a798d02ea88fe4d6eaa"
AUDIT_PROJECTION = "8660f4aaf6e60bcb8d91febc44daaf654418defce128b64e4f56d351e96ef070"
CPU_SHA = "3a51067a2bb29c5a0ed99f4b0408421555f652d93e87950945236b56c88a507a"
CPU_ROOT = "5087024c699f0e7008ff6b7526f4329aad00ab8b7644bba0303fa8da632a8d85"
CPU_PROJECTION = "00ff222140326abe9aaeb2660a40c9dfcc64f53651be64f6f81ea3be6b5dbd1f"
TASK_MANIFEST_SHA = "325df3670e69539e857784e4184f3b36e62ff11dfc5701773c75c7af457b42b0"


class TwoStageLiveExperimentError(ValueError):
    """Raised when the registered two-stage contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise TwoStageLiveExperimentError(f"two-stage live {label} drifted")


def validate_experiment_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TwoStageLiveExperimentError("two-stage live contract must be a mapping")
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
            "transport_audit",
            "two_stage_cpu_admission",
            "budgets",
            "compliance",
            "execution",
            "containment",
            "claim_boundary",
        },
        "top-level fields",
    )
    _equal(
        {key: payload.get(key) for key in ("name", "benchmark", "model")},
        {
            "name": "orchvar_qwen35_two_stage_live_smoke",
            "benchmark": "orchvar_canary",
            "model": "qwen3.5-4b",
        },
        "identity",
    )
    _equal(payload.get("conditions"), ["english_only"], "conditions")
    _equal(payload.get("task_variant"), "live_self_contained_v2", "task variant")
    _equal(payload.get("tasks"), TASK_IDS, "tasks")
    _equal(payload.get("seeds"), [42], "seeds")
    _equal(payload.get("task_manifest_sha256"), TASK_MANIFEST_SHA, "task manifest")
    _equal(
        payload.get("actor"),
        {
            "type": "transformers_two_stage_plain_action_json_v1",
            "registry_model_id": "qwen3.5-4b",
            "registry_path": "models/registry.yaml",
            "repo_id": "Qwen/Qwen3.5-4B",
            "revision": MODEL_REVISION,
            "artifact_root_sha256": MODEL_ARTIFACT_ROOT,
            "model_receipt_sha256": MODEL_RECEIPT_SHA256,
            "max_new_tokens": 256,
            "dtype": "bfloat16",
            "device_map": "auto",
            "use_chat_template": True,
            "deterministic": True,
            "attention_implementation": "eager",
            "planner_cadence": "every_decision",
            "memory_cadence": "first_decision_only",
            "message_fallback": "none",
            "action_fallback": "none",
        },
        "actor",
    )
    audit = json.loads(AUDIT.read_text())
    cpu = json.loads(CPU.read_text())
    _equal(hashlib.sha256(AUDIT.read_bytes()).hexdigest(), AUDIT_SHA, "audit file")
    _equal(hashlib.sha256(CPU.read_bytes()).hexdigest(), CPU_SHA, "CPU file")
    _equal(
        payload.get("transport_audit"),
        {
            "status": "ORCHVAR_MESSAGE_ACTION_TRANSPORT_TWO_STAGE_SELECTED_CPU_REQUIRED",
            "evidence": (
                "research/evidence/harness/orchvar-message-action-transport-audit-v1.json"
            ),
            "evidence_sha256": AUDIT_SHA,
            "projection_sha256": AUDIT_PROJECTION,
            "selected_candidate": "message_then_action_two_stage",
            "external_model_calls": 0,
        },
        "transport audit",
    )
    _equal(
        payload.get("two_stage_cpu_admission"),
        {
            "status": "ORCHVAR_TWO_STAGE_MESSAGE_ACTION_CPU_ADMISSION_PASS",
            "evidence": (
                "research/evidence/harness/"
                "orchvar-two-stage-message-action-cpu-admission-v3.json"
            ),
            "evidence_sha256": CPU_SHA,
            "evidence_root_sha256": CPU_ROOT,
            "projection_sha256": CPU_PROJECTION,
            "external_model_calls": 0,
            "task_successes": 6,
            "message_stages": 15,
            "action_stages": 15,
            "sqlite_tool_operations": 9,
            "actual_usr1_acknowledged_cells": 2,
            "safety_gate_passed": True,
        },
        "CPU admission",
    )
    _equal(audit.get("projection_sha256"), AUDIT_PROJECTION, "audit projection")
    _equal(cpu.get("evidence_root_sha256"), CPU_ROOT, "CPU root")
    _equal(cpu.get("projection_sha256"), CPU_PROJECTION, "CPU projection")
    _equal(
        payload.get("budgets"),
        {
            "max_decisions_per_task": 5,
            "max_steps_per_task": 12,
            "max_tool_calls_per_task": 4,
            "max_planner_stage_calls": 30,
            "max_memory_stage_calls": 6,
            "max_message_stage_calls": 36,
            "max_action_stage_calls": 30,
            "max_external_model_calls": 66,
            "expected_success_path_external_model_calls": 36,
            "max_local_tool_calls": 12,
            "max_prompt_tokens": 40000,
            "max_completion_tokens": 16896,
            "max_cost_usd": 0,
            "max_gpu_hours": 0.5,
        },
        "budgets",
    )
    _equal(
        payload.get("compliance"),
        {
            "required_message_compliance_rate": 1.0,
            "missing_message_policy": "stop_cell_before_action",
            "invalid_action_policy": "stop_cell_before_tool",
            "retry_count": 0,
            "synthesize_missing_messages": False,
            "coerce_action_arguments": False,
        },
        "compliance",
    )
    _equal(
        payload.get("execution"),
        {
            "run_id": "orchvar-qwen35-two-stage-live-v1",
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
    claim = payload.get("claim_boundary", {})
    if (
        claim.get("purpose")
        != "two_stage_message_action_transport_and_safety_check_only"
        or any(
            claim.get(key) is not False
            for key in (
                "scientific_claim",
                "publication_evidence",
                "language_effect_claim",
                "benchmark_validity_claim",
                "model_quality_claim",
            )
        )
        or not isinstance(claim.get("limitation"), str)
    ):
        raise TwoStageLiveExperimentError("two-stage live claim boundary drifted")
    return payload


def validate_experiment(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    return validate_experiment_payload(load_yaml_file(path))


def main() -> int:
    validate_experiment()
    print("Two-stage live OrchVar experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
