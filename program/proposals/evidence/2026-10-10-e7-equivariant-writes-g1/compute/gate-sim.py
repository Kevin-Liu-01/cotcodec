#!/usr/bin/env python3
"""S1: operating characteristics of the E7 G1 decision rule (draft e7-equivariant-writes-g1-v1).

Simulates the registered per-seed classification (ABOVE / BELOW / UNRESOLVED
against each line, from a 90% interval clustered by key sentence) and the
registered verdict rule over three seeds (a line passes when at least two
seeds are ABOVE and none is BELOW), under assumed distributions. Nothing
here is a measurement of any model. Every distribution below is an assumption,
stated in the output.

Instrument layout simulated (registration "Instrument"):
  B3 (state-necessary bin, the gate): 4 monolingual cells x 500 prompts and
  6 cross-lingual cells (En->De, De->En, En->Zh, Zh->En, En->Th, Th->En) with
  300, 300, 500, 500, 500, 500 prompts after the surface-disjoint filter
  (the En-De counts are an assumed survival rate); B1 (direct bin) monolingual
  positive control: 4 cells x 250 prompts. Key sentences are shared across
  cells and across the three seeds (one sealed prompt set); the cluster is the
  key sentence.

Outcome model (assumed): per prompt, P(target code exact) = expit(a_s +
delta_cell + u_sentence), u ~ N(0, 1) shared across cells and seeds, a_s set
so that the pooled mean of cell means equals the seed's true rate. A
non-target answer is one of the seven in-context distractor codes with
probability 0.5 (uniform among them), otherwise no in-context code. The
binding margin per prompt is EM(target) minus the mean EM over the seven
distractor codes.

Intervals in the simulation are the cluster-robust (CR1) normal 90% interval
of a mean of cell means; the registered analysis uses a sentence-cluster
bootstrap (B = 2,000). Section `coverage` compares the two.

Seeds: replicates are split over three generators seeded 42, 43 and 44.

Usage: gate-sim.py <output.json> [replicates_per_scenario] [workers]
"""

from __future__ import annotations

import json
import math
import sys
import time

import numpy as np

LINES = {"I1": 0.80, "MONO": 0.60, "CROSS": 0.15, "BIND": 0.0}
FUTILITY_MONO_UB = 0.30
Z90 = 1.6448536269514722
N_SENT = 900
B3_MONO = [500, 500, 500, 500]
B3_CROSS = [300, 300, 500, 500, 500, 500]
B1_MONO = [250, 250, 250, 250]
MONO_OFF = np.array([0.3, 0.0, -0.1, -0.2])
CROSS_OFF = np.array([0.2, 0.0, 0.1, -0.1, -0.2, 0.0])
P1_OFF = np.array([0.2, 0.0, -0.1, -0.1])
SIGMA_U = 1.0
Q_DISTRACTOR = 0.5
SEEDS = (42, 43, 44)

_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(60)
_GH_W = _GH_W / _GH_W.sum()


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def pooled_true(a: float, offsets: np.ndarray) -> float:
    vals = expit(a + offsets[:, None] + SIGMA_U * _GH_X[None, :]) @ _GH_W
    return float(vals.mean())


_A_GRID = np.linspace(-15.0, 15.0, 6001)
_LOOKUP: dict[tuple, np.ndarray] = {}


def intercept_for(mu: float, offsets: np.ndarray) -> float:
    key = tuple(np.round(offsets, 6))
    if key not in _LOOKUP:
        vals = expit(_A_GRID[:, None, None] + offsets[None, :, None] + SIGMA_U * _GH_X[None, None, :]) @ _GH_W
        _LOOKUP[key] = vals.mean(axis=1)
    return float(np.interp(mu, _LOOKUP[key], _A_GRID))


class Design:
    """One sealed prompt set: queried sentence ids per cell and sentence effects."""

    def __init__(self, rng: np.random.Generator, n_scale: float = 1.0):
        self.u = rng.normal(0.0, SIGMA_U, N_SENT)
        def cells(sizes):
            return [rng.choice(N_SENT, size=max(1, int(round(n * n_scale))), replace=False) for n in sizes]
        self.mono = cells(B3_MONO)
        self.cross = cells(B3_CROSS)
        self.p1 = cells(B1_MONO)


