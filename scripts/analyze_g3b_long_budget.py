#!/usr/bin/env python3
"""g3b-long-budget-v1 (EXPLORATORY): scoring and analysis. CPU only, on the host, where the model
outputs stay (``analyze`` itself needs only the text-free scored file, the worker summaries and
G3's committed per-request data).

Subcommands:

* ``score --workers DIR... --output FILE``: per request, from each worker's ``records.json``,
  ``texts.jsonl.gz`` and ``tokens.npz``: length, how it ended, G3's checker v2 verdict at the
  run's own budget (81,920), the same rollout scored as if capped at each rescoring cap (its first
  ``cap`` tokens, decoded by the worker), and the first differing token against the fp32 arm's
  request with the same id. Writes text-free JSONL (gzip, deterministic).
* ``analyze --scored FILE --summaries DIR... --g3-data FILE --output-dir DIR``: per arm accuracy
  at 81,920 and rescored at 32,768, paired differences against fp32 with question-cluster
  bootstrap intervals, lengths and truncation, rollouts by arm, the seed-order breakdown, G3's
  numbers on the same questions and the cross-run differences, preemptions and the fit, tokens
  per solved problem; writes ``results.json`` and ``tables.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g3_state_precision as g3  # noqa: E402
from harness import g3b_long_budget as g3b  # noqa: E402


def _g3_analysis() -> Any:
    spec = importlib.util.spec_from_file_location(
        "analyze_g3_accuracy", PROJECT_ROOT / "scripts" / "analyze_g3_accuracy.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


a3 = _g3_analysis()

#: Output caps for the descriptive accuracy curve (G3's rule: correct and ended within L tokens).
CURVE_CAPS = (16384, 32768, 49152, 65536, 81920)
SEEDS = [42, 43, 44]


# --------------------------------------------------------------------------- scoring


def load_worker(path: Path) -> dict[str, Any]:
    import gzip

    records = json.loads((path / "records.json").read_text(encoding="utf-8"))
    texts: dict[str, dict[str, Any]] = {}
    with gzip.open(path / "texts.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            texts[row["request_id"]] = row
    tokens = np.load(path / "tokens.npz")
    offsets, ids = tokens["offsets"], tokens["token_ids"]
    token_map = {
        r["request_id"]: ids[offsets[i] : offsets[i + 1]] for i, r in enumerate(records["requests"])
    }
    return {"records": records, "texts": texts, "tokens": token_map}


def score_workers(paths: list[Path]) -> list[dict[str, Any]]:
    config = g3b.load_config()
    view = g3b.g3_view(config)
    prompts = g3.load_math_prompts(view)
    caps = [int(c) for c in config["tasks"][g3b.TASK]["rescore_caps"]]
    workers = [load_worker(p) for p in paths]
    reference = {
        w["records"]["phase"]: w["tokens"]
        for w in workers
        if w["records"]["arm"] == g3b.REFERENCE_ARM
    }
    # The A/A engine compares with the main run's fp32 arm.
    rows = []
    for w in workers:
        rec = w["records"]
        ref = reference.get(rec["phase"]) or reference.get("main")
        for r in rec["requests"]:
            entry = w["texts"][r["request_id"]]
            reference_answer = prompts[r["question_index"]]["answer"]
            full = g3b.score_text(entry["text"], reference_answer)
            row: dict[str, Any] = {
                "phase": rec["phase"],
                "model": rec["model_id"],
                "arm": rec["arm"],
                "task": rec["task"],
                "request_id": r["request_id"],
                "question_index": r["question_index"],
                "seed": r["seed"],
                "prompt_len": r["prompt_len"],
                "completion_len": r["completion_len"],
                "finish_reason": r["finish_reason"],
                "first_token_s": r.get("first_token_s"),
                "finished_s": r.get("finished_s"),
                "mean_logp": (r["sum_logp"] / r["completion_len"]) if r["completion_len"] else None,
                "text_sha256": hashlib.sha256(entry["text"].encode("utf-8")).hexdigest(),
                **full,
            }
            for cap in caps:
                key = f"text_at_{cap}"
                if r["completion_len"] > cap and key not in entry:
                    raise g3b.G3bConfigError(f"{r['request_id']}: no {key} for a long rollout")
                truncated = g3b.score_text(entry[key], reference_answer) if key in entry else None
                scored = g3b.score_at_cap(
                    r["completion_len"], r["finish_reason"], full, truncated, cap
                )
                row |= {f"c{cap}_{k}": v for k, v in scored.items()}
            if ref is not None and rec["arm"] != g3b.REFERENCE_ARM and r["request_id"] in ref:
                diff = a3.first_difference(w["tokens"][r["request_id"]], ref[r["request_id"]])
                row["identical_to_fp32"] = diff is None
                row["first_diff_vs_fp32"] = diff
            rows.append(row)
    return rows


# --------------------------------------------------------------------------- statistics


def complete_pairs(rows: list[dict[str, Any]], key: str, arms: list[str]) -> list[dict[str, Any]]:
    """The rows of the (question, seed) pairs that have a value of ``key`` in every arm. A rollout
    cut by the time budget has no value where its outcome is unknown, and its pair is dropped
    from every arm, so the comparison stays paired."""

    have: dict[tuple[int, int], set[str]] = {}
    for r in rows:
        if r["arm"] in arms and r.get(key) is not None:
            have.setdefault((r["question_index"], r["seed"]), set()).add(r["arm"])
    keep = {k for k, v in have.items() if v >= set(arms)}
    return [r for r in rows if r["arm"] in arms and (r["question_index"], r["seed"]) in keep]


def paired(
    rows: list[dict[str, Any]], key: str, arms: list[str], reps: int, seed: int
) -> dict[str, Any]:
    """G3's paired summary on the complete pairs, with the number of pairs dropped."""

    sub = complete_pairs(rows, key, arms)
    out = a3.paired_summary(sub, key, arms, reps, seed, None)
    pairs = {(r["question_index"], r["seed"]) for r in rows if r["arm"] in arms}
    out["pairs"] = len({(r["question_index"], r["seed"]) for r in sub})
    out["pairs_dropped"] = len(pairs) - out["pairs"]
    return out


