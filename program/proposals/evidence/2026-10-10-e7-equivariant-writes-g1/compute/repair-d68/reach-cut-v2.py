#!/usr/bin/env python3
"""S3v2: which eval-time interventions remove which paths from the facts to the answer (D68 repair).

Wave 1's S3 (`../reach-doctor.py`, kept unedited) checked one claim: with the
recurrent state zeroed at every step, information moves at most
3 x 511 + 9 x 3 = 1,560 positions. Wave 1's registered CUT was a different
intervention (one reset of the GDN recurrent and conv states at the first token
after the facts block, SWA untouched), and both refuters and reviewer 1 showed by
complex step that it leaves live paths. This script re-checks every intervention
registration v2 uses, and the two wave-1 interventions, on a NumPy reference of
the registered A0 module graph that is closer to the real module than S3's
stand-in:

  12 pre-norm blocks, blocks 3, 7, 11 (zero-indexed) causal sliding-window
  attention (W = 512: position i attends to i-511 .. i) with RoPE (theta 1e4) on
  q and k; the other nine are Gated DeltaNet blocks as in fla 0.5.2
  `GatedDeltaNet` (use_short_conv, conv_size 4, SiLU after the conv on q, k and
  v; L2-normalised q and k per head; q scaled by head_dim^-0.5; beta =
  sigmoid(b_proj x); g = -exp(A_log) * softplus(a_proj x + dt_bias), alpha =
  exp(g); S_t = alpha_t S_{t-1} (I - beta_t k_t k_t^T) + beta_t v_t k_t^T; o_t =
  S_t q_t; output gate: RMSNorm(o) * SiLU(g_proj x) per head; o_proj); an MLP
  (Linear D->4D, SiLU, Linear 4D->D) after every mixer, as in the measured
  module. Width D = 16 with 2 heads of 8 (the real model has 768 and 12 x 64).

Method: complex step. The input embeddings of a SET of positions (the whole
facts block, or the queried fact's span) are perturbed together by i*h*r with h =
1e-30 and a fixed random real direction r per position; the derivative of the
answer-position output is Im(out) / h. An imaginary part is exactly 0.0 only when
no computational path exists from any perturbed position (a cancellation of
several nonzero contributions to exactly 0.0 has probability zero); the complex
step has no subtractive cancellation, so a path carrying 1e-40 is still seen.

Layout: [facts block: 8 facts x 8 tokens = positions 0..63] [filler] [answer at a].
c = 64 is the first post-facts position; d = a - (c - 1) is the distance from
the facts block's last token to the answer position (registration v2 defines B3 by
d >= 1,600, B2 by 560 <= d <= 1,520, B1 by the queried fact at <= 480).
The queried fact is fact 2 (positions 16..23).

Modes (registration v2 names in brackets):
  full                 the model as trained.
  v1_single_cut        wave-1 CUT: GDN recurrent state zeroed once at t = c and
                       conv inputs from t < c dropped for t >= c; SWA untouched.
  v1_value_ablation    wave-1 ABLATION: v = 0 (after the conv) on the queried
                       fact's tokens in every GDN layer.
  partial_span_cut     state zeroed at every t in [c, a - 1,561], carried after
                       (one refuter's suggested repair; included to show why the
                       span must reach the answer).
  span_cut             [REACH cut] GDN recurrence replaced by its zero-state
                       form o_t = beta_t (k_t . q_t) v_t at EVERY t >= c in every
                       GDN layer; conv and SWA unchanged.
  span_cut_convdrop    span_cut plus conv inputs from t < c dropped for t >= c.
  relay_block          [recurrent-only read] SWA queries at t >= c cannot attend
                       to keys < c; GDN state and conv unchanged (the
                       recurrent-only condition of 2610.06750 Sec. 4.1, applied
                       at the facts/filler boundary).
  disconnect           span_cut_convdrop plus relay_block (every path across
                       the boundary removed).
  write_ablation       [D1 fact-span write ablation] on the queried fact's
                       tokens in every GDN layer: beta = 0 (no erase, no write)
                       and alpha = 1 (no input-dependent decay), so the state
                       passes the span unchanged; and conv inputs from those
                       tokens dropped for every output position outside the
                       span. Only attention can carry the fact out of its span.
  write_ablation_beta_only  beta = 0 on the span (alpha left input-dependent) and
                       the same conv drop: shows that the decay gate alone is a
                       path out of the span.
  isolation            [ISO] write_ablation plus: no SWA query outside the span
                       attends to a key inside it. Nothing leaves the span.
  isolation_beta_only  isolation with alpha left input-dependent on the span.

Expected: every row's exact-zero status must equal the answer of `reachable`,
an independent symbolic reachability computation on the same layer graph and
mode semantics (no numerics). Registration v2 relies on: span_cut exactly 0 at
every d >= 1,561 (the facts block's last token is perturbed; 1,557 when only the
queried fact is perturbed, because its information reaches c - 1 through a
state no earlier than layer 0's output); disconnect exactly 0 everywhere;
isolation exactly 0 everywhere for the queried-fact set; v1_single_cut,
v1_value_ablation, partial_span_cut, write_ablation, write_ablation_beta_only
and isolation_beta_only nonzero at B3 distances; relay_block and full nonzero
everywhere.

Seeds 42, 43, 44 (weights, inputs, directions). Usage:
  reach-cut-v2.py <output.json> [workers]
This is a reference of the module graph, not the fla kernels, not the harness and
not a trained model. The harness's cpu-doctor node must reproduce the same table
on the harness's own module (registration v2, prerequisite 2a).
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np

W = 512
CONV = 4
LAYERS = 12
D = 16
HEADS = 2
HD = D // HEADS
H = 1e-30
N_FACTS, FACT_LEN = 8, 8
C = N_FACTS * FACT_LEN                     # first post-facts position
QUERIED = (2 * FACT_LEN, 3 * FACT_LEN)     # queried fact span [16, 24)
BOUND = 3 * (W - 1) + 9 * (CONV - 1)       # 1,560
DISTANCES = [300, 1000, 1557, 1560, 1561, 1600, 1700]
MODES = ["full", "v1_single_cut", "v1_value_ablation", "partial_span_cut", "span_cut", "span_cut_convdrop",
         "relay_block", "disconnect", "write_ablation", "write_ablation_beta_only", "isolation",
         "isolation_beta_only"]
SETS = ["facts_block", "queried_fact"]


def rmsnorm(x):
    return x / np.sqrt((x * x).mean(-1, keepdims=True) + 1e-6)


def l2n(x):
    return x / np.sqrt((x * x).sum(-1, keepdims=True) + 1e-6)


def silu(x):
    return x / (1.0 + np.exp(-x))


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def softplus(x):
    return np.log1p(np.exp(x))


def rope(x, pos):
    # x: (L, HD) for one head; rotate pairs (2j, 2j+1) by pos * theta^(-2j/HD)
    half = HD // 2
    inv = 10000.0 ** (-np.arange(half) * 2.0 / HD)
    ang = pos[:, None] * inv[None, :]
    cos, sin = np.cos(ang), np.sin(ang)
    x1, x2 = x[:, 0::2], x[:, 1::2]
    out = np.empty_like(x)
    out[:, 0::2] = x1 * cos - x2 * sin
    out[:, 1::2] = x1 * sin + x2 * cos
    return out


def conv(x, w, drop_from_before=None, span=None):
    """Causal depthwise conv, out[t] = sum_j w[j] x[t-j].
    drop_from_before=c: for t >= c, inputs from positions < c are dropped.
    span=(s, e): for output positions outside [s, e), inputs from inside [s, e) are dropped."""
    L = len(x)
    out = np.zeros_like(x)
    t = np.arange(L)
    for j in range(CONV):
        src = t - j
        ok = src >= 0
        keep = ok.copy()
        if drop_from_before is not None:
            keep &= ~((t >= drop_from_before) & (src < drop_from_before))
        if span is not None:
            s, e = span
            inside_src = (src >= s) & (src < e)
            inside_out = (t >= s) & (t < e)
            keep &= ~(inside_src & ~inside_out)
        idx = np.where(keep)[0]
        out[idx] += w[j] * x[src[idx]]
    return out


class Model:
    def __init__(self, rng):
        self.layers = []
        for i in range(LAYERS):
            p = {"swa": i % 4 == 3}
            s = 1.0 / np.sqrt(D)
            for name in ("q", "k", "v", "o", "g"):
                p[name] = rng.normal(0, s, (D, D))
            p["a"] = rng.normal(0, s, (D, HEADS))
            p["b"] = rng.normal(0, s, (D, HEADS))
            # head 0 slow (timescales ~ 300-3,000 tokens), head 1 as fla's range would often give (fast)
            p["A"] = np.array([rng.uniform(5e-4, 5e-3), rng.uniform(0.05, 1.0)])
            p["dt_bias"] = rng.normal(0, 0.5, HEADS)
            p["conv"] = {n: rng.normal(0, 0.5, (CONV, D)) for n in ("q", "k", "v")}
            p["onorm"] = np.ones(HD)
            p["m1"] = rng.normal(0, s, (D, 4 * D))
            p["m2"] = rng.normal(0, 0.5 / np.sqrt(4 * D), (4 * D, D))
            self.layers.append(p)

    def swa(self, p, h, mode, a):
        L = len(h)
        pos = np.arange(L, dtype=float)
        q, k, v = h @ p["q"], h @ p["k"], h @ p["v"]
        idx = np.arange(L)
        mask = (idx[None, :] <= idx[:, None]) & (idx[None, :] >= idx[:, None] - (W - 1))
        if mode in ("relay_block", "disconnect"):
            mask &= ~((idx[:, None] >= C) & (idx[None, :] < C))
        if mode in ("isolation", "isolation_beta_only"):
            s, e = QUERIED
            q_out = (idx[:, None] < s) | (idx[:, None] >= e)
            k_in = (idx[None, :] >= s) & (idx[None, :] < e)
            mask &= ~(q_out & k_in)
        out = np.zeros_like(h)
        for hh in range(HEADS):
            sl = slice(hh * HD, (hh + 1) * HD)
            qq, kk = rope(q[:, sl], pos), rope(k[:, sl], pos)
            sc = (qq @ kk.T) / np.sqrt(HD)
            sc = np.where(mask, sc, -np.inf)
            sc = np.exp(sc - sc.real.max(1, keepdims=True))
            sc = sc / sc.sum(1, keepdims=True)
            out[:, sl] = sc @ v[:, sl]
        return out @ p["o"]

    def gdn(self, p, h, mode, a):
        L = len(h)
        dfb = C if mode in ("v1_single_cut", "span_cut_convdrop", "disconnect") else None
        span = QUERIED if mode in ("write_ablation", "write_ablation_beta_only", "isolation", "isolation_beta_only") else None
        q = silu(conv(h @ p["q"], p["conv"]["q"], dfb, span))
        k = silu(conv(h @ p["k"], p["conv"]["k"], dfb, span))
        v = silu(conv(h @ p["v"], p["conv"]["v"], dfb, span))
        if mode == "v1_value_ablation":
            v = v.copy()
            v[QUERIED[0]:QUERIED[1]] = 0.0
        alpha = np.exp(-p["A"] * softplus(h @ p["a"] + p["dt_bias"]))   # (L, HEADS)
        beta = sigmoid(h @ p["b"])
        if mode in ("write_ablation", "isolation"):
            # the span is transparent to the recurrence: no write, no erase (beta = 0) and no
            # input-dependent decay (alpha = 1). With beta = 0 alone, alpha_t = exp(g(h_t)) still
            # depends on the fact's tokens and modulates the carried state (a path found by this check).
            beta = beta.copy()
            beta[QUERIED[0]:QUERIED[1]] = 0.0
            alpha = alpha.copy()
            alpha[QUERIED[0]:QUERIED[1]] = 1.0
        t_idx = np.arange(L)
        zero_prev = np.zeros(L, dtype=bool)
        if mode == "v1_single_cut":
            zero_prev[C] = True
        elif mode == "partial_span_cut":
            zero_prev[C:max(C, a - BOUND)] = True        # [c, a - 1,561]
        elif mode in ("span_cut", "span_cut_convdrop", "disconnect"):
            zero_prev[C:] = True
        out = np.zeros((L, D), dtype=complex)
        for hh in range(HEADS):
            sl = slice(hh * HD, (hh + 1) * HD)
            kk = l2n(k[:, sl])
            qq = l2n(q[:, sl]) * HD ** -0.5
            vv = v[:, sl]
            S = np.zeros((HD, HD), dtype=complex)
            o = np.zeros((L, HD), dtype=complex)
            for t in range(L):
                prev = np.zeros((HD, HD), dtype=complex) if zero_prev[t] else S
                S = alpha[t, hh] * (prev - beta[t, hh] * np.outer(prev @ kk[t], kk[t])) + beta[t, hh] * np.outer(vv[t], kk[t])
                o[t] = S @ qq[t]
            out[:, sl] = rmsnorm(o) * p["onorm"]
        gate = silu(h @ p["g"])
        return (out * gate) @ p["o"]

    def forward(self, x, mode, a):
        for p in self.layers:
            h = rmsnorm(x)
            x = x + (self.swa(p, h, mode, a) if p["swa"] else self.gdn(p, h, mode, a))
            x = x + silu(rmsnorm(x) @ p["m1"]) @ p["m2"]
        return x


def one(args):
    seed, d, mode, pset = args
    rng = np.random.default_rng(seed)
    model = Model(rng)
    a = (C - 1) + d
    L = a + 1
    x = rng.normal(0, 1, (L, D)).astype(complex)
    direction = rng.normal(0, 1, (L, D))
    positions = range(0, C) if pset == "facts_block" else range(*QUERIED)
    xp = x.copy()
    for p_ in positions:
        xp[p_] += 1j * H * direction[p_]
    t0 = time.time()
    out = model.forward(xp, mode, a)[a]
    deriv = float(np.abs(out.imag).max() / H)
    return {"seed": seed, "distance": d, "mode": mode, "set": pset, "derivative": deriv,
            "exact_zero": deriv == 0.0, "seconds": round(time.time() - t0, 2)}


def reachable(mode, pset, d):
    """Symbolic reachability on the same layer graph and mode semantics, with no numerics.

    Propagates a boolean 'depends on the perturbed set' flag through the 12 layers:
    SWA output at t depends on any flagged key in its (masked) window; a GDN conv
    output at t on any flagged input among t-3..t (minus dropped inputs); alpha_t and
    beta_t on h_t unless forced on the ablated span; the state S_t on S_{t-1} (unless
    zeroed) and on alpha_t, beta_t, k_t, v_t; o_t on S_t and q_t. Returns whether the
    answer position depends on the set. The complex step must give an exact zero
    exactly where this returns False: two independent computations of the same bound.
    """
    a = (C - 1) + d
    L = a + 1
    idx = np.arange(L)
    x = np.zeros(L, dtype=bool)
    if pset == "facts_block":
        x[0:C] = True
    else:
        x[QUERIED[0]:QUERIED[1]] = True
    s, e = QUERIED
    in_span = (idx >= s) & (idx < e)
    for i in range(LAYERS):
        if i % 4 == 3:
            # SWA: t depends on any flagged key j in [t-511, t] allowed by the mask
            pref = np.concatenate([[0], np.cumsum(x)])
            lo = np.maximum(idx - (W - 1), 0)
            any_win = (pref[idx + 1] - pref[lo]) > 0
            out = any_win.copy()
            if mode in ("relay_block", "disconnect"):
                # queries >= C may only see keys >= C
                pref_post = np.concatenate([[0], np.cumsum(x & (idx >= C))])
                lo_post = np.maximum(lo, C)
                post = (pref_post[idx + 1] - pref_post[np.minimum(lo_post, idx + 1)]) > 0
                out = np.where(idx >= C, post, any_win)
            if mode in ("isolation", "isolation_beta_only"):
                xo = x & ~in_span
                pref_o = np.concatenate([[0], np.cumsum(xo)])
                outside = (pref_o[idx + 1] - pref_o[lo]) > 0
                out = np.where(in_span, any_win, outside)
            x = x | out
        else:
            dfb = C if mode in ("v1_single_cut", "span_cut_convdrop", "disconnect") else None
            span_drop = mode in ("write_ablation", "write_ablation_beta_only", "isolation", "isolation_beta_only")
            conv_dep = np.zeros(L, dtype=bool)
            for j in range(CONV):
                src = idx - j
                ok = src >= 0
                src_c = np.clip(src, 0, L - 1)
                keep = ok.copy()
                if dfb is not None:
                    keep &= ~((idx >= dfb) & (src < dfb))
                if span_drop:
                    keep &= ~(in_span[src_c] & ~in_span)
                conv_dep |= keep & x[src_c]
            q_dep = k_dep = v_dep = conv_dep
            v_zero = in_span if mode == "v1_value_ablation" else np.zeros(L, dtype=bool)
            alpha_dep = x.copy()                      # alpha_t and beta_t are functions of h_t
            beta_dep = x.copy()
            beta_zero = np.zeros(L, dtype=bool)
            if mode in ("write_ablation", "isolation"):
                alpha_dep = alpha_dep & ~in_span      # alpha forced to 1 on the span
                beta_dep = beta_dep & ~in_span        # beta forced to 0 on the span
                beta_zero = in_span
            if mode in ("write_ablation_beta_only", "isolation_beta_only"):
                beta_dep = beta_dep & ~in_span
                beta_zero = in_span
            zero_prev = np.zeros(L, dtype=bool)
            if mode == "v1_single_cut":
                zero_prev[C] = True
            elif mode == "partial_span_cut":
                zero_prev[C:max(C, a - BOUND)] = True
            elif mode in ("span_cut", "span_cut_convdrop", "disconnect"):
                zero_prev[C:] = True
            S_dep, S_nz = False, False
            o_dep = np.zeros(L, dtype=bool)
            for t in range(L):
                prev_dep, prev_nz = (False, False) if zero_prev[t] else (S_dep, S_nz)
                if beta_zero[t]:
                    # S_t = alpha_t * prev
                    S_dep = prev_nz and (prev_dep or bool(alpha_dep[t]))
                    S_nz = prev_nz
                else:
                    # S_t = alpha_t (prev - beta_t (prev k_t) k_t^T) + beta_t v_t k_t^T
                    keep_part = prev_nz and (prev_dep or bool(alpha_dep[t]) or bool(beta_dep[t]) or bool(k_dep[t]))
                    write_part = (not v_zero[t]) and (bool(beta_dep[t]) or bool(v_dep[t]) or bool(k_dep[t]))
                    S_dep = keep_part or write_part
                    S_nz = True
                o_dep[t] = S_nz and (S_dep or bool(q_dep[t]))
            x = x | o_dep
        # MLP is position-wise: no change to the dependency set
    return bool(x[a])


def expected_zero(mode, pset, d):
    return not reachable(mode, pset, d)


def main() -> int:
    out_path = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    tasks = [(s, d, m, ps) for s in (42, 43, 44) for d in DISTANCES for m in MODES for ps in SETS]
    t0 = time.time()
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(workers) as pool:
        rows = pool.map(one, tasks, chunksize=1)
    checks = []
    for r in rows:
        exp0 = expected_zero(r["mode"], r["set"], r["distance"])
        r["expected_exact_zero"] = exp0
        r["ok"] = r["exact_zero"] == exp0
        checks.append(r["ok"])
    boundaries = {}
    for m in ("span_cut", "span_cut_convdrop"):
        for ps in SETS:
            last = None
            for dd in range(1530, 1571):
                if reachable(m, ps, dd):
                    last = dd
            boundaries[f"{m}|{ps}"] = {"max_reachable_distance_symbolic": last}
    summary = {}
    for m in MODES:
        for ps in SETS:
            sub = [r for r in rows if r["mode"] == m and r["set"] == ps]
            summary[f"{m}|{ps}"] = {str(d): ("0" if all(r["exact_zero"] for r in sub if r["distance"] == d)
                                             else ("nonzero in all seeds" if all(not r["exact_zero"] for r in sub if r["distance"] == d)
                                                   else "mixed")) for d in DISTANCES}
    # ratio of the wave-1 interventions to full at B3 distances (how much of the path they leave)
    ratios = {}
    for m in ("v1_single_cut", "v1_value_ablation", "partial_span_cut", "write_ablation", "write_ablation_beta_only", "relay_block"):
        for ps in SETS:
            vals = []
            for s in (42, 43, 44):
                for d in (1600, 1700):
                    f = next(r["derivative"] for r in rows if r["mode"] == "full" and r["set"] == ps and r["seed"] == s and r["distance"] == d)
                    g = next(r["derivative"] for r in rows if r["mode"] == m and r["set"] == ps and r["seed"] == s and r["distance"] == d)
                    vals.append(g / f if f > 0 else None)
            vals = [v for v in vals if v is not None]
            ratios[f"{m}|{ps}"] = {"min": round(min(vals), 3), "max": round(max(vals), 3)} if vals else None
    res = {
        "script": "reach-cut-v2.py",
        "bound": BOUND,
        "layout": {"facts_block": [0, C - 1], "first_post_facts_position_c": C, "queried_fact_span": list(QUERIED),
                   "distance_definition": "d = answer position - (c - 1)", "width": D, "heads": HEADS},
        "all_checks_ok": all(checks),
        "check_definition": "every row: (complex-step derivative == 0.0) equals (not reachable(mode, set, d)) from the symbolic reachability",
        "symbolic_reach_boundaries": boundaries,
        "n_rows": len(rows),
        "summary_exact_zero_by_distance": summary,
        "derivative_ratio_to_full_at_B3_distances_1600_1700": ratios,
        "rows": rows,
        "runtime_seconds": round(time.time() - t0, 1),
        "scope": ("NumPy reference of the registered A0 module graph (D = 16, 2 heads, float64/complex128); "
                  "checks which eval-time interventions remove which paths; not the fla kernels, not the harness, "
                  "not a trained model, not a pilot. Magnitudes in a random model say nothing about a trained one; "
                  "exact zeros and nonzeros are structural."),
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    print("REACH_CUT_V2", "PASS" if res["all_checks_ok"] else "FAIL", "rows", len(rows), "s", res["runtime_seconds"])
    for k, v in summary.items():
        print(k, v)
    print(json.dumps(ratios))
    return 0 if res["all_checks_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
