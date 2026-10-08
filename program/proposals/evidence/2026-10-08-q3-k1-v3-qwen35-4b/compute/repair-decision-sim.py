"""K1 v3 wave-1 repair, simulation S2: operating characteristics of the repaired decision rules.

Synthetic family tables for both targets (hs, mp), eight softmax layers and n seeds,
read by the repaired rules of the draft registration (sections "Metrics", "Decision
rules") and, on the same draws, by the wave-1 rules. Statistics follow the registered
K1 code (harness/sparse_indexer_k1_stats.py): pair-cluster sums, macro over pairs,
passage-cluster bootstrap with K1's own weight generator (seed 42), Welch-Satterthwaite
df, t(0.995). Mode `validate` checks this file's K1-estimator interval against
`k.xi_interval` and `k.xi_rel_interval` on synthetic reads (must agree to 1e-9).

Generative model (every number a stated assumption unless marked "dev", the lane-862
development receipt):
- design: 230 audit questions in 122 links (K1); a fixed controlled subset (share 0.5,
  dev 0.50); each family excluded for mask coverage with probability 0.10; unseen stratum
  14 pairs (7 X-needle, 7 English-needle, the English MN prompt shared by every
  English-needle pair, K1), seen stratum 6 pairs;
- target recall: dev per-pair and per-layer hs headroom, scaled to the masked controlled
  CX headroom H of the scenario; question effect SD 6, prompt SD 4, layer-prompt SD 3;
- indexer recall: rand + g (target - rand) - effect + noise, g = 0.85; noise = cluster
  (per link, leg, direction) + family components, each with a layer-specific part
  (per-layer SE about 1.5 times the macro's, wave-1 assumption) scaled by the square root
  of the layer's headroom share; seed effects on the CX leg per layer and per
  layer x direction, scaled so the SD of the eight-layer-average per-seed xi is the
  scenario's seed SD; seed x family noise SD 3; mp shares 0.7 of hs's cluster and family
  noise (correlation 0.7), seeds independent;
- effects (recall points, proportional to each layer's headroom unless stated):
  gamma = cross-script mismatch excess (the H_loc estimand), alpha = query-in-unseen-
  script excess, beta = needle-in-unseen-script excess. English-needle pairs: MN 0,
  CX alpha + gamma. X-needle pairs: MN alpha + beta, CX beta + gamma. So the macro xi is
  gamma, the direction half-difference is alpha and beta cancels;
- literal channel: a bias b_lit added to the indexer's MN legs in xi^M; xi^LF keeps a
  fraction r of it (S1) and a heterogeneity offset; Delta = xi^M - xi^LF has macro noise
  SD 0.4 (S1 gives 0.15-0.2; doubled for the cluster design and seeds).
"""

from __future__ import annotations

import json
import math
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np
from scipy import stats

from harness import sparse_indexer_k1_stats as k

RAND = 12.45
N_Q, N_CL = 230, 122
Q_CL = np.sort(np.r_[np.arange(N_CL), np.arange(N_Q - N_CL)])
B = int(os.environ.get("S2_BOOT", "1000"))
NP = 20
UX, UE, SX, SE = list(range(0, 7)), list(range(7, 14)), [14, 15, 16], [17, 18, 19]
UNSEEN = UX + UE
SEEN = SX + SE
EN_NEEDLE = np.array([False] * 7 + [True] * 7 + [False] * 3 + [True] * 3)
# dev receipt (lane 862), T:hs mean recall by pair and condition, order bn el he ja ka ko ta
X_CX = [49.12, 42.50, 53.03, 63.32, 38.68, 60.05, 43.53]
X_MN = [47.91, 39.66, 48.60, 69.26, 37.38, 68.65, 41.66]
E_CX = [59.64, 55.90, 53.66, 66.83, 54.23, 67.46, 56.48]
E_MN = 63.22
LAYER_CX = [21.13, 47.01, 59.41, 64.24, 70.12, 65.55, 58.40, 50.96]
LAYER_MN = [25.50, 50.51, 61.87, 64.63, 71.08, 64.68, 60.37, 56.02]
H_DEV_CX = 42.15
G_RET = 0.85
CTRL_SHARE = float(os.environ.get("S2_CTRL", "0.5"))
EXCL = 0.10
LAMBDA_L = 1.32
SD_V = 3.0
DELTA_SD = 0.4
DELTA_SD_PRE = 0.8   # PRE: about half the families and fewer blocks (S1: family SD 7.8 vs 5.3)
# noise scales calibrated to the macro se_cluster of xi: about 0.8 / 1.3 / 1.8 points, the
# wave-1 cluster SDs 6 / 10 / 13.4 at 70 effective clusters x 1.12 (calibration in the log)
SE_LOW, SE_MID, SE_HIGH = 0.8, 1.5, 2.6


