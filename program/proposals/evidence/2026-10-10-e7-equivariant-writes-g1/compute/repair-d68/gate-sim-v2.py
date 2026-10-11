#!/usr/bin/env python3
"""S1v2: operating characteristics of the registration-v2 decision rule under the registered estimator (D68 repair).

Wave 1's S1 (`../gate-sim.py`, kept unedited) classified with a CR1 normal
interval, assumed a 900-sentence pool and 300/500-prompt cross cells, had no
surface-cue null and did not simulate the CUT and ABLATION checks. This script:

* uses the REGISTERED estimator for every classification: per seed and line, the
  equal-weight mean of cell means with a 90% percentile bootstrap that resamples
  key-sentence ids with replacement (multinomial), every prompt that queries a
  drawn sentence moving with it in every cell, B = 2,000, bootstrap seed 42 (the
  registered seed, so the resampling matrix is fixed, as it will be in the
  analysis);
* takes the pool and cell sizes from P1 (`instrument-pool-v2.json`, the measured
  NTREX-128 test half under the v2 builder) and the surface-oracle rates (real
  and decoy queries) from the same file;
* simulates the v2 lines MONO (B3 monolingual), CROSS, BIND and SEM (B3
  cross-script: En->Zh, Zh->En, En->Th, Th->En; SEM is ABOVE when its lower
  bound is at least 0.03), DEC (decoy margin, for the surface sub-label) and I1
  (B1 monolingual, which v2 uses only to gate negative verdicts), and the v2
  verdict order;
* gates INSTRUMENT_INVALID on I1 below an in-window floor of 0.50 (with MONO
  below its line); the 0.80 I1 line is reported, not decision-bearing;
* simulates the v1 rule (CUT first, then I1, then PASS on CROSS and BIND
  without SEM) under the wave-1 failure modes, to show what v2 removes: a
  surface-only model under v1's uniform distractors, a state-carrying model
  under a leaky single-reset cut, and an in-window anomaly with MONO passing;
* reports the probability that the gate reaches a decisive verdict under stated
  world scenarios, and its prior-weighted average.

The REACH and ISO checks of v2 are deterministic logit-invariance checks
(S3v2, `reach-cut-v2.py`, proves that a correct harness passes them for any
weights); they are not statistical and therefore do not appear here except as
the v1 comparison.

Outcome model (assumed, as wave 1): per prompt P(target exact) = expit(a_s +
delta_cell + u_sentence), u ~ N(0, 1) shared across cells and seeds; a
non-target answer is one of the seven in-context distractor codes with
probability 0.5 (uniform), otherwise no in-context code. A decoy query (no
key's translation) under a semantic model copies an in-context code at the same
overall rate, uniformly over the eight codes. A surface-only model always
outputs an in-context code and picks the target with the measured surface-oracle
rate (clogit, P1) for real and decoy queries respectively; a sensitivity family
lets the decoy reproduce only a share phi of the real query's surface excess
over 1/8. Seed variation:
Gaussian on the probability scale, or a two-point lock-in mixture.

Usage: gate-sim-v2.py <instrument-pool-v2.json> <output.json> [replicates] [workers]
"""

from __future__ import annotations

import json
import math
import sys
import time

import numpy as np

LINES = {"I1": 0.80, "MONO": 0.60, "CROSS": 0.15, "BIND": 0.0, "SEM": 0.03, "DEC": 0.0}
I1_FLOOR = 0.50                     # INSTRUMENT_INVALID needs I1 BELOW this floor (and MONO BELOW its line)
STRICT = {"BIND", "DEC"}            # ABOVE needs lo > 0; every other line needs lo >= its threshold
FUTILITY_MONO_UB = 0.30
B = 2000
Q_DISTRACTOR = 0.5
SIGMA_U = 1.0
SEEDS = (42, 43, 44)
MONO_OFF = np.array([0.3, 0.0, -0.1, -0.2])
CROSS_OFF = np.array([0.1, -0.1, 0.0, -0.2])
P1_OFF = np.array([0.2, 0.0, -0.1, -0.1])
CROSS_CELLS = ["eng->zho", "zho->eng", "eng->tha", "tha->eng"]

