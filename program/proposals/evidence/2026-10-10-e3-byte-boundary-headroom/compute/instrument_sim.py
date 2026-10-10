#!/usr/bin/env python3
"""S1: instrument gates and decision-rule operating characteristics for the E3 Stage-0 probe.

CPU only, seeded (42, 43, 44); no FLORES text, no model, no aligner. Synthetic,
language-free parallel pairs whose byte structure mimics an English side against
a ZH-like (3-byte characters, no spaces, character aligner tokens), KO-like
(3-byte syllables, spaced eojeol, fused particles, more reordering) or PL-like
(spaced words, some 2-byte characters) side. Every sentence is a sequence of
aligned "units"; units are the generative ground truth of correspondence.

Three instruments are compared on the same synthetic boundaries:

* UOT  - the dossier's instrument: the legacy NumPy debiased unbalanced
         Sinkhorn evaluator (legacy/harness/translation_boundaries.py) on raw
         byte gaps, with word-level span links from the aligner (whitespace
         excluded, fractions 1/degree for one-to-many links).
* PBD  - projected boundary Dice (this proposal's primary): boundaries are
         snapped to canonical character gaps (whitespace runs collapsed,
         in-character boundaries snapped to the character's start), the
         aligner's links define consistent cuts (token gaps that split the
         link graph without crossing), and PBD = 2 * (cuts hit on both sides)
         / (boundaries on side a + boundaries on side b).
* A11  - token-alignability-style share of one-to-one chunk alignments
         (Hammerl et al., arXiv 2502.06468, Sec. 3.2), with the aligner's word
         links projected onto each system's chunks.

Each instrument is normalized as S = (M_sys - M_floor) / (M_ceil - M_floor)
(sign flipped for the UOT loss), with a rate- and spacing-preserving floor
(side b's boundaries circularly shifted within the sentence) and a ceiling at
the system's own per-sentence boundary budget n = round((n_a + n_b) / 2).
Two ceilings bracket the unobservable true ceiling under aligner noise:
"self" (aligner A's own cuts scored under A; circular, an upper bound) and
"xfit" (aligner B's cuts scored under A; a lower bound).

Usage: instrument_sim.py <out.json> [--quick] [--skip-uot]
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

ROOT = Path(__file__).resolve().parents[5]
SEEDS = (42, 43, 44)

PROFILES = {
    "zh": {"space": False, "swap": 0.15, "x_null": 0.05, "fuse": 0.0, "pl2": 0.0},
    "ko": {"space": True, "swap": 0.30, "x_null": 0.03, "fuse": 0.30, "pl2": 0.0},
    "pl": {"space": True, "swap": 0.10, "x_null": 0.05, "fuse": 0.0, "pl2": 0.15},
}
ALIGNER_NOISE = {"low": (0.05, 0.03), "base": (0.10, 0.06), "high": (0.20, 0.12)}


# ----------------------------------------------------------------------------
# Synthetic pairs
# ----------------------------------------------------------------------------

class Side:
    """One side of a pair: tokens, characters, canonical gaps, byte layout."""

    def __init__(self, tokens: list[tuple[list[int], frozenset, bool]]):
        # token = (char byte widths, unit set, space_before)
        self.units = [t[1] for t in tokens]
        self.n_tok = len(tokens)
        char_bytes, char_tok, char_start = [], [], []
        byte_char, byte_last, byte_space = [], [], []
        pos = 0
        for t_idx, (widths, _units, space_before) in enumerate(tokens):
            if space_before and t_idx > 0:
                byte_char.append(-1)
                byte_last.append(True)
                byte_space.append(True)
                pos += 1
            for w in widths:
                c = len(char_bytes)
                char_bytes.append(w)
                char_tok.append(t_idx)
                char_start.append(pos)
                for b in range(w):
                    byte_char.append(c)
                    byte_last.append(b == w - 1)
                    byte_space.append(False)
                pos += w
        self.byte_len = pos
        self.char_bytes = np.array(char_bytes)
        self.char_tok = np.array(char_tok)
        self.char_start = np.array(char_start)
        self.byte_char = np.array(byte_char)
        self.byte_last = np.array(byte_last)
        self.byte_space = np.array(byte_space)
        self.n_char = len(char_bytes)
        self.n_gap = self.n_char - 1  # canonical gaps between consecutive non-space chars
        # canonical gap k -> token gap index (gap after token t) or -1 if internal
        tg = np.full(self.n_gap, -1)
        for k in range(self.n_gap):
            if self.char_tok[k] != self.char_tok[k + 1]:
                tg[k] = self.char_tok[k]
        self.gap_token = tg
        self.tok_last_gap = np.full(self.n_tok, -1)
        for k in range(self.n_gap):
            if tg[k] >= 0:
                self.tok_last_gap[tg[k]] = k
        # token byte spans (whitespace excluded) for the UOT links
        self.tok_span = []
        for t in range(self.n_tok):
            cs = np.where(self.char_tok == t)[0]
            s = int(self.char_start[cs[0]])
            e = int(self.char_start[cs[-1]] + self.char_bytes[cs[-1]])
            self.tok_span.append((s, e))

    # raw byte gap g (between byte g and g+1) -> canonical gap (or -1)
    def canon_from_raw(self, g: int) -> int:
        if self.byte_space[g]:
            # last non-space char before byte g
            j = g - 1
            while j >= 0 and self.byte_space[j]:
                j -= 1
            if j < 0:
                return -1
            k = int(self.byte_char[j])
            return k if k < self.n_gap else -1
        c = int(self.byte_char[g])
        if self.byte_last[g]:
            return c if c < self.n_gap else -1
        return c - 1 if c - 1 >= 0 else -1  # in-character boundary snaps to the char's start gap

    def raw_from_canon(self, k: int, convention: str) -> int:
        if convention == "end":  # boundary after the last byte of char k (Bolmo/BPE patch-end style)
            return int(self.char_start[k] + self.char_bytes[k] - 1)
        return int(self.char_start[k + 1] - 1)  # "start": gap before char k+1 (H-Net chunk-start style)


def gen_pair(rng: np.random.Generator, prof: dict) -> tuple[Side, Side, set[tuple[int, int]], dict]:
    K = 6 + int(rng.poisson(8))
    en_tokens: list[tuple[list[int], frozenset, bool]] = []
    for u in range(K):
        if rng.random() < 0.25:
            en_tokens.append(([1] * (1 + int(rng.poisson(1.5))), frozenset(), True))
        nw = int(rng.choice([1, 2, 3], p=[0.65, 0.27, 0.08]))
        for _ in range(nw):
            en_tokens.append(([1] * (2 + int(rng.poisson(3.6))), frozenset([u]), True))
    order = list(range(K))
    i = 0
    while i < K - 1:
        if rng.random() < prof["swap"]:
            order[i], order[i + 1] = order[i + 1], order[i]
            i += 2
        else:
            i += 1
    x_tokens: list[tuple[list[int], frozenset, bool]] = []
    zh_word_gap: list[bool] = []  # ZH monolingual word gaps after each char token
    idx = 0
    while idx < K:
        u = order[idx]
        if rng.random() < prof["x_null"]:
            if prof["space"]:
                x_tokens.append(([3 if prof is PROFILES["ko"] else 1] * (1 + int(rng.poisson(1.0))), frozenset(), True))
            else:
                x_tokens.append(([3], frozenset(), False))
                zh_word_gap.append(True)
        if not prof["space"]:  # ZH-like: one token per 3-byte character
            n = 1 + int(rng.poisson(1.0))
            for c in range(n):
                x_tokens.append(([3], frozenset([u]), False))
                zh_word_gap.append(c == n - 1 or rng.random() < 0.3)
            idx += 1
        elif prof is PROFILES["ko"]:
            units = {u}
            n = 1 + int(rng.poisson(1.6))
            if idx + 1 < K and rng.random() < prof["fuse"]:
                units.add(order[idx + 1])
                n += 1 + int(rng.poisson(0.5))
                idx += 1
            x_tokens.append(([3] * n, frozenset(units), True))
            idx += 1
        else:  # PL-like
            nw = 2 if rng.random() < prof["pl2"] else 1
            for _ in range(nw):
                n = 2 + int(rng.poisson(4.5))
                widths = [2 if rng.random() < 0.08 else 1 for _ in range(n)]
                x_tokens.append((widths, frozenset([u]), True))
            idx += 1
    a, b = Side(en_tokens), Side(x_tokens)
    true_links = {(i, j) for i in range(a.n_tok) for j in range(b.n_tok) if a.units[i] & b.units[j]}
    # monolingual word gaps per side (canonical-gap booleans)
    word_a = a.gap_token >= 0
    if prof["space"]:
        word_b = b.gap_token >= 0
    else:
        word_b = np.zeros(b.n_gap, dtype=bool)
        for k in range(b.n_gap):
            t = b.char_tok[k]
            if b.char_tok[k + 1] != t:
                word_b[k] = zh_word_gap[t] or (b.units[t] != b.units[b.char_tok[k + 1]])
    return a, b, true_links, {"word_a": word_a, "word_b": word_b, "K": K}


def noisy_links(rng, a: Side, b: Side, true_links, drop: float, spur: float) -> set[tuple[int, int]]:
    links = {lk for lk in true_links if rng.random() >= drop}
    # neighbour confusions and links for unaligned (null) tokens
    for i in range(a.n_tok):
        if rng.random() < spur:
            js = [j for (ii, j) in true_links if ii == i]
            centre = js[0] if js else int(round(i * (b.n_tok - 1) / max(a.n_tok - 1, 1)))
            j = int(np.clip(centre + rng.integers(-2, 3), 0, b.n_tok - 1))
            links.add((i, j))
    if not links:
        links = set(true_links)
    return links


def cuts_from_links(a: Side, b: Side, links) -> list[tuple[np.ndarray, np.ndarray]]:
    """Consistent cuts as (canonical gaps on side a, canonical gaps on side b)."""
    na, nb = a.n_tok, b.n_tok
    maxj = np.full(na, -1)
    minj = np.full(na, nb)
    for i, j in links:
        maxj[i] = max(maxj[i], j)
        minj[i] = min(minj[i], j)
    linked = maxj >= 0
    pre_max = np.maximum.accumulate(np.where(linked, maxj, -1))
    pre_any = np.logical_or.accumulate(linked)
    suf_min = np.minimum.accumulate(np.where(linked, minj, nb)[::-1])[::-1]
    suf_any = np.logical_or.accumulate(linked[::-1])[::-1]
    groups: dict[tuple[int, int], list[int]] = {}
    for i in range(na - 1):
        if pre_any[i] and suf_any[i + 1] and pre_max[i] < suf_min[i + 1]:
            groups.setdefault((int(pre_max[i]), int(suf_min[i + 1]) - 1), []).append(i)
    cuts = []
    for (j0, j1), is_ in groups.items():
        ga = a.tok_last_gap[np.array(is_)]
        gb = b.tok_last_gap[np.arange(j0, j1 + 1)]
        ga, gb = ga[ga >= 0], gb[gb >= 0]
        if len(ga) and len(gb):
            cuts.append((ga, gb))
    return cuts


# ----------------------------------------------------------------------------
# Instruments
# ----------------------------------------------------------------------------

def pbd_tp(cuts, ba: np.ndarray, bb: np.ndarray) -> int:
    return sum(1 for ga, gb in cuts if ba[ga].any() and bb[gb].any())


def chunk_ids(n_char: int, bnd: np.ndarray) -> np.ndarray:
    ids = np.zeros(n_char, dtype=int)
    ids[1:] = np.cumsum(bnd)
    return ids


def a11(a: Side, b: Side, links, ba, bb) -> tuple[int, int]:
    """(one-to-one chunks summed over both directions, chunks on both sides)."""
    ca, cb = chunk_ids(a.n_char, ba), chunk_ids(b.n_char, bb)
    tok_ca = [set(ca[a.char_tok == t]) for t in range(a.n_tok)]
    tok_cb = [set(cb[b.char_tok == t]) for t in range(b.n_tok)]
    nca, ncb = int(ca[-1]) + 1, int(cb[-1]) + 1
    adj_a: list[set] = [set() for _ in range(nca)]
    adj_b: list[set] = [set() for _ in range(ncb)]
    for i, j in links:
        for x in tok_ca[i]:
            for y in tok_cb[j]:
                adj_a[x].add(y)
                adj_b[y].add(x)
    one_a = sum(1 for x in range(nca) if len(adj_a[x]) == 1 and adj_b[next(iter(adj_a[x]))] == {x})
    one_b = sum(1 for y in range(ncb) if len(adj_b[y]) == 1 and adj_a[next(iter(adj_b[y]))] == {y})
    return one_a + one_b, nca + ncb


def shift(arr: np.ndarray, k: int) -> np.ndarray:
    return np.roll(arr, k)


def oracle_boundaries(rng, a: Side, b: Side, cuts, n: int) -> tuple[np.ndarray, np.ndarray]:
    oa, ob = np.zeros(a.n_gap, bool), np.zeros(b.n_gap, bool)
    if not cuts or n <= 0:
        return oa, ob
    sel = rng.permutation(len(cuts))[: min(n, len(cuts))]
    for c in sel:
        oa[cuts[c][0].max()] = True
        ob[cuts[c][1].max()] = True
    for arr in (oa, ob):
        extra = n - int(arr.sum())
        free = np.where(~arr)[0]
        if extra > 0 and len(free):
            arr[rng.choice(free, size=min(extra, len(free)), replace=False)] = True
    return oa, ob


# ----------------------------------------------------------------------------
# Boundary systems
# ----------------------------------------------------------------------------

def true_cut_reps(a: Side, b: Side, cuts_true) -> tuple[np.ndarray, np.ndarray]:
    ra, rb = np.full(a.n_gap, -1), np.full(b.n_gap, -1)
    for c, (ga, gb) in enumerate(cuts_true):
        ra[ga.max()] = c
        rb[gb.max()] = c
    return ra, rb


def gaussian_scores(rng, a, b, extra, cuts_true, rho: float, mu: float, omega: float):
    """Latent boundary scores: word-gap bonus omega (monolingual structure), cut bonus mu,
    correlation rho of the two sides' cut scores (translation-shared selection)."""
    ra, rb = true_cut_reps(a, b, cuts_true)
    z = rng.standard_normal(len(cuts_true))
    sa = rng.standard_normal(a.n_gap) + omega * extra["word_a"]
    sb = rng.standard_normal(b.n_gap) + omega * extra["word_b"]
    for s, r in ((sa, ra), (sb, rb)):
        m = r >= 0
        s[m] = omega * 1.0 + mu + math.sqrt(rho) * z[r[m]] + math.sqrt(1 - rho) * rng.standard_normal(m.sum())
    return sa, sb