def pair_headroom() -> np.ndarray:
    """(pairs, legs) unmasked dev headroom; leg 0 = MN, 1 = CX. Seen pairs use unseen means."""
    h = np.zeros((NP, 2))
    for i in range(7):
        h[i] = (X_MN[i] - RAND, X_CX[i] - RAND)
        h[7 + i] = (E_MN - RAND, E_CX[i] - RAND)
    for j in range(3):
        h[14 + j] = (np.mean(X_MN) - RAND, np.mean(X_CX) - RAND)
        h[17 + j] = (E_MN - RAND, np.mean(E_CX) - RAND)
    return h


H_PAIR = pair_headroom()
H_LAYER = np.array([[m - RAND, c - RAND] for m, c in zip(LAYER_MN, LAYER_CX)])   # (8, 2)
NU = np.sqrt(H_LAYER[:, 1] / H_LAYER[:, 1].mean())                                  # noise scale


def design(seed: int = 42):
    rng = np.random.default_rng(seed)
    ctrl_q = np.sort(rng.choice(N_Q, int(round(CTRL_SHARE * N_Q)), replace=False))
    links = np.unique(Q_CL[ctrl_q])
    return ctrl_q, links


CTRL_Q, LINKS = design()
N_CLU = LINKS.size
W = k._cluster_weights(N_CLU, B, k.BOOTSTRAP_SEED)       # K1's own generator, seed 42
QIDX = {int(q): i for i, q in enumerate(CTRL_Q)}
CLU_OF_Q = np.searchsorted(LINKS, Q_CL[CTRL_Q])           # cluster index (sorted links)


def t99(df):
    return np.where(np.isfinite(df), stats.t.ppf(0.995, np.minimum(df, 1e6)), k.Z_99)


def ws_df(v_cl, df_cl, v_seed, df_seed):
    den = 0.0
    if v_cl > 0:
        den += v_cl ** 2 / df_cl
    if v_seed > 0 and df_seed > 0:
        den += v_seed ** 2 / df_seed
    return math.inf if den == 0 else (v_cl + v_seed) ** 2 / den


def interval(point, se_cl, v_seed, df_seed):
    v_cl = se_cl ** 2
    df = ws_df(v_cl, N_CLU - 1, v_seed, df_seed)
    q = float(t99(df))
    hw = q * math.sqrt(v_cl + v_seed)
    return dict(point=point, lo=point - hw, hi=point + hw, hw=hw, df=df, se_cl=se_cl,
                v_seed=v_seed)


def layer_resolved(contrib: np.ndarray):
    """contrib (seeds, layers): per-layer per-seed contributions whose seed-mean sum is the
    statistic. Seed variance of the seed-mean = sum_l var_s / n; Satterthwaite df."""
    n = contrib.shape[0]
    var_l = contrib.var(axis=0, ddof=1)
    v = float(var_l.sum() / n)
    den = float(((var_l / n) ** 2 / (n - 1)).sum())
    df = (v ** 2 / den) if den > 0 else math.inf
    return v, df


def k1_seed(contrib: np.ndarray):
    """K1's estimator: SD of the per-seed statistic (sum over layers), df n - 1."""
    n = contrib.shape[0]
    per_seed = contrib.sum(axis=1)
    return float(per_seed.var(ddof=1) / n), n - 1


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #

def build_families(rng):
    """Family list: (pair, question index into CTRL_Q); exclusion drawn per replicate."""
    pairs, qs = np.meshgrid(np.arange(NP), np.arange(CTRL_Q.size), indexing="ij")
    pairs, qs = pairs.ravel(), qs.ravel()
    keep = rng.random(pairs.size) >= EXCL
    return pairs[keep], qs[keep]


def effect_matrix(sc: dict) -> np.ndarray:
    """(layers, pairs, legs) indexer loss in recall points."""
    a = np.zeros((NP, 2))
    for stratum, plist_x, plist_e in (("u", UX, UE), ("s", SX, SE)):
        g, al, be = sc.get(f"gamma_{stratum}", 0.0), sc.get(f"alpha_{stratum}", 0.0), sc.get(f"beta_{stratum}", 0.0)
        for p in plist_e:
            a[p] = (0.0, al + g)
        for p in plist_x:
            a[p] = (al + be, be + g)
    prof = np.asarray(sc.get("layer_profile", H_LAYER[:, 1] / H_LAYER[:, 1].mean()), float)
    eff = prof[:, None, None] * a[None, :, :]
    if "layer_extra" in sc:   # (layer index, fraction of that layer's CX headroom lost on CX legs of unseen pairs)
        li, frac = sc["layer_extra"]
        hl = H_LAYER[li, 1] * sc["H"] / H_DEV_CX
        for p in UNSEEN:
            eff[li, p, 1] += frac * hl
    return eff


