"""Cross-domain scout sketch: compare 'rare-break' guards for an unqualified SMALL.

Simplified version of S2 v2's Phase 1 model (not the registered simulation):
- task propensity p_t: Beta(0.107, 0.167) (S1a beta-binomial fit), selected on
  >= SEL of 4 English successes, then p_t drawn from its posterior;
- four cells (enL, enR, arL, arR), n episodes per cell per task, no session shift;
- D_t = 0.5*[(enR-enL)+(arR-arL)];  T = 0 throughout.
Guards for SMALL (all require TOST: 90% t interval of mean D inside (-5, +5) pp):
  G0 TOST only
  G1 v2 rule: Clopper-Pearson 95% upper bound U on share of D_t <= -0.25, U*mean(enL) < 0.05
  G2 freedom-from-disease rule (Cameron & Baldock style, imperfect Se and Sp):
     reject H_break (share pi* = 0.05/mean LTR success, complete breaks at random tasks)
     if P(B <= B_obs | H_break) < 0.05, with per-task Se/false-positive rates from plug-in p.
  G3 variance-component (IBE-style) rule: 95% upper bound on sigma_D (between-task SD of
     true D_t) below SIGMA_STAR, via chi-square bound on var(D_t-hat) minus mean binomial
     sampling variance.
"""
import sys
import numpy as np
from scipy import stats

rng = np.random.default_rng(42)
A, B_ = 0.107, 0.167
SIGMA_STAR = float(sys.argv[1]) if len(sys.argv) > 1 else 0.10
SEL = int(sys.argv[2]) if len(sys.argv) > 2 else 1
PRIOR = sys.argv[3] if len(sys.argv) > 3 else "s1a"   # "s1a" (selected) or "u625" (Beta(0.5,0.3), mean 0.625)
REPS = int(sys.argv[4]) if len(sys.argv) > 4 else 3000


def draw_tasks(K):
    if PRIOR == "u625":
        return rng.beta(0.5, 0.3, size=K)
    out = []
    while len(out) < K:
        p = rng.beta(A, B_, size=4 * K)
        k = rng.binomial(4, p)
        keep = k >= SEL
        post = rng.beta(A + k[keep], B_ + 4 - k[keep])
        out.extend(post.tolist())
    return np.array(out[:K])


def logit(x):
    return np.log(x / (1 - x))


def expit(x):
    return 1 / (1 + np.exp(-x))


def solve_shift(p, target=0.05):
    lo, hi = 0.0, 5.0
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    for _ in range(50):
        mid = (lo + hi) / 2
        drop = np.mean(pc - expit(logit(pc) - mid))
        lo, hi = (mid, hi) if drop < target else (lo, mid)
    return (lo + hi) / 2


def pbinom_le(probs, bobs):
    # Poisson-binomial P(B <= bobs)
    dist = np.zeros(len(probs) + 1)
    dist[0] = 1.0
    for q in probs:
        dist[1:] = dist[1:] * (1 - q) + dist[:-1] * q
        dist[0] *= (1 - q)
    return dist[: bobs + 1].sum()


from functools import lru_cache


@lru_cache(maxsize=None)
def _p_dhat_le_cached(pL, pR, n, thr):
    return _p_dhat_le(pL, pR, n, thr)


def p_dhat_le(pL, pR, n, thr=-0.25):
    return _p_dhat_le_cached(round(float(pL), 6), round(float(pR), 6), n, thr)


def _p_dhat_le(pL, pR, n, thr=-0.25):
    """P(D_t-hat <= thr) when both text levels have LTR prob pL and RTL prob pR (exact)."""
    k = np.arange(n + 1)
    fL = stats.binom.pmf(k, n, pL)
    fR = stats.binom.pmf(k, n, pR)
    # difference per text level: (kR - kL)/n ; D = mean of two such
    diff = np.convolve(fR, fL[::-1])  # index i -> kR-kL = i-n
    vals = (np.arange(2 * n + 1) - n) / n
    tot = np.convolve(diff, diff)  # sum of two differences
    svals = (np.arange(4 * n + 1) - 2 * n) / n
    return tot[0.5 * svals <= thr + 1e-12].sum()


def run(K, n, structure):
    res = {g: 0 for g in ("G0", "G1", "G2", "G3", "G1_fpwrong", "G3_fpwrong", "nobreak")}
    tcrit = stats.t.ppf(0.95, K - 1)
    chi_lo = stats.chi2.ppf(0.05, K - 1)
    for _ in range(REPS):
        p = draw_tasks(K)
        pL = p.copy()
        if structure == "null":
            pR = p.copy()
        elif structure == "uniform":
            pR = expit(logit(np.clip(p, 1e-6, 1 - 1e-6)) - solve_shift(p))
        elif structure == "breaks":
            pi = min(1.0, 0.05 / p.mean())
            broken = rng.random(K) < pi
            pR = np.where(broken, 0.0, p)
            if not broken.any():
                res["nobreak"] += 1
        elif structure == "quarter":
            # proportional drop concentrated in a quarter of tasks, mean -5 pp
            sel = rng.random(K) < 0.25
            f = min(1.0, 0.05 / (0.25 * p.mean()))
            pR = np.where(sel, p * (1 - f), p)
        cells = {c: rng.binomial(n, pr, size=K) / n for c, pr in
                 (("enL", pL), ("enR", pR), ("arL", pL), ("arR", pR))}
        D = 0.5 * ((cells["enR"] - cells["enL"]) + (cells["arR"] - cells["arL"]))
        trueD = np.mean(pR - pL)  # finite-population (these K tasks) true mean D
        m, s = D.mean(), D.std(ddof=1)
        half = tcrit * s / np.sqrt(K)
        tost = (m - half > -0.05) and (m + half < 0.05)
        if not tost:
            continue
        res["G0"] += 1
        # G1
        b = int((D <= -0.25).sum())
        U = stats.beta.ppf(0.95, b + 1, K - b) if b < K else 1.0
        if U * cells["enL"].mean() < 0.05:
            res["G1"] += 1
            if trueD <= -0.05: res["G1_fpwrong"] += 1
        # G2
        phat = 0.5 * (cells["enL"] + cells["arL"])
        pistar = min(1.0, 0.05 / max(phat.mean(), 1e-6))
        q = []
        for pt in phat:
            se = p_dhat_le(pt, 0.0, n)
            fp = p_dhat_le(pt, pt, n)
            q.append(pistar * se + (1 - pistar) * fp)
        if pbinom_le(np.array(q), b) < 0.05:
            res["G2"] += 1
        # G3
        v = 0.25 * sum(cells[c] * (1 - cells[c]) / (n - 1) for c in cells)
        Usig2 = s * s * (K - 1) / chi_lo - v.mean()
        if np.sqrt(max(Usig2, 0.0)) < SIGMA_STAR:
            res["G3"] += 1
            if trueD <= -0.05: res["G3_fpwrong"] += 1
    return {g: round(c / REPS, 3) for g, c in res.items()}


if __name__ == "__main__":
    pm = np.mean([draw_tasks(200).mean() for _ in range(50)])
    print(f"prior {PRIOR} SEL>={SEL}: mean propensity {pm:.3f}; sigma* {SIGMA_STAR}; reps {REPS}")
    for K in (26, 43, 64, 100):
        for n in (16,):
            for st in ("null", "uniform", "quarter", "breaks"):
                print(K, n, st, run(K, n, st), flush=True)
