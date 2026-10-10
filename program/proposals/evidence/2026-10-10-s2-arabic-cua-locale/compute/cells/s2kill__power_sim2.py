"""Supplement: calibrated heterogeneous logit-shift model + analytic noise-only MDE. Seeds 42, 43, 44."""
import json, math, collections
import numpy as np
A1 = "/Users/kevinliu/repos/cotcodec/program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl"
cells = collections.defaultdict(list)
for l in open(A1):
    r = json.loads(l); s = r["score"]
    cells[(r["size"], r["harness"], r["task_id"])].append(1.0 if (s is not None and s >= 1.0) else 0.0)
pool = np.clip(np.array([sum(v)/len(v) for v in cells.values()]), 0.01, 0.99)
pq = np.mean([len(v)/(len(v)-1)*(sum(v)/len(v))*(1-sum(v)/len(v)) for v in cells.values()])

def tq(df, z):
    g1=(z**3+z)/4; g2=(5*z**5+16*z**3+3*z)/96; g3=(3*z**7+19*z**5+17*z**3-15*z)/384
    return z+g1/df+g2/df**2+g3/df**3
print(f"S1a secondary pool: {len(pool)} task-cells, mean within-cell p(1-p) = {pq:.4f}")
print("Analytic noise-only paired MDE (no task-effect heterogeneity; 80% power):")
for K, n in [(18, 8), (18, 24), (36, 8), (54, 8)]:
    se = math.sqrt(2*pq/(n*K))
    for a, z in [(0.05, 1.959964), (0.025, 2.241403)]:
        print(f"  K={K} n={n} alpha={a}: SE={100*se:.2f} pp, MDE={100*se*(tq(K-1,z)+0.8416):.1f} pp")

def lg(p): return np.log(p/(1-p))
def ex(x): return 1/(1+np.exp(-x))
def calib(delta, s, rng):
    z = rng.normal(0, s, size=(200, len(pool)))
    lo, hi = -8, 0
    for _ in range(50):
        c = (lo+hi)/2
        m = (ex(lg(pool)[None, :] + c + z) - pool[None, :]).mean()
        if m > delta: hi = c
        else: lo = c
    return (lo+hi)/2

print("\nCalibrated heterogeneous logit-shift model (realized pool-mean effect = delta):")
for s in (0.0, 1.0, 2.0):
    for delta in (-0.05, -0.10):
        c = calib(delta, s, np.random.default_rng(7))
        out = []
        for K, n in [(18, 8), (18, 24), (36, 8), (36, 24), (54, 8)]:
            pw = {0.05: [], 0.025: []}; realized = []; tauvar = []
            for sd in (42, 43, 44):
                rng = np.random.default_rng(sd)
                for _ in range(1500):
                    p = rng.choice(pool, size=K)
                    pa = ex(lg(p) + c + rng.normal(0, s, size=K))
                    realized.append((pa-p).mean()); tauvar.append((pa-p).var(ddof=1))
                    d = rng.binomial(n, pa)/n - rng.binomial(n, p)/n
                    t = d.mean()/(d.std(ddof=1)/math.sqrt(K)) if d.std(ddof=1) > 0 else 0
                    for a, z in [(0.05, 1.959964), (0.025, 2.241403)]:
                        pw[a].append(abs(t) > tq(K-1, z))
            out.append(f"K={K},n={n}: {np.mean(pw[0.05]):.2f}/{np.mean(pw[0.025]):.2f}")
        print(f"  s={s} delta={delta:+.2f} (realized mean {np.mean(realized):+.3f}, task-effect var {np.mean(tauvar):.4f}): " + "; ".join(out))