def displaced_oracle(rng, a, b, cuts_true, frac: float):
    """True-cut boundaries on both sides; on side b a fraction frac of them moved to random non-cut gaps."""
    ra, rb = true_cut_reps(a, b, cuts_true)
    oa, ob = ra >= 0, rb >= 0
    idx = np.where(ob)[0]
    k = int(rng.binomial(len(idx), frac))
    if k:
        move = rng.choice(idx, size=k, replace=False)
        free = np.where(~ob)[0]
        ob = ob.copy()
        ob[move] = False
        ob[rng.choice(free, size=min(k, len(free)), replace=False)] = True
    return oa, ob


# ----------------------------------------------------------------------------
# Corpus-level accumulation
# ----------------------------------------------------------------------------

def pbd_record(rng, pair, ba, bb, n_shift=20) -> dict:
    """Per-sentence counts for S under aligner A (self and xfit ceilings) and under the truth."""
    a, b, cuts = pair["a"], pair["b"], pair["cuts"]
    na, nb = int(ba.sum()), int(bb.sum())
    n = int(round((na + nb) / 2))
    rec = {"na": na, "nb": nb, "n2": 2 * n}
    for key in ("A", "B", "T"):
        rec[f"tp_{key}"] = pbd_tp(cuts[key], ba, bb)
        shifts = rng.integers(1, max(b.n_gap, 2), size=n_shift)
        rec[f"fl_{key}"] = float(np.mean([pbd_tp(cuts[key], ba, shift(bb, int(k))) for k in shifts]))
    # ceilings: self (A under A), xfit (B under A), mirror for B, truth (T under T)
    for name, src, dst in (("selfA", "A", "A"), ("xfitA", "B", "A"), ("selfB", "B", "B"),
                           ("xfitB", "A", "B"), ("T", "T", "T")):
        oa, ob = oracle_boundaries(rng, a, b, cuts[src], n)
        rec[f"ce_{name}"] = pbd_tp(cuts[dst], oa, ob)
    return rec


