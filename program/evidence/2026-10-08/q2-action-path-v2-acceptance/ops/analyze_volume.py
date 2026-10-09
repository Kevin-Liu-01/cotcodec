#!/usr/bin/env python3
"""The volume campaigns of q2-action-path-v2: A4 (volume) and A7 (observation service) at N*.

Runs on the host from the read-only export of the frozen commit: it imports that export's
``harness.q2.action_path.acceptance`` (frozen in the inputs addendum and pinned again in the
executor addendum). It first computes N* exactly as the ladder stage did, with
``acceptance.n_star`` over attempt 1's A1 campaigns and attempt 1's ladder (every attempt of
each rung, in the order it ran), and then calls ``acceptance.a4(campaigns, n_star)`` or
``acceptance.a7(campaigns, n_star)`` on the campaign's attempts as ``acceptance.load`` reads
them from the run directories. Every judgement is the frozen code's: A4's zero failures
(restart-only trials excused, decisions D30 and D33), the plan tiling and realized order,
the end state and the concurrency; A7's restarts of every attempt over the counting
attempts' accessibility calls, capped at the plan's 39,036, against 5 x 10^-4.

What this script adds is reported, never judged (section 12):

* per attempt: end state, counting problems, boots, steps, failed and excused trials,
  infrastructure types, observation retries, undelivered reset observations, session
  errors, restarts and accessibility calls, overlay growth, the CPU sets and the host
  snapshots' foreign jobs, load averages and container counts;
* A4: per-entry trials and passes per setting beside the plan's repetitions and per-entry
  bound, the device actions per class of the trials that ran beside the plan's (from
  ``volume_plan.json``'s per-entry class counts), and every session's result;
* A7: the restarts and accessibility calls of every session, and the N* it ran at.

    python3 -B analyze_volume.py EXPORT RUNS OUT_DIR ATTEMPTS_A1.json ATTEMPTS_LADDER.json \\
        {A4,A7} ATTEMPTS.json

ATTEMPTS_*.json map each campaign id to its job ids in attempt order (first, then a rerun
under section 6.1), as ``make_attempts.py`` writes them.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import sys
from typing import Any


def sha256(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main() -> int:
    export, runs, out_dir, a1_path, ladder_path, criterion, attempts_path = sys.argv[1:8]
    if criterion not in ("A4", "A7"):
        raise SystemExit(f"not A4 or A7: {criterion}")
    sys.path.insert(0, export)
    from harness.q2.action_path import acceptance as acc
    from harness.q2.vm.manifest import runner_cpus

    def read_json(path: str) -> Any:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def load(campaign_id: str, jobs: list[str]) -> dict[str, Any]:
        earlier = [acc.load(os.path.join(runs, job)) for job in jobs[:-1]]
        c = acc.load(os.path.join(runs, jobs[-1]), earlier=earlier)
        for attempt in [*c["earlier"], c]:
            ran = attempt["manifest"].get("campaign_id")
            if ran != campaign_id:
                raise SystemExit(f"{campaign_id}: job {attempt['job']} ran {ran}")
        return c

    # N*, as the ladder stage computed it (section 11: attempt 1's A1 and attempt 1's ladder).
    a1_campaigns = [load(k, v) for k, v in sorted(read_json(a1_path).items())]
    for c in a1_campaigns:
        w = c["manifest"]["workload"]
        if w.get("criterion") != "A1" or w.get("attempt") != 1:
            raise SystemExit(f"job {c['job']} is not an attempt-1 A1 campaign")
    rungs: dict[int, list[dict[str, Any]]] = {}
    for campaign_id, jobs in sorted(read_json(ladder_path).items()):
        c = load(campaign_id, jobs)
        w = c["manifest"]["workload"]
        if w.get("criterion") != "ladder" or w.get("attempt") != 1:
            raise SystemExit(f"job {c['job']} is not an attempt-1 ladder campaign")
        rungs.setdefault(c["manifest"]["vm"]["concurrency"], []).append(c)
    ladder = acc.n_star(a1_campaigns, rungs)
    n_star = ladder["n_star"]
    del a1_campaigns, rungs

    attempts = read_json(attempts_path)
    campaigns: dict[str, dict[str, Any]] = {}
    for campaign_id, jobs in sorted(attempts.items()):
        c = load(campaign_id, jobs)
        if c["manifest"]["workload"].get("criterion") != criterion:
            raise SystemExit(f"job {c['job']} is not an {criterion} campaign")
        campaigns[campaign_id] = c
    ordered = list(campaigns.values())
    verdict = acc.a4(ordered, n_star) if criterion == "A4" else acc.a7(ordered, n_star)

    cycles_of: dict[str, dict[int, dict[str, Any]]] = {}

    def records(run_dir: str) -> dict[int, dict[str, Any]]:
        if run_dir in cycles_of:
            return cycles_of[run_dir]
        out = {}
        cycles = os.path.join(run_dir, "cycles")
        for name in sorted(os.listdir(cycles)) if os.path.isdir(cycles) else []:
            if name.startswith("record-") and name.endswith(".json"):
                try:
                    with open(os.path.join(cycles, name), encoding="utf-8") as handle:
                        out[int(name[7:-5])] = json.load(handle)
                except ValueError:
                    continue  # acceptance.load lists it as unreadable
        cycles_of[run_dir] = out
        return out

    def host_snapshots(c: dict[str, Any]) -> dict[str, Any]:
        receipt = c["receipt"]
        snaps = [receipt.get("host_start"), receipt.get("host_end")]
        snaps += [s for session in c["sessions"] for s in session["snapshots"]]
        snaps = [s for s in snaps if s]
        foreign: dict[str, Any] = {}
        for s in snaps:
            for row in s.get("squeue_foreign") or []:
                foreign.setdefault(str(row[0]), row)
        loads = [float((s.get("loadavg") or ["0"])[0]) for s in snaps]
        return {
            "snapshots": len(snaps),
            "session_snapshots": sum(1 for s in c["sessions"] for x in s["snapshots"] if x),
            "foreign_jobs_seen": [foreign[k] for k in sorted(foreign)],
            "foreign_abort_reading_reported_only": acc.foreign_abort(c),
            "max_loadavg_1min": max(loads) if loads else None,
            "max_containers_running_total": max(
                (s.get("containers_running_total") or 0 for s in snaps), default=None
            ),
            "max_containers_ours": max(
                (s.get("containers_ours") or 0 for s in snaps), default=None
            ),
        }

    gating = acc._gating()

    def summary(campaign_id: str, c: dict[str, Any]) -> dict[str, Any]:
        receipt = c["receipt"]
        rsum = receipt.get("summary") or {}
        trials = [(s, t) for s in c["sessions"] for t in s["trials"]]
        steps = [x for _, t in trials for x in t["steps_s"]]
        boots = [s["boot_s"] for s in c["sessions"] if s["boot_s"] is not None]
        recs = records(c["run_dir"])
        overlay = [
            (r.get("vm_measurements") or {}).get("overlay_bytes")
            for r in recs.values()
            if isinstance((r.get("vm_measurements") or {}).get("overlay_bytes"), int)
        ]
        n = c["manifest"]["vm"]["concurrency"]
        w = c["manifest"]["workload"]
        return {
            "campaign_id": campaign_id,
            "criterion": w.get("criterion"),
            "jobs": attempts.get(campaign_id),
            "job": c["job"],
            "earlier_attempts": [e["job"] for e in c["earlier"]],
            "n": n,
            "session_range": w.get("session_range"),
            "attempt": w.get("attempt"),
            "settings": w.get("settings"),
            "git_sha": c["manifest"].get("git_sha"),
            "tree_sha256": (c["manifest"].get("source") or {}).get("tree_sha256"),
            "runner_cpus": c["manifest"]["runner"]["cpus"],
            "cpusets": receipt.get("cpusets"),
            "slurm": c["slurm"],
            "batch": c["batch"],
            "counting_problems": acc.counting_problems(c),
            "snapshot_problems_reported_only": acc.snapshot_problems(c),
            "infra_gates_pass": rsum.get("infra_gates_pass"),
            "qcow2_unchanged": receipt.get("qcow2_unchanged"),
            "labelled_containers_left": receipt.get("labelled_containers_left"),
            "leaked_volumes": rsum.get("leaked_volumes"),
            "no_gpu_all": rsum.get("no_gpu_all"),
            "unreadable": c["unreadable"],
            "receipt_sha256": sha256(os.path.join(c["run_dir"], "receipt.json")),
            "manifest_json_sha256": sha256(os.path.join(c["run_dir"], "manifest.json")),
            "started_at": receipt.get("started_at"),
            "finished_at": receipt.get("finished_at"),
            "sessions": len(c["sessions"]),
            "sessions_planned": w.get("sessions"),
            "trials": len(trials),
            "trials_planned": w.get("trials"),
            "trials_pass": sum(1 for _, t in trials if t["pass"]),
            "gating_trials": sum(1 for _, t in trials if t["cell"] in gating),
            "excused_trials": [
                {"cycle": s.get("cycle"), "setting": s["setting"], "seq": t["seq"],
                 "cell": t["cell"], "reasons": t["reasons"]}
                for s, t in trials
                if acc.restart_only(t)
            ],  # fmt: skip
            "failed_trials": [
                {
                    "cycle": s.get("cycle"),
                    "setting": s["setting"],
                    "seq": t["seq"],
                    "cell": t["cell"],
                    "infra": t["infra"],
                    "reasons": t["reasons"],
                    "restart_only": acc.restart_only(t),
                }
                for s, t in trials
                if not t["pass"]
            ],
            "infra_types": dict(collections.Counter(k for _, t in trials for k in t["infra"])),
            "observation_retries": dict(
                collections.Counter(k for _, t in trials for k in t["retried"])
            ),
            "reset_observations_retried": dict(
                collections.Counter(
                    k
                    for s in c["sessions"]
                    for k in ((s.get("reset_observation") or {}).get("retried") or [])
                )
            ),
            "reset_observations_not_delivered": [
                s.get("cycle")
                for s in c["sessions"]
                if s.get("reset_observation") and not s["reset_observation"]["delivered"]
            ],
            "session_errors": [
                {"cycle": s.get("cycle"), "error": s.get("error")}
                for s in c["sessions"]
                if s.get("error")
            ],
            "boot_s": {
                "n": len(boots),
                "p50": acc.quantile(boots, 0.5),
                "p95": acc.quantile(boots, 0.95),
                "max": max(boots) if boots else None,
            },
            "step_s": {
                "n": len(steps),
                "p50": acc.quantile(steps, 0.5),
                "p95": acc.quantile(steps, 0.95),
                "max": max(steps) if steps else None,
            },
            "restarts": sum(s.get("restarts") or 0 for s in c["sessions"]),
            "accessibility_calls": sum(s.get("accessibility_calls") or 0 for s in c["sessions"]),
            "overlay_bytes_per_session": {
                "n": len(overlay),
                "p50": acc.quantile([float(x) for x in overlay], 0.5),
                "max": max(overlay) if overlay else None,
            },
            "host": host_snapshots(c),
            "registered_shape": {
                "n_is_n_star": n == n_star,
                "runner_cpus_registered": c["manifest"]["runner"]["cpus"] == runner_cpus(n),
                "vm_vcpus": n * c["manifest"]["vm"]["cpu_cores"],
                "vm_vcpus_at_most_160": n * c["manifest"]["vm"]["cpu_cores"] <= 160,
                "attempt_1": w.get("attempt") == 1,
            },
        }

    every = acc.every_attempt(ordered)
    report: dict[str, Any] = {
        "criterion": criterion,
        "n_star": n_star,
        "n_star_from": "acceptance.n_star over attempt 1's A1 campaigns and attempt 1's ladder",
        "n_star_step_p95_n1_s": ladder["step_p95_n1_s"],
        "n_star_rungs_qualifying": sorted(n for n, r in ladder["rungs"].items() if r["qualifies"]),
        "program_kill_criterion": ladder["program_kill_criterion"],
        "jobs": {k: attempts[k] for k in sorted(attempts)},
        "sessions_every_attempt": [
            {
                "job": a["job"],
                "cycle": s.get("cycle"),
                "setting": s["setting"],
                "trials": len(s["trials"]),
                "pass": sum(1 for t in s["trials"] if t["pass"]),
                "failed": sum(1 for t in s["trials"] if not t["pass"]),
                "excused": sum(1 for t in s["trials"] if acc.restart_only(t)),
                "boot_s": s.get("boot_s"),
                "restarts": s.get("restarts"),
                "accessibility_calls": s.get("accessibility_calls"),
                "reset_delivered": (s.get("reset_observation") or {}).get("delivered"),
                "error": s.get("error"),
            }
            for a in every
            for s in a["sessions"]
        ],
    }
    if criterion == "A4":
        plan = read_json(os.path.join(export, "harness/q2/action_path/volume_plan.json"))
        per_entry: dict[str, dict[str, Any]] = {}
        realized_class: collections.Counter[str] = collections.Counter()
        for c in ordered:
            for s in c["sessions"]:
                for t in s["trials"]:
                    row = per_entry.setdefault(
                        t["cell"], {"trials": {}, "pass": {}, "failed": 0, "excused": 0}
                    )
                    row["trials"][s["setting"]] = row["trials"].get(s["setting"], 0) + 1
                    row["pass"][s["setting"]] = row["pass"].get(s["setting"], 0) + int(t["pass"])
                    row["failed"] += int(not t["pass"] and not acc.restart_only(t))
                    row["excused"] += int(acc.restart_only(t))
                    for name, k in plan["entries"][t["cell"]]["classes"].items():
                        realized_class[name] += k
        for cell, row in per_entry.items():
            row["plan_reps"] = plan["entries"][cell]["reps"]
            row["entry_upper_bound_95"] = plan["entries"][cell]["entry_upper_bound_95"]
            row["pure_class"] = plan["entries"][cell]["pure_class"]
        report["per_entry"] = dict(sorted(per_entry.items()))
        report["entries_run"] = len(per_entry)
        report["class_actions_of_trials_run"] = dict(sorted(realized_class.items()))
        report["class_actions_plan"] = plan["class_actions"]
        report["class_actions_note"] = (
            "device actions per class of the trials of the counting attempts, from each "
            "entry's class counts in volume_plan.json (every action of a trial that ran; a "
            "restart-only trial's actions count toward the class bounds, section 9)"
        )
    else:
        flags = acc.outcomes(ordered)
        report["trial_verdicts_reported_not_judged"] = {
            cell: {setting: f"{sum(v)}/{len(v)}" for setting, v in sorted(by.items())}
            for cell, by in sorted(flags.items())
        }
        calls = [s.get("accessibility_calls") or 0 for c in ordered for s in c["sessions"]]
        report["accessibility_calls_per_session"] = {
            "n": len(calls),
            "p50": acc.quantile([float(x) for x in calls], 0.5),
            "min": min(calls) if calls else None,
            "max": max(calls) if calls else None,
            "mean": sum(calls) / len(calls) if calls else None,
        }
        report["plan_calls_check"] = {
            "observation_plan_calls": acc.observation_plan_calls(),
            "OBSERVATION_PLAN_CALLS": acc.OBSERVATION_PLAN_CALLS,
        }

    os.makedirs(out_dir, exist_ok=True)
    tag = criterion.lower()

    def write(name: str, value: Any) -> None:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")

    write(f"{tag}-verdict.json", verdict)
    write(f"{tag}-section12-state-not-observed.json", verdict["state_not_observed"])
    write(f"{tag}-campaigns.json", [summary(k, a) for k, c in sorted(campaigns.items())
                                    for a in [*(c.get("earlier") or []), c]])  # fmt: skip
    write(f"{tag}-report.json", report)
    keys = ("trials", "failures", "restart_only_trials", "restarts", "accessibility_calls",
            "rate", "upper_95")  # fmt: skip
    print(json.dumps({"criterion": criterion, "n_star": n_star, "pass": verdict["pass"],
                      "problems": verdict["problems"],
                      **{k: verdict[k] for k in keys if k in verdict}}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