_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(60)
_GH_W = _GH_W / _GH_W.sum()
_A_GRID = np.linspace(-15.0, 15.0, 6001)
_LOOKUP: dict = {}


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def intercept_for(mu, offsets):
    key = tuple(np.round(offsets, 6))
    if key not in _LOOKUP:
        vals = expit(_A_GRID[:, None, None] + offsets[None, :, None] + SIGMA_U * _GH_X[None, None, :]) @ _GH_W
        _LOOKUP[key] = vals.mean(axis=1)
    return float(np.interp(min(max(mu, 0.002), 0.998), _LOOKUP[key], _A_GRID))


class Design:
    """The sealed prompt set (fixed, seed 42) and the registered bootstrap matrix (fixed, seed 42)."""

    def __init__(self, pool):
        self.G = int(pool["test_half_eligible"])
        rng = np.random.default_rng(42)
        n_mono = min(500, self.G)
        self.mono = [rng.choice(self.G, n_mono, replace=False) for _ in range(4)]
        self.b1 = [rng.choice(self.G, 250, replace=False) for _ in range(4)]
        self.cross_sizes = [int(pool["cells"][c]["v2"]["prompts_test_half"]) for c in CROSS_CELLS]
        self.cross = [rng.choice(self.G, n, replace=False) for n in self.cross_sizes]
        self.o_real_v2 = np.array([pool["cells"][c]["v2"]["oracle_top1_real_query"]["clogit"] for c in CROSS_CELLS])
        self.o_dec_v2 = np.array([pool["cells"][c]["v2"]["oracle_top1_decoy_query"]["clogit"] for c in CROSS_CELLS])
        self.o_real_v1 = np.array([pool["cells"][c]["v1"]["oracle_top1_real_query"]["clogit"] for c in CROSS_CELLS])
        self.cross_sizes_v1 = [min(500, int(pool["cells"][c]["v1"]["prompts_test_half"])) for c in CROSS_CELLS]
        self.cross_v1 = [rng.choice(self.G, n, replace=False) for n in self.cross_sizes_v1]
        brng = np.random.default_rng(42)
        self.W = brng.multinomial(self.G, np.full(self.G, 1.0 / self.G), size=B).astype(np.float32)   # (B, G), exact small integers
        self.cells = {"I1": self.b1, "MONO": self.mono, "CROSS": self.cross}
        self._wn = {}

    def wn(self, ids_list, tag):
        if tag not in self._wn:
            N = np.zeros((self.G, len(ids_list)))
            for k, ids in enumerate(ids_list):
                N[ids, k] = 1.0
            self._wn[tag] = (self.W @ N, N)
        return self._wn[tag]


_QIDX = (int(math.floor(0.05 * (B - 1))), int(math.floor(0.95 * (B - 1))))


def boot_lines(design, cols, tags):
    """cols: dict line -> (G x k) per-sentence sums; tags: dict line -> (cells, tag). Returns est, lo, hi per line.
    All lines share the registered resampling matrix W; percentiles use numpy's default linear interpolation."""
    names = list(cols)
    S_all = np.concatenate([cols[n] for n in names], axis=1)
    key = tuple(tags[n][1] for n in names)
    if key not in design._wn:
        WNs, Ns = zip(*[design.wn(*tags[n]) for n in names])
        design._wn[key] = (np.concatenate(WNs, axis=1), np.concatenate(Ns, axis=1))
    WN, N = design._wn[key]
    ratio = (design.W @ S_all.astype(np.float32)).astype(np.float64) / np.maximum(WN, 1e-12)
    est_cells = S_all.sum(0) / N.sum(0)
    out = {}
    j = 0
    stats = []
    for n in names:
        k = cols[n].shape[1]
        stats.append(ratio[:, j:j + k].mean(1))
        out[n] = [float(est_cells[j:j + k].mean())]
        j += k
    stats = np.stack(stats, 1)                                   # (B, lines)
    lo_i, hi_i = _QIDX
    part = np.partition(stats, [lo_i, lo_i + 1, hi_i, hi_i + 1], axis=0)
    flo, fhi = 0.05 * (B - 1) - lo_i, 0.95 * (B - 1) - hi_i
    lo = part[lo_i] + flo * (part[lo_i + 1] - part[lo_i])
    hi = part[hi_i] + fhi * (part[hi_i + 1] - part[hi_i])
    for c, n in enumerate(names):
        out[n] = (out[n][0], float(lo[c]), float(hi[c]))
    return out


