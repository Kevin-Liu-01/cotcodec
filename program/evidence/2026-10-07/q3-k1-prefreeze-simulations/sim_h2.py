"""Pass probabilities of the registered H2a / H2b gates on the dev pre-check and the audit read."""
import json, sys, os, zlib
import numpy as np
from multiprocessing import Pool
from scipy.special import expit, logit
from scipy.optimize import brentq
from harness import sparse_indexer_k1_stats as k

def calib(target, sq, pair_eff):
    # intercept so that the expected macro accuracy equals target (integrate question effect)
    z = np.random.default_rng(0).normal(0, sq, 200000)
    f = lambda a: np.mean([expit(a + pe + z).mean() for pe in pair_eff]) - target
    return brentq(f, -10, 10)

def design(setting):
    if setting == "dev":   # 20 dev questions x 14 pairs; ~20 links (assume 19 distinct)
        q_cl = np.r_[np.arange(19), 0]
        n_q = 20
    else:                  # audit: 230 questions in 122 links
        q_cl = np.sort(np.r_[np.arange(122), np.arange(108)])
        n_q = 230
    return n_q, q_cl

def one_h2a(args):
    seed, setting, a, sq, B = args
    rng = np.random.default_rng(seed)
    n_q, q_cl = design(setting)
    pair_eff = np.linspace(-0.6, 0.6, 14)
    b_q = rng.normal(0, sq, n_q)
    pair = np.repeat(np.arange(14), n_q); q = np.tile(np.arange(n_q), 14)
    p = expit(a + pair_eff[pair] + b_q[q])
    y = 100.0 * (rng.random(p.size) < p)
    iv = k.macro_mean_interval(y, pair, q_cl[q], replicates=B)
    return iv.lower > k.H2A_ACCURACY_POINTS, iv.point, iv.lower

def one_h2b(args):
    seed, setting, p_present, delta, sq, B = args
    rng = np.random.default_rng(seed)
    n_q, q_cl = design(setting)
    if setting == "dev":
        cells_q = np.tile(np.arange(n_q), 14)          # all 280 cells
    else:
        cells_q = rng.choice(np.repeat(np.arange(n_q), 14), 300, replace=False)
    b_q = rng.normal(0, sq, n_q)
    a_pres = logit(p_present); a_abs = logit(p_present - delta)
    # correlated through the question effect (same question in both twins)
    pres = 100.0 * (rng.random(cells_q.size) < expit(a_pres + b_q[cells_q]))
    absn = 100.0 * (rng.random(cells_q.size) < expit(a_abs + 0.5 * b_q[cells_q]))
    d = pres - absn
    iv = k.macro_mean_interval(d, np.zeros(d.size, dtype=np.int64), q_cl[cells_q], replicates=B)
    return (iv.lower > 0 and iv.point >= k.H2B_POINTS), iv.point, iv.lower

if __name__ == "__main__":
    reps, B = int(sys.argv[1]), int(sys.argv[2])
    out = {}
    with Pool(int(os.environ.get("NPROC", "16"))) as pool:
        for sq in (0.8, 1.5):
            for setting in ("dev", "audit"):
                for acc in (0.35, 0.40, 0.45, 0.50, 0.60):
                    a = calib(acc, sq, np.linspace(-0.6, 0.6, 14))
                    res = pool.map(one_h2a, [(zlib.crc32(f"a{setting}{acc}{sq}".encode()) + i,
                                              setting, a, sq, B) for i in range(reps)])
                    key = f"H2a sq={sq} {setting} true_macro_acc={acc}"
                    out[key] = dict(P_pass=float(np.mean([r[0] for r in res])),
                                    mean_lower=float(np.mean([r[2] for r in res])))
                    print(key, out[key], flush=True)
                for delta in (0.05, 0.08, 0.10, 0.15):
                    res = pool.map(one_h2b, [(zlib.crc32(f"b{setting}{delta}{sq}".encode()) + i,
                                              setting, 0.45, delta, sq, B) for i in range(reps)])
                    key = f"H2b sq={sq} {setting} present=0.45 true_delta={delta}"
                    out[key] = dict(P_pass=float(np.mean([r[0] for r in res])),
                                    mean_lower=float(np.mean([r[2] for r in res])))
                    print(key, out[key], flush=True)
    json.dump(out, open(f"sim_h2_{reps}_{B}.json", "w"), indent=1)
