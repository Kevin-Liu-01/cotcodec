"""D59 (iii): the section 15 items the registered report lacks, assembled with the registered
functions and fields. An operator script, not code of record.

Usage (host, after ``run_report.py``)::

    python3 -E -s -B assemble_s15.py --export X --plan plan-a0a.json --records A/a1.jsonl \
        --run-dir RUNS/1045 [--run-dir ...] --costs A/costs.json --analysis-dir A \
        --report-guarded A/report/report-guarded.json --out A/s15.json

Every item states its source and the set it reads. The items (bug B6 and the checker's gaps):

* ``dr0_per_job``: ``rules.run_dir_dr0`` on each run directory (receipt included);
* ``labels``: incomplete (``run_report.completeness``) and "not externally anchored";
* ``output_tokens``: ``tokens.completion`` (and ``tokens.prompt``) per (size, harness) on the
  primary and secondary sets' scored final records, and per job on the cost card's episodes
  (``analysis.realized_costs``: attempts ``scored`` or ``infrastructure``);
* ``steps``: the step distribution and the step-of-termination and step-of-success
  distributions censored at 15 (an episode that reached the cap without a terminate action
  counts at ``censored_at_15``), per (size, harness), on the sets' scored final records;
* ``restarts_per_episode``: ``guest_server_restarts`` per episode, over final records and
  every attempt; ``observations_per_episode`` (episodes with an observation delivered on a
  retry, slower than 30 s or undelivered); ``uncertified_exposure_per_episode``;
* ``losses_by_task`` (section 10.1): infrastructure attempts by type, final slots lost or
  cap-truncated, and base slots without a record, per task and job;
* ``cost_card_prices``: each job's and size's GPU-h per episode against the card's central
  and high prices at its V (``plan.PRICE_CENTRAL``, ``plan.PRICE_HIGH``);
* ``offline_setup_exclusions``: the plan's ``offline_excluded`` with its reasons;
* ``setup_and_postconfig_failures``: every failed setup and postconfig reply
  (``osworld_live.setup_reply_failed``) by step type and by status class;
* ``host_snapshots``: each lane receipt's snapshots and the foreign load (jobs other than the
  job's own VM and GPU jobs; another user's job name is not copied);
* ``secondary_corrected``: the registered estimands on the secondary set under corrected
  verdicts (``analyse_array(outcome_array(finals, secondary, value="corrected"))``, guarded)
  with its flips; ``per_domain`` (primary corrected, secondary raw and corrected);
* ``rescoring``: per-job coverage and the verdicts that fell back to live scores, with the
  corrected-verdict flips split into checker corrections and replay mismatches;
* ``checker_noise_set`` and ``truncation``: the sets the registered code reads, stated, with
  the base-only truncation share as a description;
* ``dr3``: DR3's components per size, read from the guarded report.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rescore_jobs as RJ  # noqa: E402
import run_report as RR  # noqa: E402
import s1a_ops as O  # noqa: E402

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


def scored_finals(finals: Mapping[Any, Mapping[str, Any]], tasks: Sequence[str]) -> list:
    task_set = set(tasks)
    return [r for k, r in sorted(finals.items()) if k[2] in task_set and r["status"] == "scored"]


# --------------------------------------------------------------------------- tokens and steps


def token_stats(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    with_tokens = [r for r in records if isinstance(r.get("tokens"), dict)]
    completion = [int(r["tokens"].get("completion") or 0) for r in with_tokens]
    prompt = [int(r["tokens"].get("prompt") or 0) for r in with_tokens]
    steps = sum(int(r.get("steps") or 0) for r in with_tokens)
    return {
        "episodes": len(records),
        "episodes_with_tokens": len(with_tokens),
        "completion": describe(completion),
        "completion_per_step": round(sum(completion) / steps, 3) if steps else None,
        "prompt": describe(prompt),
    }


def output_tokens(
    finals: Mapping[Any, Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    sets: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "source": "episode records' tokens.completion and tokens.prompt (driver: summed over "
        "the episode's model turns; an attempt lost before its loop ended has none)",
    }
    for name, tasks in sets.items():
        out[name] = {c: token_stats(rs) for c, rs in by_cell(scored_finals(finals, tasks)).items()}
    ran = [r for r in records if r.get("status") in ("scored", "infrastructure")]
    out["by_job_cost_card_episodes"] = {
        job: token_stats([r for r in ran if r["job"] == job])
        for job in sorted({r["job"] for r in ran})
    }
    return out


def step_distributions(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    steps: Counter = Counter()
    term: Counter = Counter()
    succ: Counter = Counter()
    ended: Counter = Counter()
    successes = 0
    for rec in records:
        n = int(rec.get("steps") or 0)
        how = str(rec.get("ended"))
        steps[str(n)] += 1
        ended[how] += 1
        if how.startswith(TERMINATE):
            where = str(n)
        elif how == "step_cap":
            where = f"censored_at_{STEP_CAP}"
        else:
            where = f"other:{how}"
        term[where] += 1
        if float(rec["score"]) == 1.0:
            successes += 1
            succ[where] += 1

    def ordered(c: Counter) -> dict[str, int]:
        def key(item: tuple[str, int]) -> tuple[bool, int, str]:
            name = item[0]
            return (not name.isdigit(), int(name) if name.isdigit() else 0, name)

        return dict(sorted(c.items(), key=key))

    return {
        "episodes": len(records),
        "steps_mean": round(sum(int(r.get("steps") or 0) for r in records) / len(records), 3)
        if records
        else None,
        "steps": ordered(steps),
        "ended": dict(sorted(ended.items())),
        "step_of_termination": ordered(term),
        "successes": successes,
        "step_of_success": ordered(succ),
        "not_successful": len(records) - successes,
    }


def steps_items(finals: Mapping[Any, Mapping[str, Any]], sets: Mapping[str, Sequence[str]]) -> dict:
    out: dict[str, Any] = {
        "source": "episode records' steps and ended; success is the raw verdict (score 1.0)",
        "censoring": (
            f"an episode that reached the {STEP_CAP}-step cap without a terminate action "
            f"(ended 'step_cap') is counted at 'censored_at_{STEP_CAP}': its termination step, "
            "and for a success the step at which the state became correct, are not observed"
        ),
    }
    for name, tasks in sets.items():
        out[name] = {
            c: step_distributions(rs) for c, rs in by_cell(scored_finals(finals, tasks)).items()
        }
    return out


# --------------------------------------------------------------------------- per-episode counts


def restarts(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(int(r.get("guest_server_restarts") or 0)) for r in records)
    return {
        "episodes": len(records),
        "episodes_without_field": sum(1 for r in records if "guest_server_restarts" not in r),
        "episodes_with_restart": sum(
            1 for r in records if int(r.get("guest_server_restarts") or 0)
        ),
        "restarts": sum(int(r.get("guest_server_restarts") or 0) for r in records),
        "distribution": dict(sorted(counts.items(), key=lambda kv: int(kv[0]))),
        "infra_guest_server_restart": sum(
            1 for r in records if r.get("infrastructure_type") == "guest_server_restart"
        ),
    }


def observation_episodes(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"episodes": len(records)}
    for side in ("agent", "checker"):
        for key in ("retried", "slow", "undelivered"):
            out[f"episodes_with_{side}_{key}"] = sum(
                1
                for r in records
                if int(((r.get("observations") or {}).get(side) or {}).get(key) or 0)
            )
    return out


def per_episode_items(
    finals: Mapping[Any, Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    base: Sequence[str],
) -> dict[str, Any]:
    final_list = [r for _k, r in sorted(finals.items())]
    base_scored = scored_finals(finals, base)
    return {
        "restarts_per_episode": {
            "source": "episode records' guest_server_restarts (driver.check_restarts)",
            "final_records": {c: restarts(rs) for c, rs in by_cell(final_list).items()},
            "attempts": {c: restarts(rs) for c, rs in by_cell(records).items()},
        },
        "observations_per_episode": {
            "source": "episode records' observations (agent, checker): episodes with at least one",
            "final_records": {c: observation_episodes(rs) for c, rs in by_cell(final_list).items()},
            "attempts": {c: observation_episodes(rs) for c, rs in by_cell(records).items()},
        },
        "uncertified_exposure_per_episode": {
            "source": "episode records' uncertified_key_actions; primary set, scored final records",
            "cells": {
                c: {
                    "episodes": len(rs),
                    "episodes_exposed": sum(
                        1 for r in rs if int(r.get("uncertified_key_actions") or 0)
                    ),
                    "uncertified_key_actions": sum(
                        int(r.get("uncertified_key_actions") or 0) for r in rs
                    ),
                }
                for c, rs in by_cell(base_scored).items()
            },
        },
    }


# --------------------------------------------------------------------------- losses by task


def losses_by_task(
    records: Sequence[Mapping[str, Any]],
    finals: Mapping[Any, Mapping[str, Any]],
    plan: Mapping[str, Any],
    jobs_present: Sequence[str],
) -> dict[str, Any]:
    R = O.frozen("records")
    base = list(plan["base"])
    ext = [
        t
        for b in sorted(plan.get("extension_blocks", {}), key=int)
        for t in plan["extension_blocks"][b]
    ]
    domains = plan.get("task_domains") or {}
    rows: dict[str, dict[str, Any]] = {}

    def row(task: str) -> dict[str, Any]:
        if task not in rows:
            rows[task] = {
                "domain": domains.get(task), "base": task in base, "attempts_lost": 0,
                "attempts_lost_by_type": Counter(), "final_slots_lost": 0,
                "final_slots_cap_truncated": 0, "base_slots_without_record": 0,
                "by_job": defaultdict(Counter),
            }  # fmt: skip
        return rows[task]

    for task in base:
        row(task)
    for rec in records:
        if rec["status"] == "infrastructure":
            r = row(rec["task_id"])
            r["attempts_lost"] += 1
            r["attempts_lost_by_type"][rec["infrastructure_type"]] += 1
            r["by_job"][rec["job"]]["attempts_lost"] += 1
    for key, rec in finals.items():
        if rec["status"] == "infrastructure":
            row(key[2])["final_slots_lost"] += 1
            row(key[2])["by_job"][rec["job"]]["final_slots_lost"] += 1
        elif rec["status"] == "cap_truncated":
            row(key[2])["final_slots_cap_truncated"] += 1
            row(key[2])["by_job"][rec["job"]]["final_slots_cap_truncated"] += 1
    for job in jobs_present:
        _, size, session = job.split("-")
        for task in base:
            for h in R.HARNESSES:
                for r in R.RERUNS:
                    if (size, session, task, h, r) not in finals:
                        row(task)["base_slots_without_record"] += 1
                        row(task)["by_job"][job]["base_slots_without_record"] += 1
    order = (
        base
        + [t for t in ext if t in rows]
        + sorted(t for t in rows if t not in base and t not in ext)
    )
    return {
        "source": "episode records (every attempt) and their final records (records.final_records)",
        "tasks": {
            t: {
                **{
                    k: v for k, v in rows[t].items() if k not in ("attempts_lost_by_type", "by_job")
                },
                "attempts_lost_by_type": dict(sorted(rows[t]["attempts_lost_by_type"].items())),
                "by_job": {j: dict(c) for j, c in sorted(rows[t]["by_job"].items())},
            }
            for t in order
        },
    }


# --------------------------------------------------------------------------- cost card


def cost_card_prices(costs: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any]:
    if not costs:
        return RR.not_estimable("no costs.json (analysis costs) was given")
    A, P = O.frozen("analysis"), O.frozen("plan")

    def against(g: float | None, v: int) -> dict[str, Any]:
        central, high = P.PRICE_CENTRAL[v], P.PRICE_HIGH[v]
        if g is None:
            return {"price_central": central, "price_high": high, "gpu_h_per_episode": None}
        return {
            "gpu_h_per_episode": g, "price_central": central, "price_high": high,
            "ratio_to_central": round(g / central, 4), "ratio_to_high": round(g / high, 4),
            "above_central": g > central, "above_high": g > high,
        }  # fmt: skip

    jobs = {}
    for job, c in sorted(costs.items()):
        v = int(c["V"])
        jobs[job] = {
            "V": v,
            **against(float(c["gpu_h_per_episode"]), v),
            "vm_h_per_episode": c.get("vm_h_per_episode"),
            "gpu_elapsed_source": c.get("gpu_elapsed_source"),
            "by_harness": {h: against(hc.get("gpu_h_per_episode"), v)
                           for h, hc in sorted((c.get("by_harness") or {}).items())},
        }  # fmt: skip
    sizes = {}
    for size, sc in A.costs_by_size(costs).items():
        vs = {int(costs[j]["V"]) for j in sc["jobs"]}
        sizes[size] = {
            **sc,
            **(
                against(sc["gpu_h_per_episode"], vs.pop())
                if len(vs) == 1
                else {"V": sorted(vs), "note": "jobs at different V: no single price"}
            ),
        }
    return {
        "source": "costs.json from 'analysis costs' (section 9 item 10); prices from plan.py",
        "note": "DR4 and P5 read the high price (report.json); the central comparison is "
        "descriptive (section 15)",
        "jobs": jobs,
        "by_size": sizes,
    }


# --------------------------------------------------------------------------- setup and postconfig


def reply_class(reply: Mapping[str, Any]) -> str:
    status = reply.get("status")
    if not isinstance(status, int) or isinstance(status, bool):
        return "no_http_reply"
    if status >= 500:
        return "http_5xx"
    if status != 200:
        return f"http_{status // 100}xx"
    if reply.get("returncode") not in (None, 0):
        return "http_200_nonzero_returncode"
    return "ok"


def failure_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    failed = O.frozen("osworld_live").setup_reply_failed
    out: dict[str, Any] = {
        "episodes": len(records), "setup_replies": 0, "setup_replies_failed": 0,
        "setup_failed_by_type": Counter(), "setup_failed_by_class": Counter(),
        "episodes_with_failed_setup_reply": 0, "infra_task_setup": 0, "postconfig_replies": 0,
        "postconfig_replies_failed": 0, "postconfig_failed_by_type": Counter(),
        "postconfig_failed_by_class": Counter(), "episodes_with_failed_postconfig_reply": 0,
    }  # fmt: skip
    for rec in records:
        setup = rec.get("setup") if isinstance(rec.get("setup"), dict) else {}
        bad_setup = [r for r in setup.get("replies") or () if failed(r)]
        out["setup_replies"] += len(setup.get("replies") or ())
        out["setup_replies_failed"] += len(bad_setup)
        out["episodes_with_failed_setup_reply"] += int(bool(bad_setup))
        out["infra_task_setup"] += int(rec.get("infrastructure_type") == "task_setup")
        for reply in bad_setup:
            out["setup_failed_by_type"][str(reply.get("type") or "unknown")] += 1
            out["setup_failed_by_class"][reply_class(reply)] += 1
        post = list(rec.get("postconfig_replies") or ())
        bad_post = [r for r in post if failed(r)]
        out["postconfig_replies"] += len(post)
        out["postconfig_replies_failed"] += len(bad_post)
        out["episodes_with_failed_postconfig_reply"] += int(bool(bad_post))
        for reply in bad_post:
            out["postconfig_failed_by_type"][str(reply.get("type") or "unknown")] += 1
            out["postconfig_failed_by_class"][reply_class(reply)] += 1
    return {k: (dict(sorted(v.items())) if isinstance(v, Counter) else v) for k, v in out.items()}


def failures_items(
    finals: Mapping[Any, Mapping[str, Any]], records: Sequence[Mapping[str, Any]]
) -> dict:
    final_list = [r for _k, r in sorted(finals.items())]
    return {
        "source": "episode records' setup.replies and postconfig_replies, failed by "
        "osworld_live.setup_reply_failed (not HTTP 200, or a non-zero returncode); stdout tails "
        "are never in the records (section 16)",
        "final_records": {c: failure_counts(rs) for c, rs in by_cell(final_list).items()},
        "attempts": {c: failure_counts(rs) for c, rs in by_cell(records).items()},
        "attempts_total": failure_counts(records),
    }


# --------------------------------------------------------------------------- host snapshots


def _load(snapshot: Mapping[str, Any]) -> list[float] | None:
    raw = snapshot.get("loadavg")
    try:
        return [float(x) for x in raw] if raw else None
    except (TypeError, ValueError):
        return None


def host_snapshots(run_dir: Path) -> dict[str, Any]:
    receipt = O.read_json(run_dir / "lane-receipt.json")
    vm = str(receipt.get("job_id"))
    gpu = str((receipt.get("gpu_job") or {}).get("job_id"))
    pair = {vm, gpu}
    snaps = list(receipt.get("snapshots") or [])
    owner = None
    for snap in snaps:
        for row in snap.get("squeue_foreign") or []:
            if row and str(row[0]) == gpu and len(row) > 1:
                owner = row[1]
    entries, seen = [], {}
    for snap in snaps:
        foreign = []
        for row in snap.get("squeue_foreign") or []:
            if not row or str(row[0]) in pair:
                continue
            cells = list(row) + [None] * (6 - len(row))
            same = owner is not None and cells[1] == owner
            item = {"job": cells[0], "owner": "same user" if same else "other user",
                    "state": cells[2], "cpus": cells[3], "gres": cells[4]}  # fmt: skip
            if same:
                item["name"] = cells[5]
            foreign.append(item)
            seen.setdefault(str(cells[0]), {k: v for k, v in item.items() if k != "state"})
            seen[str(cells[0])].setdefault("states", set()).add(cells[2])
        running = [f for f in foreign if f["state"] == "RUNNING"]
        entries.append({
            "block": snap.get("block"), "t": snap.get("t"), "loadavg": _load(snap),
            "containers_running_total": snap.get("containers_running_total"),
            "containers_ours": snap.get("containers_ours"), "foreign_jobs": foreign,
            "foreign_running_cpus": sum(int(f["cpus"]) for f in running
                                        if str(f["cpus"] or "").isdigit()),
        })  # fmt: skip
    loads = [e["loadavg"] for e in entries if e["loadavg"]]
    return {
        "vm_job": vm,
        "gpu_job": gpu,
        "snapshots": entries,
        "summary": {
            "snapshots": len(entries),
            "max_loadavg": [round(max(x[i] for x in loads), 2) for i in range(3)]
            if loads
            else None,
            "snapshots_with_foreign_running_job": sum(
                1 for e in entries if any(f["state"] == "RUNNING" for f in e["foreign_jobs"])
            ),
            "foreign_jobs": [
                {
                    **{k: v for k, v in item.items() if k != "states"},
                    "states": sorted(str(x) for x in item["states"]),
                }
                for _job, item in sorted(seen.items())
            ],
        },
    }


# --------------------------------------------------------------------------- corrected and domains


def per_domain_values(
    finals: Mapping[Any, Mapping[str, Any]],
    tasks: Sequence[str],
    domains: Mapping[str, str],
    value: str,
) -> dict[str, Any]:
    """``analysis.per_domain``'s description with the outcome ``value`` of ``outcome_array``."""
    A, E, R = O.frozen("analysis"), O.frozen("estimators"), O.frozen("records")
    if value == "binary":
        return A.per_domain(finals, tasks, domains)
    out: dict[str, Any] = {}
    with RR._quiet():
        for domain in sorted({domains[t] for t in tasks}):
            ts = [t for t in tasks if domains[t] == domain]
            y = R.outcome_array(finals, ts, value=value)
            out[domain] = {"tasks": len(ts), "success_by_size_harness": A._f(E.success(y)),
                           "delta": A._f(E.delta(y))}  # fmt: skip
    return out