def classify(line, lo, hi):
    thr = LINES[line]
    if (lo > thr) if line in STRICT else (lo >= thr):
        return "ABOVE"
    if hi < thr:
        return "BELOW"
    return "UNRESOLVED"


def bern(rng, p):
    return (rng.random(p.shape) < p).astype(float)


def cell_sums(design, ids, vals):
    S = np.zeros(design.G)
    np.add.at(S, ids, vals)
    return S


def seed_draw(rng, design, u, mu_i1, mu_mono, cross_spec, v1=False, cut_leak=None):
    """One seed's per-sentence sums for every line. cross_spec: ("semantic", mu) | ("surface",) | ("mixed", lam)
    | ("copy", c)."""
    cols = {}
    a = intercept_for(mu_i1, P1_OFF)
    cols["I1"] = np.stack([cell_sums(design, ids, bern(rng, expit(a + P1_OFF[k] + u[ids])))
                           for k, ids in enumerate(design.b1)], 1)
    a = intercept_for(mu_mono, MONO_OFF)
    mono_y, mono_m = [], []
    for k, ids in enumerate(design.mono):
        p = expit(a + MONO_OFF[k] + u[ids])
        y = bern(rng, p)
        dist = (y == 0) & (rng.random(len(ids)) < Q_DISTRACTOR)
        mono_y.append(cell_sums(design, ids, y))
        mono_m.append(cell_sums(design, ids, y - dist / 7.0))
    cols["MONO"] = np.stack(mono_y, 1)
    cross_ids = design.cross_v1 if v1 else design.cross
    o_real = design.o_real_v1 if v1 else design.o_real_v2
    o_dec = design.o_dec_v2
    cy, cb, cs, cd, cut_m = [], [], [], [], []
    kind = cross_spec[0]
    if kind == "semantic":
        a = intercept_for(cross_spec[1], CROSS_OFF)
    for k, ids in enumerate(cross_ids):
        n = len(ids)
        if kind == "semantic":
            p = expit(a + CROSS_OFF[k] + u[ids])
            y = bern(rng, p)
            dist = ((y == 0) & (rng.random(n) < Q_DISTRACTOR)).astype(float)
            copy_rate = p + (1 - p) * Q_DISTRACTOR
            dec_code = rng.random(n) < copy_rate
            dec_slot = rng.integers(0, 8, n)
            d_t = (dec_code & (dec_slot == 0)).astype(float)
            d_j = (dec_code & (dec_slot != 0)).astype(float)
        elif kind in ("surface", "mixed", "surface_phi"):
            lam = cross_spec[1] if kind == "mixed" else 0.0
            if kind == "surface_phi":
                # sensitivity: the decoy reproduces only a share phi of the real query's surface excess
                o_dec = 0.125 + cross_spec[1] * (o_real - 0.125)
            sem = rng.random(n) < lam
            y = np.where(sem, 1.0, bern(rng, np.full(n, o_real[k])))
            dist = 1.0 - y
            # decoy: the semantic channel has no target (uniform over 8); the surface channel picks the target
            # with the decoy oracle rate
            dsem = rng.random(n) < lam
            d_t = np.where(dsem, (rng.integers(0, 8, n) == 0).astype(float), bern(rng, np.full(n, o_dec[k])))
            d_j = 1.0 - d_t
        elif kind == "copy":
            c = cross_spec[1]
            code = rng.random(n) < c
            slot = rng.integers(0, 8, n)
            y = (code & (slot == 0)).astype(float)
            dist = (code & (slot != 0)).astype(float)
            dcode = rng.random(n) < c
            dslot = rng.integers(0, 8, n)
            d_t = (dcode & (dslot == 0)).astype(float)
            d_j = (dcode & (dslot != 0)).astype(float)
        else:
            raise ValueError(kind)
        m_real = y - dist / 7.0
        m_dec = d_t - d_j / 7.0
        cy.append(cell_sums(design, ids, y))
        cb.append(cell_sums(design, ids, m_real))
        cs.append(cell_sums(design, ids, m_real - m_dec))
        cd.append(cell_sums(design, ids, m_dec))
    cols["CROSS"] = np.stack(cy, 1)
    cols["BIND"] = np.stack(cb, 1)
    cols["SEM"] = np.stack(cs, 1)
    cols["DEC"] = np.stack(cd, 1)
    if cut_leak is not None:
        # v1 single-reset cut on B3 (v1 pooled MONO and CROSS cells; the MONO cells, whose margin dominates the
        # pool, are simulated): the cut leaves a share `cut_leak` of each prompt's above-floor target probability
        # (S3v2: the single reset leaves live paths)
        for k, ids in enumerate(design.mono):
            p = expit(intercept_for(mu_mono, MONO_OFF) + MONO_OFF[k] + u[ids])
            pc = cut_leak * p + (1 - cut_leak) * (p + (1 - p) * Q_DISTRACTOR) / 8.0
            yc = bern(rng, pc)
            copy_rate = p + (1 - p) * Q_DISTRACTOR
            dc = ((yc == 0) & (rng.random(len(ids)) < (copy_rate - pc) / np.maximum(1 - pc, 1e-9))).astype(float)
            cut_m.append(cell_sums(design, ids, yc - dc / 7.0))
        cols["CUT"] = np.stack(cut_m, 1)
    tags = {"I1": (design.b1, "b1"), "MONO": (design.mono, "mono")}
    tg = (cross_ids, "cross_v1" if v1 else "cross")
    for line in ("CROSS", "BIND", "SEM", "DEC"):
        tags[line] = tg
    if cut_leak is not None:
        tags["CUT"] = (design.mono, "mono")
    res = boot_lines(design, cols, tags)
    return res


