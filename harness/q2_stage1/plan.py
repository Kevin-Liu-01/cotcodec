"""The job plan of `q2-stage1-rescoped-v1` (S1a): caps, A0-derived constants and orders.

Everything here is fixed before any confirm-split episode (preregistration sections 5, 6
and 12) and reads no outcome: the caps and the GPU-h count under D22, the remainder rule
for the A1 caps, the K-rule and the anchor-size rule from the A0 records, the CPU
feasibility check, the seeded task draw, the dev and anchor orders, the size order and
the per-block episode orders, and the engine and Slurm arguments each job runs with.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.q2.vm.manifest import HOST_CPUS, runner_cpus

EXPERIMENT_ID = "q2-stage1-rescoped-v1"
SEEDS = (42, 43, 44)
SESSION_SEED = {"S1": 43, "S2": 44}
SIZES = ("4B", "9B")
HARNESSES = ("H-OSW-fixed", "H-GA")
K1_RAW_GOLD_FAILURES = ("0a0faba3", "15aece23", "ac1b39ff", "ed43c15f")

# ---- D22 count (section 6.1) ------------------------------------------------------- #
GPU_MINUTES_LIMIT = 480  # 8 GPU-h of one H100
# The remainder rule shares out 478 minutes, so at least 2 minutes stay unallocated.
ALLOCATABLE_MINUTES = 478
CAP_MINUTES = {"O1": 3, "A0a": 25, "A0b": 26, "O2": 3, "O2_retry": 3, "ANC": 52}
USR1_LEAD_MIN = 3  # --signal=B:USR1@180
LAUNCH_PLAN_MIN = 6  # planning value of L (job start to first dispatched request)
REQUEUE_FACTOR = 1.05  # DR0 tolerates up to 5% first-attempt loss per cell
A0A_FACTOR = 1.25
# The base floor (section 6.2; D47, D49 (i)): 32 without the anchor, whatever is amended;
# 24 only while the anchor runs and the item 18 amendment is signed (pass k_floor=24).
K_FLOOR = 24
K_MAX = 32
EPISODES_PER_TASK_PER_JOB = 4  # 2 harnesses x 2 within-session reruns
ANCHOR_MIN_TASKS = 58
ANCHOR_POOL = 116
ANCHOR_DISPATCH_MARGIN = 1.25
# A0a's gates (section 6.2): the share of model turns that end at 2,048 tokens without a
# complete tool call, per harness, and DesktopEnv.step's p95 against the action path's.
TRUNCATION_GATE = 0.20
STEP_P95_FACTOR = 2.0

# ---- Prices, GPU-h per episode (cost_s1a.json, key "s1a_v2_prices") --------------- #
# T = 15, H2-thinking-screenshot profile, slot = steps + setup (central 90 s, high 180 s)
# + OSWorld's 60 s settle after reset and 20 s before evaluation; max(closed, open loop).
PRICE_CENTRAL = {16: 0.010948, 20: 0.009020}
PRICE_HIGH = {16: 0.012901, 20: 0.011274}
# OpenCUA-7B anchor slot (minutes): the card's H1-screenshot wave at the unmeasured-rung
# rule (x1.5) plus the pinned runner's sleeps (60 s, 20 s, 5 s after each of 15 steps).
ANCHOR_SLOT_MIN = {"central": 11.29, "high": 13.17}
A0A_SLOT_HIGH_MIN = 12.39  # 9B slot at the high price, V = 16

# ---- Prompt date (sections 5.2, 9; design_diffs.md) -------------------------------- #
# Both upstream agents put today's date in the system prompt. S1a pins one date for every
# A0a, ANC and A1 episode, so between-session pairs (at least 12 h apart, usually on
# different days) and within-session pairs see the same prompt; a date change would
# otherwise be a deterministic prompt change confounded with the session.
PROMPT_DATE = "2026-10-08"  # a Thursday; the draft date
PINNED_DATE_PURPOSES = ("a0a", "a0b", "anc", "a1")

# ---- CPUs (section 5.5) ------------------------------------------------------------ #
GPU_JOB_CPUS = 32
VM_CORES = 4
CPU_LIMIT = HOST_CPUS - 8  # leaves the ladder's 8-CPU foreign allowance
VM_JOB_EXTRA_MIN = 10


class PlanError(ValueError):
    """Raised when a plan input is outside the registration."""


# --------------------------------------------------------------------------- concurrency


def a1_concurrency(n_star: int) -> int | None:
    """V per engine for A1 (and A0a) at the ladder's N*; None: S1a does not start."""
    if n_star >= 24:
        return 20
    if n_star >= 16:
        return 16
    return None