def s_from(records: list[dict], key: str, ceil: str, idx=None) -> float:
    r = records if idx is None else [records[i] for i in idx]
    den_sys = sum(x["na"] + x["nb"] for x in r)
    den_ce = sum(x["n2"] for x in r)
    f_sys = 2 * sum(x[f"tp_{key}"] for x in r) / den_sys
    f_fl = 2 * sum(x[f"fl_{key}"] for x in r) / den_sys
    f_ce = 2 * sum(x[f"ce_{ceil}"] for x in r) / den_ce
    return (f_sys - f_fl) / (f_ce - f_fl) if f_ce > f_fl else float("nan")


class Arrays:
    """Vectorized per-sentence counts for fast bootstraps."""

    def __init__(self, records: list[dict]):
        self.keys = list(records[0].keys())
        self.m = {k: np.array([r[k] for r in records], dtype=float) for k in self.keys}

    def S(self, key: str, ceil: str, idx: np.ndarray) -> np.ndarray:
        m = self.m
        den_sys = (m["na"] + m["nb"])[idx].sum(-1)
        den_ce = m["n2"][idx].sum(-1)
        f_sys = 2 * m[f"tp_{key}"][idx].sum(-1) / den_sys
        f_fl = 2 * m[f"fl_{key}"][idx].sum(-1) / den_sys
        f_ce = 2 * m[f"ce_{ceil}"][idx].sum(-1) / den_ce
        return (f_sys - f_fl) / (f_ce - f_fl)


