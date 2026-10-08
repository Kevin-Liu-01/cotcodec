"""Operating characteristics of q2-stage1-rescoped-v1 Stage S1a (CPU only, seeded).

Generative model (per size z in {4B, 9B}, task t, harness h in {OSW, GA}, session s, rerun j):
  logit p = mu_z + a_tz + c_hz + b_thz + g_sz + e_tsz + f_thsz,  y ~ Bernoulli(p)
  a_tz: task difficulty, N(0, sa^2), correlation rho_a across sizes; c_hz = -/+ delta/2;
  b_thz: task x harness, N(0, sb^2); g_sz: session shift; e_tsz: task x session, N(0, se^2);
  f_thsz: task x harness x session, N(0, sf^2).
Estimators are those registered in program/preregistrations/q2-stage1-rescoped-v1.md section 9.
Usage: python sim_s1a.py [nsim] [nperm]  -> JSON on stdout.
"""

from __future__ import annotations

import json
import math
import sys

import numpy as np
from scipy import stats

RNG = np.random.default_rng(20261008)
Z95, Z80 = 1.6448536, 0.8416212


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def calibrate_mu(p, sa):
    z = np.random.default_rng(1).normal(0, sa, 400000)
    lo, hi = -20.0, 20.0
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if expit(mid + z).mean() < p else (lo, mid)
    return 0.5 * (lo + hi)


def simulate(
    nsim, K, S, r, mus, sa, delta=(0.0, 0.0), sb=0.0, shift=0.0, sg=0.0, se=0.0, sf=0.0, rho_a=0.8
):
    Zs = len(mus)
    a0 = RNG.normal(0, sa, (nsim, 1, K, 1, 1, 1))
    a = rho_a * a0 + RNG.normal(0, sa * math.sqrt(1 - rho_a**2), (nsim, Zs, K, 1, 1, 1))
    mu = np.array(mus).reshape(1, Zs, 1, 1, 1, 1)
    c = np.zeros((1, Zs, 1, 2, 1, 1))
    for i, d in enumerate(delta[:Zs]):
        c[0, i, 0, 0], c[0, i, 0, 1] = -d / 2, d / 2
    lin = mu + a + c
    if sb:
        lin = lin + RNG.normal(0, sb, (nsim, Zs, K, 2, 1, 1))
    if sg:
        lin = lin + RNG.normal(0, sg, (nsim, Zs, 1, 1, S, 1))
    if shift:
        sh = np.zeros((1, 1, 1, 1, S, 1))
        sh[..., 0, 0], sh[..., 1, 0] = -shift / 2, shift / 2
        lin = lin + sh
    if se:
        lin = lin + RNG.normal(0, se, (nsim, Zs, K, 1, S, 1))
    if sf:
        lin = lin + RNG.normal(0, sf, (nsim, Zs, K, 2, S, 1))
    p = expit(lin)
    y = (RNG.random((nsim, Zs, K, 2, S, r)) < p).astype(np.int8)
    return y, p


def cell_means(y):
    return y.mean(axis=-1)  # (nsim, Z, K, H, S)


def delta_t(y):
    m = cell_means(y)
    return (m[:, :, :, 1, :] - m[:, :, :, 0, :]).mean(axis=-1)  # (nsim, Z, K)


def x_session_aware(y):
    """Unbiased task x harness excess: mean over tasks of the mean over ordered session pairs
    s != s'
    of d_ts * d_ts', d_ts = harness difference of the session means (S = 2: d_t1 * d_t2)."""
    m = cell_means(y)
    d = m[:, :, :, 1, :] - m[:, :, :, 0, :]  # (nsim, Z, K, S)
    S = d.shape[-1]
    tot = d.sum(-1) ** 2 - (d**2).sum(-1)
    return (tot / (S * (S - 1))).mean(-1)  # (nsim, Z)


def x_bernoulli(y):
    """Design A's correction: treats all S*r reruns as independent Bernoulli draws."""
    n = y.shape[-1] * y.shape[-2]
    ph = y.reshape(*y.shape[:4], n).mean(-1)
    v = ph * (1 - ph) / (n - 1)
    return ((ph[..., 1] - ph[..., 0]) ** 2 - v[..., 0] - v[..., 1]).mean(-1)