def generate(rng, sc: dict, n_seeds: int, se_scale: float, pairs, qs):
    m = sc["H"] / H_DEV_CX
    F = pairs.size
    en = EN_NEEDLE[pairs]
    clu = CLU_OF_Q[qs]
    direction = en.astype(int)
    # target headroom per layer, family, leg
    hpair = H_PAIR[pairs] / H_PAIR[UNSEEN].mean(axis=0)            # (F, 2)
    H = m * H_LAYER[:, None, :] * hpair[None, :, :]                 # (8, F, 2)
    hbar = H.mean(axis=0, keepdims=True)
    a_q = rng.normal(0, 6, CTRL_Q.size)
    eta = rng.normal(0, 4, (F, 2))
    eta_mn_en = rng.normal(0, 4, CTRL_Q.size)
    eta[en, 0] = eta_mn_en[qs[en]]
    eta_l = rng.normal(0, 3, (8, F, 2))
    eta_l_en = rng.normal(0, 3, (8, CTRL_Q.size))
    eta_l[:, en, 0] = eta_l_en[:, qs[en]]
    scale = H / np.maximum(hbar, 1e-9)
    tgt = RAND + H + scale * (a_q[qs][None, :, None] + eta[None]) + eta_l
    tgt = np.clip(tgt, 0, 100)
    eff = effect_matrix(sc)[:, pairs, :]                              # (8, F, 2)
    # noise components shared by the two targets with correlation 0.7
    sd_cl, sd_f = 7.0 * se_scale, 9.0 * se_scale

    def noise_draw():
        u = rng.normal(0, 1, (N_CLU, 2, 2))            # cluster x leg x direction
        ul = rng.normal(0, 1, (8, N_CLU, 2, 2))
        w = rng.normal(0, 1, (F, 2))
        w_en = rng.normal(0, 1, CTRL_Q.size)
        w[en, 0] = w_en[qs[en]]
        wl = rng.normal(0, 1, (8, F, 2))
        wl_en = rng.normal(0, 1, (8, CTRL_Q.size))
        wl[:, en, 0] = wl_en[:, qs[en]]
        cl = np.take_along_axis(u[clu], direction[:, None, None], axis=2)[..., 0]                # (F, 2)
        cll = np.take_along_axis(ul[:, clu], direction[None, :, None, None], axis=3)[..., 0]      # (8, F, 2)
        base = sd_cl * (cl[None] + LAMBDA_L * cll) + sd_f * (w[None] + LAMBDA_L * wl)
        return base * NU[:, None, None]

    shared = noise_draw()
    out = {}
    s0 = sc["seed_sd"] * 8.0 / math.sqrt(1.125 * float((NU ** 2).sum()))
    for t_i, tname in enumerate(("hs", "mp")):
        own = noise_draw()
        noise = shared if t_i == 0 else 0.7 * shared + math.sqrt(1 - 0.49) * own
        tscale = 1.0 if tname == "hs" else 0.97
        tgt_t = RAND + tscale * (tgt - RAND)
        d = rng.normal(0, 1, (n_seeds, 8)) * s0 * NU[None, :]
        dd = rng.normal(0, 1, (n_seeds, 8, 2)) * 0.5 * s0 * NU[None, :, None]
        v = rng.normal(0, SD_V, (n_seeds, 8, F, 2))
        v_en = rng.normal(0, SD_V, (n_seeds, 8, CTRL_Q.size))
        v[:, :, en, 0] = v_en[:, :, qs[en]]
        ind = RAND + G_RET * (tgt_t - RAND) - eff + noise
        ind = ind[None].repeat(n_seeds, axis=0) + v
        ind[..., 1] += d[:, :, None] + dd[:, :, direction]
        # literal channel on the MN legs of the M statistic
        ind[..., 0] += sc.get("b_lit", 0.0)
        out[tname] = (np.clip(ind, 0, 100), np.clip(tgt_t, 0, 100))
    return out


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #

def cell_matrix(pairs, clu):
    from scipy import sparse
    F = pairs.size
    return sparse.csr_matrix((np.ones(F), (np.arange(F), clu * NP + pairs)), shape=(F, N_CLU * NP))


def sums_cp(values: np.ndarray, M) -> np.ndarray:
    """Cluster x pair sums of values (..., F) -> (..., C, NP)."""
    lead = values.shape[:-1]
    flat = values.reshape(-1, values.shape[-1])
    out = np.asarray((M.T @ flat.T).T)
    return out.reshape(lead + (N_CLU, NP))


