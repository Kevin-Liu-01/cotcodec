#!/usr/bin/env python3
"""Compare the K1 fresh-job resume legs: uninterrupted R0 versus resumed R2.

R0 trains to ``--stop-after-step`` without interruption. R1 holds after a step
until the Slurm time-limit signal, saves on that signal and exits 75. R2 is a
fresh job resumed from R1's checkpoints and trains to the same step. The resume
is equivalent only if every worker's final state digest (parameters, Adam
moments and step counters) and every indexer's parameter digest in R2 equal
R0's bit for bit, and R1 terminated through a confirmed signal checkpoint.

Exit codes: 0 equivalent, 1 not equivalent, 2 unreadable input.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.sparse_indexer_k1_marker import read_checkpoint_marker  # noqa: E402


def _receipt(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "phase-0a-k1" / "receipt.json").read_text(encoding="utf-8"))


def _termination(run_dir: Path) -> dict[str, str]:
    path = run_dir / "termination.env"
    pairs = [line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines() if "=" in
             line]
    return {key: value for key, value in pairs}


def compare(r0: Path, r1: Path, r2: Path) -> dict[str, Any]:
    reference, resumed = _receipt(r0), _receipt(r2)
    report: dict[str, Any] = {"r0": str(r0), "r1": str(r1), "r2": str(r2), "checks": {}}
    checks = report["checks"]
    checks["same_stop_step"] = reference["stop_after_step"] == resumed["stop_after_step"]
    checks["final_state_digests_equal"] = (
        reference["final_state_digests"] == resumed["final_state_digests"])
    ref_params = {str(w["worker"]): w["param_digests"] for w in reference["workers"]}
    res_params = {str(w["worker"]): w["param_digests"] for w in resumed["workers"]}
    checks["param_digests_equal"] = ref_params == res_params
    checks["r2_resumed"] = all(w.get("resumed_from") is not None for w in resumed["workers"])
    termination = _termination(r1)
    checks["r1_signal_checkpoint_confirmed"] = (
        termination.get("reason") == "signal_USR1_checkpoint_confirmed"
        and termination.get("exit_code") == "75"
        and termination.get("checkpoint_ready") == "true")
    marker = read_checkpoint_marker(r1 / "checkpoint.ready")
    checks["r1_marker_has_usr1_trigger"] = marker.get("trigger") == "SIGUSR1"
    steps = {ack.get("step") for ack in marker.get("acks", {}).values()}
    checks["r1_all_workers_acknowledged_one_step"] = len(steps) == 1 and None not in steps
    report["r1_signal_step"] = sorted(s for s in steps if s is not None)
    report["r2_resumed_from"] = sorted({w.get("resumed_from") for w in resumed["workers"]},
                                       key=str)
    mismatched = sorted(
        name for worker, digests in ref_params.items() for name, digest in digests.items()
        if res_params.get(worker, {}).get(name) != digest)
    report["mismatched_indexers"] = mismatched
    report["equivalent"] = all(checks.values())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--r0", type=Path, required=True)
    parser.add_argument("--r1", type=Path, required=True)
    parser.add_argument("--r2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = compare(args.r0, args.r1, args.r2)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if args.output.exists():
        print("FAIL: output exists", file=sys.stderr)
        return 2
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"equivalent": report["equivalent"], "checks": report["checks"]}))
    return 0 if report["equivalent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
