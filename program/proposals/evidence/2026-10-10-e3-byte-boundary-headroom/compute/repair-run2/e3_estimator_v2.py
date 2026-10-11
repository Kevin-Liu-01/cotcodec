#!/usr/bin/env python3
"""Registered estimator for e3-byte-boundary-headroom-v2 (draft), as code.

This module is the decision code. The simulation S1v2 (instrument_sim_v2.py)
imports it unchanged, and the production harness must reproduce S1v2's verdicts
on its planted systems before any GPU job (registration v2, prerequisite P1).

Everything here works on WORD GAPS after canonicalization: gap t on a side lies
between word t and word t+1 of that side's registered word segmentation (English:
whitespace words with punctuation split; Chinese: the registered segmenter's
words). Aligner links are pairs (i, j) of word indices.

Pieces, in the order the analysis uses them:

1. ``allowed_pairs``: the target. Pair (t, u) of an English gap t and a Chinese
   gap u is allowed when some alignment-consistent phrase pair contains both gaps
   strictly inside and splitting it there yields two consistent sub-pairs, in
   straight order (left with left) or inverted order (left with right). The whole
   sentence is a consistent phrase pair, so its straight splits are the monotone
   consistent cuts of wave 1; nested and inverted splits are what wave 1 left out.
   Unlinked words between the two images make a range of Chinese gaps (and
   consecutive English splits with the same images a range of English gaps); every
   gap of a range is allowed.
2. ``matching_size``: hits of a selection = the maximum number of disjoint allowed
   pairs between the selected English gaps and the selected Chinese gaps (each
   gap used once).
3. ``budget``: one common per-sentence budget k = min(floor(RHO * min(word gaps
   per side)), nu_A, nu_B), where nu_X is the maximum matching size of aligner
   X's allowed pairs over all gaps. So neither side selects more than half of its
   word gaps (no saturation), and under each aligner the oracle that selects k of
   its own allowed pairs reaches D = 1 (the ceiling is 1 by construction).
4. ``select_topk``: the system's selection on a side = its k highest-scoring word
   gaps (ties broken by the registered seed). Restricting the selection to word
   gaps removes word-end detection from the statistic: a system that knows only
   where words end ranks all word gaps equally and scores 0 in expectation.
5. ``floor_hits``: the floor = expected hits of k word gaps drawn uniformly at
   random on each side independently (Monte Carlo, registered draws and seed). It
   conditions on the budget (density) and on the word structure of both sides.
6. ``s_pooled``: S_X = (sum hits - sum floor) / (sum ceiling - sum floor), pooled
   over sentences, with ceiling = k under an aligner (1 per selected pair) and
   min(k, nu_T) under the truth (simulation only). This is the form of Cohen's
   kappa_M (chance-corrected agreement scaled by its maximum at fixed marginals).
7. ``decide``: the three-way rule on one pair and the final verdict with line M.

The decision target is the CONSENSUS of the two aligners: ``consensus_links`` keeps
only links both aligner families produce, and allowed pairs are computed from those
links. A spurious link destroys every phrase pair it crosses, so a single aligner at
the published Chinese-English error rates attenuates S by about 0.3 (S1v2); a
spurious link survives the intersection only when both families make it. Per-aligner
targets are reported as secondaries. Attenuation alpha (the S of a selection made
exactly on true allowed pairs) is handled on one of two registered paths:

* band path (no gold data): S_lo = S / ALPHA_MAX and S_hi = S / alpha_min(agreement),
  where ALPHA_MAX is the largest consensus alpha S1v2 finds inside the registered
  error band (each aligner's link AER at most 0.15, any error correlation, any
  spurious:missed split) and alpha_min(agreement) the smallest alpha among band
  conditions whose pair agreement is below the measured one (ALPHA_MIN_TABLE).
  Valid only while the measured pair agreement lies in [AGREE_MIN, AGREE_MAX);
* gold path (reserved sign-off R5 granted): alpha measured on the gold-aligned
  sample and divided out, S* = S / alpha_hat, with a joint bootstrap; valid only if
  alpha_hat is at least GOLD_ALPHA_MIN (S1v2: with heavily attenuating aligners a
  gold sample whose sentences differ from the test set's mis-states alpha enough
  to produce false NO_HEADROOM calls) and at least GOLD_MIN_PAIRS pairs are usable.
  A transfer margin GOLD_TAU widens the correction: NO_HEADROOM is judged on
  S / (alpha_hat + GOLD_TAU) and HEADROOM on S / (alpha_hat - GOLD_TAU).

No randomness without a seed; every function that draws takes a numpy Generator.
"""

