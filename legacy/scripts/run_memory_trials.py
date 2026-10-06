#!/usr/bin/env python3
"""Run the deterministic executable memory-to-action study contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.causal_memory_trials import (  # noqa: E402
    AnalysisReport,
    TrialPlan,
    analyze_trials,
    verify_analysis,
)
from harness.memory_trials import (  # noqa: E402
    GeneratedMemoryTaskSource,
    MemoryBudget,
    ReplayableMemoryWorld,
    collect_resumable,
)

DEFAULT_CONFIG = PROJECT_ROOT / "experiments" / "memory" / "stage0-oracle.yaml"
ALLOWED_FEATURES = (
    "contradiction_count",
    "graph_degree",
    "proactive_hint",
    "record_cost",
    "source_quality",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_ids(
    trial_ids: tuple[str, ...],
    *,
    assignment_seed: int,
    fraction: float,
) -> frozenset[str]:
    selected = frozenset(
        trial_id
        for trial_id in trial_ids
        if int(
            hashlib.sha256(
                f"memory-engine-audit-v1:{assignment_seed}:{trial_id}".encode()
            ).hexdigest()[:16],
            16,
        )
        / float(1 << 64)
        < fraction
    )
    if not selected:
        raise ValueError("audit schedule selected no trials")
    return selected


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("xb", buffering=0) as handle:
        handle.write(encoded)
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def load_or_analyze(bundle) -> AnalysisReport:
    analysis_dir = bundle.root / "analysis"
    if not analysis_dir.exists():
        return analyze_trials(bundle)
    manifest_path = analysis_dir / "manifest.json"
    report_path = analysis_dir / "report.json"
    if not manifest_path.is_file() or not report_path.is_file():
        raise ValueError("compiled bundle has a partial analysis directory")
    artifact_sha256 = sha256_file(manifest_path)
    verify_analysis(bundle, artifact_sha256)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return AnalysisReport(**payload, artifact_sha256=artifact_sha256)


def run_study(
    config_path: Path,
    output_dir: Path,
    *,
    episodes_override: int | None = None,
    propensity_override: float | None = None,
    world_seed: int = 7,
    assignment_seed: int = 42,
    resume: bool = False,
    stop_after: int | None = None,
    stop_requested=None,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or config.get("stage") != "oracle":
        raise ValueError("run_memory_trials currently accepts only a stage: oracle contract")
    registered_episodes = int(config["source"]["episodes_per_propensity"])
    episodes = episodes_override if episodes_override is not None else registered_episodes
    if episodes < 80:
        raise ValueError("executable memory study requires at least 80 episodes")
    smoke = episodes != registered_episodes or propensity_override is not None
    registered_propensities = [
        float(value) for value in config["causal_design"]["serve_propensities"]
    ]
    propensities = (
        [float(propensity_override)]
        if propensity_override is not None
        else registered_propensities
    )
    if any(not math.isfinite(value) or not 0.0 < value < 1.0 for value in propensities):
        raise ValueError("propensities must be finite and in (0, 1)")
    if output_dir.exists() and any(output_dir.iterdir()) and not resume:
        raise ValueError(f"refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    budget_config = config["memory_budget"]
    budget = MemoryBudget(
        active_slots=int(budget_config["primary_active_slots"]),
        max_archive_reads=int(budget_config["max_archive_reads_per_opportunity"]),
        retrieval_top_k=int(budget_config["max_retrieval_top_k"]),
        max_injected_tokens=int(budget_config["max_injected_tokens"]),
    )
    source = GeneratedMemoryTaskSource(
        seed=world_seed,
        episode_count=episodes,
        budget=budget,
    )
    world = ReplayableMemoryWorld(source)
    cells: list[dict[str, Any]] = []
    for propensity in propensities:
        propensity_label = f"p{round(propensity * 100):03d}"
        cell_dir = output_dir / propensity_label
        if smoke:
            minimum_ess = max(20.0, episodes * 0.25)
            minimum_arm_ess = max(10.0, episodes * 0.08)
        else:
            minimum_ess = float(config["gates"]["minimum_total_effective_sample_size"])
            minimum_arm_ess = float(config["gates"]["minimum_arm_effective_sample_size"])
        trial_ids = source.ids()
        plan = TrialPlan(
            study_id=f"memory-stage0-oracle-{propensity_label}",
            trial_ids=trial_ids,
            allowed_features=ALLOWED_FEATURES,
            paired_audit_ids=audit_ids(
                trial_ids,
                assignment_seed=assignment_seed,
                fraction=float(config["causal_design"]["paired_replay_fraction"]),
            ),
            propensity=propensity,
            assignment_seed=assignment_seed,
            folds=int(config["causal_design"]["folds"]),
            minimum_effective_sample_size=minimum_ess,
            minimum_arm_effective_sample_size=minimum_arm_ess,
            maximum_aipw_oracle_ate_gap=float(
                config["gates"]["maximum_aipw_oracle_ate_gap"]
            ),
            minimum_aipw_oracle_correlation=float(
                config["gates"]["minimum_aipw_oracle_spearman"]
            ),
            minimum_audit_correlation=float(
                config["gates"]["minimum_policy_oracle_spearman"]
            ),
        )
        collection = collect_resumable(
            plan,
            world,
            cell_dir,
            resume=resume and cell_dir.exists(),
            stop_after=stop_after,
            stop_requested=stop_requested,
        )
        if collection.status == "CHECKPOINTED":
            cells.append(
                {
                    "propensity": propensity,
                    "episodes": episodes,
                    "status": "CHECKPOINTED",
                    "completed_trials": collection.completed_trials,
                    "checkpoint_sha256": collection.checkpoint_sha256,
                }
            )
            manifest = {
                "schema_version": 1,
                "status": "CHECKPOINTED",
                "scientific_result": False,
                "reason": "Episode-boundary checkpoint requested before collection completed.",
                "config": str(config_path.resolve()),
                "config_sha256": sha256_file(config_path),
                "episodes_per_cell": episodes,
                "world_seed": world_seed,
                "assignment_seed": assignment_seed,
                "cells": cells,
            }
            atomic_json(output_dir / "manifest.json", manifest)
            return manifest
        if collection.bundle is None:
            raise RuntimeError("complete collection did not produce a bundle")
        bundle = collection.bundle
        report = load_or_analyze(bundle)
        cells.append(
            {
                "propensity": propensity,
                "episodes": episodes,
                "paired_audits": report.paired_audits,
                "raw_manifest_sha256": bundle.manifest_sha256,
                "analysis_manifest_sha256": report.artifact_sha256,
                "checkpoint_sha256": collection.checkpoint_sha256,
                "effective_sample_size": report.effective_sample_size,
                "treated_effective_sample_size": report.treated_effective_sample_size,
                "control_effective_sample_size": report.control_effective_sample_size,
                "aipw_oracle_absolute_gap": report.aipw_oracle_absolute_gap,
                "aipw_oracle_correlation": report.aipw_oracle_correlation,
                "policy_oracle_correlation": report.policy_oracle_correlation,
                "learned_policy_success": report.learned_policy_success,
                "always_serve_success": report.always_serve_success,
                "always_holdout_success": report.always_holdout_success,
                "gates": report.gates,
            }
        )
    all_gates = all(all(cell["gates"].values()) for cell in cells)
    status = (
        "ORACLE_ENGINE_SMOKE"
        if smoke and all_gates
        else "ORACLE_ENGINE_CONTRACT_PASS"
        if all_gates
        else "FAIL"
    )
    manifest = {
        "schema_version": 1,
        "status": status,
        "scientific_result": False,
        "reason": (
            "Deterministic environment and estimator contract only; "
            "no language model or public benchmark."
        ),
        "config": str(config_path.resolve()),
        "config_sha256": sha256_file(config_path),
        "episodes_per_cell": episodes,
        "world_seed": world_seed,
        "assignment_seed": assignment_seed,
        "cells": cells,
    }
    atomic_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int)
    parser.add_argument("--propensity", type=float)
    parser.add_argument("--world-seed", type=int, default=7)
    assignment_group = parser.add_mutually_exclusive_group()
    assignment_group.add_argument("--assignment-seed", type=int)
    assignment_group.add_argument("--assignment-seeds", type=int, nargs="+")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    stop = False

    def request_stop(_signum, _frame) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGUSR1, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    assignment_seeds = (
        tuple(args.assignment_seeds)
        if args.assignment_seeds is not None
        else (args.assignment_seed,)
        if args.assignment_seed is not None
        else tuple(config["execution"]["seeds"])
    )
    if len(set(assignment_seeds)) != len(assignment_seeds):
        raise ValueError("assignment seeds must be distinct")
    if len(assignment_seeds) == 1:
        manifest = run_study(
            args.config,
            args.output_dir,
            episodes_override=args.episodes,
            propensity_override=args.propensity,
            world_seed=args.world_seed,
            assignment_seed=assignment_seeds[0],
            resume=args.resume,
            stop_after=args.stop_after,
            stop_requested=lambda: stop,
        )
    else:
        seed_manifests: list[dict[str, Any]] = []
        for assignment_seed in assignment_seeds:
            seed_dir = args.output_dir / f"seed-{assignment_seed}"
            seed_manifest = run_study(
                args.config,
                seed_dir,
                episodes_override=args.episodes,
                propensity_override=args.propensity,
                world_seed=args.world_seed,
                assignment_seed=assignment_seed,
                resume=args.resume and seed_dir.exists(),
                stop_after=args.stop_after,
                stop_requested=lambda: stop,
            )
            seed_manifests.append(
                {"assignment_seed": assignment_seed, "manifest": seed_manifest}
            )
            if seed_manifest["status"] == "CHECKPOINTED":
                break
        complete = len(seed_manifests) == len(assignment_seeds)
        failed = any(
            item["manifest"]["status"] == "FAIL" for item in seed_manifests
        )
        manifest = {
            "schema_version": 1,
            "status": (
                "ORACLE_SEED_MATRIX_PASS"
                if complete and not failed
                else "CHECKPOINTED"
                if not complete
                else "FAIL"
            ),
            "scientific_result": False,
            "reason": (
                "Assignment-seed sensitivity matrix over one frozen task set; "
                "seeds are not independent task samples."
            ),
            "assignment_seeds": list(assignment_seeds),
            "seed_manifests": seed_manifests,
        }
        atomic_json(args.output_dir / "seed-matrix-manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if args.require_gates and manifest["status"] in {"FAIL", "CHECKPOINTED"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
