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
    outcomes_at_budget,
    paired_rows,
    task_mean_bootstrap,
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

    # A resumed job's directory also holds its predecessor's copied files; the job's own run is
    # the latest run id (run ids start with a UTC timestamp). A job cancelled by scancel has no
    # summary of its own (the container was stopped), so its metrics stand alone.
    metrics_all = sorted(job_dir.glob("metrics-*.jsonl"))
    if not metrics_all:
        return None
    run_id = metrics_all[-1].name[len("metrics-") : -len(".jsonl")]
    own = job_dir / f"summary-{run_id}.json"
    summary = json.loads(own.read_text()) if own.exists() else {}
    rows = [r for r in load_jsonl(metrics_all[-1]) if "busy_slots" in r]
    slots = summary.get("slots") or max((r["busy_slots"] for r in rows), default=None)
    gpus = summary.get("visible_gpus") or (
        len(rows[-1].get("gpu_used_mib") or {}) if rows else None
    )
    if len(rows) < 3:
        return None
    gen = [(r["t"], r["completed_tokens"] + r["inflight_decoded"], r["busy_slots"]) for r in rows]
    full = [g for g in gen if slots and g[2] >= 0.9 * slots]
    window = full if len(full) >= 3 else gen
    (t0, g0, _), (t1, g1, _) = window[0], window[-1]
    rate = (g1 - g0) / (t1 - t0) if t1 > t0 else None
    total_gen = gen[-1][1]
    return {
        "job_id": job_dir.name,
        "run_id": run_id,
        "phase": summary.get("phase") or "cancelled; no summary",
        "extra_server_args": summary.get("extra_server_args"),
        "max_tokens_override": summary.get("max_tokens_override"),
        "slots": slots,
        "gpus": gpus,
        "load_s": (summary.get("server") or {}).get("load_s"),
        "generation_s": summary.get("generation_s"),
        "steady_window_s": round(t1 - t0, 1),
        "steady_busy_fraction": round(len(full) / len(gen), 2),
        "aggregate_tok_s": round(rate, 1) if rate else None,
        "tok_s_per_gpu": round(rate / gpus, 1) if rate and gpus else None,
        "generated_tokens": total_gen,
        "completed_requests": (summary.get("counts") or {}).get("ok"),
        "peak_mib": summary.get("peak_mib"),
    }


def fmt_ci(ci: list[float] | None) -> str:
    return f"[{ci[0]:+.1f}, {ci[1]:+.1f}]" if ci else ""


