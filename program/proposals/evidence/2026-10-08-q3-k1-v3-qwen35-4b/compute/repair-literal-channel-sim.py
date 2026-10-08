"""K1 v3 wave-1 repair, simulation S1: literal channels of the overlap-masked statistic.

A block-level Monte Carlo of one family's two legs (MN: question in the needle's
language; CX: human translation in the other script). It is a mechanism model, not a
measurement of Qwen3.5-4B-Base. Every parameter is a stated assumption; where the
development read (lane 862) fixes one it is used: 2,048 blocks of 4 tokens, a budget of
256 blocks (random rate 12.5 points), target headroom near 35 to 40 points, a literal
selector (LEX) that recalls 16 to 28 points of the unmasked needle on MN and random on CX.

Literal structure of a family (MN leg only; CX shares no content token, E2):
- exact literal blocks: needle blocks holding a content token of the MN question (the
  registered exact rule; these are the overlap-masked blocks) and same-language haystack
  blocks holding one;
- near-literal blocks: blocks that share a character n-gram of a question content word
  but no content token id (inflection, subword split, paraphrase); the exact rule misses
  them, the registered near rule (registration decision 75) catches them.

Selectors. T: the dense target, which itself attends to literal blocks and to the blocks
after them (spill through the hybrid's convolution, recurrence and attention states).
I: the indexer = T + noise (sigma 0.7, the V1-adequate null level of E3) + an excess
literal tilt: lam_D on literal blocks (direct) and lam_S on the blocks that follow a
literal block, decaying with range ell blocks (spill). Negative values are an indexer
less literal than its target. LEX: exact-rule count (the wave-1 literal selector).
LEXk: the registered kernel-literal selector, whose rule differs from the mask: a block's
exact count plus 0.5 and 0.25 times the counts of the one and two blocks before it.

Statistics per family, each the DiD [R_A(MN) - R_A(CX)] - [R_T(MN) - R_T(CX)]:
- xi^M: evidence = needle blocks outside the exact-rule mask (the primary statistic);
- xi^LF (literal-free, r = 2): evidence = needle blocks farther than r blocks from any
  exact or near literal needle block of either question; candidates on each leg exclude
  every block within r of a literal block (exact or near) of that leg's question and the
  needle's dilated mask; same budget. Displacement (budget taken by literal blocks and
  their neighbours) and local spill (unmasked needle blocks next to literal ones) are
  both outside xi^LF by construction.
- xi^PRE (pre-literal): evidence = needle blocks before the first exact or near
  literal needle block; candidates as for LF. Forward (causal) spill from the
  needle's own literal blocks cannot reach them.
- the pre-step's agreement diagnostic is |xi^M - xi^LF| (macro); the registered
  decision conditions are bands on xi^LF and xi^PRE (registration decisions 74, 76).

Environment: S1_FAMILIES (families per scenario, 1,200 in the bundle run),
S1_TARGET_LITERAL (the target's attraction to exact literal blocks: 2.0 strong,
1.0 weak; near-literal attraction is half of it), NPROC. The literal-leaning null
N_lambda here includes the indexer's noise (sigma 0.7); the registered N_lambda is
noise-free.

Output: JSON with, per scenario and tilt, the mean literal bias of xi^M and xi^LF (common
random numbers against the untilted indexer), the mean and family SD of
Delta = xi^M - xi^LF, the probability the macro agreement condition passes, and the
derived bound: the largest |bias of xi^M| on the grid that still passes with probability
at least 0.05. Also the wave-1 LEX check, LEXk and the literal-leaning null family
(top-k of T + lam * LEXk) used by the pre-step's sensitivity and specificity items.
"""

from __future__ import annotations

import json
import math
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np

NB, K, ROWS, R_DIL = 2048, 256, 3, 2
SIGMA_I = 0.7
H_N, H_N_CX = 1.30, 1.27          # needle relevance: target masked headroom ~35-37 on both legs
H_L = float(os.environ.get("S1_TARGET_LITERAL", "2.0"))   # target attraction to exact literal blocks
H_F, K_T, ELL_T = 0.5 * H_L, 0.5, 1.0                       # near-literal attraction, target spill
N_FAM = int(os.environ.get("S1_FAMILIES", "1200"))
MACRO_N_EFF = 970                 # ~1,450 controlled unseen families / design effect 1.5
AGREE = 2.5


