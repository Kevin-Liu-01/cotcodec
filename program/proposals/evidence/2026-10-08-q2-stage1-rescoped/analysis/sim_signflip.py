"""Add-on to sim_s1a.py: the registered sensitivity X test and the share's sampling SD.

The test is a one-sided sign-flip randomization test on the per-task session-aware products
X_t = d_t1 * d_t2, pooled over sizes.
Usage: python sim_signflip.py [nsim] [nflip] -> JSON on stdout."""

from __future__ import annotations

import json
import math
import sys

import numpy as np
import sim_s1a as S

RNG = np.random.default_rng(20261009)


def xt(y):
    m = S.cell_means(y)
    d = m[:, :, :, 1, :] - m[:, :, :, 0, :]
    return (d[..., 0] * d[..., 1]).mean(1)  # (nsim, K): product per task, mean over sizes


def signflip_p(x, nflip):
    obs = x.mean(-1)
    cnt = np.zeros(x.shape[0])
    for _ in range(nflip):
        sgn = np.where(RNG.random(x.shape) < 0.5, -1.0, 1.0)
        cnt += (x * sgn).mean(-1) >= obs - 1e-12
    return (cnt + 1) / (nflip + 1)


def main():
    nsim = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    nflip = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    out = {"seed": 20261009, "nsim": nsim, "nflip": nflip, "rows": []}
    for sname in ("literature", "opencua_calibrated"):
        sc = S.SCEN[sname]
        k = sc["sa"] / 3.5
        mus = [S.calibrate_mu(p, sc["sa"]) for p in sc["p"]]
        for K in (32, 64, 116):
            if sname != "literature" and K == 116:
                continue
            for sb, sf in (
                (0.0, 0.0),
                (0.0, 0.5 * k),
                (0.75 * k, 0.0),
                (1.0 * k, 0.0),
                (1.5 * k, 0.0),
            ):
                y, _ = S.simulate(nsim, K, 2, 2, mus, sc["sa"], sb=sb, sg=0.1, se=0.3, sf=sf)
                tq = S.true_quantities(mus, sc["sa"], sb=sb)
                X = S.x_session_aware(y)
                Db, _ = S.discordance(y)
                pi = (X / 4) / (X / 4 + Db / 2)
                pi_pool = pi.mean(1)
                out["rows"].append(
                    {
                        "scenario": sname,
                        "K": K,
                        "sb": round(sb, 3),
                        "sf": round(sf, 3),
                        "rms_pp": round(100 * math.sqrt(0.5 * (tq[0]["X"] + tq[1]["X"])), 2),
                        "pi_true": [round(tq[0]["pi"], 4), round(tq[1]["pi"], 4)],
                        "pi_pooled_true": round(0.5 * (tq[0]["pi"] + tq[1]["pi"]), 4),
                        "pi_pooled_hat_mean": round(float(np.nanmean(pi_pool)), 4),
                        "pi_pooled_hat_sd": round(float(np.nanstd(pi_pool)), 4),
                        "power_signflip": float((signflip_p(xt(y), nflip) < 0.05).mean()),
                    }
                )
                print(json.dumps(out["rows"][-1]), file=sys.stderr, flush=True)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
