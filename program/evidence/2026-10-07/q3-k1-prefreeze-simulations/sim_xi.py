"""Operating characteristics of the K1-screen xi / xi_rel decision rules (registered code)."""
import json, math, sys, os, zlib
import numpy as np
from multiprocessing import Pool
from harness import sparse_indexer_k1_stats as k

N_PAIRS, N_CL, N_Q, N_SEEDS = 14, 122, 230, 3
Q_CL = np.sort(np.r_[np.arange(N_CL), np.arange(N_Q - N_CL)])  # 122 links, 108 with 2 questions
PAIR = np.repeat(np.arange(N_PAIRS), N_Q)
QF = np.tile(np.arange(N_Q), N_PAIRS)
CL = Q_CL[QF]
EN_NEEDLE = PAIR >= 7      # pairs 7..13: needle en, MN prompt shared across the 7 pairs
RAND = 12.5
HEAD_MN, HEAD_CX = 62.5, 50.0   # target headroom over random (tgt_mn 75, tgt_cx 62.5)

def gen(rng, g_mn, g_cx, sc, sf, sv, ss, ssp=0.0, shared_cluster=None):
    n = PAIR.size
    a_q = rng.normal(0, 6, N_Q)
    # target recalls; en-needle MN prompts are one prompt per question
    mn_prompt_noise = rng.normal(0, 4, (N_PAIRS, N_Q))
    mn_prompt_noise[7:] = mn_prompt_noise[7]
    tgt_mn = 75 + a_q[QF] + mn_prompt_noise[PAIR, QF]
    tgt_cx = 62.5 + a_q[QF] + rng.normal(0, 4, n)
    # indexer deviations
    c_cl = rng.normal(0, sc, N_CL) if shared_cluster is None else shared_cluster
    w_cx = rng.normal(0, sf, n)
    w_mn_prompt = rng.normal(0, sf / 2, (N_PAIRS, N_Q)); w_mn_prompt[7:] = w_mn_prompt[7]
    d_s = rng.normal(0, ss, (N_SEEDS, 1))
    d_sp = rng.normal(0, ssp, (N_SEEDS, N_PAIRS))
    v_cx = rng.normal(0, sv, (N_SEEDS, n))
    v_mn_prompt = rng.normal(0, sv / 2, (N_SEEDS, N_PAIRS, N_Q)); v_mn_prompt[:, 7:] = v_mn_prompt[:, 7:8]
    ind_mn = RAND + g_mn * (tgt_mn - RAND) + w_mn_prompt[PAIR, QF] + v_mn_prompt[:, PAIR, QF]
    ind_cx = RAND + g_cx * (tgt_cx - RAND) + c_cl[CL] + w_cx + d_s + d_sp[:, PAIR] + v_cx
    clip = lambda x: np.clip(x, 0, 100)
    return k.FamilyTable(PAIR, CL, clip(ind_mn), clip(ind_cx), clip(tgt_mn), clip(tgt_cx),
                         np.full(n, RAND), np.full(n, RAND))

def truth(g_mn, g_cx):
    xi = g_mn * HEAD_MN - g_cx * HEAD_CX - (HEAD_MN - HEAD_CX)
    return xi, g_mn - g_cx

def one(args):
    seed, g_mn, g_cx, noise, B = args
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(2):   # two targets, independent noise
        t = gen(rng, g_mn, g_cx, **noise)
        xi, rel = k.xi_interval(t, replicates=B), k.xi_rel_interval(t, replicates=B)
        r = k.TargetRead("x", xi, rel, k.AdequacyRead((90.0,) * 3, 91.0), True)
        out.append(dict(xi=xi.point, lo=xi.lower, hi=xi.upper, hw=xi.half_width, df=xi.df,
                        sc=xi.se_cluster, ss=xi.s_seed, rp=rel.point, rlo=rel.lower,
                        rhi=rel.upper, rev=rel.evaluable, go=r.go, neg=r.negative,
                        zlo=xi.point - k.Z_99 * xi.se_total, zhi=xi.point + k.Z_99 * xi.se_total))
    return out

