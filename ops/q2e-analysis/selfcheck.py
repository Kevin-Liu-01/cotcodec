"""Analyst's self-check of E's primary reading: an independent re-implementation, from the
merged records and the registration's definitions (section 10), of the primary point
estimates, the delta paired t, the X sign flip and the task-cluster bootstrap bounds that
DR2 and DR5 read. An operator script, not code of record, and not section 18's fresh
verifier: it imports no harness module and uses its own random streams (seed 20261013), so
its randomization p-value and bootstrap bounds agree with the registered ones only to Monte
Carlo error. Point estimates and the t test must agree exactly.

    python3 -E -s -B selfcheck.py e.jsonl plan-e.json report.json > selfcheck.json
"""

from __future__ import annotations

import itertools
import json
import sys

import numpy as np
from scipy import stats

SIZES = ("4B", "9B")
OSW, GA = "H-OSW-fixed", "H-GA"
SESSIONS = ("E1", "E2", "E3", "E4")
PAIRS = list(itertools.permutations(range(4), 2))  # ordered s != s'
UPAIRS = list(itertools.combinations(range(4), 2))
N, SEED = 10_000, 20261013


def load(path: str) -> list[dict]:
    return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]


def array(records: list[dict], tasks: list[str], value: str = "raw") -> np.ndarray:
    final: dict = {}
    for r in records:
        k = (r["size"], r["session"], r["task_id"], r["harness"])
        if k not in final or r["attempt"] > final[k]["attempt"]:
            final[k] = r
    y = np.full((2, len(tasks), 2, 4), np.nan)  # (size, task, harness[OSW, GA], session)
    for zi, z in enumerate(SIZES):
        for ki, t in enumerate(tasks):
            for hi, h in enumerate((OSW, GA)):
                for si, s in enumerate(SESSIONS):
                    r = final.get((z, s, t, h))
                    if r is None or r["status"] != "scored":
                        continue
                    score = r["score"]
                    if value == "corrected" and r.get("corrected_score") is not None:
                        score = r["corrected_score"]
                    y[zi, ki, hi, si] = 1.0 if float(score) == 1.0 else 0.0
    return y


def estimates(y: np.ndarray) -> dict[str, float]:
    d = y[:, :, 1, :] - y[:, :, 0, :]  # (Z, K, S): H-GA minus H-OSW-fixed
    prod = np.stack([d[:, :, a] * d[:, :, b] for a, b in PAIRS], axis=-1).mean(-1)  # (Z, K)
    x = prod.mean(1)
    disc = np.stack([(y[..., a] != y[..., b]).astype(float) for a, b in UPAIRS], -1).mean(-1)
    db = disc.mean(axis=(1, 2))  # (Z,)
    xp = np.maximum(x, 0)
    pi = np.where(xp / 4 + db / 2 > 0, (xp / 4) / np.maximum(xp / 4 + db / 2, 1e-300), 0.0)
    return {
        "delta": float(d.mean(axis=(0, 2)).mean()),
        "delta_4B": float(d[0].mean()), "delta_9B": float(d[1].mean()),
        "D_b_4B": float(db[0]), "D_b_9B": float(db[1]), "D_b": float(db.mean()),
        "X_4B": float(x[0]), "X_9B": float(x[1]), "X": float(x.mean()),
        "pi_4B": float(pi[0]), "pi_9B": float(pi[1]), "pi_small": float(pi.mean()),
        "success_4B_OSW": float(np.nanmean(y[0, :, 0])), "success_4B_GA": float(np.nanmean(y[0, :, 1])),
        "success_9B_OSW": float(np.nanmean(y[1, :, 0])), "success_9B_GA": float(np.nanmean(y[1, :, 1])),
    }  # fmt: skip