# ----------------------------------------------------------------------------
# Pools
# ----------------------------------------------------------------------------

def make_pool(rng, lang: str, n: int, noise: str) -> list[dict]:
    prof = PROFILES[lang]
    d, s = ALIGNER_NOISE[noise]
    pool = []
    while len(pool) < n:
        a, b, true_links, extra = gen_pair(rng, prof)
        if a.n_gap < 4 or b.n_gap < 4:
            continue
        la = noisy_links(rng, a, b, true_links, d, s)
        lb = noisy_links(rng, a, b, true_links, d, s)
        cuts = {"T": cuts_from_links(a, b, true_links), "A": cuts_from_links(a, b, la),
                "B": cuts_from_links(a, b, lb)}
        if not cuts["T"] or not cuts["A"] or not cuts["B"]:
            continue
        pool.append({"a": a, "b": b, "links": {"T": true_links, "A": la, "B": lb}, "cuts": cuts,
                     "extra": extra})
    return pool


def cut_agreement(pool) -> float:
    """Inter-aligner agreement: Dice of the two aligners' cut sets (cuts as side-a representative gaps)."""
    inter = tot = 0
    for p in pool:
        sa = {int(ga.max()) for ga, _ in p["cuts"]["A"]}
        sb = {int(ga.max()) for ga, _ in p["cuts"]["B"]}
        inter += len(sa & sb)
        tot += len(sa) + len(sb)
    return 2 * inter / tot


# ----------------------------------------------------------------------------
# Part 1: PBD and A11 instrument gates
# ----------------------------------------------------------------------------

def system_boundaries(rng, p, name: str, param) -> tuple[np.ndarray, np.ndarray]:
    a, b, extra, cuts_true = p["a"], p["b"], p["extra"], p["cuts"]["T"]
    if name == "bern":
        return rng.random(a.n_gap) < param, rng.random(b.n_gap) < param
    if name == "word":
        return extra["word_a"].copy(), extra["word_b"].copy()
    if name == "char":
        return np.ones(a.n_gap, bool), np.ones(b.n_gap, bool)
    if name == "gauss":
        rho, mu, omega, ta, tb = param
        sa, sb = gaussian_scores(rng, a, b, extra, cuts_true, rho, mu, omega)
        return sa > ta, sb > tb
    if name == "displaced":
        return displaced_oracle(rng, a, b, cuts_true, param)
    if name == "displaced_plus_extra":
        frac, q = param
        oa, ob = displaced_oracle(rng, a, b, cuts_true, frac)
        return oa | (rng.random(a.n_gap) < q), ob | (rng.random(b.n_gap) < q)
    raise ValueError(name)


def permuted_cuts(rng, p) -> list:
    """Alignment-permuted control: side-b token indices relabelled at random before cutting."""
    a, b = p["a"], p["b"]
    perm = rng.permutation(b.n_tok)
    links = {(i, int(perm[j])) for i, j in p["links"]["A"]}
    return cuts_from_links(a, b, links)