def anchor_concurrency(n_star: int) -> int:
    return min(32, n_star)


def vm_job_cpus(v: int) -> int:
    return VM_CORES * v + runner_cpus(v)


def co_running_cpus(vm_concurrencies: Sequence[int], gpu_jobs: int) -> int:
    return gpu_jobs * GPU_JOB_CPUS + sum(vm_job_cpus(v) for v in vm_concurrencies)


def check_cpus(vm_concurrencies: Sequence[int], gpu_jobs: int) -> int:
    """The summed CPUs of co-running S1a jobs; refuses more than CPU_LIMIT."""
    total = co_running_cpus(vm_concurrencies, gpu_jobs)
    if total > CPU_LIMIT:
        raise PlanError(f"co-running S1a jobs need {total} CPUs, above {CPU_LIMIT}")
    return total


# --------------------------------------------------------------------------- caps


def a1_cap_minutes(prefreeze_caps: Sequence[int], anchor_runs: bool, a0b_runs: bool = True) -> int:
    """The A1 cap by the remainder rule (section 6.1), fixed at the freeze.

    ``prefreeze_caps`` lists the cap of every pre-freeze GPU job that ran (O1, A0a, A0b and
    any repeat); O2 and its one pre-funded retry are reserved; ANC is reserved when the
    anchor will run. The four A1 jobs share the rest equally, in whole minutes.
    """
    if anchor_runs and not a0b_runs:
        raise PlanError("ANC runs only after A0b")
    reserved = sum(prefreeze_caps) + CAP_MINUTES["O2"] + CAP_MINUTES["O2_retry"]
    if anchor_runs:
        reserved += CAP_MINUTES["ANC"]
    cap = math.floor((ALLOCATABLE_MINUTES - reserved) / 4)
    if cap <= 0:
        raise PlanError("no A1 time is left under 8 GPU-h")
    return cap


def total_cap_minutes(prefreeze_caps: Sequence[int], anchor_runs: bool, a1_cap: int) -> int:
    reserved = sum(prefreeze_caps) + CAP_MINUTES["O2"] + CAP_MINUTES["O2_retry"]
    if anchor_runs:
        reserved += CAP_MINUTES["ANC"]
    return reserved + 4 * a1_cap


def check_a0_caps(launch_min: float = LAUNCH_PLAN_MIN) -> dict[str, float]:
    """Each A0 job fits L + 1.25 x its high slot (one wave) before its USR1 point."""
    need = {
        "A0a": launch_min + A0A_FACTOR * A0A_SLOT_HIGH_MIN,
        "A0b": launch_min + ANCHOR_DISPATCH_MARGIN * ANCHOR_SLOT_MIN["high"],
    }
    for job, minutes in need.items():
        if minutes > CAP_MINUTES[job] - USR1_LEAD_MIN:
            raise PlanError(f"{job} needs {minutes:.1f} min before USR1")
    return need


# --------------------------------------------------------------------------- A0 constants


