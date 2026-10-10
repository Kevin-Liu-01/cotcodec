"""Synthetic S1a A1 data for the operator-script tests (ops/s1a-analysis). No real record.

Records follow the episode driver's schema (``harness.q2_stage1.driver.Runner.record``): status,
score, steps, ``ended``, ``tokens``, ``guest_server_restarts``, ``observations``, ``setup``
replies, ``postconfig_replies`` and the counts the analysis reads. ``write_scenario`` lays the
jobs out as lane run directories (``manifest.json``, ``episodes.jsonl``, ``lane-receipt.json``
with host snapshots, ``episodes/<slot>.a<n>/steps.jsonl`` and a capture marker), writes
rescoring rows in ``rescore.rescore_episode``'s shape, merges them with the frozen
``rescore.merge``, and runs the frozen ``rules dr0`` and ``analysis costs`` steps, as the
runbook does.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from harness.q2_stage1 import analysis as A
from harness.q2_stage1 import plan as P
from harness.q2_stage1 import records as R
from harness.q2_stage1 import rescore, rules

BASE = [f"b{i:02d}" for i in range(8)]
EXT = {"1": ["e01", "e02"], "2": ["e03", "e04"]}
TASKS = BASE + EXT["1"] + EXT["2"]
DOMAINS = {t: ("libreoffice_impress" if i % 3 == 0 else "os") for i, t in enumerate(TASKS)}
PLAN: dict[str, Any] = {
    "base": BASE,
    "extension_blocks": EXT,
    "flagged_tasks": ["b00"],
    "task_domains": DOMAINS,
    "offline_excluded": {t: list(r) for t, r in sorted(P.OFFLINE_EXCLUDED.items())},
    "setup_check_sha256": P.SETUP_CHECK_SHA256,
    "constants": {"anchor_runs": False, "a1_v": 20},
    "anchor_tasks": [],
}
JOBS = P.a1_job_order()  # A1-9B-S1, A1-4B-S1, A1-9B-S2, A1-4B-S2
VM = {job: str(3000 + 3 * i) for i, job in enumerate(JOBS)}
GPU = {job: str(3002 + 3 * i) for i, job in enumerate(JOBS)}
LOSS_TYPES = ("transport", "guest_observation", "guest_server_restart", "task_setup", "vm_boot")
POSTCONFIG_TYPES = ("activate_window", "execute", "close_window")


def h(*parts: Any) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def _slots(job: str) -> list[dict[str, Any]]:
    _, size, session = job.split("-")
    out = []
    index = 0
    for rerun in R.RERUNS:
        for t in BASE:
            for harness in R.HARNESSES:
                out.append(
                    {
                        "job": job,
                        "size": size,
                        "session": session,
                        "task_id": t,
                        "harness": harness,
                        "rerun": rerun,
                        "extension_block": None,
                        "block": f"base.{rerun}",
                        "slot": f"{job}:base.{rerun}:{index:03d}",
                    }
                )
                index += 1
    for block, tasks in EXT.items():
        for rerun in R.RERUNS:
            for t in tasks:
                for harness in R.HARNESSES:
                    out.append(
                        {
                            "job": job,
                            "size": size,
                            "session": session,
                            "task_id": t,
                            "harness": harness,
                            "rerun": rerun,
                            "extension_block": int(block),
                            "block": f"x{int(block):02d}",
                            "slot": f"{job}:x{int(block):02d}:{index:03d}",
                        }
                    )
                    index += 1
    return out


def _episode(slot: Mapping[str, Any], attempt: int, rng: np.random.Generator, s: Mapping[str, Any]):
    rec: dict[str, Any] = {
        "schema": R.SCHEMA,
        **slot,
        "attempt": attempt,
        "status": "scored",
        "infrastructure_type": None,
        "score": 0.0,
        "metric_exception": False,
        "steps": 0,
        "truncated_steps": 0,
        "truncated_no_tool_call_steps": 0,
        "ir_errors": 0,
        "uncertified_key_actions": 0,
        "context_fallbacks": 0,
        "ended": None,
        "host": {"slot_occupancy_s": round(float(rng.uniform(150, 600)), 3)},
        "setup": {
            "steps": 1,
            "failures": [],
            "replies": [
                {
                    "path": "/setup/execute",
                    "phase": "setup",
                    "status": 200,
                    "returncode": 0,
                    "step": 1,
                    "type": "execute",
                }
            ],
        },
    }
    return rec


def make_records(
    *,
    jobs: Sequence[str] = JOBS,
    seed: int = 0,
    p: float = 0.35,
    harness_effect: float = 0.0,
    task_sd: float = 0.25,
    floor_4b: bool = False,
    loss_every: int = 37,
    cut: Mapping[str, float] | None = None,
    all_infra: Sequence[str] = (),
    fractional: int = 0,
    trunc: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Every attempt of the jobs that ran. ``cut``: job -> share of its base slots cut by
    USR1 (and every extension slot); ``all_infra``: jobs whose every attempt is lost;
    ``loss_every``: every n-th slot loses its first attempt (half of those lose the re-queue
    too), deterministic so that DR0 fires only where a scenario wants it; ``fractional``: base
    episodes given a score strictly between 0 and 1."""
    rng = np.random.default_rng(seed)
    offset = {t: float(rng.normal(0, task_sd)) for t in TASKS}
    effect = {t: float(rng.normal(harness_effect, 0.1 if harness_effect else 0.0)) for t in TASKS}
    trunc = dict(trunc or {})
    out: list[dict[str, Any]] = []
    for job in jobs:
        slots = _slots(job)
        n_base = sum(1 for sl in slots if sl["extension_block"] is None)
        n_cut = int(round((cut or {}).get(job, 0.0) * n_base))
        for i, slot in enumerate(slots):
            size, harness = slot["size"], slot["harness"]
            if n_cut and (i >= n_base - n_cut):  # the rest of the base, then every fill block
                out.append(
                    {
                        **_episode(slot, 1, rng, {}),
                        "status": "cap_truncated",
                        "score": None,
                        "ended": None,
                    }
                )
                continue
            attempts = 1
            lost_first = job in all_infra or bool(loss_every and i % loss_every == loss_every // 2)
            if lost_first:
                attempts = 2
            for attempt in range(1, attempts + 1):
                rec = _episode(slot, attempt, rng, {})
                lost = (
                    job in all_infra
                    or (attempt == 1 and lost_first)
                    or (attempt == 2 and (i // max(loss_every, 1)) % 2 == 1)
                )
                if lost:
                    kind = LOSS_TYPES[int(rng.integers(len(LOSS_TYPES)))]
                    rec.update(
                        status="infrastructure",
                        infrastructure_type=kind,
                        score=None,
                        ended="infra",
                        steps=int(rng.integers(0, 6)),
                        guest_server_restarts=int(kind == "guest_server_restart"),
                    )
                    if kind == "task_setup":
                        rec["setup"]["replies"].append(
                            {
                                "path": "/setup/execute",
                                "phase": "setup",
                                "status": 500,
                                "step": 2,
                                "type": "execute",
                            }
                        )
                        rec["setup"]["failures"] = ["setup step 2 (execute): HTTP 500"]
                    rec["observations"] = {
                        "agent": {
                            "calls": 2,
                            "retried": 0,
                            "slow": 0,
                            "undelivered": int(kind == "guest_observation"),
                        },
                        "slow_s": 30.0,
                    }
                    out.append(rec)
                    continue
                pr = (
                    p
                    + offset[slot["task_id"]]
                    + (0.5 if harness == "H-GA" else -0.5) * effect[slot["task_id"]]
                )
                if floor_4b and size == "4B":
                    pr = 0.01
                success = rng.random() < float(np.clip(pr, 0.0, 1.0))
                steps = (
                    int(rng.integers(2, 15))
                    if success
                    else (15 if rng.random() < 0.6 else int(rng.integers(1, 15)))
                )
                ended = (
                    "terminate_success"
                    if success
                    else ("step_cap" if steps == 15 else "terminate_failure")
                )
                if success and rng.random() < 0.2:
                    steps, ended = 15, "step_cap"  # a success that ran to the cap
                share = trunc.get(f"{size}/{harness}", 0.02)
                no_tool = int(rng.binomial(steps, share))
                any_cap = no_tool + int(rng.binomial(steps - no_tool, 0.02))
                replies = []
                for k, kind in enumerate(POSTCONFIG_TYPES[: int(rng.integers(0, 3))], 1):
                    u = rng.random()
                    reply = (
                        {"status": 500}
                        if u < 0.04
                        else {"status": None}
                        if u < 0.06
                        else {"status": 200, "returncode": 1}
                        if u < 0.1
                        else {"status": 404}
                        if u < 0.12
                        else {"status": 200, "returncode": 0}
                    )
                    replies.append(
                        {
                            "path": f"/setup/{kind}",
                            "phase": "evaluate",
                            "step": k,
                            "type": kind,
                            **reply,
                        }
                    )
                metric = rng.random() < 0.02
                rec.update(
                    steps=steps,
                    ended=ended,
                    truncated_steps=any_cap,
                    truncated_no_tool_call_steps=no_tool,
                    ir_errors=int(rng.binomial(steps, 0.02)),
                    uncertified_key_actions=int(rng.random() < 0.05),
                    tokens={"prompt": steps * 3000, "completion": steps * 250 + any_cap * 1800},
                    guest_server_restarts=0,
                    observations={
                        "agent": {
                            "calls": steps + 1,
                            "retried": int(rng.random() < 0.05),
                            "slow": int(rng.random() < 0.02),
                            "undelivered": 0,
                        },
                        "checker": {
                            "calls": 2,
                            "retried": int(rng.random() < 0.03),
                            "slow": 0,
                            "undelivered": 0,
                        },
                        "slow_s": 30.0,
                    },
                    postconfig_replies=replies,
                    postconfig_failures=sum(
                        1
                        for r in replies
                        if r.get("status") != 200 or r.get("returncode") not in (None, 0)
                    ),
                    metric_exception=metric,
                    score=0.0 if metric else (1.0 if success else 0.0),
                    checker_input_sha256={
                        "/home/user/out": h(slot["task_id"], harness, "same")
                        if rng.random() < 0.3
                        else h(slot["slot"], attempt)
                    },
                    last_action_kind="DONE" if ended == "terminate_success" else "FAIL",
                )
                if metric:
                    rec["metric_error"] = "ValueError: synthetic"
                out.append(rec)
    if fractional:
        base_scored = [
            i
            for i, r in enumerate(out)
            if r["status"] == "scored"
            and r["extension_block"] is None
            and not r["metric_exception"]
        ]
        for i in base_scored[:: max(1, len(base_scored) // fractional)][:fractional]:
            out[i]["score"] = 0.83
    return out


def rescored_rows(records: Iterable[Mapping[str, Any]], seed: int = 1) -> list[dict[str, Any]]:
    """Rows in ``rescore.rescore_episode``'s shape for every scored attempt: the corrected
    comparator applies to the impress tasks (some false negatives corrected), and a few
    replays on other tasks mismatch the live score."""
    rng = np.random.default_rng(seed)
    out = []
    for rec in records:
        if rec["status"] != "scored":
            continue
        applies = DOMAINS[rec["task_id"]] == "libreoffice_impress"
        raw = float(rec["score"])
        if not applies and rng.random() < 0.03:
            raw = 1.0 - float(raw == 1.0)  # a replay mismatch
        corrected = raw
        if applies and raw == 0.0 and rng.random() < 0.15:
            corrected = 1.0
        out.append(
            {
                "slot": rec["slot"],
                "attempt": rec["attempt"],
                "task_id": rec["task_id"],
                "live_score": rec["score"],
                "raw": raw,
                "raw_state": raw,
                "corrected": corrected,
                "corrected_state": corrected,
                "corrected_applies": applies,
                "live_offline_match": float(rec["score"]) == raw,
            }
        )
    return out


def _jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    return path


def write_scenario(
    root: Path, records: Sequence[Mapping[str, Any]], *, plan=PLAN, rescore_rows=True
) -> dict:
    """Lane run directories, rescoring rows, merged records, DR0 outputs and costs.json."""
    root.mkdir(parents=True, exist_ok=True)
    plan_path = root / "plan.json"
    plan_path.write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
    analysis = root / "A"
    jobs = [job for job in JOBS if any(r["job"] == job for r in records)]
    runs: dict[str, Path] = {}
    dr0_paths: list[Path] = []
    merged_paths: list[Path] = []
    t0 = 1_791_700_000.0
    for i, job in enumerate(jobs):
        _, size, session = job.split("-")
        run_dir = root / "runs" / VM[job]
        rows = [r for r in records if r["job"] == job]
        (run_dir).mkdir(parents=True)
        (run_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "purpose": "a1",
                    "name": f"a1-{size.lower()}-{session.lower()}",
                    "a1": {"size": size, "session": session},
                    "vm": {"concurrency": 20},
                }
            )
        )
        _jsonl(run_dir / "episodes.jsonl", rows)
        start = t0 + i * 20_000
        snapshots = [
            {
                "block": block,
                "t": start + k,
                "loadavg": ["2.5", "1.5", "0.9"],
                "containers_running_total": 21,
                "containers_ours": 20,
                "squeue_foreign": [
                    [GPU[job], "kevin", "RUNNING", "32", "gres:gpu:h100:1", f"q2s1a-{job}"],
                    [
                        "777",
                        "someone",
                        "RUNNING" if k else "PENDING",
                        "4",
                        "(null)",
                        "private-name",
                    ],
                    ["778", "kevin", "PENDING", "8", "(null)", "q2s1a-next"],
                ],
            }
            for k, block in enumerate(("start", "base.1", "end"))
        ]
        receipt = {
            "schema": "q2-stage1a-lane-receipt-v1",
            "job_id": VM[job],
            "purpose": "a1",
            "gpu_job": {"job_id": GPU[job], "start_epoch": start, "state": "RUNNING"},
            "gpu_job_end": {
                "job_id": GPU[job],
                "start_epoch": start,
                "state": "COMPLETED",
                "end_epoch": start + 6000 + 300 * i,
            },
            "bridge_dir": None,
            "snapshots": snapshots,
        }
        (run_dir / "lane-receipt.json").write_text(json.dumps(receipt, sort_keys=True))
        for rec in rows:
            if rec["status"] not in ("scored", "infrastructure") or not rec.get("steps"):
                continue
            ep = run_dir / "episodes" / f"{rec['slot'].replace(':', '_')}.a{rec['attempt']}"
            steps = [
                {
                    "step": k,
                    "processed_sha256": h(
                        "shot", rec["task_id"], rec["harness"], k if k > 1 else rec["slot"]
                    ),
                    "messages_sha256": h("msg", rec["slot"], k),
                    "ir_sha256": h("ir", rec["task_id"], k),
                    "prompt_sha256": h("p", k),
                }
                for k in range(1, rec["steps"] + 1)
            ]
            _jsonl(ep / "steps.jsonl", steps)
            if rec["status"] == "scored":
                (ep / "capture").mkdir(parents=True, exist_ok=True)
                (ep / "capture" / "capture.json").write_text("{}")
        runs[job] = run_dir
        rescored = rescored_rows(rows, seed=i) if rescore_rows else []
        rescore_dir = analysis / f"rescore-{VM[job]}"
        _jsonl(rescore_dir / "rescored.jsonl", rescored)
        merged = list(rescore.merge(rows, rescored))
        merged_paths.append(_jsonl(analysis / f"merged-{VM[job]}.jsonl", merged))
        dr0 = rules.run_dir_dr0(run_dir, plan)
        dr0_path = analysis / f"dr0-{VM[job]}.json"
        dr0_path.write_text(json.dumps(dr0, indent=1, sort_keys=True))
        dr0_paths.append(dr0_path)
    a1 = analysis / "a1.jsonl"
    a1.write_text("".join(p.read_text(encoding="utf-8") for p in merged_paths), encoding="utf-8")
    costs = analysis / "costs.json"
    args = []
    for run_dir in runs.values():
        args += ["--run-dir", str(run_dir)]
    A.costs_main([*args, "--out", str(costs)])
    return {
        "root": root,
        "plan": plan_path,
        "analysis": analysis,
        "records": a1,
        "costs": costs,
        "runs": runs,
        "dr0": dr0_paths,
    }


SCENARIOS: dict[str, dict[str, Any]] = {
    "null": {},
    "harness": {"harness_effect": 0.5, "seed": 2},
    "session": {"seed": 3, "trunc": {"4B/H-GA": 0.3}, "loss_every": 31},
    "floor": {"seed": 4, "floor_4b": True},
    "dr0": {"seed": 5, "jobs": JOBS[:1], "loss_every": 6},
    "dr0late": {"seed": 6, "jobs": JOBS[:3]},
    "baseincomplete": {"seed": 7, "cut": {"A1-4B-S2": 0.4}},
    "s2allinfra": {"seed": 8, "jobs": JOBS[:3], "all_infra": (JOBS[2],)},
    "fractional": {"seed": 9, "fractional": 5},
}