def dilate(mask: np.ndarray, r: int) -> np.ndarray:
    out = mask.copy()
    for d in range(1, r + 1):
        out[d:] |= mask[:-d]
        out[:-d] |= mask[d:]
    return out


def spill(lit: np.ndarray, ell: float, depth: int = 12) -> np.ndarray:
    """Forward spill: block b receives exp(-(d-1)/ell) from a literal block b-d, d >= 1."""
    out = np.zeros(lit.shape[-1])
    if ell <= 0:
        return out
    x = lit.astype(float)
    for d in range(1, depth + 1):
        out[d:] += math.exp(-(d - 1) / ell) * x[:-d]
    return out


def family(rng: np.random.Generator, h_mean: float) -> dict:
    n_n = int(rng.integers(30, 71))
    depth = float(rng.choice([0.15, 0.5, 0.85]))
    s0 = 1 + int(round(depth * (NB - 1 - n_n)))
    needle = np.zeros(NB, bool)
    needle[s0:s0 + n_n] = True
    # exact literal needle blocks: 1-3 runs, 10-30 percent of the needle
    m = max(1, int(round(rng.uniform(0.10, 0.30) * n_n)))
    lit_e = np.zeros(NB, bool)
    runs = int(rng.integers(1, 4))
    sizes = np.maximum(1, np.round(np.full(runs, m / runs))).astype(int)
    for size in sizes:
        start = s0 + int(rng.integers(0, max(1, n_n - size)))
        lit_e[start:start + size] = True
    # near-literal needle blocks: 0-10 percent, half next to the exact runs
    m_f = int(round(rng.uniform(0.0, 0.10) * n_n))
    lit_f = np.zeros(NB, bool)
    nidx = np.flatnonzero(needle & ~lit_e)
    adj = np.flatnonzero(dilate(lit_e, 1) & needle & ~lit_e)
    for j in range(m_f):
        pool = adj if (j % 2 == 0 and adj.size) else nidx
        if pool.size:
            lit_f[int(rng.choice(pool))] = True
    # same-language haystack literal blocks on MN (exact and near)
    hay = np.flatnonzero(~needle)
    hay = hay[hay > 0]
    h = int(rng.poisson(h_mean))
    hf = int(rng.poisson(0.5 * h_mean))
    pos = rng.choice(hay, size=min(h + hf, hay.size), replace=False)
    lit_e[pos[:h]] = True
    lit_f[pos[h:]] = True
    lit_f &= ~lit_e
    rel = np.zeros(NB)
    rel[needle] = 0.5 + rng.random(n_n)
    base = rng.normal(size=NB)
    return dict(needle=needle, lit_e=lit_e, lit_f=lit_f, rel=rel, base=base, n_n=n_n)


def masks(f: dict) -> dict:
    needle = f["needle"]
    mask_e = needle & f["lit_e"]                      # registered exact-rule overlap mask
    ev_m = needle & ~mask_e
    lit_all_mn = f["lit_e"] | f["lit_f"]
    mask_lf = dilate(needle & lit_all_mn, R_DIL) & needle
    ev_lf = needle & ~mask_lf
    excl_mn = dilate(lit_all_mn, R_DIL) | mask_lf
    excl_cx = mask_lf.copy()                          # CX: no literal block of its own
    excl_mn[0] = excl_cx[0] = True                    # sink
    cand = {"MN": ~excl_mn, "CX": ~excl_cx}
    cand_all = np.ones(NB, bool)
    cand_all[0] = False
    # PRE: needle blocks before the first literal (exact or near) needle block; forward spill
    # from needle literal blocks cannot reach them (causal model)
    lit_needle = np.flatnonzero(needle & lit_all_mn)
    ev_pre = needle.copy()
    if lit_needle.size:
        ev_pre[lit_needle[0]:] = False
    return dict(ev_m=ev_m, ev_lf=ev_lf, ev_pre=ev_pre, cand=cand, cand_all=cand_all, mask_e=mask_e)