def c_a0a(slot_seconds: Sequence[float], concurrency: int) -> float:
    """GPU-h per episode from A0a: summed slot occupancy (dispatch to teardown) / (V x n).

    A0a runs one wave of V episodes at A1's V, so this is A1's cost when the engine is not
    saturated; c_proj's card term covers the saturated regime.
    """
    if not slot_seconds:
        raise PlanError("A0a completed no episode")
    return sum(slot_seconds) / 3600 / (concurrency * len(slot_seconds))


def c_proj(a1_v: int, c_a0a_value: float) -> float:
    return max(PRICE_HIGH[a1_v], A0A_FACTOR * c_a0a_value)


def k_base(a1_cap: int, launch_min: float, c_proj_value: float, k_nstar: int = K_MAX) -> int:
    """K_base = min(K_N*, 8 floor(((T_A1 - 3 - L)/60) / (4 x 1.05 x c_proj) / 8))."""
    usable_h = (a1_cap - USR1_LEAD_MIN - launch_min) / 60
    per_task = EPISODES_PER_TASK_PER_JOB * REQUEUE_FACTOR * c_proj_value
    return min(k_nstar, 8 * math.floor(usable_h / per_task / 8))


def anchor_tasks(
    n_star: int, launch_min_a0b: float, longest_a0b_slot_min: float, anc_cap: int = 0
) -> int:
    """Anchor size: n = min(116, V x floor((T_ANC - 3 - L) / (1.25 d))).

    d is the longer of A0b's longest slot and the card's central anchor slot. ANC is
    submitted only when n >= 58; otherwise the anchor is UNAVAILABLE.
    """
    cap = anc_cap or CAP_MINUTES["ANC"]
    d = max(longest_a0b_slot_min, ANCHOR_SLOT_MIN["central"])
    waves = math.floor((cap - USR1_LEAD_MIN - launch_min_a0b) / (ANCHOR_DISPATCH_MARGIN * d))
    return min(ANCHOR_POOL, anchor_concurrency(n_star) * max(waves, 0))


def anchor_dispatch_allowed(minutes_to_usr1: float, longest_a0b_slot_min: float) -> bool:
    """ANC dispatches a new episode only while 1.25 d fits before the USR1 point."""
    d = max(longest_a0b_slot_min, ANCHOR_SLOT_MIN["central"])
    return minutes_to_usr1 >= ANCHOR_DISPATCH_MARGIN * d


def fill_allowed(c_job_h: float, minutes_to_usr1: float, block_episodes: int = 32) -> bool:
    """Session-1 fill rule: 1.5 x c_job x 32 episodes <= time to USR1 - 10 minutes."""
    return 1.5 * c_job_h * 60 * block_episodes <= minutes_to_usr1 - 10