from __future__ import annotations

import numpy as np

RHO = 0.5                 # budget fraction of the smaller side's word gaps
# Band path constants, derived by band_envelope.py from S1v2's attenuation map (band-registered.json):
ALPHA_MAX = 0.97          # largest consensus alpha with each aligner's link AER <= 0.15, any correlation, any split
ALPHA_MIN_TABLE = ((0.55, 0.754), (0.65, 0.651), (0.75, 0.576), (0.85, 0.521))  # (agreement below, alpha_min)
AGREE_MIN = 0.448         # below: aligners worse than the band
AGREE_MAX = 0.85          # at or above: errors presumed shared; band path invalid
GOLD_ALPHA_MIN = 0.70     # gold path valid only if the measured alpha_hat is at least this (correction at most 1.43x)
GOLD_MIN_PAIRS = 280      # and at least this many usable gold pairs
GOLD_TAU = 0.03           # transfer margin on alpha_hat (gold sample to FLORES+); S1v2: a 0.03 shift in AER between
                          # the gold sample and the test set moves consensus alpha by about 0.03-0.05
FLOOR_DRAWS = 64          # Monte Carlo draws per sentence for the floor
NH_LOWER = 0.88           # NO_HEADROOM: lower 90% bound at least this (both aligners)
NH_POINT = 0.90           # and point estimate at least this
H_UPPER = 0.85            # HEADROOM: upper 90% bound below H_UPPER * a (both aligners)


# ----------------------------------------------------------------------------
# 1. Target: alignment-consistent split pairs, straight and inverted
# ----------------------------------------------------------------------------

_TRIPLES: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}


def _triples(n: int):
    """All (s, t, e) with s <= t < e < n (span [s, e] split after word t); cached per n."""
    if n not in _TRIPLES:
        s, t, e = np.meshgrid(np.arange(n), np.arange(n), np.arange(n), indexing="ij")
        keep = (s <= t) & (t < e)
        _TRIPLES[n] = (s[keep], t[keep], e[keep])
    return _TRIPLES[n]


def _span_tables(n: int, lo: np.ndarray, hi: np.ndarray):
    """For every span [s, e] of one side: min of lo and max of hi over its linked words, and a has-link flag."""
    big = 1 << 20
    lo_m = np.where(hi >= 0, lo, big)
    t_lo = np.full((n, n), big, dtype=np.int64)
    t_hi = np.full((n, n), -1, dtype=np.int64)
    for s in range(n):
        t_lo[s, s:] = np.minimum.accumulate(lo_m[s:])
        t_hi[s, s:] = np.maximum.accumulate(hi[s:])
    return t_lo, t_hi, t_hi >= 0


