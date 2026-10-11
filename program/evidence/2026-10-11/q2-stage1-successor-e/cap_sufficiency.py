"""Do E's per-job caps hold every slot before the GPU job's USR1? (CPU only, seeded.)

DR0 fires when an E job ends without completing its slots, and every E job's slots are the
whole task set (no fill rule), so a cap that is too tight stops E. This check simulates the
lane's continuous dispatch (S1a section 5.6: V = 20 workers, each takes the next queued slot
as soon as its previous VM is gone; a slot lost to infrastructure on its first attempt is
queued once more) for each E job in its registered order (``plan-e.json``), with slot
occupancies resampled from S1a's realized slots for the same (size, task, harness) (four
per cell: two sessions x two reruns, ``a1.jsonl``). The job starts at the longest S1a
start-up (Slurm start to first dispatch) and must finish its last slot before its USR1
point, the cap minus 180 s. Scenarios: S1a's slots as measured; every slot 10% and 20%
longer; and 5% of each (size, harness) cell's first attempts lost at full length and
re-queued (the most DR0 tolerates).

The dispatch model is checked first on S1a's own four A1 jobs: replaying each job's realized
dispatch order with its realized slot occupancies must reproduce its realized span from the
first dispatch to the last teardown.

Usage, from the repository root::

    python program/evidence/2026-10-11/q2-stage1-successor-e/cap_sufficiency.py --out OUT.json
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import platform
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from harness.q2_design import data as D  # noqa: E402
from harness.q2_stage1 import records as R1  # noqa: E402
from harness.q2_stage1e import plan as PE  # noqa: E402

SEED = 42
DRAWS = 10_000
USR1_LEAD_S = 180.0
SCENARIOS = {
    "as_measured": {"scale": 1.0, "loss_share": 0.0},
    "slots_10pct_longer": {"scale": 1.1, "loss_share": 0.0},
    "slots_20pct_longer": {"scale": 1.2, "loss_share": 0.0},
    "five_pct_lost_and_requeued": {"scale": 1.0, "loss_share": 0.05},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def makespan(durations: list[float], workers: int) -> float:
    """Continuous dispatch in queue order: the end of the last slot (from the first dispatch)."""
    free = [0.0] * workers
    heapq.heapify(free)
    end = 0.0
    for d in durations:
        start = heapq.heappop(free)
        finish = start + d
        end = max(end, finish)
        heapq.heappush(free, finish)
    return end


def s1a_replay(root: Path) -> dict[str, dict[str, float]]:
    """Each S1a A1 job: its realized span against the replay of its dispatch order."""
    out = {}
    for job, run in D.JOB_DIRS.items():
        rows = R1.read_jsonl(root / run / "episodes.jsonl")
        rows.sort(key=lambda r: float(r["host"]["t_dispatch"]))
        first = float(rows[0]["host"]["t_dispatch"])
        last = max(float(r["host"]["t_teardown"]) for r in rows)
        durations = [float(r["host"]["slot_occupancy_s"]) for r in rows]
        replay = makespan(durations, PE.V)
        out[job] = {
            "episodes": len(rows),
            "realized_span_s": round(last - first, 1),
            "replayed_span_s": round(replay, 1),
            "relative_error": round((replay - (last - first)) / (last - first), 4),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=DRAWS)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    plan = PE.load_plan(ROOT / PE.PLAN_FILE)
    cost = PE.cost_inputs(PE.load_cost_model(ROOT))
    records = R1.read_jsonl(ROOT / D.RECORDS)
    slots: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for rec in R1.final_records(records).values():
        if rec["status"] == "scored":
            key = (rec["size"], rec["task_id"], rec["harness"])
            slots[key].append(float(rec["host"]["slot_occupancy_s"]))
    rng = np.random.default_rng(SEED)
    results: dict[str, dict[str, object]] = {}
    for size in PE.SIZES:
        cap_s = plan["caps_minutes"][f"E-{size}"] * 60.0
        budget = cap_s - USR1_LEAD_S - cost["startup_s"]
        orders = [plan["episode_orders"][f"{s}:{size}"] for s in PE.SESSIONS]
        pools = [np.asarray(slots[(size, t, h)]) for order in orders for t, h in order]
        if any(len(p) != 4 for p in pools):
            raise SystemExit("every (size, task, harness) cell needs four S1a slots")
        n = len(orders[0])
        for name, spec in SCENARIOS.items():
            spans = np.empty(args.draws)
            for i in range(args.draws):
                order = i % len(orders)
                pick = rng.integers(0, 4, size=n)
                base = pools[order * n : (order + 1) * n]
                durations = [float(base[j][pick[j]]) * spec["scale"] for j in range(n)]
                if spec["loss_share"]:
                    by_cell = defaultdict(list)
                    for j, (_t, h) in enumerate(orders[order]):
                        by_cell[h].append(j)
                    lost = []
                    for _h, idx in sorted(by_cell.items()):
                        k = int(spec["loss_share"] * len(idx))
                        lost += list(rng.choice(idx, size=k, replace=False))
                    durations = durations + [durations[j] for j in sorted(lost)]
                spans[i] = makespan(durations, PE.V)
            margin = budget - spans
            results[f"{size}/{name}"] = {
                "cap_min": plan["caps_minutes"][f"E-{size}"],
                "dispatch_budget_s": round(budget, 1),
                "span_s": {q: round(float(np.percentile(spans, p)), 1)
                           for q, p in (("p50", 50), ("p95", 95), ("p99", 99), ("max", 100))},
                "p_complete_before_usr1": float(np.mean(spans <= budget)),
                "margin_s_p01": round(float(np.percentile(margin, 1)), 1),
            }  # fmt: skip
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        head = None
    dirty = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--", "harness", "scripts", "program"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    out = {
        "method": __doc__,
        "seed": SEED,
        "draws": args.draws,
        "V": PE.V,
        "startup_s": cost["startup_s"],
        "usr1_lead_s": USR1_LEAD_S,
        "s1a_replay_check": s1a_replay(ROOT),
        "e_jobs": results,
        "inputs": {
            str(PE.PLAN_FILE): sha256(ROOT / PE.PLAN_FILE),
            str(D.RECORDS): sha256(ROOT / D.RECORDS),
            str(PE.COST_MODEL): sha256(ROOT / PE.COST_MODEL),
        },
        "provenance": {
            "git_head": head,
            "tree_dirty": bool(dirty),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "argv": sys.argv,
        },  # fmt: skip
    }
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v["p_complete_before_usr1"] for k, v in results.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
