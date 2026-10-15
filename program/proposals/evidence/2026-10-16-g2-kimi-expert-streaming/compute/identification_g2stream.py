#!/usr/bin/env python3
"""G2-stream gauntlet: identification arithmetic on ds4's M5 Max targets (CPU, no data beyond docs).

Inputs are published numbers only:
  - file geometry (routed pool, routed bytes per token, non-routed "spine" bytes per token) from the
    local-frontier-moe-sweep dossier, section 2, A3 (GGUF tensor tables read by HTTP range requests);
  - ds4's M5 Max streaming measurements (docs/SSD_STREAMING.md and QA_BEFORE_RELEASES.md at
    antirez/ds4 commit 90aa4b56, 2026-09-06), as transcribed in ds4-targets.json;
  - the dossier's two-term decode model A6, its decode-efficiency range A2 (e = 0.47-0.61 of
    614 GB/s), its SSD bandwidth assumptions A5 and its cache-share hit-rate brackets A7.

It computes, per generation target:
  1. the time budget left for expert I/O after the memory term, and the (h, B) pairs that explain
     it exactly (the degeneracy the dossier names: A6 "cannot separate h from B");
  2. the dossier null's prediction interval (h from the A7 bracket for the target's cache share, B
     in 5.85-10.6 GB/s, e in 0.47-0.61) and whether the measured value falls inside it;
  3. the same for Kimi K2.6 UD-Q2_K_XL at the dossier's two memory scenarios, and the sensitivity
     of predicted decode to B, h and e.
Nothing here is fitted; the output is a pre-data map of what the validation can and cannot identify.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
GIB = 2**30
MEM_BW = 614.0  # GB/s, Apple, M5 Max 40-core GPU (dossier A1)
E_RANGE = (0.47, 0.61)  # dossier A2
B_A5 = (5.85, 10.6)  # dossier A5 assumption for purpose-built streamers
B_GRID = (3.4, 4.7, 5.85, 8.0, 10.6, 14.5)

GEOM = {  # dossier A3 (GB = 1e9 bytes)
    "glm53_iq2xxs": {"pool": 186.86, "routed_tok": 5.84, "spine_tok": 19.72, "layers": 75, "experts": 256, "k": 8},
    "v4flash_vision_mxfp4": {"pool": 147.17, "routed_tok": 3.45, "spine_tok": 7.74, "layers": 43, "experts": 256, "k": 6},
    "kimi_k26_ud_q2_k_xl": {"pool": 331.14, "routed_tok": 6.90, "spine_tok": 8.53, "layers": 60, "experts": 384, "k": 8},
}

# A7 brackets (share of pool cached -> h range); the null interpolates the bracket ends linearly in share
A7 = [(0.10, 0.45, 0.55), (0.15, 0.45, 0.55), (0.22, 0.70, 0.80), (0.26, 0.70, 0.80),
      (0.32, 0.75, 0.85), (0.38, 0.75, 0.85), (0.55, 0.85, 0.90), (0.60, 0.85, 0.90)]


def a7_bracket(share: float) -> tuple[float, float]:
    if share <= A7[0][0]:
        return A7[0][1], A7[0][2]
    if share >= A7[-1][0]:
        return A7[-1][1], A7[-1][2]
    for (s0, l0, h0), (s1, l1, h1) in zip(A7, A7[1:]):
        if s0 <= share <= s1:
            f = 0.0 if s1 == s0 else (share - s0) / (s1 - s0)
            return l0 + f * (l1 - l0), h0 + f * (h1 - h0)
    raise AssertionError


def tps(h: float, B: float, e: float, g: dict) -> float:
    t = (1 - h) * g["routed_tok"] / B + (g["routed_tok"] + g["spine_tok"]) / (e * MEM_BW)
    return 1.0 / t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    targets = json.loads((HERE / "ds4-targets.json").read_text(encoding="utf-8"))["targets"]
    out: dict = {"inputs": {"mem_bw_GBps": MEM_BW, "e_range": E_RANGE, "B_A5": B_A5, "A7": A7, "geometry": GEOM}}
    rows = []
    for t in targets:
        if t.get("metric") != "generation_tps" or t["model"] not in GEOM:
            continue
        g = GEOM[t["model"]]
        share = t["cache_gib"] * GIB / 1e9 / g["pool"]
        obs = t["value"]
        t_obs_ms = 1000.0 / obs
        mem_ms = [1000.0 * (g["routed_tok"] + g["spine_tok"]) / (e * MEM_BW) for e in E_RANGE]
        io_ms = [t_obs_ms - m for m in mem_ms]  # high e leaves more I/O time
        iso = {}
        for B in B_GRID:
            hs = [1 - (io / 1000.0) * B / g["routed_tok"] for io in io_ms]
            iso[str(B)] = [round(min(hs), 3), round(max(hs), 3)]
        lo_h, hi_h = a7_bracket(share)
        null_vals = [tps(h, B, e, g) for h in (lo_h, hi_h) for B in B_A5 for e in E_RANGE]
        rows.append({
            "id": t["id"], "model": t["model"], "cache_gib": t["cache_gib"], "share_of_pool": round(share, 3),
            "observed_tps": obs, "ms_per_token": round(t_obs_ms, 1),
            "memory_term_ms_e061_e047": [round(mem_ms[1], 1), round(mem_ms[0], 1)],
            "io_residual_ms": [round(min(io_ms), 1), round(max(io_ms), 1)],
            "h_that_fits_exactly_by_B": iso,
            "dossier_null_h_bracket": [round(lo_h, 3), round(hi_h, 3)],
            "dossier_null_tps_interval": [round(min(null_vals), 2), round(max(null_vals), 2)],
            "observed_inside_null_interval": min(null_vals) <= obs <= max(null_vals),
            "observed_over_null_midpoint": round(obs / math.sqrt(min(null_vals) * max(null_vals)), 2),
        })
    out["generation_targets"] = rows
    # Kimi K2.6 Q2 under the null, both dossier memory scenarios
    g = GEOM["kimi_k26_ud_q2_k_xl"]
    kimi = []
    for label, cache_gb in (("all_other_work_stopped", 75.2), ("first_reading_2026-10-15", 46.0)):
        share = cache_gb / g["pool"]
        lo_h, hi_h = a7_bracket(share)
        vals = {f"h={h:.2f},B={B},e={e}": round(tps(h, B, e, g), 2)
                for h in (lo_h, hi_h) for B in (3.4,) + B_A5 for e in E_RANGE}
        kimi.append({"scenario": label, "cache_GB": cache_gb, "share": round(share, 3),
                     "null_h": [round(lo_h, 3), round(hi_h, 3)], "tps": vals,
                     "range_A5": [round(min(tps(h, B, e, g) for h in (lo_h, hi_h) for B in B_A5 for e in E_RANGE), 2),
                                  round(max(tps(h, B, e, g) for h in (lo_h, hi_h) for B in B_A5 for e in E_RANGE), 2)]})
    out["kimi_null"] = kimi
    # sensitivity at the all-stopped centre (h 0.75, B 7.9 geometric mid of A5, e 0.54)
    h0, B0, e0 = 0.75, math.sqrt(B_A5[0] * B_A5[1]), 0.54
    base = tps(h0, B0, e0, g)
    sens = {
        "centre": {"h": h0, "B": round(B0, 2), "e": e0, "tps": round(base, 2)},
        "B_3.4_to_10.6_ratio": round(tps(h0, 10.6, e0, g) / tps(h0, 3.4, e0, g), 2),
        "B_5.85_to_10.6_ratio": round(tps(h0, 10.6, e0, g) / tps(h0, 5.85, e0, g), 2),
        "h_0.70_to_0.80_ratio": round(tps(0.80, B0, e0, g) / tps(0.70, B0, e0, g), 2),
        "e_0.47_to_0.61_ratio": round(tps(h0, B0, 0.61, g) / tps(h0, B0, 0.47, g), 2),
        "pct_time_per_0.01_h": round(100 * (g["routed_tok"] * 0.01 / B0) / (1 / base), 2),
    }
    out["kimi_sensitivity"] = sens
    # Frozen null predictions (registration section 8.4): A6 with B fixed by the same calibration row
    # as the emulator (CAL-B: a whole-layer 16-token append over the 186.86 GB routed pool took
    # 30.8 s; compute for 16 tokens at an assumed 257 tokens/s prefill is subtracted), e = 0.61
    # (ds4's in-memory Metal decode, A2), h = midpoint of the A7 bracket at the target's cache share.
    # V4 Flash uses the same B (same Mac model; which of ds4's two M5 Max machines ran it is unstated).
    b_cal = 186.86 / (30.8 - 16 / 257.0)
    null_rows = []
    for t in targets:
        if t.get("metric") != "generation_tps" or t["model"] not in GEOM:
            continue
        g = GEOM[t["model"]]
        share = t["cache_gib"] * GIB / 1e9 / g["pool"]
        lo_h, hi_h = a7_bracket(share)
        pred = tps((lo_h + hi_h) / 2, b_cal, 0.61, g)
        null_rows.append({"id": t["id"], "obs": t["value"], "null_pred": round(pred, 3),
                          "log_err": round(math.log(pred / t["value"]), 4)})
    contrasts = {"K1": ("V9", "V8"), "K2": ("V5", "V5b"), "K3": ("V5", "V5i")}
    obs = {r["id"]: r["obs"] for r in null_rows}
    out["null_frozen"] = {
        "B_cal_GBps": round(b_cal, 3),
        "levels": null_rows,
        "mean_abs_log_err": round(sum(abs(r["log_err"]) for r in null_rows) / len(null_rows), 4),
        "G": round(math.exp(sum(abs(r["log_err"]) for r in null_rows) / len(null_rows)), 3),
        "contrasts_null_pred_ratio_1": {k: {"obs_ratio": round(obs[a] / obs[b], 3), "null_log_err": round(-math.log(obs[a] / obs[b]), 4)} for k, (a, b) in contrasts.items()},
    }
    print("null frozen: B_cal", round(b_cal, 3), "G", out["null_frozen"]["G"], [(r["id"], r["null_pred"], r["obs"]) for r in null_rows])
    args.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for r in rows:
        print(r["id"], r["model"], "share", r["share_of_pool"], "obs", r["observed_tps"],
              "null", r["dossier_null_tps_interval"], "inside", r["observed_inside_null_interval"],
              "h@B=5.85", r["h_that_fits_exactly_by_B"]["5.85"], "h@B=10.6", r["h_that_fits_exactly_by_B"]["10.6"])
    for k in kimi:
        print("kimi", k["scenario"], k["share"], k["null_h"], k["range_A5"])
    print("sensitivity", sens)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
