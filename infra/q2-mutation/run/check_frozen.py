#!/usr/bin/env python3
"""Host-side refusal before a Q2 mutation or control run is submitted.

Run by ``submit_controls.sh`` and ``submit_mutants.sh`` on the host (system
Python 3.10, standard library only) before any Slurm job exists:

* the staged tree's ``.git_sha`` names the commit being submitted;
* for every split but dev: ``Q2M_PREREG_FROZEN=q2-evaluator-mutation-v1`` is
  set, the staged ledger's hash chain holds and its row for this experiment
  matches the staged preregistration file, and the metric image, the LO-VM
  image and (for mutation runs) the application mode equal the pins block.

The code, catalog, spec, split and input digests are checked again inside the
containers (``campaign guard``), where the staged tree and the inputs are
mounted read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from harness.q2_mutation.campaign import (  # noqa: E402
    DEV_SPLIT,
    EXPERIMENT_ID,
    PREREG_PATH,
    CampaignError,
    frozen_ledger_row,
    prereg_pins,
)


def check(
    src: Path, sha: str, split: str, metric: str, lo: str, apply_to: str | None
) -> dict[str, object]:
    marker = src / ".git_sha"
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != sha:
        raise CampaignError(f"{marker} does not name {sha}; stage the commit first")
    if split == DEV_SPLIT:
        return {"split": split, "frozen": False}
    if os.environ.get("Q2M_PREREG_FROZEN") != EXPERIMENT_ID:
        raise CampaignError("only the dev split runs before the preregistration freeze")
    row = frozen_ledger_row(src)
    if row is None:
        raise CampaignError(f"split {split!r} runs only after {EXPERIMENT_ID} is frozen")
    pins = prereg_pins((src / PREREG_PATH).read_text(encoding="utf-8"))
    wanted = {"metric_image_id": metric, "lo_vm_image_id": lo}
    if apply_to is not None:
        wanted["apply_to"] = apply_to
    wrong = sorted(key for key, value in wanted.items() if pins.get(key) != value)
    if wrong:
        raise CampaignError(f"images or apply-to differ from the preregistration pins: {wrong}")
    return {"split": split, "frozen": True, "ledger_hash": row.get("hash")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--split", required=True, choices=["dev", "confirm", "reserve"])
    parser.add_argument("--metric", required=True)
    parser.add_argument("--lo", required=True)
    parser.add_argument("--apply-to", choices=["gold", "base"], default=None)
    args = parser.parse_args(argv)
    try:
        out = check(args.src, args.sha, args.split, args.metric, args.lo, args.apply_to)
    except CampaignError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
