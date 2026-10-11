#!/usr/bin/env python3
"""S1v2: does the v2 factorial identify what it claims, in a two-layer gated delta-rule toy
with state-dependent writes, read through the registered v2 estimator and decision path?

Wave-1 S1 had one layer, exogenous writes, no presence channel, a hard-coded f_p = 2.7 and
a "decay share" defined by the clamp itself. This version answers each point:

* Two layers. Layer 1 is a gated delta-rule memory over token keys and values. Layer 2's
  keys, values and write strengths are functions of layer 1's read at each position
  (k2 = norm(Pk k + gamma r1), v2 = norm(Pv v + gamma r1), beta2 = beta * (1 + kappa tanh(r1.e))),
  and its log-decay is state-dependent (g2 = g2_base * exp(zeta tanh(r1.e2))). So a clamp or
  transplant at layer 1 moves layer 2's writes and decays, as in the real checkpoints. Every
  intervention is applied layer by layer on live values, as registered (the clamp at layer 2
  rescales layer 2's live piece decays after layer 1 has been clamped).
* A presence channel: each candidate code that occurs in the context gets +PHI on its score
  (a real model gives a code it has seen far more likelihood than a fresh one). With fresh
  foils at K = 1 this makes K = 1 a presence test at ceiling, the wave-1 defect.
* The registered operating-point rule runs on held-out episodes (200 per cell), and the
  analysis uses only the selected (K_p, f_p).
* Ground truth is not the clamp. Each world's population contrasts are the means over a pool
  of 1,600 episodes (400 articles x 4); the registered estimator's operating characteristics
  at the registered sample size are measured by resampling N_ARTICLES_BY_F[f_p] articles
  (2,000 at f_p = 2.7, 3,000 at f_p = 2.0) with replacement from the pool (2,000
  replicates), so the pool means are the truth the estimator is scored against. (The pool is
  small because the development Mac was saturated by other work while this ran; the pool
  means carry their own sampling error, reported as the pool reading's interval.)
  Mechanism truths are also known by construction: in W2 and W4 (pieces share the token's
  decay, R_F = 1) both decay contrasts are exactly 0; in W1 (duplicate, write-normalised
  pieces) the re-segmented writes add almost nothing, so the interaction should be near 0
  and TNIE near PNIE; in W7 the decay is causally inert for the facts (tiny canonical decay),
  so both decay contrasts should be near 0 although R_F = m.

Arms per episode (paired: same facts, codes, target, passage, noise): CAN, NAT(f), CLAMP(f),
DEC(f) (canonical tokens, each token's log-decay set at each layer to the sum of its pieces'
live log-decays in NAT), SIL-NAT(f) and SIL-CLAMP(f) (passage writes silenced at both
layers), DOSE(f) (canonical tokens, every passage log-decay times f), and, for the v1
comparison, NAT and CLAMP at K = 1 with fresh foils.

Effect sizes are not calibrated to any checkpoint; zeros, signs, orderings and the decision
semantics are the evidence. Usage: python mech-sim-v2.py <out.json> [world ...]
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import estimator_v2 as ev2  # noqa: E402
import estimator as ev1  # noqa: E402  (wave-1 estimator, unedited)

D = 16
N_SPAN = 64
LEAD = 4
FACT_BETA = 0.95
FACT_G = 0.001
NOISE = 0.05
TB_LO, TB_HI = 0.05, 0.20  # passage write strengths
PHI = 2.0  # presence channel
GAMMA = 0.5  # layer-2 coupling to layer-1 reads
KAPPA = 0.5  # state dependence of layer-2 write strength
ZETA = 0.5  # state dependence of layer-2 decay
ALPHA2 = 1.0  # weight of the layer-2 read in the candidate score
POOL_ARTICLES = 400
N_HELDOUT = 200
RESAMPLE_ARTICLES = None  # registered N_ARTICLES_BY_F[f_p], resampled with replacement from the pool
RESAMPLE_REPS = 2000
SEED = 42

V1_WORLDS = ("W3_clock_and_interference", "W8_line")
BASE_G = 0.7 / N_SPAN  # canonical passage keeps about exp(-0.7) of a fact at layer 1
WORLDS = {
    "W1_per_token_clock": dict(lam=0.0, rho=1.0, wnorm=True, gscale=1.0),
    "W2_self_normalised_interference": dict(lam=1.0, rho=0.0, wnorm=False, gscale=1.0),
    "W3_clock_and_interference": dict(lam=0.0, rho=0.0, wnorm=False, gscale=1.0),
    "W4_null": dict(lam=1.0, rho=1.0, wnorm=True, gscale=1.0),
    "W5_legacy_duplicates": dict(lam=0.0, rho=1.0, wnorm=False, gscale=1.0),
    "W6_partial": dict(lam=0.5, rho=0.5, wnorm=False, gscale=1.0),
    "W7_decay_inert": dict(lam=0.0, rho=0.0, wnorm=False, gscale=0.02),
    "W8_line": dict(lam=0.0, rho=1.0, wnorm=True, gscale=None),  # gscale tuned to the line by a seeded scan
    # erase-dominated: strong passage writes, so the extra pieces' delta-rule erasures remove the
    # facts before restoring decay can help (wave-1 S1's negative interaction, here by design)
    "W9_erase_dominated": dict(lam=0.0, rho=0.0, wnorm=False, gscale=1.0, tb=(0.15, 0.30)),
}


def unit(x):
    return x / np.linalg.norm(x, axis=-1, keepdims=True)


class World:
    def __init__(self, name, spec, seed):
        self.name, self.spec = name, spec
        rng = np.random.default_rng([seed, 1])
        q, _ = np.linalg.qr(rng.standard_normal((D, D)))
        self.Pk = q.astype(np.float32)
        q, _ = np.linalg.qr(rng.standard_normal((D, D)))
        self.Pv = q.astype(np.float32)
        self.e = unit(rng.standard_normal(D)).astype(np.float32)
        self.e2 = unit(rng.standard_normal(D)).astype(np.float32)


def make_bank(rng, n_art, k_facts, gscale, tb_range=None):
    m = ev2.EPISODES_PER_ARTICLE
    n = n_art * m
    art = np.repeat(np.arange(n_art), m)
    tk = unit(rng.standard_normal((n_art, N_SPAN, D)))[art]
    tv = unit(rng.standard_normal((n_art, N_SPAN, D)))[art]
    lo, hi = tb_range or (TB_LO, TB_HI)
    tb = rng.uniform(lo, hi, (n_art, N_SPAN))[art]
    tg1 = -rng.exponential(BASE_G * gscale, (n_art, N_SPAN))[art]
    tg2 = -rng.exponential(BASE_G * gscale, (n_art, N_SPAN))[art]
    lk = unit(rng.standard_normal((n, LEAD, D)))
    lv = unit(rng.standard_normal((n, LEAD, D)))
    fk = unit(rng.standard_normal((n, k_facts, D)))
    fv = unit(rng.standard_normal((n, k_facts, D)))
    target = rng.integers(0, k_facts, n)
    foils = unit(rng.standard_normal((n, 3, D)))
    noise = rng.standard_normal((n, 4))
    return dict(art=art, tk=tk, tv=tv, tb=tb, tg1=tg1, tg2=tg2, lk=lk, lv=lv, fk=fk, fv=fv, target=target,
                foils=foils, noise=noise, k=k_facts, n=n)


def refine_counts(rng, n, f):
    extra = round(f * N_SPAN) - N_SPAN
    mcount = np.ones((n, N_SPAN), dtype=int)
    for e in range(n):
        np.add.at(mcount[e], rng.integers(0, N_SPAN, extra), 1)
    return mcount


def passage(bank, world, mcount, piece_rng):
    """Re-segmented passage inputs: piece keys, values, betas, layer-1 log-decays (native),
    layer-2 base log-decays (native) and each piece's canonical token index."""
    n = bank["n"]
    lam, rho, wnorm = world.spec["lam"], world.spec["rho"], world.spec["wnorm"]
    idx = np.stack([np.repeat(np.arange(N_SPAN), mcount[e]) for e in range(n)])
    mm = np.take_along_axis(mcount, idx, 1)
    pk = np.take_along_axis(bank["tk"], idx[..., None], 1)
    pv = np.take_along_axis(bank["tv"], idx[..., None], 1)
    if rho < 1.0:
        t = idx.shape[1]
        nk = unit(piece_rng.standard_normal((n, t, D)))
        nv = unit(piece_rng.standard_normal((n, t, D)))
        single = (mm == 1)[..., None]
        pk = np.where(single, pk, unit(rho * pk + math.sqrt(1 - rho ** 2) * nk))
        pv = np.where(single, pv, unit(rho * pv + math.sqrt(1 - rho ** 2) * nv))
    b = np.take_along_axis(bank["tb"], idx, 1)
    if wnorm:
        b = 1 - (1 - b) ** (1.0 / mm)
    g1 = np.take_along_axis(bank["tg1"], idx, 1) / mm ** lam
    g2b = np.take_along_axis(bank["tg2"], idx, 1) / mm ** lam
    return dict(k=pk, v=pv, b=b, g1=g1, g2b=g2b, tok=idx)