def dr3_block(guarded: Mapping[str, Any] | None) -> dict[str, Any]:
    if guarded is None:
        return RR.not_estimable("no --report-guarded was given")
    R = O.frozen("records")
    prim = guarded["primary"]
    est = prim.get("estimates") or {}
    missing = RR.not_estimable("not in the guarded report (no size holds two sessions)")

    def pick(name: str) -> Any:
        return est.get(name, missing)

    def listed(part: str, key: str, zi: int) -> Any:
        values = (prim.get(part) or {}).get(key)
        return values[zi] if isinstance(values, list) else missing

    out: dict[str, Any] = {"source": "report-guarded.json primary (DR3 reports, decides nothing)"}
    succ = prim.get("success_by_size_harness") or []
    for zi, z in enumerate(R.SIZES):
        rates = dict(zip(R.HARNESSES, succ[zi], strict=True)) if zi < len(succ) else None
        out[z] = {
            "success_by_harness": rates,
            "D_b": pick(f"D_b_{z}"), "D_w": pick(f"D_w_{z}"), "X": pick(f"X_{z}"),
            "X_c": pick(f"X_centred_{z}"), "session_shift": pick(f"session_shift_{z}"),
            "common_session_share_rho": listed("session_common_share", "common_share", zi),
            "harness_effect_by_session": {
                key: listed("delta_session_heterogeneity", key, zi)
                for key in ("difference", "se", "n_tasks")
            },
        }  # fmt: skip
    return out