def read_target(ind, tgt, pairs, qs, sc, n_seeds, tau, layer_min=3.0):
    clu = CLU_OF_Q[qs]
    M = cell_matrix(pairs, clu)
    counts = sums_cp(np.ones(pairs.size), M)                   # (C, NP)
    wc = W @ counts                                            # (B, NP)
    cnt = counts.sum(axis=0)
    ind_l = ind.mean(axis=0)                                   # (8, F, 2) seed mean per layer
    # per-seed, per-layer pair means (seed terms)
    onehot = np.zeros((pairs.size, NP))
    onehot[np.arange(pairs.size), pairs] = 1.0 / cnt[pairs]
    pm_ind = np.moveaxis(np.moveaxis(ind, 2, -1) @ onehot, -2, -1)   # (S, 8, NP, 2)
    pm_tgt = np.moveaxis(np.moveaxis(tgt, 1, -1) @ onehot, -2, -1)   # (8, NP, 2)
    # cluster x pair sums per layer, leg and kind (indexer seed mean, target)
    V = np.stack([np.moveaxis(ind_l, -1, 1), np.moveaxis(tgt, -1, 1)])   # (2 kinds, 8, 2 legs, F)
    S_l = sums_cp(V, M)                                        # (2, 8, 2, C, NP)
    P_l = S_l.sum(axis=3) / cnt                                # (2, 8, 2, NP)
    B_l = np.tensordot(W, S_l.reshape(-1, N_CLU, NP), axes=([1], [1]))      # (B, 32, NP)
    B_l = np.moveaxis(B_l, 0, 1).reshape(2, 8, 2, B, NP) / wc
    # layer means (sums are linear, so the layer mean of sums is the sum of layer means)
    pi, pt = P_l[0].mean(axis=0), P_l[1].mean(axis=0)          # (2 legs, NP)
    bi, bt = B_l[0].mean(axis=0), B_l[1].mean(axis=0)          # (2 legs, B, NP)
    res = {}
    U = np.array(UNSEEN)
    ex_p = (pi[0] - pi[1]) - (pt[0] - pt[1])                    # (NP,)
    ex_b = (bi[0] - bi[1]) - (bt[0] - bt[1])                    # (B, NP)
    ex_sl = (pm_ind[..., 0] - pm_ind[..., 1]) - (pm_tgt[None, ..., 0] - pm_tgt[None, ..., 1])  # (S, 8, NP)

    def stat(pset, sign=None):
        if sign is None:
            pset = np.asarray(pset)
            pt_ = float(ex_p[pset].mean()); bt_ = ex_b[:, pset].mean(axis=1)
            contrib = ex_sl[:, :, pset].mean(axis=2) / 8.0
        else:
            e, x = np.asarray(sign[0]), np.asarray(sign[1])
            pt_ = float((ex_p[e].mean() - ex_p[x].mean()) / 2)
            bt_ = (ex_b[:, e].mean(axis=1) - ex_b[:, x].mean(axis=1)) / 2
            contrib = (ex_sl[:, :, e].mean(axis=2) - ex_sl[:, :, x].mean(axis=2)) / 16.0
        se = float(bt_.std(ddof=1))
        v_lr, df_lr = layer_resolved(contrib)
        v_k1, df_k1 = k1_seed(contrib)
        return dict(lr=interval(pt_, se, v_lr, df_lr), k1=interval(pt_, se, v_k1, df_k1))

    res["xi"] = stat(U)
    res["xi_E"] = stat(UE)
    res["xi_X"] = stat(UX)
    res["alpha"] = stat(None, sign=(UE, UX))
    res["seen"] = stat(SEEN)
    # xi_rel with point denominators (K1 rule: evaluability on point; replicate floor 1)
    hp = pt - RAND                                               # (2, NP)
    hb = np.maximum(bt - RAND, k.HEADROOM_FLOOR_POINTS)
    g_p = (pi - RAND) / hp
    g_b = (bi - RAND) / hb
    rel_p = float((g_p[0, U] - g_p[1, U]).mean())
    rel_b = (g_b[0][:, U] - g_b[1][:, U]).mean(axis=1)
    pm_ind_s = pm_ind[:, :, U, :]
    contrib_rel = (((pm_ind_s[..., 0] - RAND) / hp[0, U]) - ((pm_ind_s[..., 1] - RAND) / hp[1, U])).mean(axis=2) / 8.0
    se_rel = float(rel_b.std(ddof=1))
    v_lr, df_lr = layer_resolved(contrib_rel)
    v_k1, df_k1 = k1_seed(contrib_rel)
    res["xi_rel"] = dict(lr=interval(rel_p, se_rel, v_lr, df_lr), k1=interval(rel_p, se_rel, v_k1, df_k1))
    # floor: masked G(MN) macro, 99% percentile bootstrap lower bound
    gmn_b = g_b[0][:, U].mean(axis=1)
    res["floor_lb"] = float(np.percentile(gmn_b, 0.5))
    # per-layer xi_rel with per-layer denominators; seed term pooled over layers (df 8(n-1))
    xi_l_pts = ex_sl[:, :, U].mean(axis=2)                       # (S, 8) per-layer xi in points
    s2_pool = float(xi_l_pts.var(axis=0, ddof=1).mean())
    df_pool = 8 * (n_seeds - 1)
    layer = []
    for li in range(8):
        pil, ptl = P_l[0, li], P_l[1, li]                         # (2, NP)
        bil, btl = B_l[0, li], B_l[1, li]                         # (2, B, NP)
        hl = ptl - RAND
        evaluable = bool(hl[0, U].mean() >= layer_min and hl[1, U].mean() >= layer_min
                         and (hl[:, U] > 1.0).all())
        gl = (pil - RAND) / np.where(hl > 1.0, hl, np.nan)
        glb = (bil - RAND) / np.maximum(btl - RAND, 1.0)
        rl = float(np.nanmean(gl[0, U] - gl[1, U]))
        rlb = (glb[0][:, U] - glb[1][:, U]).mean(axis=1)
        h_eff = float(hl[1, U].mean())
        v_seed = s2_pool / n_seeds / max(h_eff, 1.0) ** 2
        iv_rel = interval(rl, float(rlb.std(ddof=1)), v_seed, df_pool)
        se_tot = math.sqrt(iv_rel["se_cl"] ** 2 + v_seed)
        iv_rel["lo95"], iv_rel["hi95"] = rl - stats.t.ppf(0.975, min(iv_rel["df"], 1e6)) * se_tot, \
            rl + stats.t.ppf(0.975, min(iv_rel["df"], 1e6)) * se_tot
        # per-layer xi in points (wave-1 veto), K1 seed term per layer (df n-1)
        xl = float(((pil[0] - pil[1]) - (ptl[0] - ptl[1]))[U].mean())
        xlb = ((bil[0] - bil[1]) - (btl[0] - btl[1]))[:, U].mean(axis=1)
        iv_pts = interval(xl, float(xlb.std(ddof=1)), float(xi_l_pts[:, li].var(ddof=1) / n_seeds), n_seeds - 1)
        layer.append(dict(evaluable=evaluable, rel=iv_rel, pts=iv_pts, h_cx=float(hl[1, U].mean())))
    res["layer"] = layer
    # literal-free statistic xi^LF and Delta = xi^M - xi^LF (S1-calibrated): LF keeps a
    # fraction r of the literal bias and a fraction kappa of the excess (heterogeneity)
    rng = np.random.default_rng(zlib.crc32(repr(round(float(ex_p.sum()), 9)).encode()))
    b, g = sc.get("b_lit", 0.0), sc.get("gamma_u", 0.0)
    res["delta_lf"] = float((1 - sc.get("r_lf", 0.0)) * b + (1 - sc.get("kappa_lf", 1.0)) * g
                            + rng.normal(0, DELTA_SD))
    res["delta_pre"] = float((1 - sc.get("r_pre", 0.0)) * b + (1 - sc.get("kappa_pre", 0.87)) * g
                             + rng.normal(0, DELTA_SD_PRE))
    res["xi_lf"] = res["xi"]["lr"]["point"] - res["delta_lf"]
    res["xi_pre"] = res["xi"]["lr"]["point"] - res["delta_pre"]
    return res