def mean_of_means_ci(cells_y: list[np.ndarray], cells_id: list[np.ndarray]) -> tuple[float, float, float]:
    k = len(cells_y)
    est = float(np.mean([y.mean() for y in cells_y]))
    score = np.zeros(N_SENT)
    used = np.zeros(N_SENT, dtype=bool)
    for y, ids in zip(cells_y, cells_id):
        e = (y - y.mean()) / (len(y) * k)
        np.add.at(score, ids, e)
        used[ids] = True
    g = int(used.sum())
    var = g / max(g - 1, 1) * float((score[used] ** 2).sum())
    se = math.sqrt(var)
    return est, est - Z90 * se, est + Z90 * se


def classify(lo: float, hi: float, line: float, strict: bool = False) -> str:
    if (lo > line) if strict else (lo >= line):
        return "ABOVE"
    if hi < line:
        return "BELOW"
    return "UNRESOLVED"


def draw_cells(rng, design, ids_list, offsets, mu, binding_free_copy: float | None = None):
    a = intercept_for(min(max(mu, 0.002), 0.998), offsets)
    ys, betas = [], []
    for ids, off in zip(ids_list, offsets):
        if binding_free_copy is not None:
            out = rng.random(len(ids))
            # copy an in-context code uniformly among 8 with probability c, else no in-context code
            copied = out < binding_free_copy
            slot = rng.integers(0, 8, len(ids))
            y = (copied & (slot == 0)).astype(float)
            dist_hit = (copied & (slot != 0)).astype(float)
        else:
            p = expit(a + off + design.u[ids])
            y = (rng.random(len(ids)) < p).astype(float)
            dist_hit = ((y == 0) & (rng.random(len(ids)) < Q_DISTRACTOR)).astype(float)
        ys.append(y)
        betas.append(y - dist_hit / 7.0)
    return ys, betas


def seed_lines(rng, design, mu_p1, mu_mono, mu_cross, binding_free_copy=None):
    p1_y, _ = draw_cells(rng, design, design.p1, P1_OFF, mu_p1)
    mono_y, _ = draw_cells(rng, design, design.mono, MONO_OFF, mu_mono)
    cross_y, cross_b = draw_cells(rng, design, design.cross, CROSS_OFF, mu_cross, binding_free_copy)
    out = {}
    for name, ys, ids, strict in (("I1", p1_y, design.p1, False), ("MONO", mono_y, design.mono, False),
                                  ("CROSS", cross_y, design.cross, False), ("BIND", cross_b, design.cross, True)):
        est, lo, hi = mean_of_means_ci(ys, ids)
        out[name] = {"est": est, "lo": lo, "hi": hi, "cls": classify(lo, hi, LINES[name], strict)}
    return out


def verdict(per_seed: list[dict]) -> str:
    cls = {line: [s[line]["cls"] for s in per_seed] for line in LINES}
    if cls["I1"].count("BELOW") >= 2:
        return "INSTRUMENT_INVALID"
    if all(cls[line].count("ABOVE") >= 2 and "BELOW" not in cls[line] for line in LINES):
        return "PASS"
    for line in ("MONO", "CROSS"):
        if "ABOVE" in cls[line] and "BELOW" in cls[line]:
            return "LOTTERY"
    if cls["MONO"].count("BELOW") >= 2:
        return "FAIL_MONO"
    if cls["MONO"].count("ABOVE") >= 2 and (cls["CROSS"].count("BELOW") >= 2 or cls["BIND"].count("BELOW") >= 2):
        return "FAIL_CROSS"
    return "INCONCLUSIVE"


VERDICTS = ("PASS", "FAIL_MONO", "FAIL_CROSS", "LOTTERY", "INCONCLUSIVE", "INSTRUMENT_INVALID", "FUTILITY_STOP")


