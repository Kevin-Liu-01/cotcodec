"""Kill-shot power simulation for S2 Phase 1, anchored to S1a's measured records.

Reads S1a's a1.jsonl (read-only), derives per-task success rates and rerun
noise, then simulates the S2 contrast (Arabic minus English, paired by task)
on K Relay-like tasks with n episodes per (task, locale) cell.
Seeded (numpy PCG64, seeds 42, 43, 44). No network, no writes outside stdout.
"""
import json, math, sys, collections
import numpy as np

A1 = "/Users/kevinliu/repos/cotcodec/program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"
recs = [json.loads(l) for l in open(A1)]

# --- 1. Empirical anchors from S1a -------------------------------------------
cells = collections.defaultdict(list)  # (size, harness, task) -> scores (raw, fractional -> 0/1 by >=1)
for r in recs:
    s = r["score"]
    y = 1.0 if (s is not None and s >= 1.0) else 0.0
    cells[(r["size"], r["harness"], r["task_id"], r["extension_block"] is None)].append(y)

def summarize(base_only):
    ps, pq = [], []
    for k, v in cells.items():
        if base_only and not k[3]:
            continue
        p = sum(v) / len(v)
        ps.append(p)
        n = len(v)
        # unbiased within-cell Bernoulli variance p(1-p) estimate: n/(n-1) * phat(1-phat)
        pq.append(n / (n - 1) * p * (1 - p) if n > 1 else 0.0)
    ps = np.array(ps); pq = np.array(pq)
    return ps, pq

for base_only in (True, False):
    ps, pq = summarize(base_only)
    print(f"[anchor] base_only={base_only}: cells={len(ps)} mean p={ps.mean():.3f} "
          f"share p==0 {np.mean(ps==0):.2f} share p==1 {np.mean(ps==1):.2f} "
          f"mean p(1-p)={pq.mean():.4f} (pairwise discordance ~ {2*pq.mean():.3f})")

# Empirical per-cell success-rate pool (all 113 tasks x 2 sizes x 2 harnesses) for drawing base rates
ps_all, _ = summarize(False)

# --- 2. Simulation ----------------------------------------------------------
TQ = {  # two-sided t quantiles we need, df -> (t_.975, t_.9875)
}
def t_q(df, a):
    # Cornish-Fisher style approximation to Student t quantile (adequate for df>=5)
    z = {0.975: 1.959964, 0.9875: 2.241403}[a]
    g1 = (z**3 + z) / 4
    g2 = (5*z**5 + 16*z**3 + 3*z) / 96
    g3 = (3*z**7 + 19*z**5 + 17*z**3 - 15*z) / 384
    return z + g1/df + g2/df**2 + g3/df**3

def logit(p): return math.log(p/(1-p))

def simulate(K, n, delta, sigma_tau2, effect, rng, reps=4000, alpha=0.975, base_pool=ps_all):
    """Return power of a task-clustered paired t test of mean(ar - en) at given two-sided level."""
    hits = 0
    est = []
    tq = t_q(K-1, alpha)
    for _ in range(reps):
        p_en = rng.choice(base_pool, size=K, replace=True)
        # shrink exact 0/1 slightly so a logit shift is defined; this keeps floor/ceiling tasks near-inert
        p_en = np.clip(p_en, 0.01, 0.99)
        if effect == "additive_hetero":
            # per-task additive shift with mean delta and sd sqrt(sigma_tau2), clipped to [0,1]
            tau = rng.normal(delta, math.sqrt(sigma_tau2), size=K)
            p_ar = np.clip(p_en + tau, 0.0, 1.0)
        elif effect == "logit_uniform":
            # common logit shift chosen so the expected mean shift over the pool equals delta
            p_ar = 1/(1+np.exp(-(np.log(p_en/(1-p_en)) + LOGIT_SHIFT[(round(delta,4))])))
        elif effect == "concentrated":
            # whole-task flips: each informative task (0<p<1 or p==1) flips to 0 with prob q, q set so mean = delta
            q = min(1.0, -delta / max(1e-9, p_en.mean()))
            flip = rng.random(K) < q
            p_ar = np.where(flip, 0.01, p_en)
        y_en = rng.binomial(n, p_en) / n
        y_ar = rng.binomial(n, p_ar) / n
        d = y_ar - y_en
        m = d.mean(); se = d.std(ddof=1) / math.sqrt(K)
        est.append(m)
        if se > 0 and abs(m) / se > tq:
            hits += 1
    return hits / reps, float(np.mean(est))

# calibrate a common logit shift per delta so the pool-averaged effect equals delta
LOGIT_SHIFT = {}
def calibrate(delta):
    p = np.clip(ps_all, 0.01, 0.99)
    lo, hi = -6.0, 0.0
    for _ in range(60):
        mid = (lo+hi)/2
        pa = 1/(1+np.exp(-(np.log(p/(1-p)) + mid)))
        if (pa - p).mean() > delta: hi = mid
        else: lo = mid
    LOGIT_SHIFT[round(delta,4)] = (lo+hi)/2

deltas = [-0.05, -0.08, -0.10, -0.15]
for d in deltas: calibrate(d)

designs = [(18, 8), (18, 24), (18, 64), (36, 8), (36, 24), (54, 8), (113, 4)]
scen = [("logit_uniform", 0.0), ("additive_hetero", 0.005), ("additive_hetero", 0.0117), ("concentrated", 0.0)]
print("\nPower of the paired, task-clustered t test (rows: design K tasks x n episodes per task-locale cell).")
print("alpha two-sided 0.05 (one contrast) / 0.025 (Bonferroni over glyph and mirror contrasts). 4000 reps per cell, seeds 42/43/44 averaged.")
for eff, s2 in scen:
    print(f"\n== effect model: {eff}, sigma_tau^2={s2}")
    print("K   n  | " + " | ".join(f"d={d:+.2f} a.05 / a.025" for d in deltas))
    for K, n in designs:
        row = []
        for d in deltas:
            res = []
            for a in (0.975, 0.9875):
                pw = np.mean([simulate(K, n, d, s2, eff, np.random.default_rng(sd), reps=1500, alpha=a)[0] for sd in (42, 43, 44)])
                res.append(pw)
            row.append(f"{res[0]:.2f} / {res[1]:.2f}")
        print(f"{K:<3} {n:<3}| " + " | ".join(f"{x:>20}" for x in row))
        sys.stdout.flush()