def tests(y: np.ndarray, rng: np.random.Generator) -> dict[str, float]:
    d = y[:, :, 1, :] - y[:, :, 0, :]
    dbar = d.mean(axis=(0, 2))
    n = dbar.size
    se = dbar.std(ddof=1) / np.sqrt(n)
    t = dbar.mean() / se
    q90 = stats.t.ppf(0.95, n - 1)
    prod = np.stack([d[:, :, a] * d[:, :, b] for a, b in PAIRS], -1).mean(-1)  # (Z, K)
    qt = prod.mean(0)
    flips = np.where(rng.random((N, qt.size)) < 0.5, -1.0, 1.0)
    p_x = (1 + np.sum((flips * qt).mean(1) >= qt.mean() - 1e-12)) / (1 + N)
    return {"delta_t_p": float(2 * stats.t.sf(abs(t), n - 1)),
            "delta_ci90": [float(dbar.mean() - q90 * se), float(dbar.mean() + q90 * se)],
            "x_signflip_p": float(p_x), "tasks_nonzero_q": int(np.sum(qt != 0))}  # fmt: skip


def bootstrap(y: np.ndarray, rng: np.random.Generator) -> dict[str, list[float]]:
    names = ("delta", "D_b", "pi_small", "pi_4B", "pi_9B", "X_9B")
    draws = {k: [] for k in names}
    k = y.shape[1]
    for _ in range(N):
        e = estimates(y[:, rng.integers(0, k, k)])
        for name in names:
            draws[name].append(e[name])
    out = {}
    for name in names:
        v = np.asarray(draws[name])
        out[name] = {"ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))],
                     "one_sided_95": [float(np.percentile(v, 5)), float(np.percentile(v, 95))]}  # fmt: skip
    return out


def main() -> int:
    records, plan, report = load(sys.argv[1]), json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    rng = np.random.default_rng(SEED)
    out: dict = {"note": __doc__.split("\n\n")[0]}
    for label, tasks, value, key in (
        ("primary_raw", plan["tasks"], "raw", "primary"),
        ("primary_corrected", plan["tasks"], "corrected", "checker_corrected"),
        ("s1a_base_raw", plan["s1a_base"], "raw", "secondary_s1a_base"),
    ):  # fmt: skip
        y = array(records, list(tasks), value)
        mine = estimates(y)
        reg = report[key]["estimates"]
        diffs = {n: abs(mine[n] - reg[n]["estimate"]) for n in mine if n in reg}
        block = {"missing_cells": int(np.isnan(y).sum()), "estimates": mine,
                 "max_abs_diff_point_estimates": max(diffs.values()), "diffs": diffs}  # fmt: skip
        if label == "primary_raw":
            tt = tests(y, rng)
            regt = report["primary"]["tests"]
            block["tests"] = tt
            block["registered_tests"] = {"delta_t_p": regt["delta_paired_t"]["p"],
                                         "delta_ci90": regt["delta_paired_t"]["ci90_t"],
                                         "x_signflip_p": regt["x_signflip_p"]}  # fmt: skip
            boot = bootstrap(y, rng)
            block["bootstrap"] = boot
            block["registered_bootstrap"] = {n: {"ci95": reg[n]["ci95"], "one_sided_95": reg[n]["one_sided_95"]}
                                             for n in boot}  # fmt: skip
            present = min(tt["delta_t_p"], tt["x_signflip_p"]) <= 0.025
            lo, hi = tt["delta_ci90"]
            near = (not present and lo >= -0.075 and hi <= 0.075
                    and boot["pi_small"]["one_sided_95"][1] < 0.12)  # fmt: skip
            block["dr2_recomputed"] = "Present" if present else ("Near-equivalent" if near else "Inconclusive")
            lb, ub = boot["pi_small"]["one_sided_95"]
            block["dr5_recomputed"] = "GO" if lb > 0.13 else ("NO-GO" if ub < 0.13 else "INCONCLUSIVE")
            block["registered_dr2"] = report["primary"]["DR2"].get("class")
            block["registered_dr5"] = report["primary"]["DR5"].get("outcome")
        out[label] = block
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
