#!/usr/bin/env python3
"""E4 gate repair (D60), CPU check G1: the episode-constant guard, old and new, on a categorical teacher.

Wave 1's guard called a family EPISODE_CONSTANT when KL_const / KL_S0 < 0.20. The
identification refuter showed by arithmetic that KL_S0 is dominated by
label-set recognition, so the guard fires on families Step 1 has just certified
as label-dependent. Registration v2 replaces it with two decision-bearing
conditions: the resample placebo (simulated in S1v2 and S2v2) and a label-prior
guard, KL_shift >= 0.10 KL_LD, where KL_shift is the divergence a per-episode
probe-independent shift leaves and KL_LD = sum KL(p_GOLD || p_SHUF) is the
teacher's own label sensitivity on the same probes. This script evaluates both
guards exactly (no sampling) on a categorical teacher over the grid the
refuter asked for: GOLD accuracy 0.45 to 0.90 and cardinality 2 to 8.

Teacher on a family whose answers are spread uniformly over m candidates:
  GOLD p_q: a on the correct answer, (0.95 - a)/(m - 1) on each other candidate,
  0.05 spread over V - m = 31,990 other tokens.
  Per-episode shift floor: the probe-average of p_q (the best probe-independent
  distribution for the episode).
  Family constant: the same as the shift floor for latent-parameter families
  (candidates fixed per family).
  Zero-shot student: mass s on the candidates (uniform), 1 - s elsewhere.
  SHUF teacher, three modes: 'flat' (deranged labels leave the teacher at the
  episode marginal), 'follow' (it follows the deranged mapping with the same
  confidence, as a lookup family would), 'half' (half way). A fourth teacher,
  'label_prior', has no probe dependence at all: GOLD is the episode's label
  marginal (one candidate favoured with mass a), and SHUF (labels re-drawn)
  moves the favoured candidate; it must read EPISODE_CONSTANT.

Usage: python guard-sim.py <out.json>
"""

from __future__ import annotations

import hashlib
import json
import math
import sys

V = 32000
OFF = 0.05


def kl(p: list[float], q: list[float]) -> float:
    return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0)


def dist(m: int, hot: int | None, a: float, off_each: float) -> list[float]:
    """Candidates first (m entries), then one aggregated off-candidate bucket weighted by its count."""
    rest = (1 - OFF - (a if hot is not None else 0.0)) / (m - (1 if hot is not None else 0))
    return [a if (hot is not None and i == hot) else rest for i in range(m)]


def family(m: int, a: float, s: float, mode: str) -> dict:
    off_tok = OFF / (V - m)
    zs = [s / m] * m
    zs_off = (1 - s) / (V - m)

    def full_kl(p_c, q_c, q_off):
        return kl(p_c, q_c) + OFF * math.log(off_tok / q_off)

    marg = [(1 - OFF) / m] * m
    if mode == "label_prior":
        gold = dist(m, 0, a, off_tok)  # one favoured label, same for every probe of the episode
        shuf = dist(m, 1, a, off_tok)  # labels re-drawn: a different favoured label
        kl_shift = 0.0  # the shift reproduces GOLD exactly
        kl_ld = full_kl(gold, shuf, off_tok)
        kl_s0 = full_kl(gold, zs, zs_off)
        kl_const = full_kl(gold, marg, off_tok)  # the family constant cannot know the episode's favoured label
    else:
        kl_shift = kl_const = kl_s0 = kl_ld = 0.0
        for y in range(m):  # probes with every correct answer, equally often
            gold = dist(m, y, a, off_tok)
            if mode == "flat":
                shuf = marg
            else:
                wrong = dist(m, (y + 1) % m, a, off_tok)
                shuf = wrong if mode == "follow" else [0.5 * u + 0.5 * v for u, v in zip(wrong, marg)]
            kl_shift += full_kl(gold, marg, off_tok) / m
            kl_const += full_kl(gold, marg, off_tok) / m
            kl_s0 += full_kl(gold, zs, zs_off) / m
            kl_ld += full_kl(gold, shuf, off_tok) / m
    old_ratio = kl_const / kl_s0
    new_ratio = kl_shift / kl_ld if kl_ld > 0 else float("inf")
    return {"m": m, "accuracy": a, "zero_shot_candidate_mass": s, "shuf_mode": mode,
            "KL_const_over_KL_S0": round(old_ratio, 4), "old_guard_reads_EPISODE_CONSTANT": bool(old_ratio < 0.20),
            "KL_shift_over_KL_LD": round(new_ratio, 4), "new_guard_reads_EPISODE_CONSTANT": bool(new_ratio < 0.10)}


def main() -> int:
    rows = []
    for m in (2, 3, 4, 6, 8):
        for a in (0.45, 0.60, 0.75, 0.90):
            if a < 1.0 / m + 0.10 or a > 0.95:
                continue  # not label-dependent enough to be eligible in Step 1
            for s in (0.05, 0.2, 0.4):
                for mode in ("flat", "half", "follow", "label_prior"):
                    rows.append(family(m, a, s, mode))
    dep = [r for r in rows if r["shuf_mode"] != "label_prior"]
    lp = [r for r in rows if r["shuf_mode"] == "label_prior"]
    summary = {
        "label_dependent_settings": len(dep),
        "old_guard_false_EPISODE_CONSTANT": sum(r["old_guard_reads_EPISODE_CONSTANT"] for r in dep),
        "new_guard_false_EPISODE_CONSTANT": sum(r["new_guard_reads_EPISODE_CONSTANT"] for r in dep),
        "label_prior_settings": len(lp),
        "old_guard_catches_label_prior": sum(r["old_guard_reads_EPISODE_CONSTANT"] for r in lp),
        "new_guard_catches_label_prior": sum(r["new_guard_reads_EPISODE_CONSTANT"] for r in lp),
        "min_new_ratio_label_dependent": min(r["KL_shift_over_KL_LD"] for r in dep),
        "max_new_ratio_label_prior": max(r["KL_shift_over_KL_LD"] for r in lp),
    }
    payload = {"check": "E4 gate repair G1: episode-constant guards on a categorical teacher (exact)",
               "claim_boundary": "a categorical model of the teacher's answer distribution; not a model run",
               "summary": summary, "rows": rows}
    text = json.dumps(payload, indent=1, sort_keys=True)
    payload["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    with open(sys.argv[1], "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(summary, indent=1))
    for r in rows:
        if r["zero_shot_candidate_mass"] == 0.2:
            print(r["m"], r["accuracy"], r["shuf_mode"], r["KL_const_over_KL_S0"], r["KL_shift_over_KL_LD"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
