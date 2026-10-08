#!/usr/bin/env python3
"""Combine the lane receipts of q3-dense-headroom-precheck-v2 into its read.

CPU only, no torch. v1's void rules, applied by v1's own functions
(``scripts/summarise_dense_headroom_precheck.py``: ``check_job``,
``lane_usage``, ``orx_results``, imported unchanged) to the job that wrote
each receipt, from the files beside it: ``termination.env`` completed with
exit code 0; provenance PASS for the job's git SHA and source SHA-256, which
are the receipt's; the job's ``ORX_RESULT ... job=<N> exit=0`` line in a
saved orx log; the receipt's ``slurm_job_id`` is its job directory (v2's
entry point records it from ``job.env``); every job of the lane ended,
exactly one holds a receipt, a continuation follows a confirmed signal
checkpoint and is recorded; the lane's jobs ran within its minutes; every
job ran on its own fill claim.

v2 adds the registered validity gate (D36): the Qwen3-0.6B-Base lane must
reproduce v1's job-727 receipt statistics (``harness.dense_headroom_v2.
v1_reproduction``: every numeric leaf of the registered fields to 1e-6, every
other leaf exactly, the same development artifact). A lane that does not is
INVALID, and so is the combined read, under v1's rule for a failed K1 smoke
reproduction (decision 11): the shared code path no longer reproduces the
measurement. v1's job-727 receipt is reported beside v2's.

The combined read is v1's rule (``harness.dense_headroom_stats.
combined_recommendation``): INVALID first, then INCOMPLETE when a lane has no
completed, non-void receipt, otherwise the K1 v3 designs the measured dense
headroom supports, on which base, with D26's requirements.

Exit codes: 0 written, 2 an input is missing, inconsistent or void.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import dense_headroom_data as dhd  # noqa: E402
from harness import dense_headroom_stats as dhs  # noqa: E402
from harness import dense_headroom_v2 as dv2  # noqa: E402
from harness import dense_headroom_v2_lanes as lanes  # noqa: E402
from scripts import preregister  # noqa: E402
from scripts import summarise_dense_headroom_precheck as v1s  # noqa: E402

SummaryError = v1s.SummaryError
SMALL_LANE = "qwen3-0.6b-base"


def load_receipts(paths: list[Path], orx_logs: list[Path]) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    orx_jobs = v1s.orx_results(orx_logs)
    for path in paths:
        raw = path.read_bytes()
        receipt = json.loads(raw)
        lane_id = (receipt.get("lane") or {}).get("lane_id")
        if receipt.get("experiment_id") != dv2.EXPERIMENT_ID:
            raise SummaryError(f"{path}: not a {dv2.EXPERIMENT_ID} receipt")
        if receipt.get("status") != "PRECHECK_COMPLETE":
            raise SummaryError(f"{path}: lane {lane_id} is {receipt.get('status')}")
        if lane_id not in lanes.LANES or receipt.get("profile") != "registered":
            raise SummaryError(f"{path}: {lane_id!r} is not a registered lane")
        if lane_id in receipts:
            raise SummaryError(f"two receipts for lane {lane_id}")
        if receipt.get("slurm_job_id_source") != "job.env":
            raise SummaryError(f"{path}: the receipt's Slurm job was not bound from job.env")
        job = v1s.check_job(path, receipt, lanes.LANES[lane_id], orx_jobs)
        receipts[lane_id] = {"receipt": receipt, "receipt_sha256": hashlib.sha256(raw).hexdigest(),
                             "job": job}
    return receipts


def v1_gate(receipts: dict[str, dict[str, Any]], root: Path) -> dict[str, Any] | None:
    """The validity gate on the 0.6B lane against v1's job-727 receipt, or None
    when the 0.6B lane has no receipt."""

    if SMALL_LANE not in receipts:
        return None
    v1_receipt = dv2.load_v1_small_lane_receipt(root)
    return dv2.v1_reproduction(receipts[SMALL_LANE]["receipt"], v1_receipt)


def summarise(receipts: dict[str, dict[str, Any]], *, ledger: Path, root: Path,
              run_roots: dict[str, Path] | None = None) -> dict[str, Any]:
    reads = {lane: entry["receipt"] for lane, entry in receipts.items()}
    prereg = {r["hashes"]["preregistration_sha256"] for r in reads.values()}
    bundles = {r["hashes"]["bundle_sha256"] for r in reads.values()}
    if len(prereg) > 1 or len(bundles) > 1:
        raise SummaryError("the lanes were read against different registrations or bundles")
    row = preregister.verify(dv2.EXPERIMENT_ID, ledger=ledger, root=root)
    if reads and row["sha256"] not in prereg:
        raise SummaryError("the lanes' preregistration is not the frozen one")
    if reads and bundles != {dhd.SOURCE_BUNDLE_SHA256}:
        raise SummaryError("the lanes did not read the registered K1 bundle")
    sources = {(r["hashes"].get("git_sha"), r["hashes"].get("source_sha256"))
               for r in reads.values()}
    if len(sources) > 1:
        raise SummaryError("the lanes ran different source revisions")
    gate = v1_gate(receipts, root)
    decisions = {lane: copy.deepcopy(r["decisions"]) for lane, r in reads.items()}
    if gate is not None and gate["status"] != "REPRODUCED":
        decisions[SMALL_LANE]["lane_class"] = "INVALID"
    usage: dict[str, Any] = {}
    for lane_id in lanes.REGISTERED_ORDER:
        if lane_id in receipts:
            usage[lane_id] = receipts[lane_id]["job"]["usage"]
        elif run_roots and lane_id in run_roots:
            usage[lane_id] = v1s.lane_usage(lanes.LANES[lane_id], run_roots[lane_id],
                                            strict=False)
        else:
            usage[lane_id] = None
    v1_receipt = dv2.load_v1_small_lane_receipt(root)
    return {
        "experiment_id": dv2.EXPERIMENT_ID,
        "preregistration_sha256": row["sha256"],
        "v1_job_727_reproduction": gate,
        "combined": dhs.combined_recommendation(decisions),
        "lanes": {lane: {"decisions": entry["receipt"]["decisions"],
                         "lane_class_for_combined_read": decisions[lane]["lane_class"],
                         "slurm_job_id": entry["job"]["job_id"],
                         "predecessor_job_id": entry["job"]["predecessor_job_id"],
                         "dev_artifact_sha256": entry["receipt"]["hashes"].get(
                             "dev_artifact_sha256"),
                         "receipt_sha256": entry["receipt_sha256"]}
                  for lane, entry in sorted(receipts.items())},
        "v1_small_lane_reported_beside": {
            "experiment_id": dv2.V1_EXPERIMENT_ID, "slurm_job_id": dv2.V1_SMALL_LANE_JOB,
            "receipt": dv2.V1_SMALL_LANE_RECEIPT,
            "receipt_sha256": dv2.V1_SMALL_LANE_RECEIPT_SHA256,
            "decisions": v1_receipt["decisions"]},
        "gpu_usage": usage,
        "gpu_hours_used": sum(u["gpu_hours_used"] for u in usage.values() if u),
    }


def _run_root(value: str) -> tuple[str, Path]:
    lane, separator, path = value.partition("=")
    if not separator or lane not in lanes.LANES:
        raise argparse.ArgumentTypeError("--run-root takes LANE=PATH for a registered lane")
    return lane, Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("receipts", type=Path, nargs="*")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--orx-log", type=Path, action="append", default=[],
                        help="a saved orx log of a lane job's node (repeatable)")
    parser.add_argument("--run-root", type=_run_root, action="append", default=[],
                        help="LANE=PATH: the run root of a lane without a receipt")
    parser.add_argument("--ledger", type=Path, default=preregister.DEFAULT_LEDGER)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"FAIL: {args.output} exists; never overwrite", file=sys.stderr)
        return 2
    try:
        summary = summarise(load_receipts(args.receipts, args.orx_log), ledger=args.ledger,
                            root=args.root, run_roots=dict(args.run_root))
    except (OSError, KeyError, ValueError, json.JSONDecodeError,
            preregister.PreregistrationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["combined"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
