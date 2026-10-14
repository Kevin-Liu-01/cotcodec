#!/usr/bin/env python3
"""Robustness check for the corrected G2 pilot reading (EXPLORATORY; CPU only).

The analysis controls entropy with six fixed bins. A slope within coarse bins could come from
entropy drifting inside a bin, so this recomputes the rollout-vs-trainer (dec vs r1) position
slope, all seeds, with entropy quantile bins (6, 20 and 50), both pooled across sequences
(entropy-bin fixed effects) and within sequences (sequence-by-entropy-bin fixed effects).
Same estimators and bootstrap as scripts/analyze_g2_pilot.py (2,000 draws over sequences,
seed 42). Run from the repository root:

    uv run --locked python program/evidence/2026-10-14/g2-pilot/corrections/finer_entropy_check.py \
      --per-token program/evidence/2026-10-14/g2-pilot/data/per-token.npz
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]


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
        absd = np.abs(an.path_logp(data, "dec") - an.path_logp(data, "r1"))
        x = data["position"].astype(np.int64) / 1000.0
        entropy = data["ent_r1"].astype(np.float64)
        rows = {}
        for quantiles in (6, 20, 50):
            cuts = np.quantile(entropy, np.linspace(0, 1, quantiles + 1)[1:-1])
            groups = np.searchsorted(cuts, entropy, side="right")
            pooled = an.within_bin_slope(seq, groups, x, absd, n_seq, 2000, 42)
            within = an.within_sequence_slope(seq, groups, x, absd, n_seq, 2000, 42)
            rows[f"{quantiles}_quantile_bins"] = {
                "within_entropy_bins": [float(v) for v in pooled],
                "within_sequence_x_entropy_bin": [float(v) for v in within],
            }
        out[model_id] = {"comparison": "dec_vs_r1", "subset": "all_seeds", "slopes_per_1k": rows}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
