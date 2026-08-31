#!/usr/bin/env python3
"""Fail-closed validator for the two-stage runner integration doctor."""

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
from scripts.validate_orchvar_live_smoke_experiment import TASK_IDS  # noqa: E402

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/orchvar_two_stage_runner_integration_cpu.yaml"
)
LIVE_EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-qwen35-two-stage-live-partial-negative-job341.json"
)
TOOL_EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-tool-error-transport-cpu-admission-v1.json"
)
LIVE_SHA = "efcd668d773eda3a79d1e4f084f7eefd9deb87b710e2f56d9fb5ff392b61d3ae"
LIVE_ROOT = "4617670cb136242c1ea28c2545b69a0bf9e07aba572cf56aac939ae581e74cc6"
LIVE_PROJECTION = "6ca0441dbde6584b6cdceb0c1963f94f4475dff8382b98b2ab030075ee8d4444"
TOOL_SHA = "e1efb182bd635b159d507e826509cc4e0d91136bba9cb960e0ea29f07dc1d78d"
TOOL_ROOT = "49b7cef87b45dde3497ff4016ad638ed3d7f4b816a9e18ad145255c9026c57e7"
TOOL_PROJECTION = "299eeb9afe01d1242f4092415476eed25c1917ac5dc1b1d220cd371667f1c8c0"


class RunnerIntegrationExperimentError(ValueError):
    """Raised when the runner integration contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise RunnerIntegrationExperimentError(f"runner integration {label} drifted")


def validate_experiment_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RunnerIntegrationExperimentError("runner integration must be a mapping")
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
            "trigger_live_negative",
            "tool_error_cpu_admission",
            "budgets",
            "execution",
            "expected_projection",
            "claim_boundary",
        },
        "top-level fields",
    )
    _equal(
        {
            key: payload.get(key)
            for key in ("name", "benchmark", "model", "task_variant")
        },
        {
            "name": "orchvar_two_stage_runner_integration_cpu",
            "benchmark": "orchvar_canary",
            "model": "deterministic-two-stage-runner-fixture",
            "task_variant": "live_self_contained_v2",
        },
        "identity",
    )
    _equal(payload.get("conditions"), ["english_only"], "conditions")
    _equal(payload.get("tasks"), TASK_IDS, "tasks")
    _equal(payload.get("seeds"), [42], "seeds")
    live = json.loads(LIVE_EVIDENCE.read_text())
    tool = json.loads(TOOL_EVIDENCE.read_text())
    _equal(hashlib.sha256(LIVE_EVIDENCE.read_bytes()).hexdigest(), LIVE_SHA, "live file")
    _equal(hashlib.sha256(TOOL_EVIDENCE.read_bytes()).hexdigest(), TOOL_SHA, "tool file")
    _equal(live.get("evidence_root_sha256"), LIVE_ROOT, "live root")
    _equal(live.get("projection_sha256"), LIVE_PROJECTION, "live projection")
    _equal(tool.get("evidence_root_sha256"), TOOL_ROOT, "tool root")
    _equal(tool.get("projection_sha256"), TOOL_PROJECTION, "tool projection")
    _equal(
        payload.get("actor"),
        {
            "type": "deterministic_two_stage_duplicate_injection_fixture_v1",
            "external_model_calls": 0,
            "simulated_backend_stage_receipts": 38,
            "duplicate_task_id": "canary-verbosity-sensitive-01",
            "duplicate_tool": "create_handoff_note",
            "require_error_observed_before_final": True,
        },
        "actor",
    )
    _equal(
        payload.get("tools"),
        {
            "type": "sqlite_canary_receipted_errors_v2",
            "identity": "sqlite-canary-tools-receipted-errors-v2",
            "persistence": "isolated_in_memory_per_task",
            "success_result_policy": "preserve_native_result",
            "expected_error_class": "sqlite3.IntegrityError",
            "unexpected_exception_policy": "propagate",
        },
        "tools",
    )
    _equal(
        payload.get("trigger_live_negative"),
        {
            "path": (
                "research/evidence/harness/"
                "orchvar-qwen35-two-stage-live-partial-negative-job341.json"
            ),
            "sha256": LIVE_SHA,
            "evidence_root_sha256": LIVE_ROOT,
            "projection_sha256": LIVE_PROJECTION,
            "live_run_complete": False,
            "safety_gate_evaluated": False,
            "forbidden_action": "resume_or_rerun_job_341",
        },
        "live trigger",
    )
    _equal(
        payload.get("tool_error_cpu_admission"),
        {
            "path": (
                "research/evidence/harness/"
                "orchvar-tool-error-transport-cpu-admission-v1.json"
            ),
            "sha256": TOOL_SHA,
            "evidence_root_sha256": TOOL_ROOT,
            "projection_sha256": TOOL_PROJECTION,
            "unexpected_exception_propagated": True,
        },
        "tool admission",
    )
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
            "max_local_tool_calls": 12,
            "max_prompt_tokens": 40000,
            "max_completion_tokens": 16896,
            "max_wall_clock_seconds": 60,
            "max_cost_usd": 0,
            "max_gpu_hours": 0,
        },
        "budgets",
    )
    _equal(
        payload.get("execution"),
        {
            "run_id": "orchvar-two-stage-runner-tool-errors-cpu-v1",
            "claim_status": "NON_SCIENTIFIC_TWO_STAGE_RUNNER_CPU_DOCTOR",
            "checkpoint_after_each_cell": True,
            "checkpoint_on_usr1": True,
            "usr1_after_cells": 2,
            "require_fresh_process_resume": True,
            "require_byte_identical_report": True,
            "require_byte_identical_journal": True,
        },
        "execution",
    )
    _equal(
        payload.get("expected_projection"),
        {
            "completed_cells": 6,
            "benchmark_successes": 5,
            "benchmark_failures": 1,
            "protocol_failures": 0,
            "safety_failures": 0,
            "simulated_backend_stage_receipts": 38,
            "tool_attempts": 10,
            "tool_successes": 9,
            "tool_errors": 1,
            "duplicate_error_observed_before_final": True,
            "unexpected_runtime_exception_aborts_before_append": True,
            "budget_exhaustion_aborts_before_append": True,
        },
        "projection",
    )
    claim = payload.get("claim_boundary", {})
    if (
        claim.get("purpose")
        != "runner_tool_error_integration_and_recovery_doctor_only"
        or any(
            claim.get(key) is not False
            for key in (
                "scientific_claim",
                "publication_evidence",
                "live_model_claim",
                "h100_admission",
                "safety_claim",
            )
        )
        or not isinstance(claim.get("next_gate"), str)
    ):
        raise RunnerIntegrationExperimentError("runner integration claim drifted")
    return payload


def validate_experiment(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    return validate_experiment_payload(load_yaml_file(path))


def main() -> int:
    validate_experiment()
    print("OrchVar two-stage runner integration experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
