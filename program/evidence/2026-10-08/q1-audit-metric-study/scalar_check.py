"""Q1 audit-metric study, revision 2: scalar outputs (the critique's second point), synthetic, CPU.

A scalar output (a loss, a global mean) has one element, so ``rho_inf`` is the ratio of
two independent rounding errors and is heavy-tailed. This draws fresh U[0,1) vectors
of 2^24 elements (no problem module, no evaluation unit), takes the mean in fp64 as the
oracle, and scores correct fp32 reductions in several orders against yardsticks:

* ``Y2``: CPU ``mean`` and a 4096-block tree (stand-ins for the CPU and device fp32
  references, as in the critique);
* ``Y2+seq``: ``Y2`` plus an emulated worst-valid-order member (4096-element blocks,
  then one sequential accumulator over the block sums).

Candidates: a 1024-block tree (as accurate as the yardstick), two-stage reductions with
a sequential second stage (2048- and 8192-element blocks), and the same with the block
sums added in a random order (atomics). Reported: P(rho_inf > 4), > 16, > 64, and the
largest value, with the rule's absolute floor (2^-24 |r|).

Usage: python scalar_check.py --trials 200 --out scalar-check.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

N = 1 << 24
FLOOR_REL = 2.0**-24


def two_stage(x: torch.Tensor, block: int, perm: torch.Tensor | None = None) -> float:
    """Block sums (stage 1), then one fp32 accumulator over them in order (stage 2)."""
    parts = x.view(-1, block).sum(1)
    if perm is not None:
        parts = parts[perm]
    acc = np.float32(0.0)
    for p in parts.numpy():
        acc = np.float32(acc + p)
    return float(np.float32(acc / np.float32(N)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "scalar-check.json"))
    a = ap.parse_args()
    torch.set_num_threads(8)
    names = ["tree1024", "two_stage_2048_seq", "two_stage_8192_seq", "two_stage_2048_random_order"]
    ratios: dict[str, dict[str, list[float]]] = {y: {n: [] for n in names} for y in ("Y2", "Y2+seq")}
    for s in range(a.trials):
        g = torch.Generator().manual_seed(1000 + s)
        x = torch.rand(N, generator=g)
        r = float(x.double().mean())
        y_cpu = float(x.mean())
        y_dev = float(x.view(-1, 4096).sum(1).sum() / N)
        y_seq = float(two_stage(x, 4096))
        perm = torch.randperm(N // 2048, generator=g)
        cands = {
            "tree1024": float(x.view(-1, 1024).sum(1).view(-1, 64).sum(1).sum() / N),
            "two_stage_2048_seq": float(two_stage(x, 2048)),
            "two_stage_8192_seq": float(two_stage(x, 8192)),
            "two_stage_2048_random_order": float(two_stage(x, 2048, perm)),
        }
        floor = FLOOR_REL * abs(r)
        for yname, ys in (("Y2", [y_cpu, y_dev]), ("Y2+seq", [y_cpu, y_dev, y_seq])):
            ninf = max(max(abs(y - r) for y in ys), floor)
            for n, c in cands.items():
                ratios[yname][n].append(abs(c - r) / ninf)
    out = {"trials": a.trials, "n": N, "floor_rel": FLOOR_REL, "results": {}}
    for yname, per in ratios.items():
        for n, v in per.items():
            v = sorted(v)
            out["results"].setdefault(yname, {})[n] = {
                "P_gt_4": sum(x > 4 for x in v) / len(v), "P_gt_16": sum(x > 16 for x in v) / len(v), "P_gt_64": sum(x > 64 for x in v) / len(v),
                "median": v[len(v) // 2], "p90": v[int(0.9 * len(v))], "max": v[-1],
            }
            d = out["results"][yname][n]
            print(yname.ljust(7), n.ljust(28), "P>4 %.3f P>16 %.3f P>64 %.3f median %.2f p90 %.2f max %.3g" % (d["P_gt_4"], d["P_gt_16"], d["P_gt_64"], d["median"], d["p90"], d["max"]))
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