SCEN = {
    "A_worked_cluster10_seed1": dict(sc=9.0, sf=15.0, sv=5.0, ss=1.0),
    "B_cluster3_seed1": dict(sc=3.0, sf=15.0, sv=5.0, ss=1.0),
    "C_seed_dominated_seed3": dict(sc=0.5, sf=3.0, sv=0.5, ss=3.0),
    "D_cluster2_seed2": dict(sc=2.0, sf=10.0, sv=3.0, ss=2.0),
    "E_seed_small_0.5": dict(sc=2.0, sf=10.0, sv=3.0, ss=0.5),
}
TRUTHS = {  # (g_mn, g_cx)
    "xi=0,rel=0": (1.0, 1.0),
    "weaker g=.85 (xi=-1.9,rel=0)": (0.85, 0.85),
    "xi=2.5,rel=.05": (1.0, 0.95),
    "xi=5,rel=.10": (1.0, 0.9),
    "xi=7.5,rel=.15": (1.0, 0.85),
    "xi=9,rel=.18": (1.0, 0.82),
    "xi=10,rel=.20 (MDE)": (1.0, 0.8),
    "xi=11,rel=.22": (1.0, 0.78),
    "xi=12,rel=.24": (1.0, 0.76),
}

if __name__ == "__main__":
    reps = int(sys.argv[1]); B = int(sys.argv[2]); which = sys.argv[3:] or list(SCEN)
    results = {}
    with Pool(int(os.environ.get("NPROC", "16"))) as pool:
        for sname in which:
            noise = SCEN[sname]
            for tname, (gm, gc) in TRUTHS.items():
                xi_t, rel_t = truth(gm, gc)
                runs = pool.map(one, [(zlib.crc32(f'{sname}|{tname}'.encode()) * 100003 + i, gm, gc, noise, B)
                                      for i in range(reps)])
                per = [r for pair in runs for r in pair]
                def frac(f): return float(np.mean([f(r) for r in per]))
                go_any = float(np.mean([a["go"] or b["go"] for a, b in runs]))
                neg_both = float(np.mean([a["neg"] and b["neg"] for a, b in runs]))
                row = dict(
                    xi_true=xi_t, rel_true=rel_t,
                    P_go_target=frac(lambda r: r["go"]), P_neg_target=frac(lambda r: r["neg"]),
                    P_verdict_GO=go_any, P_verdict_NEG=neg_both,
                    xi_cov_t=frac(lambda r: r["lo"] <= xi_t <= r["hi"]),
                    xi_cov_z=frac(lambda r: r["zlo"] <= xi_t <= r["zhi"]),
                    xi_upper_below_true=frac(lambda r: r["hi"] < xi_t),
                    xi_lower_above_true=frac(lambda r: r["lo"] > xi_t),
                    rel_cov=frac(lambda r: r["rev"] and r["rlo"] <= rel_t <= r["rhi"]),
                    rel_upper_below_true=frac(lambda r: r["rev"] and r["rhi"] < rel_t),
                    mean_hw=frac(lambda r: r["hw"]), mean_df=float(np.median([r["df"] for r in per])),
                    mean_se_cluster=frac(lambda r: r["sc"]), mean_s_seed=frac(lambda r: r["ss"]),
                    sd_xi_point=float(np.std([r["xi"] for r in per])),
                    mean_xi_point=frac(lambda r: r["xi"]), mean_rel_point=frac(lambda r: r["rp"]))
                results[f"{sname} | {tname}"] = row
                print(sname, "|", tname, json.dumps({k_: round(v, 4) for k_, v in row.items()}), flush=True)
    json.dump(results, open(f"sim_xi_{reps}_{B}.json", "w"), indent=1)
