#!/usr/bin/env python3
"""Planning counts for the Stage 0 cost projection (CPU, GPU-less container).

Rebuilds the substrate corpus from recorded TorchInductor codegen records (the
mock-H100 dry-run records, or device records when they exist) plus the S2
build, then, for every evaluation-set substrate (S1-eval and S2), counts the
CPU-distinct mutant candidates (the mutator's ``pool``) and the applicable
hack-emulating controls. These are the denominators the pilot cost card
multiplies; they are planning counts (no admission, no compile filter), and
the card scales the mutant pool by the compile-filter survival the pilot
measured.

    python scripts/q1_stage0_counts.py --records RECORDS --work W --out counts.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import pilot  # noqa: E402
from harness.q1.schema import iter_kernel_dirs, parse_problem_id  # noqa: E402


def stratum_of(source_kind: str, problem_id: str) -> str:
    if source_kind != "inductor":
        return "S2"
    return f"S1-L{parse_problem_id(problem_id)[0]}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    from harness.q1 import controls as core_controls
    from harness.q1 import problems
    from harness.q1.mutate import corpus
    from harness.q1.substrates import split as s1_split
    from scripts.q1_build_substrates import main as build_main

    if args.work.exists():
        print(f"error: {args.work} exists", file=sys.stderr)
        return 2
    subs = args.work / "substrates"
    kb = str(PROJECT_ROOT / "harness" / "q1" / "third_party" / "kernelbench" / "problems")
    records = args.work / "records"
    shutil.copytree(args.records, records)
    for step in (
        ["s1-convert", "--records-dir", str(records), "--out-root", str(subs)],
        ["s2-build", "--kernelbench-root", kb, "--out-root", str(subs)],
    ):
        build_main(step)
    split = s1_split.calibration_split(problems.list_problem_ids(include_excluded=True), seed=42)
    evaluation_problems = set(split["evaluation"])
    evaluation = args.work / "evaluation-substrates"
    evaluation.mkdir()
    calibration: list[str] = []
    for kernel in iter_kernel_dirs(subs):
        kind = kernel.substrate["source_kind"]
        if kind != "inductor" or kernel.problem_id in evaluation_problems:
            shutil.copytree(kernel.path, evaluation / kernel.kernel_id)
        else:
            calibration.append(kernel.kernel_id)
    pool_manifest = corpus.build_pool(evaluation, args.work / "pool")
    controls_manifest = corpus.build_controls(evaluation, None, args.work / "controls")
    hacks = Counter(row["control_id"].split(".", 1)[0] for row in controls_manifest["controls"])
    by_family: dict[str, Counter] = {}
    for line in (args.work / "pool" / "pool.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            by_family.setdefault(row["parent_substrate_id"], Counter())[row["family"]] += 1
    rows = []
    for summary in pool_manifest["substrates"]:
        kernel = next(
            k for k in iter_kernel_dirs(evaluation) if k.kernel_id == summary["substrate_id"]
        )
        kind = kernel.substrate["source_kind"]
        rows.append(
            {
                "substrate_id": kernel.kernel_id,
                "problem_id": kernel.problem_id,
                "source_kind": kind,
                "stratum": stratum_of(kind, kernel.problem_id),
                "level": parse_problem_id(kernel.problem_id)[0],
                "cpu_distinct": summary["enumeration"]["distinct"],
                "cpu_distinct_by_family": dict(sorted(by_family.get(kernel.kernel_id, {}).items())),
                "hack_controls": hacks.get(kernel.kernel_id, 0),
                "native_input_bytes": pilot.native_input_bytes(kernel.problem_id),
                "exclusive": pilot.exclusive_problem(kernel.problem_id),
            }
        )
    identity_rows = [
        {
            "problem_id": pid,
            "level": parse_problem_id(pid)[0],
            "exclusive": pilot.exclusive_problem(pid),
        }
        for pid in core_controls.identity_problems()
    ]
    result = {
        "schema": "q1-stage0-counts/1",
        "records": str(args.records),
        "s1_split_sha256": split["sha256"],
        "evaluation_substrates": rows,
        "calibration_substrates": sorted(calibration),
        "identity_controls": identity_rows,
        "adversarial_controls": 3,
        "hack_emulating_mutant_controls": 5,
        "totals": {
            "evaluation_substrates": dict(Counter(r["stratum"] for r in rows)),
            "calibration_substrates": len(calibration),
            "cpu_distinct": sum(r["cpu_distinct"] for r in rows),
            "capped_at_40_upper_bound": sum(min(40, r["cpu_distinct"]) for r in rows),
            "hack_controls": sum(r["hack_controls"] for r in rows),
            "identity_controls": len(identity_rows),
        },
    }
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps(result["totals"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
