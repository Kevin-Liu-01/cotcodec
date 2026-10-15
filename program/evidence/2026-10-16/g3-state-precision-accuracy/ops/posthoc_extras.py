#!/usr/bin/env python3
"""G3 post-hoc descriptive extras (EXPLORATORY, CPU, from the committed text-free per-request
file): paired length comparisons against fp32 on the same (question, seed), with an exact
two-sided sign test as in G2b; and the math accuracy among rollouts that ended with EOS in both
arms of a pair. Usage: posthoc_extras.py <data/per-request.jsonl.gz> <out.json>"""

from __future__ import annotations

import gzip
import json
import math
import sys


def sign_p(a: int, b: int) -> float:
    n, k = a + b, min(a, b)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def main() -> None:
    rows = [json.loads(line) for line in gzip.open(sys.argv[1], "rt")]
    out: dict = {}
    for model in sorted({r["model"] for r in rows}):
        m = {(r["arm"], r["request_id"]): r for r in rows if r["model"] == model and r["task"] == "math"}
        ids = sorted({rid for arm, rid in m if arm == "fp32"})
        for arm in ("fp16", "bf16"):
            longer = shorter = tie = 0
            both_eos = both_eos_ok_arm = both_eos_ok_ref = 0
            for rid in ids:
                a, f = m[(arm, rid)], m[("fp32", rid)]
                capped_a, capped_f = a["finish_reason"] != "stop", f["finish_reason"] != "stop"
                if capped_a and capped_f:
                    tie += 1
                elif capped_a or (not capped_f and a["completion_len"] > f["completion_len"]):
                    longer += 1
                elif capped_f or a["completion_len"] < f["completion_len"]:
                    shorter += 1
                else:
                    tie += 1
                if not capped_a and not capped_f:
                    both_eos += 1
                    both_eos_ok_arm += a["correct"]
                    both_eos_ok_ref += f["correct"]
            out[f"{model}/{arm}_vs_fp32"] = {
                "pairs": len(ids), "arm_longer": longer, "arm_shorter": shorter, "ties": tie,
                "sign_test_p": sign_p(longer, shorter),
                "both_ended_eos": both_eos,
                "accuracy_both_eos_arm": both_eos_ok_arm / both_eos if both_eos else None,
                "accuracy_both_eos_fp32": both_eos_ok_ref / both_eos if both_eos else None,
            }  # fmt: skip
    with open(sys.argv[2], "w") as handle:
        json.dump(out, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