def gate_rows(rng, pool, systems) -> list[dict]:
    rows = []
    for label, name, param in systems:
        recs, a11_sys, a11_fl, a11_ce, perm_tp, sizes = [], [0, 0], [0.0, 0], [0, 0], 0, [0, 0, 0]
        for p in pool:
            ba, bb = system_boundaries(rng, p, name, param)
            recs.append(pbd_record(rng, p, ba, bb, n_shift=8))
            pc = permuted_cuts(rng, p)
            perm_tp += pbd_tp(pc, ba, bb) if pc else 0
            o, t = a11(p["a"], p["b"], p["links"]["A"], ba, bb)
            a11_sys[0] += o
            a11_sys[1] += t
            ks = rng.integers(1, max(p["b"].n_gap, 2), size=4)
            fl = [a11(p["a"], p["b"], p["links"]["A"], ba, shift(bb, int(k))) for k in ks]
            a11_fl[0] += float(np.mean([f[0] for f in fl]))
            a11_fl[1] += float(np.mean([f[1] for f in fl]))
            n = int(round((ba.sum() + bb.sum()) / 2))
            oa, ob = oracle_boundaries(rng, p["a"], p["b"], p["cuts"]["B"], n)
            o, t = a11(p["a"], p["b"], p["links"]["A"], oa, ob)
            a11_ce[0] += o
            a11_ce[1] += t
            sizes[0] += p["a"].n_gap + p["b"].n_gap
            sizes[1] += int(ba.sum() + bb.sum())
        den = sum(r["na"] + r["nb"] for r in recs)
        f_sys = 2 * sum(r["tp_A"] for r in recs) / den
        f_perm = 2 * perm_tp / den
        f_fl = 2 * sum(r["fl_A"] for r in recs) / den
        r_sys, r_fl, r_ce = a11_sys[0] / a11_sys[1], a11_fl[0] / a11_fl[1], a11_ce[0] / a11_ce[1]
        rows.append({
            "system": label,
            "boundary_rate_per_canonical_gap": round(sizes[1] / sizes[0], 4),
            "pbd_raw_A": round(f_sys, 4), "pbd_floor_A": round(f_fl, 4), "pbd_permuted_alignment_A": round(f_perm, 4),
            "S_pbd_selfA": round(s_from(recs, "A", "selfA"), 4),
            "S_pbd_xfitA": round(s_from(recs, "A", "xfitA"), 4),
            "S_pbd_truth": round(s_from(recs, "T", "T"), 4),
            "a11_raw": round(r_sys, 4), "a11_floor": round(r_fl, 4), "a11_ceil_xfit": round(r_ce, 4),
            "S_a11_xfit": round((r_sys - r_fl) / (r_ce - r_fl), 4) if r_ce > r_fl else None,
        })
    return rows


def convention_gate(rng, pool) -> dict:
    """One-byte convention changes on side b, with common random numbers.

    Each pair's boundaries are drawn once; every variant is scored with the same
    per-pair RNG seed (same circular shifts and oracle draws), so differences in S
    come only from the boundary positions. Variants: canonical (reference), mapped
    to raw bytes under the patch-end convention and back, under the chunk-start
    convention and back, and every boundary moved one byte to the right (into the
    next character when it is multi-byte) before canonicalization.
    """
    recs = {"canonical": [], "end": [], "start": [], "plus1_byte": []}
    identity = {"end": 0, "start": 0, "plus1_byte": 0}
    for p in pool:
        ba, bb = system_boundaries(rng, p, "gauss", (0.6, 1.0, 1.0, 1.6, 1.6))
        b = p["b"]
        seed = int(rng.integers(0, 2**31 - 1))
        variants = {"canonical": bb}
        for conv in ("end", "start"):
            back = np.zeros(b.n_gap, bool)
            for k in np.where(bb)[0]:
                kk = b.canon_from_raw(b.raw_from_canon(int(k), conv))
                if kk >= 0:
                    back[kk] = True
            variants[conv] = back
        back = np.zeros(b.n_gap, bool)
        for k in np.where(bb)[0]:
            g = min(b.raw_from_canon(int(k), "end") + 1, b.byte_len - 2)
            kk = b.canon_from_raw(g)
            if kk >= 0:
                back[kk] = True
        variants["plus1_byte"] = back
        for name, arr in variants.items():
            recs[name].append(pbd_record(np.random.default_rng(seed), p, ba, arr, n_shift=8))
            if name in identity and np.array_equal(arr, bb):
                identity[name] += 1
    out = {name: round(s_from(r, "A", "selfA"), 4) for name, r in recs.items()}
    out["abs_difference_end_vs_start"] = round(abs(out["end"] - out["start"]), 4)
    out["abs_difference_plus1_vs_canonical"] = round(abs(out["plus1_byte"] - out["canonical"]), 4)
    out["round_trip_identity_share"] = {k: round(v / len(pool), 4) for k, v in identity.items()}
    return out


# ----------------------------------------------------------------------------
# Part 2: the dossier's UOT instrument on the same systems
# ----------------------------------------------------------------------------

def load_legacy():
    spec = importlib.util.spec_from_file_location("tb_legacy", ROOT / "legacy/harness/translation_boundaries.py")
    tb = importlib.util.module_from_spec(spec)
    sys.modules["tb_legacy"] = tb
    spec.loader.exec_module(tb)
    return tb


def uot_links(tb, a: Side, b: Side, links):
    deg_a, deg_b = {}, {}
    for i, j in links:
        deg_a[i] = deg_a.get(i, 0) + 1
        deg_b[j] = deg_b.get(j, 0) + 1
    out = []
    for i, j in sorted(links):
        sa, sb = a.tok_span[i], b.tok_span[j]
        if min(sa[1], a.byte_len - 1) <= sa[0] or min(sb[1], b.byte_len - 1) <= sb[0]:
            continue  # span owns no byte gaps (single final byte); the legacy evaluator fails closed on these
        out.append(tb.SpanLink(sa[0], sa[1], sb[0], sb[1], 1.0, 1.0 / deg_a[i], 1.0 / deg_b[j]))
    return tuple(out)