def canonical_passage(bank):
    n = bank["n"]
    return dict(k=bank["tk"], v=bank["tv"], b=bank["tb"], g1=bank["tg1"], g2b=bank["tg2"],
                tok=np.repeat(np.arange(N_SPAN)[None], n, 0))


def scan(keys, vals, beta, logd, want_reads):
    """keys/vals [B, T, D], beta/logd [B, T]. Returns final state [B, D, D] and the pre-update
    reads S_{t-1} k_t [B, T, D] when asked."""
    b, t, _ = keys.shape
    keys = keys.astype(np.float32)
    vals = vals.astype(np.float32)
    beta = beta.astype(np.float32)
    alpha = np.exp(logd).astype(np.float32)
    s = np.zeros((b, D, D), dtype=np.float32)
    reads = np.empty((b, t, D), dtype=np.float32) if want_reads else None
    for i in range(t):
        k, v = keys[:, i], vals[:, i]
        sk = np.matmul(s, k[:, :, None])[..., 0]
        if want_reads:
            reads[:, i] = sk
        a = alpha[:, i, None]
        u = beta[:, i, None] * (v - a * sk)  # S_t = a S (I - b k k^T) + b v k^T = a S + b (v - a S k) k^T
        s *= a[:, :, None]
        s += u[:, :, None] * k[:, None, :]
    return s, reads


