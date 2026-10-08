"""Operating characteristics of q2-stage1-rescoped-v1 after the pre-freeze review (CPU, seeded).

Every estimator and test is the registered code, imported from harness.q2_stage1.estimators.
The generative model is sim_s1a.py's, with one addition: a harness x session effect common
to every task of a session (kappa, SD sk). Per size z, task t, harness h, session s, rerun j:

  logit p = mu_z + a_tz + c_hz + b_thz + g_sz + kappa_hsz + e_tsz + f_thsz

Sessions are separate per size (sizes run one after the other). Sections:
  size   - size at the null for the delta test, the primary X sign-flip test, the X label
           permutation (sensitivity), the session sign-flip test and the draft's session
           label permutation, across session-noise settings whose D_b - D_w spans 0-10 pp;
  power  - delta MDE, X sign-flip power, session-shift power, interval half-widths;
  dr5    - the ladder's detectable share M on the pi-degree scale (see ladder_m);
  anchor - DR-A operating characteristics at the anchor sizes the plan allows.
Usage: python sim_s1a_v2.py <repo_root> <nsim> <section> -> one section's JSON on stdout
(progress on stderr); sections: size, power:<scenario>, dr5, anchor. Each section seeds its
own generator, numpy.random.default_rng([20261010, SECTION_SEEDS[section]]), so sections run
in parallel reproduce exactly. python sim_s1a_v2.py <repo_root> merge <files...> writes the
combined sim_s1a_v2.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".").resolve()
sys.path.insert(0, str(REPO))
from harness.q2_stage1 import estimators as E  # noqa: E402

NSIM = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "merge" else 2000
SEED = 20261010
SECTION_SEEDS = {
    "size": 1,
    "power:literature": 2,
    "power:high_noise": 3,
    "power:low_base": 4,
    "power:opencua_calibrated": 5,
    "dr5": 6,
    "anchor": 7,
    "dr5_oc": 8,
}
RNG = np.random.default_rng(SEED)
NFLIP, NPERM = 500, 200
Z95, Z80 = 1.6448536, 0.8416212


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def calibrate_mu(p: float, sa: float, sess_sd: float = 0.0) -> float:
    z = np.random.default_rng(1).normal(0, math.sqrt(sa**2 + sess_sd**2), 400000)
    lo, hi = -20.0, 20.0
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if expit(mid + z).mean() < p else (lo, mid)
    return 0.5 * (lo + hi)


def simulate(
    nsim, K, S, r, mus, sa, delta=None, sb=0.0, shift=0.0, sg=0.0, se=0.0, sf=0.0, sk=0.0,
    rho_a=0.8, sb_sizes=None,
):  # fmt: skip
    Zs = len(mus)
    a0 = RNG.normal(0, sa, (nsim, 1, K, 1, 1, 1))
    a = rho_a * a0 + RNG.normal(0, sa * math.sqrt(1 - rho_a**2), (nsim, Zs, K, 1, 1, 1))
    lin = np.array(mus).reshape(1, Zs, 1, 1, 1, 1) + a
    if delta is not None:
        c = np.zeros((1, Zs, 1, 2, 1, 1))
        for i, d in enumerate(delta):
            c[0, i, 0, 0], c[0, i, 0, 1] = -d / 2, d / 2
        lin = lin + c
    if sb:
        b = RNG.normal(0, sb, (nsim, Zs, K, 2, 1, 1))
        if sb_sizes is not None:
            b = b * np.array(sb_sizes, dtype=float).reshape(1, Zs, 1, 1, 1, 1)
        lin = lin + b
    if sg:
        lin = lin + RNG.normal(0, sg, (nsim, Zs, 1, 1, S, 1))
    if sk:
        lin = lin + RNG.normal(0, sk, (nsim, Zs, 1, 2, S, 1))
    if shift:
        sh = np.zeros((1, 1, 1, 1, S, 1))
        sh[..., 0, 0], sh[..., 1, 0] = -shift / 2, shift / 2
        lin = lin + sh
    if se:
        lin = lin + RNG.normal(0, se, (nsim, Zs, K, 1, S, 1))
    if sf:
        lin = lin + RNG.normal(0, sf, (nsim, Zs, K, 2, S, 1))
    p = expit(lin)
    return (RNG.random((nsim, Zs, K, 2, S, r)) < p).astype(float), p


SCEN = {
    "literature": dict(p=(0.15, 0.30), sa=3.5),
    "high_noise": dict(p=(0.15, 0.30), sa=2.5),
    "low_base": dict(p=(0.08, 0.20), sa=3.5),
    "opencua_calibrated": dict(p=(0.18, 0.243), sa=6.9),
}
NOISE = {
    "base (sg 0.1, se 0.3)": dict(sg=0.1, se=0.3),
    "sf 0.5": dict(sg=0.1, se=0.3, sf=0.5),
    "sf 1.0": dict(sg=0.1, se=0.3, sf=1.0),
    "sf 1.5": dict(sg=0.1, se=0.3, sf=1.5),
    "sf 2.0": dict(sg=0.1, se=0.3, sf=2.0),
    "sf 3.0": dict(sg=0.1, se=0.3, sf=3.0),
    "se 1.0": dict(sg=0.1, se=1.0),
    "se 1.5": dict(sg=0.1, se=1.5),
    "se 2.0": dict(sg=0.1, se=2.0),
    "se 3.0": dict(sg=0.1, se=3.0),
    "kappa 0.2": dict(sg=0.1, se=0.3, sk=0.2),
    "kappa 0.3": dict(sg=0.1, se=0.3, sk=0.3),
}


def log(obj):
    print(json.dumps(obj), file=sys.stderr, flush=True)


def rate(p, alpha=0.05):
    return round(float((np.asarray(p) <= alpha).mean()), 4)


def mde(xs, ps, target=0.8):
    for i in range(1, len(xs)):
        if ps[i - 1] < target <= ps[i]:
            f = (target - ps[i - 1]) / (ps[i] - ps[i - 1])
            return round(xs[i - 1] + f * (xs[i] - xs[i - 1]), 2)
    return None


def size_section(K_values=(24, 32)):
    sc = SCEN["literature"]
    mus = [calibrate_mu(p, sc["sa"]) for p in sc["p"]]
    out = []
    for K in K_values:
        for name, nz in NOISE.items():
            y, _ = simulate(NSIM, K, 2, 2, mus, sc["sa"], **nz)
            db, dw = E.d_between(y), E.d_within(y)
            t = E.paired_t(E.task_delta(y))
            p_x = E.x_signflip_p(y, NFLIP, RNG)
            p_s = E.session_signflip_p(y, NFLIP, RNG)
            nperm_sims = min(NSIM, 1000)
            p_xl = E.x_label_permutation_p(y[:nperm_sims], NPERM, RNG)
            p_sl = E.session_label_permutation_p(y[:nperm_sims], NPERM, RNG)
            present = np.minimum(t["p"], p_x) <= 0.025
            row = {
                "K": K,
                "noise": name,
                "Db_minus_Dw_pp": [round(float(v), 2) for v in ((db - dw).mean(0) * 100)],
                "Db_pp": [round(float(v), 2) for v in (db.mean(0) * 100)],
                "size_delta_paired_t": rate(t["p"]),
                "size_x_signflip": rate(p_x),
                "size_x_label_permutation": rate(p_xl),
                "size_session_signflip": [rate(p_s[:, 0]), rate(p_s[:, 1])],
                "size_session_label_permutation": [rate(p_sl[:, 0]), rate(p_sl[:, 1])],
                "dr2_present_rate_holm": round(float(present.mean()), 4),
            }
            out.append(row)
            log(row)
    return out


def power_section(only: str):
    out = {}
    for sname, sc in SCEN.items():
        if sname != only:
            continue
        k = sc["sa"] / 3.5
        mus = [calibrate_mu(p, sc["sa"]) for p in sc["p"]]
        Ks = (24, 32, 64, 116) if sname == "literature" else (24, 32)
        noises = (
            ("base (sg 0.1, se 0.3)", "se 1.5", "sf 1.5")
            if sname == "literature"
            else ("base (sg 0.1, se 0.3)",)
        )
        for K in Ks:
            for nname in noises:
                nz = NOISE[nname]
                key = f"{sname}|K={K}|{nname}"
                row = {}
                grid = tuple(k * g for g in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0))
                pw, pp, pw4, pp4, pw9, pp9 = [], [], [], [], [], []
                for dl in grid:
                    y, p = simulate(NSIM, K, 2, 2, mus, sc["sa"], delta=(dl, dl), **nz)
                    tt = E.paired_t(E.task_delta(y))
                    d_true = (p[..., 1, :, :] - p[..., 0, :, :]).mean(axis=(0, 2, 3, 4))
                    pw.append(float((tt["p"] <= 0.05).mean()))
                    pp.append(100 * float(d_true.mean()))
                    d = E.harness_diff(y).mean(-1)  # (nsim, Z, K)
                    pw4.append(float((E.paired_t(d[:, 0])["p"] <= 0.05).mean()))
                    pp4.append(100 * float(d_true[0]))
                    pw9.append(float((E.paired_t(d[:, 1])["p"] <= 0.05).mean()))
                    pp9.append(100 * float(d_true[1]))
                    if dl == 0.0:
                        row["delta_90ci_halfwidth_pp"] = round(
                            float(np.median(tt["ci_high"] - tt["estimate"]) * 100), 2
                        )
                        db, dw = E.d_between(y), E.d_within(y)
                        row["Db_pooled_sd_pp"] = round(float(db.mean(1).std() * 100), 2)
                        row["Db_per_size_sd_pp"] = [
                            round(float(db[:, i].std() * 100), 2) for i in range(2)
                        ]
                        row["Db_minus_Dw_pooled_sd_pp"] = round(
                            float((db - dw).mean(1).std() * 100), 2
                        )
                        row["Db_minus_Dw_mean_pp"] = [
                            round(float(v), 2) for v in ((db - dw).mean(0) * 100)
                        ]
                        pis = E.pi_small(y)
                        row["pi_small_null_mean_sd"] = [
                            round(float(pis.mean()), 4),
                            round(float(pis.std()), 4),
                        ]
                row["delta_MDE80_pp"] = {
                    "pooled": mde(pp, pw),
                    "4B": mde(pp4, pw4),
                    "9B": mde(pp9, pw9),
                }
                if sname == "literature" and K in (24, 32) and nname.startswith("base"):
                    sc_pw, sc_pp = [], []
                    for dl in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
                        y, p = simulate(NSIM, K, 2, 2, mus, sc["sa"], delta=(dl, 0.0), **nz)
                        d = E.harness_diff(y).mean(-1)
                        sc_pw.append(float((E.paired_t(d[:, 0] - d[:, 1])["p"] <= 0.05).mean()))
                        sc_pp.append(100 * float((p[:, 0, :, 1] - p[:, 0, :, 0]).mean()))
                    row["scale_screen_MDE80_pp"] = mde(sc_pp, sc_pw)
                if K in (24, 32):
                    xs = {}
                    sess_sd = math.sqrt(sum(v**2 for v in nz.values()))
                    for g in (0.75, 1.0, 1.5):
                        sb = g * k
                        y, _ = simulate(NSIM, K, 2, 2, mus, sc["sa"], sb=sb, **nz)
                        deg = [degree(m, sc["sa"], sb, sess_sd) for m in mus]
                        rms = 100 * math.sqrt(np.mean([d["X"] for d in deg]))
                        pis = E.pi_small(y)
                        xs[f"sb={round(sb, 3)}"] = {
                            "rms_per_task_effect_pp": round(rms, 1),
                            "pi_degree_small": round(float(np.mean([d["pi"] for d in deg])), 4),
                            "power_x_signflip": rate(E.x_signflip_p(y, NFLIP, RNG)),
                            "pi_small_mean_sd": [
                                round(float(pis.mean()), 4),
                                round(float(pis.std()), 4),
                            ],
                        }
                    row["x_power"] = xs
                if sname == "literature" and K in (24, 32):
                    ss = {}
                    for shift in (0.5, 0.75):
                        y, p = simulate(
                            NSIM, K, 2, 2, mus, sc["sa"], shift=shift,
                            se=nz.get("se", 0.0), sf=nz.get("sf", 0.0),
                        )  # fmt: skip
                        gap = 100 * (p[..., 1, 0].mean() - p[..., 0, 0].mean())
                        ps = E.session_signflip_p(y, NFLIP, RNG)
                        ss[str(shift)] = {
                            "gap_pp": round(float(gap), 2),
                            "power_per_size": [rate(ps[:, 0]), rate(ps[:, 1])],
                        }
                    row["session_shift_power"] = ss
                out[key] = row
                log({key: row})
    return out


# --------------------------------------------------------------------------- DR5


GH_X, GH_W = np.polynomial.hermite_e.hermegauss(48)
GH_W = GH_W / GH_W.sum()


def session_marginal(eta: np.ndarray, sd: float) -> np.ndarray:
    """E over session effects u ~ N(0, sd^2) of expit(eta + u) (Gauss-Hermite)."""
    if sd == 0:
        return expit(eta)
    return (expit(eta[..., None] + sd * GH_X) * GH_W).sum(-1)


def degree(mu: float, sa: float, sb: float, sess_sd: float, n: int = 200000) -> dict:
    """The population moments the estimators target, and the share (X/4) / (X/4 + D_b/2).

    X = E_t[(mu_t,GA - mu_t,OSW)^2] and D_b = E_t,h[2 mu_th (1 - mu_th)], where mu_th
    averages over the session effects (total logit SD sess_sd); D_b therefore includes
    the session variance.
    """
    rng = np.random.default_rng(7)
    a = rng.normal(0, sa, n)
    b = rng.normal(0, sb, (n, 2)) if sb else np.zeros((n, 2))
    m = session_marginal(mu + a[:, None] + b, sess_sd)
    X = float(((m[:, 1] - m[:, 0]) ** 2).mean())
    D = float((2 * m * (1 - m)).mean())
    return {"X": X, "D_b": D, "pi": (X / 4) / (X / 4 + D / 2) if X + D > 0 else 0.0}


def pi_degree(mu: float, sa: float, sb: float, sess_sd: float) -> float:
    return degree(mu, sa, sb, sess_sd)["pi"]


LADDER = {
    # 4B, 9B (S1a's planning scenarios), 27B and 35B-A3B (pinned planning values)
    "literature": dict(p=(0.15, 0.30, 0.40, 0.40), sa=3.5),
    "opencua_calibrated": dict(p=(0.18, 0.243, 0.35, 0.35), sa=6.9),
}
LADDER_NOISE = {
    "base (sg 0.1, se 0.3)": dict(sg=0.1, se=0.3),
    "se 1.5": dict(sg=0.1, se=1.5),
    "sf 1.5": dict(sg=0.1, se=0.3, sf=1.5),
}
LADDER_TASKS, LADDER_SESSIONS = 60, 4


def ladder_m(nsim_null=4000, nsim=2000):
    """M: the smallest pi-degree of the small rungs whose full shrinkage (large rungs at
    share 0) a harness-only ladder (60 tasks x 4 sessions x 1 rerun per rung) detects with
    power 0.8, one-sided 5% against the simulated null critical value.

    Contrast: mean(pi-hat_4B, pi-hat_9B) - mean(pi-hat_27B, pi-hat_35B) (M_small), and
    pi-hat_9B - mean(large) for the DR1 case that drops 4B (M_9B). pi-hat is the registered
    estimator (X truncated at 0, 0/0 = 0). Power is interpolated linearly in pi-degree
    between grid points of sigma_b.
    """
    out = {}
    for sname, sc in LADDER.items():
        k = sc["sa"] / 3.5
        for nname, nz in LADDER_NOISE.items():
            sess_sd = math.sqrt(sum(v**2 for v in nz.values()))
            mus = [calibrate_mu(p, sc["sa"], sess_sd) for p in sc["p"]]
            y0, _ = simulate(nsim_null, LADDER_TASKS, LADDER_SESSIONS, 1, mus, sc["sa"], **nz)
            pi0 = E.pi_by_size(y0)
            c_small0 = pi0[:, :2].mean(1) - pi0[:, 2:].mean(1)
            c_9b0 = pi0[:, 1] - pi0[:, 2:].mean(1)
            crit_small = float(np.quantile(c_small0, 0.95))
            crit_9b = float(np.quantile(c_9b0, 0.95))
            rows = []
            for g in (0.0, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0):
                sb = g * k
                y, _ = simulate(
                    nsim, LADDER_TASKS, LADDER_SESSIONS, 1, mus, sc["sa"], sb=sb,
                    sb_sizes=(1, 1, 0, 0), **nz,
                )  # fmt: skip
                pis = E.pi_by_size(y)
                cs = pis[:, :2].mean(1) - pis[:, 2:].mean(1)
                c9 = pis[:, 1] - pis[:, 2:].mean(1)
                pd = [pi_degree(mus[i], sc["sa"], sb, sess_sd) for i in range(2)]
                rows.append(
                    {
                        "sb": round(sb, 3),
                        "pi_degree_4B_9B": [round(v, 4) for v in pd],
                        "pi_degree_small": round(float(np.mean(pd)), 4),
                        "pi_hat_small_mean": round(float(pis[:, :2].mean()), 4),
                        "power_small": round(float((cs > crit_small).mean()), 4),
                        "power_9B": round(float((c9 > crit_9b).mean()), 4),
                    }
                )
            m_small = mde([r["pi_degree_small"] for r in rows], [r["power_small"] for r in rows])
            m_9b = mde([r["pi_degree_4B_9B"][1] for r in rows], [r["power_9B"] for r in rows])
            key = f"{sname}|{nname}"
            out[key] = {
                "session_logit_sd": round(sess_sd, 3),
                "crit_small": round(crit_small, 4),
                "crit_9B": round(crit_9b, 4),
                "M_small": m_small,
                "M_9B": m_9b,
                "rows": rows,
            }
            log({key: {"M_small": m_small, "M_9B": m_9b}})
    return out


def dr5_oc(nsets=300, n_boot=1000):
    """DR5's operating characteristics on S1a's side: P(GO), P(NO-GO), P(INCONCLUSIVE)
    with the registered bootstrap bounds of pi_small (fewer resamples than the analysis's
    10,000) and the frozen M, against the pi-degree of the small rungs."""
    m = 0.13
    out = {}
    for sname in ("literature", "opencua_calibrated"):
        sc = SCEN[sname]
        k = sc["sa"] / 3.5
        nz = NOISE["base (sg 0.1, se 0.3)"]
        sess_sd = math.sqrt(sum(v**2 for v in nz.values()))
        mus = [calibrate_mu(p, sc["sa"]) for p in sc["p"]]
        for K in (24, 32):
            for g in (0.0, 1.0, 1.5, 2.0, 2.5, 3.0):
                sb = g * k
                y, _ = simulate(nsets, K, 2, 2, mus, sc["sa"], sb=sb, **nz)
                go = nogo = 0
                for i in range(nsets):
                    draws = E.bootstrap(y[i], E.pi_small, n_boot, 42 + i)
                    lb, ub = E.one_sided_bounds(draws)
                    go += lb > m
                    nogo += ub < m
                deg = float(np.mean([degree(mu, sc["sa"], sb, sess_sd)["pi"] for mu in mus]))
                row = {
                    "pi_degree_small": round(deg, 4),
                    "P_GO": round(go / nsets, 3),
                    "P_NO_GO": round(nogo / nsets, 3),
                    "P_INCONCLUSIVE": round(1 - (go + nogo) / nsets, 3),
                }
                out[f"{sname}|K={K}|sb={round(sb, 3)}"] = row
                log({f"{sname}|K={K}|sb={round(sb, 3)}": row})
    return out


# --------------------------------------------------------------------------- anchor


def anchor_section(nsim=4000):
    """DR-A: kill if ours lies more than 2 SE outside [min, max] of the three public runs.

    OpenCUA-calibrated (success 24.3%, task SD 6.9 logit). run_sd adds a per-run logit
    shift (ours and each public run independently) to show the false-kill rate when runs
    differ by a session effect, which the registered rule assumes away.
    """
    mu = calibrate_mu(0.243, 6.9)
    out = {}
    for n in (58, 64, 72, 96, 116):
        for run_sd in (0.0, 0.15):
            for shift in (0.0, -0.5, -1.0, -1.5, -2.0):
                a = RNG.normal(0, 6.9, (nsim, n))
                run = RNG.normal(0, run_sd, (nsim, 4, 1)) if run_sd else np.zeros((nsim, 4, 1))
                pub = RNG.random((nsim, 3, n)) < expit(mu + a[:, None, :] + run[:, :3])
                ours = RNG.random((nsim, n)) < expit(mu + a + shift + run[:, 3])
                pub, ours = pub.astype(float), ours.astype(float)
                dt = ours - pub.mean(1)
                se = dt.std(1, ddof=1) / math.sqrt(n)
                ps, po = pub.mean(2), ours.mean(1)
                kill = (po < ps.min(1) - 2 * se) | (po > ps.max(1) + 2 * se)
                gap = 100 * float((expit(mu + a + shift) - expit(mu + a)).mean())
                out[f"n={n},run_sd={run_sd},shift={shift}"] = {
                    "gap_pp": round(gap, 2),
                    "P_kill": round(float(kill.mean()), 4),
                }
    return out


def run_section(section: str):
    global RNG
    RNG = np.random.default_rng([SEED, SECTION_SEEDS[section]])
    if section == "size":
        return size_section()
    if section.startswith("power:"):
        return power_section(section.split(":", 1)[1])
    if section == "dr5":
        return ladder_m()
    if section == "anchor":
        return anchor_section()
    if section == "dr5_oc":
        return dr5_oc()
    raise SystemExit(f"unknown section {section}")


if __name__ == "__main__":
    if sys.argv[2] == "merge":
        res = {"seed": SEED, "section_seeds": SECTION_SEEDS, "nflip": NFLIP, "nperm": NPERM}
        res["power"] = {}
        for path in sys.argv[3:]:
            part = json.loads(Path(path).read_text())
            res["nsim"] = part["nsim"]
            if part["section"].startswith("power:"):
                res["power"].update(part["result"])
            else:
                res[part["section"]] = part["result"]
        print(json.dumps(res, indent=1))
    else:
        section = sys.argv[3]
        print(json.dumps({"section": section, "nsim": NSIM, "result": run_section(section)}))
