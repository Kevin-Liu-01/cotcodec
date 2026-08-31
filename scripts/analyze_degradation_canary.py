#!/usr/bin/env python3
"""Analyze exact task/seed pairs from a completed deterministic canary run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.metrics.degradation import DegradationDetector  # noqa: E402
from harness.run_state import canonical_json  # noqa: E402
from scripts.validate_degradation_canary_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment,
)


class CanaryAnalysisError(ValueError):
    """Raised when canary outputs are incomplete or contradict the contract."""


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanaryAnalysisError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CanaryAnalysisError(f"{label} must be a mapping")
    return payload


def analyze(
    output_root: Path,
    run_id: str,
    *,
    experiment_path: Path = DEFAULT_EXPERIMENT,
    output_path: Path | None = None,
) -> dict[str, Any]:
    contract = validate_experiment(experiment_path)
    summary_path = output_root / "results" / f"{run_id}_summary.json"
    summary = _load_json(summary_path, "runner summary")
    if summary.get("status") != "COMPLETE" or summary.get("completed_cells") != 120:
        raise CanaryAnalysisError("runner summary is not the complete 120-cell plan")
    artifacts = summary.get("trace_artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 4:
        raise CanaryAnalysisError("runner summary must bind four trace artifacts")

    by_condition: dict[str, tuple[Path, str]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise CanaryAnalysisError("trace artifact is malformed")
        path = output_root / str(artifact.get("path", ""))
        if not path.is_file():
            raise CanaryAnalysisError(f"trace artifact is missing: {path}")
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != artifact.get("sha256"):
            raise CanaryAnalysisError(f"trace artifact hash drifted: {path}")
        parts = path.parts
        try:
            condition = parts[parts.index("orchvar_canary") + 1]
        except (ValueError, IndexError) as exc:
            raise CanaryAnalysisError(f"cannot infer trace condition: {path}") from exc
        if condition in by_condition:
            raise CanaryAnalysisError(f"duplicate trace artifact for {condition}")
        by_condition[condition] = (path, actual_sha)

    baseline_condition = "english_only"
    expected = contract["expected_regressions"]
    required_conditions = {baseline_condition, *expected}
    if set(by_condition) != required_conditions:
        raise CanaryAnalysisError("trace condition roster drifted")

    detector = DegradationDetector()
    treatments: dict[str, Any] = {}
    for condition, expected_categories in expected.items():
        category_report = detector.run_canary_by_category(
            by_condition[baseline_condition][0],
            by_condition[condition][0],
        )
        observed = sorted(
            category
            for category, result in category_report["categories"].items()
            if result["is_degradation"]
        )
        if observed != sorted(expected_categories):
            raise CanaryAnalysisError(
                f"{condition}: expected regressions {sorted(expected_categories)}, "
                f"observed {observed}"
            )
        from scipy import stats

        p_values = [
            category_report["categories"][category]["p_value"]
            for category in expected_categories
        ]
        fisher_statistic = -2 * sum(math.log(max(p_value, 1e-300)) for p_value in p_values)
        combined_p = 1 - stats.chi2.cdf(fisher_statistic, df=2 * len(p_values))
        treatments[condition] = {
            **category_report,
            "expected_regressions": sorted(expected_categories),
            "observed_regressions": observed,
            "fisher_expected_categories": {
                "method": "fisher",
                "statistic": round(fisher_statistic, 6),
                "combined_p_value": round(combined_p, 6),
                "is_degradation": bool(combined_p < detector.confidence_level),
            },
        }

    report = {
        "schema_version": 1,
        "status": "PASS",
        "scientific_result": False,
        "publication_ready": False,
        "run_id": run_id,
        "runner_summary": {
            "path": str(summary_path.relative_to(output_root)),
            "sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
            "contract_sha256": summary["contract_sha256"],
            "plan_sha256": summary["plan_sha256"],
            "journal_root_sha256": summary["journal_root_sha256"],
        },
        "trace_sha256_by_condition": {
            condition: receipt[1] for condition, receipt in sorted(by_condition.items())
        },
        "treatments": treatments,
        "claim_boundary": contract["claim_boundary"],
    }
    destination = output_path or output_root / "results" / f"{run_id}_degradation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(canonical_json(report) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    parser.add_argument("run_id")
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze(
        args.output_root,
        args.run_id,
        experiment_path=args.experiment,
        output_path=args.output,
    )
    print(f"OrchVar-Canary analysis {report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
