#!/usr/bin/env python3
"""Verify and aggregate a fully matched frozen-memory control screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.causal_memory_trials import TrialBundle  # noqa: E402
from harness.memory_trials import FrozenMemorySystem  # noqa: E402
from harness.memory_trials.schema import canonical_json, sha256_text  # noqa: E402
from scripts.run_memory_model_screen import summarize_screen  # noqa: E402

DEFAULT_SEEDS = (42, 43, 44)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_bundle(bundle_root: Path, claimed_manifest_sha256: str) -> TrialBundle:
    manifest_path = bundle_root / "manifest.json"
    if _sha256_file(manifest_path) != claimed_manifest_sha256:
        raise ValueError(f"compiled bundle manifest digest differs: {bundle_root}")
    manifest = _read_json(manifest_path)
    if manifest.get("status") != "COMPLETE":
        raise ValueError(f"compiled bundle is not complete: {bundle_root}")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError(f"compiled bundle lacks a file manifest: {bundle_root}")
    for name, expected in files.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError("compiled bundle file manifest is malformed")
        path = bundle_root / name
        if not path.is_file() or _sha256_file(path) != expected:
            raise ValueError(f"compiled bundle artifact differs: {path}")
    return TrialBundle(root=bundle_root, manifest_sha256=claimed_manifest_sha256)


def _validate_seed_report(
    report: dict[str, Any],
    *,
    seed: int,
    seed_dir: Path,
    control: dict[str, Any],
    task_manifest_sha256: str,
) -> dict[str, Any]:
    if report.get("status") != "MODEL_MATRIX_CELL_VALID":
        raise ValueError(
            f"{control['control_id']} seed {seed}: validity gates did not pass"
        )
    if report.get("scientific_result") is not False:
        raise ValueError("screen cells must not claim a scientific result")
    if report.get("evaluation_mode") != "matrix-cell":
        raise ValueError("screen cell did not use matrix-cell evaluation mode")
    if report.get("assignment_seed") != seed:
        raise ValueError("screen report assignment seed differs from its directory")
    actor_contract = report.get("actor_contract")
    if not isinstance(actor_contract, dict) or report.get(
        "actor_contract_sha256"
    ) != sha256_text(canonical_json(actor_contract)):
        raise ValueError("actor contract digest is missing or invalid")
    if report.get("task_manifest_sha256") != task_manifest_sha256:
        raise ValueError("screen cell task manifest differs from frozen control matrix")
    if report.get("memory_bundle_sha256") != control["bundle_sha256"]:
        raise ValueError("screen cell used a different frozen memory bundle")
    memory_system = report.get("memory_system")
    if not isinstance(memory_system, dict) or memory_system.get("system_id") != control[
        "system_id"
    ]:
        raise ValueError("screen cell memory-system receipt differs from matrix")
    validity_gates = report.get("validity_gates")
    if not isinstance(validity_gates, dict) or not validity_gates or not all(
        value is True for value in validity_gates.values()
    ):
        raise ValueError("screen cell has a failed or malformed validity gate")

    metrics = report.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("screen cell lacks metrics")
    schedule = metrics.get("assignment_schedule")
    task_results = metrics.get("task_results")
    if not isinstance(schedule, list) or metrics.get(
        "assignment_schedule_sha256"
    ) != sha256_text(canonical_json(schedule)):
        raise ValueError("assignment schedule receipt is invalid")
    if not isinstance(task_results, list) or metrics.get(
        "task_results_sha256"
    ) != sha256_text(canonical_json(task_results)):
        raise ValueError("task-result receipt is invalid")
    if metrics.get("assignment_seed") != seed:
        raise ValueError("metrics assignment seed differs from the cell")

    bundle = _verify_bundle(
        seed_dir / "bundle",
        str(report.get("bundle_manifest_sha256")),
    )
    recomputed_metrics = summarize_screen(bundle)
    if recomputed_metrics != metrics:
        raise ValueError("screen metrics differ from the sealed raw bundle")
    if metrics["assignment_journal_sha256"] != _sha256_file(
        bundle.root / "assignment_journal.jsonl"
    ):
        raise ValueError("assignment journal digest differs from the raw bundle")
    return {
        "assignment_seed": seed,
        "assignment_schedule_sha256": metrics["assignment_schedule_sha256"],
        "trial_plan_sha256": metrics["trial_plan_sha256"],
        "task_results_sha256": metrics["task_results_sha256"],
        "episodes": metrics["episodes"],
        "served_episodes": metrics["served_episodes"],
        "served_oracle_success": metrics["served_oracle_success"],
        "valid_action_rate": metrics["valid_action_rate"],
        "safety_failures": metrics["safety_failures"],
        "performance_gates": report.get("performance_gates", {}),
        "report_sha256": _sha256_file(seed_dir / "screen-report.json"),
        "bundle_manifest_sha256": report["bundle_manifest_sha256"],
        "actor_contract_sha256": report["actor_contract_sha256"],
        "model_id": report["model_id"],
        "revision": report["revision"],
        "artifact_root_sha256": report["artifact_root_sha256"],
        "memory_treatment_mode": report["memory_treatment_mode"],
    }


def aggregate_control_matrix(
    matrix_dir: Path,
    results_root: Path,
    *,
    expected_seeds: tuple[int, ...] = DEFAULT_SEEDS,
) -> dict[str, Any]:
    """Fail closed unless every frozen control is a genuinely matched cell."""

    matrix_dir = matrix_dir.resolve()
    results_root = results_root.resolve()
    manifest = _read_json(matrix_dir / "manifest.json")
    claimed_matrix_sha256 = manifest.get("matrix_sha256")
    unsigned = {key: value for key, value in manifest.items() if key != "matrix_sha256"}
    if claimed_matrix_sha256 != sha256_text(canonical_json(unsigned)):
        raise ValueError("frozen control-matrix digest is invalid")
    controls = manifest.get("controls")
    if not isinstance(controls, list) or not controls:
        raise ValueError("frozen control matrix has no controls")
    control_ids = [item.get("control_id") for item in controls if isinstance(item, dict)]
    if len(control_ids) != len(controls) or len(set(control_ids)) != len(control_ids):
        raise ValueError("frozen control matrix has invalid control IDs")
    if not expected_seeds or len(set(expected_seeds)) != len(expected_seeds):
        raise ValueError("expected assignment seeds must be non-empty and distinct")
    task_source = manifest.get("task_source")
    if not isinstance(task_source, dict):
        raise ValueError("frozen control matrix lacks task-source provenance")
    task_manifest_sha256 = task_source.get("task_manifest_sha256")
    if not isinstance(task_manifest_sha256, str):
        raise ValueError("frozen control matrix lacks an exact task manifest")

    cells: list[dict[str, Any]] = []
    match_reference: dict[str, Any] | None = None
    schedules_by_seed: dict[int, str] = {}
    plans_by_seed: dict[int, str] = {}
    for control in controls:
        control_id = str(control["control_id"])
        frozen = FrozenMemorySystem(matrix_dir / str(control["bundle_path"]))
        if frozen.bundle_sha256 != control.get("bundle_sha256"):
            raise ValueError(f"{control_id}: frozen bundle digest differs from matrix")
        if frozen.receipt.system_id != control.get("system_id"):
            raise ValueError(f"{control_id}: frozen system receipt differs from matrix")

        cell_dir = results_root / control_id
        wrapper_path = cell_dir / "screen-matrix-report.json"
        wrapper = _read_json(wrapper_path)
        if wrapper.get("status") != "MODEL_CONTROL_MATRIX_CELL_PASS":
            raise ValueError(f"{control_id}: seed matrix did not pass validity gates")
        if wrapper.get("evaluation_mode") != "matrix-cell":
            raise ValueError(f"{control_id}: wrapper evaluation mode differs")
        if tuple(wrapper.get("assignment_seeds", ())) != expected_seeds:
            raise ValueError(f"{control_id}: assignment seed matrix differs")
        embedded = wrapper.get("seed_reports")
        if not isinstance(embedded, list) or len(embedded) != len(expected_seeds):
            raise ValueError(f"{control_id}: wrapper does not contain every seed")
        embedded_by_seed = {
            item.get("assignment_seed"): item.get("report")
            for item in embedded
            if isinstance(item, dict)
        }
        if set(embedded_by_seed) != set(expected_seeds):
            raise ValueError(f"{control_id}: wrapper seed reports are malformed")

        seed_cells: list[dict[str, Any]] = []
        for seed in expected_seeds:
            seed_dir = cell_dir / f"seed-{seed}"
            report = _read_json(seed_dir / "screen-report.json")
            if report != embedded_by_seed[seed]:
                raise ValueError(f"{control_id} seed {seed}: wrapper report differs")
            seed_cell = _validate_seed_report(
                report,
                seed=seed,
                seed_dir=seed_dir,
                control=control,
                task_manifest_sha256=task_manifest_sha256,
            )
            identity = {
                key: seed_cell[key]
                for key in (
                    "model_id",
                    "revision",
                    "artifact_root_sha256",
                    "actor_contract_sha256",
                    "memory_treatment_mode",
                    "episodes",
                )
            }
            if match_reference is None:
                match_reference = identity
            elif identity != match_reference:
                raise ValueError("control cells differ in actor, model, treatment, or tasks")
            prior_schedule = schedules_by_seed.setdefault(
                seed, seed_cell["assignment_schedule_sha256"]
            )
            if prior_schedule != seed_cell["assignment_schedule_sha256"]:
                raise ValueError(f"seed {seed}: assignment schedules differ across controls")
            prior_plan = plans_by_seed.setdefault(seed, seed_cell["trial_plan_sha256"])
            if prior_plan != seed_cell["trial_plan_sha256"]:
                raise ValueError(f"seed {seed}: trial plans differ across controls")
            seed_cells.append(seed_cell)
        cells.append(
            {
                "control_id": control_id,
                "system_id": control["system_id"],
                "eligible_for_primary": control["eligible_for_primary"],
                "ineligibility_reason": control.get("ineligibility_reason"),
                "bundle_sha256": control["bundle_sha256"],
                "wrapper_report_sha256": _sha256_file(wrapper_path),
                "seeds": seed_cells,
                "mean_seed_served_oracle_success": sum(
                    float(cell["served_oracle_success"]) for cell in seed_cells
                )
                / len(seed_cells),
            }
        )

    payload = {
        "schema_version": 1,
        "status": "MATCHED_CONTROL_MATRIX_SCREEN_READY",
        "scientific_result": False,
        "reason": (
            "All frozen control cells are receipt-matched across model, task, budget, "
            "treatment, assignment schedule, and seeds. This 32-task screen is not a "
            "memory-policy effect estimate or model-selection result."
        ),
        "matrix_sha256": claimed_matrix_sha256,
        "task_manifest_sha256": task_manifest_sha256,
        "assignment_seeds": list(expected_seeds),
        "assignment_schedule_sha256s": {
            str(seed): schedules_by_seed[seed] for seed in expected_seeds
        },
        "matched_identity": match_reference,
        "strongest_control_selected": False,
        "cells": cells,
    }
    return {**payload, "aggregate_sha256": sha256_text(canonical_json(payload))}


def _write_once(path: Path, payload: dict[str, Any]) -> None:
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
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assignment-seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    args = parser.parse_args()
    report = aggregate_control_matrix(
        args.matrix_dir,
        args.results_root,
        expected_seeds=tuple(args.assignment_seeds),
    )
    _write_once(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
