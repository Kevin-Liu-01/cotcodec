#!/usr/bin/env python3
"""Print the Markdown summaries of power-g2rl.json that the proposal and the registration quote.

Usage: python3 sim_tables.py power-g2rl.json
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    r = json.load(open(sys.argv[1], encoding="utf-8"))
    print("FULL (5 runs per arm, no extension):")
    design = next(d for d in r["FULL"]["designs"] if d["stage1_runs_per_arm"] == 5 and d["max_runs_per_arm"] == 5)
    print("| per-run SD (points) | true B minus F | B collapse probability | CHANGES | NO_CHANGE_AT_MARGIN | INCONCLUSIVE |")
    print("|---:|---:|---:|---:|---:|---:|")
    for row in design["rows"]:
        print(
            f"| {row['sd']} | {row['effect']:+.0f} | {row['collapse_b']} | {row.get('CHANGES', 0):.2f} | "
            f"{row.get('NO_CHANGE_AT_MARGIN', 0):.2f} | {row.get('INCONCLUSIVE', 0):.2f} |"
        )
    for d in r["FULL"]["designs"]:
        sd2 = {(x["effect"], x["collapse_b"]): x for x in d["rows"] if x["sd"] == 2.0}
        print(
            f"design n1={d['stage1_runs_per_arm']} nmax={d['max_runs_per_arm']} at SD 2: "
            + "; ".join(f"eff {k[0]} col {k[1]}: CH {v.get('CHANGES', 0):.2f} NC {v.get('NO_CHANGE_AT_MARGIN', 0):.2f} runs {v['expected_runs_F_and_B']}" for k, v in sd2.items())
        )
    print()
    print("GRAD (eta 0.2):")
    print("| batches per arm | d_eff | kappa | kappa_hat 5-95% | P(perm p ≤ 0.05) | P(perm p ≤ 0.10) |")
    print("|---:|---:|---:|---|---:|---:|")
    seen = set()
    for row in r["GRAD"]["rows"]:
        if row["eta_bf16_extra_noise"] != 0.2:
            continue
        key = (row["batches_per_arm"], row["d_eff"], row["kappa_true"])
        if key in seen:
            continue
        seen.add(key)
        print(
            f"| {row['batches_per_arm']} | {row['d_eff']} | {row['kappa_true']} | "
            f"{row['kappa_hat_p5']:.3f} to {row['kappa_hat_p95']:.3f} | {row['power_perm_p_le_0.05']:.2f} | "
            f"{row['power_perm_p_le_0.10']:.2f} |"
        )
    print()
    print("TIS recovery r_hat (R = 4, eta 0.2), p10-p90:")
    for row in r["GRAD"]["rows"]:
        if row["eta_bf16_extra_noise"] == 0.2 and row["batches_per_arm"] == 4 and "tis_recovery_true" in row:
            print(
                f"d_eff {row['d_eff']} kappa {row['kappa_true']} r {row['tis_recovery_true']}: "
                f"{row['r_hat_p10']:.2f} / {row['r_hat_median']:.2f} / {row['r_hat_p90']:.2f}"
            )
    print()
    for m, v in r["MANIP"]["models"].items():
        print(m, round(v["point_ratio"], 2), {s: (round(x["ratio_p2.5"], 2), round(x["ratio_p97.5"], 2), x["P_ratio_lt_4"]) for s, x in v["by_seed"].items()},
              round(v["extra_trainer_k3_for_ratio_4"], 6), round(v["extra_trainer_k3_for_ratio_4_in_fp32_floors"], 2),
              round(v["extra_trainer_k3_for_ratio_2_in_fp32_floors"], 2))
    for row in r["MDE"]["rows"]:
        print("MDE", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
