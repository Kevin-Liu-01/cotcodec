"""Monte Carlo seed check of pi_small's one-sided 95% bounds (post-verification, descriptive).

Not code of record and not a registered analysis: it reads the analysis's merged records
(e.jsonl) and calls the frozen estimators of the export of f6144d6b (task_resamples,
bootstrap, one_sided_bounds, x_by_size, d_between, pi_share) on the primary set
("primary", 113 tasks) or S1a's 32 base tasks ("base"), at the registered seed 42 and at
20 other seeds (1000-1019) with the registered 10,000 resamples, and once (primary) at
200,000 resamples with seed 424242. Run on the host by stdin pipe, read-only:
    python3 -s -B - primary < mc-seed-check.py
It confirms the fresh verifier's seed-dependence finding (verifier-record.json) with the
frozen code. No rule reads it; the registered reading is the seed-42 one in report.json.
"""
import json, sys, time, warnings
X = "/home/kevin/cotcodec-runs/stage0/q2-stage1e/src/f6144d6bf745d944cb016cfc2b9894e1dbf7eb66"
A = "/home/kevin/cotcodec-runs/stage0/q2-stage1e/analysis/e-v1"
sys.path.insert(0, X)
import numpy as np
from harness.q2_stage1 import estimators as E
from harness.q2_stage1e import records as RE
plan = json.load(open(X + "/program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json"))
recs = [RE.validate(json.loads(l)) for l in open(A + "/e.jsonl")]
finals = RE.final_records(recs)
mode = sys.argv[1]
tasks = list(plan["tasks"]) if mode == "primary" else list(plan["s1a_base"])
y = RE.outcome_array(finals, tasks)
def fn(yy):
    pis = E.pi_share(E.x_by_size(yy), E.d_between(yy))
    return np.nanmean(pis, axis=-1)
warnings.simplefilter("ignore")
t0 = time.time()
ubs = []
for seed in [42] + list(range(1000, 1020)):
    d = E.bootstrap(y, fn, 10000, seed)
    lb, ub = E.one_sided_bounds(d, 0.95)
    if seed != 42: ubs.append(ub)
    print(mode, "seed", seed, "B 10000", "lb %.6f ub %.6f" % (lb, ub), flush=True)
u = np.array(ubs)
print(mode, "20 seeds: min %.4f max %.4f mean %.4f sd %.4f n>=0.12 %d" % (u.min(), u.max(), u.mean(), u.std(ddof=1), (u >= 0.12).sum()))
if mode == "primary":
    d = E.bootstrap(y, fn, 200000, 424242)
    lb, ub = E.one_sided_bounds(d, 0.95)
    print(mode, "seed 424242 B 200000 lb %.6f ub %.6f share>=0.12 %.4f" % (lb, ub, float((d >= 0.12).mean())))
print("secs %.1f" % (time.time() - t0))
