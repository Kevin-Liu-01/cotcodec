#!/usr/bin/env python3
"""Fail-closed validator for the deterministic OrchVar-Canary proof."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.yaml_utils import load_yaml_file  # noqa: E402

DEFAULT_EXPERIMENT = PROJECT_ROOT / "experiments/degradation_canary_local_01.yaml"
TASK_MANIFEST = PROJECT_ROOT / "harness/benchmarks/specs/orchvar_canary_tasks.yaml"
TASK_IDS = [
    "canary-reasoning-depth-01",
    "canary-context-recall-01",
    "canary-verbosity-sensitive-01",
    "canary-multi-turn-memory-01",
    "canary-tool-argument-precision-01",
    "canary-safety-01",
]
CONDITIONS = [
    "english_only",
    "english_only_low_effort",
    "english_only_no_thinking_cache",
    "english_only_25word_limit",
]


class CanaryExperimentError(ValueError):
    """Raised when the deterministic canary contract drifts."""


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CanaryExperimentError(f"deterministic canary {label} drifted")


def validate_experiment(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    payload = load_yaml_file(path)
    if not isinstance(payload, dict):
        raise CanaryExperimentError("deterministic canary contract must be a mapping")
    _equal(
        {key: payload.get(key) for key in ("name", "benchmark", "model")},
        {
            "name": "degradation_canary_local_01",
            "benchmark": "orchvar_canary",
            "model": "deterministic-canary-v1",
        },
        "identity",
    )
    _equal(payload.get("conditions"), CONDITIONS, "conditions")
    _equal(payload.get("tasks"), TASK_IDS, "task roster")
    _equal(payload.get("seeds"), [42, 43, 44, 45, 46], "seeds")
    _equal(payload.get("actor"), {"type": "deterministic_canary_v1"}, "actor")
    _equal(
        payload.get("budgets"),
        {
            "max_steps_per_task": 12,
            "max_tool_calls_per_task": 4,
            "external_model_calls": 0,
            "external_tool_calls": 0,
            "max_cost_usd": 0,
        },
        "budgets",
    )
    _equal(
        payload.get("execution"),
        {
            "run_id": "degradation-canary-local-01",
            "checkpoint_after_each_cell": True,
            "checkpoint_on_usr1": True,
            "deterministic_latency": True,
        },
        "execution",
    )
    _equal(
        payload.get("expected_regressions"),
        {
            "english_only_low_effort": ["reasoning_depth"],
            "english_only_no_thinking_cache": [
                "context_recall",
                "multi_turn_memory",
            ],
            "english_only_25word_limit": ["verbosity_sensitive"],
        },
        "expected regressions",
    )
    manifest_sha = hashlib.sha256(TASK_MANIFEST.read_bytes()).hexdigest()
    _equal(payload.get("task_manifest_sha256"), manifest_sha, "task manifest hash")
    if not isinstance(payload.get("claim_boundary"), str) or not payload[
        "claim_boundary"
    ].strip():
        raise CanaryExperimentError("deterministic canary claim boundary is missing")
    return payload


def main() -> int:
    validate_experiment()
    print("Deterministic OrchVar-Canary experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
