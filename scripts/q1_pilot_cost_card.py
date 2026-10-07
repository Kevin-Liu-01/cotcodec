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
drafted design and a grid of simple trims, and under the proposed trimming rule
``q1-stage0-trim/1`` (``cost_card.TRIM_RULE``) at the measured cost and, when
``--pair-job`` names a paired re-run of the same items at another concurrency,
at that job's measured per-gate cost ratio.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    out["fidelity"] = {
        "kernels": len(per_kernel),
        "per_gate": cc.gate_stats(fidelity_items),
        "per_kernel_gpu_seconds": cc.summarize(list(per_kernel.values())),
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
) -> dict[str, float]:
    """Fixed phases under the trimming rule (GPU-h): admission of every problem
    (corpus metrics), specializations of in-scope parents, calibration on the
    S1-cal substrates within the FRR set's largest input size, a registered
    fidelity sample (every in-scope evaluation substrate, the three adversarial
    controls and one test mutant per family and source tier), the timing noise
    floor (``timing_floor_items`` timing items at the measured GPU-seconds of one)
    and the audit-hole replay cap (the draft's cap, not measured)."""
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
        "timing_noise_floor": timing_floor_hours(rule, timing_item_seconds, args),
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
) -> dict[str, float | None]:
    """Cluster bootstrap of the trimmed scoring projection over pilot parents
    (each with its mutants and controls), refitting the size model each time."""
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
    totals = []
    for _ in range(args.resamples):
        sample = [i for _ in keys for i in clusters[rng.choice(keys)]]
        fits = cc.fit_item_costs(sample)
        totals.append(
            cc.project_trimmed(counts, fits, survival=survival, rule=rule, factors=factors)[
                "gpu_hours"
            ]
        )
    totals.sort()
    return {
        "low": round(totals[int(0.025 * (len(totals) - 1))], 3),
        "high": round(totals[int(round(0.975 * (len(totals) - 1)))], 3),
    }


def stop_point(
    projection: dict[str, Any], fixed_total: float, scale: float | None
) -> dict[str, Any]:
    """Where the rule's 8 GPU-h stop falls (central and high projection): the last
    priority bucket that completes, the share of the next one that runs, and the
    test-split mutants scored (P2 plus the P7 extension that fits)."""
    buckets = projection["gpu_hours_by_priority"]
    test_quota = sum(v["test"] for v in projection["mutants_per_family"].values())
    extension = sum(v["test_extension_max"] for v in projection["mutants_per_family"].values())
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
            partial = {"bucket": name, "share": round(room / hours, 3) if hours else 0.0}
            break
        scored_test = test_quota if "P2" in completed else None
        if scored_test is not None:
            if "P7" in completed:
                scored_test += extension
            elif partial and partial["bucket"] == "P7":
                scored_test += round(extension * partial["share"])
        if partial and partial["bucket"] == "P2":
            scored_test = round(test_quota * partial["share"])
        out[label] = {
            "completed": completed,
            "partial": partial,
            "test_mutants_scored": scored_test,
        }
    return out


