"""The job plan of `q2-stage1-successor-e-v1` (successor E): tasks, orders, caps and jobs.

Everything here is fixed before any E episode and reads no outcome. E adds data to S1a's
design without changing its estimands or rules (D66, D69, D80 (iii)):

* **tasks**: every task of S1a's eligible pool (S1a's ``plan.eligible_pool``: the confirm
  split minus the four K1 raw-gold failures and the three offline-setup exclusions), 113
  tasks, with no new draw. The list equals S1a's base plus its extension blocks;
* **sizes**: Qwen3.5-9B then 4B in every session, S1a's seeded order (``plan.size_order``);
* **sessions**: four new serving sessions per size, ``E1``-``E4``; a session's jobs start at
  least 12 hours after the later job of the session before it has ended;
* **one episode** per (size, task, harness, session): one block ``e1`` per job, rerun 1, in
  a seeded order that interleaves the harnesses; no fill rule (every job's slots are the
  whole task set);
* **caps** from arithmetic on S1a's realized cost (the design study's cost model, D66): a
  job's cap is ceil(3 + (L + (N x slot / V + drain) x 1.2 x 1.05) / 60) minutes, with L the
  longest S1a start-up, slot the size's mean S1a slot over the 113 tasks and drain the
  size's longest S1a drain; one overlay build from the freeze commit and one pre-funded
  retry are reserved (3 + 3 minutes). Each E job's cap is 52 minutes at 9B and 48 at 4B;
  the caps sum to 406 minutes (6.77 GPU-h), within S1a's 478-minute maximum.

The engine argv, request sampling, prompt date, VM settings and CPU plan are S1a's
(``harness.q2_stage1.plan``), imported unchanged.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_stage1 import plan as P1

EXPERIMENT_ID = "q2-stage1-successor-e-v1"
SIZES = P1.SIZES
HARNESSES = P1.HARNESSES
SESSIONS = ("E1", "E2", "E3", "E4")
RERUN = 1  # one episode per (size, task, harness, session)
BLOCK = "e1"
ORDER_SEED = 42
N_STAR = 32  # action-path v2 attempt 1 (D53): V = 20, the sizes one after the other
V = 20
SESSION_GAP_H = 12
USR1_LEAD_MIN = P1.USR1_LEAD_MIN  # --signal=B:USR1@180
DR4_FACTOR = 1.2  # DR4's projection rule: realized cost x 1.2
REQUEUE_FACTOR = P1.REQUEUE_FACTOR  # 1.05, the re-queues DR0 tolerates
OVERLAY_CAPS = {"OE": 3, "OE_retry": 3}  # S1a's O2 and its pre-funded retry
ALLOCATABLE_MINUTES = P1.ALLOCATABLE_MINUTES  # 478: S1a's maximum, 7.967 GPU-h
GPU_MINUTES_LIMIT = P1.GPU_MINUTES_LIMIT  # 480 = 8 GPU-h of one H100
SPLITS = "program/evidence/q2-mutation/splits.json"
SPLITS_SHA256 = "2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9"
# The design study's cost model (D66): S1a's realized start-up, slots and drains.
COST_MODEL = "program/evidence/2026-10-10/q2-design-study/cost-model.json"
COST_MODEL_SHA256 = "36887d3c13b9f4b0809b27ae4f6b825cab80dd824be5f0621bd74156d22346a9"
# S1a's frozen plan: its base (E's registered secondary set) and the pool's domains.
S1A_PLAN = "program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json"
S1A_PLAN_SHA256 = "6a3f0219448301d95a80d443ed75892eaac093e42349ef98fb985a5d87467d51"
PLAN_FILE = "program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json"
PLAN_STATUS = "registered"


class PlanError(ValueError):
    """Raised when a plan input is outside the registration."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    """S1a's canonical JSON digest (``plan.digest``)."""
    return P1.digest(value)


# --------------------------------------------------------------------------- tasks and jobs


