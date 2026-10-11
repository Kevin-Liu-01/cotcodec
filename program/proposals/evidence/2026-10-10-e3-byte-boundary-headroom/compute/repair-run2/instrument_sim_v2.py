#!/usr/bin/env python3
"""S1v2: the registered v2 estimator on synthetic EN-X pairs, with an aligner error model.

CPU only, seeded; no FLORES text, no model, no aligner. Imports the registered
estimator (e3_estimator_v2.py) unchanged, so every number here is produced by the
decision code. Wave 1's S1 (../instrument_sim.py) is kept as it was.

Synthetic pairs (word level, with a byte layout for the convention check):
* K semantic units in English order, bracketed by a random binary tree (a
  synchronous tree); each internal node is inverted in the other language with
  probability p_inv (ZH-like 0.20, PL-like 0.06, KO-like 0.45); a final full stop
  is aligned on both sides.
* English: 1-3 content words per unit, an unlinked function word before a unit
  with probability 0.25. ZH-like: 1-3 segmenter words per unit (1-3 characters of
  3 bytes each), an unlinked function word after a unit with probability 0.15, and
  with probability p_split a unit's last word moved elsewhere (a discontiguous,
  crossing unit). PL-like: spaced words, some 2-byte characters. KO-like: one
  eojeol per unit, and an English function word fused into the next eojeol (and
  linked to it) with probability 0.5.
* True links: words of the same unit, all pairs.

Aligner error model (calibrated to link-level AER against the true links, sure
links only): each true link dropped with probability d; each word of either side
receives, with probability s, a spurious link to a word one or two positions from
its partner's position (or from its neighbour's partner when it is unlinked).
Two aligners A and B draw their error events from a shared stream with
probability c (error correlation) and from private streams otherwise.

Parts:
  calib   - (d, s) for each target AER, balanced, precision-heavy and recall-heavy
  atten   - attenuation alpha = S under an aligner of the truth oracle, by AER, c, profile
  ident   - wave 1's density / word-end scenario under the v1 statistic and under v2
  gates   - I1 transplant control, I2 random, I3 convention, budget and drop diagnostics
  oc      - decision operating characteristics (band path and gold-corrected path)
  linem   - the monolingual syntactic reference (line M) under tree divergence

Usage: instrument_sim_v2.py <out.json> --part <part> [--seeds ...] [--cond ...] [--quick]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3_estimator_v2 as est  # noqa: E402

PROFILES = {
    "zh": {"p_inv": 0.20, "p_split": 0.04, "x_null": 0.15, "kind": "zh"},
    "pl": {"p_inv": 0.06, "p_split": 0.01, "x_null": 0.05, "kind": "pl"},
    "ko": {"p_inv": 0.45, "p_split": 0.03, "x_null": 0.05, "kind": "ko"},
}

# ----------------------------------------------------------------------------
# Synthetic pairs
# ----------------------------------------------------------------------------


class Node:
    __slots__ = ("left", "right", "unit", "inv")

    def __init__(self, left=None, right=None, unit=None, inv=False):
        self.left, self.right, self.unit, self.inv = left, right, unit, inv


def build_tree(rng, lo: int, hi: int, p_inv: float) -> Node:
    if hi - lo == 1:
        return Node(unit=lo)
    s = int(rng.integers(lo + 1, hi))
    return Node(build_tree(rng, lo, s, p_inv), build_tree(rng, s, hi, p_inv), inv=bool(rng.random() < p_inv))


def leaves(node: Node, side: str) -> list[int]:
    if node.unit is not None:
        return [node.unit]
    a, b = leaves(node.left, side), leaves(node.right, side)
    return b + a if (side == "b" and node.inv) else a + b


def cat(rng, values, cum) -> int:
    return values[int(np.searchsorted(cum, rng.random(), side="right"))]


_P3 = (1, 2, 3)
_C_EN = np.cumsum([0.6, 0.3, 0.1])[:-1]
_C_ZHW = np.cumsum([0.65, 0.30, 0.05])[:-1]
_C_ZHC = np.cumsum([0.35, 0.55, 0.10])[:-1]
_C_PL = np.cumsum([0.85, 0.15])[:-1]


def gen_pair(rng, prof: dict, K_mean: float = 8.0) -> dict:
    K = 6 + int(rng.poisson(K_mean))
    tree = build_tree(rng, 0, K, prof["p_inv"])
    # tokens: (char widths, unit or -1, space_before)
    en: list[tuple[list[int], int, bool]] = []
    en_fused_into: dict[int, int] = {}  # EN function word index -> unit it is fused with (KO-like)
    for u in leaves(tree, "a"):
        if rng.random() < 0.25:
            en.append(([1] * (1 + int(rng.poisson(1.5))), -1, True))
            if prof["kind"] == "ko" and rng.random() < 0.5:
                en_fused_into[len(en) - 1] = u
        nw = cat(rng, _P3, _C_EN)
        for _ in range(nw):
            en.append(([1] * (2 + int(rng.poisson(3.6))), u, True))
    en.append(([1], K, False))  # full stop, unit K
    xb: list[tuple[list[int], int, bool]] = []
    order_b = leaves(tree, "b")
    for u in order_b:
        if prof["kind"] == "zh":
            nw = cat(rng, _P3, _C_ZHW)
            for _ in range(nw):
                nc = cat(rng, _P3, _C_ZHC)
                xb.append(([3] * nc, u, False))
            if rng.random() < prof["x_null"]:
                xb.append(([3], -1, False))
        elif prof["kind"] == "pl":
            nw = cat(rng, (1, 2), _C_PL)
            for _ in range(nw):
                n = 2 + int(rng.poisson(4.5))
                xb.append(([2 if rng.random() < 0.08 else 1 for _ in range(n)], u, True))
            if rng.random() < prof["x_null"]:
                xb.append(([1] * (1 + int(rng.poisson(1.0))), -1, True))
        else:  # ko
            n = 2 + int(rng.poisson(1.2))
            xb.append(([3] * n, u, True))
    # discontiguous units: move a unit's last word elsewhere
    if prof["p_split"] > 0:
        by_unit: dict[int, list[int]] = {}
        for idx, t in enumerate(xb):
            if t[1] >= 0:
                by_unit.setdefault(t[1], []).append(idx)
        for u, idxs in list(by_unit.items()):
            if len(idxs) >= 2 and rng.random() < prof["p_split"]:
                tok = xb.pop(idxs[-1])
                xb.insert(int(rng.integers(0, len(xb) + 1)), tok)
                by_unit = {}
                for idx, t in enumerate(xb):
                    if t[1] >= 0:
                        by_unit.setdefault(t[1], []).append(idx)
    xb.append(([3] if prof["kind"] == "zh" else [1], K, False))
    unit_a = np.array([t[1] for t in en])
    unit_b = np.array([t[1] for t in xb])
    by_b: dict[int, list[int]] = {}
    for j, u in enumerate(unit_b.tolist()):
        if u >= 0:
            by_b.setdefault(u, []).append(j)
    links = {(i, j) for i, u in enumerate(unit_a.tolist()) if u >= 0 for j in by_b.get(u, [])}
    for i, u in en_fused_into.items():  # KO-like fused particles
        for j in range(len(xb)):
            if unit_b[j] == u:
                links.add((i, j))
    return {"tree": tree, "en": en, "xb": xb, "unit_a": unit_a, "unit_b": unit_b, "K": K, "links_T": links,
            "n_a": len(en), "n_b": len(xb)}


# ----------------------------------------------------------------------------
# Aligner error model
# ----------------------------------------------------------------------------

def noisy_links(pair: dict, d: float, s: float, c: float, shared: np.ndarray, rng) -> set:
    """Links of one aligner. shared: (n_events, 2) uniforms common to both aligners of this pair."""
    T = sorted(pair["links_T"])
    n_a, n_b = pair["n_a"], pair["n_b"]
    n_ev = len(T) + n_a + n_b
    own = rng.random((n_ev, 2))
    use = rng.random(n_ev) < c
    U = np.where(use[:, None], shared[:n_ev], own)
    out = {lk for e, lk in enumerate(T) if U[e, 0] >= d}
    part_a: dict[int, list[int]] = {}
    part_b: dict[int, list[int]] = {}
    for i, j in T:
        part_a.setdefault(i, []).append(j)
        part_b.setdefault(j, []).append(i)

    def centre_a(i):
        for off in (0, -1, 1, -2, 2, -3, 3):
            if 0 <= i + off < n_a and (i + off) in part_a:
                return int(np.median(part_a[i + off]))
        return int(round(i * (n_b - 1) / max(n_a - 1, 1)))

    def centre_b(j):
        for off in (0, -1, 1, -2, 2, -3, 3):
            if 0 <= j + off < n_b and (j + off) in part_b:
                return int(np.median(part_b[j + off]))
        return int(round(j * (n_a - 1) / max(n_b - 1, 1)))

    offs = np.array([-2, -1, 1, 2])
    base = len(T)
    for i in range(n_a):
        u0, u1 = U[base + i]
        if u0 < s:
            j = int(np.clip(centre_a(i) + offs[min(int(u1 * 4), 3)], 0, n_b - 1))
            out.add((i, j))
    base += n_a
    for j in range(n_b):
        u0, u1 = U[base + j]
        if u0 < s:
            i = int(np.clip(centre_b(j) + offs[min(int(u1 * 4), 3)], 0, n_a - 1))
            out.add((i, j))
    if not out:
        out = set(T)
    return out


def aer(pred: set, true: set) -> tuple[float, float, float]:
    inter = len(pred & true)
    p = inter / max(len(pred), 1)
    r = inter / max(len(true), 1)
    return 1 - 2 * inter / max(len(pred) + len(true), 1), p, r


# ----------------------------------------------------------------------------
# Pools
# ----------------------------------------------------------------------------

def prepare(pair: dict, la: set, lb: set, rng, rho: float = est.RHO, floor_draws: int = est.FLOOR_DRAWS,
            with_mono: bool = False) -> dict:
    n_a, n_b = pair["n_a"], pair["n_b"]
    links = {"T": pair["links_T"], "A": la, "B": lb, "C": est.consensus_links(la, lb)}
    M = {k: est.allowed_pairs(n_a, n_b, v) for k, v in links.items()}
    adj = {k: est.row_masks(v) for k, v in M.items()}
    nus = {k: est.nu(M[k], adj=adj[k]) for k in M}
    k = est.budget(n_a - 1, n_b - 1, nus["A"], nus["B"], nus["C"], rho=rho)
    pair = dict(pair)
    pair.update({"links": links, "M": M, "adj": adj, "nu": nus, "k": k})
    pair["agree"] = est.pair_agreement(M["A"], M["B"])
    if with_mono:
        pair["Mmono"] = {kk: est.monotone_pairs(n_a, n_b, v) for kk, v in links.items()}
    if k <= 0:
        pair["floor"] = {x: 0.0 for x in M}
        return pair
    pair["floor"] = {x: est.floor_hits(M[x], k, rng, floor_draws, adj=adj[x]) for x in M}
    return pair


def make_pool(seed: int, prof_name: str, n: int, aer_ab: tuple[float, float], c: float, calib: dict,
              split: str = "balanced", K_mean: float = 8.0, floor_draws: int = est.FLOOR_DRAWS) -> list[dict]:
    rng = np.random.default_rng(seed)
    prof = PROFILES[prof_name]
    da, sa = calib_lookup(calib, prof_name, aer_ab[0], split)
    db, sb = calib_lookup(calib, prof_name, aer_ab[1], split)
    pool = []
    while len(pool) < n:
        pair = gen_pair(rng, prof, K_mean)
        n_ev = len(pair["links_T"]) + pair["n_a"] + pair["n_b"]
        shared = rng.random((n_ev, 2))
        la = noisy_links(pair, da, sa, c, shared, rng)
        lb = noisy_links(pair, db, sb, c, shared, rng)
        pool.append(prepare(pair, la, lb, rng, floor_draws=floor_draws))
    return pool


# ----------------------------------------------------------------------------
# Calibration of the error model to AER
# ----------------------------------------------------------------------------

AER_TARGETS = (0.05, 0.085, 0.12, 0.15, 0.20, 0.25)
SPLITS = {"balanced": 1.0, "precision_heavy": 0.5, "recall_heavy": 2.0}  # ratio of spurious to missed links


def _measure_aer(pairs, d, s, seed):
    r2 = np.random.default_rng(seed)
    num = den_p = den_t = 0
    for p in pairs:
        n_ev = len(p["links_T"]) + p["n_a"] + p["n_b"]
        L = noisy_links(p, d, s, 0.0, r2.random((n_ev, 2)), r2)
        num += len(L & p["links_T"])
        den_p += len(L)
        den_t += len(p["links_T"])
    return 1 - 2 * num / (den_p + den_t), num / den_p, num / den_t


def calib_part(seed: int, n_pairs: int, only: list[str] | None = None) -> dict:
    """Find (d, s) giving each target AER, with the spurious:missed link ratio set by the split.

    With s tied to d so that expected spurious links = ratio x expected missed links, the
    expected AER is 1 - 2(1 - d) / (2 - d + ratio d) when spurious links never coincide
    with existing ones; that value starts a short bisection on measured AER (collisions
    make the measured AER slightly lower).
    """
    out = {}
    for prof_name in PROFILES:
        if only and not any(o.split(":")[0] == prof_name for o in only):
            continue
        rng = np.random.default_rng(seed)
        pairs = [gen_pair(rng, PROFILES[prof_name]) for _ in range(n_pairs)]
        n_true = sum(len(p["links_T"]) for p in pairs)
        n_words = sum(p["n_a"] + p["n_b"] for p in pairs)
        out[prof_name] = {"true_links_per_word": round(n_true / n_words, 4)}
        splits = SPLITS if prof_name == "zh" else {"balanced": 1.0}
        for split, ratio in splits.items():
            if only and f"{prof_name}:{split}" not in only:
                continue
            rows = []
            for target in AER_TARGETS:
                # analytic start: solve 1 - 2(1-d)/(2 - d + ratio d) = target for d
                d0 = 2 * target / (2 - target * (ratio - 1)) if ratio != 1 else target
                d0 = d0 / (1 + target) if ratio == 1 else d0
                lo, hi = max(d0 * 0.6, 0.0), min(d0 * 1.6 + 0.02, 0.9)
                for _ in range(9):
                    d = (lo + hi) / 2
                    s = min(ratio * d * n_true / n_words, 0.95)
                    a, pr, rc = _measure_aer(pairs, d, s, seed + 1)
                    if a < target:
                        lo = d
                    else:
                        hi = d
                d = (lo + hi) / 2
                s = min(ratio * d * n_true / n_words, 0.95)
                a, pr, rc = _measure_aer(pairs, d, s, seed + 1)
                rows.append({"aer_target": target, "d": round(d, 5), "s": round(s, 5), "aer": round(a, 4),
                             "precision": round(pr, 4), "recall": round(rc, 4)})
            out[prof_name][split] = rows
    return {"seed": seed, "pairs": n_pairs, "splits_spurious_to_missed": SPLITS, "table": out}


CALIB: dict | None = None


def calib_lookup(calib: dict, prof_name: str, target: float, split: str = "balanced") -> tuple[float, float]:
    """(d, s) for a target AER: the calibrated row, or linear interpolation between neighbouring rows."""
    rows = sorted(calib["table"][prof_name][split], key=lambda r: r["aer_target"])
    for r in rows:
        if abs(r["aer_target"] - target) < 1e-9:
            return r["d"], r["s"]
    for r0, r1 in zip(rows, rows[1:]):
        if r0["aer_target"] < target < r1["aer_target"]:
            t = (target - r0["aer_target"]) / (r1["aer_target"] - r0["aer_target"])
            return r0["d"] + t * (r1["d"] - r0["d"]), r0["s"] + t * (r1["s"] - r0["s"])
    raise KeyError((prof_name, target, split))


# ----------------------------------------------------------------------------
# Systems (selections of k word gaps per side)
# ----------------------------------------------------------------------------

def oracle_selection(pair: dict, src: str, rng) -> tuple[np.ndarray, np.ndarray]:
    """k pairs drawn from a random maximum matching of src's allowed pairs; random fill if nu < k."""
    k, M = pair["k"], pair["M"][src]
    mm = est.max_matching_pairs(M, rng, adj=pair["adj"][src])
    sel = [mm[i] for i in rng.permutation(len(mm))[: min(k, len(mm))]]
    sa = {a for a, _ in sel}
    sb = {b for _, b in sel}
    na, nb = M.shape
    for s_, n in ((sa, na), (sb, nb)):
        free = [g for g in range(n) if g not in s_]
        need = k - len(s_)
        if need > 0:
            s_.update(rng.choice(free, size=need, replace=False).tolist())
    return np.array(sorted(sa)), np.array(sorted(sb))