def token_sums(x, tok):
    """Sum per-position values x [B, T] over each canonical token's pieces -> [B, N_SPAN]."""
    out = np.zeros((x.shape[0], N_SPAN))
    for e in range(x.shape[0]):
        np.add.at(out[e], tok[e], x[e])
    return out


def run_arm(bank, world, psg, mode, dec_targets=None, can_targets=None, dose=1.0, silence=False, k1_fresh=False):
    """mode: native | clamp | transplant. Returns outcome (points), the layer-1 and layer-2
    per-canonical-token log-decay sums, and the layer-2 passage keys (for the drift ledger)."""
    n, kf = bank["n"], bank["k"]
    keys = np.concatenate([bank["lk"], bank["fk"], psg["k"]], 1)
    vals = np.concatenate([bank["lv"], bank["fv"], psg["v"]], 1)
    pb = np.zeros_like(psg["b"]) if silence else psg["b"]
    beta = np.concatenate([np.full((n, LEAD), 0.5), np.full((n, kf), FACT_BETA), pb], 1)
    p0 = LEAD + kf
    g1 = psg["g1"] * dose
    if mode == "clamp":  # layer 1: pieces rescaled so each token's sum equals CAN's value
        sums = token_sums(g1, psg["tok"])
        g1 = g1 * np.take_along_axis(can_targets["g1"] / sums, psg["tok"], 1)
    elif mode == "transplant":  # canonical tokens take NAT's per-token piece sums
        g1 = dec_targets["g1"].copy()
    logd1 = np.concatenate([np.full((n, LEAD), -FACT_G), np.full((n, kf), -FACT_G), g1], 1)
    s1, r1 = scan(keys, vals, beta, logd1, True)
    # layer-2 inputs from layer-1 reads (state-dependent writes and decays)
    k2 = unit(np.einsum("ij,btj->bti", world.Pk, keys) + GAMMA * r1)
    v2 = unit(np.einsum("ij,btj->bti", world.Pv, vals) + GAMMA * r1)
    proj = np.tanh(r1 @ world.e)
    beta2 = np.clip(beta * (1 + KAPPA * proj), 0.0, 0.99)
    g2_live = psg["g2b"] * dose * np.exp(ZETA * np.tanh(r1[:, p0:] @ world.e2))
    if mode == "clamp":
        sums2 = token_sums(g2_live, psg["tok"])
        g2_live = g2_live * np.take_along_axis(can_targets["g2"] / sums2, psg["tok"], 1)
    elif mode == "transplant":
        g2_live = dec_targets["g2"].copy()
    logd2 = np.concatenate([np.full((n, p0), -FACT_G), g2_live], 1)
    s2, _ = scan(k2, v2, beta2, logd2, False)
    # query read
    tgt = bank["target"]
    q = bank["fk"][np.arange(n), tgt].astype(np.float32)
    o1 = np.einsum("bvk,bk->bv", s1, q)
    q2 = unit(q @ world.Pk.T + GAMMA * o1)
    o2 = np.einsum("bvk,bk->bv", s2, q2)
    tv = bank["fv"][np.arange(n), tgt]
    if kf >= 4:
        others = np.stack([np.delete(bank["fv"][e], tgt[e], 0)[:3] for e in range(n)])
        present = np.ones((n, 4))
    else:
        others = bank["foils"]
        present = np.array([1.0, 0.0, 0.0, 0.0])[None].repeat(n, 0)
    cands = np.concatenate([tv[:, None], others], 1)
    scores = (np.einsum("bcv,bv->bc", cands, o1) + ALPHA2 * np.einsum("bcv,bv->bc", cands @ world.Pv.T, o2)
              + NOISE * bank["noise"] + PHI * present)
    y = (scores.argmax(1) == 0).astype(float) * 100.0
    return dict(y=y, g1_tok=token_sums(g1, psg["tok"]), g2_tok=token_sums(g2_live, psg["tok"]), k2=k2[:, p0:])