def discordance(y):
    """D_b: cross-session rerun pairs; D_w: same-session pairs. Means over (task, harness)."""
    S, r = y.shape[-2], y.shape[-1]
    nb = []
    for s1 in range(S):
        for s2 in range(s1 + 1, S):
            a, b = y[..., s1, :], y[..., s2, :]
            nb.append((a[..., :, None] != b[..., None, :]).mean(axis=(-1, -2)))
    Db = np.mean(nb, axis=0).mean(axis=(2, 3))
    Dw = None
    if r >= 2:
        nw = [(y[..., j1] != y[..., j2]).mean(-1) for j1 in range(r) for j2 in range(j1 + 1, r)]
        Dw = np.mean(nw, axis=0).mean(axis=(2, 3))
    return Db, Dw


def paired_t_p(x):
    K = x.shape[-1]
    m, sd = x.mean(-1), x.std(-1, ddof=1)
    t = np.where(sd > 0, m / (sd / math.sqrt(K) + 1e-15), 0.0)
    return 2 * stats.t.sf(np.abs(t), K - 1), sd / math.sqrt(K)


def perm_x_p(y, nperm, xfun):
    """Permute harness labels within task x session; one-sided p for the pooled X."""
    nsim, Zs, K, H, S, r = y.shape
    obs = xfun(y).mean(1)
    ep = np.transpose(y, (0, 1, 2, 4, 3, 5)).reshape(nsim, Zs, K, S, H * r)
    cnt = np.zeros(nsim)
    for _ in range(nperm):
        idx = np.argsort(RNG.random(ep.shape), axis=-1)
        pe = (
            np.take_along_axis(ep, idx, -1)
            .reshape(nsim, Zs, K, S, H, r)
            .transpose(0, 1, 2, 4, 3, 5)
        )
        cnt += xfun(pe).mean(1) >= obs - 1e-12
    return (cnt + 1) / (nperm + 1)


def perm_session_p(y, nperm):
    """Per size: permute session labels within (task, harness); stat = mean(S2 minus S1)."""
    nsim, Zs, K, H, S, r = y.shape
    flat = y.reshape(nsim, Zs, K, H, S * r).astype(float)

    def stat(v):
        return v[..., r:].mean(-1).mean(axis=(2, 3)) - v[..., :r].mean(-1).mean(axis=(2, 3))

    obs = stat(flat)
    cnt = np.zeros((nsim, Zs))
    for _ in range(nperm):
        idx = np.argsort(RNG.random(flat.shape), axis=-1)
        cnt += np.abs(stat(np.take_along_axis(flat, idx, -1))) >= np.abs(obs) - 1e-12
    return (cnt + 1) / (nperm + 1)


def true_quantities(mus, sa, delta=(0.0, 0.0), sb=0.0, n=200000, rho_a=0.8):
    rng = np.random.default_rng(7)
    out = []
    for i, mu in enumerate(mus):
        a = rng.normal(0, sa, n)
        b = rng.normal(0, sb, (n, 2)) if sb else np.zeros((n, 2))
        p0, p1 = expit(mu + a - delta[i] / 2 + b[:, 0]), expit(mu + a + delta[i] / 2 + b[:, 1])
        X = float(((p1 - p0) ** 2).mean())
        D = float(
            (p0 * (1 - p0) + p1 * (1 - p1)).mean()
        )  # = 2 * mean p(1-p) over harnesses / 2 * 2
        out.append(
            {
                "success": float(0.5 * (p0 + p1).mean()),
                "delta_pp": float((p1 - p0).mean()),
                "X": X,
                "D": D,
                "pi": (X / 4) / (X / 4 + D / 2),
            }
        )
    return out


def mde(xs, ps, target=0.8):
    for i in range(1, len(xs)):
        if ps[i - 1] < target <= ps[i]:
            f = (target - ps[i - 1]) / (ps[i] - ps[i - 1])
            return round(xs[i - 1] + f * (xs[i] - xs[i - 1]), 4)
    return None


SCEN = {
    "literature": dict(p=(0.15, 0.30), sa=3.5),
    "high_noise": dict(p=(0.15, 0.30), sa=2.5),
    "low_base": dict(p=(0.08, 0.20), sa=3.5),
    "opencua_calibrated": dict(p=(0.18, 0.243), sa=6.9),
}