def raw_mass(side: Side, canon: np.ndarray, conv: str, eps=1e-3) -> np.ndarray:
    m = np.full(side.byte_len - 1, eps)
    for k in np.where(canon)[0]:
        g = side.raw_from_canon(int(k), conv)
        if 0 <= g < side.byte_len - 1:
            m[g] = 1.0
    return m


def uot_loss(tb, cfg, p, ma, mb, links) -> float:
    a, b = p["a"], p["b"]
    return tb.transport_boundary_mass(tb.BoundaryView(a.byte_len, ma), tb.BoundaryView(b.byte_len, mb), links, cfg).loss


def uot_gate(seed: int, lang: str, n_pairs: int, n_shift: int) -> dict:
    tb = load_legacy()
    cfg = tb.BoundaryTransportConfig()
    rng = np.random.default_rng(seed + 1000)
    pool = make_pool(rng, lang, n_pairs, "base")
    systems = [
        ("oracle_aligner_token_edges", "tokedge", None),
        ("bernoulli_p0.05", "bern", 0.05), ("bernoulli_p0.2", "bern", 0.2), ("bernoulli_p0.5", "bern", 0.5),
        ("word_gaps_both_sides", "word", None),
        ("gauss_rho0.0", "gauss", (0.0, 1.0, 1.0, 1.6, 1.6)),
        ("gauss_rho1.0", "gauss", (1.0, 1.0, 1.0, 1.6, 1.6)),
        ("true_cut_oracle", "displaced", 0.0),
    ]
    rows = []
    for label, name, param in systems:
        al, pe, fl, ce_x, ce_s, conv_shift = [], [], [], [], [], []
        for p in pool:
            a, b = p["a"], p["b"]
            if name == "tokedge":
                ba = np.zeros(a.n_gap, bool)
                bb = np.zeros(b.n_gap, bool)
                ba[a.tok_last_gap[a.tok_last_gap >= 0]] = True
                bb[b.tok_last_gap[b.tok_last_gap >= 0]] = True
            else:
                ba, bb = system_boundaries(rng, p, name, param)
            links = uot_links(tb, a, b, p["links"]["A"])
            ma, mb = raw_mass(a, ba, "end"), raw_mass(b, bb, "end")
            al.append(uot_loss(tb, cfg, p, ma, mb, links))
            perm = rng.permutation(b.n_tok)
            plinks = uot_links(tb, a, b, {(i, int(perm[j])) for i, j in p["links"]["A"]})
            try:
                pe.append(uot_loss(tb, cfg, p, ma, mb, plinks))
            except tb.BoundaryContractError:
                pass
            fl.append(float(np.mean([uot_loss(tb, cfg, p, ma, raw_mass(b, shift(bb, int(k)), "end"), links)
                                     for k in rng.integers(1, max(b.n_gap, 2), size=n_shift)])))
            n = int(round((ba.sum() + bb.sum()) / 2))
            oa, ob = oracle_boundaries(rng, a, b, p["cuts"]["B"], n)
            ce_x.append(uot_loss(tb, cfg, p, raw_mass(a, oa, "end"), raw_mass(b, ob, "end"), links))
            oa, ob = oracle_boundaries(rng, a, b, p["cuts"]["A"], n)
            ce_s.append(uot_loss(tb, cfg, p, raw_mass(a, oa, "end"), raw_mass(b, ob, "end"), links))
            conv_shift.append(uot_loss(tb, cfg, p, ma, raw_mass(b, bb, "start"), links))
        L, P, F, CX, CS, CV = (float(np.mean(v)) for v in (al, pe, fl, ce_x, ce_s, conv_shift))
        rows.append({
            "system": label, "uot_aligned": round(L, 4), "uot_permuted_alignment": round(P, 4),
            "aligned_over_permuted": round(L / P, 3) if P > 0 else None,
            "uot_floor_circular_shift": round(F, 4), "uot_ceiling_xfit": round(CX, 4), "uot_ceiling_self": round(CS, 4),
            "S_uot_xfit": round((F - L) / (F - CX), 4) if F > CX else None,
            "S_uot_self": round((F - L) / (F - CS), 4) if F > CS else None,
            "uot_side_b_start_convention": round(CV, 4),
            "convention_loss_ratio": round(CV / L, 3) if L > 0 else None,
        })
    return {"seed": seed, "lang": lang, "pairs": n_pairs, "floor_shifts": n_shift, "rows": rows}


# ----------------------------------------------------------------------------
# Part 3: decision-rule operating characteristics (PBD)
# ----------------------------------------------------------------------------

RULES = {
    # name: (NO_HEADROOM point line, NO_HEADROOM lower-bound line, HEADROOM upper-bound line)
    "dossier_literal": (0.90, 0.85, 0.90),
    "margin_only": (0.88, 0.85, 0.85),
    "registered": (0.88, 0.85, None),  # HEADROOM line depends on inter-aligner cut agreement
}
AGREEMENT_MIN = 0.75          # below: INSTRUMENT_INVALID for the pair (no verdict)
AGREEMENT_STRICT_BELOW = 0.85  # in [0.75, 0.85): HEADROOM line tightens to 0.80


