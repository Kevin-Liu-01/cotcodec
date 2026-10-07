#!/usr/bin/env python3
"""Derive the K1 successor's job limits from a throughput-probe receipt.

The registered formula is ``harness/sparse_indexer_k1_budget_v2.derive_limits``.
This script only applies it:

* ``--probe-receipt PATH``: checks that the receipt is a complete registered
  ``q3-k1-throughput-probe-v1`` receipt, recomputes the limits from its rates,
  refuses if they differ from the limits the probe itself wrote, prints the
  limits table (JSON and the Markdown rows of the v2 preregistration's table),
  and reports whether the caps with the probe exceed 8 GPU-h (then the gauntlet
  applies before any freeze, program decision D20).
* ``--apply``: writes the limits and the receipt's SHA-256 into the v2 contract
  (``execution.job_limits`` and ``throughput_probe.receipt_sha256``), replacing
  the two ``null`` placeholders, and refuses when the gauntlet applies.
* ``--scenario NAME``: the same table for one of the design analysis's
  scenarios (estimates, for the registration's sensitivity table).

Exit codes: 0 limits derived (or applied), 1 the gauntlet applies, 2 bad input.
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

from harness import sparse_indexer_k1_budget_v2 as budget  # noqa: E402

CONTRACT = (PROJECT_ROOT / "experiments" / "architectures"
            / "translation-supervised-sparse-indexer-k1-screen-v2.yaml")
PROBE_ID = "q3-k1-throughput-probe-v1"
LIMITS_PLACEHOLDER = "  job_limits: null\n"
RECEIPT_PLACEHOLDER = ("  receipt_sha256: null  # written from the probe receipt before the v2 "
                       "freeze\n")


class DeriveError(ValueError):
    """The probe receipt cannot give registered limits."""


ROW_LABELS = {"main": "main (and its continuation, if any)",
              "extension": "extension (only when the main read calls for it, then mandatory)"}
PROBE_ROW = "| q3-k1-throughput-probe-v1 | 1 | | 9 | 0.15 |"


def markdown_rows(derived: dict[str, Any]) -> list[str]:
    """The rows of the v2 preregistration's limits table ("Compute"), in its order."""

    rows = []
    for job, entry in derived["jobs"].items():
        rows.append(f"| {ROW_LABELS.get(job, job)} | {entry['gpus']} | "
                    f"{entry['projected_minutes']:.1f} | {entry['minutes']} | "
                    f"{entry['max_gpu_hours']:.2f} |")
    for run, cap in derived["probe_runs_gpu_hours"].items():  # every probe run counts
        rows.append(PROBE_ROW if run == PROBE_ID else f"| {run} | | | | {cap:.2f} |")
    rows.append(f"| Total with the probe | | | | {derived['total_gpu_hours_with_probe']:.2f} |")
    return rows


def from_receipt(path: Path) -> tuple[dict[str, Any], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("experiment_id") != PROBE_ID:
        raise DeriveError(f"not a {PROBE_ID} receipt")
    if payload.get("status") != "PROBE_COMPLETE":
        raise DeriveError(f"the probe ended {payload.get('status')}, not PROBE_COMPLETE")
    if payload.get("profile") != "registered":
        raise DeriveError("the probe did not run the registered profile")
    derived = budget.derive_limits(budget.Rates.from_dict(payload["rates"]))
    if budget.limits_table(derived) != payload.get("limits_table"):
        raise DeriveError("the receipt's limits differ from the registered formula's")
    return derived, hashlib.sha256(path.read_bytes()).hexdigest()


def apply(contract: Path, derived: dict[str, Any], receipt_sha: str) -> None:
    text = contract.read_text(encoding="utf-8")
    if text.count(LIMITS_PLACEHOLDER) != 1 or text.count(RECEIPT_PLACEHOLDER) != 1:
        raise DeriveError("the contract's placeholders are not in their registered form")
    table = budget.limits_table(derived)
    block = "  job_limits:\n" + "".join(
        f"    {job}: {{minutes: {entry['minutes']}, max_gpu_hours: {entry['max_gpu_hours']:.2f}}}\n"
        for job, entry in table.items())
    text = text.replace(LIMITS_PLACEHOLDER, block).replace(
        RECEIPT_PLACEHOLDER, f"  receipt_sha256: {receipt_sha}\n")
    contract.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--probe-receipt", type=Path)
    source.add_argument("--scenario", choices=sorted(budget.SCENARIO_INPUTS))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    args = parser.parse_args(argv)
    try:
        if args.scenario:
            if args.apply:
                raise DeriveError("--apply takes a probe receipt, never a scenario")
            derived, receipt_sha = budget.derive_limits(budget.scenario_rates(args.scenario)), None
        else:
            derived, receipt_sha = from_receipt(args.probe_receipt)
        if args.apply:
            if derived["gauntlet_required"]:
                raise DeriveError("the caps with the probe exceed 8 GPU-h: the gauntlet "
                                  "applies (program decision D20); nothing is written")
            assert receipt_sha is not None
            apply(args.contract, derived, receipt_sha)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"limits": budget.limits_table(derived),
                      "total_gpu_hours_with_probe": derived["total_gpu_hours_with_probe"],
                      "gauntlet_required": derived["gauntlet_required"],
                      "probe_receipt_sha256": receipt_sha,
                      "markdown_rows": markdown_rows(derived)}, indent=2))
    return 1 if derived["gauntlet_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
