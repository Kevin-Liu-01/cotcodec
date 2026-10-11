#!/usr/bin/env python3
"""Operating characteristics of every decision rule in r01-rerun-noise-sources-v2, under the
registered estimator (``harness.r01.estimators``: task-cluster percentile bootstrap, 2,000
resamples, ``numpy.random.default_rng(42)``; readings as registered).

Seeds 42, 43, 44 for the simulated data (each block runs once per seed; pooled). Inputs: the
committed A0 digest table (S1a's per-task step-1 outcomes, 4B H-OSW-fixed, and every group's
pairs for the two-stage model) and a1.jsonl. Task heterogeneity is calibrated on S1a: the
step-1 intraclass correlation of a task's two within-session pairs is 0.06-0.42 for reply text
and 0.34-0.48 for IR across the four size-harness groups, so cells are simulated as
beta-binomial by task with ICC 0.2 (text) and 0.45 (IR), with sensitivity rows at 0.6.

Blocks:

  B_det    DET on 226 step-1 replica pairs (and 113 step-2): exact binomial; beta-binomial by task.
  B_cell1  step-1 cell readings (226 pairs on 113 tasks): text SUFFICIENT/PARTIAL/INERT and IR
           MAJOR/PARTIAL/MINOR over a grid of true hazards.
  B_cell2  step-2 cell readings (113 pairs, one per task).
  VAL      the all-sources live cell against S1a's own per-task step-1 data (205/226, 79/226).
  DECISIVE joint scenarios: how often the primary readings are decisive.
  A1_cen   the region census on 226 cross-boot pairs (task-cluster bootstrap).
  C_env, K6, CL   the wave-1 blocks for the unchanged Stage C rule, the P-K6 prediction and the
           dropped closed loop, re-run from ``../power_r01.py``.
  PRED     the two-stage model: S1a validation (every group, leave-one-group-out), the D_w
           sensitivity to the step-1 onset hazard, and predictions for every removal arm under
           the scenarios with intervals from Stage B sampling and an S1a task-bootstrap refit.

Usage (worktree root): PYTHONPATH=. uv run --locked python <this> --out power-r01-v2.json [--reps N]
(blocks may run as parallel parts with --only and be joined with --merge; each block's seeds are
its own, so a part equals the same block in a single run)
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
from scipy import stats

from harness.r01 import estimators as E
from harness.r01 import stepkick as SK

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
DIGESTS = ROOT / "program/evidence/2026-10-11/r01-stage-a0/s1a-step-digests.jsonl.gz"
A1 = ROOT / "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"
CENSUS = ROOT / "program/evidence/2026-10-11/r01-stage-a0/census.json"
SEEDS = (42, 43, 44)
BLOCK_NAMES = ("B_det", "B_cells", "VAL", "DECISIVE", "A1_cen", "PRED", "V1")
TASKS = 113
ICC_TEXT, ICC_IR = 0.2, 0.45


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_probs(rng, h: float, icc: float, reps: int, tasks: int = TASKS) -> np.ndarray:
    if h <= 0:
        return np.zeros((reps, tasks))
    if h >= 1:
        return np.ones((reps, tasks))
    a, b = h * (1 - icc) / icc, (1 - h) * (1 - icc) / icc
    return rng.beta(a, b, size=(reps, tasks))


def sim_cell(rng, h: float, icc: float, reps: int, per_task: int) -> tuple[np.ndarray, np.ndarray]:
    p = task_probs(rng, h, icc, reps)
    k = rng.binomial(per_task, p).astype(float)
    return k, np.full_like(k, float(per_task))


def readings(h: float, icc: float, reps: int, per_task: int, level: str) -> dict:
    out = {}
    agg = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        k, c = sim_cell(rng, h, icc, reps, per_task)
        _, lo, hi = E.bounds_many(k, c, boot=E.BOOT, seed=seed)
        if level == "text":
            agg.append(((lo > E.TEXT_SUFFICIENT).mean(), (hi < E.TEXT_INERT).mean()))
        else:
            agg.append(((lo > E.IR_MAJOR).mean(), (hi < E.IR_MINOR).mean()))
    a = np.mean(agg, axis=0)
    hi_label, lo_label = ("SUFFICIENT", "INERT") if level == "text" else ("MAJOR", "MINOR")
    out.update(
        {
            "true_h": h,
            "icc": icc,
            f"P_{hi_label}": round(float(a[0]), 3),
            f"P_{lo_label}": round(float(a[1]), 3),
            "P_PARTIAL": round(float(1 - a[0] - a[1]), 3),
        }
    )
    return out


def block_det() -> dict:
    out = {}
    for n, per_task in ((226, 2), (113, 1)):
        kstar = E.det_threshold(n)
        rows = []
        for p in (0.0, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.03, 0.05):
            pk = stats.binom.pmf(np.arange(n + 1), n, p) if p > 0 else np.r_[1.0, np.zeros(n)]
            rows.append(
                {
                    "p": p,
                    "P_DET_OK": round(float(pk[0]), 4),
                    "P_DET_NEAR": round(float(pk[1:kstar].sum()), 4),
                    "P_DET_UNATTAINABLE": round(float(pk[kstar:].sum()), 4),
                }
            )
        bb = []
        if per_task > 1:
            for icc in (0.2, 0.5):
                for p in (0.0025, 0.005, 0.01, 0.02):
                    res = []
                    for seed in SEEDS:
                        rng = np.random.default_rng(seed)
                        k = rng.binomial(per_task, task_probs(rng, p, icc, 20000)).sum(axis=1)
                        res.append(((k == 0).mean(), (k >= kstar).mean()))
                    r = np.mean(res, axis=0)
                    bb.append(
                        {
                            "p": p,
                            "icc": icc,
                            "P_DET_OK": round(float(r[0]), 4),
                            "P_DET_UNATTAINABLE": round(float(r[1]), 4),
                        }
                    )
        out[f"n{n}"] = {
            "k_star": kstar,
            "upper95_at_zero": round(1 - 0.05 ** (1 / n), 5),
            "exact": rows,
            "beta_binomial_by_task": bb,
        }
    return out


def block_cells(reps: int) -> dict:
    out = {
        "step1": [],
        "step2": [],
        "design": {"step1": "113 tasks x 2 pairs", "step2": "113 tasks x 1 pair"},
    }
    for h in (0.0, 0.01, 0.03, 0.05, 0.10, 0.20, 0.30, 0.40, 0.63, 0.90):
        out["step1"].append({"level": "text", **readings(h, ICC_TEXT, reps, 2, "text")})
    for h in (0.0, 0.01, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.25, 0.35):
        out["step1"].append({"level": "ir", **readings(h, ICC_IR, reps, 2, "ir")})
    for h in (0.05, 0.10, 0.25):
        out["step1"].append({"level": "ir", **readings(h, 0.6, reps, 2, "ir")})
    for h in (0.01, 0.05, 0.20, 0.30, 0.63):
        out["step2"].append({"level": "text", **readings(h, ICC_TEXT, reps, 1, "text")})
    for h in (0.01, 0.05, 0.10, 0.25, 0.35):
        out["step2"].append({"level": "ir", **readings(h, ICC_IR, reps, 1, "ir")})
    return out


def s1a_step1(rows: list[dict]) -> dict:
    key = lambda r: (r["size"], r["harness"], r["session"], r["task_id"], r["rerun"])  # noqa: E731
    d = {key(r): r for r in rows}
    tasks = sorted({r["task_id"] for r in rows})
    out = {"tasks": [], "text": [], "ir": []}
    for s in ("S1", "S2"):
        for t in tasks:
            a, b = (
                d[("4B", "H-OSW-fixed", s, t, 1)]["steps"][0],
                d[("4B", "H-OSW-fixed", s, t, 2)]["steps"][0],
            )
            out["tasks"].append(t)
            out["text"].append(int(a["rep"] != b["rep"]))
            out["ir"].append(int(a["ir"] != b["ir"]))
    return out


def block_val(s1a: dict, reps: int) -> dict:
    ss_t, sc_t = E.task_sums(s1a["tasks"], s1a["text"])
    ss_i, sc_i = E.task_sums(s1a["tasks"], s1a["ir"])
    rows = []
    for text_h, ir_h in (
        (0.907, 0.350),
        (0.907, 0.30),
        (0.907, 0.25),
        (0.907, 0.20),
        (0.907, 0.15),
        (0.907, 0.45),
        (0.907, 0.50),
        (0.85, 0.35),
        (0.80, 0.35),
        (0.70, 0.35),
        (0.65, 0.06),
    ):
        counts = {"VAL_PASS": 0, "VAL_FAIL": 0, "VAL_UNRESOLVED": 0}
        n = 0
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            kt, ct = sim_cell(rng, text_h, ICC_TEXT, reps, 2)
            ki, ci = sim_cell(rng, ir_h, ICC_IR, reps, 2)
            for r in range(reps):
                flags = []
                for bs, bc, ss, sc in ((kt[r], ct[r], ss_t, sc_t), (ki[r], ci[r], ss_i, sc_i)):
                    lo, hi, d = E.diff_bounds(bs, bc, ss, sc, E.BOOT, seed + r)
                    flags.append((lo, hi, d))
                if all(lo > -E.VAL_MARGIN and hi < E.VAL_MARGIN for lo, hi, _ in flags):
                    counts["VAL_PASS"] += 1
                elif any((lo > 0 or hi < 0) and abs(d) > E.VAL_FAIL_DIFF for lo, hi, d in flags):
                    counts["VAL_FAIL"] += 1
                else:
                    counts["VAL_UNRESOLVED"] += 1
                n += 1
        rows.append(
            {
                "true_text": text_h,
                "true_ir": ir_h,
                **{f"P_{k}": round(v / n, 3) for k, v in counts.items()},
            }
        )
    return {
        "s1a": {
            "text": [int(ss_t.sum()), int(sc_t.sum())],
            "ir": [int(ss_i.sum()), int(sc_i.sum())],
        },
        "rule": "VAL_PASS: both differences' 95% intervals inside +-0.15; VAL_FAIL: either excludes 0 with |diff| > 0.10",
        "rows": rows,
    }


SCENARIOS = {
    "records_redundant": {
        "s": (0.63, 0.05),
        "c": (0.60, 0.10),
        "o": (0.80, 0.30),
        "X": (0.907, 0.35),
    },
    "serving_only": {"s": (0.63, 0.05), "c": (0.01, 0.002), "o": (0.02, 0.005), "X": (0.65, 0.06)},
    "screen_content": {"s": (0.63, 0.05), "c": (0.15, 0.01), "o": (0.85, 0.33), "X": (0.907, 0.35)},
    "clock_heavy": {"s": (0.63, 0.05), "c": (0.85, 0.30), "o": (0.30, 0.05), "X": (0.907, 0.35)},
    "intermediate_adversarial": {
        "s": (0.63, 0.05),
        "c": (0.12, 0.12),
        "o": (0.20, 0.15),
        "X": (0.85, 0.30),
    },
}


def block_decisive(s1a: dict, reps: int) -> dict:
    ss_t, sc_t = E.task_sums(s1a["tasks"], s1a["text"])
    ss_i, sc_i = E.task_sums(s1a["tasks"], s1a["ir"])
    out = {}
    for name, sc in SCENARIOS.items():
        tally = {
            "joint_text_decisive": 0,
            "ir_all_decisive": 0,
            "val_decisive": 0,
            "gate_decisive": 0,
        }
        joint_counts: dict[str, int] = {}
        n = 0
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            sims = {}
            for cell, (th, ih) in sc.items():
                kt, ct = sim_cell(rng, th, ICC_TEXT, reps, 2)
                ki, ci = sim_cell(rng, ih, ICC_IR, reps, 2)
                _, tlo, thi = E.bounds_many(kt, ct, boot=E.BOOT, seed=seed)
                _, ilo, ihi = E.bounds_many(ki, ci, boot=E.BOOT, seed=seed + 100)
                sims[cell] = (kt, ct, tlo, thi, ki, ci, ilo, ihi)
            for r in range(reps):
                text = {c: E.read_text(sims[c][2][r], sims[c][3][r]) for c in ("s", "c", "o")}
                ir = {c: E.read_ir(sims[c][6][r], sims[c][7][r]) for c in ("s", "c", "o")}
                joint = E.joint_text(text)
                joint_counts[joint] = joint_counts.get(joint, 0) + 1
                kt, ct, _, _, ki, ci, _, _ = sims["X"]
                flags = [
                    E.diff_bounds(kt[r], ct[r], ss_t, sc_t, 500, seed + r),
                    E.diff_bounds(ki[r], ci[r], ss_i, sc_i, 500, seed + r),
                ]
                if all(lo > -E.VAL_MARGIN and hi < E.VAL_MARGIN for lo, hi, _ in flags):
                    val = "VAL_PASS"
                elif any((lo > 0 or hi < 0) and abs(d) > E.VAL_FAIL_DIFF for lo, hi, d in flags):
                    val = "VAL_FAIL"
                else:
                    val = "VAL_UNRESOLVED"
                jt = joint != "MIXED"
                ira = all(v != "PARTIAL" for v in ir.values())
                vd = val != "VAL_UNRESOLVED"
                tally["joint_text_decisive"] += jt
                tally["ir_all_decisive"] += ira
                tally["val_decisive"] += vd
                tally["gate_decisive"] += jt and vd
                n += 1
        out[name] = {
            "cells_true_text_ir": sc,
            **{f"P_{k}": round(v / n, 3) for k, v in tally.items()},
            "joint_text_distribution": {
                k: round(v / n, 3) for k, v in sorted(joint_counts.items())
            },
        }
    out["definition"] = (
        "gate decisive = the joint text reading over s, c, o is REDUNDANT, SINGLE_SOURCE or NEITHER (not MIXED) "
        "and VAL is PASS or FAIL (not UNRESOLVED); DET's three labels are all readings. VAL here uses 500 "
        "resamples per replicate for speed (the registered analysis uses 2,000)."
    )
    return out


def block_a1(reps: int) -> dict:
    rows = []
    for s in (0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
        agg = []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            k, c = sim_cell(rng, s, ICC_IR, reps, 2)
            _, lo, hi = E.bounds_many(k, c, boot=E.BOOT, seed=seed)
            agg.append(((lo > 0.20).mean(), (hi < 0.20).mean()))
        a = np.mean(agg, axis=0)
        rows.append(
            {
                "true_non_clock_share": s,
                "P_MULTI_REGION": round(float(a[0]), 3),
                "P_CLOCK_ONLY": round(float(a[1]), 3),
                "P_UNRESOLVED": round(float(1 - a[0] - a[1]), 3),
            }
        )
    return {
        "design": "226 cross-boot default pairs (b1/b2, b3/b4) on 113 tasks, task-cluster bootstrap, ICC 0.45",
        "rule": {"MULTI_REGION": "lower bound > 0.20", "CLOCK_ONLY": "upper bound < 0.20"},
        "rows": rows,
    }


def v1_blocks(quick: float) -> dict:
    spec = importlib.util.spec_from_file_location("power_r01_v1", HERE.parent / "power_r01.py")
    v1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v1)
    counts = v1.s1a_counts(A1)
    return {
        "C_env": v1.block_c(reps=int(2000 * quick)),
        "K6": v1.block_k6(counts, reps=int(4000 * quick)),
        "CL": v1.block_cl(counts, reps=int(3000 * quick)),
        "note": "wave-1 functions from ../power_r01.py, unchanged designs (Stage C, P-K6, the dropped closed loop)",
    }


def combine(th: dict, *cells: str) -> tuple[float, float]:
    """Text and IR hazards of several independent sources acting together."""
    return (
        float(1 - np.prod([1 - th[c][0] for c in cells])),
        float(1 - np.prod([1 - th[c][1] for c in cells])),
    )


def block_pred(rows: list[dict], recs: list[dict], reps: int) -> dict:
    groups = {
        f"{z}/{h}": SK.pairs_from(rows, recs, z, h)
        for z in ("4B", "9B")
        for h in ("H-OSW-fixed", "H-GA")
    }
    validation = {g: SK.validate(groups, g) for g in groups}
    target = groups["4B/H-OSW-fixed"]
    base = validation["4B/H-OSW-fixed"]
    p = base["params"]
    refits = SK.refit_draws(target, 500, seed=42)
    sens = []
    for k1 in (0.0, 0.05, 0.10, 0.20, 0.30, 0.50, 0.63, 0.80, 0.907):
        pr = SK.predict(k1, k1 * p["pi"], k1, rho=p["rho"], tau=p["tau"], q=base["q"])
        sens.append(
            {
                "kappa_1_and_k": k1,
                "pi": round(p["pi"], 4),
                "N": round(pr["N"], 4),
                "D_w": round(pr["D_w"], 4),
            }
        )
    # removal arms: (step-1 cell, step-2 cell) per arm; truths from the scenarios (step 2 = step 1)
    arms = {
        "live (all sources)": "X",
        "remove serving (screen live)": "x",
        "remove clock": "os",
        "remove non-clock regions": "cs",
        "remove observation (serving only)": "s",
        "remove serving and clock": "o",
        "remove serving and non-clock": "c",
        "frozen (none)": "floor",
    }
    preds = {}
    for name, sc in SCENARIOS.items():
        th = {"X": sc["X"], "s": sc["s"], "c": sc["c"], "o": sc["o"], "floor": (0.0, 0.0)}
        # combined cells under independence of sources for the scenario truths
        th["x"] = combine(th, "c", "o")
        th["os"] = combine(th, "o", "s")
        th["cs"] = combine(th, "c", "s")
        res = {}
        per_arm = {}
        for i, (arm, cell) in enumerate(arms.items()):
            kt, ki = th[cell]
            rng = np.random.default_rng(42 + i)
            k1 = (
                rng.binomial(2, task_probs(rng, kt, ICC_TEXT, 500)).sum(axis=1) / 226
                if kt > 0
                else np.zeros(500)
            )
            i1 = (
                rng.binomial(2, task_probs(rng, ki, ICC_IR, 500)).sum(axis=1) / 226
                if ki > 0
                else np.zeros(500)
            )
            k2 = (
                rng.binomial(1, task_probs(rng, kt, ICC_TEXT, 500)).sum(axis=1) / 113
                if kt > 0
                else np.zeros(500)
            )
            i1 = np.minimum(i1, k1)
            per_arm[arm] = np.array(
                [
                    SK.predict(a, b, c, rho=rho, tau=tau, q=q)["D_w"]
                    for a, b, c, (rho, tau, q) in zip(k1, i1, k2, refits, strict=True)
                ]
            )
            point = SK.predict(kt, ki, kt, rho=p["rho"], tau=p["tau"], q=base["q"])
            res[arm] = {
                "cell": cell,
                "true_text_ir": [round(kt, 4), round(ki, 4)],
                "D_w_point": round(point["D_w"], 4),
                "D_w_95": [
                    round(float(np.quantile(per_arm[arm], 0.025)), 4),
                    round(float(np.quantile(per_arm[arm], 0.975)), 4),
                ],
            }
        live = per_arm["live (all sources)"]
        for arm in arms:
            delta = (
                per_arm[arm] - live
            )  # the same S1a refit in both arms: q's uncertainty is shared
            res[arm]["delta_vs_live_pp"] = round(100 * float(np.median(delta)), 2)
            res[arm]["delta_vs_live_95_pp"] = [
                round(100 * float(np.quantile(delta, 0.025)), 2),
                round(100 * float(np.quantile(delta, 0.975)), 2),
            ]
        preds[name] = res
    return {
        "validation": validation,
        "sensitivity_to_onset_hazard": sens,
        "removal_predictions": preds,
        "note": (
            "Removal-arm truths for combined cells assume independent sources (scenario construction only); "
            "the registered predictions use each arm's measured cell. Intervals: 500 draws pairing simulated "
            "Stage B cell estimates (step 1: 226 pairs; step 2: 113) with S1a task-bootstrap refits of rho, tau, q."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reps", type=int, default=300, help="replicates per seed per scenario")
    ap.add_argument("--quick", type=float, default=1.0, help="scale for the wave-1 blocks")
    ap.add_argument(
        "--only", default=None, help="comma-separated blocks (parts are joined with --merge)"
    )
    ap.add_argument(
        "--merge", type=Path, nargs="+", default=None, help="join part files into --out"
    )
    args = ap.parse_args()
    if args.merge:
        merged: dict = {}
        timings: dict = {}
        for part in args.merge:
            data = json.loads(part.read_text())
            timings.update(data.pop("timings_s", {}))
            for key, value in data.items():
                if key in merged and merged[key] != value and key not in BLOCK_NAMES:
                    raise SystemExit(f"parts disagree on {key}")
                merged.setdefault(key, value)
        merged["timings_s"] = timings
        merged["merged_from"] = [p.name for p in args.merge]
        args.out.write_text(json.dumps(merged, indent=1) + "\n")
        return 0
    with gzip.open(DIGESTS, "rt") as handle:
        rows = [json.loads(x) for x in handle]
    recs = [json.loads(x) for x in A1.read_text().splitlines()]
    s1a = s1a_step1(rows)
    out = {
        "schema": "r01-power-v2",
        "seeds": list(SEEDS),
        "reps_per_seed": args.reps,
        "bootstrap": E.BOOT,
        "icc": {"text": ICC_TEXT, "ir": ICC_IR},
        "inputs": {
            "digests_sha256": sha(DIGESTS),
            "a1_jsonl_sha256": sha(A1),
            "census_sha256": sha(CENSUS),
        },
        "thresholds": {
            "text_sufficient": E.TEXT_SUFFICIENT,
            "text_inert": E.TEXT_INERT,
            "ir_major": round(E.IR_MAJOR, 4),
            "ir_minor": round(E.IR_MINOR, 4),
            "val_margin": E.VAL_MARGIN,
            "val_fail_diff": E.VAL_FAIL_DIFF,
        },
    }
    blocks = {
        "B_det": lambda: block_det(),
        "B_cells": lambda: block_cells(args.reps),
        "VAL": lambda: block_val(s1a, args.reps),
        "DECISIVE": lambda: block_decisive(s1a, args.reps),
        "A1_cen": lambda: block_a1(args.reps),
        "PRED": lambda: block_pred(rows, recs, args.reps),
        "V1": lambda: v1_blocks(args.quick),
    }
    timings = {}
    for name, fn in blocks.items():
        if args.only and name not in args.only.split(","):
            continue
        t = time.time()
        out[name] = fn()
        timings[name] = round(time.time() - t, 1)
        print(name, timings[name], "s", flush=True)
        args.out.write_text(json.dumps(out, indent=1) + "\n")
    out["timings_s"] = timings
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
