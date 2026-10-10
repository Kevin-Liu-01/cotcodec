"""S1a's committed records and plan, read with the registered record functions.

Paths are relative to the repository root. The primary set is the registered one: the 32
base tasks, raw verdicts (``records.outcome_array``, y = 1 iff the checker score is 1.0).
The eligible pool is the base plus the 81 extension tasks (113), every one of which ran in
all four A1 jobs (the registered secondary set).
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from harness.q2_stage1 import records as R

ANALYSIS_DIR = Path("program/evidence/2026-10-10/q2-stage1-analysis")
A1_DIR = Path("program/evidence/2026-10-10/q2-stage1-a1")
RECORDS = ANALYSIS_DIR / "a1.jsonl"
COSTS = ANALYSIS_DIR / "costs.json"
REPORT = ANALYSIS_DIR / "report" / "report-guarded.json"
PLAN = Path("program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json")
JOB_DIRS = {
    "A1-9B-S1": A1_DIR / "a1-9b-s1" / "vm-1045",
    "A1-4B-S1": A1_DIR / "a1-4b-s1" / "vm-1048",
    "A1-9B-S2": A1_DIR / "a1-9b-s2" / "vm-1051",
    "A1-4B-S2": A1_DIR / "a1-4b-s2" / "vm-1062",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class S1aData:
    """The arrays and task lists the fit and the simulator read."""

    base: tuple[str, ...]
    extension: tuple[str, ...]  # the registered extension order (blocks 1-11)
    domains: dict[str, str]
    y_base: np.ndarray  # (Z, 32, H, S, R), raw verdicts
    y_pool: np.ndarray  # (Z, 113, H, S, R): base then extension order
    slot_s: dict[tuple[str, str], float]  # (size, task) -> mean slot occupancy, seconds
    digests: dict[str, str]

    @property
    def pool(self) -> tuple[str, ...]:
        return self.base + self.extension


def load(root: Path = Path(".")) -> S1aData:
    """Read a1.jsonl and the frozen plan from the repository at ``root``."""
    records = R.read_jsonl(root / RECORDS)
    finals = R.final_records(records)
    plan = json.loads((root / PLAN).read_text(encoding="utf-8"))
    base = tuple(plan["base"])
    blocks = {int(k): v for k, v in plan["extension_blocks"].items()}
    done = R.completed_extension_blocks(records, blocks)
    if done != sorted(blocks):
        raise ValueError(f"expected every extension block completed, got {done}")
    extension = tuple(t for b in sorted(blocks) for t in blocks[b])
    occ: dict[tuple[str, str], list[float]] = defaultdict(list)
    for rec in finals.values():
        if rec["status"] == "scored":
            occ[(rec["size"], rec["task_id"])].append(float(rec["host"]["slot_occupancy_s"]))
    y_base = R.outcome_array(finals, list(base))
    y_pool = R.outcome_array(finals, list(base + extension))
    if np.isnan(y_pool).any():
        raise ValueError("S1a's pool array has missing slots; the fit assumes none")
    return S1aData(
        base=base,
        extension=extension,
        domains={t: plan["task_domains"][t] for t in base + extension},
        y_base=y_base,
        y_pool=y_pool,
        slot_s={k: float(np.mean(v)) for k, v in occ.items()},
        digests={str(p): sha256(root / p) for p in (RECORDS, PLAN, COSTS, REPORT)},
    )