def displace(sel: np.ndarray, n: int, f: float, mode: str, rng) -> np.ndarray:
    s = set(sel.tolist())
    out = set(s)
    for g in sel.tolist():
        if rng.random() >= f:
            continue
        out.discard(g)
        cand = []
        if mode == "near":
            cand = [h for h in (g - 1, g + 1) if 0 <= h < n and h not in out and h not in s]
        if not cand:
            cand = [h for h in range(n) if h not in out and h not in s]
        if not cand:
            cand = [h for h in range(n) if h not in out]
        out.add(int(rng.choice(cand)))
    return np.array(sorted(out))


def random_selection(pair: dict, rng) -> tuple[np.ndarray, np.ndarray]:
    na, nb = pair["M"]["T"].shape
    k = pair["k"]
    return np.sort(rng.choice(na, k, replace=False)), np.sort(rng.choice(nb, k, replace=False))


def side_tree(node: Node, side: str):
    """Ordered tree for one side: ('L', unit) or ('N', left, right) in that side's word order."""
    if node.unit is not None:
        return ("L", node.unit)
    a, b = side_tree(node.left, side), side_tree(node.right, side)
    return ("N", b, a) if (side == "b" and node.inv) else ("N", a, b)


def rotate(t, rng, q: float):
    """Side-specific rotations ((A B) C) -> (A (B C)) with probability q per node; leaf order is kept."""
    if t[0] == "L":
        return t
    left, right = t[1], t[2]
    if q > 0 and left[0] == "N" and rng.random() < q:
        t = ("N", left[1], ("N", left[2], right))
    return ("N", rotate(t[1], rng, q), rotate(t[2], rng, q))


