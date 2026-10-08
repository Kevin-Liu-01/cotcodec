#!/usr/bin/env python3
"""D37 (iii) validation job under ``q1-stage0-exec/2``: safety, cost and projection.

CPU only. Written and committed before the job ran (rule ``q1-exec2-validation/1``,
``harness/q1/exec2_validation.py``); run once on the job's output. Inputs (hashes
recorded in the output):

- the job's driver output (``<run>/q1``) with its store beside it (``<run>/q1-refstore``)
  and the lane's ``job.env`` / ``termination.env`` (physical GPU-hours);
- the committed D31 cost card (``../../2026-10-07/q1-engineering-d31/cost-card-d31.json``);
- the host-only Stage 0 planning counts (``stage0-counts-v2.json``, the file every
  earlier card used);
- the D31 re-pilot's run directory (Slurm 713, ``<run713>/q1``): the store model the
  fix pass projected with, and the same items at ``q1-stage0-exec/1`` for a paired
  comparison.

What it reports:

1. **Safety**: resource failures (out-of-memory and the other ``faults`` markers)
   per item attempt, shared or alone; contention retries; crashes and timeouts;
   health-check events, recoveries and failures alone; retired slots and devices;
   memory-guard waits and unreadable readings; A5 ``na`` checks with their reasons;
   items started, final, never final, cut at the hard deadline, never started; the
   store's lookups (used or inline, why); measured peak GPU memory against each
   item's estimate and the largest concurrent sum of measured peaks.
2. **Cost** (pre-specified): each final item's GPU-seconds (its share of the GPU
   while it ran, ``cost_card.charge``) against the ``q1-stage0-exec/2`` model of the
   fix pass: the D31 size model, ``cost_card.concurrency_multiplier`` at the item's
   units, and for a consumer that read the store the pre-specified (linear) store
   ratio; reference items against the store model's reference fits. Per gate, per
   concurrency regime (12 per GPU, fewer), per problem, overall; the adversarial
   controls (L1/1) separately; and the same (kernel, gate) store items as job 713 ran
   them under ``q1-stage0-exec/1`` (paired).
3. **Adversarial controls**: store against inline rows of each consumer gate.
4. **Projection** through P3 and P7, central and high (the card's convention: fixed
   part plus scoring times the matching registered scenario's bootstrap scale), with
   this job's physical GPU-hours added to the fixed part:
   - A: ``q1-stage0-exec/2`` without the store (fix pass, model only);
   - B: ``q1-stage0-exec/2``, store without gate (a), linear ratio (pre-specified),
     per job (fix pass, model only);
   - C (primary, pre-specified): B with its scoring scaled by R, this job's
     measured over B-predicted GPU-seconds of every final re-pilot item (store
     scoring items and reference items; the adversarial controls excluded, reported
     apart); also with R at the 2.5% and 97.5% points of a bootstrap over the
     problems reached (1,000 resamples, seed 42);
   - D: B with each gate's size model scaled by that gate's measured/predicted
     ratio (references by theirs; a gate with no final item keeps R);
   - E: A with its scoring scaled by the ratio over the store-independent gates
     only (every gate but c, A1, A2, A3, A5).
   C-E are post hoc in the sense that matters: they scale a model by a partial
   sample that the rule's cheapest-first order selected, so the problems the model
   expects to be most expensive are the least represented.

    python analyze_exec2_validation.py --run RUN/q1 --run-root RUN --counts stage0-counts-v2.json \\
        --repilot-run RUN713/q1 --out exec2-validation.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from harness.q1 import cost_card as cc  # noqa: E402
from harness.q1 import exec2_validation as rule  # noqa: E402
from harness.q1 import faults, memory, pilot, repilot, trim  # noqa: E402

CARD = ROOT / "program/evidence/2026-10-07/q1-engineering-d31/cost-card-d31.json"
CONSUMERS = cc.STORE_CONSUMER_GATES
SEED = 42
RESAMPLES = 1000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def env_file(path: Path) -> dict[str, str]:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k] = v
    return out


def physical_gpu_hours(run_root: Path) -> dict[str, Any]:
    job, term = env_file(run_root / "job.env"), env_file(run_root / "termination.env")
    start, end = job.get("started_at"), term.get("finished_at")
    seconds = None
    if start and end:
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        seconds = (datetime.strptime(end, fmt) - datetime.strptime(start, fmt)).total_seconds()
    gpus = len([g for g in job.get("gpu_devices", "").split(",") if g != ""]) or 1
    return {
        "job_id": job.get("job_id"),
        "started_at": start,
        "finished_at": end,
        "seconds": seconds,
        "gpus": gpus,
        "gpu_hours": None if seconds is None else round(gpus * seconds / 3600, 4),
        "termination": {
            k: term.get(k)
            for k in ("reason", "exit_code", "checkpoint_ready", "container_killed_by")
        },
    }


# --- 1. safety --------------------------------------------------------------------


def safety(run: Path, store: Path, planned: list[dict[str, Any]]) -> dict[str, Any]:
    phase = run / "validation"
    summary = json.loads((run / "summary.json").read_text())
    rows = read_jsonl(phase / "journal.jsonl")
    refs = read_jsonl(phase / "references.jsonl")
    cut = read_jsonl(phase / "cut.jsonl")
    mem = read_jsonl(phase / "memory.jsonl")
    attempts: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows + refs:
        attempts[(row["details"]["item_key"], int(row.get("attempt") or 1))].append(row)
    resource = []
    for (key, attempt), group in sorted(attempts.items()):
        text = json.dumps([r["details"] for r in group], default=str)
        if faults.is_resource_text(text):
            resource.append(
                {
                    "item_key": key,
                    "attempt": attempt,
                    "exclusive": bool(group[0]["details"].get("item_exclusive")),
                    "units": group[0]["details"].get("item_units"),
                    "final": any(r["details"].get("item_final") for r in group),
                    "marker": faults.first_marker(text, faults.RESOURCE_MARKERS),
                }
            )
    status: dict[str, dict[str, Any]] = {}
    for (key, attempt), group in sorted(attempts.items(), key=lambda x: (x[0][0], x[0][1])):
        final = group[-1]["details"].get("item_final", False)
        status[key] = {"attempt": attempt, "final": bool(final)}
    planned_keys = [f"{e['kernel_id']}|{e['gate']}|seed-{e['seed']}" for e in planned]
    started = [k for k in planned_keys if k in status]
    final = [k for k in started if status[k]["final"]]
    never_final = [k for k in started if not status[k]["final"]]
    cut_keys = sorted({c["item_key"] for c in cut})
    not_started = [k for k in planned_keys if k not in status and k not in cut_keys]
    a5 = [r for r in rows if r["gate"] == "A5"]
    na_checks = []
    for row in a5:
        for check in row["details"].get("checks") or []:
            if check.get("status") == "na":
                na_checks.append(
                    {
                        "item_key": row["details"]["item_key"],
                        "check": check.get("check"),
                        "na_reasons": check.get("na_reasons"),
                    }
                )
    a5_errors = [
        {"item_key": r["details"]["item_key"], "reason": r["details"].get("reason")}
        for r in a5
        if r["verdict"] == "error"
    ]
    lookups: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    for path in sorted((store / "uses").glob("*.json")) if (store / "uses").exists() else []:
        record = json.loads(path.read_text())
        for lookup in record.get("lookups", []):
            used = bool(lookup.get("used"))
            lookups["used" if used else "inline"] += 1
            if not used:
                reasons[str(lookup.get("reason"))[:80]] += 1
    entries = Counter()
    for entry in store.glob("*/*/entry.json"):
        data = json.loads(entry.read_text())
        entries["usable" if data.get("usable") else "unusable"] += 1
        if not data.get("usable"):
            entries["unusable:" + str(data.get("reason") or data.get("unusable_reason"))[:60]] += 1
    ratios = []
    spans = {}
    for row in rows + refs:
        d = row["details"]
        if d.get("item_started_at") and d.get("item_ended_at"):
            spans[(d["item_key"], int(row.get("attempt") or 1))] = (
                d["item_started_at"],
                d["item_ended_at"],
            )
    concurrent = []
    for record in mem:
        peak, estimate = record.get("peak_reserved_bytes"), record.get("memory_bytes_estimate")
        if peak is not None and estimate:
            ratios.append(
                {
                    "item_key": record["item_key"],
                    "units": record.get("units"),
                    "peak_gb": round(peak / 1e9, 3),
                    "estimate_gb": round(estimate / 1e9, 3),
                    "peak_over_estimate": round(peak / estimate, 4),
                }
            )
        span = spans.get((record["item_key"], int(record.get("attempt") or 1)))
        if span and peak is not None:
            concurrent.append((span[0], span[1], peak))
    events = sorted({t for s, e, _ in concurrent for t in (s, e)})
    largest = (0.0, None)
    for left, right in zip(events, events[1:], strict=False):
        total = sum(p for s, e, p in concurrent if s <= left and e >= right)
        if total > largest[0]:
            largest = (total, left)
    ratio_values = [r["peak_over_estimate"] for r in ratios]
    return {
        "runner_summary": {
            k: summary.get(k)
            for k in (
                "run",
                "skipped",
                "crashes",
                "timeouts",
                "infra_failures",
                "contention_oom_shared",
                "contention_timeout_shared",
                "health_recovered_alone",
                "health_failed_alone",
                "retired_slots",
                "retired_devices",
                "health_events",
                "memory_guard_waits",
                "memory_guard_unreadable",
                "left_in_queue",
                "deferred_by_deadline",
                "time_boxed",
                "expired_at_hard_deadline",
                "interrupted",
                "on_done_errors",
                "driver_seconds",
                "soft_deadline_seconds",
                "hard_deadline_seconds",
            )
        },
        "resource_failures": {
            "item_attempts": len(resource),
            "shared": sum(1 for r in resource if not r["exclusive"]),
            "alone": sum(1 for r in resource if r["exclusive"]),
            "by_problem": dict(
                Counter(
                    next(
                        (
                            e["problem_id"]
                            for e in planned
                            if r["item_key"].startswith(e["kernel_id"] + "|")
                        ),
                        "?",
                    )
                    for r in resource
                )
            ),
            "list": resource,
        },
        "items": {
            "planned": len(planned_keys),
            "started": len(started),
            "final": len(final),
            "never_final": never_final,
            "cut_at_hard_deadline": cut_keys,
            "not_started": len(not_started),
            "not_started_by_problem": dict(
                Counter(
                    e["problem_id"]
                    for e in planned
                    if f"{e['kernel_id']}|{e['gate']}|seed-{e['seed']}" in set(not_started)
                )
            ),
            "second_attempts": sum(1 for v in status.values() if v["attempt"] > 1),
        },
        "a5": {
            "rows": len(a5),
            "na_checks": na_checks,
            "error_rows": a5_errors,
        },
        "store": {
            "lookups": dict(lookups),
            "inline_reasons": dict(reasons),
            "entries": dict(entries),
        },
        "memory": {
            "records": len(ratios),
            "peak_over_estimate_max": max(ratio_values) if ratio_values else None,
            "peak_over_estimate_median": statistics.median(ratio_values) if ratio_values else None,
            "items_over_estimate": [r for r in ratios if r["peak_over_estimate"] > 1],
            "largest_concurrent_measured_peak_gb": round(largest[0] / 1e9, 2),
            "device_bytes_policy": memory.POLICY["device_bytes"],
            "guard_budget_gb": round(memory.budget_bytes() / 1e9, 1),
        },
    }


# --- 2. cost ----------------------------------------------------------------------


def predicted(
    item: Mapping[str, Any],
    plan: Mapping[str, Mapping[str, Any]],
    fits: Mapping[str, Any],
    factors: Mapping[str, float],
    store: cc.StoreModel,
    *,
    with_store: bool,
) -> float | None:
    gate, problem = item["gate"], item["problem_id"]
    gb = (pilot.native_input_bytes(problem) or 0) / 1e9
    if gate.startswith("ref_"):
        fit = store.reference_fits.get(gate)
        return None if fit is None else max(0.0, fit["alpha"] + fit["beta"] * gb)
    fit = fits.get(gate)
    if fit is None:
        return None
    seconds = fit["alpha"] + fit["beta"] * gb
    planned = plan[item["item_key"]]
    if (pilot.native_input_bytes(problem) or 0) < cc.CONCURRENCY_BELOW_BYTES and gate in factors:
        seconds *= cc.concurrency_multiplier(int(planned["units"]), factors[gate])
    if with_store and gate in CONSUMERS and "reference_store" in (planned.get("options") or {}):
        seconds *= store.ratio(gate, gb)
    return seconds


def ratio_block(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    measured = sum(r["measured"] for r in rows)
    model = sum(r[key] for r in rows)
    return {
        "items": len(rows),
        "measured_gpu_seconds": round(measured, 2),
        "model_gpu_seconds": round(model, 2),
        "measured_over_model": round(measured / model, 3) if model else None,
        "median_item_measured": round(statistics.median([r["measured"] for r in rows]), 3)
        if rows
        else None,
    }


def cost(
    run: Path,
    planned: list[dict[str, Any]],
    card: Mapping[str, Any],
    store: cc.StoreModel,
    store_free: cc.StoreModel,
    run713: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fits, factors = card["size_model"], card["paired_concurrency"]["factors"]
    plan = {f"{e['kernel_id']}|{e['gate']}|seed-{e['seed']}": e for e in planned}
    job = cc.load_job(run)
    rows = []
    for item in job["items"]:
        if not item["final"] or item["gpu_seconds"] is None or item["item_key"] not in plan:
            continue
        units = int(plan[item["item_key"]]["units"])
        base, arm = rule.arm_of(item["kernel_id"])
        rows.append(
            {
                "item_key": item["item_key"],
                "kernel_id": base,
                "arm": arm,
                "gate": item["gate"],
                "problem_id": item["problem_id"],
                "units": units,
                "per_gpu": 12 // units,
                "attempt": item["attempt"],
                "exclusive": bool(item["exclusive"]),
                "measured": item["gpu_seconds"],
                "wall": item["wall"],
                "model_exec2_no_store": predicted(
                    item, plan, fits, factors, store, with_store=False
                ),
                "model_exec2_store": predicted(item, plan, fits, factors, store, with_store=True),
                "adversarial": item["problem_id"] == rule.ADVERSARIAL_PROBLEM,
                "reference": item["gate"].startswith("ref_"),
            }
        )
    usable = [r for r in rows if r["model_exec2_store"] is not None]
    repilot_rows = [r for r in usable if not r["adversarial"] and r["arm"] == "store"]
    scoring = [r for r in repilot_rows if not r["reference"]]
    references = [r for r in repilot_rows if r["reference"]]
    out: dict[str, Any] = {
        "overall_repilot_store_and_references": ratio_block(repilot_rows, "model_exec2_store"),
        "repilot_scoring_items": ratio_block(scoring, "model_exec2_store"),
        "repilot_reference_items": ratio_block(references, "model_exec2_store"),
        "repilot_scoring_vs_no_store_model": ratio_block(scoring, "model_exec2_no_store"),
        "store_independent_gates": ratio_block(
            [r for r in scoring if r["gate"] not in CONSUMERS], "model_exec2_no_store"
        ),
        "by_gate": {
            g: ratio_block([r for r in repilot_rows if r["gate"] == g], "model_exec2_store")
            for g in sorted({r["gate"] for r in repilot_rows})
        },
        "by_regime": {
            "12_per_gpu": ratio_block(
                [r for r in scoring if r["per_gpu"] >= 12], "model_exec2_store"
            ),
            "fewer_than_12_per_gpu": ratio_block(
                [r for r in scoring if r["per_gpu"] < 12], "model_exec2_store"
            ),
            "by_items_per_gpu": {
                str(k): ratio_block([r for r in scoring if r["per_gpu"] == k], "model_exec2_store")
                for k in sorted({r["per_gpu"] for r in scoring})
            },
        },
        "by_problem": {
            p: ratio_block([r for r in repilot_rows if r["problem_id"] == p], "model_exec2_store")
            for p in rule.PROBLEM_ORDER
            if any(r["problem_id"] == p for r in repilot_rows)
        },
        "adversarial": {
            arm: ratio_block(
                [r for r in usable if r["adversarial"] and r["arm"] == arm and not r["reference"]],
                "model_exec2_store" if arm == "store" else "model_exec2_no_store",
            )
            for arm in ("store", "inline")
        }
        | {
            "references": ratio_block(
                [r for r in usable if r["adversarial"] and r["reference"]], "model_exec2_store"
            )
        },
        "references_free_bound_note": (
            "reference items are priced by the D31 store model fitted at 12 per GPU "
            "(job 713); the projection rows scale them with the scoring"
        ),
    }
    # The same store items in job 713 (q1-stage0-exec/1, 12 per GPU, store twin ``.store``).
    old = {
        (i["kernel_id"].removesuffix(".store"), i["gate"]): i
        for i in cc.load_job(run713)["items"]
        if i["final"]
        and i["gpu_seconds"] is not None
        and (i["kernel_id"].endswith(".store") or i["gate"].startswith("ref_"))
    }
    paired = []
    for r in repilot_rows:
        before = old.get((r["kernel_id"], r["gate"]))
        if before is not None:
            paired.append(
                {
                    "problem_id": r["problem_id"],
                    "gate": r["gate"],
                    "exec2": r["measured"],
                    "exec1_job713": before["gpu_seconds"],
                    "exec1_attempt": before["attempt"],
                    "exec1_exclusive": bool(before["exclusive"]),
                }
            )
    out["paired_with_job713_exec1"] = {
        "items": len(paired),
        "exec2_gpu_seconds": round(sum(p["exec2"] for p in paired), 2),
        "exec1_gpu_seconds": round(sum(p["exec1_job713"] for p in paired), 2),
        "exec2_over_exec1": round(
            sum(p["exec2"] for p in paired) / sum(p["exec1_job713"] for p in paired), 3
        )
        if paired
        else None,
        "by_problem": {
            p: {
                "items": len(v),
                "exec2_over_exec1": round(
                    sum(x["exec2"] for x in v) / sum(x["exec1_job713"] for x in v), 3
                ),
            }
            for p, v in sorted(
                {
                    p: [x for x in paired if x["problem_id"] == p]
                    for p in {x["problem_id"] for x in paired}
                }.items()
            )
        },
    }
    return out, rows


# --- 3. adversarial controls --------------------------------------------------------


def adversarial(run: Path, store: Path) -> dict[str, Any]:
    rows = [
        r
        for r in read_jsonl(run / "validation" / "journal.jsonl")
        if r["kernel_id"].startswith("ctl-kernelbench-")
    ]

    # Group by the item's gate (the item key), not the row's: gate (c) items write
    # rows c1, c2, c3, c_1e-2 and c_kbv_raw (corrected after the job; the first run of
    # this script grouped by row gate and found no gate (c) rows).
    def item_gate(r: Mapping[str, Any]) -> str:
        return r["details"]["item_key"].split("|")[1]

    finals: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    last_attempt: dict[tuple[str, str], int] = {}
    for r in rows:
        key = (r["kernel_id"], item_gate(r))
        last_attempt[key] = max(last_attempt.get(key, 0), int(r.get("attempt") or 1))
    for r in rows:
        if int(r.get("attempt") or 1) != last_attempt[(r["kernel_id"], item_gate(r))]:
            continue
        base, arm = rule.arm_of(r["kernel_id"])
        finals[(base, item_gate(r), arm)].append(r)
    uses = {}
    if (store / "uses").exists():
        for path in (store / "uses").glob("*.json"):
            record = json.loads(path.read_text())
            if record.get("item_key", "").startswith("ctl-kernelbench-"):
                uses[record["item_key"]] = record.get("lookups")
    out = []
    for name in rule.ADVERSARIAL:
        kernel = f"ctl-kernelbench-{name.replace('_', '-')}-L1-1"
        for gate in rule.ADVERSARIAL_GATES:
            store_rows = finals.get((kernel, gate, "store"), [])
            inline_rows = finals.get((kernel, gate, "inline"), [])
            entry: dict[str, Any] = {
                "control": kernel,
                "gate": gate,
                "store_verdicts": dict(Counter(r["verdict"] for r in store_rows)),
                "inline_verdicts": dict(Counter(r["verdict"] for r in inline_rows)),
                "store_aggregate": sorted(
                    f"{r['gate']}:{r['verdict']}"
                    for r in store_rows
                    if r["config_id"] == "aggregate"
                ),
                "inline_aggregate": sorted(
                    f"{r['gate']}:{r['verdict']}"
                    for r in inline_rows
                    if r["config_id"] == "aggregate"
                ),
                "a5_checks": {
                    arm: [
                        (c.get("check"), c.get("status"), (c.get("failures") or [""])[0][:80])
                        for r in side
                        for c in (r["details"].get("checks") or [])
                    ]
                    for arm, side in (("store", store_rows), ("inline", inline_rows))
                }
                if gate == "A5"
                else None,
                "store_lookups": uses.get(f"{kernel}|{gate}|seed-42"),
            }
            if store_rows and inline_rows:
                left = sorted(repilot.normalized_row(r) for r in store_rows)
                right = sorted(repilot.normalized_row(r) for r in inline_rows)
                entry["rows_identical"] = left == right
                entry["verdicts_identical"] = sorted(r["verdict"] for r in store_rows) == sorted(
                    r["verdict"] for r in inline_rows
                )
                if left != right:
                    diffs = set()
                    for a, b in zip(left, right, strict=False):
                        diffs |= set(repilot._diff_paths(json.loads(a), json.loads(b)))
                    entry["differing_fields"] = sorted(diffs)[:20]
            else:
                entry["rows_identical"] = None
                entry["verdicts_identical"] = None
            out.append(entry)
    measured = [e for e in out if e["rows_identical"] is not None]
    return {
        "pairs": out,
        "pairs_measured": len(measured),
        "pairs_rows_identical": sum(1 for e in measured if e["rows_identical"]),
        "pairs_verdicts_identical": sum(1 for e in measured if e["verdicts_identical"]),
    }


# --- 4. projection -------------------------------------------------------------------


def projection(
    counts: Mapping[str, Any],
    card: Mapping[str, Any],
    store: cc.StoreModel,
    rows: list[dict[str, Any]],
    job_gpu_hours: float,
) -> dict[str, Any]:
    fits, factors = card["size_model"], card["paired_concurrency"]["factors"]
    anchors, survival = card["large_problem_anchors"], card["compile_filter"]["survival"]
    exposed = trim.load_exposed(trim.PILOT_EXPOSED_PATH)
    scenarios = {t["name"]: t for t in card["trimmed"]}

    def units_of(problem: str, gate: str) -> int:
        return trim.item_units(problem, gate)[0]

    def project(model_fits: Mapping[str, Any] = fits, **kw: Any) -> dict[str, Any]:
        return cc.project_trimmed(
            counts,
            model_fits,
            survival=survival,
            rule=cc.TRIM_RULE,
            factors=factors,
            anchors=anchors,
            exposed=exposed,
            units_of=units_of,
            **kw,
        )

    def through(p: Mapping[str, Any], bucket: str) -> float:
        return sum(v for k, v in p["gpu_hours_by_priority"].items() if k <= bucket)

    def registered(name: str) -> dict[str, float]:
        t = scenarios[name]
        return {
            "fixed": round(sum(t["fixed_gpu_hours"].values()), 3),
            "scale": t["scoring_gpu_hours_95"]["high"] / t["gpu_hours"],
        }

    def row(label: str, p: Mapping[str, Any], match: str, factor: float = 1.0, note: str = ""):
        reg = registered(match)
        fixed = reg["fixed"] + job_gpu_hours
        out = {"scenario": label, "high_scale_from": match, "note": note}
        for bucket in ("P3", "P7"):
            scoring = factor * through(p, bucket)
            out[f"{bucket}_scoring_central"] = round(scoring, 3)
            out[f"{bucket}_central"] = round(fixed + scoring, 2)
            out[f"{bucket}_high"] = round(fixed + reg["scale"] * scoring, 2)
        out["fixed_gpu_hours"] = round(fixed, 3)
        return out

    store_match = "trim2-store-per-job-paired-concurrency"
    nostore_match = "trim2-paired-concurrency"
    a = project()
    b = project(store=store, store_mode="per-job")
    repilot_rows = [
        r for r in rows if not r["adversarial"] and r["arm"] == "store" and r["model_exec2_store"]
    ]
    measured = sum(r["measured"] for r in repilot_rows)
    model = sum(r["model_exec2_store"] for r in repilot_rows)
    big_r = measured / model if model else None
    # cluster bootstrap over the problems reached
    problems = sorted({r["problem_id"] for r in repilot_rows})
    by_problem = {
        p: (
            sum(r["measured"] for r in repilot_rows if r["problem_id"] == p),
            sum(r["model_exec2_store"] for r in repilot_rows if r["problem_id"] == p),
        )
        for p in problems
    }
    rng = random.Random(SEED)
    draws = []
    for _ in range(RESAMPLES):
        pick = [rng.choice(problems) for _ in problems]
        m = sum(by_problem[p][0] for p in pick)
        d = sum(by_problem[p][1] for p in pick)
        if d:
            draws.append(m / d)
    draws.sort()
    lo = draws[int(0.025 * (len(draws) - 1))] if draws else None
    hi = draws[int(0.975 * (len(draws) - 1))] if draws else None
    out: dict[str, Any] = {
        "job_gpu_hours_added_to_fixed": job_gpu_hours,
        "R_measured_over_model_B": round(big_r, 3) if big_r else None,
        "R_bootstrap_problems": {"2.5%": lo and round(lo, 3), "97.5%": hi and round(hi, 3)},
        "problems_in_R": problems,
        "rows": [
            row(
                "A: exec/2 without the store (fix pass model)",
                a,
                nostore_match,
                note="model only; reproduces 18.9 (P3 10.46 / 12.31), this job in the fixed part",
            ),
            row(
                "B: exec/2, store without gate (a), linear ratio (pre-specified), per job (model)",
                b,
                store_match,
                note="model only; reproduces 18.9 (P3 10.66 / 12.58), this job in the fixed part",
            ),
        ],
    }
    if big_r:
        out["rows"].append(
            row(
                f"C: B scaled by this job's measured/model R = {big_r:.3f} (primary)",
                b,
                store_match,
                big_r,
                note="partial sample chosen by order (cheapest first); unreached problems carry R",
            )
        )
        for label, value in (("2.5%", lo), ("97.5%", hi)):
            if value:
                out["rows"].append(
                    row(
                        f"C{label}: B scaled by the bootstrap {label} point of R ({value:.3f})",
                        b,
                        store_match,
                        value,
                        note="cluster bootstrap over the problems reached",
                    )
                )
        # D: per-gate scaled
        per_gate = {}
        for gate in fits:
            g_rows = [r for r in repilot_rows if r["gate"] == gate]
            m, d = sum(r["measured"] for r in g_rows), sum(r["model_exec2_store"] for r in g_rows)
            per_gate[gate] = (m / d) if d else big_r
        ref_rows = [r for r in repilot_rows if r["reference"]]
        m, d = sum(r["measured"] for r in ref_rows), sum(r["model_exec2_store"] for r in ref_rows)
        ref_scale = (m / d) if d else big_r
        scaled_fits = {
            g: {**f, "alpha": f["alpha"] * per_gate[g], "beta": f["beta"] * per_gate[g]}
            for g, f in fits.items()
        }
        scaled_store = cc.StoreModel(
            ratio_fits=store.ratio_fits,
            reference_fits={
                g: {**f, "alpha": f["alpha"] * ref_scale, "beta": f["beta"] * ref_scale}
                for g, f in store.reference_fits.items()
            },
            constant_ratios=store.constant_ratios,
            free_references=store.free_references,
        )
        d_proj = project(scaled_fits, store=scaled_store, store_mode="per-job")
        out["per_gate_scale"] = {g: round(v, 3) for g, v in per_gate.items()}
        out["reference_scale"] = round(ref_scale, 3)
        out["rows"].append(
            row(
                "D: B with per-gate scales (references by theirs)",
                d_proj,
                store_match,
                note="post hoc; a gate's scale rests on its few final items",
            )
        )
    independent = [
        r
        for r in repilot_rows
        if not r["reference"] and r["gate"] not in CONSUMERS and r["model_exec2_no_store"]
    ]
    m = sum(r["measured"] for r in independent)
    d = sum(r["model_exec2_no_store"] for r in independent)
    if d:
        out["R_store_independent"] = round(m / d, 3)
        out["rows"].append(
            row(
                f"E: A scaled by the store-independent gates' R = {m / d:.3f}",
                a,
                nostore_match,
                m / d,
                note="post hoc; gates a, b and A4 only (no reference read)",
            )
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="the job's <run>/q1")
    parser.add_argument("--run-root", type=Path, required=True, help="the lane's run directory")
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--repilot-run", type=Path, required=True, help="job 713's <run>/q1")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    card = json.loads(CARD.read_text())
    counts = json.loads(args.counts.read_text())
    planned = read_jsonl(args.run / "validation" / "items.jsonl")
    store_dir = args.run.parent / f"{args.run.name}-refstore"
    old = cc.load_job(args.repilot_run)["items"]
    pairs, refs = cc.repilot_pairs(old), cc.reference_items(old)
    store = cc.fit_store_model(pairs, refs, ratio_mode="linear", consumers=CONSUMERS)
    store_free = cc.fit_store_model(
        pairs, refs, ratio_mode="constant", consumers=CONSUMERS, free_references=True
    )
    gpu = physical_gpu_hours(args.run_root)
    record: dict[str, Any] = {
        "schema": "q1-exec2-validation-analysis/1",
        "rule": rule.RULE,
        "execution_policy": memory.POLICY_VERSION,
        "inputs": {
            "cost_card_sha256": sha256(CARD),
            "counts_sha256": sha256(args.counts),
            "journal_sha256": sha256(args.run / "validation" / "journal.jsonl"),
            "references_sha256": sha256(args.run / "validation" / "references.jsonl")
            if (args.run / "validation" / "references.jsonl").exists()
            else None,
            "items_sha256_file": sha256(args.run / "validation" / "items.jsonl"),
            "repilot_journal_sha256": sha256(args.repilot_run / "repilot" / "journal.jsonl"),
            "memory_table_sha256": sha256(memory.TABLE_PATH),
        },
        "gpu": gpu,
        "safety": safety(args.run, store_dir, planned),
    }
    record["cost"], rows = cost(args.run, planned, card, store, store_free, args.repilot_run)
    record["adversarial_controls"] = adversarial(args.run, store_dir)
    record["projection"] = projection(counts, card, store, rows, gpu["gpu_hours"] or 0.0)
    record["item_costs"] = rows
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + "\n")
    brief = {k: v for k, v in record.items() if k not in {"item_costs"}}
    brief["safety"] = {k: v for k, v in record["safety"].items() if k != "memory"} | {
        "memory": {
            k: v for k, v in record["safety"]["memory"].items() if k != "items_over_estimate"
        }
    }
    print(json.dumps(brief["projection"]["rows"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