def seed_heterogeneity(
    rows: list[dict[str, Any]], key: str, arm: str, ref: str, reps: int, seed: int
) -> dict[str, Any]:
    """(arm - ref at seed 42) minus the mean of (arm - ref) at seeds 43-44, paired by question,
    with a question bootstrap. Seed 42 was submitted (and admitted) first."""

    rows = complete_pairs(rows, key, [ref, arm])
    seeds = sorted({r["seed"] for r in rows})
    if len(seeds) < 2:
        return {}
    r_ref = a3.per_question_seed_matrix(rows, key, ref, seeds)
    r_arm = a3.per_question_seed_matrix(rows, key, arm, seeds)
    qs = sorted(set(r_ref) & set(r_arm))
    if not qs:
        return {}
    d = np.array([r_arm[q] for q in qs]) - np.array([r_ref[q] for q in qs])
    h = d[:, :1] - d[:, 1:].mean(axis=1, keepdims=True)
    b = a3.bootstrap(h, reps, seed)
    return {
        "seeds": seeds,
        "n_questions": len(qs),
        "contrast": b["point"][0],
        "ci95": [b["ci95"][0][0], b["ci95"][1][0]],
    }


def gap_change(
    new_rows: list[dict[str, Any]],
    new_key: str,
    old_rows: list[dict[str, Any]],
    old_key: str,
    arm: str,
    reps: int,
    seed: int,
) -> dict[str, Any]:
    """Per question: (arm - fp32 in the new run) minus (arm - fp32 in the old run), with a
    question bootstrap; also each arm's new-minus-old difference."""

    def per_q(rows: list[dict[str, Any]], key: str) -> dict[int, np.ndarray]:
        qs, sums, counts = a3.cluster_matrix(rows, key, [g3b.REFERENCE_ARM, arm])
        means = sums / counts
        return {q: means[i] for i, q in enumerate(qs)}

    new_rows = complete_pairs(new_rows, new_key, [g3b.REFERENCE_ARM, arm])
    new, old = per_q(new_rows, new_key), per_q(old_rows, old_key)
    qs = sorted(set(new) & set(old))
    if not qs:
        return {"n_questions": 0}
    n = np.array([new[q] for q in qs])
    o = np.array([old[q] for q in qs])
    stats = np.column_stack(
        [n[:, 0] - o[:, 0], n[:, 1] - o[:, 1], (n[:, 1] - n[:, 0]) - (o[:, 1] - o[:, 0])]
    )
    b = a3.bootstrap(stats, reps, seed)
    names = [f"{g3b.REFERENCE_ARM}_new_minus_old", f"{arm}_new_minus_old", "gap_new_minus_gap_old"]
    out: dict[str, Any] = {"n_questions": len(qs)}
    for j, name in enumerate(names):
        out[name] = {"diff": b["point"][j], "ci95": [b["ci95"][0][j], b["ci95"][1][j]]}
    return out