def factorial(bank, world, f, seed_key):
    mcount = refine_counts(np.random.default_rng(seed_key + [1]), bank["n"], f)
    psg = passage(bank, world, mcount, np.random.default_rng(seed_key + [2]))
    can_psg = canonical_passage(bank)
    can = run_arm(bank, world, can_psg, "native")
    tg = {"g1": can["g1_tok"], "g2": can["g2_tok"]}
    nat = run_arm(bank, world, psg, "native")
    clamp = run_arm(bank, world, psg, "clamp", can_targets=tg)
    dec = run_arm(bank, world, can_psg, "transplant", dec_targets={"g1": nat["g1_tok"], "g2": nat["g2_tok"]})
    sil_nat = run_arm(bank, world, psg, "native", silence=True)
    sil_clamp = run_arm(bank, world, psg, "clamp", can_targets=tg, silence=True)
    dose = run_arm(bank, world, can_psg, "native", dose=f)
    split = mcount > 1
    rf1 = (nat["g1_tok"] / can["g1_tok"])[split]
    rf2 = (nat["g2_tok"] / can["g2_tok"])[split]
    # write drift ledger: layer-2 passage keys, NAT vs CLAMP (same pieces), CAN vs DEC (same tokens)
    drift_clamp = float(np.mean(np.linalg.norm(clamp["k2"] - nat["k2"], axis=-1)))
    drift_dec = float(np.mean(np.linalg.norm(dec["k2"] - can["k2"], axis=-1)))
    # piece-sum checks (registered I8 analogue): CLAMP sums equal CAN's, DEC sums equal NAT's
    clamp_err = float(max(np.max(np.abs(clamp["g1_tok"] - can["g1_tok"])), np.max(np.abs(clamp["g2_tok"] - can["g2_tok"]))))
    dec_err = float(max(np.max(np.abs(dec["g1_tok"] - nat["g1_tok"])), np.max(np.abs(dec["g2_tok"] - nat["g2_tok"]))))
    arms = {"CAN": can["y"], "NAT": nat["y"], "CLAMP": clamp["y"], "DEC": dec["y"], "SIL_NAT": sil_nat["y"],
            "SIL_CLAMP": sil_clamp["y"], "DOSE": dose["y"]}
    ledger = {"rf_median_pooled": float(np.median(np.concatenate([rf1, rf2]))), "rf_median_layer1": float(np.median(rf1)),
              "rf_median_layer2": float(np.median(rf2)), "share_split": float(split.mean()),
              "drift_k2_clamp_vs_nat": drift_clamp, "drift_k2_dec_vs_can": drift_dec,
              "max_abs_piece_sum_error_clamp": clamp_err, "max_abs_piece_sum_error_dec": dec_err}
    return arms, ledger


