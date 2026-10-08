#!/usr/bin/env python3
"""Write the Q1 Stage 0 pilot cost card (CPU; ``harness/q1/cost_card.py``).

    python scripts/q1_pilot_cost_card.py \\
        --smoke-job RUNS/474 --pilot-job RUNS/NNN --corpus PREP/corpus \\
        --counts stage0-counts.json --out OUT

``--smoke-job`` and ``--pilot-job`` are lane run directories (each holds the
driver's ``q1/`` tree and the lane's ``job.env``/``termination.env``).
Outputs ``cost_card.json`` and ``cost_card.md``: per-gate GPU-seconds (median,
p95) of the scored items, per-kernel cost by rung, the c/b ratio, the measured
fixed phases, items a time box killed (lower bounds), and the projected Stage 0
total against the 8 GPU-h cap with a cluster-bootstrap interval, under the
drafted design and a grid of simple trims, and under the trimming rule
``q1-stage0-trim/2`` (``harness.q1.trim``; ``q1-stage0-trim/1``, the pilot pass's
proposal, is recomputed beside it) at the measured cost and, when ``--pair-job``
names a paired re-run of the same items at another concurrency, at that job's
measured per-gate cost ratio.

Since the second review: the c/b statistic comes from the analysis code
(``analysis.c_over_b_statistic``: the pinned ratio of medians with a cluster
bootstrap interval, and the other readings reported beside it); items of 1 GB or
more are anchored to the measured and censored pilot costs
(``cost_card.large_problem_anchors``); the fidelity sample is charged at the
measured allocation per kernel of the pilot's fidelity phase; the timing noise
floor is charged at the allocation of its registered protocol (an 8-GPU job
timing on 2 GPUs); the timing bias of the identity control is reported under
both TF32 policies; the pilot-exposed mutants (``harness/q1/data/pilot_exposed.json``)
leave the frames; and ``--records`` binds the run records by hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import analysis, trim  # noqa: E402
from harness.q1 import cost_card as cc  # noqa: E402

FIDELITY_GATES = (
    "a_upstream_44130946",
    "a_upstream_423217d9",
    "b_native",
    "c1_kbv_compat",
    "c1_kbv_native",
)


def _env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (line.partition("=") for line in path.read_text().splitlines())
    return {key: value for key, sep, value in pairs if sep}


def _phase(job: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((p for p in job["phases"]["phases"] if p["phase"] == name), None)


def survival_from(corpus: Path) -> dict[str, Any]:
    manifest = json.loads((corpus / "mutants" / "manifest.json").read_text())
    distinct = sum(s["cpu_distinct"] for s in manifest["substrates"])
    eligible = sum(s["eligible"] for s in manifest["substrates"])
    return {
        "cpu_distinct": distinct,
        "compile_distinct": eligible,
        "survival": eligible / distinct if distinct else 1.0,
        "selected": manifest["totals"]["selected"],
        "compile_checked": manifest["compile_checked"],
    }


def fixed_phases(
    smoke: dict[str, Any], pilot: dict[str, Any], counts: dict[str, Any], kinds: dict[str, Any]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    root = Path(smoke["dir"])
    admission = _phase(smoke, "admission") or {}
    codegen = (
        [
            json.loads(line)
            for line in (root / "records-cuda" / "codegen_log.jsonl").read_text().splitlines()
            if line.strip()
        ]
        if (root / "records-cuda" / "codegen_log.jsonl").exists()
        else []
    )
    hook_rows = (
        [
            json.loads(line)
            for line in (root / "substrates-built" / "admission_hook.jsonl")
            .read_text()
            .splitlines()
            if line.strip()
        ]
        if (root / "substrates-built" / "admission_hook.jsonl").exists()
        else []
    )
    problems = len([r for r in codegen if r.get("status") not in {"excluded", "exists"}]) or 1
    hooked = len({r["kernel_id"] for r in hook_rows}) or 1
    hook_seconds = sum(r["wall_seconds"] for r in hook_rows) / 2  # two rows per substrate
    all_problems = 196
    built = (
        sum(counts["totals"]["evaluation_substrates"].values())
        + counts["totals"]["calibration_substrates"]
    )
    other = max(0.0, admission.get("seconds", 0.0) - hook_seconds)
    out["admission"] = {
        "measured_seconds": admission.get("seconds"),
        "codegen_problems": problems,
        "gpu_admitted_substrates": hooked,
        "codegen_and_build_seconds_per_problem": round(other / problems, 2),
        "gpu_admission_seconds_per_substrate": round(hook_seconds / hooked, 2),
        "projected_seconds": round(
            other / problems * all_problems + hook_seconds / hooked * built, 1
        ),
    }
    spec = _phase(smoke, "specializations") or {}
    n_spec = len(list((root / "specializations").glob("*/specializations.json"))) or 1
    eval_subs = sum(counts["totals"]["evaluation_substrates"].values())
    out["specializations"] = {
        "measured_seconds": spec.get("seconds"),
        "substrates": n_spec,
        "projected_seconds": round((spec.get("seconds") or 0.0) / n_spec * eval_subs, 1),
    }
    smoke_phase = sum(p.get("seconds", 0.0) for p in smoke["phases"]["phases"])
    out["smoke_job_driver_seconds"] = round(smoke_phase, 1)
    calibration_items = [i for i in pilot["items"] if i["phase"] == "calibration" and i["final"]]
    a1 = [i["gpu_seconds"] for i in calibration_items if i["gpu_seconds"] is not None]
    out["calibration"] = {
        "measured_items": len(a1),
        "a1_gpu_seconds": cc.summarize(a1),
        "projected_seconds": round(
            (statistics.fmean(a1) if a1 else 0.0) * counts["totals"]["calibration_substrates"], 1
        ),
    }
    fidelity_items = [i for i in pilot["items"] if i["phase"] == "fidelity" and i["final"]]
    per_kernel: dict[str, float] = {}
    for item in fidelity_items:
        if item["gate"] in FIDELITY_GATES and item["gpu_seconds"] is not None:
            per_kernel[item["kernel_id"]] = (
                per_kernel.get(item["kernel_id"], 0.0) + item["gpu_seconds"]
            )
    fidelity_phase = _phase(pilot, "fidelity") or {}
    out["fidelity"] = {
        "kernels": len(per_kernel),
        "per_gate": cc.gate_stats(fidelity_items),
        "per_kernel_gpu_seconds": cc.summarize(list(per_kernel.values())),
        # The phase held the GPU for its whole wall time (4 items per GPU, our gates on
        # the adversarial controls and mutants included): the charge per kernel.
        "phase_seconds": fidelity_phase.get("seconds"),
        "allocation_seconds_per_kernel": round(fidelity_phase["seconds"] / len(per_kernel), 2)
        if fidelity_phase.get("seconds") and per_kernel
        else None,
    }
    return out


def trimmed_fixed_hours(
    counts: dict[str, Any],
    fits: dict[str, Any],
    fixed: dict[str, Any],
    projection: dict[str, Any],
    args: argparse.Namespace,
    *,
    factors: dict[str, float] | None,
    rule: dict[str, Any],
    timing_item_seconds: float | None = None,
    measured_charges: bool = True,
) -> dict[str, float]:
    """Fixed phases under the trimming rule (GPU-h): admission of every problem
    (corpus metrics), specializations of in-scope parents, calibration on the
    S1-cal substrates within the FRR set's largest input size, a registered
    fidelity sample (every in-scope evaluation substrate, the three adversarial
    controls and one test mutant per family and source tier), the timing noise
    floor and the audit-hole replay cap (the draft's cap, not measured).

    ``measured_charges`` (the second review's corrections, 6(b) and 6(d)): the
    fidelity sample at the measured allocation per kernel of the pilot's fidelity
    phase, and the timing floor at the allocation of its registered protocol
    (``timing_floor_job_gpus`` GPUs held while ``timing_floor_timing_gpus`` time).
    Without it, the pilot pass's charges (size model; one GPU per timing item)."""
    from harness.q1 import pilot

    def seconds(problem_id: str, gates: dict[str, float]) -> float:
        return sum(
            weight * cc.kernel_replicate_seconds(fits, problem_id, factors=factors, gates=(gate,))
            for gate, weight in gates.items()
        )

    scope = int(rule["scope_bytes"])
    rows = counts["evaluation_substrates"]
    in_scope = [r for r in rows if int(r.get("native_input_bytes") or 0) < scope]
    largest = max(
        [
            int(r.get("native_input_bytes") or 0)
            for r in rows
            if r["substrate_id"] in set(projection["frr_extra_substrates"])
        ]
        or [scope - 1]
    )
    spec = fixed["specializations"]
    per_spec = (spec["measured_seconds"] or 0.0) / max(1, spec["substrates"])
    calibration = [
        sid.removeprefix("s1-inductor-").replace("-", "/", 1)
        for sid in counts["calibration_substrates"]
    ]
    calibration = [p for p in calibration if (pilot.native_input_bytes(p) or 0) <= largest]
    n_fidelity = len(in_scope) + 3 + 12 * int(rule["fidelity_mutants_per_family_tier"])
    per_kernel = fixed["fidelity"].get("allocation_seconds_per_kernel")
    if measured_charges and per_kernel:
        fidelity = n_fidelity * per_kernel
    else:
        fidelity_gates = {"a": 2.0, "a_head_1e-4": 1.0, "b1": 1.0, "b2": 1.0, "c": 0.4}
        fidelity = sum(seconds(r["problem_id"], fidelity_gates) for r in in_scope)
        fidelity += 3 * seconds("L1/1_Square_matrix_multiplication_", fidelity_gates)
        mean_substrate = fidelity / max(1, len(in_scope))
        fidelity += 12 * int(rule["fidelity_mutants_per_family_tier"]) * mean_substrate
    return {
        "already_spent_this_pass": args.spent_gpu_hours,
        "admission_full": fixed["admission"]["projected_seconds"] / 3600,
        "specializations_in_scope": per_spec * len(in_scope) / 3600,
        "calibration_within_frr_bound": sum(seconds(p, {"A1": 1.0}) for p in calibration) / 3600,
        "fidelity_sample": fidelity / 3600,
        "timing_noise_floor": timing_floor_hours(
            rule, timing_item_seconds, args, allocation=measured_charges
        ),
        "audit_hole_replay_cap": args.replay_gpu_hours,
    }


def bootstrap_trimmed(
    items: list[dict[str, Any]],
    kinds: dict[str, Any],
    counts: dict[str, Any],
    survival: float,
    rule: dict[str, Any],
    factors: dict[str, float] | None,
    args: argparse.Namespace,
    seed: int = 0,
    store_inputs: tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Cluster bootstrap of the trimmed scoring projection over pilot parents
    (each with its mutants and controls), refitting the size model each time (the
    large-problem anchors stay fixed: they are lower bounds from one measured and
    one censored item).

    With ``store_inputs`` (the re-pilot's pairs and reference items, decision D31)
    each resample also draws the re-pilot's problems with replacement and refits
    the store model, independently of the pilot draw. ``cumulative`` holds the
    2.5% and 97.5% points of the scoring GPU-h through each bucket."""
    import random
    from collections import defaultdict

    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        parent = kinds.get(item["kernel_id"], {}).get("parent", item["kernel_id"])
        clusters[parent].append(item)
    keys = sorted(clusters)
    if len(keys) < 2:
        return {"low": None, "high": None}
    rng = random.Random(seed)
    store_rng = random.Random(seed + 1)
    problems: list[str] = []
    if store_inputs is not None:
        problems = sorted({p["problem_id"] for p in store_inputs[0]})
    totals = []
    cumulative: dict[str, list[float]] = defaultdict(list)
    for _ in range(args.resamples):
        sample = [i for _ in keys for i in clusters[rng.choice(keys)]]
        fits = cc.fit_item_costs(sample)
        options = dict(extra)
        if store_inputs is not None:
            drawn = [store_rng.choice(problems) for _ in problems]
            pairs = [p for name in drawn for p in store_inputs[0] if p["problem_id"] == name]
            refs = [r for name in drawn for r in store_inputs[1] if r["problem_id"] == name]
            options["store"] = cc.fit_store_model(pairs, refs, **store_inputs[2])
        projection = cc.project_trimmed(
            counts, fits, survival=survival, rule=rule, factors=factors, **options
        )
        totals.append(projection["gpu_hours"])
        running = 0.0
        for bucket, hours in sorted(projection["gpu_hours_by_priority"].items()):
            running += hours
            cumulative[bucket].append(running)
    totals.sort()

    def point(values: list[float], q: float) -> float:
        ordered = sorted(values)
        return round(ordered[int(round(q * (len(ordered) - 1)))], 3)

    return {
        "low": round(totals[int(0.025 * (len(totals) - 1))], 3),
        "high": round(totals[int(round(0.975 * (len(totals) - 1)))], 3),
        "cumulative": {
            bucket: {"low": point(values, 0.025), "high": point(values, 0.975)}
            for bucket, values in sorted(cumulative.items())
        },
    }


def stop_point(
    projection: dict[str, Any], fixed_total: float, scale: float | None
) -> dict[str, Any]:
    """Where the 8 GPU-h total falls (central and high projection): the last priority
    bucket that completes, the share of the next one that runs, and the test-split
    mutants scored (the test quota plus the extension that fits)."""
    buckets = projection["gpu_hours_by_priority"]
    test_quota = sum(v["test"] for v in projection["mutants_per_family"].values())
    extension = sum(v["test_extension_max"] for v in projection["mutants_per_family"].values())
    quota_bucket, extension_bucket = "P2", max(buckets) if buckets else "P8"
    out: dict[str, Any] = {}
    for label, factor in (("central", 1.0), ("high", scale)):
        if factor is None:
            out[label] = None
            continue
        room = cc.CAP_GPU_HOURS - fixed_total
        completed, partial = [], None
        for name, hours in buckets.items():
            hours *= factor
            if hours <= room:
                room -= hours
                completed.append(name)
                continue
            partial = {"bucket": name, "share": round(max(0.0, room) / hours, 3) if hours else 0.0}
            break
        scored_test = test_quota if quota_bucket in completed else None
        if scored_test is not None:
            if extension_bucket in completed:
                scored_test += extension
            elif partial and partial["bucket"] == extension_bucket:
                scored_test += round(extension * partial["share"])
        if partial and partial["bucket"] == quota_bucket:
            scored_test = round(test_quota * partial["share"])
        out[label] = {
            "completed": completed,
            "partial": partial,
            "test_mutants_scored": scored_test,
        }
    return out


def timing_floor_hours(
    rule: dict[str, Any],
    timing_item_seconds: float | None,
    args: argparse.Namespace,
    *,
    allocation: bool = True,
) -> float:
    """The noise floor at the measured seconds of one timing item. With
    ``allocation`` (the registered protocol: timing on GPUs 6-7 while GPUs 0-5
    are held idle and then loaded) the charge is the job's GPUs times its wall
    time; without it, one GPU per item (the pilot pass's charge)."""
    if timing_item_seconds is None:
        return args.timing_floor_gpu_hours
    items = int(rule["timing_floor_items"])
    if not allocation:
        return items * timing_item_seconds / 3600
    timing_gpus = int(rule.get("timing_floor_timing_gpus", 2))
    job_gpus = int(rule.get("timing_floor_job_gpus", 8))
    wall = math.ceil(items / timing_gpus) * timing_item_seconds
    return job_gpus * wall / 3600


def timing_bias(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Speedup of reference-identity controls timed against their own reference
    (a candidate equal to the reference): the systematic bias of the paired
    protocol under each TF32 policy (second review, 6(e))."""
    out = []
    for job in jobs:
        root = Path(job["dir"])
        for journal in sorted(root.glob("*timing*/journal.jsonl")):
            for line in journal.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if not row["kernel_id"].startswith("ctl-identity-"):
                    continue
                details = row["details"]
                out.append(
                    {
                        "job": root.parent.name,
                        "kernel_id": row["kernel_id"],
                        **{
                            policy: {
                                "median_speedup": round(details[policy]["median_speedup"], 4),
                                "ci95": [round(x, 4) for x in details[policy]["speedup_ci95"]],
                                "rounds_kept": details[policy]["rounds_kept"],
                            }
                            for policy in ("strict_fp32", "tf32")
                            if isinstance(details.get(policy), dict)
                        },
                    }
                )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--smoke-job", type=Path, required=True)
    parser.add_argument("--pilot-job", type=Path, required=True)
    parser.add_argument(
        "--pair-job",
        type=Path,
        help="a paired re-run of a prefix of the pilot job's scoring items (concurrency)",
    )
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--spent-gpu-hours",
        type=float,
        required=True,
        help="GPU-h of every Stage 0 job so far (this pass), from the lane",
    )
    parser.add_argument("--timing-floor-gpu-hours", type=float, default=0.5)
    parser.add_argument("--replay-gpu-hours", type=float, default=0.5)
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument(
        "--witness-rate",
        type=float,
        default=0.5,
        help="share of scored mutants the primary audit witnesses (planning value)",
    )
    parser.add_argument(
        "--exposed",
        type=Path,
        default=trim.PILOT_EXPOSED_PATH,
        help="pilot-exposed kernels (hash-checked); their mutants leave the frames",
    )
    parser.add_argument(
        "--records",
        type=Path,
        default=None,
        help="run-records JSON of the jobs (scripts/q1_pilot_records.py), bound by hash",
    )
    parser.add_argument(
        "--repilot-job",
        type=Path,
        default=None,
        help="the decision-D31 re-pilot (paired inline and reference-store arms)",
    )
    args = parser.parse_args(argv)
    smoke = cc.load_job(args.smoke_job / "q1")
    pilot = cc.load_job(args.pilot_job / "q1")
    counts = json.loads(args.counts.read_text())
    kinds = cc.classify(args.corpus)
    survival = survival_from(args.corpus)
    scoring_items = [i for i in pilot["items"] if i["phase"] == "scoring"]
    smoke_items = [i for i in smoke["items"] if i["phase"] == "smoke"]
    kernel_rows = cc.kernel_seed_costs(scoring_items, kinds)
    means = cc.class_means(kernel_rows)
    fixed = fixed_phases(smoke, pilot, counts, kinds)
    rung = {name: cc.summarize([row[name] for row in kernel_rows]) for name in cc.RUNGS}
    # The pinned c/b statistic (analysis.c_over_b_statistic; sections 5.5 and 12) with a
    # cluster bootstrap over pilot parents, and the other readings reported beside it.
    per_kernel_items: dict[tuple[str, int], dict[str, float]] = {}
    for item in scoring_items:
        if (
            item["final"]
            and item["gpu_seconds"] is not None
            and item["gate"] in {"a", "b1", "b2", "c"}
        ):
            per_kernel_items.setdefault((item["kernel_id"], item["seed"]), {})[item["gate"]] = item[
                "gpu_seconds"
            ]
    c_over_b_rows = [
        {**gates, "cluster": kinds.get(kernel, {}).get("parent", kernel)}
        for (kernel, _seed), gates in sorted(per_kernel_items.items())
        if {"a", "b1", "b2", "c"} <= set(gates)
        and any(r["kernel_id"] == kernel for r in kernel_rows)
    ]
    c_over_b = analysis.c_over_b_statistic(c_over_b_rows, resamples=args.resamples, seed=0)
    ratio = {
        "median_c_cumulative_over_b_cumulative": None
        if c_over_b["value"] is None
        else round(c_over_b["value"], 3),
        "median_c_marginal_over_b_marginal": None
        if c_over_b["other_readings_reported_only"]["marginal_ratio_of_medians"]["value"] is None
        else round(
            c_over_b["other_readings_reported_only"]["marginal_ratio_of_medians"]["value"], 3
        ),
        "c_lite_trigger_2x": c_over_b["c_lite_triggered"],
        "pinned_statistic": c_over_b,
    }
    # The size model uses the pilot job's scored items only: job 1's smoke items ran
    # the pre-fix reductions (host fp64 copies) and were cut by the fixed 180 s watchdog,
    # so they are reported (per_gate_smoke_identity) but not used for the projection.
    all_scored = [i for i in pilot["items"] if i["phase"] in {"scoring", "smoke"}]
    fits = cc.fit_item_costs(all_scored)

    def model(gate: str, problem_id: str) -> float:
        fit = fits.get(gate)
        return 0.0 if fit is None else fit["alpha"] + fit["beta"] * cc._gigabytes(problem_id)

    # Fidelity per kernel: the unmodified upstream runs do the work of our a (44130946),
    # a_head_1e-4 (423217d9), a + b1 + b2 (KernelGYM's b0, detection and profiling) and
    # c1 twice (KBV and ours in compatibility mode; c1 is about 4 of c's 20 draws).
    fidelity_weights = {"a": 2.0, "a_head_1e-4": 1.0, "b1": 1.0, "b2": 1.0, "c": 0.4}

    def fidelity_seconds(problem_id: str) -> float:
        return sum(w * model(g, problem_id) for g, w in fidelity_weights.items())

    fidelity_problems = (
        [r["problem_id"] for r in counts["evaluation_substrates"]] * 2
        + [r["problem_id"] for r in counts["identity_controls"]]
        + ["L1/1_Square_matrix_multiplication_"] * 3
    )
    fidelity_hours = sum(fidelity_seconds(p) for p in fidelity_problems) / 3600
    calibration_problems = [
        sid.removeprefix("s1-inductor-").replace("-", "/", 1)
        for sid in counts["calibration_substrates"]
    ]
    calibration_hours = sum(model("A1", p) for p in calibration_problems) / 3600
    fixed_hours = {
        "already_spent_this_pass": args.spent_gpu_hours,
        "admission_full": fixed["admission"]["projected_seconds"] / 3600,
        "specializations_full": fixed["specializations"]["projected_seconds"] / 3600,
        "fidelity_full": fidelity_hours,
        "calibration_full": calibration_hours,
        "timing_noise_floor_estimate": args.timing_floor_gpu_hours,
        "audit_hole_replay_cap": args.replay_gpu_hours,
    }
    fixed_total = sum(fixed_hours.values())
    rules = [
        {"name": "as-drafted", "scope": "all", "cap": 40},
        {"name": "all-cap40-m1", "scope": "all", "cap": 40, "mutant_seeds": 1},
        {"name": "all-cap8-m1-c1", "scope": "all", "cap": 8, "mutant_seeds": 1, "control_seeds": 1},
        {"name": "shared-cap40", "scope": "shared", "cap": 40},
        {"name": "shared-cap40-m1", "scope": "shared", "cap": 40, "mutant_seeds": 1},
        {"name": "shared-cap16-m1", "scope": "shared", "cap": 16, "mutant_seeds": 1},
        {"name": "shared-cap8-m1", "scope": "shared", "cap": 8, "mutant_seeds": 1},
        {
            "name": "shared-cap8-m1-c1",
            "scope": "shared",
            "cap": 8,
            "mutant_seeds": 1,
            "control_seeds": 1,
        },
        {
            "name": "shared-cap8-m1-c1-h25",
            "scope": "shared",
            "cap": 8,
            "mutant_seeds": 1,
            "control_seeds": 1,
            "hack_fraction": 0.25,
        },
        {
            "name": "shared-cap4-m1-c1-h25",
            "scope": "shared",
            "cap": 4,
            "mutant_seeds": 1,
            "control_seeds": 1,
            "hack_fraction": 0.25,
        },
        {
            "name": "shared-cap2-m1-c1-h25",
            "scope": "shared",
            "cap": 2,
            "mutant_seeds": 1,
            "control_seeds": 1,
            "hack_fraction": 0.25,
        },
    ]
    scenarios = []
    for rule in rules:
        options = {k: v for k, v in rule.items() if k not in {"name", "cap"}}
        projection = cc.project_scoring(
            counts, fits, cap=rule["cap"], survival=survival["survival"], **options
        )
        mutant_seeds = options.pop("mutant_seeds", None)
        interval = cc.bootstrap_projection(
            all_scored,
            kinds,
            counts,
            cap=rule["cap"],
            survival=survival["survival"],
            mutant_seeds=mutant_seeds,
            resamples=args.resamples,
            **options,
        )
        witnessed_test = {
            family: round(n * args.witness_rate * 0.5)
            for family, n in projection["mutants_per_family"].items()
        }
        pooled = sum(witnessed_test.values())
        total = round(fixed_total + projection["gpu_hours"], 3)
        high = None if interval["high"] is None else round(fixed_total + interval["high"], 3)
        scenarios.append(
            {
                "name": rule["name"],
                **projection,
                "scoring_gpu_hours_95": interval,
                "fixed_gpu_hours": round(fixed_total, 3),
                "total_gpu_hours": total,
                "total_gpu_hours_high": high,
                "fits_8_gpu_h": (high if high is not None else total) <= cc.CAP_GPU_HOURS,
                "witnessed_test_mutants": witnessed_test,
                "precision": {
                    family: {
                        "n": n,
                        "half_width_pp": None if not n else round(100 * cc.half_width(n), 1),
                    }
                    for family, n in witnessed_test.items()
                },
                "families_with_30_witnessed_test": sum(
                    1 for n in witnessed_test.values() if n >= 30
                ),
                "pooled_witnessed_test": pooled,
                "pooled_half_width_pp": None
                if not pooled
                else round(100 * cc.half_width(pooled, p=0.17), 1),
                "detectable_difference_pp": None
                if not pooled
                else round(100 * cc.detectable_difference(pooled), 1),
            }
        )
    censored = cc.censored_items(args.pilot_job / "q1") + cc.censored_items(args.smoke_job / "q1")
    paired = None
    factors = None
    if args.pair_job is not None:
        other = cc.load_job(args.pair_job / "q1")
        paired = cc.pair_jobs(pilot["items"], other["items"])
        censored += cc.censored_items(args.pair_job / "q1")
        factors = {
            gate: v["gpu_seconds_ratio_median"]
            for gate, v in paired["per_gate"].items()
            if v["gpu_seconds_ratio_median"] is not None
        }
        paired["factors"] = factors
        paired["timing_items"] = cc.gate_stats(
            [i for i in other["items"] if i["phase"] == "timing"]
        )
        paired["phases"] = other["phases"]
    timing_items = [
        i["gpu_seconds"]
        for job in ([other] if args.pair_job is not None else []) + [pilot]
        for i in job["items"]
        if i["phase"] in {"timing", "smoke-timing"} and i["final"] and i["gpu_seconds"]
    ]
    timing_seconds = statistics.median(timing_items) if timing_items else None
    timing_phase_seconds = None
    if args.pair_job is not None:
        phase = _phase(other, "timing")
        runs = (phase or {}).get("runs") or []
        ran = sum(r.get("run", 0) for r in runs)
        if phase and ran:
            timing_phase_seconds = phase["seconds"] / ran
    exposed = trim.load_exposed(args.exposed)
    anchors = cc.large_problem_anchors(kernel_rows, censored)
    repilot = None
    store_model = None
    store_inputs = None
    if args.repilot_job is not None:
        from harness.q1 import repilot as repilot_rule
        from harness.q1.journal import Journal

        rp = cc.load_job(args.repilot_job / "q1")
        pairs = cc.repilot_pairs(rp["items"])
        refs = [dict(r) for r in cc.reference_items(rp["items"])]
        # The store as job 713 ran it (gate (a) a consumer), as pre-specified.
        store_model = cc.fit_store_model(pairs, refs, consumers=cc.STORE_CONSUMER_GATES_REPILOT)
        store_inputs = (pairs, refs)
        rows = Journal(args.repilot_job / "q1" / "repilot" / "journal.jsonl").final_rows()
        repilot = {
            "job": str(args.repilot_job),
            "phases": rp["phases"],
            "summary": cc.repilot_summary(rp["items"], pairs),
            "store_model": {
                "ratio_fits": store_model.ratio_fits,
                "reference_fits": store_model.reference_fits,
                "constant_ratios_same_mode_pairs": cc.fit_store_model(
                    pairs, refs, ratio_mode="constant", consumers=cc.STORE_CONSUMER_GATES_REPILOT
                ).constant_ratios,
                "pairs_same_mode": sum(1 for p in pairs if p["same_mode"]),
            },
            "per_gate_items": cc.gate_stats(rp["items"]),
            "twin_rows": repilot_rule.compare_twins(rows),
            "censored_items": cc.censored_items(args.repilot_job / "q1"),
        }
    trimmed = []
    scenarios_trim = (
        # The pilot pass's proposal recomputed under /2's accounting of units and samples
        # (no margin, no anchors, no exposure, its charges for the fidelity sample and
        # the timing floor); its own card (7.37 GPU-h) is in git at 5af0375.
        ("trim1-recomputed-paired-concurrency", cc.TRIM_RULE_V1, factors, False),
        # The registered rule with the second review's corrections.
        ("trim2-paired-concurrency", cc.TRIM_RULE, factors, True),
        ("trim2-measured-4-per-gpu", cc.TRIM_RULE, None, True),
        (
            "trim2-q30-paired-concurrency",
            {**cc.TRIM_RULE, "family_quota_test": 30, "family_quota_dev": 8},
            factors,
            True,
        ),
        (
            "trim2-no-margin-paired-concurrency",
            {**cc.TRIM_RULE, "frr_margin_units": 0},
            factors,
            True,
        ),
    )
    repilot_consumers = {"consumers": cc.STORE_CONSUMER_GATES_REPILOT}
    store_variants: dict[str, dict[str, Any]] = {
        # written before the re-pilot ran
        "store": {"ratio_mode": "linear", **repilot_consumers},
        # after: one ratio per gate over same-mode pairs; and the references-free bound
        # (post hoc ratio)
        "store-constant": {"ratio_mode": "constant", **repilot_consumers},
        "store-free-references": {
            "ratio_mode": "constant",
            "free_references": True,
            **repilot_consumers,
        },
        # D31 review fix pass: gate (a) is not a consumer (section 18.9)
        "store-no-a": {"ratio_mode": "linear"},
        "store-no-a-constant": {"ratio_mode": "constant"},
    }
    if store_model is not None:
        for variant in store_variants:
            for mode in ("per-bucket", "per-job"):
                if variant == "store-free-references" and mode == "per-bucket":
                    continue
                scenarios_trim += (
                    (f"trim2-{variant}-{mode}-paired-concurrency", cc.TRIM_RULE, factors, True),
                )
    # D31 review fix pass: the memory-aware execution policy (section 18.9; model-based).
    scenarios_trim += (("trim2-exec2-paired-concurrency", cc.TRIM_RULE, factors, True),)
    for label, rule, fac, corrected in scenarios_trim:
        if label.endswith("paired-concurrency") and not factors:
            continue
        extra = {"anchors": anchors, "exposed": exposed} if corrected else {}
        if "-exec2" in label:
            extra["units_of"] = lambda problem, gate: trim.item_units(problem, gate)[0]
        boot_store = None
        if "-store" in label:
            variant = label.removeprefix("trim2-").split("-per-")[0]
            options = store_variants[variant]
            extra["store"] = cc.fit_store_model(*store_inputs, **options)
            extra["store_mode"] = "per-bucket" if "per-bucket" in label else "per-job"
            boot_store = (*store_inputs, options)
        projection = cc.project_trimmed(
            counts,
            fits,
            survival=survival["survival"],
            rule=rule,
            factors=fac,
            witness_rate=args.witness_rate,
            **extra,
        )
        fixed_trim = trimmed_fixed_hours(
            counts,
            fits,
            fixed,
            projection,
            args,
            factors=fac,
            rule=rule,
            timing_item_seconds=(timing_phase_seconds or timing_seconds)
            if corrected
            else timing_seconds,
            measured_charges=corrected,
        )
        boot_extra = {k: v for k, v in extra.items() if k != "store"}
        interval = bootstrap_trimmed(
            all_scored,
            kinds,
            counts,
            survival["survival"],
            rule,
            fac,
            args,
            store_inputs=boot_store,
            **boot_extra,
        )
        buckets = projection["gpu_hours_by_priority"]
        extension_bucket = max(buckets) if buckets else None
        extension = buckets.get(extension_bucket, 0.0) if extension_bucket else 0.0
        core = projection["gpu_hours"] - extension
        fixed_sum = sum(fixed_trim.values())
        total = round(fixed_sum + core, 3)
        scale = (
            interval["high"] / projection["gpu_hours"]
            if interval["high"] and projection["gpu_hours"]
            else None
        )
        high = None if scale is None else round(fixed_sum + core * scale, 3)
        cumulative = []
        running = fixed_sum
        direct = interval.get("cumulative", {})
        for bucket, hours in buckets.items():
            running += hours
            cumulative.append(
                {
                    "through": bucket,
                    "total_central": round(running, 3),
                    "total_high": None
                    if scale is None
                    else round(
                        fixed_sum + scale * sum(v for k, v in buckets.items() if k <= bucket), 3
                    ),
                    # The bootstrap's own 97.5% point of the scoring through this bucket
                    # (not the uniform scale of the whole projection), plus the fixed part.
                    "total_high_direct": None
                    if bucket not in direct
                    else round(fixed_sum + direct[bucket]["high"], 3),
                }
            )
        trimmed.append(
            {
                "name": label,
                "corrected_for_second_review": corrected,
                **projection,
                "priority_cumulative_with_reserve": cumulative,
                "budget_stop": stop_point(projection, fixed_sum, scale),
                "scoring_gpu_hours_95": interval,
                "fixed_gpu_hours": {k: round(v, 3) for k, v in fixed_trim.items()},
                "total_gpu_hours": total,
                "total_gpu_hours_high": high,
                "fits_8_gpu_h": total <= cc.CAP_GPU_HOURS,
                "fits_8_gpu_h_at_high": None if high is None else high <= cc.CAP_GPU_HOURS,
            }
        )
    card = {
        "schema": "q1-pilot-cost-card/2",
        "repilot": repilot,
        "censored_items": censored,
        "large_problem_anchors": anchors,
        "timing_bias_identity_controls": timing_bias([pilot] + ([other] if args.pair_job else [])),
        "timing_phase_seconds_per_item": timing_phase_seconds,
        "exposed_sha256": hashlib.sha256(args.exposed.read_bytes()).hexdigest(),
        "run_records_sha256": None
        if args.records is None
        else hashlib.sha256(args.records.read_bytes()).hexdigest(),
        "paired_concurrency": paired,
        "trimmed": trimmed,
        "spent_gpu_hours": args.spent_gpu_hours,
        "smoke_job": str(args.smoke_job),
        "pilot_job": str(args.pilot_job),
        "per_gate_scoring": cc.gate_stats(scoring_items),
        "per_gate_job1_smoke_prefix": cc.gate_stats(smoke_items),
        "kernel_replicates_complete": len(kernel_rows),
        "kernel_replicate_cost_by_class": {
            klass: cc.summarize([r["total"] for r in kernel_rows if r["cost_class"] == klass])
            for klass in sorted({r["cost_class"] for r in kernel_rows})
        },
        "kernel_replicate_cost_by_role": {
            role: cc.summarize([r["total"] for r in kernel_rows if r["role"] == role])
            for role in sorted({r["role"] for r in kernel_rows})
        },
        "per_kernel_rung": rung,
        "c_over_b": ratio,
        "fixed_phases": fixed,
        "fixed_gpu_hours": fixed_hours,
        "size_model": fits,
        "class_means_cross_check": {k: round(v, 2) for k, v in means.items()},
        "compile_filter": survival,
        "scenarios": scenarios,
        "phases": {
            "smoke": smoke["phases"],
            "pilot": pilot["phases"],
        },
        "kernel_rows": kernel_rows,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cost_card.json").write_text(
        json.dumps(card, indent=1, sort_keys=True, default=str)
    )
    lines = ["| gate | n | median GPU-s | p95 GPU-s | mean GPU-s |", "|---|---:|---:|---:|---:|"]
    for gate, stats in card["per_gate_scoring"].items():
        g = stats["gpu_seconds"]
        lines.append(f"| {gate} | {g['n']} | {g['median']} | {g['p95']} | {g['mean']} |")
    lines += [
        "",
        "| rule | scoring GPU-h | 95% | fixed GPU-h | total GPU-h | high | fits | units |",
        "|---|---:|---|---:|---:|---:|---|---:|",
    ]
    for sc in scenarios:
        band = sc["scoring_gpu_hours_95"]
        low = None if band["low"] is None else round(band["low"], 2)
        high = None if band["high"] is None else round(band["high"], 2)
        lines.append(
            f"| {sc['name']} | {sc['gpu_hours']} | {low}-{high} | {sc['fixed_gpu_hours']} | "
            f"{sc['total_gpu_hours']} | {sc['total_gpu_hours_high']} | {sc['fits_8_gpu_h']} | "
            f"{sc['n_eval_independent']} |"
        )
    lines += [
        "",
        "| trimmed rule | in-scope substrates | units | mutants | scoring GPU-h (all buckets) "
        "| fixed GPU-h | total GPU-h (without the open extension) | high | fits "
        "| pooled witnessed (planning) | families >= 30 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for sc in trimmed:
        lines.append(
            f"| {sc['name']} | {sc['in_scope_substrates']} | {sc['n_eval_independent']} | "
            f"{sc['kernels'].get('mutant')} | {sc['gpu_hours']} | "
            f"{round(sum(sc['fixed_gpu_hours'].values()), 3)} | {sc['total_gpu_hours']} | "
            f"{sc['total_gpu_hours_high']} | {sc['fits_8_gpu_h']} | "
            f"{sc['pooled_witnessed_test_planning']} | {sc['families_with_30_witnessed_test']} |"
        )
    (args.out / "cost_card.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
