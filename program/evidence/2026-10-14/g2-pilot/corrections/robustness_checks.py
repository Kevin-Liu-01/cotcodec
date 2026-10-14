#!/usr/bin/env python3
"""Checks behind the corrected G2 pilot reading (EXPLORATORY; CPU only).

For the rollout-vs-trainer comparison (dec vs r1), all seeds, per model:

* ``entropy_quantile_slopes``: the analysis controls entropy with six fixed bins, and a slope
  within coarse bins could come from entropy drifting inside a bin. This recomputes the
  position slope with entropy quantile bins (6, 20 and 50), pooled across sequences
  (entropy-bin fixed effects) and within sequences (sequence-by-entropy-bin fixed effects),
  with the same estimators and bootstrap as scripts/analyze_g2_pilot.py (2,000 draws over
  sequences, seed 42).
* ``early_rise``: how many sequences have a higher mean |d|, and a higher mean r1 entropy, in
  the third 1K position bin (2,048-3,071) than in the first (every sequence covers both);
  and how many sequences reach each 1K bin (composition with position).
* ``calibration``: mean -log p_dec of the sampled tokens against the mean r1 entropy. For
  untruncated T = 1 sampling the two should agree.

Run from the repository root:

    uv run --locked python \\
      program/evidence/2026-10-14/g2-pilot/corrections/robustness_checks.py \\
      --per-token program/evidence/2026-10-14/g2-pilot/data/per-token.npz
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]


def per_seq_mean(seq: np.ndarray, mask: np.ndarray, values: np.ndarray, n_seq: int) -> np.ndarray:
    n = np.bincount(seq[mask], minlength=n_seq)
    s = np.bincount(seq[mask], weights=values[mask], minlength=n_seq)
    return np.where(n > 0, s / np.maximum(n, 1), np.nan)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--per-token", required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("an", ROOT / "scripts" / "analyze_g2_pilot.py")
    an = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(an)
    out: dict[str, dict[str, object]] = {}
    for model_id, data in an.load_per_token(Path(args.per_token)).items():
        offsets = data["offsets"]
        n_seq = len(offsets) - 1
        seq = np.repeat(np.arange(n_seq), np.diff(offsets))
        dec = an.path_logp(data, "dec")
        absd = np.abs(dec - an.path_logp(data, "r1"))
        position = data["position"].astype(np.int64)
        x = position / 1000.0
        entropy = data["ent_r1"].astype(np.float64)
        slopes = {}
        for quantiles in (6, 20, 50):
            cuts = np.quantile(entropy, np.linspace(0, 1, quantiles + 1)[1:-1])
            groups = np.searchsorted(cuts, entropy, side="right")
            pooled = an.within_bin_slope(seq, groups, x, absd, n_seq, 2000, 42)
            within = an.within_sequence_slope(seq, groups, x, absd, n_seq, 2000, 42)
            slopes[f"{quantiles}_quantile_bins"] = {
                "within_entropy_bins": [float(v) for v in pooled],
                "within_sequence_x_entropy_bin": [float(v) for v in within],
            }
        bins = position // 1024
        d0, d2 = (per_seq_mean(seq, bins == b, absd, n_seq) for b in (0, 2))
        e0, e2 = (per_seq_mean(seq, bins == b, entropy, n_seq) for b in (0, 2))
        both = np.isfinite(d0) & np.isfinite(d2)
        out[model_id] = {
            "comparison": "dec_vs_r1",
            "subset": "all_seeds",
            "entropy_quantile_slopes_per_1k": slopes,
            "early_rise": {
                "sequences_covering_bins_0_and_2": int(both.sum()),
                "higher_mean_abs_in_bin_2_than_bin_0": int((d2[both] > d0[both]).sum()),
                "higher_mean_entropy_in_bin_2_than_bin_0": int((e2[both] > e0[both]).sum()),
                "sequences_per_1k_bin": [
                    int(len(np.unique(seq[bins == b]))) for b in range(int(bins.max()) + 1)
                ],
            },
            "calibration": {
                "mean_neg_logp_decode": float(-dec.mean()),
                "mean_entropy_r1": float(entropy.mean()),
            },
        }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