def _first(t):
    return t[1] if t[0] == "L" else _first(t[1])


def _last(t):
    return t[1] if t[0] == "L" else _last(t[2])


def tree_depths(node: Node, side: str, rng, q: float) -> dict:
    """Depth of the split between every pair of adjacent units on one side, after rotations."""
    out = {}

    def walk(t, d):
        if t[0] == "L":
            return
        out[(_last(t[1]), _first(t[2]))] = d
        walk(t[1], d + 1)
        walk(t[2], d + 1)

    walk(rotate(side_tree(node, side), rng, q), 0)
    return out


def syntax_scores(pair: dict, side: str, rng, q: float, sigma: float) -> np.ndarray:
    """Monolingual syntactic gap strength: minus the LCA depth of the two words' units (deepest inside a unit)."""
    units = pair["unit_a"] if side == "a" else pair["unit_b"]
    toks = pair["en"] if side == "a" else pair["xb"]
    n = len(toks)
    K = pair["K"]
    dep = tree_depths(pair["tree"], side, rng, q)
    maxd = max(dep.values()) + 2 if dep else 2
    # function words join the next unit (English) or the previous unit (other side)
    eff = units.copy()
    if side == "a":
        nxt = -1
        for i in range(n - 1, -1, -1):
            if eff[i] >= 0:
                nxt = eff[i]
            else:
                eff[i] = nxt
    else:
        prv = -1
        for i in range(n):
            if eff[i] >= 0:
                prv = eff[i]
            else:
                eff[i] = prv
    sc = np.zeros(n - 1)
    for t in range(n - 1):
        u, v = eff[t], eff[t + 1]
        if u == v or u < 0 or v < 0:
            sc[t] = -maxd
        elif v == K:          # gap before the final full stop: the shallowest boundary
            sc[t] = 1.0
        else:
            sc[t] = -dep.get((u, v), maxd - 1)
    return sc + sigma * rng.standard_normal(n - 1)


