#!/usr/bin/env python3
"""Fail-closed aggregation for the registered MemoryBank H100 screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.causal_memory_trials import TrialBundle  # noqa: E402
from harness.memory_trials import FrozenMemorySystem  # noqa: E402
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.run_memory_model_screen import summarize_screen  # noqa: E402
from scripts.validate_memorybank_h100_experiment import (  # noqa: E402
    DEFAULT_EXPERIMENT,
    validate_experiment_contract,
)

ARM_ORDER = ("corrected", "upstream_precedence", "no_decay")
CONTRASTS = (
    ("corrected_minus_upstream_precedence", "corrected", "upstream_precedence"),
    ("corrected_minus_no_decay", "corrected", "no_decay"),
)
BOOTSTRAP_SEED = 20260816
BOOTSTRAP_DRAWS = 20_000


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"artifact must be a regular non-symlink file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _verify_bundle(seed_root: Path, claimed_manifest_sha256: str) -> TrialBundle:
    bundle_root = (seed_root / "bundle").resolve()
    manifest_path = bundle_root / "manifest.json"
    if _sha256_file(manifest_path) != claimed_manifest_sha256:
        raise ValueError(f"bundle manifest digest differs: {bundle_root}")
    manifest = _read_json(manifest_path)
    if manifest.get("status") != "COMPLETE":
        raise ValueError(f"bundle is not complete: {bundle_root}")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"bundle file manifest is missing: {bundle_root}")
    for name, expected in files.items():
        if (
            not isinstance(name, str)
            or not isinstance(expected, str)
            or Path(name).is_absolute()
            or ".." in Path(name).parts
        ):
            raise ValueError("bundle file manifest is malformed")
        artifact = (bundle_root / name).resolve()
        if bundle_root not in artifact.parents or not artifact.is_file() or artifact.is_symlink():
            raise ValueError(f"bundle artifact is unsafe or absent: {artifact}")
        if _sha256_file(artifact) != expected:
            raise ValueError(f"bundle artifact digest differs: {artifact}")
    return TrialBundle(root=bundle_root, manifest_sha256=claimed_manifest_sha256)


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("cannot compute a mean over an empty sequence")
    return math.fsum(values) / len(values)


def _percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot compute a percentile over an empty sequence")
    position = probability * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _cluster_bootstrap_ratio(
    clusters: Mapping[str, tuple[float, int]],
    *,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if draws < 1:
        raise ValueError("bootstrap draws must be positive")
    cluster_ids = sorted(clusters)
    if not cluster_ids:
        raise ValueError("bootstrap requires at least one task cluster")
    total_numerator = math.fsum(clusters[item][0] for item in cluster_ids)
    total_denominator = sum(clusters[item][1] for item in cluster_ids)
    if total_denominator <= 0:
        raise ValueError("bootstrap estimand has no observations")
    point = 100.0 * total_numerator / total_denominator
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(draws):
        chosen = rng.choices(cluster_ids, k=len(cluster_ids))
        denominator = sum(clusters[item][1] for item in chosen)
        if denominator == 0:
            continue
        numerator = math.fsum(clusters[item][0] for item in chosen)
        samples.append(100.0 * numerator / denominator)
    samples.sort()
    if len(samples) != draws:
        raise ValueError("bootstrap produced an empty-observation resample")
    return {
        "point_delta_points": point,
        "ci95_low_points": _percentile(samples, 0.025),
        "ci95_high_points": _percentile(samples, 0.975),
        "cluster_count": len(cluster_ids),
        "observation_count": total_denominator,
        "bootstrap_draws": draws,
        "bootstrap_seed": seed,
    }


def _validate_arm(
    *,
    arm: str,
    arm_root: Path,
    config: Mapping[str, Any],
) -> dict[int, dict[str, Any]]:
    arm_spec = config["input"]["bundles"][arm]
    frozen_path = PROJECT_ROOT / arm_spec["path"]
    if _sha256_file(frozen_path) != arm_spec["file_sha256"]:
        raise ValueError(f"{arm}: registered frozen bundle file differs")
    frozen = FrozenMemorySystem(frozen_path)
    if frozen.bundle_sha256 != arm_spec["semantic_sha256"]:
        raise ValueError(f"{arm}: registered frozen bundle semantics differ")
    if frozen.receipt.system_id != arm_spec["system_id"]:
        raise ValueError(f"{arm}: registered memory system identity differs")

    wrapper_path = arm_root / "screen-matrix-report.json"
    wrapper = _read_json(wrapper_path)
    seeds = tuple(config["design"]["assignment_seeds"])
    if (
        wrapper.get("status") != "MODEL_CONTROL_MATRIX_CELL_PASS"
        or wrapper.get("scientific_result") is not False
        or wrapper.get("evaluation_mode") != "matrix-cell"
        or tuple(wrapper.get("assignment_seeds", ())) != seeds
    ):
        raise ValueError(f"{arm}: matrix wrapper is incomplete or invalid")
    embedded = wrapper.get("seed_reports")
    if not isinstance(embedded, list) or len(embedded) != len(seeds):
        raise ValueError(f"{arm}: matrix wrapper lacks every seed")
    embedded_by_seed = {
        item.get("assignment_seed"): item.get("report")
        for item in embedded
        if isinstance(item, dict)
    }
    if set(embedded_by_seed) != set(seeds):
        raise ValueError(f"{arm}: matrix wrapper seed identities differ")

    validated: dict[int, dict[str, Any]] = {}
    for seed in seeds:
        seed_root = arm_root / f"seed-{seed}"
        report_path = seed_root / "screen-report.json"
        report = _read_json(report_path)
        if report != embedded_by_seed[seed]:
            raise ValueError(f"{arm} seed {seed}: embedded report differs")
        if (
            report.get("status") != "MODEL_MATRIX_CELL_VALID"
            or report.get("scientific_result") is not False
            or report.get("evaluation_mode") != "matrix-cell"
            or report.get("assignment_seed") != seed
        ):
            raise ValueError(f"{arm} seed {seed}: cell is not valid")
        if (
            report.get("model_id") != config["model"]["model_id"]
            or report.get("revision") != config["model"]["revision"]
            or report.get("artifact_root_sha256")
            != config["model"]["artifact_root_sha256"]
        ):
            raise ValueError(f"{arm} seed {seed}: model identity differs")
        if (
            report.get("task_manifest_sha256")
            != config["input"]["task_manifest_sha256"]
            or report.get("memory_bundle_sha256") != arm_spec["semantic_sha256"]
            or report.get("memory_treatment_mode")
            != config["input"]["treatment_mode"]
        ):
            raise ValueError(f"{arm} seed {seed}: task or memory contract differs")
        memory_system = report.get("memory_system")
        if not isinstance(memory_system, dict) or memory_system.get("system_id") != arm_spec[
            "system_id"
        ]:
            raise ValueError(f"{arm} seed {seed}: memory-system receipt differs")
        gates = report.get("validity_gates")
        if not isinstance(gates, dict) or not gates or not all(
            value is True for value in gates.values()
        ):
            raise ValueError(f"{arm} seed {seed}: a validity gate failed")
        actor_contract = report.get("actor_contract")
        if not isinstance(actor_contract, dict) or report.get(
            "actor_contract_sha256"
        ) != sha256_text(canonical_json(actor_contract)):
            raise ValueError(f"{arm} seed {seed}: actor contract digest differs")

        bundle = _verify_bundle(seed_root, str(report.get("bundle_manifest_sha256")))
        metrics = summarize_screen(bundle)
        if metrics != report.get("metrics"):
            raise ValueError(f"{arm} seed {seed}: metrics differ from raw bundle")
        if (
            metrics.get("episodes") != config["input"]["task_count"]
            or metrics.get("assignment_seed") != seed
            or len(metrics.get("task_results", ())) != config["input"]["task_count"]
        ):
            raise ValueError(f"{arm} seed {seed}: task coverage differs")
        validated[seed] = {
            "report": report,
            "metrics": metrics,
            "report_sha256": _sha256_file(report_path),
            "bundle_manifest_sha256": bundle.manifest_sha256,
        }
    return validated


def _contrast(
    *,
    left: str,
    right: str,
    cells: Mapping[str, Mapping[int, dict[str, Any]]],
    seeds: Sequence[int],
) -> dict[str, Any]:
    task_all: dict[str, list[float]] = {}
    task_served: dict[str, list[float]] = {}
    task_holdout: dict[str, list[float]] = {}
    per_seed: list[dict[str, Any]] = []
    for seed in seeds:
        left_metrics = cells[left][seed]["metrics"]
        right_metrics = cells[right][seed]["metrics"]
        if (
            left_metrics["assignment_schedule_sha256"]
            != right_metrics["assignment_schedule_sha256"]
            or left_metrics["trial_plan_sha256"] != right_metrics["trial_plan_sha256"]
        ):
            raise ValueError(f"seed {seed}: contrast assignment contract differs")
        left_rows = left_metrics["task_results"]
        right_rows = right_metrics["task_results"]
        if len(left_rows) != len(right_rows):
            raise ValueError(f"seed {seed}: contrast task counts differ")
        all_deltas: list[float] = []
        served_deltas: list[float] = []
        holdout_deltas: list[float] = []
        for left_row, right_row in zip(left_rows, right_rows, strict=True):
            identity = ("trial_id", "group_id", "visibility")
            if any(left_row[key] != right_row[key] for key in identity):
                raise ValueError(f"seed {seed}: paired task identity differs")
            trial_id = str(left_row["trial_id"])
            delta = float(bool(left_row["success"])) - float(bool(right_row["success"]))
            task_all.setdefault(trial_id, []).append(delta)
            all_deltas.append(delta)
            if left_row["visibility"] == "serve":
                task_served.setdefault(trial_id, []).append(delta)
                served_deltas.append(delta)
            else:
                task_holdout.setdefault(trial_id, []).append(delta)
                holdout_deltas.append(delta)
        per_seed.append(
            {
                "assignment_seed": seed,
                "all_task_delta_points": 100.0 * _mean(all_deltas),
                "served_delta_points": 100.0 * _mean(served_deltas),
                "holdout_delta_points": 100.0 * _mean(holdout_deltas),
                "served_tasks": len(served_deltas),
                "holdout_tasks": len(holdout_deltas),
            }
        )

    all_clusters = {
        trial_id: (math.fsum(values), len(values)) for trial_id, values in task_all.items()
    }
    served_clusters = {
        trial_id: (math.fsum(values), len(values))
        for trial_id, values in task_served.items()
    }
    holdout_clusters = {
        trial_id: (math.fsum(values), len(values))
        for trial_id, values in task_holdout.items()
    }
    return {
        "left_arm": left,
        "right_arm": right,
        "primary_served_oracle_success": _cluster_bootstrap_ratio(served_clusters),
        "diagnostic_all_assignment_cells": _cluster_bootstrap_ratio(all_clusters),
        "diagnostic_holdout_cells": _cluster_bootstrap_ratio(holdout_clusters),
        "coverage": {
            "total_tasks": len(task_all),
            "tasks_observed_served_at_least_once": len(task_served),
            "tasks_observed_holdout_at_least_once": len(task_holdout),
            "tasks_never_observed_served": len(set(task_all) - set(task_served)),
            "tasks_never_observed_holdout": len(set(task_all) - set(task_holdout)),
        },
        "per_seed": per_seed,
        "seed_semantics": "repeated assignment designs; not independent task samples",
    }


def aggregate_memorybank_h100_screen(
    *,
    experiment_path: Path,
    arm_roots: Mapping[str, Path],
) -> dict[str, Any]:
    config = validate_experiment_contract(experiment_path)
    if set(arm_roots) != set(ARM_ORDER):
        raise ValueError("exactly the three registered MemoryBank arms are required")
    cells = {
        arm: _validate_arm(arm=arm, arm_root=arm_roots[arm].resolve(), config=config)
        for arm in ARM_ORDER
    }
    seeds = tuple(config["design"]["assignment_seeds"])
    reference_identity: dict[str, Any] | None = None
    schedules: dict[int, str] = {}
    plans: dict[int, str] = {}
    arm_receipts: list[dict[str, Any]] = []
    for arm in ARM_ORDER:
        seed_receipts: list[dict[str, Any]] = []
        for seed in seeds:
            report = cells[arm][seed]["report"]
            metrics = cells[arm][seed]["metrics"]
            identity = {
                "model_id": report["model_id"],
                "revision": report["revision"],
                "artifact_root_sha256": report["artifact_root_sha256"],
                "actor_contract_sha256": report["actor_contract_sha256"],
                "task_manifest_sha256": report["task_manifest_sha256"],
                "memory_treatment_mode": report["memory_treatment_mode"],
            }
            if reference_identity is None:
                reference_identity = identity
            elif identity != reference_identity:
                raise ValueError("actor/model/task identity differs across arms or seeds")
            prior_schedule = schedules.setdefault(seed, metrics["assignment_schedule_sha256"])
            prior_plan = plans.setdefault(seed, metrics["trial_plan_sha256"])
            if prior_schedule != metrics["assignment_schedule_sha256"]:
                raise ValueError(f"seed {seed}: assignment schedule differs across arms")
            if prior_plan != metrics["trial_plan_sha256"]:
                raise ValueError(f"seed {seed}: trial plan differs across arms")
            seed_receipts.append(
                {
                    "assignment_seed": seed,
                    "report_sha256": cells[arm][seed]["report_sha256"],
                    "bundle_manifest_sha256": cells[arm][seed][
                        "bundle_manifest_sha256"
                    ],
                    "served_episodes": metrics["served_episodes"],
                    "served_oracle_success": metrics["served_oracle_success"],
                    "valid_action_rate": metrics["valid_action_rate"],
                    "safety_failures": metrics["safety_failures"],
                }
            )
        arm_receipts.append(
            {
                "arm": arm,
                "system_id": config["input"]["bundles"][arm]["system_id"],
                "frozen_bundle_sha256": config["input"]["bundles"][arm][
                    "semantic_sha256"
                ],
                "seeds": seed_receipts,
            }
        )

    contrasts = {
        name: _contrast(left=left, right=right, cells=cells, seeds=seeds)
        for name, left, right in CONTRASTS
    }
    primary = contrasts["corrected_minus_upstream_precedence"][
        "primary_served_oracle_success"
    ]
    threshold = float(config["design"]["minimum_corrected_minus_upstream_points"])
    effect_gate = primary["point_delta_points"] >= threshold
    interval_gate = primary["ci95_low_points"] > 0.0
    validity_gate = all(
        seed["safety_failures"] == 0
        for arm in arm_receipts
        for seed in arm["seeds"]
    )
    passed = effect_gate and interval_gate and validity_gate
    unsigned = {
        "schema_version": 1,
        "status": (
            "MEMORYBANK_CORRECTED_DECAY_ACTOR_PASS"
            if passed
            else "MEMORYBANK_CORRECTED_DECAY_ACTOR_KILLED"
        ),
        "scientific_result": False,
        "publication_ready": False,
        "reason": (
            "Bounded discovery-only model screen over one synthetic task panel; "
            "the result is not an upstream MemoryBank reproduction or publication claim."
        ),
        "experiment_sha256": _sha256_file(experiment_path),
        "matched_identity": reference_identity,
        "assignment_seeds": list(seeds),
        "assignment_schedule_sha256s": {
            str(seed): schedules[seed] for seed in seeds
        },
        "trial_plan_sha256s": {str(seed): plans[seed] for seed in seeds},
        "arms": arm_receipts,
        "contrasts": contrasts,
        "gates": {
            "minimum_corrected_minus_upstream_points": effect_gate,
            "paired_task_clustered_ci_excludes_zero": interval_gate,
            "zero_safety_failures": validity_gate,
        },
        "registered_threshold_points": threshold,
        "inference": {
            "unit": "generated task group",
            "task_groups": config["input"]["task_count"],
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "assignment_seed_treatment": "within-task repeated design",
        },
    }
    return {**unsigned, "aggregate_sha256": sha256_text(canonical_json(unsigned))}


def _write_once(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--corrected-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--no-decay-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    report = aggregate_memorybank_h100_screen(
        experiment_path=args.experiment,
        arm_roots={
            "corrected": args.corrected_root,
            "upstream_precedence": args.upstream_root,
            "no_decay": args.no_decay_root,
        },
    )
    _write_once(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_gates and report["status"] != "MEMORYBANK_CORRECTED_DECAY_ACTOR_PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
