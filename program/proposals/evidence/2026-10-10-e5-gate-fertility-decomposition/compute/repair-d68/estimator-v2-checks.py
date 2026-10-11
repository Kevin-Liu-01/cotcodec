#!/usr/bin/env python3
"""Unit checks of estimator_v2.py: the operating-point rule on every branch, every per-subject
reading, the overall rule, the exact identity TE = PNIE + PNDE + INT, and agreement of
read_subject, cluster_normal and cluster_normal_matrix. The future CPU doctor (registration
v2, prerequisite 6) starts from these. Usage: python estimator-v2-checks.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimator_v2 as e  # noqa: E402

I = e.Interval
checks = [
    (e.select_operating_point({4: 95, 8: 88, 16: 70}, {(8, 2.7): 45, (8, 2.0): 60}), (8, 2.7)),
    (e.select_operating_point({4: 85}, {(4, 2.7): 29, (4, 2.0): 31}), (4, 2.0)),
    (e.select_operating_point({4: 85}, {(4, 2.7): 29, (4, 2.0): 29}), None),
    (e.select_operating_point({4: 95, 8: 93, 16: 91}, {}), None),
    (e.select_operating_point({4: 45}, {(4, 2.7): 40}), None),
    (e.decide_subject(I(4, 1, 7), I(0, -1, 1), 2.0), "MATERIAL"),
    (e.decide_subject(I(0, -1, 2.9), I(0, -1, 2.9), 2.0), "KILL"),
    (e.decide_subject(I(0, -1, 2.9), I(0, -1, 2.9), 1.2), "SELF_NORMALIZED"),
    (e.decide_subject(I(0, -1, 2.9), I(5, 2, 8), 1.2), "MASKED"),
    (e.decide_subject(I(0, -1, 2.9), I(2, 0.5, 3.5), 2.0), "PARITY_NULL"),
    (e.decide_subject(I(2, -1, 5), I(0, -1, 1), 2.0), "INCONCLUSIVE"),
    (e.decide_overall({"G": "KILL", "R": "KILL"}), "KILL"),
    (e.decide_overall({"G": "KILL", "R": "MASKED"}), "LOSS_NULL_MIXED"),
    (e.decide_overall({"G": "MATERIAL", "R": "MASKED"}), "SPLIT"),
    (e.decide_overall({"G": "MATERIAL", "R": "INCONCLUSIVE"}), "INCONCLUSIVE"),
    (e.decide_overall({"G": "NOT_ADMISSIBLE", "R": "KILL"}), "NOT_ADMISSIBLE"),
]
bad = [i for i, (got, want) in enumerate(checks) if got != want]
rng = np.random.default_rng(0)
n = 400
can, dec, cl, nat = [(rng.random(n) < p) * 100.0 for p in (0.8, 0.75, 0.6, 0.55)]
c = e.contrasts(can, dec, cl, nat)
ident = bool(np.allclose(c["TE"], c["PNIE"] + c["PNDE"] + c["INT"]))
art = np.repeat(np.arange(100), 4)
r = e.read_subject(can, dec, cl, nat, art, 2.7, 2.0)
x = cl - nat
iv = e.cluster_normal([x[art == a] for a in range(100)], scale=e.secant_scale(2.7))
_, _, h = e.cluster_normal_matrix(x.reshape(1, 100, 4), scale=e.secant_scale(2.7))
agree = abs(r["estimates"]["TNIE"]["hi"] - iv.hi) < 1e-12 and abs(h[0] - iv.hi) < 1e-12
print({"rule_checks": len(checks), "failed": bad, "identity_exact": ident, "interval_paths_agree": agree,
       "line_raw_points_per_log_f": e.LINE * e.GUESS_SCALE})
sys.exit(0 if not bad and ident and agree else 1)
