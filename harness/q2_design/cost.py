"""Cost model for successor designs, from S1a's realized cost (costs.json, lane receipts).

Each A1 job held one H100 engine and a pool of V VMs; the engine never queued a request
(RESULTS.md: queue time below 0.01 ms per request), so a job's GPU time is set by the VM
slots, not by the GPU. Each job's Slurm elapsed time decomposes, from its lane receipt and
records, as

    elapsed = L (Slurm start to first dispatch: engine start-up and first boot)
              + sum(slot occupancy) / V
              + drain (the last wave: VMs idle while the final episodes finish)

and a successor job with N episodes on tasks with mean slot s at the same V is priced as
L + N s / V + drain. Slots are measured per (size, task) in S1a (both harnesses, all four
jobs), so a design on other pool tasks is priced on those tasks' slots.

Accounting. The program counts registered caps, not usage (D22), against 8 GPU-h (D20,
D24): S1a's caps summed to at most 478 minutes. A successor's job cap here is
3 min (USR1 lead) + L + (N s / V + drain) x 1.2 (DR4: projections use realized cost x 1.2)
x 1.05 (the K-rule's re-queue allowance), rounded up to whole minutes; one overlay build
from the freeze commit and its pre-funded retry (3 + 3 minutes, as O2) are reserved.

CPU constraint (``harness.q2_stage1.plan``): a GPU job takes 32 CPUs, a VM job 4V +
runner_cpus(V), and co-running jobs must stay at or below 200 of the host's 208. At V = 20
one (size, session) pair takes 122, so pairs run one after the other (two at once need
244). V = 20 is the card's measured value and the only one A1 ran; V = 32 fits (176 CPUs)
and is within the action path's qualified N* = 32, but would need its own step-p95 gate
under load, so it is reported as an option only.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np

from harness.q2_design import data as D
from harness.q2_design.model import Design
from harness.q2_stage1 import plan as P
from harness.q2_stage1 import records as R

V_REGISTERED = 20
USR1_LEAD_MIN = 3
OVERLAY_MIN = 3 + 3  # O2-type overlay build and its pre-funded retry
CAP_TOTAL_MIN = 478  # S1a's maximum (7.967 GPU-h): at least 2 of 480 minutes unallocated
DR4_FACTOR = 1.2
REQUEUE_FACTOR = 1.05
BUDGET_GPU_H = 8.0


def job_timing(root: Path = Path(".")) -> dict[str, Any]:
    """Per A1 job: elapsed, start-up L, summed slots, drain, from receipt and records."""
    costs = json.loads((root / D.COSTS).read_text(encoding="utf-8"))
    out = {}
    for job, run in D.JOB_DIRS.items():
        receipt = json.loads((root / run / "lane-receipt.json").read_text(encoding="utf-8"))
        rows = R.read_jsonl(root / run / "episodes.jsonl")
        start = float(receipt["gpu_job_end"]["start_epoch"])
        end = float(receipt["gpu_job_end"]["end_epoch"])
        v = int(costs[job]["V"])
        occ = np.array([float(r["host"]["slot_occupancy_s"]) for r in rows])
        first = min(float(r["host"]["t_dispatch"]) for r in rows)
        elapsed = end - start
        if abs(elapsed - float(costs[job]["gpu_elapsed_s"])) > 1e-6:
            raise ValueError(f"{job}: receipt elapsed differs from costs.json")
        startup = first - start
        out[job] = {
            "size": costs[job]["size"],
            "V": v,
            "episodes": len(rows),
            "elapsed_s": elapsed,
            "startup_s": startup,
            "slot_sum_over_V_s": float(occ.sum() / v),
            "drain_s": elapsed - startup - float(occ.sum() / v),
            "mean_slot_s": float(occ.mean()),
            "gpu_h_per_episode": float(costs[job]["gpu_h_per_episode"]),
            "vm_h_per_episode": float(costs[job]["vm_h_per_episode"]),
        }
    return out


class CostModel:
    """Prices a design from S1a's per-job overheads and per-task slot occupancies."""

    def __init__(self, timing: Mapping[str, Any], slot_s: Mapping[tuple[str, str], float]):
        self.timing = dict(timing)
        self.slot_s = dict(slot_s)
        self.startup_s = max(j["startup_s"] for j in timing.values())
        self.drain_s = {
            z: max(j["drain_s"] for j in timing.values() if j["size"] == z) for z in R.SIZES
        }

    def mean_slot(self, size: str, tasks: Iterable[str]) -> float:
        return float(np.mean([self.slot_s[(size, t)] for t in tasks]))

    def job(self, size: str, n_episodes: int, mean_slot_s: float, v: int = V_REGISTERED):
        work_s = n_episodes * mean_slot_s / v + self.drain_s[size]
        physical_s = self.startup_s + work_s
        cap_min = math.ceil(
            USR1_LEAD_MIN + (self.startup_s + work_s * DR4_FACTOR * REQUEUE_FACTOR) / 60
        )
        return {"physical_gpu_h": physical_s / 3600, "cap_min": cap_min,
                "wall_h": physical_s / 3600}  # fmt: skip

    def design(
        self, design: Design, tasks: Iterable[str] | None = None, v: int = V_REGISTERED
    ) -> dict[str, Any]:
        """Physical GPU-h, registered caps and VM-h for a design (one job per size x session).

        ``tasks`` are the design's pool tasks; by default the pool's mean slot is used for
        designs that draw from the pool and the base's for ``tasks='base'``."""
        if tasks is None:
            pool = sorted({t for (_z, t) in self.slot_s})
            tasks = self._base if design.tasks == "base" else pool
        tasks = list(tasks)
        n_job = design.K * 2 * design.R
        jobs, phys, caps, vm_h = [], 0.0, 0, 0.0
        for z in design.sizes:
            s = self.mean_slot(z, tasks)
            for _ in range(design.S):
                j = self.job(z, n_job, s, v)
                jobs.append({"size": z, "episodes": n_job, "mean_slot_s": s, **j})
                phys += j["physical_gpu_h"]
                caps += j["cap_min"]
                vm_h += n_job * s / 3600
        total_caps = caps + OVERLAY_MIN
        return {
            "episodes": design.episodes,
            "jobs": len(jobs),
            "physical_gpu_h": phys,
            "physical_gpu_h_per_episode": phys / design.episodes,
            "caps_min": total_caps,
            "caps_gpu_h": total_caps / 60,
            "within_478_min": total_caps <= CAP_TOTAL_MIN,
            "vm_h": vm_h,
            "wall_h_sequential": sum(j["wall_h"] for j in jobs),
            "cpus_per_pair": P.vm_job_cpus(v) + P.GPU_JOB_CPUS,
            "pairs_at_once": max(1, P.CPU_LIMIT // (P.vm_job_cpus(v) + P.GPU_JOB_CPUS)),
            "per_job": jobs,
        }

    _base: list[str] = []

    def max_tasks(
        self, S: int, R_: int, sizes: tuple[str, ...] = R.SIZES, v: int = V_REGISTERED,
        tasks_pool: list[str] | None = None,
    ) -> int:  # fmt: skip
        """The largest K (at the pool's mean slot) whose caps fit 478 minutes."""
        best = 0
        for k in range(2, 1000):
            d = Design(K=k, S=S, R=R_, sizes=sizes, tasks="srs")
            if self.design(d, tasks_pool, v)["within_478_min"]:
                best = k
            else:
                break
        return best


def build(root: Path = Path("."), s1a: D.S1aData | None = None) -> tuple[CostModel, dict]:
    s1a = s1a or D.load(root)
    timing = job_timing(root)
    model = CostModel(timing, s1a.slot_s)
    model._base = list(s1a.base)
    return model, timing


def summary(model: CostModel, timing: Mapping[str, Any], s1a: D.S1aData) -> dict[str, Any]:
    """The cost card a design comparison reads."""
    pool, base = list(s1a.pool), list(s1a.base)
    by_size = {}
    for z in R.SIZES:
        jobs = [j for j in timing.values() if j["size"] == z]
        sb, sp = model.mean_slot(z, base), model.mean_slot(z, pool)
        marginal = sp / V_REGISTERED / 3600
        by_size[z] = {
            "realized_gpu_h_per_episode_jobs": [j["gpu_h_per_episode"] for j in jobs],
            "realized_vm_h_per_episode_jobs": [j["vm_h_per_episode"] for j in jobs],
            "mean_slot_s_base": sb,
            "mean_slot_s_pool": sp,
            "marginal_gpu_h_per_episode_pool_V20": marginal,
            "planning_gpu_h_per_episode_pool_V20": marginal * DR4_FACTOR * REQUEUE_FACTOR,
            "drain_s": model.drain_s[z],
        }
    per_ep = float(np.mean([by_size[z]["marginal_gpu_h_per_episode_pool_V20"] for z in R.SIZES]))
    overhead_job_h = (model.startup_s + float(np.mean(list(model.drain_s.values())))) / 3600
    structures = []
    for sizes in (R.SIZES, ("9B",)):
        for S, R_ in ((2, 2), (2, 1), (3, 1), (3, 2), (4, 1), (4, 2), (5, 1), (6, 1), (8, 1)):
            k = model.max_tasks(S, R_, sizes, tasks_pool=pool)
            kp = max(2, min(k, len(pool)))
            d = model.design(Design(K=kp, S=S, R=R_, sizes=sizes, tasks="srs"), pool)
            structures.append({
                "sizes": list(sizes), "S": S, "R": R_, "K_max_caps_478": k,
                "K": kp, "episodes": d["episodes"], "jobs": d["jobs"],
                "caps_min": d["caps_min"], "physical_gpu_h": round(d["physical_gpu_h"], 4),
                "vm_h": round(d["vm_h"], 1), "wall_h_sequential": round(d["wall_h_sequential"], 2),
            })  # fmt: skip
    s1a_design = model.design(Design(K=32, S=2, R=2, tasks="base"))
    return {
        "V": V_REGISTERED,
        "cpu": {
            "host_cpus": P.HOST_CPUS,
            "limit": P.CPU_LIMIT,
            "gpu_job": P.GPU_JOB_CPUS,
            "vm_job_V20": P.vm_job_cpus(20),
            "pair_V20": P.vm_job_cpus(20) + P.GPU_JOB_CPUS,
            "pair_V32": P.vm_job_cpus(32) + P.GPU_JOB_CPUS,
            "pairs_at_once_V20": P.CPU_LIMIT // (P.vm_job_cpus(20) + P.GPU_JOB_CPUS),
        },
        "jobs": dict(timing),
        "startup_s_max": model.startup_s,
        "by_size": by_size,
        "overhead_per_job_gpu_h": overhead_job_h,
        "marginal_gpu_h_per_episode_pool_mean": per_ep,
        "planning_gpu_h_per_episode_pool_mean": per_ep * DR4_FACTOR * REQUEUE_FACTOR,
        "episodes_per_8_gpu_h_physical": {
            f"{j}_jobs": int((BUDGET_GPU_H - j * overhead_job_h) / per_ep)
            for j in (4, 6, 8, 12, 16)
        },
        "structures_within_478_cap_minutes": structures,
        "s1a_base_design_repriced": {
            k: s1a_design[k] for k in ("episodes", "physical_gpu_h", "caps_min", "vm_h")
        },
        "rules": {
            "cap_per_job_min": "ceil(3 + L/60 + (N * slot / V + drain) * 1.2 * 1.05 / 60)",
            "reserved_min": OVERLAY_MIN,
            "cap_total_min": CAP_TOTAL_MIN,
        },
    }