def median_first_token(rows: list[dict[str, Any]], arm: str, seed: int) -> float | None:
    """Median time to a request's first token (s from the phase start): its admission."""

    values = [
        r["first_token_s"]
        for r in rows
        if r["arm"] == arm and r["seed"] == seed and r["first_token_s"] is not None
    ]
    return float(np.median(values)) if values else None


def by_arm(rows: list[dict[str, Any]], arms: list[str], cap: int) -> dict[str, Any]:
    out = {}
    for arm in arms:
        ar = [r for r in rows if r["arm"] == arm]
        if not ar:
            continue
        lens = np.array([r["completion_len"] for r in ar])
        eos = [r for r in ar if r["finish_reason"] == "stop"]
        long_ = [r for r in ar if r["completion_len"] > cap]
        out[arm] = {
            "requests": len(ar),
            "ended_eos": len(eos),
            "accuracy_among_eos": (sum(r["correct"] for r in eos) / len(eos)) if eos else None,
            "wrong_answer_given": sum(1 for r in ar if r["has_answer"] and not r["correct"]),
            "no_answer": sum(1 for r in ar if not r["has_answer"]),
            "cap_hit": sum(1 for r in ar if r["finish_reason"] == "length"),
            "time_cut": sum(1 for r in ar if r["finish_reason"] == g3b.TIME_CUT),
            "capped_after_thinking_closed": sum(
                1 for r in ar if r["finish_reason"] == "length" and r["thinking_closed"]
            ),
            "mean_len": float(lens.mean()),
            "median_len": float(np.median(lens)),
            "p90_len": float(np.percentile(lens, 90)),
            "max_len": int(lens.max()),
            "output_tokens": int(lens.sum()),
            "tokens_within_cap": int(np.minimum(lens, cap).sum()),
            # Rollouts past the rescoring cap: how many then ended on their own, and how many of
            # those were correct.
            "past_cap": len(long_),
            "past_cap_ended": sum(1 for r in long_ if r["finish_reason"] == "stop"),
            "past_cap_correct": sum(r["correct"] for r in long_),
            "solved": int(sum(r["correct"] for r in ar)),
            "solved_at_cap": int(sum(r[f"c{cap}_correct"] or 0 for r in ar)),
            "undetermined_at_cap": sum(1 for r in ar if r[f"c{cap}_correct"] is None),
            "time_cut_rollouts": [
                {"request_id": r["request_id"], "tokens_at_cut": r["completion_len"]}
                for r in ar
                if r["finish_reason"] == g3b.TIME_CUT
            ],
        }
    return out


# --------------------------------------------------------------------------- analysis


def g3_rows_on(g3_rows: list[dict[str, Any]], questions: list[int]) -> list[dict[str, Any]]:
    qs = set(questions)
    out = []
    for r in g3_rows:
        if (
            r["phase"] == "main"
            and r["model"] == g3b.MODEL_ID
            and r["task"] == "math"
            and r["question_index"] in qs
        ):
            out.append(dict(r, cap_hit=int(r["finish_reason"] == "length")))
    return out


def overlaps(engine: dict[str, Any], window: dict[str, str]) -> bool:
    start, end = engine.get("phase_start_utc"), engine.get("phase_end_utc")
    return bool(start and end and start < window["end_utc"] and window["start_utc"] < end)