def run(nsim, nperm):
    res = {"seed": 20261008, "nsim": nsim, "nperm": nperm, "rows": []}
    S, r = 2, 2
    for sname, sc in SCEN.items():
        mus = [calibrate_mu(p, sc["sa"]) for p in sc["p"]]
        tq0 = true_quantities(mus, sc["sa"])
        for K in (16, 32, 48, 64, 116):
            if sname != "literature" and K not in (32, 64):
                continue
            row = {"scenario": sname, "K": K, "episodes": K * 16, "true_null": tq0}
            y, _ = simulate(nsim, K, S, r, mus, sc["sa"], sg=0.1, se=0.3)
            d = delta_t(y)
            p_pool, se_pool = paired_t_p(d.mean(1))
            row["type1_delta_pooled"] = float((p_pool < 0.05).mean())
            row["delta_pooled_90ci_halfwidth_pp"] = float(
                np.median(stats.t.ppf(0.95, K - 1) * se_pool) * 100
            )
            Db, Dw = discordance(y)
            row["Db_pooled_sd_pp"] = float(Db.mean(1).std() * 100)
            row["Db_per_size_sd_pp"] = [float(Db[:, 0].std() * 100), float(Db[:, 1].std() * 100)]
            row["Db_minus_Dw_sd_pp"] = float((Db - Dw).mean(1).std() * 100)
            k = sc["sa"] / 3.5
            grid = tuple(k * g for g in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0))
            pw, pp, pw4, pp4, pw9, pp9 = [], [], [], [], [], []
            for dl in grid:
                y, _ = simulate(nsim, K, S, r, mus, sc["sa"], delta=(dl, dl), sg=0.1, se=0.3)
                d = delta_t(y)
                tq = true_quantities(mus, sc["sa"], (dl, dl))
                pw.append(float((paired_t_p(d.mean(1))[0] < 0.05).mean()))
                pp.append(100 * 0.5 * (tq[0]["delta_pp"] + tq[1]["delta_pp"]))
                pw4.append(float((paired_t_p(d[:, 0])[0] < 0.05).mean()))
                pp4.append(100 * tq[0]["delta_pp"])
                pw9.append(float((paired_t_p(d[:, 1])[0] < 0.05).mean()))
                pp9.append(100 * tq[1]["delta_pp"])
            row["delta_MDE80_pp"] = {
                "pooled": mde(pp, pw),
                "4B": mde(pp4, pw4),
                "9B": mde(pp9, pw9),
            }
            if sname == "literature" and K in (32, 64):
                sc_pw, sc_pp = [], []
                for dl in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
                    y, _ = simulate(nsim, K, S, r, mus, sc["sa"], delta=(dl, 0.0), sg=0.1, se=0.3)
                    d = delta_t(y)
                    sc_pw.append(float((paired_t_p(d[:, 0] - d[:, 1])[0] < 0.05).mean()))
                    sc_pp.append(100 * true_quantities(mus, sc["sa"], (dl, 0.0))[0]["delta_pp"])
                row["scale_contrast_MDE80_pp"] = mde(sc_pp, sc_pw)
            if K in (32, 64):
                nx = min(nsim, 500)
                xs = {}
                for sb in (0.0, 1.0 * k, 1.5 * k):
                    for sf in (0.0, 0.5) if sb == 0.0 else (0.0,):
                        y, _ = simulate(nx, K, S, r, mus, sc["sa"], sb=sb, sg=0.1, se=0.3, sf=sf)
                        tq = true_quantities(mus, sc["sa"], sb=sb)
                        xa = x_session_aware(y).mean(1)
                        xb = x_bernoulli(y).mean(1)
                        Db, _ = discordance(y)
                        pi_hat = (x_session_aware(y) / 4) / (x_session_aware(y) / 4 + Db / 2)
                        key = f"sb={sb},sf={sf}"
                        xs[key] = {
                            "X_true_pooled": round(0.5 * (tq[0]["X"] + tq[1]["X"]), 5),
                            "rms_pp": round(100 * math.sqrt(0.5 * (tq[0]["X"] + tq[1]["X"])), 2),
                            "pi_true": [round(tq[0]["pi"], 4), round(tq[1]["pi"], 4)],
                            "X_session_aware_mean": round(float(xa.mean()), 5),
                            "X_bernoulli_mean": round(float(xb.mean()), 5),
                            "pi_hat_mean": [
                                round(float(pi_hat[:, 0].mean()), 4),
                                round(float(pi_hat[:, 1].mean()), 4),
                            ],
                            "pi_hat_sd": [
                                round(float(pi_hat[:, 0].std()), 4),
                                round(float(pi_hat[:, 1].std()), 4),
                            ],
                            "power_perm_session_aware": float(
                                (perm_x_p(y, nperm, x_session_aware) < 0.05).mean()
                            ),
                            "power_perm_bernoulli": float(
                                (perm_x_p(y, nperm, x_bernoulli) < 0.05).mean()
                            ),
                        }
                row["X"] = xs
                ns = min(nsim, 500)
                sess = {}
                for shift in (0.0, 0.5, 0.75):
                    y, p = simulate(ns, K, S, r, mus, sc["sa"], shift=shift, se=0.3)
                    gap = float(100 * (p[..., 1, 0].mean() - p[..., 0, 0].mean()))
                    pv = perm_session_p(y, nperm)
                    sess[str(shift)] = {
                        "gap_pp": round(gap, 2),
                        "power_per_size": [
                            float((pv[:, 0] < 0.05).mean()),
                            float((pv[:, 1] < 0.05).mean()),
                        ],
                    }
                row["session_shift"] = sess
            res["rows"].append(row)
            print(
                json.dumps({k: row[k] for k in row if k != "true_null"}),
                file=sys.stderr,
                flush=True,
            )
    return res


