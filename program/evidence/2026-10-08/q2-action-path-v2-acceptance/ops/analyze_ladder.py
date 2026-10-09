#!/usr/bin/env python3
"""The concurrency ladder of q2-action-path-v2: each rung's qualification, N* and A1 at N*.

Runs on the host from the read-only export of the frozen commit: it imports that export's
``harness.q2.action_path.acceptance`` (frozen in the inputs addendum and pinned again in the
executor addendum) and calls ``acceptance.n_star`` on attempt 1's A1 campaigns (the N = 1
reference) and the ladder's rung campaigns, as ``acceptance.load`` reads them from the run
directories, every attempt of a rung in the order it ran. Each rung's qualification
(``acceptance.rung``, which ``n_star`` calls), its foreign-load abort
(``acceptance.foreign_abort``, from the host snapshots alone) and N* are the frozen code's.

Two things are computed here, and only from the frozen code's own helpers:

* the concurrency table of section 12 (boot and step quantiles, pass rate, excused trials,
  restarts and accessibility calls per rung attempt, the host snapshots' foreign jobs, load
  averages and container counts, overlay growth from each session's record), reported and
  not judged;
* A1 at N* > 1 (section 7): "passes the seed-43 shuffle under both observation settings at
  the operating concurrency N*, which the ladder rung N* shows (its first five repetitions
  are that shuffle)", under the rung's rule (section 6.1: at most two excused trials in the
  rung, which may both fall in one entry). No frozen function computes it, so this script
  takes rung N*'s trials at positions 0-499 of each setting's order (the first five
  repetitions; ``order.py`` builds the order repetition by repetition from one generator),
  checks that they are A1's seed-43 shuffle (``order.shuffle_order(ids, 43, 5)``), and reads
  every G entry on its counted trials there with ``acceptance.outcomes`` (restart-only
  trials excused, ``acceptance.restart_only``) and ``acceptance.entry_status``, as
  ``acceptance.rung`` reads the whole rung. The rung's own qualification (every counted G
  trial of all r_N repetitions passes, at most two excused trials over every attempt that
  did not abort, the attempt rules of section 6.1) is reported beside it.

    python3 -B analyze_ladder.py EXPORT RUNS OUT_DIR ATTEMPTS_A1.json ATTEMPTS_LADDER.json

ATTEMPTS_*.json map each campaign id to its job ids in attempt order (first, then a rerun
under section 6.1 or the ladder's abort rule), as ``make_attempts.py`` writes them.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import sys
from typing import Any

FIRST_REPS = 5  # A1's repetitions; the rung's first five are A1's seed-43 shuffle (section 9)


def sha256(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main() -> int:
    export, runs, out_dir, a1_path, ladder_path = sys.argv[1:6]
    sys.path.insert(0, export)
    from harness.q2.action_path import acceptance as acc
    from harness.q2.action_path import order
    from harness.q2.vm.manifest import ladder_reps, runner_cpus

    def read_attempts(path: str) -> dict[str, list[str]]:
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

    a1_attempts = read_attempts(a1_path)
    a1_campaigns = [load(k, v) for k, v in sorted(a1_attempts.items())]
    for c in a1_campaigns:
        w = c["manifest"]["workload"]
        if w.get("criterion") != "A1" or w.get("attempt") != 1:
            raise SystemExit(f"job {c['job']} is not an attempt-1 A1 campaign")
    ladder_attempts = read_attempts(ladder_path)
    rungs: dict[int, list[dict[str, Any]]] = {}
    jobs_of: dict[str, list[str]] = {}
    loaded: dict[str, dict[str, Any]] = {}
    for campaign_id, jobs in sorted(ladder_attempts.items()):
        c = load(campaign_id, jobs)
        loaded[campaign_id] = c
        w = c["manifest"]["workload"]
        if w.get("criterion") != "ladder" or w.get("attempt") != 1:
            raise SystemExit(f"job {c['job']} is not an attempt-1 ladder campaign")
        rungs.setdefault(c["manifest"]["vm"]["concurrency"], []).append(c)
        jobs_of[campaign_id] = jobs

    verdict = acc.n_star(a1_campaigns, rungs)
    reference = verdict["step_p95_n1_s"]
    gating = acc._gating()
    ids = acc._layer_ids("L0-fixed")

    def records(run_dir: str) -> dict[int, dict[str, Any]]:
        out = {}
        cycles = os.path.join(run_dir, "cycles")
        for name in sorted(os.listdir(cycles)) if os.path.isdir(cycles) else []:
            if name.startswith("record-") and name.endswith(".json"):
                try:
                    with open(os.path.join(cycles, name), encoding="utf-8") as handle:
                        out[int(name[7:-5])] = json.load(handle)
                except ValueError:
                    continue  # acceptance.load lists it as unreadable
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
            "max_loadavg_1min": max(loads) if loads else None,
            "max_containers_running_total": max(
                (s.get("containers_running_total") or 0 for s in snaps), default=None
            ),
            "max_containers_ours": max(
                (s.get("containers_ours") or 0 for s in snaps), default=None
            ),
        }

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
        gating_trials = [(s, t) for s, t in trials if t["cell"] in gating]
        excused = [(s, t) for s, t in trials if acc.restart_only(t)]
        n = c["manifest"]["vm"]["concurrency"]
        return {
            "campaign_id": campaign_id,
            "jobs": jobs_of.get(campaign_id),
            "job": c["job"],
            "n": n,
            "reps": c["manifest"]["workload"].get("reps"),
            "runner_cpus": c["manifest"]["runner"]["cpus"],
            "cpusets": receipt.get("cpusets"),
            "slurm": c["slurm"],
            "batch": c["batch"],
            "counting_problems": acc.counting_problems(c),
            "foreign_abort": acc.foreign_abort(c),
            "snapshot_problems": acc.snapshot_problems(c),
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
            "trials": len(trials),
            "trials_pass": sum(1 for _, t in trials if t["pass"]),
            "gating_trials": len(gating_trials),
            "gating_trials_pass": sum(1 for _, t in gating_trials if t["pass"]),
            "excused_trials": [
                {
                    "cycle": s.get("cycle"),
                    "setting": s["setting"],
                    "seq": t["seq"],
                    "cell": t["cell"],
                }
                for s, t in excused
            ],  # fmt: skip
            "failed_trials": [
                {
                    "cycle": s.get("cycle"),
                    "setting": s["setting"],
                    "seq": t["seq"],
                    "cell": t["cell"],
                    "gating": t["cell"] in gating,
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
            "reset_observations_not_delivered": [
                s.get("cycle")
                for s in c["sessions"]
                if s.get("reset_observation") and not s["reset_observation"]["delivered"]
            ],
            "session_errors": [s.get("error") for s in c["sessions"] if s.get("error")],
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
                "p95_over_n1_reference": (
                    acc.quantile(steps, 0.95) / reference if steps and reference else None
                ),
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
                "reps_is_ladder_reps": c["manifest"]["workload"].get("reps") == ladder_reps(n),
                "runner_cpus_registered": c["manifest"]["runner"]["cpus"] == runner_cpus(n),
                "vm_vcpus": n * c["manifest"]["vm"]["cpu_cores"],
                "vm_vcpus_at_most_160": n * c["manifest"]["vm"]["cpu_cores"] <= 160,
            },
        }

    def a1_at(n: int) -> dict[str, Any]:
        """A1 at N* > 1 from rung N*'s first five repetitions, under the rung's rule."""
        campaigns = rungs[n]
        plan = order.plan(ids, 43, ladder_reps(n), list(acc.SETTINGS), acceptance=True)
        position: dict[tuple[int, int], int] = {}
        offsets: dict[str, int] = {}
        for cycle, session in enumerate(plan):
            base = offsets.get(session["setting"], 0)
            for seq, _ in session["trials"]:
                position[(cycle, seq)] = base + seq
            offsets[session["setting"]] = base + len(session["trials"])
        a1_order = order.shuffle_order(ids, 43, FIRST_REPS, acceptance=True)
        limit = FIRST_REPS * len(ids)
        problems: list[str] = []

        def first_five(c: dict[str, Any]) -> dict[str, Any]:
            sessions = []
            for s in c["sessions"]:
                kept = [
                    t for t in s["trials"] if position.get((s["cycle"], t["seq"]), limit) < limit
                ]
                sessions.append({**s, "trials": kept})
            return {**c, "sessions": sessions}

        counting = [first_five(c) for c in campaigns]
        for c in counting:
            for setting in acc.SETTINGS:
                got = sorted(
                    (position[(s["cycle"], t["seq"])], t["cell"])
                    for s in c["sessions"]
                    if s["setting"] == setting
                    for t in s["trials"]
                )
                if [cell for _, cell in got] != a1_order:
                    problems.append(
                        f"job {c['job']} {setting}: the first five repetitions run "
                        f"({len(got)} trials) are not A1's seed-43 shuffle ({len(a1_order)})"
                    )
        flags = acc.outcomes(counting, acc.restart_only)
        status = {cell: acc.entry_status(v) for cell, v in flags.items()}
        failing = sorted(cell for cell in gating if status.get(cell) != "PASS")
        if failing:
            problems.append(f"gating entries not PASS in the first five repetitions: {failing}")
        not_aborted = [
            p for c in campaigns for p in c.get("earlier") or [] if not acc.foreign_abort(p)
        ]
        earlier_failed = [
            (p["job"], f)
            for p in not_aborted
            for f in acc.failed_trials(first_five(p), acc.restart_only, gating)
        ]
        if earlier_failed:
            problems.append(f"earlier attempts' counted gating failures: {earlier_failed[:5]}")
        excused_rung = acc._excused_total([*not_aborted, *campaigns])
        if excused_rung > acc.MAX_EXCUSED_PER_RUNG:
            problems.append(f"{excused_rung} excused trials in the rung (at most 2)")
        excused_first = acc.excused_repetitions(counting)
        trials = [t for c in counting for s in c["sessions"] for t in s["trials"]]
        steps = [x for t in trials for x in t["steps_s"]]
        rung_verdict = verdict["rungs"][n]
        return {
            "what": "A1 at N* (section 7): rung N*'s first five repetitions (positions 0-499 "
            "of each setting's order, A1's seed-43 shuffle), every G entry on its counted "
            "trials, under the rung's rule (at most two excused trials in the rung)",
            "n_star": n,
            "pass": not problems and rung_verdict["qualifies"],
            "problems": problems,
            "rung_qualifies": rung_verdict["qualifies"],
            "trials": len(trials),
            "trials_pass": sum(1 for t in trials if t["pass"]),
            "gating_trials": sum(1 for t in trials if t["cell"] in gating),
            "gating_trials_pass": sum(1 for t in trials if t["cell"] in gating and t["pass"]),
            "excused_in_first_five": excused_first,
            "excused_in_rung": excused_rung,
            "entries": dict(sorted(status.items())),
            "step_p95_s": acc.quantile(steps, 0.95),
        }

    a1_n_star = (
        a1_at(verdict["n_star"])
        if verdict["n_star"] > 1
        else {"n_star": verdict["n_star"], "what": "N* = 1: A1 at N = 1 gates it (section 7)"}
    )

    table = [
        {
            "n": 1,
            "what": "A1 (N = 1 reference, both shuffles and settings pooled)",
            "jobs": [c["job"] for c in a1_campaigns],
            "step_p95_s": reference,
        }
    ]
    for n in sorted(verdict["rungs"]):
        r = verdict["rungs"][n]
        attempts = [a for c in rungs[n] for a in [*(c.get("earlier") or []), c]]
        trials = [t for a in attempts[-1:] for s in a["sessions"] for t in s["trials"]]
        steps = [x for t in trials for x in t["steps_s"]]
        boots = [s["boot_s"] for a in attempts[-1:] for s in a["sessions"] if s["boot_s"]]
        table.append(
            {
                "n": n,
                "reps": ladder_reps(n),
                "jobs": [a["job"] for a in attempts],
                "counting_job": attempts[-1]["job"],
                "qualifies": r["qualifies"],
                "aborted": r["aborted"],
                "abort_reasons": r["abort_reasons"],
                "problems": r["problems"],
                "boots": r["boots"],
                "boot_p50_s": acc.quantile(boots, 0.5),
                "boot_p95_s": r["boot_p95_s"],
                "step_p50_s": acc.quantile(steps, 0.5),
                "step_p95_s": r["step_p95_s"],
                "step_p95_limit_s": acc.STEP_P95_FACTOR * reference if reference else None,
                "trials": len(trials),
                "trials_pass": sum(1 for t in trials if t["pass"]),
                "excused_trials": r["excused_trials"],
                "restarts": sum(s.get("restarts") or 0 for s in attempts[-1]["sessions"]),
                "accessibility_calls": sum(
                    s.get("accessibility_calls") or 0 for s in attempts[-1]["sessions"]
                ),
                "earlier_attempts": r["earlier_attempts"],
            }
        )

    os.makedirs(out_dir, exist_ok=True)

    def write(name: str, value: Any) -> None:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")

    write("ladder-n-star.json", verdict)
    write(
        "ladder-section12-state-not-observed.json",
        {str(n): verdict["rungs"][n]["state_not_observed"] for n in sorted(verdict["rungs"])},
    )
    write("ladder-concurrency-table.json", table)
    write(
        "ladder-campaigns.json",
        [summary(k, a) for k, c in sorted(loaded.items()) for a in [*(c.get("earlier") or []), c]],
    )
    write("a1-at-n-star.json", a1_n_star)
    print(
        json.dumps(
            {
                "n_star": verdict["n_star"],
                "step_p95_n1_s": reference,
                "rungs": {
                    str(n): {
                        "qualifies": r["qualifies"],
                        "aborted": r["aborted"],
                        "problems": r["problems"],
                        "boot_p95_s": r["boot_p95_s"],
                        "step_p95_s": r["step_p95_s"],
                        "excused": r["excused_trials"],
                    }
                    for n, r in sorted(verdict["rungs"].items())
                },
                "a1_at_n_star_pass": a1_n_star.get("pass"),
                "program_kill_criterion": verdict["program_kill_criterion"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