def quantile(values: Sequence[float], q: float) -> float | None:
    """The action path's quantile (``acceptance.quantile``): the ceil(q n)-th smallest."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(q * len(ordered))) - 1]


def a0a_gates(
    episodes: Iterable[Mapping[str, Any]], action_path_step_p95_s: float
) -> dict[str, Any]:
    """A0a's truncation and concurrency gates (section 6.2) from its step logs.

    ``episodes`` holds A0a's completed (scored) episodes, as for c_A0a, each
    ``{"harness": ..., "steps": [rows of its steps.jsonl]}``. Per harness, the truncation
    share is the model turns whose reply hit the token cap without a complete tool call
    (``truncated`` and not ``complete_tool_call``) over all its model turns. The step p95
    is the action path's statistic (``quantile`` at 0.95 of every ``DesktopEnv.step``'s
    ``timing_s.total``, harnesses pooled), the one the accepted attempt's A1 step p95
    (``action_path_step_p95_s``, its ``step_p95_n1_s``) uses. A gate that cannot be read
    (no turn under a harness, no timed step) does not hold.
    """
    if not (isinstance(action_path_step_p95_s, int | float) and action_path_step_p95_s > 0):
        raise PlanError("the action path's A1 step p95 must be a positive number of seconds")
    turns = dict.fromkeys(HARNESSES, 0)
    cut = dict.fromkeys(HARNESSES, 0)
    times: list[float] = []
    for episode in episodes:
        harness = episode["harness"]
        if harness not in turns:
            raise PlanError(f"unknown harness {harness}")
        for row in episode["steps"]:
            turns[harness] += 1
            cut[harness] += int(bool(row.get("truncated")) and not row.get("complete_tool_call"))
            for executed in row.get("executed") or []:
                total = (executed.get("timing_s") or {}).get("total")
                if isinstance(total, int | float) and not isinstance(total, bool):
                    times.append(float(total))
    share = {h: (cut[h] / turns[h] if turns[h] else None) for h in HARNESSES}
    p95 = quantile(times, 0.95)
    out = {
        "turns": turns,
        "truncated_without_tool_call": cut,
        "truncation_share": share,
        "truncation_gate": TRUNCATION_GATE,
        "steps_timed": len(times),
        "step_p95_s": p95,
        "action_path_step_p95_s": float(action_path_step_p95_s),
        "step_p95_limit_s": STEP_P95_FACTOR * float(action_path_step_p95_s),
    }
    out["problems"] = a0a_gate_problems(out)
    return out


def a0a_gate_problems(gates: Mapping[str, Any]) -> list[str]:
    """What fails in an ``a0a_gates`` result, re-read from its numbers."""
    problems = []
    share = gates.get("truncation_share") or {}
    for harness in HARNESSES:
        value = share.get(harness)
        if not isinstance(value, int | float):
            problems.append(f"truncation gate: no {harness} turn in A0a")
        elif value > TRUNCATION_GATE:
            problems.append(
                f"truncation gate: {value:.3f} of {harness}'s turns hit the token cap without "
                f"a complete tool call (above {TRUNCATION_GATE})"
            )
    p95, reference = gates.get("step_p95_s"), gates.get("action_path_step_p95_s")
    if not isinstance(p95, int | float) or not isinstance(reference, int | float):
        problems.append("concurrency gate: no timed DesktopEnv.step or no action-path p95")
    elif p95 > STEP_P95_FACTOR * reference:
        problems.append(
            f"concurrency gate: DesktopEnv.step p95 {p95:.3f} s above {STEP_P95_FACTOR} x "
            f"the action path's {reference:.3f} s"
        )
    return problems


def load_a0a_episodes(run_dir: Path) -> list[dict[str, Any]]:
    """A0a's completed episodes and their step logs from a lane run directory (the host's
    ``episodes.jsonl`` and ``episodes/<slot>.a<attempt>/steps.jsonl``)."""
    out = []
    lines = (run_dir / "episodes.jsonl").read_text(encoding="utf-8").splitlines()
    for line in lines:
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("status") != "scored":
            continue
        name = f"{str(record['slot']).replace(':', '_')}.a{record['attempt']}"
        steps = run_dir / "episodes" / name / "steps.jsonl"
        rows = [json.loads(x) for x in steps.read_text(encoding="utf-8").splitlines() if x.strip()]
        out.append({"harness": record["harness"], "slot": record["slot"], "steps": rows})
    return out


@dataclass(frozen=True)
class FreezeConstants:
    """What section 3.2 writes into the registration before the freeze."""

    n_star: int
    a1_v: int
    c_a0a: float
    c_proj: float
    launch_a0a_min: float
    a1_cap_min: int
    k_base: int
    k_floor: int
    anchor_tasks: int
    anchor_runs: bool
    total_cap_min: int
    truncation_share: dict[str, float]
    a0a_step_p95_s: float
    action_path_step_p95_s: float

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def freeze_constants(
    *,
    n_star: int,
    a0a_slot_seconds: Sequence[float],
    launch_a0a_min: float,
    prefreeze_caps: Sequence[int],
    anchor_available: bool,
    a0a_gates: Mapping[str, Any],
    launch_a0b_min: float | None = None,
    longest_a0b_slot_min: float | None = None,
    k_floor: int = K_MAX,
) -> FreezeConstants:
    """The registered constants from the A0 records (no outcome is read).

    The floor follows the branch (section 6.2; D47, D49 (i)): 32 when the anchor does not
    run, whatever ``k_floor`` says; 24 only when the anchor runs and ``k_floor=24`` is
    passed, which needs the item 18 amendment (section 18). K_base below the floor sends the
    draft back to review. ``a0a_gates`` is ``a0a_gates(...)``'s result; a failed truncation
    or concurrency gate stops the freeze too.
    """
    if k_floor not in (K_FLOOR, K_MAX):
        raise PlanError("the floor is 24 (anchor running, item 18 signed) or 32")
    problems = a0a_gate_problems(a0a_gates)
    if problems:
        raise PlanError("A0a's gates do not hold, not frozen: " + "; ".join(problems))
    v = a1_concurrency(n_star)
    if v is None:
        raise PlanError("N* < 16: S1a does not start")
    if anchor_available and (launch_a0b_min is None or longest_a0b_slot_min is None):
        raise PlanError("an available anchor needs A0b's launch time and longest slot")
    n_anchor = anchor_tasks(n_star, launch_a0b_min, longest_a0b_slot_min) if anchor_available else 0
    runs = anchor_available and n_anchor >= ANCHOR_MIN_TASKS
    cap = a1_cap_minutes(prefreeze_caps, runs, a0b_runs=anchor_available)
    c = c_a0a(a0a_slot_seconds, v)
    cp = c_proj(v, c)
    k = k_base(cap, launch_a0a_min, cp)
    floor = k_floor if runs else K_MAX
    if k < floor:
        branch = "the anchor runs" if runs else "the anchor does not run"
        raise PlanError(f"K_base {k} is below the floor {floor} ({branch}): back to review")
    total = total_cap_minutes(prefreeze_caps, runs, cap)
    if total > GPU_MINUTES_LIMIT:
        raise PlanError("the caps exceed 8 GPU-h")
    return FreezeConstants(
        n_star=n_star,
        a1_v=v,
        c_a0a=round(c, 6),
        c_proj=round(cp, 6),
        launch_a0a_min=launch_a0a_min,
        a1_cap_min=cap,
        k_base=k,
        k_floor=floor,
        anchor_tasks=n_anchor if runs else 0,
        anchor_runs=runs,
        total_cap_min=total,
        truncation_share={h: round(float(v), 6) for h, v in a0a_gates["truncation_share"].items()},
        a0a_step_p95_s=float(a0a_gates["step_p95_s"]),
        action_path_step_p95_s=float(a0a_gates["action_path_step_p95_s"]),
    )


# --------------------------------------------------------------------------- tasks


def task_pool(confirm_ids: Sequence[str]) -> list[str]:
    return sorted(t for t in confirm_ids if t[:8] not in K1_RAW_GOLD_FAILURES)


def apportion(k: int, counts: Mapping[str, int]) -> dict[str, int]:
    """Plain largest-remainder apportionment of k seats over domains (ties by name)."""
    n = sum(counts.values())
    quota = {d: k * c / n for d, c in counts.items()}
    seats = {d: math.floor(q) for d, q in quota.items()}
    for d in sorted(quota, key=lambda d: (-(quota[d] - seats[d]), d))[: k - sum(seats.values())]:
        seats[d] += 1
    if min(seats.values()) < 1:
        raise PlanError(f"K={k} leaves a domain empty")
    return dict(sorted(seats.items()))


def draw_tasks(pool: Sequence[str], domain: Mapping[str, str], k: int) -> dict[str, Any]:
    """The base set and the extension blocks (section 5.4); K = 24 and 16 nest in K = 32."""
    counts = Counter(domain[t] for t in pool)
    seats = apportion(k, counts)
    base: list[str] = []
    for d in sorted(seats):
        ids = sorted(t for t in pool if domain[t] == d)
        random.Random(f"q2-stage1a:base:42:{d}").shuffle(ids)
        base += ids[: seats[d]]
    rest = sorted(set(pool) - set(base))
    random.Random("q2-stage1a:ext:42").shuffle(rest)
    blocks = [rest[i : i + 8] for i in range(0, len(rest), 8)]
    return {
        "K_base": k,
        "pool_size": len(pool),
        "pool_domains": dict(sorted(counts.items())),
        "seats": seats,
        "base": sorted(base),
        "extension_blocks": blocks,
    }


def dev_tasks(dev_ids: Sequence[str], setup_ok: Mapping[str, bool], n: int = 4) -> list[str]:
    """Filter the dev split by offline setup (G0 item 5), then take the first n of the
    sorted ids shuffled by random.Random("q2-stage1a:dev:42")."""
    ids = sorted(dev_ids)
    random.Random("q2-stage1a:dev:42").shuffle(ids)
    chosen = [t for t in ids if setup_ok.get(t, False)][:n]
    if len(chosen) < n:
        raise PlanError("fewer dev tasks than needed complete their setup offline")
    return chosen


def anchor_order(pool: Sequence[str], domain: Mapping[str, str]) -> list[str]:
    """Domain-stratified anchor order: every prefix is near-proportional by domain.

    Within each domain the sorted ids are shuffled by
    random.Random(f"q2-stage1a:anchor:42:{domain}"); position i takes the domain whose
    taken count lags its proportional share n_d x i / N the most (ties by name).
    """
    by_domain: dict[str, list[str]] = {}
    for d in sorted({domain[t] for t in pool}):
        ids = sorted(t for t in pool if domain[t] == d)
        random.Random(f"q2-stage1a:anchor:42:{d}").shuffle(ids)
        by_domain[d] = ids
    total = len(pool)
    taken = dict.fromkeys(by_domain, 0)
    order: list[str] = []
    for i in range(1, total + 1):
        open_domains = [d for d in by_domain if taken[d] < len(by_domain[d])]
        # Integer lag n_d * i - taken_d * N (exact), largest first, ties by domain name.
        d = min(
            open_domains,
            key=lambda d: (taken[d] * total - len(by_domain[d]) * i, d),
        )
        order.append(by_domain[d][taken[d]])
        taken[d] += 1
    return order


def size_order() -> list[str]:
    """Sizes run one after the other in each session, in this seeded order (both sessions)."""
    sizes = list(SIZES)
    random.Random("q2-stage1a:size-order:42").shuffle(sizes)
    return sizes


def block_order(tasks: Sequence[str], session: str, size: str, block: str) -> list[tuple[str, str]]:
    """The (task, harness) order of one block (harnesses interleaved)."""
    cells = [(t, h) for t in sorted(tasks) for h in HARNESSES]
    seed = SESSION_SEED[session]
    random.Random(f"q2-stage1a:{session}:{size}:{block}:{seed}").shuffle(cells)
    return cells


def episode_orders(draw: Mapping[str, Any]) -> dict[str, list[list[str]]]:
    """Every block's order: base blocks b1 and b2, extension sub-blocks x01.1, x01.2, ..."""
    out: dict[str, list[list[str]]] = {}
    for session in ("S1", "S2"):
        for size in SIZES:
            for block in ("b1", "b2"):
                key = f"{session}:{size}:{block}"
                out[key] = [list(c) for c in block_order(draw["base"], session, size, block)]
            for b, tasks in enumerate(draw["extension_blocks"], start=1):
                for sub in (1, 2):
                    block = f"x{b:02d}.{sub}"
                    key = f"{session}:{size}:{block}"
                    out[key] = [list(c) for c in block_order(tasks, session, size, block)]
    return out


def digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


# --------------------------------------------------------------------------- engines


CARD_ENGINE_FLAGS = (
    "--load-format", "auto",
    "--disable-uvicorn-access-log",
    "--tensor-parallel-size", "1",
    "--dtype", "bfloat16",
    "--seed", "42",
    "--max-model-len", "131072",
    "--gpu-memory-utilization", "0.9",
    "--max-num-seqs", "256",
    "--max-num-batched-tokens", "8192",
    "--enable-prefix-caching",
    "--generation-config", "vllm",
    "--limit-mm-per-prompt", '{"image":{"count":20,"height":1080,"width":1920},"video":0}',
)  # fmt: skip
ANCHOR_MAX_MODEL_LEN = 32768  # OpenCUA-7B derives 128,000; the card's 131,072 is refused
ANCHOR_IMAGE_LIMIT = '{"image":{"count":4,"height":1080,"width":1920},"video":0}'


def engine_argv(model_dir: str, served_name: str, anchor: bool = False) -> list[str]:
    """``vllm serve`` argv: the card's flags (section 4), or the anchor's variant."""
    flags = list(CARD_ENGINE_FLAGS)
    if anchor:
        flags[flags.index("--max-model-len") + 1] = str(ANCHOR_MAX_MODEL_LEN)
        flags[flags.index("--limit-mm-per-prompt") + 1] = ANCHOR_IMAGE_LIMIT
        flags.append("--trust-remote-code")
    return [
        "vllm", "serve", model_dir, "--served-model-name", served_name,
        "--host", "127.0.0.1", "--port", "8000", *flags,
    ]  # fmt: skip