# --------------------------------------------------------------------------- assemble


def assemble(
    records: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    runs: Mapping[str, Path],
    *,
    costs: Mapping[str, Any] | None,
    analysis_dir: Path | None,
    guarded: Mapping[str, Any] | None,
) -> dict[str, Any]:
    A, R, P, rules = (O.frozen(n) for n in ("analysis", "records", "plan", "rules"))
    recs = [R.validate(r) for r in records]
    finals = R.final_records(recs)
    base = list(plan["base"])
    blocks = {int(k): v for k, v in plan.get("extension_blocks", {}).items()}
    done = R.completed_extension_blocks(recs, blocks)
    secondary = base + [t for b in done for t in blocks[b]]
    sets = {"primary": base, "secondary": secondary}
    dr0 = {job: rules.run_dir_dr0(run_dir, plan) for job, run_dir in sorted(runs.items())}
    comp = RR.completeness(recs, plan, list(dr0.values()))
    out: dict[str, Any] = {
        "schema": O.SCHEMA + "-s15",
        "sets": {
            "primary": "base (plan['base'])",
            "secondary": f"base plus completed extension "
            f"blocks {done} (records.completed_extension_blocks)",
        },  # fmt: skip
        "labels": RR.labels(comp, plan),
        "completeness": comp,
        "dr0_per_job": {"source": "rules.run_dir_dr0 (receipt included); exit 3 = fires", **dr0},
        "output_tokens": output_tokens(finals, recs, sets),
        "steps": steps_items(finals, sets),
        **per_episode_items(finals, recs, base),
        "losses_by_task": losses_by_task(recs, finals, plan, comp["jobs_present"]),
        "cost_card_prices": cost_card_prices(costs),
        "offline_setup_exclusions": {
            "source": "the frozen plan's offline_excluded (plan.offline_exclusions over G0 "
            "item 5's "
            "second-pass records, section 5.4)",
            "rules": "(a) a setup or postconfig step installs from the network; (b) a setup step "
            "failed in the guest, or a diagnostic lacks its product; (c) postconfig not probed, "
            "or its install failed on the initial state",
            "excluded": plan.get("offline_excluded"),
            "equals_plan_module_constant": plan.get("offline_excluded")
            == {t: list(r) for t, r in sorted(P.OFFLINE_EXCLUDED.items())},
            "setup_check_sha256": plan.get("setup_check_sha256"),
        },
        "setup_and_postconfig_failures": failures_items(finals, recs),
        "host_snapshots": {
            "source": "lane-receipt.json snapshots (harness.q2.vm.driver.snapshot_host): load "
            "average, Slurm queue, container counts; foreign = jobs other than the pair",
            **{job: host_snapshots(run_dir) for job, run_dir in sorted(runs.items())},
        },
    }
    with RR._quiet():
        y = R.outcome_array(finals, secondary, value="corrected")
    block, notes = RR.guarded_analysis(y, comp)
    out["secondary_corrected"] = {
        "source": "analysis.analyse_array(records.outcome_array(finals, secondary, "
        "value='corrected')) with the guard; corrected verdicts stay secondary (section 8)",
        "blocks": done,
        **block,
        "flips_per_task": A.corrected_flips(finals, secondary),
        "guard_readings": notes,
    }
    domains = plan.get("task_domains") or {}
    if domains:
        out["per_domain"] = {
            "source": "descriptive (section 15); report.json holds primary raw",
            "primary_corrected": per_domain_values(finals, base, domains, "corrected"),
            "secondary_raw": per_domain_values(finals, secondary, domains, "binary"),
            "secondary_corrected": per_domain_values(finals, secondary, domains, "corrected"),
        }
    rows: list[dict[str, Any]] = []
    coverage: dict[str, Any] = {}
    if analysis_dir is not None:
        for job, run_dir in sorted(runs.items()):
            rescore_dir = analysis_dir / f"rescore-{RJ.vm_job_id(run_dir)}"
            coverage[job] = RJ.job_coverage(run_dir, rescore_dir)
            if (rescore_dir / "rescored.jsonl").is_file():
                rows += O.read_jsonl(rescore_dir / "rescored.jsonl")
    by_attempt = RJ.rows_by_attempt(rows)
    out["rescoring"] = {
        "source": "rescore capture rows (rescore-<vm>/rescored.jsonl) and the merged records",
        "coverage_by_job": coverage or RR.not_estimable("no --analysis-dir was given"),
        "primary": RJ.verdict_sources(finals, base, by_attempt),
        "secondary": RJ.verdict_sources(finals, secondary, by_attempt),
        "note": "a verdict without corrected_score falls back to the live score "
        "(records.outcome_array); a flip where no correction applies is a replay mismatch",
    }
    base_set = set(base)
    scored = [k for k, r in finals.items() if r["status"] == "scored"]
    out["checker_noise_set"] = {
        "set": "analysis.checker_noise reads every final record with status 'scored', on base "
        "and extension tasks alike (not only the base primary set); pairs are formed within "
        "(size, task, harness) over sessions and reruns; mismatches compare offline_raw_score "
        "with the live score",
        "scored_final_records_read": {
            "base": sum(1 for k in scored if k[2] in base_set),
            "extension": sum(1 for k in scored if k[2] not in base_set),
        },
    }
    out["truncation"] = {
        "registered_label_set": "analysis.truncation_labels reads every final record (base and "
        "extension tasks, every status): the registered definition, since section 15 names the "
        "function",
        "base_only_description": A.truncation_labels(
            {k: r for k, r in finals.items() if k[2] in base_set}
        ),
    }
    out["dr3"] = dr3_block(guarded)
    out["report_carries"] = (
        "losses by type and cell, IRError and metric-exception counts, observation and postconfig "
        "counts per cell and session, cap truncations, the sensitivities, truncation shares, "
        "exposure strata, checker-input discordance, corrected flips (base), fractional counts, "
        "DR1, DR2, DR4, DR5 and P1-P5: read them from report-guarded.json"
    )
    return out


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True, help="merged A1 records (a1.jsonl)")
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument("--costs", type=Path)
    parser.add_argument("--analysis-dir", type=Path, help="holds rescore-<vm>/rescored.jsonl")
    parser.add_argument("--report-guarded", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    O.use_export(args.export)
    if args.out.exists():
        raise O.OpsError(f"{args.out} exists; operator outputs are never overwritten")
    R = O.frozen("records")
    out = assemble(
        R.read_jsonl(args.records),
        O.read_json(args.plan),
        O.run_dirs_by_job(args.run_dir),
        costs=O.read_json(args.costs) if args.costs else None,
        analysis_dir=args.analysis_dir,
        guarded=O.read_json(args.report_guarded) if args.report_guarded else None,
    )
    out["inputs"] = {
        "records": O.sha256_file(args.records),
        "plan": O.sha256_file(args.plan),
        "costs": O.sha256_file(args.costs) if args.costs else None,
        "report_guarded": O.sha256_file(args.report_guarded) if args.report_guarded else None,
    }
    O.write_new(args.out, O.dumps(out))
    print(json.dumps({"label": out["labels"]["incomplete"], "items": sorted(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