# ----------------------------------------------------------------------------
# Per-sentence hit records for a system
# ----------------------------------------------------------------------------

def hits_record(pool: list[dict], selector) -> dict:
    h = {x: np.zeros(len(pool)) for x in ("T", "A", "B", "C")}
    for i, p in enumerate(pool):
        if p["k"] <= 0:
            continue
        sa, sb = selector(p)
        for x in h:
            h[x][i] = est.matching_size_masks(p["adj"][x], sa, sb)
    return h


def pool_arrays(pool: list[dict]) -> dict:
    k = np.array([p["k"] for p in pool], dtype=float)
    return {"k": k, "ceilT": np.minimum(k, np.array([p["nu"]["T"] for p in pool], dtype=float)),
            "fT": np.array([p["floor"]["T"] for p in pool]), "fA": np.array([p["floor"]["A"] for p in pool]),
            "fB": np.array([p["floor"]["B"] for p in pool]), "fC": np.array([p["floor"]["C"] for p in pool]),
            "ag_num": np.array([p["agree"][0] for p in pool], dtype=float),
            "ag_den": np.array([p["agree"][1] for p in pool], dtype=float)}


def s_values(arr: dict, h: dict, idx=None) -> dict:
    return {"T": est.s_pooled(h["T"], arr["fT"], arr["ceilT"], idx),
            "A": est.s_pooled(h["A"], arr["fA"], arr["k"], idx),
            "B": est.s_pooled(h["B"], arr["fB"], arr["k"], idx),
            "C": est.s_pooled(h["C"], arr["fC"], arr["k"], idx)}


# ----------------------------------------------------------------------------
# Part: attenuation map
# ----------------------------------------------------------------------------

def atten_part(seed: int, calib: dict, n: int, cells: list[tuple]) -> dict:
    """Attenuation alpha = S of the truth oracle under each target (A, B, consensus C), per cell."""
    rows = []
    for prof, split, c, aa, ab in cells:
        pool = make_pool(seed, prof, n, (aa, ab), c, calib, split, floor_draws=32)
        arr = pool_arrays(pool)
        rng = np.random.default_rng(seed + 7)
        h_or = hits_record(pool, lambda p: oracle_selection(p, "T", rng))
        s_or = s_values(arr, h_or)
        meas = np.array([aer(p["links"]["A"], p["links"]["T"]) for p in pool])
        measB = np.array([aer(p["links"]["B"], p["links"]["T"]) for p in pool])
        measC = np.array([aer(p["links"]["C"], p["links"]["T"]) for p in pool])
        rows.append({"profile": prof, "split": split, "c": c, "aer_target_A": aa, "aer_target_B": ab,
                     "aer_measured_A": round(float(meas[:, 0].mean()), 4), "aer_measured_B": round(float(measB[:, 0].mean()), 4),
                     "consensus_precision": round(float(measC[:, 1].mean()), 4), "consensus_recall": round(float(measC[:, 2].mean()), 4),
                     "alpha_A": round(float(s_or["A"]), 4), "alpha_B": round(float(s_or["B"]), 4),
                     "alpha_C": round(float(s_or["C"]), 4),
                     "S_truth_oracle": round(float(s_or["T"]), 4),
                     "pair_agreement_dice": round(float(arr["ag_num"].sum() / arr["ag_den"].sum()), 4),
                     "mean_k": round(float(arr["k"].mean()), 3),
                     "share_k0": round(float((arr["k"] == 0).mean()), 4),
                     "floor_share_C": round(float(arr["fC"].sum() / arr["k"].sum()), 4)})
        print(f"atten {prof} {split} c={c} aer={aa},{ab} alphaA={rows[-1]['alpha_A']} alphaC={rows[-1]['alpha_C']} agree={rows[-1]['pair_agreement_dice']}", flush=True)
    return {"seed": seed, "pairs": n, "floor_draws": 32, "rows": rows}


