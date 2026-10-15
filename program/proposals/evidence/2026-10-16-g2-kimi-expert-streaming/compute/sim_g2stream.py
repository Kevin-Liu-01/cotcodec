#!/usr/bin/env python3
"""G2-stream gauntlet: cache-policy simulators, their unit tests, and operating characteristics.

CPU only, seeded, synthetic data only. Nothing here reads a real routing trace; the real traces
come from the pilot (registration g2-kimi-expert-streaming-v1). This file does three things:

A. Simulators for one MoE layer's expert cache under event-atomic replay (arXiv 2608.07911,
   Definition 2): all k experts a token selects at a layer form one event; hits are counted before
   any insertion; the event's experts are protected from eviction while it is served.
     - LRU;
     - ds4's Metal policy as read at antirez/ds4 commit 90aa4b56 (ds4_metal.m: route hotness counts
       every selection, hit or miss; all counts halve every 16 decode tokens; the victim is the
       non-protected entry with the lowest hotness, ties broken by least recent use);
     - LFU (persistent counts, ties by LRU);
     - static pinned (the cap most frequent experts of a separate calibration split; never refilled);
     - Belady (evict the non-protected entry whose next use is farthest; event-atomic).
   Unit tests: Che's approximation on IRM traces, LRU inclusion, ds4 policy with hotness disabled
   equals LRU exactly, Belady upper-bounds every online policy on the same traces.

B. Operating characteristics of the pilot's hit-rate readout: a synthetic routing generator
   (per-layer Zipf popularity over E = 384 experts, top-8, a temporal-reuse knob calibrated to the
   reuse rates S82 reports for DeepSeek-V3 and Kimi K3, and session- and workload-level hot-set
   shifts), the between-session spread of h at 14%, 22% and 32% of the pool, the share of misses
   that are compulsory (cold start) as a function of decode length, and cluster-bootstrap CI
   half-widths for n sessions per workload.

C. Operating characteristics of the emulator-validation rule (registration section 8): Monte Carlo
   over emulator bias and spread, observation noise per ds4 target class, and calibration noise
   propagated into every holdout.

Usage (repo root):
  uv run --locked python program/proposals/evidence/2026-10-16-g2-kimi-expert-streaming/compute/sim_g2stream.py \
      --out program/proposals/evidence/2026-10-16-g2-kimi-expert-streaming/compute/sim-g2stream.json
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import OrderedDict
from pathlib import Path

import numpy as np

E = 384
K = 8
SEEDS = [42, 43, 44]


# ----------------------------------------------------------------------------------------------
# A. Simulators (one layer; a trace is an int array [T, k] of expert ids, distinct within a row)
# ----------------------------------------------------------------------------------------------


def sim_lru(trace: np.ndarray, cap: int) -> np.ndarray:
    od: OrderedDict[int, None] = OrderedDict()
    hits = np.zeros(len(trace), dtype=np.int64)
    for t, row in enumerate(trace):
        h = 0
        for e in row:
            e = int(e)
            if e in od:
                h += 1
                od.move_to_end(e)
        for e in row:
            e = int(e)
            if e not in od:
                od[e] = None
        hits[t] = h
        # The event's experts are now the most recent entries, so when cap >= k the oldest entry
        # is never protected.
        while len(od) > cap:
            od.popitem(last=False)
    return hits


def sim_ds4(trace: np.ndarray, cap: int, decay_every: int = 16, hotness: bool = True) -> np.ndarray:
    hot = np.zeros(E, dtype=np.int64)
    last = np.full(E, -1, dtype=np.int64)
    cached = np.zeros(E, dtype=bool)
    n_cached = 0
    hits = np.zeros(len(trace), dtype=np.int64)
    stamp = 0
    for t, row in enumerate(trace):
        if hotness and t > 0 and t % decay_every == 0:
            hot >>= 1
        hits[t] = int(cached[row].sum())
        if hotness:
            hot[row] += 1
        hitm = cached[row]
        new = row[~hitm]
        # per-access recency stamps: hits in row order, then insertions in row order (the order an
        # OrderedDict LRU uses); ds4 keeps a per-entry last_used stamp
        acc = np.concatenate([row[hitm], new])
        last[acc] = stamp + np.arange(len(acc))
        stamp += len(acc)
        cached[new] = True
        n_cached += len(new)
        if n_cached > cap:
            prot = np.zeros(E, dtype=bool)
            prot[row] = True
            cand = np.flatnonzero(cached & ~prot)
            n_evict = n_cached - cap
            # lexicographic (hotness, last_used) ascending; evicting the n lowest at once equals
            # evicting one at a time, because evictions do not change other entries' keys
            order = np.lexsort((last[cand], hot[cand]))
            victims = cand[order[:n_evict]]
            cached[victims] = False
            n_cached -= n_evict
    return hits


def sim_lfu(trace: np.ndarray, cap: int) -> np.ndarray:
    cnt = np.zeros(E, dtype=np.int64)
    last = np.full(E, -1, dtype=np.int64)
    cached = np.zeros(E, dtype=bool)
    n_cached = 0
    hits = np.zeros(len(trace), dtype=np.int64)
    stamp = 0
    for t, row in enumerate(trace):
        hits[t] = int(cached[row].sum())
        cnt[row] += 1
        hitm = cached[row]
        new = row[~hitm]
        acc = np.concatenate([row[hitm], new])
        last[acc] = stamp + np.arange(len(acc))
        stamp += len(acc)
        cached[new] = True
        n_cached += len(new)
        if n_cached > cap:
            prot = np.zeros(E, dtype=bool)
            prot[row] = True
            cand = np.flatnonzero(cached & ~prot)
            order = np.lexsort((last[cand], cnt[cand]))
            victims = cand[order[: n_cached - cap]]
            cached[victims] = False
            n_cached = cap
    return hits


def sim_static(trace: np.ndarray, cap: int, pinned: np.ndarray) -> np.ndarray:
    keep = np.zeros(E, dtype=bool)
    keep[pinned[:cap]] = True
    return keep[trace].sum(axis=1).astype(np.int64)


def sim_belady(trace: np.ndarray, cap: int) -> np.ndarray:
    T = len(trace)
    nxt = np.full((T, E), T + 1, dtype=np.int64)  # next use strictly after t
    upcoming = np.full(E, T + 1, dtype=np.int64)
    for t in range(T - 1, -1, -1):
        nxt[t] = upcoming
        upcoming[trace[t]] = t
    cached = np.zeros(E, dtype=bool)
    n_cached = 0
    hits = np.zeros(T, dtype=np.int64)
    for t, row in enumerate(trace):
        hits[t] = int(cached[row].sum())
        new = row[~cached[row]]
        cached[new] = True
        n_cached += len(new)
        if n_cached > cap:
            prot = np.zeros(E, dtype=bool)
            prot[row] = True
            cand = np.flatnonzero(cached & ~prot)
            order = np.argsort(-nxt[t][cand], kind="stable")
            victims = cand[order[: n_cached - cap]]
            cached[victims] = False
            n_cached = cap
    return hits


# ----------------------------------------------------------------------------------------------
# Synthetic routing generator
# ----------------------------------------------------------------------------------------------


def zipf_weights(alpha: float) -> np.ndarray:
    w = np.arange(1, E + 1, dtype=float) ** (-alpha)
    return w / w.sum()


def shifted_perm(rng: np.random.Generator, base: np.ndarray, frac: float) -> np.ndarray:
    perm = base.copy()
    n = int(round(frac * E))
    if n >= 2:
        idx = rng.choice(E, n, replace=False)
        perm[idx] = perm[rng.permutation(idx)]
    return perm


def gen_layer_trace(rng: np.random.Generator, T: int, perm: np.ndarray, alpha: float, rho: float) -> np.ndarray:
    w = zipf_weights(alpha)
    p = np.empty(E)
    p[perm] = w
    out = np.empty((T, K), dtype=np.int64)
    prev = rng.choice(E, K, replace=False, p=p)
    for t in range(T):
        keep = prev[rng.random(K) < rho]
        pp = p.copy()
        pp[keep] = 0.0
        pp /= pp.sum()
        new = rng.choice(E, K - len(keep), replace=False, p=pp)
        cur = np.concatenate([keep, new])
        out[t] = cur
        prev = cur
    return out


def reuse_stats(trace: np.ndarray, window: int = 64) -> tuple[float, float]:
    T = len(trace)
    r1 = np.mean([len(set(trace[t]) & set(trace[t - 1])) / K for t in range(1, T)])
    last_seen = np.full(E, -(10**9))
    within = 0
    total = 0
    for t, row in enumerate(trace):
        if t >= window:
            within += int(np.sum(t - last_seen[row] <= window))
            total += K
        last_seen[row] = t
    return float(r1), float(within / max(total, 1))


# ----------------------------------------------------------------------------------------------
# Unit tests
# ----------------------------------------------------------------------------------------------


def che_hit_rate(p: np.ndarray, cap: int) -> float:
    lo, hi = 0.0, 1e9
    for _ in range(200):
        mid = (lo + hi) / 2
        if np.sum(1 - np.exp(-p * mid)) < cap:
            lo = mid
        else:
            hi = mid
    tc = (lo + hi) / 2
    return float(np.sum(p * (1 - np.exp(-p * tc))))


def lru_single(seq: np.ndarray, cap: int) -> int:
    od: OrderedDict[int, None] = OrderedDict()
    h = 0
    for e in seq:
        e = int(e)
        if e in od:
            h += 1
            od.move_to_end(e)
        else:
            od[e] = None
            if len(od) > cap:
                od.popitem(last=False)
    return h


def unit_tests(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    out: dict = {}
    # 1. Che's approximation on IRM single-item traces
    p = zipf_weights(0.9)
    seq = rng.choice(E, 60_000, p=p)
    rows = []
    for cap in (20, 54, 84, 123, 192):
        warm = 10_000
        od_h = lru_single(seq, cap) - lru_single(seq[:warm], cap)
        sim = od_h / (len(seq) - warm)
        che = che_hit_rate(p, cap)
        rows.append({"cap": cap, "lru_sim": round(sim, 4), "che": round(che, 4), "abs_diff": round(abs(sim - che), 4)})
    out["che_irm"] = {"rows": rows, "pass": all(r["abs_diff"] <= 0.01 for r in rows), "tolerance": 0.01}
    # 2. LRU inclusion on single-item traces
    short = seq[:5_000]
    hs = [lru_single(short, c) for c in range(1, 151)]
    out["lru_inclusion_single"] = {"pass": all(b >= a for a, b in zip(hs, hs[1:]))}
    # 3. ds4 policy with hotness disabled equals LRU exactly (event-atomic)
    perm = rng.permutation(E)
    tr = gen_layer_trace(rng, 800, perm, 0.95, 0.25)
    eq = all(np.array_equal(sim_lru(tr, c), sim_ds4(tr, c, hotness=False)) for c in (12, 54, 84, 160))
    out["ds4_without_hotness_equals_lru"] = {"pass": bool(eq)}
    # 4. Event-atomic LRU monotone in capacity (empirical) and Belady >= every online policy
    caps = [16, 32, 54, 84, 123, 192]
    lru_h = [int(sim_lru(tr, c).sum()) for c in caps]
    out["lru_event_atomic_monotone"] = {"pass": all(b >= a for a, b in zip(lru_h, lru_h[1:])), "hits": lru_h}
    cal = gen_layer_trace(rng, 800, perm, 0.95, 0.25)
    pinned = np.argsort(-np.bincount(cal.ravel(), minlength=E), kind="stable")
    bel_rows = []
    ok = True
    for c in caps:
        b = int(sim_belady(tr, c).sum())
        others = {
            "lru": int(sim_lru(tr, c).sum()),
            "ds4": int(sim_ds4(tr, c).sum()),
            "lfu": int(sim_lfu(tr, c).sum()),
            "static": int(sim_static(tr, c, pinned).sum()),
        }
        ok &= all(b >= v for v in others.values())
        bel_rows.append({"cap": c, "belady": b, **others})
    out["belady_upper_bound"] = {"pass": bool(ok), "rows": bel_rows, "selections": int(tr.size)}
    out["all_pass"] = all(v["pass"] for v in out.values() if isinstance(v, dict) and "pass" in v)
    return out


# ----------------------------------------------------------------------------------------------
# B. Hit-rate readout: spread, cold start, CI half-width
# ----------------------------------------------------------------------------------------------


def calibrate_rho(seed: int, alpha: float) -> dict:
    rng = np.random.default_rng(seed)
    perm = rng.permutation(E)
    grid = []
    for rho in (0.0, 0.15, 0.25, 0.35):
        tr = gen_layer_trace(rng, 800, perm, alpha, rho)
        r1, r64 = reuse_stats(tr)
        grid.append({"rho": rho, "reuse_at_1": round(r1, 3), "reuse_within_64": round(r64, 3)})
    return {"alpha": alpha, "grid": grid}


def session_hits(rng, T, layers, wl_perm, alpha, rho, shift, caps, policies, pinned_by_layer):
    res = {pol: {c: [0, 0] for c in caps} for pol in policies}
    distinct = 0
    sel = 0
    for li in range(layers):
        perm = shifted_perm(rng, wl_perm[li], shift)
        tr = gen_layer_trace(rng, T, perm, alpha, rho)
        distinct += len(np.unique(tr))
        sel += tr.size
        for c in caps:
            for pol in policies:
                if pol == "lru":
                    h = sim_lru(tr, c)
                elif pol == "ds4":
                    h = sim_ds4(tr, c)
                elif pol == "static":
                    h = sim_static(tr, c, pinned_by_layer[li])
                else:
                    raise ValueError(pol)
                res[pol][c][0] += int(h.sum())
                res[pol][c][1] += tr.size
    return {pol: {c: v[0] / v[1] for c, v in d.items()} for pol, d in res.items()}, distinct / sel


def readout_oc(seed: int, alpha: float, rho: float, n_sessions: int, T: int, layers: int) -> dict:
    rng = np.random.default_rng(seed)
    caps = {"14pct": round(0.14 * E), "22pct": round(0.22 * E), "32pct": round(0.32 * E)}
    base = rng.permutation(E)
    workloads = {}
    for w in range(4):
        wl_perm = [shifted_perm(rng, shifted_perm(rng, base, 0.15), 0.6) for _ in range(layers)]
        # calibration split for the static policy: 4 extra sessions from the same workload
        pinned = []
        for li in range(layers):
            cnt = np.zeros(E, dtype=np.int64)
            for _ in range(4):
                tr = gen_layer_trace(rng, T, shifted_perm(rng, wl_perm[li], 0.3), alpha, rho)
                cnt += np.bincount(tr.ravel(), minlength=E)
            pinned.append(np.argsort(-cnt, kind="stable"))
        sess = []
        comp = []
        for _ in range(n_sessions):
            h, c = session_hits(rng, T, layers, wl_perm, alpha, rho, 0.3, list(caps.values()), ["lru", "ds4", "static"], pinned)
            sess.append(h)
            comp.append(c)
        workloads[f"W{w}"] = {"sessions": sess, "compulsory_share": comp}
    # summarise
    summary = {}
    boot_rng = np.random.default_rng(42)
    for wname, d in workloads.items():
        s = {}
        for pol in ("lru", "ds4", "static"):
            for lab, c in caps.items():
                vals = np.array([x[pol][c] for x in d["sessions"]])
                hw = {}
                for n in (8, 16, 32):
                    if n > len(vals):
                        continue
                    means = [boot_rng.choice(vals, n, replace=True).mean() for _ in range(2000)]
                    lo, hi = np.percentile(means, [2.5, 97.5])
                    hw[str(n)] = round(float((hi - lo) / 2), 4)
                s[f"{pol}@{lab}"] = {
                    "mean": round(float(vals.mean()), 4),
                    "sd_between_sessions": round(float(vals.std(ddof=1)), 4),
                    "ci95_half_width_by_n": hw,
                }
        s["compulsory_share_mean"] = round(float(np.mean(d["compulsory_share"])), 4)
        summary[wname] = s
    return {"alpha": alpha, "rho": rho, "T": T, "layers": layers, "n_sessions_per_workload": n_sessions, "caps": caps, "workloads": summary}


def cold_start_curve(seed: int, alpha: float, rho: float, layers: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    cap = round(0.22 * E)
    for T in (64, 128, 512, 2048):
        hs_cold, hs_steady, comp = [], [], []
        for _ in range(4):
            for _li in range(layers):
                tr = gen_layer_trace(rng, T + 2048, rng.permutation(E), alpha, rho)
                warm = sim_ds4(tr, cap)
                # cold window: the first T tokens from an empty cache; steady: T tokens after 2048 tokens of warm-up
                hs_cold.append(warm[:T].sum() / (T * K))
                hs_steady.append(warm[2048:].sum() / (T * K))
                comp.append(len(np.unique(tr[:T])) / (T * K))
        out.append({
            "decode_tokens": T,
            "ds4_h22_cold_start": round(float(np.mean(hs_cold)), 4),
            "ds4_h22_after_2048_warmup": round(float(np.mean(hs_steady)), 4),
            "compulsory_share_of_selections": round(float(np.mean(comp)), 4),
        })
    return out


# ----------------------------------------------------------------------------------------------
# C. Emulator-validation rule: operating characteristics
# ----------------------------------------------------------------------------------------------

# Level holdouts (registration section 8.3; ds4-targets.json): (id, noise class).
LEVELS = [("V2", "median3"), ("V3", "repeated"), ("V4", "repeated"), ("V5", "median3"), ("V5i", "median3"),
          ("V5b", "median3"), ("V5bi", "median3"), ("V6", "single"), ("V7", "single"), ("V8", "single"), ("V9", "single")]
EPS = {"median3": 0.10, "repeated": 0.10, "single": 0.15}
# Observation noise (log scale). ds4's own regression floors sit about 10% below its three-run reference
# medians, and the same GLM 8K/12K condition measured on ds4's two M5 Max machines differed by 1.9-3.8% in
# generation (QA_BEFORE_RELEASES.md, 2026-09-06); single runs are given twice the spread of medians.
SIGMA_OBS = {"median3": 0.035, "repeated": 0.035, "single": 0.07}
PRIMARY_CONTRASTS = [("K1", "single"), ("K2", "median3"), ("K3", "median3")]


def validation_oc(seed: int, reps: int, null_mean_abs: float) -> dict:
    rng = np.random.default_rng(seed)
    classes = [c for _, c in LEVELS]
    s_obs = np.array([SIGMA_OBS[c] for c in classes])
    bound = np.array([math.log(1.20 * (1 + EPS[c])) for c in classes])
    level_rows = []
    for beta in (0.0, 0.1, 0.18, 0.25, 0.35):
        for sm in (0.05, 0.10, 0.15, 0.25):
            # calibration noise: CAL-B (three-run median) fixes B; its error reaches every level with
            # gain 0.6 (the I/O share of decode time in the GLM 61 GiB rows, identification table)
            cal = 0.6 * rng.normal(0, SIGMA_OBS["median3"], reps)
            err = beta + cal[:, None] + rng.normal(0, sm, (reps, len(classes))) - rng.normal(0, s_obs, (reps, len(classes)))
            a = np.abs(err)
            agg = np.exp(a.mean(axis=1)) <= 1.20
            per = (a <= bound).all(axis=1)
            skill = a.mean(axis=1) < null_mean_abs
            level_rows.append({"bias_log": beta, "bias_pct": round(100 * (math.exp(beta) - 1), 1), "emulator_sd_log": sm,
                               "p_levels_pass": round(float((agg & per & skill).mean()), 3),
                               "p_aggregate_only": round(float(agg.mean()), 3)})
    c_obs = np.array([np.sqrt(2) * SIGMA_OBS[c] for _, c in PRIMARY_CONTRASTS])
    obs_ratio = np.log(np.array([1.625, 1.249, 1.352]))
    contrast_rows = []
    for gamma in (0.0, 0.1, 0.2, 0.3):
        for sc in (0.03, 0.06, 0.10):
            err = gamma + rng.normal(0, sc, (reps, 3)) - rng.normal(0, c_obs, (reps, 3))
            within = (np.abs(err) <= math.log(1.15)).all(axis=1)
            sign = ((obs_ratio + err) > 0).all(axis=1)
            contrast_rows.append({"mechanism_bias_log": gamma, "contrast_sd_log": sc,
                                  "p_contrasts_pass": round(float((within & sign).mean()), 3)})
    # the dossier null predicts a ratio of 1 for every primary contrast (no cache-state dependence)
    null_contrast_err = [-x for x in obs_ratio]
    return {"levels": LEVELS, "eps": EPS, "sigma_obs_log": SIGMA_OBS, "null_mean_abs_log_err": null_mean_abs,
            "level_rows": level_rows, "contrast_rows": contrast_rows,
            "null_contrast_log_err": [round(x, 3) for x in null_contrast_err],
            "null_contrasts_pass": bool(all(abs(x) <= math.log(1.15) for x in null_contrast_err))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sessions", type=int, default=24)
    ap.add_argument("--T", type=int, default=768)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--readout-seeds", type=int, default=3)
    ap.add_argument("--validation-reps", type=int, default=20000)
    args = ap.parse_args()
    t0 = time.time()
    res: dict = {"seeds": SEEDS, "E": E, "k": K, "note": "synthetic routing only; no real trace is read"}
    res["unit_tests"] = {str(s): unit_tests(s) for s in SEEDS}
    print("unit tests", {s: v["all_pass"] for s, v in res["unit_tests"].items()}, f"{time.time()-t0:.0f}s", flush=True)
    res["rho_calibration"] = [calibrate_rho(42, a) for a in (0.9, 1.0)]
    print("rho calibration done", f"{time.time()-t0:.0f}s", flush=True)
    # S82 targets: reuse at 1 token 26-36%, within 64 tokens 80-85% (DeepSeek-V3, Kimi K3)
    alpha, rho = 0.95, 0.25
    res["readout_oc"] = {str(s): readout_oc(s, alpha, rho, args.sessions, args.T, args.layers) for s in SEEDS[: args.readout_seeds]}
    print("readout oc done", f"{time.time()-t0:.0f}s", flush=True)
    res["cold_start"] = cold_start_curve(42, alpha, rho, 1)
    print("cold start done", f"{time.time()-t0:.0f}s", flush=True)
    ident = json.loads((Path(__file__).resolve().parent / "identification-g2stream.json").read_text(encoding="utf-8"))
    res["validation_oc"] = validation_oc(42, args.validation_reps, ident["null_frozen"]["mean_abs_log_err"])
    res["runtime_s"] = round(time.time() - t0, 1)
    args.out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print("wrote", args.out, f"{res['runtime_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