def timing_floor_hours(
    rule: dict[str, Any], timing_item_seconds: float | None, args: argparse.Namespace
) -> float:
    """The noise floor at the measured GPU-seconds of one timing item (it runs
    alone on its GPU), else the draft's estimate."""
    if timing_item_seconds is None:
        return args.timing_floor_gpu_hours
    return int(rule["timing_floor_items"]) * timing_item_seconds / 3600


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
    b_cum = [row["a"] + row["b_marginal"] for row in kernel_rows]
    c_cum = [row["a"] + row["b_marginal"] + row["c_marginal"] for row in kernel_rows]
    ratio = {
        "median_c_cumulative_over_b_cumulative": (
            round(statistics.median(c_cum) / statistics.median(b_cum), 3) if b_cum else None
        ),
        "median_c_marginal_over_b_marginal": (
            round(
                statistics.median([r["c_marginal"] for r in kernel_rows])
                / statistics.median([r["b_marginal"] for r in kernel_rows]),
                3,
            )
            if kernel_rows
            else None
        ),
        "c_lite_trigger_2x": None,
    }
    if ratio["median_c_cumulative_over_b_cumulative"] is not None:
        ratio["c_lite_trigger_2x"] = ratio["median_c_cumulative_over_b_cumulative"] > 2.0
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
    trimmed = []
    for label, quota_test, quota_dev, fac in (
        ("trim-q60", 60, 15, None),
        ("trim-q30", 30, 8, None),
        ("trim-q120", 120, 30, None),
        ("trim-q60-paired-concurrency", 60, 15, factors),
        ("trim-q120-paired-concurrency", 120, 30, factors),
        ("trim-q200-paired-concurrency", 200, 50, factors),
    ):
        if label.endswith("paired-concurrency") and not factors:
            continue
        rule = {**cc.TRIM_RULE, "family_quota_test": quota_test, "family_quota_dev": quota_dev}
        projection = cc.project_trimmed(
            counts,
            fits,
            survival=survival["survival"],
            rule=rule,
            factors=fac,
            witness_rate=args.witness_rate,
        )
        fixed_trim = trimmed_fixed_hours(
            counts,
            fits,
            fixed,
            projection,
            args,
            factors=fac,
            rule=rule,
            timing_item_seconds=timing_seconds,
        )
        interval = bootstrap_trimmed(
            all_scored, kinds, counts, survival["survival"], rule, fac, args
        )
        # The P7 extension is open-ended by design (the stop cuts it), so the rule
        # "fits" when everything through P6 fits.
        extension = projection["gpu_hours_by_priority"].get("P7", 0.0)
        core = projection["gpu_hours"] - extension
        total = round(sum(fixed_trim.values()) + core, 3)
        high = (
            None
            if interval["high"] is None
            else round(
                sum(fixed_trim.values())
                + core * interval["high"] / max(projection["gpu_hours"], 1e-9),
                3,
            )
        )
        # Under the rule's stop, scoring halts when the Stage 0 total would pass 8 GPU-h
        # with the timing floor and the replay cap held in reserve; where the stop
        # falls at the central and at the high projection.
        before = sum(
            v
            for k, v in fixed_trim.items()
            if k not in {"timing_noise_floor", "audit_hole_replay_cap"}
        )
        reserve = fixed_trim["timing_noise_floor"] + fixed_trim["audit_hole_replay_cap"]
        scale = (
            interval["high"] / projection["gpu_hours"]
            if interval["high"] and projection["gpu_hours"]
            else None
        )
        cumulative = []
        running = before + reserve
        for bucket, hours in projection["gpu_hours_by_priority"].items():
            running_high = None
            running += hours
            if scale is not None:
                running_high = (
                    before
                    + reserve
                    + scale
                    * sum(v for k, v in projection["gpu_hours_by_priority"].items() if k <= bucket)
                )
            cumulative.append(
                {
                    "through": bucket,
                    "total_central": round(running, 3),
                    "total_high": None if running_high is None else round(running_high, 3),
                }
            )
        stop = stop_point(projection, before + reserve, scale)
        trimmed.append(
            {
                "name": label,
                **projection,
                "priority_cumulative_with_reserve": cumulative,
                "budget_stop": stop,
                "scoring_gpu_hours_95": interval,
                "fixed_gpu_hours": {k: round(v, 3) for k, v in fixed_trim.items()},
                "total_gpu_hours": total,
                "total_gpu_hours_high": high,
                "fits_8_gpu_h": total <= cc.CAP_GPU_HOURS,
                "fits_8_gpu_h_at_high": None if high is None else high <= cc.CAP_GPU_HOURS,
            }
        )
    card = {
        "schema": "q1-pilot-cost-card/1",
        "censored_items": censored,
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
        "| trimmed rule | in-scope substrates | units | mutants | scoring GPU-h (P1-P7) "
        "| fixed GPU-h | total GPU-h (P1-P6) | high | fits | pooled witnessed (planning) "
        "| families >= 30 |",
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