def allowed_pairs(n_a: int, n_b: int, links) -> np.ndarray:
    """Boolean (n_a - 1, n_b - 1) matrix of allowed (English gap, Chinese gap) pairs."""
    na_g, nb_g = n_a - 1, n_b - 1
    if na_g <= 0 or nb_g <= 0 or not links:
        return np.zeros((max(na_g, 0), max(nb_g, 0)), dtype=bool)
    big = 1 << 20
    a_lo = np.full(n_a, big, dtype=np.int64)
    a_hi = np.full(n_a, -1, dtype=np.int64)
    b_lo = np.full(n_b, big, dtype=np.int64)
    b_hi = np.full(n_b, -1, dtype=np.int64)
    for i, j in links:
        a_lo[i] = min(a_lo[i], j)
        a_hi[i] = max(a_hi[i], j)
        b_lo[j] = min(b_lo[j], i)
        b_hi[j] = max(b_hi[j], i)
    img_lo, img_hi, has_a = _span_tables(n_a, a_lo, a_hi)   # English span -> Chinese image
    src_lo, src_hi, _ = _span_tables(n_b, b_lo, b_hi)        # Chinese span -> English sources
    # flat views: 2-D fancy indexing is slow in this numpy build, flat indexing is not
    il, ih, ha = img_lo.ravel(), img_hi.ravel(), has_a.ravel()
    sl, sh = src_lo.ravel(), src_hi.ravel()
    S, T, E = _triples(n_a)
    # the enclosing span [S, E] must be a consistent phrase pair
    ok = ha[S * n_a + E]
    S, T, E = S[ok], T[ok], E[ok]
    se = S * n_a + E
    j1, j2 = il[se], ih[se]
    jj = j1 * n_b + j2
    ok = (sl[jj] >= S) & (sh[jj] <= E)
    # both halves linked
    ok &= ha[S * n_a + T] & ha[(T + 1) * n_a + E]
    S, T, E = S[ok], T[ok], E[ok]
    st, te = S * n_a + T, (T + 1) * n_a + E
    l1, l2 = il[st], ih[st]
    r1, r2 = il[te], ih[te]
    ll, rr = l1 * n_b + l2, r1 * n_b + r2
    cl = (sl[ll] >= S) & (sh[ll] <= T)
    cr = (sl[rr] >= T + 1) & (sh[rr] <= E)
    straight = cl & cr & (l2 < r1)
    inverted = cl & cr & (r2 < l1)
    rows = np.concatenate([T[straight], T[inverted]])
    start = np.concatenate([l2[straight], r2[inverted]])    # Chinese gaps after words start .. stop-1
    stop = np.concatenate([r1[straight], l1[inverted]])
    diff = np.zeros((na_g * (nb_g + 1)), dtype=np.int64)
    np.add.at(diff, rows * (nb_g + 1) + start, 1)
    np.add.at(diff, rows * (nb_g + 1) + stop, -1)
    return np.cumsum(diff.reshape(na_g, nb_g + 1)[:, :nb_g], axis=1) > 0


def consensus_links(links_a, links_b) -> set:
    """Links produced by both aligner families (the decision target's links)."""
    return set(links_a) & set(links_b)


def pair_agreement(M_a: np.ndarray, M_b: np.ndarray) -> tuple[int, int]:
    """(2 x shared allowed pairs, allowed pairs of A + of B) for a pooled Dice of the two aligners' targets."""
    return 2 * int((M_a & M_b).sum()), int(M_a.sum() + M_b.sum())


def monotone_pairs(n_a: int, n_b: int, links) -> np.ndarray:
    """Straight splits of the whole sentence only (wave 1's consistent cuts, on word gaps)."""
    na_g, nb_g = n_a - 1, n_b - 1
    M = np.zeros((max(na_g, 0), max(nb_g, 0)), dtype=bool)
    if na_g <= 0 or nb_g <= 0 or not links:
        return M
    maxj = np.full(n_a, -1)
    minj = np.full(n_a, n_b)
    for i, j in links:
        maxj[i] = max(maxj[i], j)
        minj[i] = min(minj[i], j)
    linked = maxj >= 0
    pre_max = np.maximum.accumulate(np.where(linked, maxj, -1))
    pre_any = np.logical_or.accumulate(linked)
    suf_min = np.minimum.accumulate(np.where(linked, minj, n_b)[::-1])[::-1]
    suf_any = np.logical_or.accumulate(linked[::-1])[::-1]
    for t in range(n_a - 1):
        if pre_any[t] and suf_any[t + 1] and pre_max[t] < suf_min[t + 1]:
            M[t, pre_max[t]:suf_min[t + 1]] = True
    return M


# ----------------------------------------------------------------------------
# 2. Hits: maximum bipartite matching on the allowed pairs of a selection
# ----------------------------------------------------------------------------

def row_masks(M: np.ndarray) -> list[int]:
    """Allowed pairs as one Python int bitmask of Chinese gaps per English gap."""
    w = 1 << np.arange(M.shape[1], dtype=object) if M.shape[1] else np.zeros(0, dtype=object)
    return [int(sum(w[np.flatnonzero(r)])) if r.any() else 0 for r in M]


_POW = [1 << i for i in range(512)]