def verdict_v2(cls, futility_stop=False, seed42_i1=None):
    """cls["I1F"] is I1 classified against the in-window floor I1_FLOOR; seed42_i1 is seed 42's I1F class."""
    if futility_stop:
        return "INSTRUMENT_INVALID" if seed42_i1 == "BELOW" else "FAIL_MONO"
    def passes(line):
        return cls[line].count("ABOVE") >= 2 and "BELOW" not in cls[line]
    if all(passes(l) for l in ("MONO", "CROSS", "BIND", "SEM")):
        return "PASS"
    for line in ("MONO", "CROSS"):
        if "ABOVE" in cls[line] and "BELOW" in cls[line]:
            return "LOTTERY"
    if passes("MONO"):
        if cls["CROSS"].count("BELOW") >= 2 or cls["BIND"].count("BELOW") >= 2:
            return "FAIL_CROSS"
        if (cls["CROSS"].count("ABOVE") >= 2 and cls["BIND"].count("ABOVE") >= 2 and not passes("SEM")
                and cls["DEC"].count("ABOVE") >= 2):
            return "FAIL_CROSS_SURFACE"
    if cls["I1F"].count("BELOW") >= 2 and cls["MONO"].count("BELOW") >= 2:
        return "INSTRUMENT_INVALID"
    if cls["MONO"].count("BELOW") >= 2:
        return "FAIL_MONO"
    return "INCONCLUSIVE"


def verdict_v1(cls, cut_fail_seeds=0):
    if cls["I1"].count("BELOW") >= 2 or cut_fail_seeds >= 2:
        return "INSTRUMENT_INVALID"
    def passes(line):
        return cls[line].count("ABOVE") >= 2 and "BELOW" not in cls[line]
    if all(passes(l) for l in ("I1", "MONO", "CROSS", "BIND")):
        return "PASS"
    for line in ("MONO", "CROSS"):
        if "ABOVE" in cls[line] and "BELOW" in cls[line]:
            return "LOTTERY"
    if cls["MONO"].count("BELOW") >= 2:
        return "FAIL_MONO"
    if cls["MONO"].count("ABOVE") >= 2 and (cls["CROSS"].count("BELOW") >= 2 or cls["BIND"].count("BELOW") >= 2):
        return "FAIL_CROSS"
    return "INCONCLUSIVE"


VERDICTS = ("PASS", "FAIL_MONO", "FAIL_CROSS", "FAIL_CROSS_SURFACE", "LOTTERY", "INCONCLUSIVE", "INSTRUMENT_INVALID")
DECISIVE = ("PASS", "FAIL_MONO", "FAIL_CROSS", "FAIL_CROSS_SURFACE", "LOTTERY")

_DESIGN = None


def _init(pool):
    global _DESIGN
    _DESIGN = Design(pool)