def verdicts(reads: dict, sc: dict, tau_rescaled: tuple, n_seeds: int) -> dict:
    """Apply wave-1 and repaired rule variants to both targets' reads."""
    out = {}
    H_ref = sc["H"]

    def neg_new(r, est="lr", tau=tau_rescaled, dir_rule="E_gated", layer_rule="rel", lit="bands"):
        xi, rel = r["xi"][est], r["xi_rel"][est]
        ok = (abs(xi["point"]) <= 5 and xi["lo"] > -10 and xi["hi"] < 10 and xi["hw"] <= 5
              and abs(rel["point"]) <= tau[0] and rel["lo"] > -tau[1] and rel["hi"] < tau[1]
              and r["floor_lb"] >= 0.5)
        labels = []
        if dir_rule in ("alpha", "both"):
            a = r["alpha"][est]
            if not (abs(a["point"]) <= 5 and a["lo"] > -10 and a["hi"] < 10):
                labels.append("QUERY_SCRIPT")
        if dir_rule == "alpha_strict":
            a = r["alpha"][est]
            if not (abs(a["point"]) <= 2.5 and a["lo"] > -7.5 and a["hi"] < 7.5):
                labels.append("QUERY_SCRIPT")
        if dir_rule in ("points", "both", "E_gated"):
            if abs(r["xi_E"][est]["point"]) > 5 or abs(r["xi_X"][est]["point"]) > 5:
                labels.append("DIRECTION")
        if dir_rule == "E_gated":
            e = r["xi_E"][est]
            if not (e["lo"] > -10 and e["hi"] < 10):
                labels.append("ENGLISH_NEEDLE")
        if abs(r["seen"][est]["point"]) > 5:
            labels.append("SEEN")
        if layer_rule in ("rel", "rel95"):
            lo_k, hi_k = ("lo", "hi") if layer_rule == "rel" else ("lo95", "hi95")
            for L in r["layer"]:
                iv = L["rel"]
                if L["evaluable"] and abs(iv["point"]) >= 0.2 and (iv[lo_k] > 0 or iv[hi_k] < 0):
                    labels.append("LAYER")
                    break
        if lit == "bands" and (abs(r["xi_lf"]) > 5 or abs(r["xi_pre"]) > 5):
            labels.append("LITERAL")
        if lit == "agree" and abs(r["delta_lf"]) > 2.5:
            labels.append("LITERAL")
        return ok and not labels, labels

    def go_new(r, est="lr", lit="bands"):
        xi, rel = r["xi"][est], r["xi_rel"][est]
        lit_ok = (r["xi_lf"] >= 5 and r["xi_pre"] >= 5) if lit == "bands" else abs(r["delta_lf"]) <= 2.5
        return xi["point"] >= 10 and xi["lo"] > 0 and rel["lo"] > 0 and lit_ok

    def neg_old(r):
        xi, rel = r["xi"]["k1"], r["xi_rel"]["k1"]
        ok = (xi["point"] <= 5 and xi["hi"] < 10 and xi["hw"] <= 5 and rel["point"] <= 0.1
              and rel["hi"] < 0.2 and r["floor_lb"] >= 0.5)
        rob = (r["seen"]["k1"]["point"] <= 5 and r["xi_E"]["k1"]["point"] <= 5
               and r["xi_X"]["k1"]["point"] <= 5
               and not any(L["pts"]["point"] >= 10 and L["pts"]["lo"] > 0 for L in r["layer"]))
        return ok and rob

    def go_old(r):
        xi, rel = r["xi"]["k1"], r["xi_rel"]["k1"]
        return xi["point"] >= 10 and xi["lo"] > 0 and rel["lo"] > 0

    variants = {
        "wave1": (lambda r: go_old(r), lambda r: (neg_old(r), [])),
        "repaired": (lambda r: go_new(r), lambda r: neg_new(r)),
        "repaired_fixed_tau": (lambda r: go_new(r), lambda r: neg_new(r, tau=(0.1, 0.2))),
        "repaired_k1_seed": (lambda r: go_new(r, "k1"), lambda r: neg_new(r, "k1")),
        "repaired_direction_alpha_interval": (lambda r: go_new(r), lambda r: neg_new(r, dir_rule="alpha")),
        "repaired_direction_alpha_strict": (lambda r: go_new(r), lambda r: neg_new(r, dir_rule="alpha_strict")),
        "repaired_direction_points_only": (lambda r: go_new(r), lambda r: neg_new(r, dir_rule="points")),
        "repaired_literal_agreement_only": (lambda r: go_new(r, lit="agree"), lambda r: neg_new(r, lit="agree")),
        "repaired_layer_veto95": (lambda r: go_new(r), lambda r: neg_new(r, layer_rule="rel95")),
    }
    for name, (gf, nf) in variants.items():
        go = any(gf(r) for r in reads.values())
        negs = [nf(r) for r in reads.values()]
        neg = (not go) and all(n[0] for n in negs)
        labels = sorted({l for n in negs for l in n[1]})
        out[name] = dict(go=go, neg=neg, labels=labels)
    return out