def _kuhn(adj: list[int], rows, colmask: int) -> tuple[int, dict]:
    """Kuhn's augmenting-path matching on bitmask adjacency restricted to colmask."""
    match: dict[int, int] = {}

    def try_row(r: int, seen: list[int]) -> bool:
        while True:
            avail = adj[r] & colmask & ~seen[0]
            if not avail:
                return False
            low = avail & -avail
            seen[0] |= low
            c = low.bit_length() - 1
            if c not in match or try_row(match[c], seen):
                match[c] = r
                return True

    size = 0
    for r in rows:
        if adj[r] & colmask and try_row(r, [0]):
            size += 1
    return size, match


def matching_size_masks(adj: list[int], rows, cols) -> int:
    colmask = 0
    for c in cols:
        colmask |= _POW[c]
    # fast path: rows whose available columns are disjoint single bits need no augmentation
    av = [a for a in (adj[r] & colmask for r in rows) if a]
    used = 0
    simple = True
    for a in av:
        if a & (a - 1) or a & used:
            simple = False
            break
        used |= a
    if simple:
        return len(av)
    return _kuhn(adj, [int(r) for r in rows], colmask)[0]


def matching_size(M: np.ndarray, rows, cols) -> int:
    """Maximum number of disjoint allowed pairs between selected rows and selected columns."""
    return matching_size_masks(row_masks(M), rows, cols)


def max_matching_pairs(M: np.ndarray, rng: np.random.Generator | None = None, adj: list[int] | None = None):
    """One maximum matching over all gaps (row order randomised when rng is given)."""
    n_r, n_c = M.shape
    adj = row_masks(M) if adj is None else adj
    order = list(range(n_r)) if rng is None else rng.permutation(n_r).tolist()
    _, match = _kuhn(adj, order, (1 << n_c) - 1)
    return [(r, c) for c, r in match.items()]


def nu(M: np.ndarray, adj: list[int] | None = None) -> int:
    if M.size == 0:
        return 0
    return len(max_matching_pairs(M, adj=adj))


# ----------------------------------------------------------------------------
# 3-5. Budget, selection, floor
# ----------------------------------------------------------------------------

def budget(n_gap_a: int, n_gap_b: int, *nus: int, rho: float = RHO) -> int:
    """k = min(floor(rho * smaller side's word gaps), nu of every target in use)."""
    return int(max(0, min([int(np.floor(rho * min(n_gap_a, n_gap_b)))] + [int(x) for x in nus])))


