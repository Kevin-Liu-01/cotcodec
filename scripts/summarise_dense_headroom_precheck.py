#!/usr/bin/env python3
"""Combine the lane receipts of the dense headroom pre-check into its read.

CPU only, no torch. Each receipt (``<run_root>/<job>/dense-precheck/receipt.json``
on the host) must be a completed lane of ``q3-dense-headroom-precheck-v1``
(status ``PRECHECK_COMPLETE``, registered profile) read against the same frozen
preregistration and the same K1 bundle; the frozen file must still match its
ledger row. The registration's void rules are applied to the job that wrote
each receipt, from the files beside it:

* ``termination.env``: ``reason=completed``, ``exit_code=0``;
* ``provenance-verification.txt``: ``status`` PASS for the job's git SHA and
  source SHA-256 (``job.env``), which are the receipt's;
* the job's orx node printed ``ORX_RESULT kind=slurm-manifest ... job=<job>
  exit=0`` in one of the saved orx logs passed with ``--orx-log``;
* every job in the lane's run root has ended and exactly one holds a receipt;
  a continuation's predecessor ended with a confirmed signal checkpoint (exit
  75) and the receipt records that predecessor;
* the lane's jobs together ran no longer than the lane's minutes;
* every job of the lane, the first included, ran on its own fill claim
  (``<run_root>/fill-claims``, matched by the job's ``manifest.json``) and no
  longer than the claim's minutes, and no claim carries two jobs. This is the
  backstop against a filled manifest submitted twice: the entry point cannot
  see the run root from inside its container, so it cannot refuse one.

The combined read applies the registered rule
(``harness.dense_headroom_stats.combined_recommendation``): INVALID when a
lane's K1 smoke reproduction failed, INCOMPLETE when a lane has no receipt,
otherwise which K1 v3 designs the measured dense headroom supports, on which
base, with which requirements. GPU-hours are reported per lane from its run
root (``--run-root LANE=PATH`` for a lane without a receipt).

Exit codes: 0 written, 2 an input is missing, inconsistent or void.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import dense_headroom_data as dhd  # noqa: E402
from harness import dense_headroom_stats as dhs  # noqa: E402
from scripts import fill_dense_headroom_precheck_manifests as filler  # noqa: E402
from scripts import preregister  # noqa: E402


class SummaryError(ValueError):
    """A lane receipt is missing, incomplete, inconsistent or void."""


def orx_results(logs: list[Path]) -> set[str]:
    """Job ids whose orx node printed a successful slurm-manifest ORX_RESULT line."""

    pattern = re.compile(r"^ORX_RESULT kind=slurm-manifest direction=\S+ job=([0-9]+) exit=0$")
    jobs: set[str] = set()
    for log in logs:
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            match = pattern.match(line.strip())
            if match:
                jobs.add(match.group(1))
    return jobs


def lane_usage(lane: dhd.Lane, run_root: Path, *, strict: bool = True) -> dict[str, Any]:
    """Every job of the lane in its run root, with the GPU time it used. A lane
    read (``strict``) is void when its jobs together ran longer than its
    minutes, or under the claim rule (``filler.claim_problems``): a job without
    a fill claim, a job that ran longer than its claim's minutes, or two jobs on
    one claim. A lane without a receipt only reports both."""

    try:
        jobs = filler.lane_jobs(run_root)
        claims = filler.read_claims(run_root)
    except (filler.FillError, OSError, ValueError) as exc:
        raise SummaryError(f"{lane.lane_id}: {exc}") from exc
    elapsed = sum(job.elapsed_seconds for job in jobs)
    within = elapsed <= lane.minutes * 60
    if strict and not within:
        raise SummaryError(f"{lane.lane_id}: its jobs ran {elapsed:.0f} s, more than the "
                           f"lane's {lane.minutes} minutes")
    problems = filler.claim_problems(jobs, claims)
    if strict and problems:
        raise SummaryError(f"{lane.lane_id} is void: {'; '.join(problems)}")
    return {"jobs": [job.as_dict() for job in jobs], "elapsed_seconds": elapsed,
            "within_cap": within, "claim_problems": problems,
            "gpu_hours_used": lane.gpus * elapsed / 3600.0,
            "charged_minutes": filler.lane_charge(jobs), "cap_minutes": lane.minutes,
            "cap_gpu_hours": lane.cap_gpu_hours}


def check_job(path: Path, receipt: dict[str, Any], lane: dhd.Lane, orx_jobs: set[str]
              ) -> dict[str, Any]:
    """The registration's void rules for the job that wrote ``path``."""

    if path.name != "receipt.json" or path.parent.name != dhd.OUTPUT_SUBDIR:
        raise SummaryError(f"{path}: not <job>/{dhd.OUTPUT_SUBDIR}/receipt.json")
    job_dir = path.parent.parent
    job_id = job_dir.name
    if not filler.JOB_RE.fullmatch(job_id) or str(receipt.get("slurm_job_id")) != job_id:
        raise SummaryError(f"{path}: the receipt's Slurm job is not its job directory")
    end = filler.env_file(job_dir / "termination.env")
    if (end.get("job_id"), end.get("reason"), end.get("exit_code")) != (job_id, "completed",
                                                                        "0"):
        raise SummaryError(f"job {job_id} did not end completed with exit code 0: {end}")
    job = filler.env_file(job_dir / "job.env")
    hashes = receipt.get("hashes", {})
    if (job.get("git_sha"), job.get("source_sha256")) != (hashes.get("git_sha"),
                                                          hashes.get("source_sha256")):
        raise SummaryError(f"job {job_id}: job.env and the receipt name different sources")
    try:
        provenance = json.loads((job_dir / "provenance-verification.txt").read_text(
            encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SummaryError(f"job {job_id}: provenance verification is missing") from exc
    if (provenance.get("status"), provenance.get("git_sha"),
            provenance.get("source_sha256")) != ("PASS", job.get("git_sha"),
                                                 job.get("source_sha256")):
        raise SummaryError(f"job {job_id}: provenance verification did not pass")
    if job_id not in orx_jobs:
        raise SummaryError(f"job {job_id}: no ORX_RESULT ... job={job_id} exit=0 line in the "
                           "orx logs")
    usage = lane_usage(lane, job_dir.parent)
    holders = [j["job_id"] for j in usage["jobs"] if j["has_receipt"]]
    if holders != [job_id]:
        raise SummaryError(f"{lane.lane_id}: jobs {holders} hold a lane receipt; exactly one "
                           "may")
    predecessor = job.get("predecessor_job_id", "none")
    recorded = hashes.get("job", {})
    if predecessor not in ("", "none"):
        before = next((j for j in filler.lane_jobs(job_dir.parent)
                       if j.job_id == predecessor), None)
        if before is None or not before.checkpointed:
            raise SummaryError(f"job {job_id}: its predecessor {predecessor} did not end with "
                               "a confirmed signal checkpoint")
        if (recorded.get("kind"), recorded.get("predecessor_job_id")) != ("continuation",
                                                                          predecessor):
            raise SummaryError(f"job {job_id}: the receipt does not record its predecessor")
    elif recorded.get("kind") != "fresh":
        raise SummaryError(f"job {job_id}: the receipt's job kind is {recorded.get('kind')}")
    return {"job_id": job_id, "predecessor_job_id": None if predecessor in ("", "none")
            else predecessor, "usage": usage}


def load_receipts(paths: list[Path], orx_logs: list[Path]) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    orx_jobs = orx_results(orx_logs)
    for path in paths:
        raw = path.read_bytes()
        receipt = json.loads(raw)
        lane_id = receipt.get("lane", {}).get("lane_id")
        if receipt.get("experiment_id") != dhd.EXPERIMENT_ID:
            raise SummaryError(f"{path}: not a {dhd.EXPERIMENT_ID} receipt")
        if receipt.get("status") != "PRECHECK_COMPLETE":
            raise SummaryError(f"{path}: lane {lane_id} is {receipt.get('status')}")
        if lane_id not in dhd.LANES or receipt.get("profile") != "registered":
            raise SummaryError(f"{path}: {lane_id!r} is not a registered lane")
        if lane_id in receipts:
            raise SummaryError(f"two receipts for lane {lane_id}")
        job = check_job(path, receipt, dhd.LANES[lane_id], orx_jobs)
        receipts[lane_id] = {"receipt": receipt, "receipt_sha256": hashlib.sha256(raw).hexdigest(),
                             "job": job}
    return receipts


def summarise(receipts: dict[str, dict[str, Any]], *, ledger: Path, root: Path,
              run_roots: dict[str, Path] | None = None) -> dict[str, Any]:
    reads = {lane: entry["receipt"] for lane, entry in receipts.items()}
    prereg = {r["hashes"]["preregistration_sha256"] for r in reads.values()}
    bundles = {r["hashes"]["bundle_sha256"] for r in reads.values()}
    if len(prereg) > 1 or len(bundles) > 1:
        raise SummaryError("the lanes were read against different registrations or bundles")
    row = preregister.verify(dhd.EXPERIMENT_ID, ledger=ledger, root=root)
    if reads and row["sha256"] not in prereg:
        raise SummaryError("the lanes' preregistration is not the frozen one")
    if reads and bundles != {dhd.SOURCE_BUNDLE_SHA256}:
        raise SummaryError("the lanes did not read the registered K1 bundle")
    sources = {(r["hashes"].get("git_sha"), r["hashes"].get("source_sha256"))
               for r in reads.values()}
    if len(sources) > 1:
        raise SummaryError("the lanes ran different source revisions")
    usage: dict[str, Any] = {}
    for lane_id in dhd.REGISTERED_ORDER:
        if lane_id in receipts:
            usage[lane_id] = receipts[lane_id]["job"]["usage"]
        elif run_roots and lane_id in run_roots:
            usage[lane_id] = lane_usage(dhd.LANES[lane_id], run_roots[lane_id], strict=False)
        else:
            usage[lane_id] = None
    return {
        "experiment_id": dhd.EXPERIMENT_ID,
        "preregistration_sha256": row["sha256"],
        "combined": dhs.combined_recommendation({lane: r["decisions"]
                                                 for lane, r in reads.items()}),
        "lanes": {lane: {"decisions": entry["receipt"]["decisions"],
                         "slurm_job_id": entry["job"]["job_id"],
                         "predecessor_job_id": entry["job"]["predecessor_job_id"],
                         "dev_artifact_sha256": entry["receipt"]["hashes"].get(
                             "dev_artifact_sha256"),
                         "receipt_sha256": entry["receipt_sha256"]}
                  for lane, entry in sorted(receipts.items())},
        "gpu_usage": usage,
        "gpu_hours_used": sum(u["gpu_hours_used"] for u in usage.values() if u),
    }


def _run_root(value: str) -> tuple[str, Path]:
    lane, separator, path = value.partition("=")
    if not separator or lane not in dhd.LANES:
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
