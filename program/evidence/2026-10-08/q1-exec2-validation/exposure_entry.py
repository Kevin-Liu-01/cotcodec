#!/usr/bin/env python3
"""Exposure ledger entry for the D37 validation job (Slurm 752): which kernels it
scored, with which gates, and which split half they belong to. CPU only.

    python exposure_entry.py --run RUN752/q1 --out validation-752-exposure.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    exposure = json.loads((args.run / "exposure.json").read_text())
    journal = args.run / "validation" / "journal.jsonl"
    gates: dict[str, set[str]] = defaultdict(set)
    verdicts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for line in journal.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        kernel = row["kernel_id"].removesuffix(".inline")
        gates[kernel].add(row["details"]["item_key"].split("|")[1])
        verdicts[kernel][row["verdict"]] += 1
    kernels = []
    for entry in exposure["kernels"]:
        scored = sorted(gates.get(entry["kernel_id"], set()))
        kernels.append(
            {
                **entry,
                "gates_scored": scored,
                "verdict_rows": dict(verdicts.get(entry["kernel_id"], {})),
            }
        )
    scored = [k for k in kernels if k["gates_scored"]]
    record = {
        "schema": "q1-exposure-ledger-entry/1",
        "job": 752,
        "rule": "q1-exec2-validation/1",
        "replicate": 42,
        "journal_sha256": hashlib.sha256(journal.read_bytes()).hexdigest(),
        "s1_split_sha256": exposure.get("s1_split_sha256"),
        "kernels": kernels,
        "summary": {
            "kernels_planned": len(kernels),
            "kernels_scored": len(scored),
            "scored_s1_calibration_repilot": sum(
                1 for k in scored if k["role"] == "repilot" and k["s1_half"] == "calibration"
            ),
            "scored_s1_evaluation": sum(1 for k in scored if k["s1_half"] == "evaluation"),
            "scored_repilot_with_s2_substrate": sum(
                1 for k in scored if k["role"] == "repilot" and k["problem_has_s2_substrate"]
            ),
            "scored_adversarial_controls": sum(1 for k in scored if k["role"] == "adversarial"),
        },
        "consequence": (
            "No evaluation unit was scored. The re-pilot kernels scored here are S1-cal "
            "substrates already exposed by job 713 (no identity control or mutant was "
            "reached). The adversarial controls run on L1/1, whose problem has an S2 "
            "evaluation substrate; no S2 kernel was loaded, and the L1/1 reference items "
            "run only the KernelBench reference. The three controls were already listed "
            "in pilot_exposed.json (job 518)."
        ),
    }
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(json.dumps(record["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