def one(args):
    seed, sc, n_seeds, se_scale = args
    rng = np.random.default_rng(seed)
    pairs, qs = build_families(rng)
    data = generate(rng, sc, n_seeds, se_scale, pairs, qs)
    tau = (5.0 / sc["H"], 10.0 / sc["H"])
    reads = {t: read_target(ind, tgt, pairs, qs, sc, n_seeds, tau) for t, (ind, tgt) in data.items()}
    v = verdicts(reads, sc, tau, n_seeds)
    hs = reads["hs"]
    diag = dict(xi=hs["xi"]["lr"]["point"], hw_lr=hs["xi"]["lr"]["hw"], hw_k1=hs["xi"]["k1"]["hw"],
                se_cl=hs["xi"]["lr"]["se_cl"], df_lr=hs["xi"]["lr"]["df"], df_k1=hs["xi"]["k1"]["df"],
                rel=hs["xi_rel"]["lr"]["point"], rel_hw=hs["xi_rel"]["lr"]["hw"],
                alpha=hs["alpha"]["lr"]["point"], alpha_hw=hs["alpha"]["lr"]["hw"],
                seen=hs["seen"]["lr"]["point"], floor_lb=hs["floor_lb"],
                l3_rel=hs["layer"][0]["rel"]["point"], l3_rel_hw=hs["layer"][0]["rel"]["hw"],
                l3_eval=hs["layer"][0]["evaluable"], l3_h=hs["layer"][0]["h_cx"])
    return v, diag