def analyze(
    rows: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    g3_rows: list[dict[str, Any]],
    reps: int,
    seed: int,
    cap: int = g3b.G3_CAP,
    timing_windows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """``timing_windows``: external events ({start_utc, end_utc, note}) that can distort wall-clock
    and throughput figures; an engine whose generation phase overlaps one is flagged."""

    config = g3b.load_config()
    questions = [int(q) for q in config["questions"]["indices"]]
    main = [dict(r) for r in rows if r["phase"] in ("main", "aa")]
    arms = [a for a in g3b.ARM_DTYPES if any(r["arm"] == a for r in main)]
    if arms[:1] != [g3b.REFERENCE_ARM]:
        raise g3b.G3bConfigError("the analysis needs the fp32 arm")
    for r in main:
        cut = r["finish_reason"] == g3b.TIME_CUT
        r["time_cut"] = int(cut)
        r["ended"] = int(r["finish_reason"] == "stop")
        # At 81,920 a time-cut rollout's outcome is unknown: as run it counts as unsolved (its text
        # has no answer); "complete" drops its pair from both arms; "upper" counts it as solved.
        r["correct_complete"] = None if cut else r["correct"]
        r["correct_upper"] = 1 if cut else r["correct"]
        r["cap_hit"] = None if cut else int(r["finish_reason"] == "length")
        r["has_answer_i"] = None if cut else int(bool(r["has_answer"]))
        r["len_complete"] = None if cut else int(r["completion_len"])
        c = r[f"c{cap}_correct"]
        r[f"c{cap}_correct_lower"] = 0 if c is None else c
        r[f"c{cap}_correct_upper"] = 1 if c is None else c
        h = r[f"c{cap}_has_answer"]
        r[f"c{cap}_has_answer_i"] = None if h is None else int(bool(h))
        r[f"len_capped_{cap}"] = r[f"c{cap}_len"]
    results: dict[str, Any] = {
        "experiment_id": g3b.EXPERIMENT_ID,
        "claim_level": "exploratory",
        "bootstrap": {"reps": reps, "seed": seed, "unit": "question"},
        "questions": {
            "n": len(questions),
            "indices_sha256": config["questions"]["indices_sha256"],
            "in_data": sorted({r["question_index"] for r in main}) == questions,
        },
        "arms": arms,
        "rescore_cap": cap,
    }
    keys = {
        "correct": "accuracy at 81,920, as run (a time-cut rollout counts as unsolved)",
        "correct_complete": "accuracy at 81,920, pairs with no time-cut rollout",
        "correct_upper": "accuracy at 81,920, time-cut rollouts counted as solved (bound)",
        f"c{cap}_correct": f"accuracy rescored at {cap:,}, pairs with a known outcome",
        f"c{cap}_correct_lower": f"accuracy rescored at {cap:,}, unknown counted unsolved",
        f"c{cap}_correct_upper": f"accuracy rescored at {cap:,}, unknown counted solved",
        "len_complete": "length (tokens), complete pairs",
        "cap_hit": "reached 81,920",
        f"c{cap}_cap_hit": f"past {cap:,}",
        "has_answer_i": "final answer given at 81,920",
        f"c{cap}_has_answer_i": f"final answer given within {cap:,}",
        "time_cut": "cut by the time budget",
        f"len_capped_{cap}": f"length capped at {cap:,}",
    }
    results["paired"] = {key: paired(main, key, arms, reps, seed) for key in keys}
    results["paired_labels"] = keys
    results["by_arm"] = by_arm(main, arms, cap)
    # Descriptive accuracy curve (G3's rule: correct and ended within L tokens).
    curve = {}
    for c in CURVE_CAPS:
        for r in main:
            unknown = r["finish_reason"] == g3b.TIME_CUT and r["completion_len"] < c
            r["correct_curve"] = (
                None if unknown else int(bool(r["correct"]) and r["completion_len"] <= c)
            )
        curve[str(c)] = paired(main, "correct_curve", arms, reps, seed)
    results["curve_ended_within"] = curve
    # Seed order: seed 42 submitted and admitted first.
    results["by_seed"] = {
        key: {
            str(s): paired([r for r in main if r["seed"] == s], key, arms, reps, seed)
            for s in SEEDS
        }
        for key in (
            "correct",
            "correct_complete",
            f"c{cap}_correct",
            "len_complete",
            f"c{cap}_cap_hit",
        )
    }
    results["seed_heterogeneity"] = {
        key: seed_heterogeneity(main, key, "bf16", g3b.REFERENCE_ARM, reps, seed)
        for key in ("correct_complete", f"c{cap}_correct")
    }
    results["admission_by_seed"] = {
        arm: {str(s): median_first_token(main, arm, s) for s in SEEDS} for arm in arms
    }
    # G3 on the same questions (selected on G3's own outcomes: biased, see the README).
    old = g3_rows_on(g3_rows, questions)
    old_arms = ["fp32", "fp16", "bf16"]
    results["g3_same_questions"] = {
        "correct": a3.paired_summary(old, "correct", old_arms, reps, seed, None),
        "cap_hit": a3.paired_summary(old, "cap_hit", old_arms, reps, seed, None),
        "completion_len": a3.paired_summary(old, "completion_len", old_arms, reps, seed, None),
        "by_seed": {
            str(s): a3.paired_summary(
                [r for r in old if r["seed"] == s], "correct", old_arms, reps, seed, None
            )
            for s in SEEDS
        },
        "seed_heterogeneity": seed_heterogeneity(old, "correct", "bf16", "fp32", reps, seed),
    }
    results["g3b_vs_g3"] = {
        f"at_{cap}": gap_change(main, f"c{cap}_correct", old, "correct", "bf16", reps, seed),
        "at_81920": gap_change(main, "correct_complete", old, "correct", "bf16", reps, seed),
        f"cap_hit_at_{cap}": gap_change(
            main, f"c{cap}_cap_hit", old, "cap_hit", "bf16", reps, seed
        ),
    }
    # Token-level agreement with fp32 (same request id and seed).
    tok = {}
    for arm in arms[1:]:
        ps = [r for r in main if r["arm"] == arm and "identical_to_fp32" in r]
        firsts = [r["first_diff_vs_fp32"] for r in ps if r["first_diff_vs_fp32"] is not None]
        tok[arm] = {
            "pairs": len(ps),
            "identical": sum(1 for r in ps if r["identical_to_fp32"]),
            "first_diff_median": float(np.median(firsts)) if firsts else None,
            "first_diff_p10_p90": [
                float(np.percentile(firsts, 10)),
                float(np.percentile(firsts, 90)),
            ]
            if firsts
            else None,
        }
    results["vs_fp32_tokens"] = tok
    # Engines: preemptions, fit, throughput, solved per engine-second, tokens per solved.
    engines = []
    for s in summaries:
        if s["phase"] not in ("main", "aa"):
            continue
        ba = results["by_arm"].get(s["arm"], {})
        solved, solved_cap = ba.get("solved"), ba.get("solved_at_cap")
        affected = [w["note"] for w in timing_windows or [] if overlaps(s, w)]
        engines.append(
            s
            | {
                "timing_affected_by": affected,
                "solved": solved,
                "solved_at_cap": solved_cap,
                "solved_per_1000_engine_s": 1000 * solved / s["wall_s"] if s["wall_s"] else None,
                "tokens_per_solved": s["output_tokens"] / solved if solved else None,
                "tokens_within_cap_per_solved_at_cap": ba["tokens_within_cap"] / solved_cap
                if solved_cap
                else None,
            }
        )
    results["engines"] = engines
    results["timing_windows"] = timing_windows or []
    results["preemptions_total"] = sum((e.get("preemptions") or 0) for e in engines)
    return results


def phase_start_utc(progress: Path) -> str | None:
    if not progress.is_file():
        return None
    for line in progress.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "phase-start":
            return str(event["utc"])
    return None


def worker_summaries(paths: list[Path]) -> list[dict[str, Any]]:
    out = []
    for path in paths:
        for summary in sorted(path.glob("*/summary.json")):
            data = json.loads(summary.read_text(encoding="utf-8"))
            if "task" not in data or "phase" not in data:
                continue
            p, e = data["phase"], data["engine"]
            start = phase_start_utc(summary.parent / "worker-progress.jsonl")
            end = None
            if start and p.get("wall_s") is not None:
                t0 = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
                end = (t0 + timedelta(seconds=float(p["wall_s"]))).strftime("%Y-%m-%dT%H:%M:%SZ")
            out.append(
                {
                    "arm": data["arm"],
                    "phase": data.get("phase_name"),
                    "wall_s": p.get("wall_s"),
                    "output_tokens": p.get("output_tokens"),
                    "output_tok_per_s": p.get("output_tok_per_s"),
                    "requests": p.get("requests"),
                    "finished": p.get("finished"),
                    "mean_running": p.get("mean_running"),
                    "peak_running": p.get("peak_running"),
                    "mean_waiting": p.get("mean_waiting"),
                    "preemptions": p.get("preemptions_delta"),
                    "peak_kv_usage": p.get("peak_kv_usage"),
                    "aborted": (p.get("info") or {}).get("aborted"),
                    "stopped_by": (p.get("info") or {}).get("stopped_by"),
                    "num_gpu_blocks": e.get("num_gpu_blocks"),
                    "block_size": e.get("block_size"),
                    "mamba_ssm_cache_dtype": e.get("mamba_ssm_cache_dtype"),
                    "max_num_seqs": e.get("max_num_seqs"),
                    "max_model_len": e.get("max_model_len"),
                    "fit": e.get("fit"),
                    "init_s": e.get("init_s"),
                    "phase_start_utc": start,
                    "phase_end_utc": end,
                }
            )
    return out


# --------------------------------------------------------------------------- tables


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}"