def run_scenario(reps: int, seed_mu, n_scale: float = 1.0, binding_free_copy=None, futility=True) -> dict:
    """seed_mu(rng) -> list of three (mu_p1, mu_mono, mu_cross) tuples."""
    counts = {v: 0 for v in VERDICTS}
    counts_nofut = {v: 0 for v in VERDICTS}
    per_reps = [reps // 3 + (1 if i < reps % 3 else 0) for i in range(3)]
    for stream, r in zip(SEEDS, per_reps):
        rng = np.random.default_rng(stream)
        for _ in range(r):
            design = Design(rng, n_scale)
            mus = seed_mu(rng)
            seeds = [seed_lines(rng, design, *m, binding_free_copy=binding_free_copy) for m in mus]
            v = verdict(seeds)
            counts_nofut[v] += 1
            if futility and seeds[0]["MONO"]["hi"] < FUTILITY_MONO_UB:
                counts["FUTILITY_STOP"] += 1
            else:
                counts[v] += 1
    return {"with_futility": {k: round(c / reps, 4) for k, c in counts.items()},
            "without_futility": {k: round(c / reps, 4) for k, c in counts_nofut.items()}}


def gaussian(mu_p1, mu_mono, mu_cross, sd):
    def f(rng):
        z = rng.normal(size=(3, 3)) * sd
        return [tuple(float(np.clip(m + z[i, j], 0.002, 0.998)) for j, m in enumerate((mu_p1, mu_mono, mu_cross)))
                for i in range(3)]
    return f


def lockin(pi, locked, unlocked, which=("p1", "mono", "cross")):
    def f(rng):
        out = []
        for _ in range(3):
            lk = rng.random() < pi
            out.append(tuple(locked[i] if (lk and name in which) or name not in which else unlocked[i]
                             for i, name in enumerate(("p1", "mono", "cross"))))
        return out
    return f


def coverage_check(n_draws: int, B: int) -> dict:
    """CR1 normal interval vs sentence-cluster Poisson bootstrap at the cross line, one seed per draw."""
    rng = np.random.default_rng(42)
    mu = LINES["CROSS"]
    cover_n = cover_b = agree = 0
    for _ in range(n_draws):
        design = Design(rng)
        ys, _ = draw_cells(rng, design, design.cross, CROSS_OFF, mu)
        est, lo, hi = mean_of_means_ci(ys, design.cross)
        sums = np.zeros((len(ys), N_SENT))
        cnts = np.zeros((len(ys), N_SENT))
        for k, (y, ids) in enumerate(zip(ys, design.cross)):
            np.add.at(sums[k], ids, y)
            np.add.at(cnts[k], ids, 1.0)
        w = rng.poisson(1.0, size=(B, N_SENT)).astype(float)
        stat = np.mean((w @ sums.T) / np.maximum(w @ cnts.T, 1e-12), axis=1)
        blo, bhi = np.quantile(stat, [0.05, 0.95])
        cover_n += lo <= mu <= hi
        cover_b += blo <= mu <= bhi
        agree += classify(lo, hi, mu) == classify(blo, bhi, mu)
    return {"draws": n_draws, "bootstrap_B": B, "true_rate": mu,
            "coverage_cr1_normal_90": round(cover_n / n_draws, 3),
            "coverage_poisson_bootstrap_90": round(cover_b / n_draws, 3),
            "classification_agreement_at_the_line": round(agree / n_draws, 3),
            "note": "Coverage is against the population rate; the realized-sentence estimand differs by sentence sampling, which both intervals include."}


def halfwidths() -> dict:
    rng = np.random.default_rng(42)
    out = {}
    for name, mu in (("CROSS_at_0.15", 0.15), ("MONO_at_0.60", 0.60)):
        hw = []
        for _ in range(300):
            design = Design(rng)
            if name.startswith("CROSS"):
                ys, _ = draw_cells(rng, design, design.cross, CROSS_OFF, mu)
                _, lo, hi = mean_of_means_ci(ys, design.cross)
            else:
                ys, _ = draw_cells(rng, design, design.mono, MONO_OFF, mu)
                _, lo, hi = mean_of_means_ci(ys, design.mono)
            hw.append((hi - lo) / 2)
        out[name] = {"mean_90_halfwidth": round(float(np.mean(hw)), 4), "p95": round(float(np.quantile(hw, 0.95)), 4)}
    return out


def futility_single_seed(reps: int) -> dict:
    out = {}
    for mu in (0.10, 0.20, 0.25, 0.28, 0.30, 0.35, 0.40, 0.60):
        stops = 0
        for stream in SEEDS:
            rng = np.random.default_rng(stream)
            for _ in range(reps // 3):
                design = Design(rng)
                ys, _ = draw_cells(rng, design, design.mono, MONO_OFF, mu)
                _, _, hi = mean_of_means_ci(ys, design.mono)
                stops += hi < FUTILITY_MONO_UB
        out[str(mu)] = round(stops / (3 * (reps // 3)), 4)
    return out


def _task(args):
    path, kind, params, kw = args
    builders = {"gaussian": gaussian, "lockin": lockin}
    return path, run_scenario(kw.pop("reps"), builders[kind](*params), **kw)


def main() -> int:
    out_path = sys.argv[1]
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    t0 = time.time()
    res: dict = {
        "script": "gate-sim.py", "replicates_per_scenario": reps, "seeds": list(SEEDS),
        "lines": LINES, "futility_mono_ub": FUTILITY_MONO_UB,
        "pass_rule": "a line passes when at least two of three seeds are ABOVE and none is BELOW; PASS needs I1, MONO, CROSS and BIND to pass",
        "assumptions": {
            "eligible_key_sentences": N_SENT, "b3_mono_cells": B3_MONO, "b3_cross_cells": B3_CROSS,
            "b1_mono_cells": B1_MONO, "cell_offsets_logit": {"mono": MONO_OFF.tolist(), "cross": CROSS_OFF.tolist(), "p1": P1_OFF.tolist()},
            "sentence_effect_sd_logit": SIGMA_U, "distractor_share_of_non_target_answers": Q_DISTRACTOR,
            "seed_variation": "Gaussian on the probability scale (sd listed per scenario), or a two-point lock-in mixture",
            "interval_in_simulation": "CR1 cluster-robust normal 90% (registered analysis: sentence-cluster bootstrap, B = 2,000)",
            "common_random_numbers": "every scenario restarts the generators seeded 42, 43, 44",
        },
    }
    tasks = []
    for sd in (0.0, 0.03, 0.06, 0.10):
        for m in (0.30, 0.45, 0.50, 0.55, 0.58, 0.60, 0.62, 0.65, 0.70, 0.80):
            tasks.append((("mono_oc", f"sd={sd}", str(m)), "gaussian", (0.95, m, 0.30, sd), {"reps": reps}))
        for c in (0.05, 0.10, 0.125, 0.14, 0.15, 0.16, 0.18, 0.20, 0.25):
            tasks.append((("cross_oc", f"sd={sd}", str(c)), "gaussian", (0.95, 0.85, c, sd), {"reps": reps}))
    for p in (0.60, 0.70, 0.75, 0.78, 0.80, 0.82, 0.85, 0.90):
        tasks.append((("i1_oc", str(p)), "gaussian", (p, 0.85, 0.30, 0.03), {"reps": reps}))
    for name, params in (("all_lines_plus_5pts_sd0.03", (0.85, 0.65, 0.20, 0.03)),
                         ("all_lines_plus_10pts_sd0.03", (0.90, 0.70, 0.25, 0.03)),
                         ("all_lines_plus_5pts_sd0.06", (0.85, 0.65, 0.20, 0.06)),
                         ("all_lines_at_line_sd0.03", (0.80, 0.60, 0.15, 0.03)),
                         ("cross_minus_3pts_mono_plus_10_sd0.03", (0.95, 0.70, 0.12, 0.03))):
        tasks.append((("pass_power", name), "gaussian", params, {"reps": reps}))
    for pi in (0.1, 0.3, 0.5, 0.7, 0.9, 1.0):
        tasks.append((("lockin_both_lines", str(pi)), "lockin", (pi, (0.95, 0.85, 0.25), (0.95, 0.15, 0.06), ("mono", "cross")), {"reps": reps}))
        tasks.append((("lockin_cross_only", str(pi)), "lockin", (pi, (0.95, 0.85, 0.25), (0.95, 0.85, 0.06), ("cross",)), {"reps": reps}))
    for c in (0.5, 0.8, 1.0):
        tasks.append((("binding_free_null", f"copy_prob={c}"), "gaussian", (0.95, 0.85, 0.0, 0.0), {"reps": reps, "binding_free_copy": c}))
    for c in (0.10, 0.125, 0.15, 0.18, 0.20, 0.25):
        tasks.append((("n_half_sensitivity_cross_sd0.03", str(c)), "gaussian", (0.95, 0.85, c, 0.03), {"reps": reps, "n_scale": 0.5}))
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(workers) as pool:
        for path, val in pool.imap(_task, tasks):
            node = res
            for key in path[:-1]:
                node = node.setdefault(key, {})
            node[path[-1]] = val
    res["binding_free_null_note"] = ("Cross answers come from copying one of the 8 in-context codes uniformly (no key binding); "
                                     "the target is hit with probability c/8 <= 0.125, below the 0.15 cross line.")
    res["futility_single_seed_stop_prob"] = futility_single_seed(reps)
    res["halfwidths"] = halfwidths()
    res["coverage"] = coverage_check(300, 2000)
    res["runtime_seconds"] = round(time.time() - t0, 1)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print(f"wrote {out_path} in {res['runtime_seconds']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
