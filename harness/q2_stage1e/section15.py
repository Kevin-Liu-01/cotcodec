"""E's descriptive outputs of S1a section 15 that the report does not compute (D59 (iii)).

S1a assembled these after its data with an operator script written under D59 (iii)
(``ops/s1a-analysis/assemble_s15.py``); E registers the same items before any E episode and
computes them here from the registered fields, with the same definitions:

* output and prompt tokens per (size, harness) and per job (``tokens``);
* the step, step-of-termination and step-of-success distributions, censored at 15 steps
  (``steps``, ``ended``; success is the raw verdict);
* guest-server restarts and observation events per episode (``guest_server_restarts``,
  ``observations``), over the final records and over every attempt;
* losses by task (every attempt and the final records), and slots with no record;
* the cost card against the card's central and high prices at V = 20 (S1a ``plan.py``);
* setup and postconfig reply failures by step type and by class
  (``osworld_live.setup_reply_failed``);
* host snapshots and foreign load per job (the lane receipts' ``snapshots``);
* first divergence (``first_divergence``): E's tasks, scored final records, each final
  attempt's ``steps.jsonl`` from its own job's run directory, classified by S1a's
  ``records.first_divergence`` through ``analysis.divergence_summary``. With one episode per
  session every pair is a between-session pair.

Nothing here enters a decision rule; every output carries the report's labels.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from harness.q2_stage1 import analysis as A1
from harness.q2_stage1 import plan as P1
from harness.q2_stage1 import records as R1
from harness.q2_stage1e import plan as PE
from harness.q2_stage1e import records as RE

STEP_CAP = 15
TERMINATE = "terminate_"


def _cell(rec: Mapping[str, Any]) -> str:
    return f"{rec['size']}/{rec['harness']}"


def describe(values: Iterable[float]) -> dict[str, Any]:
    v = np.asarray([float(x) for x in values], dtype=float)
    if not v.size:
        return {"n": 0}
    return {
        "n": int(v.size),
        "total": round(float(v.sum()), 3),
        "mean": round(float(v.mean()), 3),
        "median": round(float(np.percentile(v, 50)), 3),
        "p90": round(float(np.percentile(v, 90)), 3),
        "max": round(float(v.max()), 3),
    }


def by_cell(records: Iterable[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    out: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for rec in records:
        out[_cell(rec)].append(rec)
    return dict(sorted(out.items()))


def scored(finals: Mapping[Any, Mapping[str, Any]], tasks: Sequence[str]) -> list:
    task_set = set(tasks)
    return [r for k, r in sorted(finals.items()) if k[2] in task_set and r["status"] == "scored"]


def token_stats(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    with_tokens = [r for r in records if isinstance(r.get("tokens"), dict)]
    completion = [int(r["tokens"].get("completion") or 0) for r in with_tokens]
    steps = sum(int(r.get("steps") or 0) for r in with_tokens)
    return {
        "episodes": len(records),
        "episodes_with_tokens": len(with_tokens),
        "completion": describe(completion),
        "completion_per_step": round(sum(completion) / steps, 3) if steps else None,
        "prompt": describe(int(r["tokens"].get("prompt") or 0) for r in with_tokens),
    }


def step_distributions(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    steps: Counter = Counter()
    term: Counter = Counter()
    succ: Counter = Counter()
    for rec in records:
        n = int(rec.get("steps") or 0)
        how = str(rec.get("ended"))
        steps[f"{n:02d}"] += 1
        where = f"{n:02d}" if how.startswith(TERMINATE) else (
            f"censored_at_{STEP_CAP}" if how == "step_cap" else f"other:{how}")  # fmt: skip
        term[where] += 1
        if float(rec["score"]) == 1.0:
            succ[where] += 1
    return {
        "episodes": len(records),
        "steps": dict(sorted(steps.items())),
        "step_of_termination": dict(sorted(term.items())),
        "successes": sum(succ.values()),
        "step_of_success": dict(sorted(succ.items())),
    }


def per_episode(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "episodes": len(records),
        "episodes_with_restart": sum(
            1 for r in records if int(r.get("guest_server_restarts") or 0)
        ),
        "restarts": sum(int(r.get("guest_server_restarts") or 0) for r in records),
    }
    for side in ("agent", "checker"):
        for key in R1.OBSERVATION_COUNTS[1:]:
            out[f"episodes_with_{side}_{key}"] = sum(
                1 for r in records
                if int(((r.get("observations") or {}).get(side) or {}).get(key) or 0)
            )  # fmt: skip
    return out


def losses_by_task(
    records: Sequence[Mapping[str, Any]], finals: Mapping[Any, Mapping[str, Any]],
    tasks: Sequence[str], jobs_present: Sequence[str],
) -> dict[str, Any]:  # fmt: skip
    rows: dict[str, dict[str, Any]] = {
        t: {"attempts_lost": 0, "attempts_lost_by_type": Counter(), "final_slots_lost": 0,
            "final_slots_cap_truncated": 0, "slots_without_record": 0}
        for t in tasks
    }  # fmt: skip
    for rec in records:
        if rec["status"] == "infrastructure" and rec["task_id"] in rows:
            rows[rec["task_id"]]["attempts_lost"] += 1
            rows[rec["task_id"]]["attempts_lost_by_type"][rec["infrastructure_type"]] += 1
    for key, rec in finals.items():
        if key[2] in rows and rec["status"] == "infrastructure":
            rows[key[2]]["final_slots_lost"] += 1
        elif key[2] in rows and rec["status"] == "cap_truncated":
            rows[key[2]]["final_slots_cap_truncated"] += 1
    for job in jobs_present:
        size, session = PE.parse_job(job)
        for t in tasks:
            for h in RE.HARNESSES:
                if (size, session, t, h, PE.RERUN) not in finals:
                    rows[t]["slots_without_record"] += 1
    return {
        t: {**{k: v for k, v in r.items() if k != "attempts_lost_by_type"},
            "attempts_lost_by_type": dict(sorted(r["attempts_lost_by_type"].items()))}
        for t, r in rows.items()
        if any(r[k] for k in ("attempts_lost", "final_slots_lost", "final_slots_cap_truncated",
                              "slots_without_record"))
    }  # fmt: skip


def cost_card_prices(costs: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any]:
    """Each job's realized GPU-h per episode against the card's central and high prices at
    its V (DR4 and P5 read the high price; the central comparison is descriptive)."""
    if not costs:
        return {"not_estimable": "no costs.json (analysis costs) was given"}

    def against(g: float | None, v: int) -> dict[str, Any]:
        central, high = P1.PRICE_CENTRAL[v], P1.PRICE_HIGH[v]
        if g is None:
            return {"price_central": central, "price_high": high, "gpu_h_per_episode": None}
        return {
            "gpu_h_per_episode": g,
            "price_central": central,
            "price_high": high,
            "ratio_to_central": round(g / central, 4),
            "ratio_to_high": round(g / high, 4),
        }

    return {
        "jobs": {job: {"V": int(c["V"]), **against(float(c["gpu_h_per_episode"]), int(c["V"])),
                       "vm_h_per_episode": c.get("vm_h_per_episode")}
                 for job, c in sorted(costs.items())},
        "by_size": A1.costs_by_size(costs),
    }  # fmt: skip


def reply_class(reply: Mapping[str, Any]) -> str:
    status = reply.get("status")
    if not isinstance(status, int) or isinstance(status, bool):
        return "no_http_reply"
    if status >= 500:
        return "http_5xx"
    if status != 200:
        return f"http_{status // 100}xx"
    return "http_200_nonzero_returncode" if reply.get("returncode") not in (None, 0) else "ok"


def failure_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    from harness.q2_stage1.osworld_live import setup_reply_failed as failed

    out: dict[str, Any] = {
        "episodes": len(records), "setup_replies_failed": 0, "setup_failed_by_class": Counter(),
        "infra_task_setup": 0, "postconfig_replies": 0, "postconfig_replies_failed": 0,
        "postconfig_failed_by_type": Counter(), "postconfig_failed_by_class": Counter(),
    }  # fmt: skip
    for rec in records:
        setup = rec.get("setup") if isinstance(rec.get("setup"), dict) else {}
        for reply in [r for r in setup.get("replies") or () if failed(r)]:
            out["setup_replies_failed"] += 1
            out["setup_failed_by_class"][reply_class(reply)] += 1
        out["infra_task_setup"] += int(rec.get("infrastructure_type") == "task_setup")
        post = list(rec.get("postconfig_replies") or ())
        out["postconfig_replies"] += len(post)
        for reply in [r for r in post if failed(r)]:
            out["postconfig_replies_failed"] += 1
            out["postconfig_failed_by_type"][str(reply.get("type") or "unknown")] += 1
            out["postconfig_failed_by_class"][reply_class(reply)] += 1
    return {k: (dict(sorted(v.items())) if isinstance(v, Counter) else v) for k, v in out.items()}


def host_snapshots(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """The lane's snapshots (start, each block, end): load averages, container counts and
    foreign Slurm jobs (the pair's own jobs left out); no host name is recorded."""
    pair = {str(receipt.get("job_id")), str((receipt.get("gpu_job") or {}).get("job_id"))}
    entries = []
    for snap in receipt.get("snapshots") or []:
        foreign = [
            row for row in snap.get("squeue_foreign") or [] if row and str(row[0]) not in pair
        ]
        entries.append(
            {
                "block": snap.get("block"),
                "t": snap.get("t"),
                "loadavg": snap.get("loadavg"),
                "containers_running_total": snap.get("containers_running_total"),
                "foreign_jobs": len(foreign),
                "foreign_running": sum(
                    1 for row in foreign if len(row) > 2 and row[2] == "RUNNING"
                ),
            }
        )
    return {
        "snapshots": entries,
        "snapshots_with_foreign_running_job": sum(1 for e in entries if e["foreign_running"]),
    }


def step_logs(
    finals: Mapping[Any, Mapping[str, Any]], tasks: Sequence[str], runs: Mapping[str, Path]
) -> tuple[dict[Any, list[dict[str, Any]]], list[str]]:
    """(slot key -> steps of its final scored attempt, slots whose log was not found)."""
    task_set = set(tasks)
    logs: dict[Any, list[dict[str, Any]]] = {}
    missing: list[str] = []
    for key, rec in sorted(finals.items()):
        if rec["status"] != "scored" or key[2] not in task_set:
            continue
        run_dir = runs.get(rec["job"])
        name = f"{str(rec['slot']).replace(':', '_')}.a{rec['attempt']}"
        path = run_dir / "episodes" / name / "steps.jsonl" if run_dir is not None else None
        if path is None or not path.is_file():
            missing.append(f"{rec['slot']}.a{rec['attempt']}")
            continue
        logs[key] = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    return logs, missing


def first_divergence(
    finals: Mapping[Any, Mapping[str, Any]], tasks: Sequence[str], runs: Mapping[str, Path]
) -> dict[str, Any]:
    logs, missing = step_logs(finals, tasks, runs)
    return {
        "set": "E's tasks; scored final records; the final attempt's steps.jsonl in its own "
               "job's run directory; every pair is between sessions (one episode per session)",
        "step_logs_read": len(logs),
        "step_logs_missing": len(missing),
        "step_logs_missing_slots": missing[:200],
        "first_divergence": A1.divergence_summary(logs),
        "first_divergence_by_size": {
            z: A1.divergence_summary({k: v for k, v in logs.items() if k[0] == z}) for z in RE.SIZES
        },
        "note": "descriptive: the guest's top-bar clock is on every screenshot, so nearly every "
                "pair parts at step 1 as 'environment' (S1a section 9 item 11)",
    }  # fmt: skip


def run_dirs_by_job(run_dirs: Iterable[Path]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for run_dir in run_dirs:
        manifest = json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))
        e = manifest.get("e") or {}
        if manifest.get("purpose") != "e":
            raise ValueError(f"{run_dir} is not an E job's run directory")
        job = PE.job_name(str(e.get("size")), str(e.get("session")))
        if job in out:
            raise ValueError(f"{job} is named by two run directories")
        out[job] = Path(run_dir)
    return out