def anchor_oc(nsim=4000):
    """OpenCUA-7B anchor: 116 tasks, three public runs plus ours, all exchangeable under H0
    (OpenCUA-calibrated model: success 24.3%, task SD 6.9 logit). Kill if ours lies more than
    2 paired-bootstrap SE outside [min, max] of the three public runs' success on the same tasks."""
    mu = calibrate_mu(0.243, 6.9)
    out = {}
    for n_ours in (116, 72, 58):
        for shift in (0.0, -0.5, -1.0, -1.5, -2.0, -3.0):
            a = RNG.normal(0, 6.9, (nsim, 116))
            pub = RNG.random((nsim, 3, 116)) < expit(mu + a)[:, None, :]
            ours = RNG.random((nsim, 116)) < expit(mu + a + shift)
            pub, ours = pub[:, :, :n_ours].astype(float), ours[:, :n_ours].astype(float)
            dt = ours - pub.mean(1)
            se = dt.std(1, ddof=1) / math.sqrt(n_ours)
            ps, po = pub.mean(2), ours.mean(1)
            kill = (po < ps.min(1) - 2 * se) | (po > ps.max(1) + 2 * se)
            gap = float(100 * (expit(mu + a + shift).mean() - expit(mu + a).mean()))
            out[f"n={n_ours},shift={shift}"] = {
                "gap_pp": round(gap, 2),
                "P_kill": float(kill.mean()),
                "median_2se_pp": round(float(np.median(2 * se) * 100), 2),
            }
    return out


def ladder_m(nsim=1500):
    """Indicative M: smallest 4B harness share whose full shrinkage (large rungs at share 0) a
    harness-only ladder of 60 tasks x 4 sessions x 1 rerun per rung detects with 80% power
    (one-sided 5%, normal approximation on the simulated SD of the contrast)."""
    out = {}
    for name, (p4, pl, sa) in {
        "literature": (0.15, 0.40, 3.5),
        "opencua_calibrated": (0.18, 0.35, 6.9),
    }.items():
        mus = [calibrate_mu(p4, sa), calibrate_mu(pl, sa), calibrate_mu(pl, sa)]
        rows = []
        for sb in tuple(sa / 3.5 * g for g in (0.0, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5)):
            y4, _ = simulate(nsim, 60, 4, 1, [mus[0]], sa, sb=sb, sg=0.1, se=0.3, rho_a=1.0)
            yl, _ = simulate(nsim, 60, 4, 1, mus[1:], sa, sg=0.1, se=0.3)

            def pi(y):
                X = x_session_aware(y)
                Db, _ = discordance(y)
                return (X / 4) / (X / 4 + Db / 2)

            con = pi(y4)[:, 0] - pi(yl).mean(1)
            tq = true_quantities([mus[0]], sa, sb=sb)[0]
            rows.append(
                {
                    "sb": sb,
                    "pi4_true": round(tq["pi"], 4),
                    "contrast_mean": round(float(con.mean()), 4),
                    "contrast_sd": round(float(con.std()), 4),
                    "detectable": bool(tq["pi"] >= (Z95 + Z80) * float(con.std())),
                }
            )
        m = next((rw["pi4_true"] for rw in rows if rw["detectable"] and rw["pi4_true"] > 0), None)
        out[name] = {"rows": rows, "indicative_M": m}
    return out


if __name__ == "__main__":
    nsim = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    nperm = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    res = run(nsim, nperm)
    res["anchor_oc"] = anchor_oc()
    res["ladder_indicative_M"] = ladder_m()
    print(json.dumps(res, indent=1))
