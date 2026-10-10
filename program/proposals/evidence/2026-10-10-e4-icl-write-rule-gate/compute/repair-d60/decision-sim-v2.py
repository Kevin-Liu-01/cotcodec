#!/usr/bin/env python3
"""E4 gate repair (D60), CPU check S2v2: the v2 decision path end to end, and its decisiveness.

Wave 1's S2 simulated eligibility with Holm over 14 families and K2 at an
absolute 8 of 14, and never simulated the guard or STOP_TR. Registration v2
has 15 built families (10 episode-specific, 5 fixed-function; `family-table.json`),
K2 = fewer than 4 eligible episode-specific families, the placebo test as the
decision-bearing episode-specificity rule, and the capacity and span rules of
wave 1 applied to the families that pass it. This script runs the whole path
per replicate: Step 1 (cluster-t, Holm over 15) -> K2 -> placebo test -> STOP_TR
-> capacity -> span, under six named scenarios whose correct verdict is known,
and reports how often the gate reaches the correct decisive verdict, any
decisive verdict, or a wrong one.

The instrument gates (I1-I3, I5-I7) are not resampled here; their pass rates come
from the S1v2 surrogate (`oracle-estimator-v2*.json`) and enter the summary as a
separate factor. Every noise SD is an assumption until the pilot measures it.

Usage: python decision-sim-v2.py <out.json>
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import zlib

import numpy as np
from scipy import stats

REPS = 2000
N_EP_STEP1, N_Q = 75, 16
N_EVAL = 32
ES = ["L1", "L2", "L3", "L4", "L5", "A1", "A2", "A3", "A4", "A5"]
FF = ["F1", "F2", "F3", "F4", "F5"]
LOOKUP = {"A1", "A2"}
DECISIVE = {"STOP_TEACHER", "STOP_TR", "STOP_INTERFACE", "STOP_SPAN", "OPEN"}


def rng_for(*key):
    return np.random.default_rng(zlib.crc32(repr((42,) + key).encode()))


def bounds(x):  # x: (..., n) -> one-sided 95% t bounds over the last axis
    n = x.shape[-1]
    m = x.mean(-1)
    se = x.std(-1, ddof=1) / math.sqrt(n)
    t = stats.t.ppf(0.95, n - 1)
    return m, m - t * se, m + t * se


def step1(rng, gaps: np.ndarray, p_shuf=0.35, sd_ep=0.15):
    """gaps: (n_fam,). Returns eligible (REPS, n_fam) under Holm at one-sided 0.05 over all families."""
    n_fam = len(gaps)
    re = rng.normal(0, sd_ep, (REPS, n_fam, N_EP_STEP1))
    ps = np.clip(p_shuf + re, 0.01, 0.99)
    pg = np.clip(p_shuf + gaps[None, :, None] + re, 0.01, 0.99)
    d = (rng.binomial(N_Q, pg) - rng.binomial(N_Q, ps)) / N_Q
    est = d.mean(-1)
    se = d.std(-1, ddof=1) / math.sqrt(N_EP_STEP1)
    tval = np.where(se > 0, est / np.maximum(se, 1e-12), 0.0)
    p = stats.t.sf(tval, N_EP_STEP1 - 1)
    order = np.argsort(p, axis=1)
    p_sorted = np.take_along_axis(p, order, axis=1)
    thresh = 0.05 / (n_fam - np.arange(n_fam))[None, :]
    ok_sorted = np.cumprod(p_sorted <= thresh, axis=1).astype(bool)
    rejected = np.zeros_like(ok_sorted)
    np.put_along_axis(rejected, order, ok_sorted, axis=1)
    return rejected & (est >= 0.10)


def run_scenario(name: str, sc: dict, sd_d: float, sd_e: float, n_eval: int = N_EVAL) -> dict:
    rng = rng_for(name, sd_d, sd_e, n_eval)
    gaps = np.array([sc["gap_es"].get(f, 0.0) for f in ES] + [sc.get("gap_ff", 0.2)] * len(FF))
    elig = step1(rng, gaps)[:, : len(ES)]  # (REPS, 10)
    n_elig = elig.sum(1)
    verdict = np.full(REPS, "", dtype=object)
    verdict[n_elig < 4] = "STOP_TEACHER"
    # placebo test (episode-specificity) on eligible families
    mu_res = np.array([sc["mu_res"].get(f, sc["mu_res_default"]) for f in ES])
    dres = mu_res[None, :, None] + rng.normal(0, 0.10, (REPS, len(ES), 1)) + rng.normal(0, sc.get("sd_res", 0.4), (REPS, len(ES), n_eval))
    _, dres_lo, _ = bounds(dres)
    es_pass = elig & (dres_lo > 0.10)
    n_es = es_pass.sum(1)
    verdict[(verdict == "") & (n_es < 4)] = "STOP_TR"
    # capacity on episode-specific families
    mu_e = np.array([sc["mu_e"].get(f, sc["mu_e_default"]) for f in ES])
    e = mu_e[None, :, None] + rng.normal(0, 0.10, (REPS, len(ES), 1)) + rng.normal(0, sd_e, (REPS, len(ES), n_eval))
    _, e_lo, e_hi = bounds(e)
    cap_ok = es_pass & (e_lo >= 0.50)
    cap_low = es_pass & (e_hi < 0.50)
    n_ok = cap_ok.sum(1)
    cap_pass = n_ok >= np.ceil(0.75 * n_es)
    cap_stop = cap_low.sum(1) >= np.ceil(0.5 * n_es)
    undecided = verdict == ""
    verdict[undecided & ~cap_pass & cap_stop] = "STOP_INTERFACE"
    verdict[undecided & ~cap_pass & ~cap_stop] = "INCONCLUSIVE_CAPACITY"
    # span on CAP_OK families
    mu_d = np.array([0.0 if f in LOOKUP else sc["mu_d_default"] for f in ES])
    fam_sd = np.array([0.02 if f in LOOKUP else sc.get("sd_family_d", 0.05) for f in ES])
    d = mu_d[None, :, None] + rng.normal(0, 1, (REPS, len(ES), 1)) * fam_sd[None, :, None] + rng.normal(0, sd_d, (REPS, len(ES), n_eval))
    d_m, d_lo, d_hi = bounds(d)
    lookup_mask = np.array([f in LOOKUP for f in ES])[None, :]
    # lookup families are SPAN_VACUOUS by construction (their probes are the demonstrated names; S1v2 I1 0.04-0.06):
    # they are not counted in the span verdict and serve only as the OPEN guard
    span_ok = cap_ok & ~lookup_mask
    n_span = span_ok.sum(1)
    tie = span_ok & (d_hi <= 0.05)
    gap = span_ok & (d_m >= 0.10) & (d_lo > 0.02)
    lookup_ok = ~np.any(cap_ok & lookup_mask & (d_m > 0.05), axis=1)
    # STOP_SPAN (v2): n_ok >= 3, no GAP family, and the one-sided 95% upper bound of the across-family mean of the
    # family D_span means (t over CAP_OK families, df n_ok - 1) at most 0.05; wave 1's count rule is reported beside it
    fam_mean = np.where(span_ok, d_m, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        mbar = np.nanmean(fam_mean, axis=1)
        sbar = np.nanstd(fam_mean, axis=1, ddof=1)
        tq = stats.t.ppf(0.95, np.maximum(n_span - 1, 1))
        ub = mbar + tq * sbar / np.sqrt(np.maximum(n_span, 1))
    stop_span = (n_span >= 3) & (gap.sum(1) == 0) & (ub <= 0.05)
    stop_span_v1_count_rule = (n_span >= 3) & (tie.sum(1) >= np.ceil(0.75 * n_span))
    open_ = (gap.sum(1) >= np.maximum(2, np.ceil(0.5 * n_span))) & lookup_ok & ~stop_span
    undecided = verdict == ""
    verdict[undecided & stop_span] = "STOP_SPAN"
    verdict[undecided & open_] = "OPEN"
    verdict[undecided & ~stop_span & ~open_] = "INCONCLUSIVE_SPAN"
    counts = {v: round(float(np.mean(verdict == v)), 4) for v in sorted(set(verdict))}
    pre_span = (n_elig >= 4) & (n_es >= 4) & cap_pass
    v1_rule = round(float(np.mean(pre_span & stop_span_v1_count_rule)), 4)
    correct = sc["correct"]
    return {"scenario": name, "sd_episode_D": sd_d, "sd_episode_E": sd_e, "n_eval_episodes": n_eval,
            "correct_verdict": correct, "P_correct": counts.get(correct, 0.0),
            "P_decisive": round(float(np.mean([v in DECISIVE for v in verdict])), 4),
            "P_wrong_decisive": round(float(np.mean([(v in DECISIVE) and v != correct for v in verdict])), 4),
            "verdict_distribution": counts, "P_STOP_SPAN_under_v1_count_rule": v1_rule}


SCENARIOS = {
    "weak_teacher": {"gap_es": {"L3": 0.15, "A3": 0.15}, "mu_res": {}, "mu_res_default": 0.8,
                     "mu_e": {}, "mu_e_default": 0.75, "mu_d_default": 0.0, "correct": "STOP_TEACHER"},
    "task_recognition": {"gap_es": {f: 0.20 for f in ES[:8]}, "mu_res": {}, "mu_res_default": 0.0,
                         "mu_e": {}, "mu_e_default": 0.75, "mu_d_default": 0.0, "correct": "STOP_TR"},
    "low_capacity": {"gap_es": {f: 0.20 for f in ES[:8]}, "mu_res": {}, "mu_res_default": 0.8,
                     "mu_e": {}, "mu_e_default": 0.30, "mu_d_default": 0.0, "correct": "STOP_INTERFACE"},
    "tie": {"gap_es": {f: 0.20 for f in ES[:8]}, "mu_res": {}, "mu_res_default": 0.8,
            "mu_e": {}, "mu_e_default": 0.75, "mu_d_default": 0.0, "correct": "STOP_SPAN"},
    "tie_negative": {"gap_es": {f: 0.20 for f in ES[:8]}, "mu_res": {}, "mu_res_default": 0.8,
                     "mu_e": {}, "mu_e_default": 0.75, "mu_d_default": -0.02, "correct": "STOP_SPAN"},
    "gap": {"gap_es": {f: 0.20 for f in ES[:8]}, "mu_res": {}, "mu_res_default": 0.8,
            "mu_e": {}, "mu_e_default": 0.75, "mu_d_default": 0.20, "correct": "OPEN"},
    "small_gap": {"gap_es": {f: 0.20 for f in ES[:8]}, "mu_res": {}, "mu_res_default": 0.8,
                  "mu_e": {}, "mu_e_default": 0.65, "mu_d_default": 0.12, "correct": "OPEN"},
}


def main() -> int:
    rows = []
    for name, sc in SCENARIOS.items():
        for sd_d in (0.05, 0.10, 0.20):
            for sd_e in (0.15, 0.30):
                rows.append(run_scenario(name, sc, sd_d, sd_e))
    for name in ("tie", "tie_negative", "gap"):  # the variance rule's extra 32 episodes (demonstration seed 45)
        rows.append(run_scenario(name, SCENARIOS[name], 0.20, 0.15, n_eval=64))
    for name in ("tie", "tie_negative", "gap", "small_gap"):  # the 32-probe branch: 24 evaluation episodes per family
        for sd_d, sd_e in ((0.10, 0.15), (0.20, 0.30)):
            rows.append(run_scenario(name, SCENARIOS[name], sd_d, sd_e, n_eval=24))
    central = [r for r in rows if r["sd_episode_D"] == 0.10 and r["sd_episode_E"] == 0.15 and r["n_eval_episodes"] == 32]
    noisy = [r for r in rows if r["sd_episode_D"] == 0.20 and r["sd_episode_E"] == 0.30 and r["n_eval_episodes"] == 32]
    n24 = [r for r in rows if r["n_eval_episodes"] == 24]
    summary = {
        "n32_branch_24_eval_episodes": {f'{r["scenario"]} sd_D {r["sd_episode_D"]} sd_E {r["sd_episode_E"]}': r["P_correct"] for r in n24},
        "central_noise (sd_D 0.10, sd_E 0.15)": {r["scenario"]: r["P_correct"] for r in central},
        "central_min_P_correct": min(r["P_correct"] for r in central),
        "central_mean_P_correct": round(float(np.mean([r["P_correct"] for r in central])), 4),
        "central_max_P_wrong_decisive": max(r["P_wrong_decisive"] for r in central),
        "high_noise (sd_D 0.20, sd_E 0.30)": {r["scenario"]: r["P_correct"] for r in noisy},
        "high_noise_mean_P_correct": round(float(np.mean([r["P_correct"] for r in noisy])), 4),
        "high_noise_max_P_wrong_decisive": max(r["P_wrong_decisive"] for r in noisy),
    }
    payload = {"check": "E4 gate repair S2v2: v2 decision path end to end (simulation)",
               "claim_boundary": "assumed noise SDs; instrument gates assumed passed (their rates are in S1v2)",
               "reps": REPS, "families": {"episode_specific": ES, "fixed_function": FF, "lookup": sorted(LOOKUP)},
               "design_seed": 42, "numpy": np.__version__, "scipy": __import__("scipy").__version__,
               "summary": summary, "rows": rows}
    text = json.dumps(payload, indent=1, sort_keys=True)
    payload["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    with open(sys.argv[1], "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for r in rows:
        print(r["scenario"], r["sd_episode_D"], r["sd_episode_E"], r["n_eval_episodes"], "P_correct", r["P_correct"],
              "P_decisive", r["P_decisive"], "P_wrong", r["P_wrong_decisive"], r["verdict_distribution"],
              "v1_count_rule_STOP_SPAN", r["P_STOP_SPAN_under_v1_count_rule"])
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