def pair_agreement(pool: list[dict]) -> float:
    inter = tot = 0
    for p in pool:
        a, b = p["M"]["A"], p["M"]["B"]
        inter += int((a & b).sum())
        tot += int(a.sum() + b.sum())
    return 2 * inter / max(tot, 1)


# ----------------------------------------------------------------------------
# Part: identification (wave 1's density / word-end scenario)
# ----------------------------------------------------------------------------

def ident_part(seed: int, calib: dict, n: int) -> dict:
    """Score-based systems at the stage-1-like operating point, v2 estimator (word gaps, top-k).

    A 'perfect Chinese placement' system marks every Chinese gap of a true allowed
    pair plus extra Chinese word gaps up to density d (binary scores, 1 = boundary);
    the English side marks every word gap except a fraction m (word-end misses).
    Under v2 the selection is top-k of these scores among word gaps, so a binary
    near-saturated side carries little placement information and S does not depend
    on m beyond the gaps it removes. Also: a pure word-end detector (all word gaps
    equal), and graded scores where cut gaps outrank other word gaps.
    """
    pool = make_pool(seed, "zh", n, (0.085, 0.085), 0.5, calib)
    arr = pool_arrays(pool)
    rows = []
    for d in (0.54, 0.85, 0.92, 0.99):
        for m in (0.0, 0.03, 0.10):
            rng = np.random.default_rng(seed + int(100 * d) + int(1000 * m))

            def sel(p, graded=False):
                M = p["M"]["T"]
                na, nb = M.shape
                cut_b = M.any(0)
                sb = cut_b.astype(float)
                extra = np.flatnonzero(~cut_b)
                n_target = int(round(d * nb)) - int(cut_b.sum())
                if n_target > 0 and len(extra):
                    sb[rng.choice(extra, size=min(n_target, len(extra)), replace=False)] = 1.0
                sa = (rng.random(na) >= m).astype(float)
                if graded:
                    sa = sa + 0.5 * M.any(1)
                    sb = sb + 0.5 * cut_b
                k = p["k"]
                return est.select_topk(sa, k, rng), est.select_topk(sb, k, rng)

            hb = hits_record(pool, lambda p: sel(p, False))
            hg = hits_record(pool, lambda p: sel(p, True))
            rows.append({"zh_density": d, "en_word_end_miss": m,
                         "S_binary_truth": round(float(s_values(arr, hb)["T"]), 4),
                         "S_binary_A": round(float(s_values(arr, hb)["A"]), 4),
                         "S_graded_truth": round(float(s_values(arr, hg)["T"]), 4),
                         "S_graded_A": round(float(s_values(arr, hg)["A"]), 4)})
    rng = np.random.default_rng(seed + 5)
    hw = hits_record(pool, lambda p: (est.select_topk(np.ones(p["M"]["T"].shape[0]), p["k"], rng),
                                      est.select_topk(np.ones(p["M"]["T"].shape[1]), p["k"], rng)))
    return {"seed": seed, "pairs": n, "aligner_aer": 0.085, "c": 0.5, "rows": rows,
            "word_end_detector_only": {k: round(float(v), 4) for k, v in s_values(arr, hw).items()},
            "max_word_gap_density_selected": round(float(max(p["k"] / min(p["M"]["T"].shape) for p in pool if p["k"])), 4),
            "mean_one_minus_floor_A": round(float(1 - arr["fA"].sum() / arr["k"].sum()), 4)}


# ----------------------------------------------------------------------------
# Part: gates
# ----------------------------------------------------------------------------