def _diff(d: dict[str, Any], scale: float = 100.0, digits: int = 1) -> str:
    return f"{scale * d['diff']:+.{digits}f} {a3.fmt_ci(d['ci95'], scale, digits)}"


def tables_md(results: dict[str, Any]) -> str:
    arms = results["arms"]
    cap = results["rescore_cap"]
    others = arms[1:]
    lines = [
        "# g3b-long-budget-v1 tables (EXPLORATORY)",
        "",
        f"Qwen3.5-4B, {results['questions']['n']} MATH-500 level-5 questions (those with a capped "
        "rollout in G3) x seeds 42-44. Percent of rollouts; differences in points (arm minus "
        "fp32, same question and request seed), with 95% question-cluster bootstrap intervals "
        f"({results['bootstrap']['reps']} draws, seed {results['bootstrap']['seed']}).",
        "",
        "## Accuracy",
        "",
        "| Budget and treatment of time-cut rollouts | Pairs | "
        + " | ".join(arms)
        + " | "
        + " | ".join(f"{a} - fp32" for a in others)
        + " |",
        "|---|---:|" + "---:|" * len(arms) + "---|" * len(others),
    ]
    for key in (
        "correct",
        "correct_complete",
        "correct_upper",
        f"c{cap}_correct",
        f"c{cap}_correct_lower",
        f"c{cap}_correct_upper",
    ):
        c = results["paired"][key]
        row = [results["paired_labels"][key], str(c["pairs"])] + [_pct(c[a]["mean"]) for a in arms]
        row += [_diff(c[f"{a}_minus_fp32"]) for a in others]
        lines.append("| " + " | ".join(row) + " |")
    g = results["g3_same_questions"]["correct"]
    lines += [
        "",
        "## G3 on the same questions (32,768 cap, heavy preemption; selected on these outcomes)",
        "",
        "| Run | fp32 | fp16 | bf16 | bf16 - fp32 |",
        "|---|---:|---:|---:|---|",
        f"| G3 | {_pct(g['fp32']['mean'])} | {_pct(g['fp16']['mean'])} | {_pct(g['bf16']['mean'])} "
        f"| {_diff(g['bf16_minus_fp32'])} |",
        "",
        "## G3b minus G3, per question (same questions and request seeds)",
        "",
        "| Measure | fp32 | bf16 | bf16 gap (G3b) minus bf16 gap (G3) |",
        "|---|---|---|---|",
    ]
    for key, label in (
        (f"at_{cap}", f"accuracy, G3b rescored at {cap:,}"),
        ("at_81920", "accuracy, G3b at 81,920"),
        (f"cap_hit_at_{cap}", f"past {cap:,} tokens"),
    ):
        v = results["g3b_vs_g3"][key]
        if v.get("n_questions"):
            lines.append(
                f"| {label} | {_diff(v['fp32_new_minus_old'])} | {_diff(v['bf16_new_minus_old'])} "
                f"| {_diff(v['gap_new_minus_gap_old'])} |"
            )
    lines += [
        "",
        "## Lengths and truncation",
        "",
        "| Measure | "
        + " | ".join(arms)
        + " | "
        + " | ".join(f"{a} - fp32" for a in others)
        + " |",
        "|---|" + "---:|" * len(arms) + "---|" * len(others),
    ]
    for key, scale, digits in (
        ("len_complete", 1.0, 0),
        ("cap_hit", 100.0, 1),
        (f"c{cap}_cap_hit", 100.0, 1),
        ("has_answer_i", 100.0, 1),
        (f"c{cap}_has_answer_i", 100.0, 1),
        ("time_cut", 100.0, 1),
    ):
        c = results["paired"][key]
        label = results["paired_labels"][key] + ("" if scale == 1.0 else " (%)")
        label += f", {c['pairs']} pairs"
        row = [label] + [f"{scale * c[a]['mean']:.{digits}f}" for a in arms]
        row += [_diff(c[f"{a}_minus_fp32"], scale, digits) for a in others]
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "## Rollouts by arm",
        "",
        "| Arm | Rollouts | Ended (EOS) | Accuracy among EOS | Wrong answer given | No answer "
        "| Reached 81,920 | Time cut | Median | p90 | Max | Past 32,768: ended / correct |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for arm, v in results["by_arm"].items():
        lines.append(
            f"| {arm} | {v['requests']} | {v['ended_eos']} | {_pct(v['accuracy_among_eos'])} | "
            f"{v['wrong_answer_given']} | {v['no_answer']} | {v['cap_hit']} | {v['time_cut']} | "
            f"{v['median_len']:.0f} | {v['p90_len']:.0f} | {v['max_len']} | "
            f"{v['past_cap_ended']} / {v['past_cap_correct']} of {v['past_cap']} |"
        )
    lines += [
        "",
        "## Accuracy by output cap (correct and ended within L tokens; descriptive)",
        "",
        "| Cap L | " + " | ".join(arms) + " | " + " | ".join(f"{a} - fp32" for a in others) + " |",
        "|---:|" + "---:|" * len(arms) + "---|" * len(others),
    ]
    for c, v in results["curve_ended_within"].items():
        row = [f"{int(c):,}"] + [_pct(v[a]["mean"]) for a in arms]
        row += [_diff(v[f"{a}_minus_fp32"]) for a in others]
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "## Seed order (seed 42 submitted and admitted first; descriptive)",
        "",
        "| Budget | Seed | fp32 | bf16 | bf16 - fp32 | G3: fp32 | G3: bf16 | G3: bf16 - fp32 |",
        "|---|---:|---:|---:|---|---:|---:|---|",
    ]
    gs = results["g3_same_questions"]["by_seed"]
    for key, label in (
        ("correct_complete", "81,920 (complete pairs)"),
        (f"c{cap}_correct", f"{cap:,}"),
    ):
        for s, v in results["by_seed"][key].items():
            o = gs[s]
            lines.append(
                f"| {label} | {s} | {_pct(v['fp32']['mean'])} | {_pct(v['bf16']['mean'])} | "
                f"{_diff(v['bf16_minus_fp32'])} | {_pct(o['fp32']['mean'])} | "
                f"{_pct(o['bf16']['mean'])} | {_diff(o['bf16_minus_fp32'])} |"
            )
    lines += [
        "",
        "Seed-order contrast: (bf16 - fp32 at seed 42) minus its mean at seeds 43-44, paired by "
        "question.",
        "",
        "| Run | Budget | Contrast [95%] |",
        "|---|---|---|",
    ]
    for key, label in (
        ("correct_complete", "81,920 (complete pairs)"),
        (f"c{cap}_correct", f"{cap:,}"),
    ):
        h = results["seed_heterogeneity"][key]
        if h:
            lines.append(
                f"| G3b | {label} | {100 * h['contrast']:+.1f} {a3.fmt_ci(h['ci95'])} "
                f"({h['n_questions']} questions) |"
            )
    h = results["g3_same_questions"]["seed_heterogeneity"]
    if h:
        lines.append(
            f"| G3 | 32,768 | {100 * h['contrast']:+.1f} {a3.fmt_ci(h['ci95'])} "
            f"({h['n_questions']} questions) |"
        )
    lines += [
        "",
        "## Engines (one per arm; single runs)",
        "",
        "| Arm | Requests | Wall (s) | Output tokens | Output tok/s | Mean running | Peak running "
        "| Preemptions | Peak KV | Blocks x size | Fit (max sequences at max_model_len) "
        "| Time-cut | Solved (as run) | Solved per 1,000 s | Tokens per solved | Tokens per solved "
        "at 32,768 | Wall-clock figures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for e in results["engines"]:
        fit = e.get("fit") or {}
        hit = e.get("timing_affected_by") or []
        timing = "affected: " + "; ".join(hit) if hit else "clean"
        lines.append(
            f"| {e['arm']} | {e['requests']} | {e['wall_s']:.0f} | {e['output_tokens']:,} | "
            f"{e['output_tok_per_s']:.0f} | {(e['mean_running'] or 0):.1f} | "
            f"{(e['peak_running'] or 0):.0f} | {(e['preemptions'] or 0):.0f} | "
            f"{100 * (e['peak_kv_usage'] or 0):.0f}% | {e['num_gpu_blocks']} x {e['block_size']} | "
            f"{fit.get('max_sequences_that_fit', 'n/a')} >= {e['max_num_seqs']} | "
            f"{e['requests'] - e['finished']} | "
            f"{e['solved']} | {(e['solved_per_1000_engine_s'] or 0):.1f} | "
            f"{(e['tokens_per_solved'] or 0):,.0f} | "
            f"{(e['tokens_within_cap_per_solved_at_cap'] or 0):,.0f} | "
            f"{timing} |"
        )
    cuts = [(arm, v["time_cut_rollouts"]) for arm, v in results["by_arm"].items()]
    if any(c for _, c in cuts):
        lines += [
            "",
            "## Rollouts cut by the job's time budget (outcome unknown at 81,920)",
            "",
            "| Arm | Request | Tokens at the cut |",
            "|---|---|---:|",
        ]
        for arm, c in cuts:
            for x in c:
                lines.append(f"| {arm} | {x['request_id']} | {x['tokens_at_cut']:,} |")
    lines += [
        "",
        "## Token-level agreement with the fp32 arm (same request id and seed)",
        "",
        "| Arm | Pairs | Identical | First difference, median (p10, p90) |",
        "|---|---:|---:|---|",
    ]
    for arm, v in results["vs_fp32_tokens"].items():
        fd = (
            "n/a"
            if v["first_diff_median"] is None
            else f"{v['first_diff_median']:.0f} ({v['first_diff_p10_p90'][0]:.0f}, "
            f"{v['first_diff_p10_p90'][1]:.0f})"
        )
        lines.append(f"| {arm} | {v['pairs']} | {v['identical']} | {fd} |")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- commands


def cmd_score(args: argparse.Namespace) -> int:
    rows = score_workers([Path(p) for p in args.workers])
    a3.write_jsonl_gz(Path(args.output), rows)
    print(json.dumps({"rows": len(rows), "output": args.output}))
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    config = g3b.load_config()
    rows = a3.read_jsonl_gz(Path(args.scored))
    g3_path = Path(args.g3_data)
    if g3.sha256_file(g3_path) != config["questions"]["source_sha256"]:
        raise g3b.G3bConfigError("G3's per-request data differs from the pinned digest")
    g3_rows = g3b.read_g3_rows(g3_path)
    if g3b.capped_questions(g3_rows) != [int(q) for q in config["questions"]["indices"]]:
        raise g3b.G3bConfigError("the pinned questions do not follow from G3's data")
    summaries = worker_summaries([Path(p) for p in args.summaries])
    windows = json.loads(Path(args.timing_windows).read_text()) if args.timing_windows else None
    a = config["analysis"]
    results = analyze(
        rows,
        summaries,
        g3_rows,
        int(a["bootstrap_reps"]),
        int(a["bootstrap_seed"]),
        timing_windows=windows,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    (out / "tables.md").write_text(tables_md(results))
    print(json.dumps({"arms": results["arms"], "output": str(out)}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("score", allow_abbrev=False)
    s.add_argument("--workers", nargs="+", required=True)
    s.add_argument("--output", required=True)
    a = sub.add_parser("analyze", allow_abbrev=False)
    a.add_argument("--scored", required=True)
    a.add_argument("--summaries", nargs="+", required=True)
    a.add_argument(
        "--g3-data",
        default=str(
            PROJECT_ROOT
            / "program/evidence/2026-10-16/g3-state-precision-accuracy/data/per-request.jsonl.gz"
        ),
    )
    a.add_argument("--timing-windows", default=None)
    a.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    return {"score": cmd_score, "analyze": cmd_analyze}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