def select_point(world, seed):
    """Registered operating-point rule on 200 held-out episodes per cell (50 articles)."""
    can_acc, nat_acc = {}, {}
    for k in ev2.K_LADDER:
        bank = make_bank(np.random.default_rng([seed, 11, k]), N_HELDOUT // 4, k, world.gscale, world.spec.get("tb"))
        can_acc[k] = float(run_arm(bank, world, canonical_passage(bank), "native")["y"].mean())
        for f in ev2.F_LADDER:
            mcount = refine_counts(np.random.default_rng([seed, 12, k, int(f * 10)]), bank["n"], f)
            psg = passage(bank, world, mcount, np.random.default_rng([seed, 13, k, int(f * 10)]))
            nat_acc[(k, f)] = float(run_arm(bank, world, psg, "native")["y"].mean())
    return ev2.select_operating_point(can_acc, nat_acc), can_acc, {f"{a}|{b}": v for (a, b), v in nat_acc.items()}


def pool_summary(arms, f_p):
    s = ev2.secant_scale(f_p)
    c = ev2.contrasts(arms["CAN"], arms["DEC"], arms["CLAMP"], arms["NAT"])
    out = {f"b_{k}": float(v.mean() * s) for k, v in c.items()}
    out.update({f"acc_{k}": float(v.mean()) for k, v in arms.items()})
    out["b_SIL_decay"] = float((arms["SIL_CLAMP"] - arms["SIL_NAT"]).mean() * s)
    out["b_DOSE"] = float((arms["CAN"] - arms["DOSE"]).mean() * s)
    out["discordance_TNIE"] = float((c["TNIE"] != 0).mean())
    out["discordance_PNIE"] = float((c["PNIE"] != 0).mean())
    out["identity_TE_eq_PNIE_PNDE_INT"] = float(np.max(np.abs(c["TE"] - (c["PNIE"] + c["PNDE"] + c["INT"]))))
    return out


def resample_oc(arms, art, f_p, rf, rng):
    """Registered estimator and rule on 1,000 articles resampled with replacement from the pool."""
    n_art = art.max() + 1
    m = ev2.EPISODES_PER_ARTICLE
    n_res = ev2.N_ARTICLES_BY_F[f_p]
    c = ev2.contrasts(arms["CAN"], arms["DEC"], arms["CLAMP"], arms["NAT"])
    tn = c["TNIE"].reshape(n_art, m)
    pn = c["PNIE"].reshape(n_art, m)
    counts, cov = {}, {"TNIE": 0, "PNIE": 0}
    s = ev2.secant_scale(f_p)
    truth = {"TNIE": c["TNIE"].mean() * s, "PNIE": c["PNIE"].mean() * s}
    for start in range(0, RESAMPLE_REPS, 500):
        idx = rng.integers(0, n_art, (500, n_res))
        pt, lt, ht = ev2.cluster_normal_matrix(tn[idx], scale=s)
        pp, lp, hp = ev2.cluster_normal_matrix(pn[idx], scale=s)
        for i in range(500):
            r = ev2.decide_subject(ev2.Interval(pt[i], lt[i], ht[i]), ev2.Interval(pp[i], lp[i], hp[i]), rf)
            counts[r] = counts.get(r, 0) + 1
        cov["TNIE"] += int(((lt <= truth["TNIE"]) & (ht >= truth["TNIE"])).sum())
        cov["PNIE"] += int(((lp <= truth["PNIE"]) & (hp >= truth["PNIE"])).sum())
    return {"n_articles_resampled": n_res, "P": {k: v / RESAMPLE_REPS for k, v in sorted(counts.items())},
            "coverage_90": {k: v / RESAMPLE_REPS for k, v in cov.items()}}


def v1_reading_oc(y_k1, y_k4, rng, f=2.7):
    """The wave-1 rule (pooled K in {1, 4}, raw points, line 3) at its registered size, 375
    passages x 4 episodes per load, resampled with replacement from 150-article pools: P(KILL)."""
    n1 = y_k1["NAT"].size // 4
    n4 = y_k4["NAT"].size // 4
    d1 = (y_k1["CLAMP"] - y_k1["NAT"]).reshape(n1, 4)
    d4 = (y_k4["CLAMP"] - y_k4["NAT"]).reshape(n4, 4)
    lnf = math.log(f)
    kill = 0
    reps = 1000
    for _ in range(reps):
        i1 = rng.integers(0, n1, 375)
        i4 = rng.integers(0, n4, 375)
        x = np.concatenate([d1[i1], d4[i4]], 1)
        iv = ev1.cluster_normal([x[j] for j in range(375)])
        kill += int(ev1.decide_subject(ev1.Interval(iv.point / lnf, iv.lo / lnf, iv.hi / lnf)) == "KILL")
    return {"P_KILL_v1_rule": kill / reps, "NIE_K1_points": float(d1.mean()), "NIE_K4_points": float(d4.mean()),
            "acc_NAT_K1": float(y_k1["NAT"].mean()), "acc_CLAMP_K1": float(y_k1["CLAMP"].mean())}


def tune_line(seed):
    """Seeded scan of the canonical decay scale in a W1-type world (duplicate, write-normalised
    pieces, so little extra interference) for the scale whose TNIE at the operating point the
    registered rule selects is nearest the line (1,000 episodes per scale)."""
    rows = []
    for gs in (0.15, 0.3, 0.6):
        w = World("scan", dict(lam=0.0, rho=1.0, wnorm=True), seed)
        w.gscale = gs
        sel, _, _ = select_point(w, seed)
        if sel is None:
            rows.append({"gscale": gs, "selected": None})
            continue
        k_p, f_p = sel
        bank = make_bank(np.random.default_rng([seed, 21, int(gs * 100)]), 250, k_p, gs)
        mcount = refine_counts(np.random.default_rng([seed, 22, int(gs * 100)]), bank["n"], f_p)
        psg = passage(bank, w, mcount, np.random.default_rng([seed, 23, int(gs * 100)]))
        can = run_arm(bank, w, canonical_passage(bank), "native")
        nat = run_arm(bank, w, psg, "native")
        clamp = run_arm(bank, w, psg, "clamp", can_targets={"g1": can["g1_tok"], "g2": can["g2_tok"]})
        rows.append({"gscale": gs, "selected": [k_p, f_p],
                     "b_TNIE": float((clamp["y"] - nat["y"]).mean() * ev2.secant_scale(f_p)),
                     "acc_CAN": float(can["y"].mean()), "acc_NAT": float(nat["y"].mean())})
    ok = [r for r in rows if r.get("selected")]
    best = min(ok, key=lambda r: abs(r["b_TNIE"] - ev2.LINE))
    return best["gscale"], rows


def run_world(name, seed=SEED):
    t0 = time.time()
    spec = dict(WORLDS[name])
    res = {"world": name, "spec": spec}
    if spec["gscale"] is None:
        gs, scan_rows = tune_line(seed)
        spec["gscale"] = gs
        res["line_scan"] = scan_rows
    world = World(name, spec, seed)
    world.gscale = spec["gscale"]
    sel, can_acc, nat_acc = select_point(world, seed)
    res["heldout"] = {"CAN": can_acc, "NAT": nat_acc, "selected": sel}
    if sel is None:
        res["reading"] = "NOT_ADMISSIBLE"
        return res
    k_p, f_p = sel
    bank = make_bank(np.random.default_rng([seed, 31, k_p]), POOL_ARTICLES, k_p, world.gscale, world.spec.get("tb"))
    arms, ledger = factorial(bank, world, f_p, [seed, 32, k_p, int(f_p * 10)])
    res["pool"] = pool_summary(arms, f_p)
    res["ledger"] = ledger
    rf = ledger["rf_median_pooled"]
    # the registered reading on the whole pool (a 6,000-episode realisation) and its OC by resampling
    res["pool_reading"] = ev2.read_subject(arms["CAN"], arms["DEC"], arms["CLAMP"], arms["NAT"], bank["art"], f_p, rf)
    res["oc"] = resample_oc(arms, bank["art"], f_p, rf, np.random.default_rng([seed, 33]))
    if name not in V1_WORLDS:
        res["elapsed_s"] = round(time.time() - t0, 1)
        return res
    # v1 comparison: K = 1 with fresh foils (presence test) and K = 4, f = 2.7, 600-episode pools each
    k1 = make_bank(np.random.default_rng([seed, 41]), 150, 1, world.gscale, world.spec.get("tb"))
    k4 = make_bank(np.random.default_rng([seed, 42]), 150, 4, world.gscale, world.spec.get("tb"))
    out = {}
    for lbl, b in (("K1", k1), ("K4", k4)):
        mcount = refine_counts(np.random.default_rng([seed, 43, b["k"]]), b["n"], 2.7)
        psg = passage(b, world, mcount, np.random.default_rng([seed, 44, b["k"]]))
        can = run_arm(b, world, canonical_passage(b), "native")
        nat = run_arm(b, world, psg, "native")
        clamp = run_arm(b, world, psg, "clamp", can_targets={"g1": can["g1_tok"], "g2": can["g2_tok"]})
        out[lbl] = {"CAN": can["y"], "NAT": nat["y"], "CLAMP": clamp["y"]}
    res["v1_rule"] = v1_reading_oc(out["K1"], out["K4"], np.random.default_rng([seed, 45]))
    res["v1_rule"]["acc_CAN_K1"] = float(out["K1"]["CAN"].mean())
    res["elapsed_s"] = round(time.time() - t0, 1)
    return res


def main() -> int:
    out_path = Path(sys.argv[1])
    names = sys.argv[2:] or list(WORLDS)
    res = {"params": dict(D=D, N_SPAN=N_SPAN, LEAD=LEAD, FACT_BETA=FACT_BETA, FACT_G=FACT_G, NOISE=NOISE, TB=(TB_LO, TB_HI), PHI=PHI,
                          GAMMA=GAMMA, KAPPA=KAPPA, ZETA=ZETA, ALPHA2=ALPHA2, BASE_G=BASE_G,
                          POOL_ARTICLES=POOL_ARTICLES, N_HELDOUT=N_HELDOUT, RESAMPLE_ARTICLES="N_ARTICLES_BY_F[f_p]", V1_WORLDS=V1_WORLDS,
                          RESAMPLE_REPS=RESAMPLE_REPS, SEED=SEED, worlds=WORLDS), "worlds": {}}
    for name in names:
        r = run_world(name)
        res["worlds"][name] = r
        p = r.get("pool", {})
        print(name, r["heldout"]["selected"], {k: round(v, 2) for k, v in p.items() if k.startswith("b_")},
              r.get("pool_reading", {}).get("reading"), r.get("oc", {}).get("P"), r.get("v1_rule", {}).get("P_KILL_v1_rule"),
              r.get("elapsed_s"), flush=True)
    out_path.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
