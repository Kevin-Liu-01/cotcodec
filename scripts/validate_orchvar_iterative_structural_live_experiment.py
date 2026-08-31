#!/usr/bin/env python3
"""Fail-closed validator for structural iterative live protocol v2."""

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.yaml_utils import load_yaml_file  # noqa: E402
from scripts.validate_orchvar_iterative_live_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT as V1_EXPERIMENT,
)
from scripts.validate_orchvar_iterative_live_experiment import (  # noqa: E402
    IterativeLiveExperimentError,
)
from scripts.validate_orchvar_iterative_live_experiment import (  # noqa: E402
    validate_experiment_payload as validate_v1,
)

DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments/orchvar_qwen35_iterative_structural_live_smoke.yaml"
)
EVIDENCE = (
    PROJECT_ROOT
    / "research/evidence/harness/"
    "orchvar-iterative-structural-json-v2-cpu-admission.json"
)
EVIDENCE_SHA256 = "2f538b4057276f61ab3ab7ea29bb2bd53dc68d2487b2eaec7380206f39c9e15f"
EVIDENCE_ROOT = "8dc084bb24b54e15fe0d6d301a5268c3c9028e1fb16044097c8428a93b751dbc"
PROJECTION = "c15a7f8a44fdf46ae43a3dd998f11b1f4c3ddc0409567c83592b0b4cb80be6c9"


def validate_experiment_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise IterativeLiveExperimentError("structural live contract must be a mapping")
    v1 = load_yaml_file(V1_EXPERIMENT)
    normalized = deepcopy(payload)
    normalized["name"] = v1["name"]
    normalized["actor"]["type"] = v1["actor"]["type"]
    normalized["iterative_cpu_admission"] = v1["iterative_cpu_admission"]
    normalized["execution"] = v1["execution"]
    normalized["claim_boundary"] = v1["claim_boundary"]
    validate_v1(normalized)
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    expected_admission = {
        "status": "ORCHVAR_ITERATIVE_STRUCTURAL_JSON_V2_CPU_ADMISSION_PASS",
        "evidence": (
            "research/evidence/harness/"
            "orchvar-iterative-structural-json-v2-cpu-admission.json"
        ),
        "evidence_sha256": EVIDENCE_SHA256,
        "evidence_root_sha256": EVIDENCE_ROOT,
        "projection_sha256": PROJECTION,
        "external_model_calls": 0,
        "deterministic_task_successes": 6,
        "sqlite_tool_operations": 9,
        "actual_usr1_acknowledged_cells": 2,
        "safety_gate_passed": True,
    }
    claim = payload.get("claim_boundary", {})
    if (
        payload.get("name") != "orchvar_qwen35_iterative_structural_live_smoke"
        or payload.get("actor", {}).get("type")
        != "transformers_iterative_structural_json_v2"
        or payload.get("iterative_cpu_admission") != expected_admission
        or payload.get("execution", {}).get("run_id")
        != "orchvar-qwen35-iterative-structural-live-v2"
        or hashlib.sha256(EVIDENCE.read_bytes()).hexdigest() != EVIDENCE_SHA256
        or evidence.get("evidence_root_sha256") != EVIDENCE_ROOT
        or evidence.get("projection_sha256") != PROJECTION
        or claim.get("purpose")
        != "structural_iterative_tool_result_conditioning_and_safety_check_only"
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
    ):
        raise IterativeLiveExperimentError("structural live contract drifted")
    return payload


def validate_experiment(path: Path = DEFAULT_EXPERIMENT) -> dict[str, Any]:
    return validate_experiment_payload(load_yaml_file(path))


def main() -> int:
    validate_experiment()
    print("Structural iterative live OrchVar experiment PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