def run(sc: dict, n_seeds: int, se_scale: float, reps: int, pool) -> dict:
    tag = json.dumps(sc, sort_keys=True) + f"|{n_seeds}|{se_scale}"
    seeds = [zlib.crc32(tag.encode()) * 100003 + i for i in range(reps)]
    res = pool.map(one, [(s, sc, n_seeds, se_scale) for s in seeds], chunksize=4)
    out = {}
    for name in res[0][0]:
        go = np.mean([r[0][name]["go"] for r in res])
        neg = np.mean([r[0][name]["neg"] for r in res])
        lab = {}
        for r in res:
            for l in r[0][name]["labels"]:
                lab[l] = lab.get(l, 0) + 1
        out[name] = dict(P_GO=float(go), P_NEG=float(neg), P_decisive=float(go + neg),
                         label_rates={l: c / reps for l, c in sorted(lab.items())})
    diag = {key: float(np.median([r[1][key] for r in res])) for key in res[0][1]}
    diag["sd_xi_point"] = float(np.std([r[1]["xi"] for r in res]))
    out["diagnostics_hs_median"] = diag
    return out


def validate() -> dict:
    """The K1-estimator interval of this file against the registered K1 code, on synthetic reads."""
    rng = np.random.default_rng(7)
    report = []
    for trial in range(3):
        pairs, qs = build_families(rng)
        sc = dict(H=30.0, seed_sd=1.5, gamma_u=3.0 * trial)
        data = generate(rng, sc, 3, 1.0, pairs, qs)
        ind, tgt = data["hs"]
        U = np.isin(pairs, UNSEEN)
        fam_ind = ind.mean(axis=1)[:, U, :]          # (S, F_u, 2) layer mean
        fam_tgt = tgt.mean(axis=0)[U, :]
        clu = CLU_OF_Q[qs[U]]
        table = k.FamilyTable(pairs[U], LINKS[clu], fam_ind[..., 0], fam_ind[..., 1],
                              fam_tgt[:, 0], fam_tgt[:, 1], np.full(U.sum(), RAND), np.full(U.sum(), RAND))
        kx = k.xi_interval(table, replicates=B)
        kr = k.xi_rel_interval(table, replicates=B)
        mine = read_target(ind, tgt, pairs, qs, sc, 3, (5 / 30, 10 / 30))
        report.append(dict(
            k1_point=kx.point, mine_point=mine["xi"]["k1"]["point"],
            k1_se=kx.se_cluster, mine_se=mine["xi"]["k1"]["se_cl"],
            k1_hw=kx.half_width, mine_hw=mine["xi"]["k1"]["hw"], k1_df=kx.df, mine_df=mine["xi"]["k1"]["df"],
            k1_rel=kr.point, mine_rel=mine["xi_rel"]["k1"]["point"],
            k1_rel_se=kr.se_cluster, mine_rel_se=mine["xi_rel"]["k1"]["se_cl"],
            k1_rel_hw=kr.half_width, mine_rel_hw=mine["xi_rel"]["k1"]["hw"],
            lr_hw=mine["xi"]["lr"]["hw"], lr_df=mine["xi"]["lr"]["df"]))
    worst = max(max(abs(r["k1_point"] - r["mine_point"]), abs(r["k1_se"] - r["mine_se"]),
                    abs(r["k1_hw"] - r["mine_hw"]), abs(r["k1_rel"] - r["mine_rel"]),
                    abs(r["k1_rel_se"] - r["mine_rel_se"]), abs(r["k1_rel_hw"] - r["mine_rel_hw"]))
                for r in report)
    return dict(trials=report, max_abs_difference=worst, agree_1e9=bool(worst < 1e-9))


