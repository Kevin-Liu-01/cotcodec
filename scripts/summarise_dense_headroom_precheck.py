#!/usr/bin/env python3
"""Combine the two lane receipts of the dense headroom pre-check into its read.

CPU only, no torch. Each receipt must be a completed lane of
``q3-dense-headroom-precheck-v1`` (status ``PRECHECK_COMPLETE``) read against
the same frozen preregistration and the same K1 bundle; the frozen file must
still match its ledger row. The combined read applies the registered base and
design rule (``harness.dense_headroom_stats.combined_recommendation``): which
K1 v3 designs the measured dense headroom supports, on which base, and with
which requirements. A missing or incomplete lane gives ``INCOMPLETE``.

Exit codes: 0 written, 2 an input is missing or inconsistent.
"""

from __future__ import annotations

import argparse
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
from scripts import preregister  # noqa: E402


class SummaryError(ValueError):
    """A lane receipt is missing, incomplete or inconsistent."""


def load_receipts(paths: list[Path]) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for path in paths:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        lane = receipt.get("lane", {}).get("lane_id")
        if receipt.get("experiment_id") != dhd.EXPERIMENT_ID:
            raise SummaryError(f"{path}: not a {dhd.EXPERIMENT_ID} receipt")
        if receipt.get("status") != "PRECHECK_COMPLETE":
            raise SummaryError(f"{path}: lane {lane} is {receipt.get('status')}")
        if lane not in dhd.LANES:
            raise SummaryError(f"{path}: {lane!r} is not a registered lane")
        if lane in receipts:
            raise SummaryError(f"two receipts for lane {lane}")
        receipts[lane] = receipt
    return receipts


def summarise(receipts: dict[str, dict[str, Any]], *, ledger: Path, root: Path
              ) -> dict[str, Any]:
    prereg = {r["hashes"]["preregistration_sha256"] for r in receipts.values()}
    bundles = {r["hashes"]["bundle_sha256"] for r in receipts.values()}
    if len(prereg) != 1 or len(bundles) != 1:
        raise SummaryError("the lanes were read against different registrations or bundles")
    row = preregister.verify(dhd.EXPERIMENT_ID, ledger=ledger, root=root)
    if row["sha256"] not in prereg:
        raise SummaryError("the lanes' preregistration is not the frozen one")
    if bundles != {dhd.SOURCE_BUNDLE_SHA256}:
        raise SummaryError("the lanes did not read the registered K1 bundle")
    decisions = {lane: r["decisions"] for lane, r in receipts.items()}
    return {
        "experiment_id": dhd.EXPERIMENT_ID,
        "preregistration_sha256": row["sha256"],
        "combined": dhs.combined_recommendation(decisions),
        "lanes": {lane: {"decisions": r["decisions"],
                         "slurm_job_id": r.get("slurm_job_id"),
                         "dev_artifact_sha256": r["hashes"].get("dev_artifact_sha256"),
                         "receipt_sha256": hashlib.sha256(
                             json.dumps(r, sort_keys=True).encode()).hexdigest()}
                  for lane, r in sorted(receipts.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("receipts", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, default=preregister.DEFAULT_LEDGER)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"FAIL: {args.output} exists; never overwrite", file=sys.stderr)
        return 2
    try:
        summary = summarise(load_receipts(args.receipts), ledger=args.ledger, root=args.root)
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