def tasks(confirm_ids: Sequence[str]) -> list[str]:
    """Every eligible pool task (S1a section 5.4): 113, sorted, no draw."""
    return list(P1.eligible_pool(confirm_ids, P1.OFFLINE_EXCLUDED))


def size_order() -> list[str]:
    """9B then 4B in every session: S1a's seeded size order, unchanged."""
    return P1.size_order()


def job_name(size: str, session: str) -> str:
    if size not in SIZES or session not in SESSIONS:
        raise PlanError(f"unknown E job {size} {session}")
    return f"E-{size}-{session}"


def parse_job(job: str) -> tuple[str, str]:
    parts = str(job).split("-")
    if len(parts) != 3 or parts[0] != "E":
        raise PlanError(f"{job!r} is not an E job")
    job_name(parts[1], parts[2])
    return parts[1], parts[2]


def job_order() -> list[str]:
    """The registered order: E1 to E4, each 9B then 4B. A job may start only after every
    earlier one has ended and passed DR0 (S1a section 11)."""
    return [job_name(size, session) for session in SESSIONS for size in size_order()]


def block_order(task_ids: Sequence[str], session: str, size: str) -> list[tuple[str, str]]:
    """One job's (task, harness) order: every cell once, harnesses interleaved."""
    if session not in SESSIONS or size not in SIZES:
        raise PlanError(f"unknown E job {size} {session}")
    cells = [(t, h) for t in sorted(task_ids) for h in HARNESSES]
    random.Random(f"q2-stage1e:{session}:{size}:{BLOCK}:{ORDER_SEED}").shuffle(cells)
    return cells


def episode_orders(task_ids: Sequence[str]) -> dict[str, list[list[str]]]:
    """Every job's order, keyed ``<session>:<size>``."""
    return {
        f"{session}:{size}": [list(c) for c in block_order(task_ids, session, size)]
        for session in SESSIONS
        for size in SIZES
    }


def slots(plan: Mapping[str, Any], size: str, session: str) -> list[dict[str, Any]]:
    """One E job's slots from the plan file: block ``e1``, rerun 1, in its seeded order.
    Slot ids are S1a's ``<job>:<block>:<index>`` (``plan.block_slots``)."""
    orders = plan["episode_orders"]
    if digest(orders) != plan["episode_orders_sha256"]:
        raise PlanError("the plan's episode orders do not match their digest")
    job = job_name(size, session)
    cells = orders[f"{session}:{size}"]
    if sorted(map(tuple, cells)) != sorted((t, h) for t in plan["tasks"] for h in HARNESSES):
        raise PlanError(f"{job}: the order is not every (task, harness) cell once")
    return P1.block_slots(job, size, session, BLOCK, RERUN, cells)


def session_not_before(job: str, ends: Mapping[str, float]) -> float | None:
    """The earliest start of ``job``: None in session E1; otherwise the later end of the
    previous session's two jobs (``ends``: job -> end epoch) plus 12 hours. Within a session
    the second size waits for the first by the job order (``job_order``)."""
    _, session = parse_job(job)
    k = SESSIONS.index(session)
    if k == 0:
        return None
    previous = [job_name(z, SESSIONS[k - 1]) for z in SIZES]
    missing = [p for p in previous if p not in ends]
    if missing:
        raise PlanError(f"{job} needs the end of {missing}")
    return max(float(ends[p]) for p in previous) + SESSION_GAP_H * 3600


# --------------------------------------------------------------------------- caps


def load_cost_model(source_dir: Path) -> dict[str, Any]:
    """The design study's cost model, refused unless its SHA-256 is the registered one."""
    data = (Path(source_dir) / COST_MODEL).read_bytes()
    if _sha256_bytes(data) != COST_MODEL_SHA256:
        raise PlanError(f"{COST_MODEL} is not the registered cost model")
    return json.loads(data.decode("utf-8"))


