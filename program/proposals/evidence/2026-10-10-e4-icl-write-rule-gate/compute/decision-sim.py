#!/usr/bin/env python3
"""E4 gate, CPU check S2: operating characteristics of the registered decision rules.

Simulates the draft registration's three decision layers under assumed noise:

* eligibility (Step 1): per-family label-dependence gap G_LD = acc(gold) -
  acc(shuffled) over 3 demonstration seeds x 25 episodes x 16 queries, with
  episode random effects; eligible when G_LD >= 0.10 and the one-sided
  cluster-t lower bound (clusters = episodes) is above 0 after Holm over 14
  families (one-sided alpha 0.05 family-wise);
* capacity (Step 2): per-family episode-specific recovered fraction E_free on
  32 evaluation episodes; CAP_OK when the one-sided 95% lower bound >= 0.50,
  CAP_LOW when the upper bound < 0.50; gate CAPACITY_PASS when CAP_OK holds in
  at least ceil(0.75 n) families, CAPACITY_STOP when CAP_LOW holds in at least
  ceil(0.5 n) families, else INCONCLUSIVE;
* span (Step 2): per CAP_OK family, the paired shortfall D_span = E_free -
  E_span(B); TIE when its one-sided 95% upper bound <= 0.05; GAP when the
  point estimate >= 0.10 and the one-sided 95% lower bound > 0.02; gate
  STOP_SPAN when TIE holds in at least ceil(0.75 n_ok) families (n_ok >= 3),
  OPEN when GAP holds in at least max(2, ceil(0.5 n_ok)) families, else
  INCONCLUSIVE_SPAN.

Every noise SD is an assumption until the pilot measures it; the output is a
sensitivity table, not a power claim. Seeds: every scenario's generator is
seeded from CRC32 of its key; design seed 42.

Usage: python decision-sim.py <out.json>
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import zlib

import numpy as np
from scipy import stats

REPS = 4000
N_EVAL_EP = 32


def rng_for(*key: object) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32(repr((42,) + key).encode()))


# ---------------------------------------------------------------- eligibility
def eligibility(gap: float, p_shuf: float, sd_ep: float, n_fam: int = 14) -> dict:
    """P(a family with true gap is declared eligible), Holm over n_fam (others null)."""
    rng = rng_for("elig", gap, p_shuf, sd_ep)
    n_ep, n_q = 75, 16  # 3 seeds x 25 episodes, 16 queries per episode
    hits = 0
    for _ in range(REPS // 4):
        # target family plus n_fam - 1 null families for the Holm step
        gaps = np.array([gap] + [0.0] * (n_fam - 1))
        pvals, ests = [], []
        for g in gaps:
            re = rng.normal(0, sd_ep, n_ep)
            ps = np.clip(p_shuf + re, 0.01, 0.99)
            pg = np.clip(p_shuf + g + re, 0.01, 0.99)
            acc_s = rng.binomial(n_q, ps) / n_q
            acc_g = rng.binomial(n_q, pg) / n_q
            d = acc_g - acc_s
            est = d.mean()
            se = d.std(ddof=1) / math.sqrt(n_ep)
            t = est / se if se > 0 else 0.0
            pvals.append(stats.t.sf(t, n_ep - 1))
            ests.append(est)
        order = np.argsort(pvals)
        rejected = np.zeros(n_fam, bool)
        for rank, idx in enumerate(order):
            if pvals[idx] <= 0.05 / (n_fam - rank):
                rejected[idx] = True
            else:
                break
        if rejected[0] and ests[0] >= 0.10:
            hits += 1
    return {"true_gap": gap, "p_shuffled": p_shuf, "episode_sd": sd_ep,
            "p_eligible": round(hits / (REPS // 4), 4)}


# ---------------------------------------------------------------- capacity and span
def family_bounds(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """x: (reps, fam, ep). One-sided 95% t bounds per family (df = ep - 1)."""
    m = x.mean(-1)
    se = x.std(-1, ddof=1) / math.sqrt(x.shape[-1])
    tq = stats.t.ppf(0.95, x.shape[-1] - 1)
    return m, m - tq * se, m + tq * se


def capacity_span(n_fam: int, mu_e: float, sd_fam_e: float, sd_ep_e: float,
                  mu_d: float, sd_fam_d: float, sd_ep_d: float) -> dict:
    rng = rng_for("cap", n_fam, mu_e, sd_fam_e, sd_ep_e, mu_d, sd_fam_d, sd_ep_d)
    fam_e = rng.normal(mu_e, sd_fam_e, (REPS, n_fam, 1))
    fam_d = np.clip(rng.normal(mu_d, sd_fam_d, (REPS, n_fam, 1)), 0, None)
    e = fam_e + rng.normal(0, sd_ep_e, (REPS, n_fam, N_EVAL_EP))
    d = fam_d + rng.normal(0, sd_ep_d, (REPS, n_fam, N_EVAL_EP))
    _, e_lo, e_hi = family_bounds(e)
    cap_ok = e_lo >= 0.50
    cap_low = e_hi < 0.50
    n_ok = cap_ok.sum(1)
    cap_pass = n_ok >= math.ceil(0.75 * n_fam)
    cap_stop = cap_low.sum(1) >= math.ceil(0.5 * n_fam)
    d_m, d_lo, d_hi = family_bounds(d)
    tie = (d_hi <= 0.05) & cap_ok
    gap = (d_m >= 0.10) & (d_lo > 0.02) & cap_ok
    n_tie = tie.sum(1)
    n_gap = gap.sum(1)
    need_tie = np.ceil(0.75 * n_ok)
    need_gap = np.maximum(2, np.ceil(0.5 * n_ok))
    stop_span = cap_pass & (n_ok >= 3) & (n_tie >= need_tie)
    open_ = cap_pass & (n_gap >= need_gap) & ~stop_span
    return {
        "n_es_families": n_fam, "mu_E_free": mu_e, "sd_family_E": sd_fam_e, "sd_episode_E": sd_ep_e,
        "mu_D_span": mu_d, "sd_family_D": sd_fam_d, "sd_episode_D": sd_ep_d,
        "P_capacity_pass": round(float(cap_pass.mean()), 4),
        "P_capacity_stop": round(float((cap_stop & ~cap_pass).mean()), 4),
        "P_stop_span": round(float(stop_span.mean()), 4),
        "P_open": round(float(open_.mean()), 4),
        "P_inconclusive_span_given_capacity_pass": round(
            float(((~stop_span) & (~open_) & cap_pass).sum() / max(1, cap_pass.sum())), 4),
    }


def main() -> int:
    elig = [eligibility(g, ps, sd) for g in (0.0, 0.05, 0.10, 0.15, 0.20)
            for ps in (0.2, 0.5) for sd in (0.10, 0.20)]
    cap = []
    for n in (4, 6, 9):
        for mu_e in (0.30, 0.45, 0.60, 0.75):
            for sd_ep_e in (0.15, 0.30):
                for mu_d in (0.0, 0.05, 0.10, 0.20):
                    for sd_ep_d in (0.05, 0.10, 0.20):
                        for sd_fam_d in (0.0, 0.05):
                            cap.append(capacity_span(n, mu_e, 0.10, sd_ep_e, mu_d, sd_fam_d, sd_ep_d))
    payload = {
        "check": "E4 gate S2: decision-rule operating characteristics (simulation)",
        "claim_boundary": "assumed noise SDs; a sensitivity table for the draft registration's thresholds, not a measured power",
        "reps": REPS, "n_eval_episodes_per_family": N_EVAL_EP, "design_seed": 42,
        "numpy": np.__version__, "scipy": __import__("scipy").__version__,
        "eligibility": elig, "capacity_and_span": cap,
    }
    text = json.dumps(payload, sort_keys=True)
    payload["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    with open(sys.argv[1], "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for row in elig:
        print("elig", row)
    for row in cap:
        if row["sd_family_D"] == 0.05 and row["sd_episode_E"] == 0.15:
            print("cap", {k: row[k] for k in ("n_es_families", "mu_E_free", "mu_D_span", "sd_episode_D",
                                              "P_capacity_pass", "P_capacity_stop", "P_stop_span", "P_open")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