def seed_rates(rng, spec):
    """spec: {"kind": "gaussian", "mu": (i1, mono, cross_mu_or_None), "sd": s} or lock-in."""
    if spec["kind"] == "gaussian":
        out = []
        for _ in range(3):
            z = rng.normal(size=3) * spec["sd"]
            i1, mono, cr = spec["mu"]
            out.append((float(np.clip(i1 + z[0], 0.002, 0.998)), float(np.clip(mono + z[1], 0.002, 0.998)),
                        None if cr is None else float(np.clip(cr + z[2], 0.002, 0.998))))
        return out
    out = []
    for _ in range(3):
        lk = rng.random() < spec["pi"]
        out.append(spec["locked"] if lk else spec["unlocked"])
    return out


def run_scenario(args):
    name, spec, reps = args
    d = _DESIGN
    counts_v2 = {v: 0 for v in VERDICTS}
    counts_v2_sem0 = {v: 0 for v in VERDICTS}
    counts_v1 = {v: 0 for v in VERDICTS}
    fut = 0
    per = [reps // 3 + (1 if i < reps % 3 else 0) for i in range(3)]
    for stream, r in zip(SEEDS, per):
        rng = np.random.default_rng(stream)
        for _ in range(r):
            u = rng.normal(0, SIGMA_U, d.G)
            rates = seed_rates(rng, spec)
            per_seed, per_seed_v1, cut_fail = [], [], 0
            for (i1, mono, cr) in rates:
                cross_spec = spec.get("cross_spec") or ("semantic", cr)
                if cross_spec[0] == "semantic" and cr is not None:
                    cross_spec = ("semantic", cr)
                res = seed_draw(rng, d, u, i1, mono, cross_spec, v1=False)
                per_seed.append({k: classify(k, v[1], v[2]) if k in LINES else None for k, v in res.items()}
                                | {"_mono_hi": res["MONO"][2],
                                   "_i1f": "BELOW" if res["I1"][2] < I1_FLOOR else ("ABOVE" if res["I1"][1] >= I1_FLOOR else "UNRESOLVED"),
                                   "_sem0": "ABOVE" if res["SEM"][1] > 0 else ("BELOW" if res["SEM"][2] < 0 else "UNRESOLVED")})
                if spec.get("v1_compare"):
                    cs1 = spec.get("cross_spec_v1") or cross_spec
                    res1 = seed_draw(rng, d, u, i1, mono, cs1, v1=True, cut_leak=spec.get("cut_leak"))
                    c1 = {k: classify(k, v[1], v[2]) for k, v in res1.items() if k in LINES}
                    per_seed_v1.append(c1)
                    if "CUT" in res1 and res1["CUT"][1] > 0:
                        cut_fail += 1
            cls = {line: [s[line] for s in per_seed] for line in LINES}
            cls["I1F"] = [s["_i1f"] for s in per_seed]
            stop = per_seed[0]["_mono_hi"] < FUTILITY_MONO_UB
            fut += stop
            counts_v2[verdict_v2(cls, futility_stop=stop, seed42_i1=per_seed[0]["_i1f"])] += 1
            cls0 = dict(cls)
            cls0["SEM"] = [s["_sem0"] for s in per_seed]
            counts_v2_sem0[verdict_v2(cls0, futility_stop=stop, seed42_i1=per_seed[0]["_i1f"])] += 1
            if spec.get("v1_compare"):
                cls1 = {line: [s[line] for s in per_seed_v1] for line in ("I1", "MONO", "CROSS", "BIND")}
                counts_v1[verdict_v1(cls1, cut_fail)] += 1
    out = {"v2": {k: round(v / reps, 4) for k, v in counts_v2.items()}, "futility_stop_share": round(fut / reps, 4)}
    out["v2"]["DECISIVE"] = round(sum(counts_v2[v] for v in DECISIVE) / reps, 4)
    out["v2_if_SEM_threshold_were_0"] = {k: round(v / reps, 4) for k, v in counts_v2_sem0.items()}
    if spec.get("v1_compare"):
        out["v1"] = {k: round(v / reps, 4) for k, v in counts_v1.items()}
    out["spec"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in spec.items()}
    return name, out


def halfwidths_and_coverage(pool, reps=300):
    d = Design(pool)
    rng = np.random.default_rng(42)
    acc = {"MONO@0.60": [], "CROSS@0.15": [], "BIND@CROSS0.15": [], "SEM@CROSS0.15": []}
    cover = {"MONO@0.60": 0, "CROSS@0.15": 0}
    for _ in range(reps):
        u = rng.normal(0, SIGMA_U, d.G)
        res = seed_draw(rng, d, u, 0.95, 0.60, ("semantic", 0.15))
        acc["MONO@0.60"].append((res["MONO"][2] - res["MONO"][1]) / 2)
        acc["CROSS@0.15"].append((res["CROSS"][2] - res["CROSS"][1]) / 2)
        acc["BIND@CROSS0.15"].append((res["BIND"][2] - res["BIND"][1]) / 2)
        acc["SEM@CROSS0.15"].append((res["SEM"][2] - res["SEM"][1]) / 2)
        cover["MONO@0.60"] += res["MONO"][1] <= 0.60 <= res["MONO"][2]
        cover["CROSS@0.15"] += res["CROSS"][1] <= 0.15 <= res["CROSS"][2]
    return ({k: round(float(np.mean(v)), 4) for k, v in acc.items()},
            {k: round(v / reps, 3) for k, v in cover.items()})


def futility_single_seed(pool, reps=600):
    d = Design(pool)
    out = {}
    for mu in (0.10, 0.20, 0.25, 0.28, 0.30, 0.35, 0.40):
        rng = np.random.default_rng(42)
        stops = 0
        for _ in range(reps):
            u = rng.normal(0, SIGMA_U, d.G)
            res = seed_draw(rng, d, u, 0.95, mu, ("semantic", 0.10))
            stops += res["MONO"][2] < FUTILITY_MONO_UB
        out[str(mu)] = round(stops / reps, 4)
    return out


def main() -> int:
    pool = json.load(open(sys.argv[1]))
    out_path = sys.argv[2]
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    t0 = time.time()
    g = lambda i1, mono, cr, sd, **kw: {"kind": "gaussian", "mu": (i1, mono, cr), "sd": sd, **kw}
    sc = []
    for sd in (0.0, 0.03, 0.06):
        for m in (0.30, 0.45, 0.55, 0.58, 0.60, 0.62, 0.65, 0.70, 0.80):
            sc.append((f"mono_oc|sd={sd}|{m}", g(0.95, m, 0.30, sd)))
        for c in (0.05, 0.10, 0.125, 0.14, 0.15, 0.16, 0.18, 0.20, 0.25):
            sc.append((f"cross_oc|sd={sd}|{c}", g(0.95, 0.85, c, sd)))
    for sd in (0.0, 0.03):
        sc.append((f"surface_only_v2_and_v1|sd={sd}", g(0.95, 0.85, None, sd, cross_spec=("surface",), v1_compare=True)))
    for lam in (0.05, 0.10, 0.20):
        sc.append((f"mixed_semantic_lambda={lam}|sd=0.03", g(0.95, 0.85, None, 0.03, cross_spec=("mixed", lam))))
    for phi in (1.0, 0.8, 0.7, 0.6, 0.5, 0.4, 0.0):
        sc.append((f"surface_only_decoy_reproduces_phi={phi}|sd=0.03", g(0.95, 0.85, None, 0.03, cross_spec=("surface_phi", phi))))
    for c in (0.5, 0.8, 1.0):
        sc.append((f"binding_free_copy={c}", g(0.95, 0.85, None, 0.0, cross_spec=("copy", c), v1_compare=True)))
    for pi in (0.1, 0.3, 0.5, 0.7, 0.9, 1.0):
        sc.append((f"lockin_both|pi={pi}", {"kind": "lockin", "pi": pi, "locked": (0.95, 0.85, 0.25), "unlocked": (0.95, 0.15, 0.06)}))
    sc.append(("in_window_anomaly_mono_passes|I1=0.70", g(0.70, 0.80, 0.25, 0.03, v1_compare=True)))
    sc.append(("instrument_invalid_world|I1=0.40_MONO=0.10", g(0.40, 0.10, 0.06, 0.03, v1_compare=True)))
    sc.append(("weak_in_window_mono_fails|I1=0.60_MONO=0.20", g(0.60, 0.20, 0.08, 0.03, v1_compare=True)))
    sc.append(("mono_unresolved_with_I1_low|I1=0.70_MONO=0.58", g(0.70, 0.58, 0.20, 0.03, v1_compare=True)))
    for leak in (0.0, 0.02, 0.05, 0.10, 0.25, 1.0):
        sc.append((f"v1_cut_leak={leak}|pass_level_model", g(0.95, 0.80, 0.25, 0.03, v1_compare=True, cut_leak=leak)))
    worlds = {"W1_fail_mono": (0.90, 0.25, 0.08), "W2_fail_cross": (0.95, 0.80, 0.10), "W3_pass": (0.95, 0.80, 0.22),
              "W4_near_line": (0.95, 0.62, 0.16), "W7_instrument_invalid": (0.40, 0.10, 0.06)}
    for sd in (0.03, 0.06):
        for wname, mu in worlds.items():
            sc.append((f"world|{wname}|sd={sd}", g(*mu, sd)))
        sc.append((f"world|W5_lottery|sd={sd}", {"kind": "lockin", "pi": 0.5, "locked": (0.95, 0.85, 0.25), "unlocked": (0.95, 0.15, 0.06)}))
        sc.append((f"world|W6_surface|sd={sd}", g(0.95, 0.80, None, sd, cross_spec=("surface",))))
    import multiprocessing as mp
    res: dict = {"script": "gate-sim-v2.py", "replicates_per_scenario": reps, "seeds": list(SEEDS),
                 "estimator": "registered: equal-weight mean of cell means; 90% percentile bootstrap over key sentences (multinomial resampling of sentence ids, every prompt of a drawn sentence moves with it in every cell), B = 2,000, bootstrap seed 42 (fixed resampling matrix)",
                 "lines": LINES, "futility_mono_ub": FUTILITY_MONO_UB}
    d0 = Design(pool)
    res["design_from_P1"] = {"key_sentences_test_half": d0.G, "mono_cells": [len(x) for x in d0.mono],
                             "b1_cells": [len(x) for x in d0.b1], "cross_script_cells": dict(zip(CROSS_CELLS, d0.cross_sizes)),
                             "cross_script_cells_v1_comparison": dict(zip(CROSS_CELLS, d0.cross_sizes_v1)),
                             "surface_oracle_clogit_real_v2": dict(zip(CROSS_CELLS, d0.o_real_v2.tolist())),
                             "surface_oracle_clogit_decoy_v2": dict(zip(CROSS_CELLS, d0.o_dec_v2.tolist())),
                             "surface_oracle_clogit_real_v1": dict(zip(CROSS_CELLS, d0.o_real_v1.tolist()))}
    with mp.get_context("spawn").Pool(workers, initializer=_init, initargs=(pool,)) as p:
        for name, val in p.imap_unordered(run_scenario, [(n, s, reps) for n, s in sc]):
            node = res.setdefault("scenarios", {})
            node[name] = val
            print(name, json.dumps(val["v2"]), json.dumps(val.get("v1", {})), flush=True)
    res["scenarios"] = dict(sorted(res["scenarios"].items()))
    hw, cov = halfwidths_and_coverage(pool)
    res["mean_90_halfwidth_per_seed"] = hw
    res["coverage_registered_bootstrap_superpopulation"] = cov
    res["futility_single_seed_stop_prob"] = futility_single_seed(pool)
    prior = {"W1_fail_mono": 0.20, "W2_fail_cross": 0.40, "W3_pass": 0.10, "W4_near_line": 0.10, "W5_lottery": 0.15,
             "W7_instrument_invalid": 0.05}
    dec = {}
    for sd in (0.03, 0.06):
        tot = 0.0
        for wname, w in prior.items():
            tot += w * res["scenarios"][f"world|{wname}|sd={sd}"]["v2"]["DECISIVE"]
        dec[f"sd={sd}"] = round(tot, 4)
    res["prior_weighted_decisive"] = {"weights": prior, "by_seed_sd": dec,
                                      "definition": "decisive = PASS, FAIL_MONO (with futility), FAIL_CROSS (any sub-label, including surface) or LOTTERY; INSTRUMENT_INVALID and INCONCLUSIVE are not decisive"}
    res["runtime_seconds"] = round(time.time() - t0, 1)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print("prior-weighted decisive", dec, "runtime", res["runtime_seconds"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