def recall(scores: np.ndarray, cand: np.ndarray, ev: np.ndarray) -> float:
    """Mean over rows of the percent of evidence blocks in the top-K candidate blocks."""
    if ev.sum() == 0:
        return float("nan")
    s = np.where(cand, scores, -np.inf)
    k = min(K, int(cand.sum()))
    top = np.argpartition(-s, k - 1, axis=-1)[..., :k]
    hit = ev[top].sum(axis=-1)
    return float(np.mean(hit / ev.sum() * 100.0))


def target_scores(f: dict, rng: np.random.Generator) -> dict:
    out = {}
    lit_all = (f["lit_e"] | f["lit_f"])
    sp = spill(lit_all, ELL_T)
    for leg, hn in (("MN", H_N), ("CX", H_N_CX)):
        s = f["base"][None, :] + 0.5 * rng.normal(size=(ROWS, NB)) + hn * f["rel"][None, :]
        if leg == "MN":
            s = s + H_L * f["lit_e"] + H_F * f["lit_f"] + K_T * H_L * sp
        out[leg] = s
    return out


def lex_scores(f: dict, rng: np.random.Generator, kernel: bool) -> dict:
    out = {}
    for leg in ("MN", "CX"):
        c = f["lit_e"].astype(float) if leg == "MN" else np.zeros(NB)
        if kernel:
            k = c.copy()
            k[1:] += 0.5 * c[:-1]
            k[2:] += 0.25 * c[:-2]
            c = k
        out[leg] = c[None, :] + 1e-6 * rng.random((ROWS, NB))
    return out


def lexk_unit(f: dict) -> dict:
    out = {}
    for leg in ("MN", "CX"):
        c = f["lit_e"].astype(float) if leg == "MN" else np.zeros(NB)
        k = c.copy()
        k[1:] += 0.5 * c[:-1]
        k[2:] += 0.25 * c[:-2]
        out[leg] = k
    return out


def dids(sel: dict, tgt: dict, m: dict) -> dict:
    res = {}
    for name, cand_key, ev_key in (("M", "all", "ev_m"), ("LF", "lf", "ev_lf"), ("PRE", "lf", "ev_pre")):
        def r(scores, leg):
            cand = m["cand_all"] if cand_key == "all" else m["cand"][leg]
            return recall(scores[leg], cand, m[ev_key])
        res[name] = (r(sel, "MN") - r(sel, "CX")) - (r(tgt, "MN") - r(tgt, "CX"))
    return res


def run_family(args) -> dict:
    seed, h_mean, ell, grid, gammas, null_lams = args
    rng = np.random.default_rng(seed)
    f = family(rng, h_mean)
    m = masks(f)
    tgt = target_scores(f, rng)
    eps = {leg: SIGMA_I * rng.normal(size=(ROWS, NB)) for leg in ("MN", "CX")}
    lit_all = f["lit_e"] | f["lit_f"]
    direct = f["lit_e"] + 0.5 * f["lit_f"]
    sp = spill(lit_all, ell)
    out = {"lf_evidence_blocks": int(m["ev_lf"].sum()), "m_evidence_blocks": int(m["ev_m"].sum()),
           "pre_evidence_blocks": int(m["ev_pre"].sum()),
           "needle_blocks": f["n_n"], "tilt": {}, "gamma": {}, "null": {}}
    # target headroom (masked) on each leg, for calibration
    rand_m = K / (NB - 1) * 100.0
    out["target_masked_recall"] = {leg: recall(tgt[leg], m["cand_all"], m["ev_m"]) for leg in ("MN", "CX")}
    out["rand"] = rand_m
    for (lam_d, lam_s) in grid:
        ind = {}
        for leg in ("MN", "CX"):
            s = tgt[leg] + eps[leg]
            if leg == "MN":
                s = s + lam_d * direct + lam_s * sp
            ind[leg] = s
        out["tilt"][f"{lam_d},{lam_s}"] = dids(ind, tgt, m)
    for name, (g, where) in gammas.items():
        ind = {}
        w = np.ones(NB)
        if where == "near":   # deficit twice as large within 2 blocks of a literal needle block
            near = dilate(f["needle"] & lit_all, R_DIL + 1) & f["needle"]
            w = np.where(near, 2.0, 0.5)
        for leg in ("MN", "CX"):
            s = tgt[leg] + eps[leg]
            if leg == "CX":
                s = s - g * H_N_CX * f["rel"] * w
            ind[leg] = s
        out["gamma"][name] = dids(ind, tgt, m)
    # wave-1 LEX and the kernel-literal selector LEXk as selectors in place of the indexer
    out["LEX"] = dids(lex_scores(f, rng, False), tgt, m)
    out["LEXk"] = dids(lex_scores(f, rng, True), tgt, m)
    # literal-leaning null family: top-k of (target + lam * LEXk)
    lk = lexk_unit(f)
    for lam in null_lams:
        sel = {leg: tgt[leg] + eps[leg] + lam * lk[leg][None, :] for leg in ("MN", "CX")}
        out["null"][str(lam)] = dids(sel, tgt, m)
    # plain block-score null (no tilt): specificity of the agreement condition
    out["null"]["sigma_only"] = dids({leg: tgt[leg] + eps[leg] for leg in ("MN", "CX")}, tgt, m)
    return out


