"""Input and invocation of the S1a secondary model (registration section 10.1, G0 item 12).

``glmm.R`` fits the registered crossed logit GLMM with glmmTMB in the pinned CPU container
(``infra/q2-stage1/glmm/Dockerfile``, run through ``s1a-cpu.sbatch`` with no network and no
GPU). This module writes its input, one row per final scored episode of the analysis set
(``records.final_records``), with session labels nested in size (``"9B:S1"``), and holds the
synthetic generator of the container's acceptance test: the registered generative model of
section 10.2 (task, task x size, task x harness, session, harness x session, task x session,
task x harness x session effects on the logit scale, Bernoulli outcomes).
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from harness.q2_stage1.records import HARNESSES, RERUNS, SESSIONS, SIZES, outcome

COLUMNS = ("y", "size", "harness", "task", "session", "rerun")
DEFAULT_BOOT = 200  # parametric-bootstrap refits per fit (registration G0 item 12)
SYNTHETIC_TRUTH = {
    "intercept": -1.0,
    "size_9B": 0.5,
    "harness_GA": 0.0,
    "sd_task": 1.5,
    "sd_task_size": 0.3,
    "sd_task_harness": 1.0,
    "sd_task_size_harness": 0.2,
    "sd_session": 0.1,
    "sd_harness_session": 0.05,
    "sd_task_session": 0.3,
    "sd_task_harness_session": 0.3,
}


def rows_from_records(
    finals: Mapping[tuple[str, str, str, str, int], Mapping[str, Any]], tasks: Sequence[str]
) -> list[dict[str, Any]]:
    """One row per final scored slot of ``tasks`` (missing and lost slots are left out)."""
    out = []
    for size in SIZES:
        for task in tasks:
            for harness in HARNESSES:
                for session in SESSIONS:
                    for rerun in RERUNS:
                        rec = finals.get((size, session, task, harness, rerun))
                        y = outcome(rec)
                        if np.isnan(y):
                            continue
                        out.append({"y": int(y), "size": size, "harness": harness,
                                    "task": task, "session": f"{size}:{session}",
                                    "rerun": rerun})  # fmt: skip
    return out


def write_csv(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in COLUMNS})


def synthetic(k: int = 32, seed: int = 42, truth: Mapping[str, float] = SYNTHETIC_TRUTH):
    """Rows from the registered generative model (two sizes, two harnesses, two sessions per
    size, two reruns): the GLMM container's acceptance data."""
    rng = np.random.default_rng(seed)
    t = dict(truth)
    task = rng.normal(0, t["sd_task"], k)
    task_size = rng.normal(0, t["sd_task_size"], (k, 2))
    task_harness = rng.normal(0, t["sd_task_harness"], (k, 2))
    task_size_harness = rng.normal(0, t["sd_task_size_harness"], (k, 2, 2))
    session = rng.normal(0, t["sd_session"], (2, 2))
    harness_session = rng.normal(0, t["sd_harness_session"], (2, 2, 2))
    task_session = rng.normal(0, t["sd_task_session"], (k, 2, 2))
    task_harness_session = rng.normal(0, t["sd_task_harness_session"], (k, 2, 2, 2))
    rows = []
    for zi, size in enumerate(SIZES):
        for ti in range(k):
            for hi, harness in enumerate(HARNESSES):
                for si, sess in enumerate(SESSIONS):
                    eta = (t["intercept"] + t["size_9B"] * (size == "9B")
                           + t["harness_GA"] * (harness == "H-GA") + task[ti]
                           + task_size[ti, zi] + task_harness[ti, hi]
                           + task_size_harness[ti, zi, hi] + session[zi, si]
                           + harness_session[zi, hi, si] + task_session[ti, zi, si]
                           + task_harness_session[ti, zi, hi, si])  # fmt: skip
                    p = 1 / (1 + np.exp(-eta))
                    for rerun in RERUNS:
                        rows.append({"y": int(rng.random() < p), "size": size,
                                     "harness": harness, "task": f"t{ti:03d}",
                                     "session": f"{size}:{sess}", "rerun": rerun})  # fmt: skip
    return rows


def rscript_argv(csv_in: str, json_out: str, n_boot: int = DEFAULT_BOOT, seed: int = 42):
    """The container command (the script is read from the mounted source tree)."""
    return ["Rscript", "/src/harness/q2_stage1/glmm.R", csv_in, json_out, str(n_boot), str(seed)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    syn = sub.add_parser("synthetic", help="write the acceptance data set")
    syn.add_argument("--out", type=Path, required=True)
    syn.add_argument("--k", type=int, default=32)
    syn.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    rows = synthetic(args.k, args.seed)
    write_csv(rows, args.out)
    meta = {"rows": len(rows), "k": args.k, "seed": args.seed, "truth": SYNTHETIC_TRUTH}
    args.out.with_suffix(".truth.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
    print(json.dumps({"rows": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