def plan():
    base = dict(H=30.0, seed_sd=1.0)
    A = []
    for H in (20.0, 30.0, 40.0):
        for s in (0.5, 1.0, 2.0, 3.0):
            for g in (0.0, 2.5, 5.0, 7.5, 10.0, 12.0, 15.0):
                A.append(("A", dict(H=H, seed_sd=s, gamma_u=g), 3, SE_MID))
    Bp = []
    for name, extra in (
        ("alpha6", dict(alpha_u=6.0)), ("alpha10", dict(alpha_u=10.0)),
        ("beta10", dict(beta_u=10.0)),
        ("layer3_total_failure", dict(layer_extra=(0, 0.8))),
        ("layer31_15pts", dict(layer_extra=(7, 15.0 / (H_LAYER[7, 1] * 30.0 / H_DEV_CX)))),
        ("seen_excess8", dict(gamma_s=8.0)),
        # literal channels, residual fractions r from S1 (repair-literal-channel-sim.json)
        ("gamma10_displacement_minus8_h80", dict(gamma_u=10.0, b_lit=-8.0, r_lf=0.0, r_pre=0.07)),
        ("gamma7.5_displacement_minus4_h80", dict(gamma_u=7.5, b_lit=-4.0, r_lf=0.0, r_pre=0.05)),
        ("gamma0_displacement_minus3.6_h80", dict(b_lit=-3.6, r_lf=0.0, r_pre=0.0)),
        ("gamma7.5_longrange_antispill_h40_ell3", dict(gamma_u=7.5, b_lit=-5.3, r_lf=0.52, r_pre=-0.09)),
        ("gamma10_longrange_antispill_h40_ell3", dict(gamma_u=10.0, b_lit=-5.6, r_lf=0.49, r_pre=-0.08)),
        ("gamma0_longrange_spill_plus10_h15_ell3", dict(b_lit=9.9, r_lf=1.0, r_pre=-0.1)),
        ("gamma5_longrange_spill_plus6_h40_ell3", dict(gamma_u=5.0, b_lit=6.0, r_lf=1.0, r_pre=-0.3)),
        ("gamma12_near_concentrated", dict(gamma_u=12.0, kappa_lf=0.68, kappa_pre=0.53)),
        ("gamma0_alpha6_displacement_minus3", dict(alpha_u=6.0, b_lit=-3.0, r_lf=0.0, r_pre=0.0)),
    ):
        Bp.append(("B:" + name, {**base, **extra}, 3, SE_MID))
    C = []
    for se in (SE_LOW, SE_MID, SE_HIGH):
        for s in (1.0, 2.0):
            for g in (0.0, 12.0):
                C.append(("C", dict(H=30.0, seed_sd=s, gamma_u=g), 3, se))
    D = []
    for H in (20.0, 30.0, 40.0):
        for s in (1.0, 2.0, 3.0, 4.0):
            for g in (0.0, 12.0):
                D.append(("D5", dict(H=H, seed_sd=s, gamma_u=g), 5, SE_MID))
    return Bp + A + C + D


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "validate":
        print(json.dumps(validate(), indent=1))
        return
    reps = int(os.environ.get("S2_REPS", "2000"))
    if mode == "resume":
        # Complete a run that was stopped: rows are keyed by (table, scenario,
        # seeds, scale) and every replicate's generator is seeded from that key,
        # so a resumed row equals the row an uninterrupted run would write.
        path = sys.argv[2]
        out = json.load(open(path))
        done = {(r["table"], json.dumps(r["scenario"], sort_keys=True), r["n_seeds"], r["se_scale"]) for r in out["rows"]}
        out.setdefault("resumed_rows", [])
        with Pool(int(os.environ.get("NPROC", "16"))) as pool:
            for table, sc, n_seeds, se_scale in plan():
                key = (table, json.dumps(sc, sort_keys=True), n_seeds, se_scale)
                if key in done:
                    continue
                r = run(sc, n_seeds, se_scale, reps, pool)
                out["rows"].append(dict(table=table, scenario=sc, n_seeds=n_seeds, se_scale=se_scale, result=r))
                out["resumed_rows"].append(len(out["rows"]) - 1)
                print(table, json.dumps(sc), n_seeds, se_scale, flush=True)
                with open(path, "w") as fh:
                    json.dump(out, fh, indent=1, sort_keys=True)
        return
    out = {"parameters": dict(B=B, reps=reps, ctrl_share=CTRL_SHARE, n_clusters=int(N_CLU),
                              controlled_questions=int(CTRL_Q.size), exclusion=EXCL, g=G_RET,
                              lambda_layer=LAMBDA_L, sd_seed_family=SD_V, delta_sd=DELTA_SD),
           "validation": validate(), "rows": []}
    print("validation", json.dumps({k_: v for k_, v in out["validation"].items() if k_ != "trials"}), flush=True)
    with Pool(int(os.environ.get("NPROC", "16"))) as pool:
        for table, sc, n_seeds, se_scale in plan():
            r = run(sc, n_seeds, se_scale, reps, pool)
            row = dict(table=table, scenario=sc, n_seeds=n_seeds, se_scale=se_scale, result=r)
            out["rows"].append(row)
            brief = {v: (round(r[v]["P_GO"], 3), round(r[v]["P_NEG"], 3)) for v in r if v != "diagnostics_hs_median"}
            d = r["diagnostics_hs_median"]
            print(table, json.dumps(sc), n_seeds, se_scale, json.dumps(brief),
                  f"se_cl {d['se_cl']:.2f} hw_lr {d['hw_lr']:.2f} hw_k1 {d['hw_k1']:.2f} df_lr {d['df_lr']:.1f}",
                  flush=True)
            path = sys.argv[2] if len(sys.argv) > 2 else "repair-decision-sim.json"
            with open(path, "w") as fh:     # rewritten after every row
                json.dump(out, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