def cost_inputs(cost_model: Mapping[str, Any]) -> dict[str, Any]:
    """L (the longest S1a start-up, Slurm start to first dispatch), and per size the mean S1a
    slot occupancy over the 113 pool tasks and the longest S1a drain, in seconds."""
    by_size = cost_model["by_size"]
    return {
        "startup_s": float(cost_model["startup_s_max"]),
        "mean_slot_s": {z: float(by_size[z]["mean_slot_s_pool"]) for z in SIZES},
        "drain_s": {z: float(by_size[z]["drain_s"]) for z in SIZES},
        "V": int(cost_model["V"]),
    }


def job_cap_minutes(size: str, n_episodes: int, inputs: Mapping[str, Any], v: int = V) -> int:
    """ceil(3 + (L + (N x slot / V + drain) x 1.2 x 1.05) / 60): the realized price x 1.2
    (DR4) x 1.05 (re-queues), plus S1a's start-up and the USR1 lead."""
    if int(inputs["V"]) != v:
        raise PlanError(f"the cost model is priced at V = {inputs['V']}, not {v}")
    work = n_episodes * float(inputs["mean_slot_s"][size]) / v + float(inputs["drain_s"][size])
    seconds = float(inputs["startup_s"]) + work * DR4_FACTOR * REQUEUE_FACTOR
    return math.ceil(USR1_LEAD_MIN + seconds / 60)


def episodes_per_job(n_tasks: int) -> int:
    return n_tasks * len(HARNESSES) * RERUN


def caps(inputs: Mapping[str, Any], n_tasks: int) -> dict[str, int]:
    """Each size's job cap in minutes."""
    return {z: job_cap_minutes(z, episodes_per_job(n_tasks), inputs) for z in SIZES}


def total_cap_minutes(job_caps: Mapping[str, int]) -> int:
    """Every E job's cap (four sessions per size) plus the overlay build and its retry."""
    total = sum(job_caps[z] for z in SIZES) * len(SESSIONS) + sum(OVERLAY_CAPS.values())
    if total > ALLOCATABLE_MINUTES:
        raise PlanError(f"E's caps total {total} minutes, above {ALLOCATABLE_MINUTES}")
    return total


def jobs(job_caps: Mapping[str, int], n_tasks: int) -> list[dict[str, Any]]:
    """The post-freeze jobs in order with their CPU and minute plans (S1a section 5.5:
    VM job first, its GPU job held by ``--dependency=after:``; the VM job's limit is the
    GPU cap plus 10 minutes; one (size, session) pair at a time)."""
    out: list[dict[str, Any]] = [
        {"job": name, "gpu_minutes": minutes} for name, minutes in OVERLAY_CAPS.items()
    ]
    for job in job_order():
        size, session = parse_job(job)
        k = SESSIONS.index(session)
        gap = None
        if k:
            previous = [job_name(z, SESSIONS[k - 1]) for z in size_order()]
            gap = {"after_the_later_end_of": previous, "hours": SESSION_GAP_H}
        out.append({
            "job": job,
            "size": size,
            "session": session,
            "episodes": episodes_per_job(n_tasks),
            "gpu_minutes": job_caps[size],
            "vm_concurrency": V,
            "vm_cpus": P1.vm_job_cpus(V),
            "vm_minutes": job_caps[size] + P1.VM_JOB_EXTRA_MIN,
            "co_running_cpus": P1.check_cpus([V], 1),
            "not_before": gap,
        })  # fmt: skip
    return out


# --------------------------------------------------------------------------- plan file


def load_s1a_plan(source_dir: Path) -> dict[str, Any]:
    """S1a's frozen plan file, refused unless its ``plan_sha256`` is the frozen one."""
    data = json.loads((Path(source_dir) / S1A_PLAN).read_text(encoding="utf-8"))
    body = {k: v for k, v in data.items() if k != "plan_sha256"}
    if not (data.get("plan_sha256") == digest(body) == S1A_PLAN_SHA256):
        raise PlanError(f"{S1A_PLAN} is not S1a's frozen plan")
    return data