def load_wave1():
    spec = importlib.util.spec_from_file_location("s1_wave1", HERE.parent / "instrument_sim.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["s1_wave1"] = mod
    spec.loader.exec_module(mod)
    return mod


def gates_part(seed: int, calib: dict, n: int) -> dict:
    out = {"seed": seed, "pairs": n}
    pool = make_pool(seed, "zh", n, (0.085, 0.085), 0.5, calib)
    for p in pool:  # monotone targets for the comparison row
        p["Mmono"] = {x: est.monotone_pairs(p["n_a"], p["n_b"], p["links"][x]) for x in ("T", "A")}
    arr = pool_arrays(pool)
    rng = np.random.default_rng(seed + 11)
    # I2: random selections at the same budget
    out["I2_random_S"] = {k: round(float(v), 4) for k, v in s_values(arr, hits_record(pool, lambda p: random_selection(p, rng))).items()}
    # I1: transplant control. Each sentence's consensus-oracle selection scored against a donor's consensus pairs
    by_shape: dict[tuple[int, int], list[int]] = {}
    for i, p in enumerate(pool):
        by_shape.setdefault(p["M"]["C"].shape, []).append(i)
    own, trans, fl_t, fl_o, kk, matched = [], [], [], [], [], 0
    for i, p in enumerate(pool):
        if p["k"] <= 0:
            continue
        cands = [j for j in by_shape[p["M"]["C"].shape] if j != i and pool[j]["k"] > 0]
        if not cands:
            continue
        matched += 1
        j = int(rng.choice(cands))
        sa, sb = oracle_selection(p, "C", rng)
        own.append(est.matching_size_masks(p["adj"]["C"], sa, sb))
        trans.append(est.matching_size_masks(pool[j]["adj"]["C"], sa, sb))
        fl_t.append(est.floor_hits(pool[j]["M"]["C"], p["k"], rng, 32, adj=pool[j]["adj"]["C"]))
        fl_o.append(p["floor"]["C"])
        kk.append(p["k"])
    own, trans, fl_t, fl_o, kk = map(np.array, (own, trans, fl_t, fl_o, kk))
    out["I1_transplant"] = {"sentences_with_same_shape_donor": matched,
                            "S_oracle_against_own": round(float(est.s_pooled(own, fl_o, kk)), 4),
                            "S_oracle_against_donor": round(float(est.s_pooled(trans, fl_t, kk)), 4)}
    # budget and density diagnostics
    k = arr["k"]
    na = np.array([p["M"]["T"].shape[0] for p in pool])
    nb = np.array([p["M"]["T"].shape[1] for p in pool])
    out["budget"] = {"mean_k": round(float(k.mean()), 3), "share_k0": round(float((k == 0).mean()), 4),
                     "mean_word_gaps_en": round(float(na.mean()), 2), "mean_word_gaps_x": round(float(nb.mean()), 2),
                     "max_density_selected": round(float(max(k[i] / min(na[i], nb[i]) for i in range(len(k)) if k[i] > 0)), 4),
                     "mean_nu_T": round(float(np.mean([p["nu"]["T"] for p in pool])), 3),
                     "mean_nu_C": round(float(np.mean([p["nu"]["C"] for p in pool])), 3),
                     "pooled_one_minus_floor_C": round(float(1 - arr["fC"].sum() / k.sum()), 4),
                     "mean_nu_T_monotone": round(float(np.mean([est.nu(p["Mmono"]["T"]) for p in pool])), 3),
                     "share_pairs_inverted_or_nested": round(float(1 - sum(p["Mmono"]["T"].sum() for p in pool) / max(sum(p["M"]["T"].sum() for p in pool), 1)), 4),
                     "pooled_one_minus_floor_A": round(float(1 - arr["fA"].sum() / k.sum()), 4)}
    # what the monotone target does to a system that marks inverted splits correctly
    hm = {x: np.zeros(len(pool)) for x in ("T",)}
    for i, p in enumerate(pool):
        if p["k"] <= 0:
            continue
        sa, sb = oracle_selection(p, "T", rng)
        hm["T"][i] = est.matching_size(p["Mmono"]["T"], sa, sb)
    fl_mono = np.array([est.floor_hits(p["Mmono"]["T"], p["k"], rng, 16) if p["k"] > 0 else 0.0 for p in pool])
    out["truth_oracle_scored_on_monotone_target"] = round(float(est.s_pooled(hm["T"], fl_mono, arr["ceilT"])), 4)
    # I3 convention invariance through the byte layout (wave 1's canonicalization, unchanged)
    w1 = load_wave1()
    ident = diff = 0
    for p in pool[:300]:
        side = w1.Side([(w, frozenset([u]) if u >= 0 else frozenset(), sp) for (w, u, sp) in p["xb"]])
        # word gap t of side b <-> canonical gap after the last char of word t
        last_char = [int(np.flatnonzero(side.char_tok == t)[-1]) for t in range(side.n_tok - 1)]
        scores_c = rng.random(side.n_gap)  # a score on every canonical gap
        wg = scores_c[last_char]
        for conv in ("end", "start"):
            back = np.full(side.n_gap, -1.0)
            for kk_ in range(side.n_gap):
                kk2 = side.canon_from_raw(side.raw_from_canon(kk_, conv))
                if kk2 >= 0:
                    back[kk2] = scores_c[kk_]
            wg2 = back[last_char]
            if np.array_equal(wg, wg2):
                ident += 1
            else:
                diff += 1
    out["I3_convention"] = {"word_gap_score_vectors_identical": ident, "differ": diff}
    return out


# ----------------------------------------------------------------------------
# Part: decision operating characteristics
# ----------------------------------------------------------------------------

F_GRID = (0.0, 0.03, 0.06, 0.10, 0.15, 0.25, 0.40, 0.70)


def oc_part(seed: int, calib: dict, prof: str, aer_ab: tuple[float, float], c: float, split: str,
            pool_n: int, n_eval: int, reps: int, n_boot: int, gold_n: int, gold_pool_n: int,
            gold_shifts: tuple[float, ...], band: dict, floor_draws: int = est.FLOOR_DRAWS) -> dict:
    """Operating characteristics of the registered v2 rule on the consensus target.

    Population: a pool of pool_n synthetic pairs; each replicate draws n_eval pairs WITH
    replacement from it (the pool is the population) and a bootstrap of n_boot inside.
    Gold path: a gold pool per AER shift (longer sentences, aligner AER shifted by the
    given amount), from which each replicate draws gold_n pairs with replacement; alpha_C
    is the truth oracle's S on them. Systems: truth-oracle selections with a fraction f of
    each side's selected gaps displaced to random (random_f) or adjacent (near_f) word
    gaps. Line M scenarios: M_high (a reference already on true pairs, f = 0) and M_low
    (the synthetic syntactic ranker, rotations 0.35, parse noise 1.0).
    """
    t0 = time.time()
    pool = make_pool(seed, prof, pool_n, aer_ab, c, calib, split, floor_draws=floor_draws)
    golds = {}
    for g in gold_shifts:
        ga = (round(min(max(aer_ab[0] + g, 0.05), 0.25), 3), round(min(max(aer_ab[1] + g, 0.05), 0.25), 3))
        golds[g] = make_pool(seed + 500 + int(1000 * (g + 0.5)), prof, gold_pool_n, ga, c, calib, split, K_mean=10.0,
                             floor_draws=floor_draws)
    arr = pool_arrays(pool)
    rng = np.random.default_rng(seed + 13)
    systems = {}
    for mode in ("random", "near"):
        for f in F_GRID:
            systems[f"{mode}_{f}"] = hits_record(pool, lambda p: (
                lambda sel: (displace(sel[0], p["M"]["T"].shape[0], f, mode, rng),
                             displace(sel[1], p["M"]["T"].shape[1], f, mode, rng)))(oracle_selection(p, "T", rng)))
    mono = {"M_high": systems["random_0.0"],
            "M_low": hits_record(pool, lambda p: (est.select_topk(syntax_scores(p, "a", rng, 0.35, 1.0), p["k"], rng),
                                                  est.select_topk(syntax_scores(p, "b", rng, 0.35, 1.0), p["k"], rng)))}
    garr = {g: pool_arrays(gp) for g, gp in golds.items()}
    len_pool = np.array([min(p["n_a"], p["n_b"]) for p in pool])
    gw = {g: est.poststrat_weights(np.array([min(p["n_a"], p["n_b"]) for p in gp]), len_pool) for g, gp in golds.items()}
    g_or = {g: hits_record(gp, lambda p: oracle_selection(p, "T", rng)) for g, gp in golds.items()}
    s_true = {name: float(s_values(arr, h)["T"]) for name, h in systems.items()}
    s_true_mono = {q: float(s_values(arr, h)["T"]) for q, h in mono.items()}
    paths = ["band"] + [f"gold{g:+.2f}" for g in gold_shifts]
    counts = {name: {path: {} for path in paths} for name in systems}
    pts = {name: {"C": [], "A": [], "B": [], "lo": [], **{f"star{g:+.2f}": [] for g in gold_shifts}} for name in systems}
    mono_counts = {q: {path: {} for path in paths} for q in mono}
    agree_vals, band_ok_count = [], 0
    raw = {"agreement": [], "systems": {name: {path: [] for path in ["C"] + [f"gold{g:+.2f}" for g in gold_shifts]} for name in list(systems) + list(mono)}}
    for r in range(reps):
        idx = rng.integers(0, len(pool), size=n_eval)
        boot = idx[rng.integers(0, n_eval, size=(n_boot, n_eval))]
        agree = float(arr["ag_num"][idx].sum() / arr["ag_den"][idx].sum())
        agree_vals.append(agree)
        ok_band = est.band_valid(agree, band["agree_min"], band["agree_max"])
        band_ok_count += ok_band
        al, alb = {}, {}
        for g in gold_shifts:
            gidx = rng.integers(0, len(golds[g]), size=gold_n)
            gboot = gidx[rng.integers(0, gold_n, size=(n_boot, gold_n))]
            al[g] = float(est.s_pooled(g_or[g]["C"], garr[g]["fC"], garr[g]["k"], gidx, w=gw[g]))
            alb[g] = est.s_pooled(g_or[g]["C"], garr[g]["fC"], garr[g]["k"], gboot, w=gw[g])

        raw["agreement"].append(round(agree, 5))

        def verdicts(h, name):
            pt = float(est.s_pooled(h["C"], arr["fC"], arr["k"], idx))
            bs = est.s_pooled(h["C"], arr["fC"], arr["k"], boot)
            lo, hi = est.percentile_ci(bs)
            raw["systems"][name]["C"].append([round(pt, 5), round(lo, 5), round(hi, 5)])
            v = {"band": est.decide_band(pt, lo, hi, band["alpha_min"], band["alpha_max"]) if ok_band else "INV"}
            out = {"C": pt, "lo": lo}
            for g in gold_shifts:
                st = pt / al[g]
                lo2, hi2 = est.percentile_ci(bs / alb[g])
                raw["systems"][name][f"gold{g:+.2f}"].append([round(st, 5), round(lo2, 5), round(hi2, 5)])
                v[f"gold{g:+.2f}"] = est.decide_one(st, lo2, hi2, 1.0)
                out[f"star{g:+.2f}"] = st
            return v, out

        vm = {}
        for q, hm in mono.items():
            vm[q], _ = verdicts(hm, q)
            for path in paths:
                mono_counts[q][path][vm[q][path]] = mono_counts[q][path].get(vm[q][path], 0) + 1
        for name, h in systems.items():
            vp, op = verdicts(h, name)
            pts[name]["C"].append(op["C"])
            pts[name]["lo"].append(op["lo"])
            for g in gold_shifts:
                pts[name][f"star{g:+.2f}"].append(op[f"star{g:+.2f}"])
            if r < 20:
                pts[name]["A"].append(float(est.s_pooled(h["A"], arr["fA"], arr["k"], idx)))
                pts[name]["B"].append(float(est.s_pooled(h["B"], arr["fB"], arr["k"], idx)))
            for path in paths:
                c_ = counts[name][path]
                c_.setdefault("primary", {})
                c_["primary"][vp[path]] = c_["primary"].get(vp[path], 0) + 1
                for q in mono:
                    if vp[path] == "INV" or vm[q][path] == "INV":
                        fv = "INSTRUMENT_INVALID"
                    else:
                        fv = est.final_verdict(vp[path], vm[q][path])
                    c_.setdefault(q, {})
                    c_[q][fv] = c_[q].get(fv, 0) + 1
    rows = []
    for name in systems:
        row = {"system": name, "S_true": round(s_true[name], 4),
               "S_C_mean": round(float(np.mean(pts[name]["C"])), 4), "S_C_sd": round(float(np.std(pts[name]["C"])), 4),
               "S_A_mean": round(float(np.mean(pts[name]["A"])), 4), "S_B_mean": round(float(np.mean(pts[name]["B"])), 4),
               "verdicts": {path: {k: {kk: round(vv / reps, 4) for kk, vv in d.items()}
                                   for k, d in counts[name][path].items()} for path in paths}}
        for g in gold_shifts:
            v = pts[name][f"star{g:+.2f}"]
            row[f"S_star_mean_gold{g:+.2f}"] = round(float(np.mean(v)), 4)
            row[f"S_star_sd_gold{g:+.2f}"] = round(float(np.std(v)), 4)
        rows.append(row)
    h_or = systems["random_0.0"]
    res = {"seed": seed, "profile": prof, "aer_A_B": list(aer_ab), "c": c, "split": split, "pool": pool_n, "floor_draws": floor_draws,
           "n_eval": n_eval, "replicates": reps, "bootstrap": n_boot, "gold_n": gold_n, "gold_pool": gold_pool_n,
           "gold_aer_shifts": list(gold_shifts), "band": band,
           "pair_agreement_mean": round(float(np.mean(agree_vals)), 4),
           "share_replicates_band_valid": round(band_ok_count / reps, 4),
           "alpha_pool": {x: round(float(v), 4) for x, v in s_values(arr, h_or).items()},
           "alpha_gold_pop": {f"{g:+.2f}": round(float(est.s_pooled(g_or[g]["C"], garr[g]["fC"], garr[g]["k"])), 4) for g in gold_shifts},
           "alpha_gold_pop_poststratified": {f"{g:+.2f}": round(float(est.s_pooled(g_or[g]["C"], garr[g]["fC"], garr[g]["k"], w=gw[g])), 4) for g in gold_shifts},
           "S_true_mono": {q: round(v, 4) for q, v in s_true_mono.items()},
           "mono_verdicts": {q: {path: {k: round(v / reps, 4) for k, v in d.items()} for path, d in pc.items()}
                             for q, pc in mono_counts.items()},
           "mean_k": round(float(arr["k"].mean()), 3), "share_k0": round(float((arr["k"] == 0).mean()), 4),
           "S_true_all": {**{k: round(v, 4) for k, v in s_true.items()}, **{k: round(v, 4) for k, v in s_true_mono.items()}},
           "rows": rows, "raw_replicates": raw, "elapsed_s": round(time.time() - t0, 1)}
    return res


# ----------------------------------------------------------------------------
# Part: line M (monolingual syntactic reference)
# ----------------------------------------------------------------------------

def linem_part(seed: int, calib: dict, n: int) -> dict:
    pool = make_pool(seed, "zh", n, (0.085, 0.085), 0.5, calib)
    arr = pool_arrays(pool)
    rows = []
    for q in (0.0, 0.1, 0.2, 0.35, 0.5):
        for sigma in (0.0, 0.3, 1.0):
            rng = np.random.default_rng(seed + int(100 * q) + int(10 * sigma))
            h = hits_record(pool, lambda p: (est.select_topk(syntax_scores(p, "a", rng, q, sigma), p["k"], rng),
                                             est.select_topk(syntax_scores(p, "b", rng, q, sigma), p["k"], rng)))
            v = s_values(arr, h)
            rows.append({"rotation_q": q, "parse_noise_sigma": sigma, **{f"S_{k}": round(float(x), 4) for k, x in v.items()}})
    return {"seed": seed, "pairs": n, "rows": rows}


# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--part", required=True, choices=["calib", "atten", "ident", "gates", "oc", "linem"])
    ap.add_argument("--seeds", type=int, nargs="+", default=[42])
    ap.add_argument("--calib", type=Path, default=HERE / "calib.json")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--profile", default="zh")
    ap.add_argument("--aer", type=float, nargs=2, default=[0.085, 0.05])
    ap.add_argument("--c", type=float, default=0.0)
    ap.add_argument("--split", default="balanced")
    ap.add_argument("--gold-shifts", type=float, nargs="+", default=[0.0])
    ap.add_argument("--gold-pool", type=int, default=600)
    ap.add_argument("--band", type=Path, default=HERE / "band.json")
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--pool", type=int, default=4000)
    ap.add_argument("--cells", nargs="+", default=[])
    ap.add_argument("--floor-draws", type=int, default=est.FLOOR_DRAWS)
    args = ap.parse_args()
    t0 = time.time()
    res: dict = {"script": "instrument_sim_v2.py", "estimator": "e3_estimator_v2.py", "argv": sys.argv[1:],
                 "estimator_constants": {"RHO": est.RHO, "FLOOR_DRAWS": est.FLOOR_DRAWS, "NH_POINT": est.NH_POINT,
                                         "NH_LOWER": est.NH_LOWER, "H_UPPER": est.H_UPPER}}
    if args.part == "calib":
        res["calib"] = calib_part(args.seeds[0], 120 if args.quick else 300, args.cells or None)
    else:
        calib = json.loads(args.calib.read_text())["calib"]
        if args.part == "atten":
            cells = [tuple(x.split(":")) for x in args.cells]
            cells = [(a, b, float(c), float(d), float(e)) for a, b, c, d, e in cells]
            res["atten"] = [atten_part(s, calib, args.pool, cells) for s in args.seeds]
        elif args.part == "ident":
            res["ident"] = [ident_part(s, calib, args.pool) for s in args.seeds]
        elif args.part == "gates":
            res["gates"] = [gates_part(s, calib, args.pool) for s in args.seeds]
        elif args.part == "linem":
            res["linem"] = [linem_part(s, calib, args.pool) for s in args.seeds]
        elif args.part == "oc":
            band = json.loads(args.band.read_text())
            res["oc"] = [oc_part(s, calib, args.profile, tuple(args.aer), args.c, args.split,
                                 args.pool, 1012, args.reps, args.boot, 300, args.gold_pool,
                                 tuple(args.gold_shifts), band, args.floor_draws) for s in args.seeds]
    res["elapsed_seconds"] = round(time.time() - t0, 1)
    args.out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