def sampling(harness: str) -> dict[str, Any]:
    """Request sampling for both Qwen harnesses: greedy, top_p and top_k sent explicitly."""
    if harness not in HARNESSES:
        raise PlanError(f"unknown harness {harness}")
    return {"temperature": 0.0, "top_p": 0.9, "top_k": -1, "max_tokens": 2048}


# --------------------------------------------------------------------------- jobs


def session_jobs(n_star: int, a1_cap: int, *, anchor_runs: bool) -> list[dict[str, Any]]:
    """The post-freeze jobs in submission order with their CPU and minute plans.

    Each GPU job waits for its VM job to start (Slurm ``--dependency=after:<vm job>``);
    the VM job's limit is the GPU cap plus 10 minutes. Sizes run one after the other.
    """
    v = a1_concurrency(n_star)
    if v is None:
        raise PlanError("N* < 16: S1a does not start")
    jobs: list[dict[str, Any]] = [{"job": "O2", "gpu_minutes": CAP_MINUTES["O2"]}]
    if anchor_runs:
        va = anchor_concurrency(n_star)
        jobs.append(
            {
                "job": "ANC",
                "gpu_minutes": CAP_MINUTES["ANC"],
                "vm_concurrency": va,
                "vm_cpus": vm_job_cpus(va),
                "vm_minutes": CAP_MINUTES["ANC"] + VM_JOB_EXTRA_MIN,
                "co_running_cpus": check_cpus([va], 1),
            }
        )
    for session in ("S1", "S2"):
        for size in size_order():
            jobs.append(
                {
                    "job": f"A1-{size}-{session}",
                    "gpu_minutes": a1_cap,
                    "vm_concurrency": v,
                    "vm_cpus": vm_job_cpus(v),
                    "vm_minutes": a1_cap + VM_JOB_EXTRA_MIN,
                    "co_running_cpus": check_cpus([v], 1),
                }
            )
    return jobs