def analyze(
    args: argparse.Namespace,
    grades_path: Path | None = None,
    min_max_tokens: int | None = None,
    caps_path: Path | None = None,
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
    caps_file = caps_path or args.caps
    caps = json.loads(caps_file.read_text()) if caps_file else {}
    per_arm = caps.get("per_arm", {})

    def cap_of(arm: str, task: str) -> int:
        return per_arm.get(arm, {}).get(task, caps.get(task, 0))

    if caps:
        # Only the evaluated prefix of each task's order enters the analysis: the plan's cut, or
        # an arm's complete prefix (all three seeds) when its run covered less (per_arm).
        grades = [
            g for g in grades if g["rank"] is not None and g["rank"] < cap_of(g["arm"], g["task"])
        ]
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
    if per_arm:
        # Every arm on the common prefix (the smallest cap per task), for a like-for-like table.
        common = {t: min(cap_of(a, t) for a in arms if cap_of(a, t) > 0) for t in tasks}
        result["common_prefix"] = common
        result["accuracy_common"] = {
            a: {
                t: accuracy_block([g for g in by[(a, t)] if g["rank"] < common[t]])
                for t in tasks
                if by[(a, t)]
            }
            for a in arms
        }
    for key, pairs in (("g4", PAIRS_G4), ("models", PAIRS_MODELS)):
        for x, y in pairs:
            entry = {}
            pairs_by_task = {}
            for t in tasks:
                if by[(x, t)] and by[(y, t)]:
                    a_vals, b_vals = paired_rows(by[(x, t)], by[(y, t)])
                    entry[t] = cluster_bootstrap_diff(a_vals, b_vals)
                    pairs_by_task[t] = (a_vals, b_vals)
            # Equal-weight task mean of per-task differences, over the tasks both arms have, with
            # a bootstrap that resamples items within every task in each draw.
            tm = task_mean_bootstrap(pairs_by_task)
            entry["task_mean_diff"] = tm["diff"]
            entry["task_mean"] = tm
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
                f"{b['accuracy']:.1f} [{b['ci95'][0]:.1f}, {b['ci95'][1]:.1f}] ({b['items']} items, {b['samples']} samples)"
                if b and b["accuracy"] is not None
                else "-"
            )
        out.append(f"| {a} | " + " | ".join(cells) + " |")
    if result.get("accuracy_common"):
        cp = result["common_prefix"]
        out += [
            "",
            "## Accuracy on the common prefix ("
            + ", ".join(f"{t} {cp[t]} items" for t in tasks)
            + ")",
            "",
        ]
        out += ["| Arm | " + " | ".join(tasks) + " |", "|---|" + "---|" * len(tasks)]
        for a, blocks in result["accuracy_common"].items():
            cells = []
            for t in tasks:
                b = blocks.get(t)
                cells.append(
                    f"{b['accuracy']:.1f} [{b['ci95'][0]:.1f}, {b['ci95'][1]:.1f}]"
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
            tmb = entry.get("task_mean") or {}
            out.append(
                f"| {name} | "
                + " | ".join(cells)
                + f" | {tmb['diff']:+.1f} {fmt_ci(tmb['ci95'])} |"
                if tmb.get("diff") is not None
                else f"| {name} | " + " | ".join(cells) + " | - |"
            )
        out += [
            "",
            "Minimum detectable difference (80% power, two-sided 5%, from the paired bootstrap SE), points: "
            + "; ".join(
                f"{name} "
                + ", ".join(
                    f"{t} {entry[t]['mdd80']}"
                    for t in tasks
                    if entry.get(t) and entry[t].get("mdd80") is not None
                )
                + (
                    f", task mean {entry['task_mean']['mdd80']}"
                    if entry.get("task_mean", {}).get("mdd80") is not None
                    else ""
                )
                for name, entry in result["paired"][key].items()
                if any(entry.get(t) and entry[t].get("mdd80") is not None for t in tasks)
            )
            + ".",
        ]
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
        "| Arm | Job (phase) | GPUs | Slots | Load s | Aggregate tok/s (all slots busy) | tok/s per GPU | Generated tokens | Completed requests |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a, rows in result["throughput"].items():
        for r in rows:
            out.append(
                f"| {a} | {r['job_id']} ({r['phase']}{', ' + ' '.join(r['extra_server_args']) if r.get('extra_server_args') else ''}) | {r['gpus']} | {r['slots']} | {r['load_s']} | {r['aggregate_tok_s']} | {r['tok_s_per_gpu']} | {r['generated_tokens']} | {r['completed_requests']} |"
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


SWEEP_ARMS = ("v4f-q8", "v4f-iq3", "v4f-q2", "gptoss120")


def budget_sweep(
    graded_path: Path, censored_dir: Path, budgets: list[int], cap: int
) -> dict[str, Any]:
    """Accuracy and paired contrasts at each budget ("stopped within B tokens"), for the arms
    with all 20 items per task; censored attempts count where B is at or below their tokens."""

    graded = [g for g in load_jsonl(graded_path) if g["rank"] < cap and g["arm"] in SWEEP_ARMS]
    censored = [
        c
        for p in sorted(censored_dir.glob("*.jsonl"))
        for c in load_jsonl(p)
        if c["rank"] < cap and c["arm"] in SWEEP_ARMS
    ]
    out: dict[str, Any] = {}
    for b in budgets:
        rows = outcomes_at_budget(graded, censored, b)
        by = {
            (a, t): [r for r in rows if r["arm"] == a and r["task"] == t]
            for a in SWEEP_ARMS
            for t in ("math", "code", "knowledge")
        }
        acc = {
            a: {
                t: round(100 * sum(r["correct"] for r in by[(a, t)]) / len(by[(a, t)]), 1)
                for t in ("math", "code", "knowledge")
                if by[(a, t)]
            }
            for a in SWEEP_ARMS
        }
        paired = {}
        for x, y in PAIRS_G4 + [p for p in PAIRS_MODELS if "qwen235-q3" not in p]:
            entry = {}
            for t in ("math", "code", "knowledge"):
                a_vals, b_vals = paired_rows(by[(x, t)], by[(y, t)])
                d = cluster_bootstrap_diff(a_vals, b_vals)
                entry[t] = {k: d[k] for k in ("diff", "ci95", "n_items")}
            paired[f"{x} - {y}"] = entry
        out[str(b)] = {"accuracy": acc, "paired": paired, "keys": len(rows)}
    return out


def code_breakdown(grades_path: Path, nocap_path: Path, cap: int) -> dict[str, Any]:
    """ds4 Q2 and UD-IQ3_XXS against Q8 on code at the primary budget: where the losses are, and
    whether the quantized files write longer code answers (per-item mean tokens, censored rows at
    their lower bound)."""

    rows = [g for g in load_jsonl(grades_path) if g["rank"] < cap and g["task"] == "code"]
    nocap = {g["key"]: g for g in load_jsonl(nocap_path) if g["rank"] < cap and g["task"] == "code"}
    by_arm = {
        a: {(r["item_id"], r["seed"]): r for r in rows if r["arm"] == a}
        for a in ("v4f-q8", "v4f-q2", "v4f-iq3")
    }
    q8 = by_arm["v4f-q8"]
    unfinished = lambda r: bool(r.get("censored") or r.get("over_analysis_cap"))  # noqa: E731
    out: dict[str, Any] = {}
    for arm in ("v4f-q2", "v4f-iq3"):
        other = by_arm[arm]
        keys = sorted(set(q8) & set(other))
        lost = [k for k in keys if q8[k]["correct"] and not other[k]["correct"]]
        won = [k for k in keys if other[k]["correct"] and not q8[k]["correct"]]
        unf = [k for k in keys if unfinished(other[k])]
        both = [k for k in keys if not unfinished(other[k]) and not unfinished(q8[k])]
        items = sorted({k[0] for k in keys})

        def mean_tokens(table: dict, item: str) -> float:
            vals = [
                int(table[(item, s)]["completion_tokens"] or 0)
                for s in (42, 43, 44)
                if (item, s) in table
            ]
            return sum(vals) / len(vals)

        longer = sum(1 for i in items if mean_tokens(other, i) > mean_tokens(q8, i))
        a_vals = [1.0 if other[k]["correct"] else 0.0 for k in both]
        b_vals = [1.0 if q8[k]["correct"] else 0.0 for k in both]
        by_item: dict[str, list[tuple[float, float]]] = {}
        for k, a, b in zip(both, a_vals, b_vals, strict=True):
            by_item.setdefault(k[0], []).append((a, b))
        pa = [sum(x for x, _ in v) / len(v) for _, v in sorted(by_item.items())]
        pb = [sum(y for _, y in v) / len(v) for _, v in sorted(by_item.items())]
        out[arm] = {
            "samples": len(keys),
            "q8_solved_arm_not": len(lost),
            "of_which_arm_finished_wrong": sum(1 for k in lost if not unfinished(other[k])),
            "of_which_arm_unfinished": sum(1 for k in lost if unfinished(other[k])),
            "arm_solved_q8_not": len(won),
            "arm_unfinished": len(unf),
            "q8_unfinished": sum(1 for k in keys if unfinished(q8[k])),
            "q8_solved_where_arm_unfinished": sum(1 for k in unf if q8[k]["correct"]),
            "both_finished_pairs": len(both),
            "both_finished_arm_solved": int(sum(a_vals)),
            "both_finished_q8_solved": int(sum(b_vals)),
            "both_finished_paired": cluster_bootstrap_diff(pa, pb),
            "items_longer_than_q8": longer,
            "items": len(items),
            "rerun_rows_kept_in_nocap": sum(
                1 for k in keys if f"{arm}|code|{k[0]}|{k[1]}" in nocap
            ),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--plan", type=Path, default=PROJECT_ROOT / "experiments/lm2/lm2-resident-eval-v1.json"
    )
    parser.add_argument("--grades", type=Path, required=True)
    parser.add_argument("--grades-16k", type=Path, help="grades scored with no analysis cap")
    parser.add_argument("--alt-grades", type=Path, help="a second budget reading")
    parser.add_argument("--alt-caps", type=Path)
    parser.add_argument("--alt-name", default="alternative reading")
    parser.add_argument("--caps", type=Path)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--gpu-hours", type=Path)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--sweep-censored", type=Path, help="directory of censored-row files")
    parser.add_argument("--sweep-budgets", type=int, nargs="+", default=[2048, 3072, 4096, 5120])
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
    if args.alt_grades:
        alt = analyze(args, args.alt_grades, None, args.alt_caps)
        result["alt_reading"] = {
            "name": args.alt_name,
            **{
                k: alt.get(k)
                for k in (
                    "caps",
                    "accuracy",
                    "accuracy_common",
                    "common_prefix",
                    "paired",
                    "by_source",
                )
            },
        }
        md += f"\n# {args.alt_name}\n\n"
        md += "\n".join(tables(alt).splitlines()[2:]).split("## Output tokens")[0]
    if args.sweep_censored:
        sweep = budget_sweep(args.grades_16k, args.sweep_censored, args.sweep_budgets, 20)
        result["budget_sweep"] = sweep
        md += "\n# Budget sweep (answered within B tokens; three V4 Flash files and gpt-oss)\n\n"
        md += "| Budget | " + " | ".join(f"{a} math/code/knowledge" for a in SWEEP_ARMS) + " |\n"
        md += "|---|" + "---|" * len(SWEEP_ARMS) + "\n"
        for b, v in sweep.items():
            md += (
                f"| {b} | "
                + " | ".join(
                    "/".join(f"{v['accuracy'][a][t]:.1f}" for t in ("math", "code", "knowledge"))
                    for a in SWEEP_ARMS
                )
                + " |\n"
            )
        md += "\n| Budget | Contrast | Math | Code | Knowledge |\n|---|---|---|---|---|\n"
        for b, v in sweep.items():
            for name, e in v["paired"].items():
                md += (
                    f"| {b} | {name} | "
                    + " | ".join(
                        f"{e[t]['diff']:+.1f} {fmt_ci(e[t]['ci95'])}"
                        for t in ("math", "code", "knowledge")
                    )
                    + " |\n"
                )
        breakdown = code_breakdown(args.grades, args.grades_16k, 20)
        result["code_breakdown_vs_q8"] = breakdown
        md += "\n# Code against Q8 at the 5,120 budget\n\n| Arm | Q8 solved, arm not | of which finished, wrong | of which unfinished | Arm solved, Q8 not | Arm unfinished | Q8 solved where arm unfinished | Both finished: pairs, arm / Q8 solved, paired diff | Items longer than Q8 |\n|---|---:|---:|---:|---:|---:|---:|---|---:|\n"
        for a, v in breakdown.items():
            d = v["both_finished_paired"]
            md += f"| {a} | {v['q8_solved_arm_not']} | {v['of_which_arm_finished_wrong']} | {v['of_which_arm_unfinished']} | {v['arm_solved_q8_not']} | {v['arm_unfinished']} of {v['samples']} | {v['q8_solved_where_arm_unfinished']} | {v['both_finished_pairs']}, {v['both_finished_arm_solved']} / {v['both_finished_q8_solved']}, {d['diff']:+.1f} {fmt_ci(d['ci95'])} | {v['items_longer_than_q8']} of {v['items']} |\n"
    args.out_json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    args.out_md.write_text(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