def headroom_line(rule: str, agreement: float) -> float:
    line = RULES[rule][2]
    if line is not None:
        return line
    return 0.85 if agreement >= AGREEMENT_STRICT_BELOW else 0.80


def decide(s_self_ci, s_self_hat, rule: str = "registered", agreement: float = 1.0) -> str:
    """Three-way rule on one pair under one aligner (self ceiling); see the registration.

    registered: INSTRUMENT_INVALID if the two aligners' cut Dice < 0.75. NO_HEADROOM if the
    point estimate >= 0.88 and the lower 90% bound >= 0.85. HEADROOM if the upper 90% bound
    < 0.85 (cut Dice >= 0.85) or < 0.80 (cut Dice in [0.75, 0.85)). INDETERMINATE otherwise.
    The pair's verdict needs both aligners to agree.
    """
    if rule == "registered" and agreement < AGREEMENT_MIN:
        return "INSTRUMENT_INVALID"
    p_line, lo_line, _ = RULES[rule]
    lo, hi = s_self_ci
    if s_self_hat >= p_line and lo >= lo_line:
        return "NO_HEADROOM"
    if hi < headroom_line(rule, agreement):
        return "HEADROOM"
    return "INDETERMINATE"


def combine(d_a: str, d_b: str) -> str:
    if "INSTRUMENT_INVALID" in (d_a, d_b):
        return "INSTRUMENT_INVALID"
    return d_a if d_a == d_b else "INDETERMINATE"


def oc_part(seed: int, lang: str, pool_n: int, n_eval: int, reps: int, n_boot: int, noise: str) -> dict:
    rng = np.random.default_rng(seed)
    pool = make_pool(rng, lang, pool_n, noise)
    agreement = cut_agreement(pool)
    inter = np.zeros(len(pool))
    tot = np.zeros(len(pool))
    for i, p in enumerate(pool):
        sa = {int(ga.max()) for ga, _ in p["cuts"]["A"]}
        sb = {int(ga.max()) for ga, _ in p["cuts"]["B"]}
        inter[i], tot[i] = len(sa & sb), len(sa) + len(sb)
    out_rows = []
    for frac in (0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.14, 0.20):
        recs = []
        for p in pool:
            ba, bb = system_boundaries(rng, p, "displaced_plus_extra", (frac, 0.02))
            recs.append(pbd_record(rng, p, ba, bb, n_shift=10))
        arr = Arrays(recs)
        allidx = np.arange(len(recs))
        s_true = float(arr.S("T", "T", allidx))
        pop = {k: float(arr.S(*k.split("|"), allidx)) for k in ("A|selfA", "A|xfitA", "B|selfB", "B|xfitB")}
        counts = {r: {"NO_HEADROOM": 0, "HEADROOM": 0, "INDETERMINATE": 0, "INSTRUMENT_INVALID": 0} for r in RULES}
        widths, hats = [], []
        for _ in range(reps):
            idx = rng.choice(len(recs), size=n_eval, replace=False)
            boot = idx[rng.integers(0, n_eval, size=(n_boot, n_eval))]
            agr = float(2 * inter[idx].sum() / tot[idx].sum())
            dec = {r: [] for r in RULES}
            for key, sc in (("A", "selfA"), ("B", "selfB")):
                s_self_hat = float(arr.S(key, sc, idx))
                bs_self = arr.S(key, sc, boot)
                ci_self = (float(np.quantile(bs_self, 0.05)), float(np.quantile(bs_self, 0.95)))
                widths.append(ci_self[1] - ci_self[0])
                hats.append(s_self_hat)
                for r in RULES:
                    dec[r].append(decide(ci_self, s_self_hat, r, agr))
            for r in RULES:
                counts[r][combine(*dec[r])] += 1
        out_rows.append({"displaced_fraction": frac, "S_true": round(s_true, 4),
                         **{f"S_pop_{k.replace('|', '_')}": round(v, 4) for k, v in pop.items()},
                         "mean_90ci_width_self": round(float(np.mean(widths)), 4),
                         "sd_of_estimate_self": round(float(np.std(hats)), 4),
                         **{f"{r}:{k}": round(v / reps, 4) for r in RULES for k, v in counts[r].items()}})
    return {"seed": seed, "lang": lang, "aligner_noise": noise, "pool": pool_n, "n_eval": n_eval,
            "replicates": reps, "bootstrap": n_boot, "inter_aligner_cut_dice": round(agreement, 4), "rows": out_rows}


# ----------------------------------------------------------------------------
# Part 4: rate calibration in the latent-score model (what calibration fixes vs placement)
# ----------------------------------------------------------------------------