def gpu_sbatch_time(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}:00"


# --------------------------------------------------------------------------- the plan file

#: Tasks in the flagged-task sensitivity (section 8): the P1 save-flip tasks whose saved gold
#: both raters accept, the P1 raw flip whose saved gold both reject, the two confirmed false
#: positives, and the two false-positive candidates whose label the raters contradicted
#: (pending Kevin's adjudication; a434992a is also the uncorrected tolerant-family z-order
#: false negative).
FLAGGED_TASKS = (
    "9ec204e4-f0a3-42f8-8458-b772a6797cab",
    "b8adbc24-cef2-4b15-99d5-ecbe7ff445eb",
    "30e3e107-1cfb-46ee-a755-2cd080d7ba6a",
    "70bca0cc-c117-427e-b0be-4df7299ebeb6",
    "d53ff5ee-3b1a-431e-b2be-30ed2673079b",
    "358aa0a7-6677-453f-ae35-e440f004c31e",
    "a434992a-89df-4577-925c-0c58b747f0f4",
)
MODEL_DIRS = {
    "4B": "/model-cache/cotcodec-models/qwen3.5-4b",
    "9B": "/model-cache/cotcodec-models/qwen3.5-9b",
    "anchor": "/model-cache/cotcodec-models/opencua-7b",
}
SERVED_NAME = "s1a-model"