def assemble(
    records: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    *,
    labels: Mapping[str, Any],
    costs: Mapping[str, Mapping[str, Any]] | None = None,
    runs: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Every item listed in this module's docstring, with the report's ``labels``."""
    recs = [RE.validate(r) for r in records]
    finals = RE.final_records(recs)
    tasks = list(plan["tasks"])
    finals_list = [r for _k, r in sorted(finals.items())]
    present = [job for job in plan["job_order"] if any(r["job"] == job for r in recs)]
    out: dict[str, Any] = {
        "labels": dict(labels),
        "output_tokens": {c: token_stats(rs) for c, rs in by_cell(scored(finals, tasks)).items()},
        "output_tokens_by_job": {
            job: token_stats(
                [r for r in recs if r["job"] == job and r["status"] in ("scored", "infrastructure")]
            )
            for job in present
        },  # fmt: skip
        "steps": {c: step_distributions(rs) for c, rs in by_cell(scored(finals, tasks)).items()},
        "per_episode": {
            "final_records": {c: per_episode(rs) for c, rs in by_cell(finals_list).items()},
            "attempts": {c: per_episode(rs) for c, rs in by_cell(recs).items()},
        },
        "losses_by_task": losses_by_task(recs, finals, tasks, present),
        "cost_card_prices": cost_card_prices(costs),
        "setup_and_postconfig_failures": {
            "final_records": {c: failure_counts(rs) for c, rs in by_cell(finals_list).items()},
            "attempts": {c: failure_counts(rs) for c, rs in by_cell(recs).items()},
        },
        "offline_setup_exclusions": dict(plan.get("offline_excluded", {})),
    }
    if runs:
        out["host_snapshots"] = {
            job: host_snapshots(json.loads((run / "lane-receipt.json").read_text(encoding="utf-8")))
            for job, run in sorted(runs.items())
        }
        out["first_divergence"] = first_divergence(finals, tasks, runs)
    return out