def calibration_part(seed: int, lang: str, pool_n: int) -> dict:
    rng = np.random.default_rng(seed + 2000)
    pool = make_pool(rng, lang, pool_n, "base")
    dev, test = pool[: pool_n // 2], pool[pool_n // 2:]
    rows = []
    for rho in (0.0, 0.5, 0.9, 1.0):
        mu, omega, ta = 1.0, 1.0, 1.6
        tb_native = -0.5  # side b heavily over-segmented at its native threshold (most character gaps)
        scores_dev = [gaussian_scores(rng, p["a"], p["b"], p["extra"], p["cuts"]["T"], rho, mu, omega) for p in dev]
        target = np.mean([(sa > ta).sum() for sa, _ in scores_dev])
        allb = np.concatenate([sb for _, sb in scores_dev])
        n_b = len(scores_dev)
        # threshold on side b so that mean boundaries per sentence equals side a's (fit on dev)
        tb_cal = float(np.sort(allb)[::-1][int(round(target * n_b)) - 1])
        recs = {"native": [], "calibrated": [], "word": []}
        for p in test:
            sa, sb = gaussian_scores(rng, p["a"], p["b"], p["extra"], p["cuts"]["T"], rho, mu, omega)
            recs["native"].append(pbd_record(rng, p, sa > ta, sb > tb_native, n_shift=8))
            recs["calibrated"].append(pbd_record(rng, p, sa > ta, sb > tb_cal, n_shift=8))
            recs["word"].append(pbd_record(rng, p, p["extra"]["word_a"], p["extra"]["word_b"], n_shift=8))
        row = {"rho": rho}
        for k, r in recs.items():
            na = sum(x["na"] for x in r) / len(r)
            nb = sum(x["nb"] for x in r) / len(r)
            den = sum(x["na"] + x["nb"] for x in r)
            row[k] = {"mean_boundaries_a": round(na, 2), "mean_boundaries_b": round(nb, 2),
                      "pbd_raw_A": round(2 * sum(x["tp_A"] for x in r) / den, 4),
                      "S_selfA": round(s_from(r, "A", "selfA"), 4), "S_xfitA": round(s_from(r, "A", "xfitA"), 4),
                      "S_truth": round(s_from(r, "T", "T"), 4)}
        rows.append(row)
    return {"seed": seed, "lang": lang, "pool": pool_n, "dev_test_split": "first half fits the side-b threshold, second half scores", "rows": rows}


# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--skip-uot", action="store_true")
    ap.add_argument("--only", choices=["gates", "uot", "oc", "calibration"], default=None)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    ap.add_argument("--langs", nargs="+", default=None)
    args = ap.parse_args()
    seeds = tuple(args.seeds)
    q = args.quick
    t0 = time.time()
    result: dict = {"script": "instrument_sim.py", "seeds": list(seeds), "argv": sys.argv[1:], "profiles": PROFILES,
                    "aligner_noise_drop_spur": ALIGNER_NOISE, "quick": q}
    parts = [args.only] if args.only else ["gates", "uot", "oc", "calibration"]
    if "gates" in parts:
        gates = []
        for seed in seeds:
            for lang in (args.langs or ("zh", "ko", "pl")):
                rng = np.random.default_rng(seed)
                pool = make_pool(rng, lang, 120 if q else 400, "base")
                systems = [
                    ("bernoulli_p0.05", "bern", 0.05), ("bernoulli_p0.10", "bern", 0.10),
                    ("bernoulli_p0.20", "bern", 0.20), ("bernoulli_p0.30", "bern", 0.30),
                    ("bernoulli_p0.50", "bern", 0.50),
                    ("word_gaps_both_sides", "word", None), ("every_char_gap_both_sides", "char", None),
                    ("gauss_rho0.00", "gauss", (0.0, 1.0, 1.0, 1.6, 1.6)),
                    ("gauss_rho0.50", "gauss", (0.5, 1.0, 1.0, 1.6, 1.6)),
                    ("gauss_rho0.90", "gauss", (0.9, 1.0, 1.0, 1.6, 1.6)),
                    ("gauss_rho1.00", "gauss", (1.0, 1.0, 1.0, 1.6, 1.6)),
                    ("true_cuts_displaced_0.00", "displaced", 0.0),
                    ("true_cuts_displaced_0.10", "displaced", 0.10),
                    ("true_cuts_displaced_0.30", "displaced", 0.30),
                    ("true_cuts_plus_extra_q0.05", "displaced_plus_extra", (0.0, 0.05)),
                    ("true_cuts_plus_extra_q0.20", "displaced_plus_extra", (0.0, 0.20)),
                ]
                gates.append({"seed": seed, "lang": lang, "pairs": len(pool),
                              "inter_aligner_cut_dice": round(cut_agreement(pool), 4),
                              "rows": gate_rows(rng, pool, systems),
                              "convention": convention_gate(rng, pool[:200])})
                print(f"gates seed={seed} lang={lang} t={time.time() - t0:.0f}s", flush=True)
        result["pbd_a11_gates"] = gates
    if "uot" in parts and not args.skip_uot:
        result["uot_gates"] = []
        for seed in seeds:
            for lang in (args.langs or ("zh", "pl")):
                result["uot_gates"].append(uot_gate(seed, lang, 12 if q else 40, 2 if q else 3))
                print(f"uot seed={seed} lang={lang} t={time.time() - t0:.0f}s", flush=True)
    if "oc" in parts:
        result["oc"] = []
        for seed in seeds:
            for lang, noise in (("zh", "low"), ("zh", "base"), ("pl", "base"), ("zh", "high"), ("ko", "base"), ("ko", "high")):
                if args.langs and f"{lang}-{noise}" not in args.langs:
                    continue
                result["oc"].append(oc_part(seed, lang, 2000 if q else 5000, 1012,
                                            40 if q else 200, 500 if q else 1000, noise))
                print(f"oc seed={seed} lang={lang} noise={noise} t={time.time() - t0:.0f}s", flush=True)
    if "calibration" in parts:
        result["calibration"] = [calibration_part(seed, "zh", 600 if q else 2000) for seed in seeds]
        print(f"calibration t={time.time() - t0:.0f}s", flush=True)
    result["elapsed_seconds"] = round(time.time() - t0, 1)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