def select_topk(scores: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """Indices of the k highest scores; ties broken by a seeded random key."""
    if k <= 0:
        return np.zeros(0, dtype=np.int64)
    key = rng.random(len(scores))
    order = np.lexsort((key, -np.asarray(scores, dtype=float)))
    return np.sort(order[:k])


def floor_hits(M: np.ndarray, k: int, rng: np.random.Generator, draws: int = FLOOR_DRAWS,
               adj: list[int] | None = None) -> float:
    """Expected hits of k word gaps drawn uniformly at random per side (Monte Carlo)."""
    if k <= 0:
        return 0.0
    n_r, n_c = M.shape
    adj = row_masks(M) if adj is None else adj
    ra = np.argsort(rng.random((draws, n_r)), axis=1)[:, :k].tolist()
    cb = np.argsort(rng.random((draws, n_c)), axis=1)[:, :k].tolist()
    tot = 0
    for d in range(draws):
        tot += matching_size_masks(adj, ra[d], cb[d])
    return tot / draws


# ----------------------------------------------------------------------------
# 6. Pooled statistic and bootstrap
# ----------------------------------------------------------------------------

def s_pooled(hits: np.ndarray, floor: np.ndarray, ceil: np.ndarray, idx=None, w: np.ndarray | None = None):
    """S = (sum hits - sum floor) / (sum ceil - sum floor); idx may be (B, n) for a bootstrap; w = sentence weights."""
    if w is not None:
        hits, floor, ceil = hits * w, floor * w, ceil * w
    if idx is None:
        h, f, c = hits.sum(), floor.sum(), ceil.sum()
    else:
        h, f, c = hits[idx].sum(-1), floor[idx].sum(-1), ceil[idx].sum(-1)
    return (h - f) / (c - f)


LENGTH_BINS = (0, 15, 20, 25, 30, 40, 10**6)   # smaller side's word count, for post-stratifying the gold sample


def poststrat_weights(gold_lengths: np.ndarray, target_lengths: np.ndarray) -> np.ndarray:
    """Weights that give the gold sample the target's distribution over LENGTH_BINS (empty gold bins merge down)."""
    gb = np.digitize(gold_lengths, LENGTH_BINS[1:-1])
    tb = np.digitize(target_lengths, LENGTH_BINS[1:-1])
    nbin = len(LENGTH_BINS) - 1
    pg = np.bincount(gb, minlength=nbin) / len(gb)
    pt = np.bincount(tb, minlength=nbin) / len(tb)
    for b in range(nbin):                      # move target mass of empty gold bins to the nearest filled bin
        if pg[b] == 0 and pt[b] > 0:
            filled = np.flatnonzero(pg > 0)
            nb = filled[np.argmin(np.abs(filled - b))]
            pt[nb] += pt[b]
            pt[b] = 0
    return (pt / np.where(pg > 0, pg, 1))[gb]


def percentile_ci(boot: np.ndarray, level: float = 0.90) -> tuple[float, float]:
    a = (1 - level) / 2
    return float(np.quantile(boot, a)), float(np.quantile(boot, 1 - a))


# ----------------------------------------------------------------------------
# 7. Decision rule
# ----------------------------------------------------------------------------

def decide_one(point: float, lo: float, hi: float, a: float = 1.0) -> str:
    """Generic three-way rule on a corrected statistic: NO_HEADROOM, HEADROOM or INDETERMINATE."""
    if point >= NH_POINT and lo >= NH_LOWER:
        return "NH"
    if hi < H_UPPER * a:
        return "H"
    return "I"


def alpha_min_for(agreement: float, table=None) -> float:
    """Smallest band alpha consistent with a pair agreement below the next table edge."""
    for edge, amin in (ALPHA_MIN_TABLE if table is None else table):
        if agreement < edge:
            return amin
    return float("nan")


def decide_band(point: float, lo: float, hi: float, alpha_min: float | None = None,
                alpha_max: float | None = None, agreement: float | None = None) -> str:
    """Band path on the consensus S: NH judged on S / alpha_max, HEADROOM on S / alpha_min(agreement)."""
    amin = alpha_min if alpha_min is not None else alpha_min_for(agreement)
    amax = ALPHA_MAX if alpha_max is None else alpha_max
    if point / amax >= NH_POINT and lo / amax >= NH_LOWER:
        return "NH"
    if hi / amin < H_UPPER:
        return "H"
    return "I"


def band_valid(agreement: float, agree_min: float | None = None, agree_max: float | None = None) -> bool:
    lo = AGREE_MIN if agree_min is None else agree_min
    hi = AGREE_MAX if agree_max is None else agree_max
    return lo <= agreement < hi


def decide_gold(point_star: float, lo_star: float, hi_star: float, alpha_hat: float, tau: float = GOLD_TAU) -> str:
    """Gold path. S* = S / alpha_hat with its joint-bootstrap interval; NO_HEADROOM judged on S / (alpha_hat + tau)
    (point and lower bound scaled by alpha_hat / (alpha_hat + tau)), HEADROOM on S / (alpha_hat - tau)."""
    if not gold_valid(alpha_hat):
        return "INV"
    lo_scale, hi_scale = alpha_hat / (alpha_hat + tau), alpha_hat / (alpha_hat - tau)
    if point_star * lo_scale >= NH_POINT and lo_star * lo_scale >= NH_LOWER:
        return "NH"
    if hi_star * hi_scale < H_UPPER:
        return "H"
    return "I"


def gold_valid(alpha_hat: float, usable_pairs: int = GOLD_MIN_PAIRS) -> bool:
    return alpha_hat >= GOLD_ALPHA_MIN and usable_pairs >= GOLD_MIN_PAIRS


def combine(*vs: str) -> str:
    return vs[0] if all(v == vs[0] for v in vs) else "I"


def final_verdict(v_primary: str, v_mono: str, gates_ok: bool = True) -> str:
    """Final verdict from the primary system's and the monolingual reference's combined verdicts."""
    if not gates_ok:
        return "INSTRUMENT_INVALID"
    if v_primary == "NH":
        return "NO_HEADROOM"
    if v_mono == "NH":
        return "HEADROOM_MONOLINGUAL"
    if v_primary == "H" and v_mono == "H":
        return "HEADROOM"
    return "INDETERMINATE"