def summarise(rows: list[dict], key_path) -> dict:
    vals_m = np.array([key_path(r)["M"] for r in rows])
    vals_lf = np.array([key_path(r)["LF"] for r in rows])
    vals_pre = np.array([key_path(r)["PRE"] for r in rows])
    pre_n = np.array([r["pre_evidence_blocks"] for r in rows])
    ok = np.isfinite(vals_m) & np.isfinite(vals_lf)
    okp = ok & np.isfinite(vals_pre) & (pre_n >= 8)
    d = vals_m[ok] - vals_lf[ok]
    return dict(xi_M=float(vals_m[ok].mean()), xi_LF=float(vals_lf[ok].mean()),
                xi_PRE=float(vals_pre[okp].mean()), xi_PRE_family_sd=float(vals_pre[okp].std(ddof=1)),
                n_pre=int(okp.sum()),
                delta=float(d.mean()), delta_family_sd=float(d.std(ddof=1)),
                xi_M_family_sd=float(vals_m[ok].std(ddof=1)),
                xi_LF_family_sd=float(vals_lf[ok].std(ddof=1)), n=int(ok.sum()))


def pass_prob(mean: float, fam_sd: float) -> float:
    from scipy.stats import norm
    sd = fam_sd / math.sqrt(MACRO_N_EFF)
    return float(norm.cdf((AGREE - mean) / sd) - norm.cdf((-AGREE - mean) / sd))