def render_plan(
    *,
    confirm_ids: Sequence[str],
    dev_ids: Sequence[str],
    domain: Mapping[str, str],
    splits_sha256: str,
    constants: FreezeConstants | None = None,
    dev_setup_ok: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """The plan file: draw, orders, jobs and engine arguments. With ``constants`` it is the
    frozen plan; without, the draft plan at the largest base (K = 32) with no jobs."""
    pool = task_pool(confirm_ids)
    k = constants.k_base if constants else K_MAX
    draw = draw_tasks(pool, domain, k)
    orders = episode_orders(draw)
    anchor = anchor_order(pool, domain)
    plan: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "status": "frozen-constants" if constants else "draft",
        "splits_sha256": splits_sha256,
        "base": draw["base"],
        "seats": draw["seats"],
        "extension_blocks": {str(i): b for i, b in enumerate(draw["extension_blocks"], 1)},
        "flagged_tasks": [t for t in FLAGGED_TASKS if t in pool],
        "task_domains": {t: domain[t] for t in pool},
        "size_order": size_order(),
        "episode_orders_sha256": digest(orders),
        "anchor_order": anchor,
        "anchor_order_sha256": digest(anchor),
        "engine_argv": {size: engine_argv(MODEL_DIRS[size], SERVED_NAME) for size in SIZES},
        "anchor_engine_argv": engine_argv(MODEL_DIRS["anchor"], SERVED_NAME, anchor=True),
        "sampling": {h: sampling(h) for h in HARNESSES},
        "prompt_date": PROMPT_DATE,
        "caps_minutes": dict(CAP_MINUTES),
    }
    if dev_setup_ok is not None:
        plan["dev_tasks_a0b"] = dev_tasks(dev_ids, dev_setup_ok, 4)
    if constants:
        plan["constants"] = constants.as_dict()
        plan["anchor_tasks"] = anchor[: constants.anchor_tasks]
        plan["jobs"] = session_jobs(
            constants.n_star, constants.a1_cap_min, anchor_runs=constants.anchor_runs
        )
        if dev_setup_ok is not None:
            plan["dev_tasks_a0a"] = dev_tasks(dev_ids, dev_setup_ok, constants.a1_v // 4)
    plan["plan_sha256"] = digest(plan)
    return plan


# --------------------------------------------------------------------------- command line


def main(argv: list[str] | None = None) -> int:
    """``a0a-gates``: A0a's gates from its lane run directory (on the host), as the
    ``a0a_gates`` input of the freeze constants (``scripts/render_q2_stage1_plan.py``)."""
    import argparse

    parser = argparse.ArgumentParser(description="S1a plan tools")
    sub = parser.add_subparsers(dest="command", required=True)
    gates = sub.add_parser("a0a-gates", help="A0a's truncation and concurrency gates")
    gates.add_argument("--run-dir", type=Path, required=True)
    gates.add_argument("--action-path-step-p95", type=float, required=True)
    args = parser.parse_args(argv)
    result = a0a_gates(load_a0a_episodes(args.run_dir), args.action_path_step_p95)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 3 if result["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