def load_splits(source_dir: Path) -> dict[str, Any]:
    data = (Path(source_dir) / SPLITS).read_bytes()
    if _sha256_bytes(data) != SPLITS_SHA256:
        raise PlanError(f"{SPLITS} is not the registered split file")
    return json.loads(data.decode("utf-8"))


def render_plan(source_dir: Path) -> dict[str, Any]:
    """The plan file: tasks, orders, caps, jobs and the engine arguments (all S1a's but the
    task set, the sessions, the orders and the caps). It reads no outcome."""
    splits = load_splits(source_dir)
    s1a = load_s1a_plan(source_dir)
    pool = tasks(splits["confirm"])
    s1a_pool = list(s1a["base"]) + [t for b in sorted(s1a["extension_blocks"], key=int)
                                    for t in s1a["extension_blocks"][b]]  # fmt: skip
    if sorted(s1a_pool) != pool or len(pool) != 113:
        raise PlanError("E's tasks must be S1a's eligible pool, its base plus extension blocks")
    inputs = cost_inputs(load_cost_model(source_dir))
    job_caps = caps(inputs, len(pool))
    orders = episode_orders(pool)
    plan: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "status": PLAN_STATUS,
        "splits_sha256": SPLITS_SHA256,
        "s1a_plan_sha256": S1A_PLAN_SHA256,
        "cost_model_sha256": COST_MODEL_SHA256,
        "offline_excluded": {t: list(r) for t, r in sorted(P1.OFFLINE_EXCLUDED.items())},
        "tasks": pool,
        "s1a_base": list(s1a["base"]),
        "flagged_tasks": [t for t in P1.FLAGGED_TASKS if t in pool],
        "task_domains": {t: s1a["task_domains"][t] for t in pool},
        "sizes": list(SIZES),
        "size_order": size_order(),
        "sessions": list(SESSIONS),
        "rerun": RERUN,
        "block": BLOCK,
        "job_order": job_order(),
        "episode_orders": orders,
        "episode_orders_sha256": digest(orders),
        "engine_argv": {z: P1.engine_argv(P1.MODEL_DIRS[z], P1.SERVED_NAME) for z in SIZES},
        "sampling": {h: P1.sampling(h) for h in HARNESSES},
        "prompt_date": P1.PROMPT_DATE,
        "n_star": N_STAR,
        "V": V,
        "session_gap_h": SESSION_GAP_H,
        "cost_inputs": inputs,
        "cap_rule": "ceil(3 + (L + (N x slot / V + drain) x 1.2 x 1.05) / 60) minutes per job",
        "caps_minutes": {**{f"E-{z}": job_caps[z] for z in SIZES}, **OVERLAY_CAPS},
        "total_cap_minutes": total_cap_minutes(job_caps),
        "jobs": jobs(job_caps, len(pool)),
    }
    plan["plan_sha256"] = digest(plan)
    return plan


def load_plan(path: Path) -> dict[str, Any]:
    """A plan file whose ``plan_sha256`` matches its body."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in data.items() if k != "plan_sha256"}
    if data.get("plan_sha256") != digest(body):
        raise PlanError(f"{path} does not match its plan_sha256")
    if data.get("experiment_id") != EXPERIMENT_ID or data.get("status") != PLAN_STATUS:
        raise PlanError(f"{path} is not E's registered plan")
    return data


def main(argv: list[str] | None = None) -> int:
    """``render``: write the plan file (never overwrites)."""
    import argparse

    parser = argparse.ArgumentParser(description="successor E plan tools")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("render", help="render the plan file from the committed inputs")
    cmd.add_argument("--source-dir", type=Path, default=Path("."))
    cmd.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; plan files are never overwritten")
    plan = render_plan(args.source_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(plan["plan_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
