#!/usr/bin/env python3
"""Summarize the Q1 pilot jobs' verdicts for the evidence record (CPU).

Reads the pilot job's driver output (``<run_dir>/q1``) and writes one JSON
document with: the smoke checks (expected verdicts of the reference-identity
control and the cached-output control), the fidelity comparison of each gate
with the unmodified upstream run on the same kernel (gate (a) with KernelBench
@44130946, ``a_head_1e-4`` with @423217d9, ``b`` with KernelGYM's
``eval_kernel_against_ref``, ``c1`` in KBV-compatibility mode with KBV's
``run_hidden_correctness_check`` per configuration), the calibration record,
and the verdict counts of the scored items by gate and kernel role.

    python scripts/q1_pilot_evidence.py --job RUNS/NNN --corpus PREP/corpus --out evidence.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import cost_card as cc  # noqa: E402

IDENTITY_EXPECT = {
    "a": "accept",
    "a_1e-3": "accept",
    "a_head_1e-4": "accept",
    "a_head_1e-2": "accept",
    "a_static": None,
    "b1": "reject",
    "b2": "reject",
    "A1": "accept",
    "A2": "accept",
    "A4": "accept",
    "A4_poison": "accept",
    "A4_sanitizer": "accept",
}


def rows_of(root: Path, phase: str) -> list[dict[str, Any]]:
    path = root / phase / "journal.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    final = {}
    for row in rows:
        key = (row["details"]["item_key"], row["gate"], row["config_id"])
        final[key] = row
    return list(final.values())


def headline(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    """One verdict per (kernel, gate, seed): the aggregate row, else the single row."""
    out: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in rows:
        key = (row["kernel_id"], row["gate"], row.get("seed") or 42)
        if row["config_id"] == "aggregate" or key not in out:
            if key in out and out[key]["config_id"] == "aggregate":
                continue
            out[key] = row
    return out


def verdict(table: dict, kernel: str, gate: str, seed: int = 42) -> str | None:
    row = table.get((kernel, gate, seed))
    return None if row is None else row["verdict"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.job / "q1"
    kinds = cc.classify(args.corpus)
    phases = ("smoke", "smoke-timing", "fidelity", "calibration", "scoring", "timing")
    rows = {phase: rows_of(root, phase) for phase in phases}
    every = [r for phase in phases for r in rows[phase]]
    table = headline(every)

    smoke = []
    identity = sorted({r["kernel_id"] for r in rows["smoke"] if r["kernel_id"].startswith("ctl-")})
    for kernel in identity:
        for gate, expected in IDENTITY_EXPECT.items():
            got = verdict(table, kernel, gate)
            smoke.append(
                {
                    "kernel": kernel,
                    "gate": gate,
                    "expected": expected,
                    "got": got,
                    "ok": None if expected is None or got is None else got == expected,
                }
            )
        for gate in ("c", "c1", "c2", "c3", "A3", "A5"):
            smoke.append(
                {
                    "kernel": kernel,
                    "gate": gate,
                    "expected": None,
                    "got": verdict(table, kernel, gate),
                    "ok": None,
                }
            )
    retry = []
    for row in rows["smoke"]:
        if row["gate"] == "b2":
            retry.append(
                {
                    "kernel": row["kernel_id"],
                    "verdict": row["verdict"],
                    "profile_attempts": row["details"].get("profile_attempts"),
                    "details": {
                        k: row["details"].get(k)
                        for k in (
                            "reason",
                            "b0_calls_replayed",
                            "event_rows",
                            "retried",
                            "custom_kernels",
                            "total_kernels",
                        )
                    },
                }
            )

    fidelity: list[dict[str, Any]] = []
    kernels = sorted({r["kernel_id"] for r in rows["fidelity"]})
    for kernel in kernels:
        entry: dict[str, Any] = {"kernel": kernel, "role": kinds.get(kernel, {}).get("role")}
        ours_a, up_a = verdict(table, kernel, "a"), verdict(table, kernel, "a_upstream_44130946")
        ours_h, up_h = (
            verdict(table, kernel, "a_head_1e-4"),
            verdict(table, kernel, "a_upstream_423217d9"),
        )
        entry["a_vs_44130946"] = {
            "ours": ours_a,
            "upstream": up_a,
            "agree": None if None in (ours_a, up_a) else ours_a == up_a,
        }
        head_row = table.get((kernel, "a_head_1e-4", 42))
        listed = (
            ours_h == "error"
            and head_row is not None
            and head_row["details"].get("reason") == "reference-raised"
            and up_h == "reject"
        )
        entry["a_head_1e-4_vs_423217d9"] = {
            "ours": ours_h,
            "upstream": up_h,
            "agree": None if None in (ours_h, up_h) else ours_h == up_h,
            "listed_in_advance": listed,
        }
        b1, b2 = verdict(table, kernel, "b1"), verdict(table, kernel, "b2")
        native = table.get((kernel, "b_native", 42))
        if native is not None:
            d = native["details"]
            ours_decoy = None if None in (b1, b2) else (b1 == "reject" or b2 == "reject")
            entry["b_vs_kernelgym"] = {
                "ours_b1": b1,
                "ours_b2": b2,
                "ours_decoy": ours_decoy,
                "upstream_decoy": d.get("decoy_kernel"),
                "upstream_b0_correct": d.get("b0_correctness"),
                "ours_a": ours_a,
                "upstream_verdict": native["verdict"],
                # KernelGYM runs b1 only after b0 passes and b2 only when b1 found no
                # decoy, so detection is comparable only on b0-correct items.
                "decoy_agree": None
                if ours_decoy is None
                or d.get("decoy_kernel") is None
                or not d.get("b0_correctness")
                else ours_decoy == bool(d.get("decoy_kernel")),
                "decoy_not_comparable": "upstream skips detection when b0 fails"
                if d.get("b0_correctness") is False
                else None,
                "b0_vs_a_agree": None
                if ours_a is None or d.get("b0_correctness") is None
                else (ours_a == "accept") == bool(d.get("b0_correctness")),
                "upstream_reason": d.get("reason"),
            }
        compat = {
            r["config_id"]: r["verdict"]
            for r in rows["fidelity"]
            if r["kernel_id"] == kernel and r["gate"] == "c1_kbv_compat"
        }
        raw_aggregate = next(
            (
                r["verdict"]
                for r in rows["fidelity"]
                if r["kernel_id"] == kernel
                and r["gate"] == "c1_kbv_compat_raw"
                and r["config_id"] == "aggregate"
            ),
            None,
        )
        native_rows = [
            r for r in rows["fidelity"] if r["kernel_id"] == kernel and r["gate"] == "c1_kbv_native"
        ]
        if compat and native_rows:
            ordered_ours = [
                r
                for r in rows["fidelity"]
                if r["kernel_id"] == kernel
                and r["gate"] == "c1_kbv_compat"
                and r["config_id"] != "aggregate"
            ]
            ours_list = [
                "accept"
                if r["verdict"] == "accept" or r["details"].get("reference_raised")
                else "reject"
                for r in ordered_ours
            ]
            theirs = [r["verdict"] for r in native_rows if r["config_id"] != "aggregate"]
            native_agg = next((r for r in native_rows if r["config_id"] == "aggregate"), None)
            entry["c1_kbv_compat_vs_native"] = {
                "ours_per_config": ours_list,
                "kbv_per_config": theirs,
                "agree_per_config": ours_list == theirs,
                "ours_aggregate_validity_filtered": compat.get("aggregate"),
                "ours_aggregate_kbv_raw": raw_aggregate,
                "kbv_aggregate": None if native_agg is None else native_agg["verdict"],
                "kbv_problem_equals_ours": None
                if native_agg is None
                else native_agg["details"].get("kbv_problem_equals_ours_after_header"),
                "kbv_reason": None if native_agg is None else native_agg["details"].get("reason"),
            }
        fidelity.append(entry)

    def tally(name: str) -> dict[str, Any]:
        counts: dict[str, Counter] = defaultdict(Counter)
        for row in rows[name]:
            if row["config_id"] == "aggregate" or row["config_id"].startswith(("item", "native")):
                counts[row["gate"]][row["verdict"]] += 1
        return {gate: dict(c) for gate, c in sorted(counts.items())}

    calibration = None
    if (root / "audit-calibration.json").exists():
        calibration = json.loads((root / "audit-calibration.json").read_text())
    agreements = Counter()
    for entry in fidelity:
        for key in ("a_vs_44130946", "a_head_1e-4_vs_423217d9"):
            label = entry[key]["agree"]
            if entry[key].get("listed_in_advance"):
                label = "listed-in-advance"
            agreements[f"{key}:{label}"] += 1
        if "b_vs_kernelgym" in entry:
            agreements[f"b_decoy:{entry['b_vs_kernelgym']['decoy_agree']}"] += 1
            agreements[f"b0_vs_a:{entry['b_vs_kernelgym']['b0_vs_a_agree']}"] += 1
        if "c1_kbv_compat_vs_native" in entry:
            agreements[f"c1_per_config:{entry['c1_kbv_compat_vs_native']['agree_per_config']}"] += 1
    document = {
        "schema": "q1-pilot-evidence/1",
        "job": str(args.job),
        "smoke_checks": smoke,
        "smoke_checks_failed": [c for c in smoke if c["ok"] is False],
        "b2_rows": retry,
        "fidelity": fidelity,
        "fidelity_agreement_counts": dict(agreements),
        "calibration": calibration,
        "verdict_counts": {name: tally(name) for name in phases},
        "phases": json.loads((root / "phases.json").read_text()),
    }
    args.out.write_text(json.dumps(document, indent=1, sort_keys=True, default=str))
    print(
        json.dumps(
            {
                "fidelity_agreement_counts": dict(agreements),
                "smoke_failed": len(document["smoke_checks_failed"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
