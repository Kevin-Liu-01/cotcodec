#!/usr/bin/env python3
"""G2-RL gauntlet (CPU, exploratory re-analysis of committed data): what a response cap leaves of
the G2b/G2c rollout-trainer mismatch, and what importance weights an RL trainer would see.

Inputs are the committed seed-42 per-token files (exact rows, 24 MATH-500 L5 prompts, seed 42):
  G2b  program/evidence/2026-10-15/g2b-state-dtype/data/per-token-<model>-seed42.npz
       arm 0 = fp32 state, arm 1 = bf16 state
  G2c  program/evidence/2026-10-15/g2c-precision-vs-layout/data/per-token-<model>-seed42.npz
       arm 0 = fp16 state, arm 1 = bf16 state at fp32's 528-token block (not used here)

d_dec = log p_decode - log p_r1 (vLLM rollout minus the HF+FLA bf16 trainer forward on the same
tokens). The trainer/rollout importance weight is w = exp(-d_dec) = pi_trainer / mu_rollout, and
k3 = E_mu[(w - 1) - log w].

For caps of 4,096, 8,192, 16,384 tokens and no cap (completion tokens beyond the cap dropped,
which is what the rollout would have contained had it been cut there; it is not what a capped
sampler would have generated after the cap, and a capped rollout's tokens before the cap are
identical), per arm:
  * mean |d|, k3, share of tokens with w > 2 (verl's default token-TIS threshold), w > 5, w < 0.5;
  * per sequence: the log trajectory ratio sum(log w) and the geometric mean ratio
    exp(mean log w); share of sequences whose geometric mean falls outside [0.999, 1.001] and
    outside [0.99, 1.01];
  * a sequence mask calibrated on fp32 (|mean log w| above fp32's 90th percentile): the share of
    each arm's sequences it would remove;
  * PSIS k-hat (Zhang-Stephens generalized Pareto fit to the largest weights, Vehtari et al.
    arXiv 1507.02646) for the pooled token weights and for the per-sequence trajectory weights (the
    sequence value is NaN here: 24 sequences per arm give fewer than 5 tail draws);
  * the share of rollouts the cap would cut (completion longer than the cap, or unfinished);
  * k3 and mean |d| ratios to fp32, with a 95% bootstrap over prompts (2,000 draws, seed 42;
    prompts are shared across arms, so the bootstrap resamples prompts jointly).

Usage (repo root): python3 <this file> --out <json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
G2B = ROOT / "program/evidence/2026-10-15/g2b-state-dtype/data"
G2C = ROOT / "program/evidence/2026-10-15/g2c-precision-vs-layout/data"
CAPS = (4096, 8192, 16384, None)
MODELS = ("qwen3.5-4b", "qwen3.5-9b")


def gpd_khat(x: np.ndarray) -> float:
    """Zhang and Stephens (2009) generalized Pareto shape estimate for exceedances x > 0, with the
    weakly informative prior adjustment used by PSIS (k = (n k + 10 * 0.5) / (n + 10))."""

    x = np.sort(np.asarray(x, dtype=np.float64))
    n = x.size
    if n < 5 or not np.isfinite(x).all() or x[-1] <= 0:
        return float("nan")
    m = 30 + int(math.sqrt(n))
    prior_bs, prior_k = 3.0, 10.0
    quart = x[int(n / 4 + 0.5) - 1]
    if quart <= 0:
        quart = x[x > 0][0]
    b = 1.0 / x[-1] + (1.0 - np.sqrt(m / (np.arange(1, m + 1) - 0.5))) / prior_bs / quart
    k = np.log1p(-b[:, None] * x).mean(axis=1)
    len_scale = n * (np.log(-(b / k)) - k - 1.0)
    with np.errstate(over="ignore"):
        w = 1.0 / np.exp(len_scale - len_scale[:, None]).sum(axis=1)
    keep = w >= 10 * np.finfo(float).eps
    w, b = w[keep], b[keep]
    w /= w.sum()
    b_post = (b * w).sum()
    # mean(log1p(-b x)) is already the usual shape parameterisation (positive = heavy tail),
    # as in the reference psis.py gpdfitnew.
    k_hat = np.log1p(-b_post * x).mean()
    return float((n * k_hat + prior_k * 0.5) / (n + prior_k))


def psis_khat(log_w: np.ndarray) -> float:
    """PSIS diagnostic: fit the GPD to the M = min(S/5, 3 sqrt(S)) largest weights above the
    (M+1)-th largest (Vehtari et al., Algorithm 1)."""

    lw = np.asarray(log_w, dtype=np.float64)
    lw = lw[np.isfinite(lw)]
    s = lw.size
    m = int(min(0.2 * s, 3 * math.sqrt(s)))
    if m < 5:
        return float("nan")
    lw = lw - lw.max()
    order = np.sort(lw)
    cutoff = order[-m - 1]
    tail = np.exp(order[-m:]) - math.exp(cutoff)
    tail = tail[tail > 0]
    return gpd_khat(tail)


def load(path: Path) -> dict[str, np.ndarray]:
    raw = np.load(path)
    return {k: raw[k] for k in raw.files if k != "meta_json"}


def arm_rows(raw: dict[str, np.ndarray], arm: int) -> list[dict]:
    off = raw["offsets"]
    rows = []
    for i in np.flatnonzero(raw["arm"] == arm):
        d = raw["d_dec"][off[i] : off[i + 1]].astype(np.float64)
        rows.append(
            {
                "prompt": int(raw["prompt_index"][i]),
                "finished": bool(raw["finished"][i]),
                "d": d,
            }
        )
    return sorted(rows, key=lambda r: r["prompt"])


def per_seq(rows: list[dict], cap: int | None) -> dict[str, np.ndarray]:
    n = len(rows)
    out = {k: np.zeros(n) for k in ("n", "sum_abs", "sum_k3", "gt2", "gt5", "lt05", "sum_logw")}
    cut = np.zeros(n, dtype=bool)
    for j, r in enumerate(rows):
        d = r["d"] if cap is None else r["d"][:cap]
        d = d[np.isfinite(d)]
        lw = -d
        out["n"][j] = d.size
        out["sum_abs"][j] = np.abs(d).sum()
        out["sum_k3"][j] = (np.expm1(lw) - lw).sum()
        out["gt2"][j] = (lw > math.log(2)).sum()
        out["gt5"][j] = (lw > math.log(5)).sum()
        out["lt05"][j] = (lw < math.log(0.5)).sum()
        out["sum_logw"][j] = lw.sum()
        cut[j] = (cap is not None and r["d"].size > cap) or (cap is None and not r["finished"])
    out["cut"] = cut.astype(float)
    return out


def summarize(rows: list[dict], cap: int | None) -> dict:
    s = per_seq(rows, cap)
    n = s["n"].sum()
    mean_logw = s["sum_logw"] / np.maximum(s["n"], 1)
    pooled_lw = np.concatenate(
        [-(r["d"] if cap is None else r["d"][:cap]) for r in rows]
    )
    pooled_lw = pooled_lw[np.isfinite(pooled_lw)]
    return {
        "tokens": int(n),
        "sequences": len(rows),
        "mean_abs_d": float(s["sum_abs"].sum() / n),
        "k3": float(s["sum_k3"].sum() / n),
        "share_w_gt_2": float(s["gt2"].sum() / n),
        "share_w_gt_5": float(s["gt5"].sum() / n),
        "share_w_lt_0p5": float(s["lt05"].sum() / n),
        "seq_log_traj_ratio_median_abs": float(np.median(np.abs(s["sum_logw"]))),
        "seq_log_traj_ratio_p90_abs": float(np.quantile(np.abs(s["sum_logw"]), 0.9)),
        "seq_geo_mean_outside_0p999_1p001": float(np.mean(np.abs(mean_logw) > math.log(1.001))),
        "seq_geo_mean_outside_0p99_1p01": float(np.mean(np.abs(mean_logw) > math.log(1.01))),
        "seq_abs_mean_logw_quantiles": {
            q: float(np.quantile(np.abs(mean_logw), float(q))) for q in ("0.5", "0.9", "0.95")
        },
        "seq_mean_logw_median": float(np.median(mean_logw)),
        "psis_khat_token": psis_khat(pooled_lw),
        "psis_khat_sequence": psis_khat(s["sum_logw"]),
        "share_cut_by_cap": float(s["cut"].mean()),
        "mean_tokens_kept": float(s["n"].mean()),
    }


def ratio_ci(rows_a: list[dict], rows_b: list[dict], cap: int | None, reps: int, seed: int) -> dict:
    """Ratio A/B of pooled k3 and mean |d|, bootstrap over the shared prompts."""

    sa, sb = per_seq(rows_a, cap), per_seq(rows_b, cap)
    pa = [r["prompt"] for r in rows_a]
    pb = [r["prompt"] for r in rows_b]
    assert pa == pb, "arms must share prompts in the same order"
    rng = np.random.default_rng(seed)
    k = len(pa)

    def ratios(idx: np.ndarray) -> tuple[float, float]:
        k3a = sa["sum_k3"][idx].sum() / sa["n"][idx].sum()
        k3b = sb["sum_k3"][idx].sum() / sb["n"][idx].sum()
        ma = sa["sum_abs"][idx].sum() / sa["n"][idx].sum()
        mb = sb["sum_abs"][idx].sum() / sb["n"][idx].sum()
        return k3a / k3b, ma / mb

    point = ratios(np.arange(k))
    boot = np.array([ratios(rng.integers(0, k, k)) for _ in range(reps)])
    lo, hi = np.quantile(boot, [0.025, 0.975], axis=0)
    return {
        "k3_ratio": point[0],
        "k3_ratio_ci95": [float(lo[0]), float(hi[0])],
        "mean_abs_ratio": point[1],
        "mean_abs_ratio_ci95": [float(lo[1]), float(hi[1])],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reps", type=int, default=2000)
    args = ap.parse_args()
    result: dict = {
        "what": "G2b/G2c committed seed-42 per-token data re-read under response caps (exploratory, CPU)",
        "inputs": {},
        "models": {},
    }
    for model in MODELS:
        fb, fc = G2B / f"per-token-{model}-seed42.npz", G2C / f"per-token-{model}-seed42.npz"
        result["inputs"][model] = {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (fb, fc)
        }
        b, c = load(fb), load(fc)
        arms = {"fp32": arm_rows(b, 0), "bf16": arm_rows(b, 1), "fp16": arm_rows(c, 0)}
        mres: dict = {}
        for cap in CAPS:
            key = "none" if cap is None else str(cap)
            block = {arm: summarize(rows, cap) for arm, rows in arms.items()}
            # a sequence-level mask calibrated on fp32 (threshold = fp32's 90th percentile of
            # |mean log w|): the share of each arm's sequences it would mask (24 sequences each)
            per = {arm: per_seq(rows, cap) for arm, rows in arms.items()}
            thr = float(np.quantile(np.abs(per["fp32"]["sum_logw"] / np.maximum(per["fp32"]["n"], 1)), 0.9))
            block["fp32_calibrated_seq_mask"] = {
                "threshold_abs_mean_logw": thr,
                **{arm: float(np.mean(np.abs(v["sum_logw"] / np.maximum(v["n"], 1)) > thr)) for arm, v in per.items()},
            }
            block["ratio_to_fp32"] = {
                arm: ratio_ci(arms[arm], arms["fp32"], cap, args.reps, 42) for arm in ("bf16", "fp16")
            }
            mres[key] = block
        result["models"][model] = mres
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    for model, mres in result["models"].items():
        for cap, block in mres.items():
            r = block["ratio_to_fp32"]
            print(
                f"{model} cap={cap:>5} | k3 fp32 {block['fp32']['k3']:.2e} bf16 {block['bf16']['k3']:.2e} "
                f"fp16 {block['fp16']['k3']:.2e} | k3 ratio bf16 {r['bf16']['k3_ratio']:.1f} "
                f"[{r['bf16']['k3_ratio_ci95'][0]:.1f},{r['bf16']['k3_ratio_ci95'][1]:.1f}] "
                f"fp16 {r['fp16']['k3_ratio']:.1f} | w>2 fp32 {block['fp32']['share_w_gt_2']:.4%} "
                f"bf16 {block['bf16']['share_w_gt_2']:.4%} fp16 {block['fp16']['share_w_gt_2']:.4%} | "
                f"khat tok {block['fp32']['psis_khat_token']:.2f}/{block['bf16']['psis_khat_token']:.2f}/"
                f"{block['fp16']['psis_khat_token']:.2f} seq {block['fp32']['psis_khat_sequence']:.2f}/"
                f"{block['bf16']['psis_khat_sequence']:.2f}/{block['fp16']['psis_khat_sequence']:.2f} | "
                f"cut {block['fp32']['share_cut_by_cap']:.2f}/{block['bf16']['share_cut_by_cap']:.2f}/"
                f"{block['fp16']['share_cut_by_cap']:.2f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
