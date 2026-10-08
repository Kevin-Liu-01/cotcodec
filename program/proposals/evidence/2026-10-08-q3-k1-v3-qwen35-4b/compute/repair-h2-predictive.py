"""K1 v3 wave-1 repair: predictive pass probability of the H2 gate (H2b binds; H2a passes easily).

Uses the wave-1 normal approximation of the gate (synthesis-power-approximations.py: ICC from
the development read, 2,000 audit cells in 122 clusters, pass = 99 percent lower bound above 0
and point at least 5) and integrates it over the uncertainty in the true H2b effect instead of
plugging in the development point (the wave-1 defect named by the feasibility refuter).
Priors: flat (posterior N(8.57, 7.0^2) from the development read) and skeptical N(5, 5^2)
combined with the development likelihood. The development point is itself selected (the
lane advanced because H2 was not FAIL), so the flat-prior figure is an upper reference.
"""
import json, math
import numpy as np
from scipy import stats

sig2 = 4900.0
se_dev, m_dev, dev_point = 7.000556, 14, 8.571428571
v_cm = (se_dev * math.sqrt(20)) ** 2
rho = (v_cm / sig2 - 1 / m_dev) / (1 - 1 / m_dev)


def oc(true, cells, clusters):
    m = cells / clusters
    v = sig2 * (rho + (1 - rho) / m)
    se = math.sqrt(v / clusters)
    hw = stats.t.ppf(0.995, clusters - 1) * se
    return float(stats.norm.cdf((true - max(hw, 5.0)) / se)), se, hw


def predictive(mean, sd, cells, clusters):
    xs = np.linspace(mean - 6 * sd, mean + 6 * sd, 4001)
    w = stats.norm.pdf(xs, mean, sd)
    p = np.array([oc(x, cells, clusters)[0] for x in xs])
    return float((w * p).sum() / w.sum())


out = {"icc": rho}
prec = 1 / 5 ** 2 + 1 / se_dev ** 2
skept = ((5 / 25 + dev_point / se_dev ** 2) / prec, math.sqrt(1 / prec))
for cells, clusters, label in ((2000, 122, "2,000 audit cells (registered)"),
                               (3220, 122, "3,220 audit cells (all unseen CX)"),
                               (4000, 366, "2,000 audit + 2,000 primary (owner option, decision 64)")):
    out[label] = dict(
        plug_in_at_dev_point=oc(dev_point, cells, clusters)[0],
        se=oc(0, cells, clusters)[1], half_width=oc(0, cells, clusters)[2],
        predictive_flat=predictive(dev_point, se_dev, cells, clusters),
        predictive_skeptical_N5_5=predictive(skept[0], skept[1], cells, clusters),
        oc_at={str(t): oc(t, cells, clusters)[0] for t in (3, 5, 8.6, 10, 14)})
print(json.dumps(out, indent=1))
