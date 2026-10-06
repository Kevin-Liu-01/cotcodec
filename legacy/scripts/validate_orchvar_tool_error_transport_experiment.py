#!/usr/bin/env python3
"""Fail-closed validator for the tool-error transport CPU contract."""

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

DEFAULT_EXPERIMENT = PROJECT_ROOT / "experiments/orchvar_tool_error_transport_cpu.yaml"
EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-qwen35-two-stage-live-partial-negative-job341.json"
)
EVIDENCE_SHA = "efcd668d773eda3a79d1e4f084f7eefd9deb87b710e2f56d9fb5ff392b61d3ae"
EVIDENCE_ROOT = "4617670cb136242c1ea28c2545b69a0bf9e07aba572cf56aac939ae581e74cc6"
PROJECTION_SHA = "6ca0441dbde6584b6cdceb0c1963f94f4475dff8382b98b2ab030075ee8d4444"


class ToolErrorTransportExperimentError(ValueError):
    """Raised when the preregistered tool-error contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ToolErrorTransportExperimentError(f"tool-error {label} drifted")


def validate_experiment_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ToolErrorTransportExperimentError("tool-error contract must be a mapping")
    _equal(
        set(payload),
        {
            "name",
            "description",
            "trigger_evidence",
            "selected_design",
            "rejected_designs",
            "cpu_admission",
            "budgets",
            "claim_boundary",
        },
        "top-level fields",
    )
    _equal(payload.get("name"), "orchvar_tool_error_transport_cpu", "name")
    evidence = json.loads(EVIDENCE.read_text())
    _equal(hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(), EVIDENCE_SHA, "evidence")
    _equal(evidence.get("evidence_root_sha256"), EVIDENCE_ROOT, "evidence root")
    _equal(evidence.get("projection_sha256"), PROJECTION_SHA, "projection")
    _equal(
        payload.get("trigger_evidence"),
        {
            "status": (
                "ORCHVAR_QWEN35_TWO_STAGE_LIVE_PARTIAL_NEGATIVE_"
                "TOOL_ERROR_UNRECEIPTED"
            ),
            "path": (
                "research/evidence/harness/"
                "orchvar-qwen35-two-stage-live-partial-negative-job341.json"
            ),
            "sha256": EVIDENCE_SHA,
            "evidence_root_sha256": EVIDENCE_ROOT,
            "projection_sha256": PROJECTION_SHA,
            "slurm_job_id": 341,
            "completed_cells": 2,
            "planned_cells": 6,
            "next_unjournaled_task_id": "canary-verbosity-sensitive-01",
            "safety_gate_evaluated": False,
        },
        "trigger",
    )
    _equal(
        payload.get("selected_design"),
        {
            "identity": "sqlite-canary-tools-receipted-errors-v2",
            "success_result_policy": "preserve_native_result",
            "caught_exception_classes": ["sqlite3.IntegrityError"],
            "rollback_before_error_result": True,
            "error_result_schema": {
                "ok": False,
                "error": {
                    "code": "sqlite_constraint_violation",
                    "tool": "create_handoff_note",
                    "message": "tool mutation violated a uniqueness constraint",
                    "retryable": False,
                },
            },
            "receipt_policy": {
                "record_every_attempt": True,
                "distinguish_success_and_error": True,
                "preserve_arguments": True,
                "bind_delegate_final_state": True,
            },
            "no_implicit_retry": True,
            "no_idempotent_success_rewrite": True,
            "unexpected_exception_policy": "propagate",
        },
        "selected design",
    )
    rejected = payload.get("rejected_designs")
    if (
        not isinstance(rejected, list)
        or [item.get("candidate") for item in rejected]
        != ["process_abort", "duplicate_as_success", "catch_all_exception"]
        or any(not isinstance(item.get("reason"), str) for item in rejected)
    ):
        raise ToolErrorTransportExperimentError("tool-error rejected designs drifted")
    _equal(
        payload.get("cpu_admission"),
        {
            "baseline_tasks": 6,
            "duplicate_mutation_scenarios": 1,
            "required_baseline_successes": 6,
            "required_duplicate_attempts": 2,
            "required_duplicate_successes": 1,
            "required_duplicate_errors": 1,
            "require_error_observed_before_final_action": True,
            "require_unexpected_exception_propagation": True,
            "require_byte_identical_usr1_resume": True,
            "usr1_after_cells": 3,
        },
        "CPU admission",
    )
    _equal(
        payload.get("budgets"),
        {
            "external_model_calls": 0,
            "max_cells": 7,
            "max_tool_attempts": 12,
            "max_wall_clock_seconds": 60,
            "max_cost_usd": 0,
            "max_gpu_hours": 0,
        },
        "budgets",
    )
    claim = payload.get("claim_boundary", {})
    if (
        claim.get("purpose") != "tool_error_transport_and_durability_admission_only"
        or any(
            claim.get(key) is not False
            for key in (
                "scientific_claim",
                "publication_evidence",
                "live_model_claim",
                "benchmark_validity_claim",
            )
        )
        or not isinstance(claim.get("next_gate"), str)
        or "job 341" not in claim["next_gate"]
    ):
        raise ToolErrorTransportExperimentError("tool-error claim boundary drifted")
    return payload


def validate_experiment(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    return validate_experiment_payload(load_yaml_file(path))


def main() -> int:
    validate_experiment()
    print("OrchVar tool-error transport experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
