#!/usr/bin/env python3
"""LM2 (D129, EXPLORATORY) analysis: text-free grade rows and job records in, results out.

Inputs (all text-free, committed under program/evidence/2026-10-16/lm2-resident-eval/):
- ``data/grades.jsonl``: one row per (arm, task, item, seed) from scripts/lm2_score.py;
- ``jobs/<arm>/<job>/summary-*.json`` and ``metrics-*.jsonl``: the driver's records;
- ``jobs/gpu-hours.json``: physical GPU-hours per job (GPUs x Slurm RunTime);
- the plan.

Outputs: ``results.json`` and ``tables.md``. Accuracy is the mean over items of the per-item share
of correct seeds; paired differences use the (item, seed) keys both arms have, with a percentile
bootstrap over items (question clusters; 10,000 draws, seed 42). No multiplicity correction.
"""

# ruff: noqa: E501  (table rows are written as single f-strings)
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.lm2_resident_eval import (  # noqa: E402
    bootstrap_mean,
    cluster_bootstrap_diff,
    item_means,
    load_plan,
    paired_rows,
)

GIB = 2**30
# Dossier fit tiers (DOSSIER.md A10): weights + KV at the stated context + 3 GiB, other work
# stopped. Yes <= 95 GiB, Tight 95-107.5 GiB (the default Metal working-set ceiling), No above.
FIT_YES_GIB, FIT_TIGHT_GIB, BUFFERS_GIB = 95.0, 107.5, 3.0
# KV at 32K tokens, GiB, from the dossier (A9) and its sources; see tables.md for the basis.
KV_32K_GIB = {
    "deepseek-v4-flash-0731": 0.27,  # ds4: 8.39 GiB at 1M tokens -> 8.6 KB per token
    "qwen3-235b-a22b-instruct-2507": 5.875,  # 94 layers x 4 KV heads x 128 x 2 x 2 bytes
    "gpt-oss-120b": 1.1,  # 0.3 GB per 8,192 tokens (dossier S98)
}
# Mac decode speed on a 128 GB M5 Max (dossier section 2): measured where a measurement exists.
MAC_DECODE = {
    "v4f-q2": (39.35, "measured, ds4 maintainer, 2K context (S95)"),
    "v4f-iq3": (36.0, "estimate, dossier row F2: 31-41 (midpoint)"),
    "v4f-q8": (None, "does not fit (reference only)"),
    "qwen235-q3": (31.0, "estimate, dossier row Q2: 27-35 (midpoint)"),
    "gptoss120": (105.0, "community report, upstream llama.cpp tg128 (S97)"),
}
PAIRS_G4 = [("v4f-q2", "v4f-q8"), ("v4f-iq3", "v4f-q8"), ("v4f-q2", "v4f-iq3")]
PAIRS_MODELS = [
    ("v4f-q2", "qwen235-q3"),
    ("v4f-q2", "gptoss120"),
    ("v4f-iq3", "qwen235-q3"),
    ("v4f-iq3", "gptoss120"),
    ("qwen235-q3", "gptoss120"),
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def fit_tier(plan: dict[str, Any], arm_id: str) -> dict[str, Any]:
    arm = plan["arms"][arm_id]
    weights = arm["file_bytes"] / GIB
    kv = KV_32K_GIB[arm["family"]]
    total = weights + kv + BUFFERS_GIB
    tier = "Yes" if total <= FIT_YES_GIB else "Tight" if total <= FIT_TIGHT_GIB else "No"
    return {
        "file_gb": round(arm["file_bytes"] / 1e9, 1),
        "weights_gib": round(weights, 1),
        "kv_32k_gib": kv,
        "resident_32k_gib": round(total, 1),
        "tier_at_32k": tier,
    }


def accuracy_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    means = item_means(rows)
    values = list(means.values())
    n_samples = len(rows)
    tokens = [r["completion_tokens"] or 0 for r in rows]
    correct_tokens = [r["completion_tokens"] or 0 for r in rows if r["correct"]]
    truncated = sum(1 for r in rows if r.get("finish_reason") == "length")
    no_answer = sum(1 for r in rows if not r.get("has_answer"))
    n_correct = sum(1 for r in rows if r["correct"])
    return {
        "items": len(values),
        "samples": n_samples,
        "accuracy": round(100 * sum(values) / len(values), 2) if values else None,
        "ci95": bootstrap_mean(values) if values else None,
        "mean_output_tokens": round(statistics.mean(tokens)) if tokens else None,
        "median_output_tokens": round(statistics.median(tokens)) if tokens else None,
        "mean_tokens_correct": round(statistics.mean(correct_tokens)) if correct_tokens else None,
        "tokens_per_correct": round(sum(tokens) / n_correct) if n_correct else None,
        "truncated_pct": round(100 * truncated / n_samples, 1) if n_samples else None,
        "no_answer_pct": round(100 * no_answer / n_samples, 1) if n_samples else None,
    }


def throughput(job_dir: Path) -> dict[str, Any] | None:
    """Aggregate generated tok/s while every slot is busy (completed + in-flight decoded)."""

    metrics_files = sorted(job_dir.glob("metrics-*.jsonl"))
    summaries = sorted(job_dir.glob("summary-*.json"))
    if not metrics_files or not summaries:
        return None
    summary = json.loads(summaries[0].read_text())
    slots = summary.get("slots")
    rows = load_jsonl(metrics_files[0])
    rows = [r for r in rows if "busy_slots" in r]
    if len(rows) < 3:
        return None
    gen = [(r["t"], r["completed_tokens"] + r["inflight_decoded"], r["busy_slots"]) for r in rows]
    full = [g for g in gen if slots and g[2] >= 0.9 * slots]
    window = full if len(full) >= 3 else gen
    (t0, g0, _), (t1, g1, _) = window[0], window[-1]
    rate = (g1 - g0) / (t1 - t0) if t1 > t0 else None
    total_gen = gen[-1][1]
    return {
        "job_id": summary.get("job_id"),
        "slots": slots,
        "gpus": summary.get("visible_gpus"),
        "load_s": (summary.get("server") or {}).get("load_s"),
        "generation_s": summary.get("generation_s"),
        "steady_window_s": round(t1 - t0, 1),
        "steady_busy_fraction": round(len(full) / len(gen), 2),
        "aggregate_tok_s": round(rate, 1) if rate else None,
        "tok_s_per_gpu": round(rate / summary["visible_gpus"], 1)
        if rate and summary.get("visible_gpus")
        else None,
        "generated_tokens": total_gen,
        "completed_requests": (summary.get("counts") or {}).get("ok"),
        "peak_mib": summary.get("peak_mib"),
    }


def fmt_ci(ci: list[float] | None) -> str:
    return f"[{ci[0]:+.1f}, {ci[1]:+.1f}]" if ci else ""


def analyze(
    args: argparse.Namespace, grades_path: Path | None = None, min_max_tokens: int | None = None
) -> dict[str, Any]:
    plan = load_plan(args.plan)
    grades = [g for g in load_jsonl(grades_path or args.grades) if g.get("correct") is not None]
    if min_max_tokens is not None:
        # The completed-only reading at the run cap: rows run with a lower cap (re-run holes) and
        # censored rows are left out, which favours arms whose long responses never finished.
        grades = [
            g
            for g in grades
            if (g.get("max_tokens") or 0) >= min_max_tokens and not g.get("censored")
        ]
    caps = json.loads(args.caps.read_text()) if args.caps else {}
    if caps:
        # Only the registered prefix of each task's order enters the analysis.
        grades = [g for g in grades if g["rank"] is not None and g["rank"] < caps.get(g["task"], 0)]
    arms = list(plan["arms"])
    tasks = [t for t in plan["order"]["interleave"] if any(g["task"] == t for g in grades)]
    by = {
        (a, t): [g for g in grades if g["arm"] == a and g["task"] == t] for a in arms for t in tasks
    }
    result: dict[str, Any] = {
        "experiment": plan["experiment"],
        "status": "EXPLORATORY",
        "caps": caps,
        "arms": {},
        "accuracy": {},
        "by_source": {},
        "paired": {"g4": {}, "models": {}},
        "throughput": {},
    }
    for a in arms:
        arm = plan["arms"][a]
        result["arms"][a] = {
            "label": arm["label"],
            "mode": arm["mode"],
            "sampling": arm["sampling"],
            "max_tokens": {
                t: arm.get("max_tokens", {}).get(t, plan["tasks"][t]["max_tokens"]) for t in tasks
            },
            "fit": fit_tier(plan, a),
            "mac_decode_tok_s": MAC_DECODE[a][0],
            "mac_decode_basis": MAC_DECODE[a][1],
        }
    for a in arms:
        result["accuracy"][a] = {t: accuracy_block(by[(a, t)]) for t in tasks if by[(a, t)]}
        sources = sorted({g["source"] for g in grades if g["arm"] == a})
        result["by_source"][a] = {
            s: accuracy_block([g for g in grades if g["arm"] == a and g["source"] == s])
            for s in sources
        }
    for key, pairs in (("g4", PAIRS_G4), ("models", PAIRS_MODELS)):
        for x, y in pairs:
            entry = {}
            for t in tasks:
                if by[(x, t)] and by[(y, t)]:
                    a_vals, b_vals = paired_rows(by[(x, t)], by[(y, t)])
                    entry[t] = cluster_bootstrap_diff(a_vals, b_vals)
            # Equal-weight task mean of per-task differences, over the tasks both arms have.
            diffs = [entry[t]["diff"] for t in entry if entry[t]["diff"] is not None]
            entry["task_mean_diff"] = round(sum(diffs) / len(diffs), 2) if diffs else None
            result["paired"][key][f"{x} - {y}"] = entry
    if args.jobs:
        for arm_dir in sorted(p for p in args.jobs.iterdir() if p.is_dir()):
            rows = []
            for job_dir in sorted(p for p in arm_dir.iterdir() if p.is_dir()):
                tp = throughput(job_dir)
                if tp:
                    rows.append(tp)
            if rows:
                result["throughput"][arm_dir.name] = rows
    if args.gpu_hours and args.gpu_hours.exists():
        result["gpu_hours"] = json.loads(args.gpu_hours.read_text())
    return result


def tables(result: dict[str, Any]) -> str:
    out = ["# LM2 tables (EXPLORATORY)", ""]
    tasks = sorted(
        {t for a in result["accuracy"].values() for t in a}, key=["math", "code", "knowledge"].index
    )
    out += [
        "## Accuracy by arm and task (percent of samples correct; 95% item-bootstrap interval)",
        "",
    ]
    out += ["| Arm | " + " | ".join(tasks) + " |", "|---|" + "---|" * len(tasks)]
    for a, blocks in result["accuracy"].items():
        cells = []
        for t in tasks:
            b = blocks.get(t)
            cells.append(
                f"{b['accuracy']:.1f} [{b['ci95'][0]:.1f}, {b['ci95'][1]:.1f}] (n={b['items']}x{b['samples'] // max(1, b['items'])})"
                if b and b["accuracy"] is not None
                else "-"
            )
        out.append(f"| {a} | " + " | ".join(cells) + " |")
    for key, title in (
        ("g4", "Quantization cost inside V4 Flash 0731 (paired, points)"),
        ("models", "Between models (paired, points)"),
    ):
        out += [
            "",
            f"## {title}",
            "",
            "| Contrast | " + " | ".join(tasks) + " | task mean |",
            "|---|" + "---|" * (len(tasks) + 1),
        ]
        for name, entry in result["paired"][key].items():
            cells = []
            for t in tasks:
                e = entry.get(t)
                cells.append(
                    f"{e['diff']:+.1f} {fmt_ci(e['ci95'])} (items {e['n_items']}, {e['items_a_better']}/{e['items_b_better']})"
                    if e and e["diff"] is not None
                    else "-"
                )
            tm = entry.get("task_mean_diff")
            out.append(
                f"| {name} | " + " | ".join(cells) + f" | {tm:+.1f} |"
                if tm is not None
                else f"| {name} | " + " | ".join(cells) + " | - |"
            )
    out += [
        "",
        "## Output tokens and truncation",
        "",
        "| Arm | Task | Mean tokens | Median | Mean tokens (correct) | Tokens per correct | Truncated % | No answer % |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for a, blocks in result["accuracy"].items():
        for t, b in blocks.items():
            out.append(
                f"| {a} | {t} | {b['mean_output_tokens']} | {b['median_output_tokens']} | {b['mean_tokens_correct']} | {b['tokens_per_correct']} | {b['truncated_pct']} | {b['no_answer_pct']} |"
            )
    out += [
        "",
        "## Throughput on the H100s (llama.cpp b11669, layer split)",
        "",
        "| Arm | Job | GPUs | Slots | Load s | Aggregate tok/s (all slots busy) | tok/s per GPU | Generated tokens | Completed requests |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a, rows in result["throughput"].items():
        for r in rows:
            out.append(
                f"| {a} | {r['job_id']} | {r['gpus']} | {r['slots']} | {r['load_s']} | {r['aggregate_tok_s']} | {r['tok_s_per_gpu']} | {r['generated_tokens']} | {r['completed_requests']} |"
            )
    out += [
        "",
        "## Quality against resident memory on a 128 GB machine",
        "",
        "| Arm | File GB | Weights GiB | KV at 32K GiB | Resident at 32K GiB | Fit tier | Mac decode tok/s (basis) | "
        + " | ".join(f"{t} acc" for t in tasks)
        + " |",
        "|---|---:|---:|---:|---:|---|---|" + "---:|" * len(tasks),
    ]
    for a, info in result["arms"].items():
        f = info["fit"]
        accs = [f"{result['accuracy'].get(a, {}).get(t, {}).get('accuracy', '-')}" for t in tasks]
        mac = (
            f"{info['mac_decode_tok_s']} ({info['mac_decode_basis']})"
            if info["mac_decode_tok_s"]
            else info["mac_decode_basis"]
        )
        out.append(
            f"| {a} | {f['file_gb']} | {f['weights_gib']} | {f['kv_32k_gib']} | {f['resident_32k_gib']} | {f['tier_at_32k']} | {mac} | "
            + " | ".join(accs)
            + " |"
        )
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--plan", type=Path, default=PROJECT_ROOT / "experiments/lm2/lm2-resident-eval-v1.json"
    )
    parser.add_argument("--grades", type=Path, required=True)
    parser.add_argument("--grades-16k", type=Path, help="grades scored with no analysis cap")
    parser.add_argument("--caps", type=Path)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--gpu-hours", type=Path)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args(argv)
    result = analyze(args)
    md = tables(result)
    if args.grades_16k:
        secondary = analyze(args, args.grades_16k, 16384)
        result["secondary_16k_completed_only"] = {
            k: secondary[k] for k in ("accuracy", "paired", "by_source")
        }
        md += "\n# Secondary reading: completed responses at the 16,384 run cap only\n\n"
        md += "\n".join(tables(secondary).splitlines()[2:]).split("## Throughput")[0]
    args.out_json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    args.out_md.write_text(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
