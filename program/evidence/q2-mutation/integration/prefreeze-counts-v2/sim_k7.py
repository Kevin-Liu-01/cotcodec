"""K7 power under the registered rule: two-sided 95% task-cluster percentile
bootstrap (task-equal mean), family flagged when the 2.5% limit exceeds 5%.
Beta-binomial tasks: per-task rate ~ Beta(p(1/icc-1), (1-p)(1/icc-1))."""
import json, sys
import numpy as np

def power(p, tasks, m, icc, reps=400, n_boot=2000, seed=0):
    rng = np.random.default_rng(seed)
    s = 1 / icc - 1
    hits = 0
    for _ in range(reps):
        rates = rng.beta(p * s, (1 - p) * s, size=tasks)
        events = rng.binomial(m, rates)
        per_task = events / m
        idx = rng.integers(0, tasks, size=(n_boot, tasks))
        boot = per_task[idx].mean(axis=1)
        low = np.quantile(boot, 0.025)
        hits += low > 0.05
    return hits / reps

out = {}
for tasks, m in ((31, 4), (21, 4), (31, 3), (21, 3), (8, 5)):
    row = {}
    for p in (0.05, 0.10, 0.14, 0.17, 0.20, 0.22, 0.25, 0.30, 0.35):
        row[str(p)] = power(p, tasks, m, 0.5)
    out[f"{tasks}x{m}"] = row
    print(tasks, m, row, flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