def main() -> None:
    lam_d_grid = [-1.0, -0.5, 0.0, 0.25, 0.5, 1.0, 2.0]
    lam_s_grid = [-0.5, 0.0, 0.25, 0.5, 1.0, 2.0]
    grid = [(a, b) for a in lam_d_grid for b in lam_s_grid]
    gammas = {"gamma0.15_uniform": (0.15, "uniform"), "gamma0.30_uniform": (0.30, "uniform"),
              "gamma0.30_near_concentrated": (0.30, "near")}
    null_lams = [0.25, 0.5, 1.0, 2.0, 4.0]
    scenarios = [(h, ell) for h in (15, 40, 80) for ell in (0.5, 1.0, 3.0)]
    results = {"parameters": dict(NB=NB, K=K, ROWS=ROWS, R_DIL=R_DIL, SIGMA_I=SIGMA_I, H_N=H_N,
                                  H_N_CX=H_N_CX, H_L=H_L, H_F=H_F, K_T=K_T, ELL_T=ELL_T,
                                  families=N_FAM, macro_n_eff=MACRO_N_EFF, agree=AGREE,
                                  lam_d_grid=lam_d_grid, lam_s_grid=lam_s_grid,
                                  null_lams=null_lams),
               "scenarios": {}}
    with Pool(int(os.environ.get("NPROC", "16"))) as pool:
        for h_mean, ell in scenarios:
            tag = f"h{h_mean}_ell{ell}"
            seeds = [zlib.crc32(tag.encode()) * 1000003 + i for i in range(N_FAM)]
            rows = pool.map(run_family, [(s, h_mean, ell, grid, gammas, null_lams) for s in seeds],
                            chunksize=8)
            base = summarise(rows, lambda r: r["tilt"]["0.0,0.0"])
            sc = {"untilted": base}
            tilt = {}
            for (a, b) in grid:
                s = summarise(rows, lambda r, a=a, b=b: r["tilt"][f"{a},{b}"])
                s["bias_M"] = s["xi_M"] - base["xi_M"]
                s["bias_LF"] = s["xi_LF"] - base["xi_LF"]
                s["bias_PRE"] = s["xi_PRE"] - base["xi_PRE"]
                s["p_agree"] = pass_prob(s["delta"], s["delta_family_sd"])
                tilt[f"{a},{b}"] = s
            sc["tilt"] = tilt
            passing = [abs(v["bias_M"]) for v in tilt.values() if v["p_agree"] >= 0.05]
            # NEGATIVE-side bound: the largest downward bias of xi^M that passes the agreement
            # condition (a downward bias is what can hide a true excess inside NEGATIVE)
            neg_passing = [-v["bias_M"] for v in tilt.values() if v["p_agree"] >= 0.05 and v["bias_M"] < 0]
            sc["bound_downward_bias_M_passing_p05"] = float(max(neg_passing)) if neg_passing else 0.0
            sc["bound_downward_bias_LF_passing_p05"] = float(max([-v["bias_LF"] for v in tilt.values()
                                                                    if v["p_agree"] >= 0.05 and v["bias_LF"] < 0] or [0.0]))
            caught = [abs(v["bias_M"]) for v in tilt.values() if v["p_agree"] < 0.05]
            sc["bound_abs_bias_M_passing_p05"] = float(max(passing)) if passing else float("nan")
            sc["smallest_abs_bias_M_caught"] = float(min(caught)) if caught else float("nan")
            sc["gamma"] = {}
            for name in gammas:
                s = summarise(rows, lambda r, n=name: r["gamma"][n])
                s["p_agree"] = pass_prob(s["delta"], s["delta_family_sd"])
                sc["gamma"][name] = s
            sc["LEX_wave1"] = summarise(rows, lambda r: r["LEX"])
            sc["LEXk"] = summarise(rows, lambda r: r["LEXk"])
            sc["literal_leaning_null"] = {}
            for lam in null_lams + ["sigma_only"]:
                s = summarise(rows, lambda r, l=lam: r["null"][str(l)])
                s["p_agree"] = pass_prob(s["delta"], s["delta_family_sd"])
                sc["literal_leaning_null"][str(lam)] = s
            ev_lf = np.array([r["lf_evidence_blocks"] for r in rows])
            ev_m = np.array([r["m_evidence_blocks"] for r in rows])
            ev_pre = np.array([r["pre_evidence_blocks"] for r in rows])
            sc["evaluability"] = dict(
                share_lf_at_least_8_blocks=float((ev_lf >= 8).mean()),
                share_m_at_least_8_blocks=float((ev_m >= 8).mean()),
                share_pre_at_least_8_blocks=float((ev_pre >= 8).mean()),
                median_lf_over_needle=float(np.median(ev_lf / np.array([r["needle_blocks"] for r in rows]))),
                median_m_over_needle=float(np.median(ev_m / np.array([r["needle_blocks"] for r in rows]))))
            tm = np.array([[r["target_masked_recall"]["MN"], r["target_masked_recall"]["CX"]] for r in rows])
            sc["target_masked_headroom"] = dict(MN=float(np.nanmean(tm[:, 0]) - rows[0]["rand"]),
                                                CX=float(np.nanmean(tm[:, 1]) - rows[0]["rand"]))
            results["scenarios"][tag] = sc
            print(tag, json.dumps({"untilted": {k: round(v, 3) for k, v in base.items()},
                                   "bound": round(sc["bound_abs_bias_M_passing_p05"], 2),
                                   "bound_down": round(sc["bound_downward_bias_M_passing_p05"], 2),
                                   "smallest_caught": round(sc["smallest_abs_bias_M_caught"], 2),
                                   "LEX_xi_M": round(sc["LEX_wave1"]["xi_M"], 2),
                                   "LEXk_xi_M": round(sc["LEXk"]["xi_M"], 2),
                                   "headroom": {k: round(v, 1) for k, v in sc["target_masked_headroom"].items()},
                                   "eval": {k: round(v, 3) for k, v in sc["evaluability"].items()}}),
                  flush=True)
    out = sys.argv[1] if len(sys.argv) > 1 else "repair-literal-channel-sim.json"
    with open(out, "w") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
