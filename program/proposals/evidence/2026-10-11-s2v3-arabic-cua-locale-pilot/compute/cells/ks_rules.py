"""Alternative SMALL rules on the same simulated data: can any rule be both reachable (null) and valid (break-type -5 pp)?"""
import importlib.util, json, math, sys
import numpy as np
from scipy import stats
exec(open('ks_power.py').read().split("scen = [")[0])  # reuse loader, prior, synth, n_max, real_post
NREP = 400
def sim(pa, pb, st, c, n, seed):
    K = pa.shape[0]; rng = np.random.Generator(np.random.PCG64([seed, 1]))
    p0 = rng.beta(np.broadcast_to(pa, (NREP, K, 2)), np.broadcast_to(pb, (NREP, K, 2)))
    u = rng.normal(0.0, pw.SESSION_SD, size=(NREP, 1, 1)); p0s = pw.expit(pw.logit(p0) + u)
    if st == 'flip':
        cd = (rng.random((NREP, K)) < c['frac_d']).astype(float); ct = (rng.random((NREP, K)) < c['frac_t']).astype(float)
        pc = pw.cell_probs(p0s, 'flip', 1.0, 1.0, cd, ct)
    elif st == 'perturb':
        eps = c['theta_d'] + rng.standard_normal((NREP, K)); pc = pw.cell_probs(p0s, 'perturb', 0.0, c['theta_t'], None, None, eps_d=eps)
    else:
        pc = pw.cell_probs(p0s, 'logit', c['theta_d'], c['theta_t'], None, None)
    nh = n // 2; k = rng.binomial(nh, pc); y = k.sum(axis=2) / n
    D = ((y[..., 3] - y[..., 1]) + (y[..., 2] - y[..., 0])) / 2
    kk = k.sum(axis=2)  # (R,K,4) successes of n per cell
    return D, kk, y[..., 0].mean(axis=1)
def rules(D, kk, en, n):
    R, K = D.shape; est = D.mean(1); se = D.std(1, ddof=1) / math.sqrt(K); q = stats.t.ppf(0.95, K - 1)
    tost = (est - q * se > -0.05) & (est + q * se < 0.05)
    def cp(B): return np.where(B < K, stats.beta.ppf(0.95, B + 1, np.maximum(K - B, 1)), 1.0)
    Bd = (D <= -0.25 + 1e-12).sum(1); Bu = (D >= 0.25 - 1e-12).sum(1)
    r = {'R1_tost_only': tost, 'R2_v2_rare_break': tost & (cp(Bd) * en < 0.05),
         'R3_symmetric_excess': tost & (cp(np.maximum(Bd - Bu, 0)) * en < 0.05)}
    # R4: break = one-sided Fisher-type test RTL vs LTR pooled over text level (2n vs 2n episodes), alpha 0.01
    sL = kk[..., 0] + kk[..., 1]; sR = kk[..., 2] + kk[..., 3]; N = 2 * n
    # hypergeometric lower tail P(X <= sR) with total successes sL+sR, draws N from 2N
    tot = sL + sR; p = stats.hypergeom.cdf(sR, 2 * N, tot, N)
    B4 = (p <= 0.01).sum(1)
    r['R4_test_breaks_a01'] = tost & (cp(B4) * en < 0.05)
    return {k: float(v.mean()) for k, v in r.items()}, float(Bd.mean()), float(Bu.mean()), float(B4.mean())
scen = [('null_logit', 'logit', 0.0), ('null_perturb', 'perturb', 0.0), ('flip_-5', 'flip', -0.05), ('perturb_-5', 'perturb', -0.05), ('logit_-5','logit',-0.05)]
out = {}
base_pa, base_pb = real_post(sets['LO_TB_GIMP'])
for extra, n in ((0, 12), (13, 10), (57, 4)):
    if extra: spa, spb = synth(extra, True, 42 if extra < 50 else 44); pa = np.vstack([base_pa, spa]); pb = np.vstack([base_pb, spb])
    else: pa, pb = base_pa, base_pb
    K = pa.shape[0]
    rngc = np.random.Generator(np.random.PCG64([42, 800]))
    bank = rngc.beta(np.broadcast_to(pa, (pw.CAL_BANK, K, 2)), np.broadcast_to(pb, (pw.CAL_BANK, K, 2)))
    bank = pw.expit(pw.logit(bank) + rngc.normal(0, pw.SESSION_SD, size=(pw.CAL_BANK, 1, 1)))
    for sname, st, td in scen:
        c = pw.calibrate(st, td, pw.T_TARGET, bank, 42)
        if c is None: continue
        acc = []
        for sd in pw.SEEDS:
            D, kk, en = sim(pa, pb, st, c, n, sd * 1000 + n); acc.append(rules(D, kk, en, n))
        res = {k: round(float(np.mean([a[0][k] for a in acc])), 3) for k in acc[0][0]}
        res.update(mean_Bdown=round(np.mean([a[1] for a in acc]), 2), mean_Bup=round(np.mean([a[2] for a in acc]), 2), mean_B4=round(np.mean([a[3] for a in acc]), 2))
        out[f'K{K}_n{n}|{sname}'] = res; print(f'K{K} n{n} {sname}', res, flush=True)
json.dump(out, open('ks_rules_out.json', 'w'), indent=1)
