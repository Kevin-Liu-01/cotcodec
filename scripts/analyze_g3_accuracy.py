#!/usr/bin/env python3
"""g3-state-precision-accuracy-v1 (EXPLORATORY): scoring and analysis. CPU only, on the host,
where the model outputs stay.

Subcommands:

* ``score --workers DIR... --output FILE``: per request, from each worker's ``records.json``,
  ``texts.jsonl.gz`` and ``tokens.npz``: length, how it ended, whether the thinking block
  closed, whether a final answer was given, the math checker's and G2b's string-match verdicts,
  the long-context containment check and the reply's SHA-256, and, against the fp32 arm's
  request with the same id, the first differing token position. Writes text-free JSONL (gzip).
* ``judge-input --scored FILE --workers DIR... --lme PATH --output FILE``: the judge job's study
  artifact (questions and every distinct long-context reply; stays on the host).
* ``analyze --scored FILE [--judge-labels FILE --judge-input FILE] --summaries DIR...
  --output-dir DIR``: per model x task x arm accuracy, paired differences against fp32 with
  question-cluster bootstrap intervals, length and truncation shifts, the equivalence reading,
  throughput; writes ``results.json`` and ``tables.md``.
* ``pilot --scored FILE --summaries DIR... --output FILE``: the sizing numbers from the pilot.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g3_state_precision as g3  # noqa: E402

MATH_CAP_REASON = "length"
CAPS = (8192, 16384, 24576, 32768)
TAIL_FROM = 28672  # 28K tokens


# --------------------------------------------------------------------------- loading


def load_worker(path: Path) -> dict[str, Any]:
    records = json.loads((path / "records.json").read_text(encoding="utf-8"))
    texts: dict[str, str] = {}
    with gzip.open(path / "texts.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            texts[row["request_id"]] = row["text"]
    tokens = np.load(path / "tokens.npz")
    offsets = tokens["offsets"]
    ids = tokens["token_ids"]
    token_map = {
        r["request_id"]: ids[offsets[i] : offsets[i + 1]] for i, r in enumerate(records["requests"])
    }
    return {"records": records, "texts": texts, "tokens": token_map}


def first_difference(a: np.ndarray, b: np.ndarray) -> int | None:
    """First index where two token sequences differ; None when they are identical."""

    n = min(len(a), len(b))
    if n:
        diff = np.nonzero(a[:n] != b[:n])[0]
        if diff.size:
            return int(diff[0])
    return None if len(a) == len(b) else n


def score_workers(paths: list[Path]) -> list[dict[str, Any]]:
    config = g3.load_config()
    prompts = g3.load_math_prompts(config)
    workers = [load_worker(p) for p in paths]
    reference: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    for w in workers:
        rec = w["records"]
        if rec["arm"] == "fp32":
            reference[(rec["phase"], rec["model_id"], rec["task"])] = w["tokens"]
    rows = []
    for w in workers:
        rec = w["records"]
        ref = reference.get((rec["phase"], rec["model_id"], rec["task"]))
        for r in rec["requests"]:
            text = w["texts"][r["request_id"]]
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
                "mean_logp": (r["sum_logp"] / r["completion_len"]) if r["completion_len"] else None,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
            if rec["task"] == "math":
                ans = g3.final_answer(text)
                reference_answer = prompts[r["question_index"]]["answer"]
                row |= {
                    "thinking_closed": ans["thinking_closed"],
                    "has_answer": ans["answer"] is not None,
                    "correct": int(g3.math_equiv(ans["answer"], reference_answer)),
                    "correct_anywhere": int(
                        g3.math_equiv(ans["answer_anywhere"], reference_answer)
                    ),
                    "correct_g2b": int(
                        g3.g2b_string_match(ans["answer_anywhere"], reference_answer)
                    ),
                    "answer_sha256": hashlib.sha256((ans["answer"] or "").encode()).hexdigest()
                    if ans["answer"] is not None
                    else None,
                }
            else:
                row |= {
                    "question_id": r["question_id"],
                    "reply_sha256": hashlib.sha256(g3.reply_text(text).encode()).hexdigest(),
                }
            if ref is not None and rec["arm"] != "fp32" and r["request_id"] in ref:
                diff = first_difference(w["tokens"][r["request_id"]], ref[r["request_id"]])
                row["identical_to_fp32"] = diff is None
                row["first_diff_vs_fp32"] = diff
            rows.append(row)
    return rows


def add_containment(rows: list[dict[str, Any]], paths: list[Path], lme: dict[str, Any]) -> None:
    texts: dict[tuple[str, str, str, str], str] = {}
    for p in paths:
        w = load_worker(p)
        rec = w["records"]
        if rec["task"] != "lme":
            continue
        for r in rec["requests"]:
            texts[(rec["phase"], rec["model_id"], rec["arm"], r["request_id"])] = w["texts"][
                r["request_id"]
            ]
    for row in rows:
        if row["task"] != "lme":
            continue
        text = texts[(row["phase"], row["model"], row["arm"], row["request_id"])]
        reply = g3.reply_text(text)
        row["contains_answer"] = g3.contains_answer(reply, lme[row["question_id"]]["answer"])
        row["says_idk"] = int("don't know" in reply.lower() or "do not know" in reply.lower())


# --------------------------------------------------------------------------- statistics


def cluster_matrix(
    rows: list[dict[str, Any]], key: str, arms: list[str]
) -> tuple[list[Any], np.ndarray, np.ndarray]:
    """Per question (cluster) and arm: the sum and count of ``key`` over that question's
    requests. Only questions present in every arm are kept."""

    sums: dict[Any, np.ndarray] = {}
    counts: dict[Any, np.ndarray] = {}
    for row in rows:
        value = row.get(key)
        if value is None or row["arm"] not in arms:
            continue
        q = row.get("question_id", row["question_index"])
        a = arms.index(row["arm"])
        sums.setdefault(q, np.zeros(len(arms)))[a] += float(value)
        counts.setdefault(q, np.zeros(len(arms)))[a] += 1
    keep = sorted(q for q in sums if np.all(counts[q] > 0))
    return keep, np.array([sums[q] for q in keep]), np.array([counts[q] for q in keep])


def bootstrap(per_q: np.ndarray, reps: int, seed: int) -> dict[str, Any]:
    """Mean over questions of per-question values (columns), with percentile intervals from
    resampling questions. ``per_q`` is questions x statistics."""

    rng = np.random.default_rng(seed)
    n = per_q.shape[0]
    point = per_q.mean(axis=0)
    idx = rng.integers(0, n, size=(reps, n))
    draws = per_q[idx].mean(axis=1)
    out = {"point": point.tolist(), "n_questions": int(n)}
    # 98.75%: a Bonferroni level for the four primary contrasts (2 models x fp16, bf16).
    levels = {"95": (2.5, 97.5), "90": (5.0, 95.0), "98_75": (0.625, 99.375)}
    for level, (lo, hi) in levels.items():
        out[f"ci{level}"] = [
            np.percentile(draws, lo, axis=0).tolist(),
            np.percentile(draws, hi, axis=0).tolist(),
        ]
    return out


def paired_summary(
    rows: list[dict[str, Any]],
    key: str,
    arms: list[str],
    reps: int,
    seed: int,
    margin: float | None,
) -> dict[str, Any]:
    """Per arm: the mean of ``key`` (per-question means averaged over questions); per non-fp32
    arm: the paired difference against fp32, its intervals, and the equivalence reading."""

    questions, sums, counts = cluster_matrix(rows, key, arms)
    if not questions:
        return {"n_questions": 0}
    means = sums / counts
    diffs = means[:, 1:] - means[:, :1]
    stats = bootstrap(np.concatenate([means, diffs], axis=1), reps, seed)
    out: dict[str, Any] = {"n_questions": len(questions), "requests": counts.sum(axis=0).tolist()}
    for i, arm in enumerate(arms):
        out[arm] = {"mean": stats["point"][i], "ci95": [stats["ci95"][0][i], stats["ci95"][1][i]]}
    for j, arm in enumerate(arms[1:], start=len(arms)):
        d = {
            "diff": stats["point"][j],
            "ci95": [stats["ci95"][0][j], stats["ci95"][1][j]],
            "ci90": [stats["ci90"][0][j], stats["ci90"][1][j]],
            "ci98_75": [stats["ci98_75"][0][j], stats["ci98_75"][1][j]],
        }
        if margin is not None:
            d["within_margin_90"] = bool(-margin < d["ci90"][0] and d["ci90"][1] < margin)
            d["within_margin_95"] = bool(-margin < d["ci95"][0] and d["ci95"][1] < margin)
        out[f"{arm}_minus_fp32"] = d
    return out


def per_question_variance(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """From k >= 2 samples per question: the unbiased per-question p(1-p) mean, via the
    pairwise disagreement rate (E[1{y_i != y_j}] = 2 p (1 - p))."""

    by_q: dict[Any, list[int]] = defaultdict(list)
    for row in rows:
        if row.get(key) is not None:
            by_q[row["question_index"]].append(int(row[key]))
    terms = []
    for values in by_q.values():
        k = len(values)
        if k < 2:
            continue
        ones = sum(values)
        pairs = k * (k - 1) / 2
        disagree = ones * (k - ones)
        terms.append(disagree / pairs / 2)
    return {"questions": len(terms), "mean_p_one_minus_p": float(np.mean(terms)) if terms else None}


def half_width(m: float, questions: int, samples: int, z: float = 1.96) -> float:
    """95% half-width of a paired accuracy difference with no arm effect and independent arms
    given the question: z * sqrt(2 m / (Q k))."""

    return z * math.sqrt(2.0 * m / (questions * samples))


def per_question_seed_matrix(
    rows: list[dict[str, Any]], key: str, arm: str, seeds: list[int]
) -> dict[Any, list[float]]:
    out: dict[Any, list[float]] = {}
    for row in rows:
        if row["arm"] != arm or row.get(key) is None or row["seed"] not in seeds:
            continue
        out.setdefault(row["question_index"], [float("nan")] * len(seeds))[
            seeds.index(row["seed"])
        ] = float(row[key])
    return {q: v for q, v in out.items() if not any(math.isnan(x) for x in v)}


def seed_heterogeneity(
    rows: list[dict[str, Any]], key: str, reps: int, seed: int
) -> dict[str, Any]:
    """Per 16-bit arm: (arm - fp32 at the first seed) - mean(arm - fp32 at the later seeds),
    paired by question, with a question bootstrap. The first seed was submitted first."""

    seeds = sorted({r["seed"] for r in rows})
    if len(seeds) < 2:
        return {}
    ref = per_question_seed_matrix(rows, key, "fp32", seeds)
    out: dict[str, Any] = {"seeds": seeds}
    for arm in ("fp16", "bf16"):
        m = per_question_seed_matrix(rows, key, arm, seeds)
        qs = sorted(set(ref) & set(m))
        d = np.array([m[q] for q in qs]) - np.array([ref[q] for q in qs])
        h = d[:, :1] - d[:, 1:].mean(axis=1, keepdims=True)
        b = bootstrap(h, reps, seed)
        out[arm] = {
            "n_questions": len(qs),
            "contrast": b["point"][0],
            "ci95": [b["ci95"][0][0], b["ci95"][1][0]],
        }
    return out


def pooled_over_models(
    rows: list[dict[str, Any]], key: str, models: list[str], reps: int, seed: int
) -> dict[str, Any]:
    """Per 16-bit arm: the paired difference against fp32 averaged over the models question by
    question (questions resampled jointly for all models)."""

    arms = list(g3.ARM_NAMES)
    per_model = {}
    for model in models:
        qs, sums, counts = cluster_matrix([r for r in rows if r["model"] == model], key, arms)
        means = sums / counts
        per_model[model] = {q: means[i, 1:] - means[i, 0] for i, q in enumerate(qs)}
    shared = sorted(set.intersection(*(set(v) for v in per_model.values())))
    pooled = np.array([np.mean([per_model[m][q] for m in models], axis=0) for q in shared])
    b = bootstrap(pooled, reps, seed)
    out: dict[str, Any] = {"models": models, "n_questions": len(shared)}
    for j, arm in enumerate(arms[1:]):
        out[f"{arm}_minus_fp32"] = {
            "diff": b["point"][j],
            "ci95": [b["ci95"][0][j], b["ci95"][1][j]],
            "ci98_75": [b["ci98_75"][0][j], b["ci98_75"][1][j]],
        }
    return out


def distinct_ngram_share(tokens: np.ndarray, n: int = 16, window: int = 8192) -> float | None:
    """Distinct n-grams over all n-grams in the last ``window`` tokens (1.0: no repeat)."""

    t = tokens[-window:]
    if len(t) < n:
        return None
    grams = {tuple(t[i : i + n].tolist()) for i in range(len(t) - n + 1)}
    return len(grams) / (len(t) - n + 1)


# --------------------------------------------------------------------------- tables


def worker_summaries(paths: list[Path]) -> list[dict[str, Any]]:
    out = []
    for path in paths:
        for summary in sorted(path.glob("*/summary.json")):
            data = json.loads(summary.read_text(encoding="utf-8"))
            if "task" not in data or "phase" not in data:
                continue
            p = data["phase"]
            out.append(
                {
                    "model": data["model"],
                    "arm": data["arm"],
                    "task": data["task"],
                    "phase": data.get("phase_name"),
                    "wall_s": p.get("wall_s"),
                    "output_tokens": p.get("output_tokens"),
                    "output_tok_per_s": p.get("output_tok_per_s"),
                    "prompt_tokens": p.get("prompt_tokens"),
                    "prompt_tok_per_s": p.get("prompt_tok_per_s"),
                    "requests": p.get("requests"),
                    "finished": p.get("finished"),
                    "mean_running": p.get("mean_running"),
                    "peak_running": p.get("peak_running"),
                    "preemptions": p.get("preemptions_delta"),
                    "peak_kv_usage": p.get("peak_kv_usage"),
                    "num_gpu_blocks": data["engine"].get("num_gpu_blocks"),
                    "block_size": data["engine"].get("block_size"),
                    "mamba_ssm_cache_dtype": data["engine"].get("mamba_ssm_cache_dtype"),
                    "init_s": data["engine"].get("init_s"),
                    "aborted": (p.get("info") or {}).get("aborted"),
                }
            )
    return out


def fmt_pct(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:.{digits}f}"


def fmt_ci(ci: list[float], scale: float = 100.0, digits: int = 1) -> str:
    return f"[{scale * ci[0]:+.{digits}f}, {scale * ci[1]:+.{digits}f}]"


def analyze(
    rows: list[dict[str, Any]],
    judge: dict[str, int] | None,
    throughput: list[dict[str, Any]],
    reps: int,
    seed: int,
    margin: float,
) -> dict[str, Any]:
    arms = list(g3.ARM_NAMES)
    results: dict[str, Any] = {
        "experiment_id": g3.EXPERIMENT_ID,
        "claim_level": "exploratory",
        "bootstrap": {"reps": reps, "seed": seed, "unit": "question"},
        "equivalence_margin": margin,
        "cells": {},
    }
    # The 4B's long-context arms ran as phase lme_extra (after the main run; the config).
    main = [
        r
        for r in rows
        if r["phase"] == "main" or (r["phase"] == "lme_extra" and r["task"] == "lme")
    ]
    if judge is not None:
        for r in main:
            if r["task"] == "lme":
                r["judge_correct"] = judge.get(r["reply_key"]) if "reply_key" in r else None
    for model in sorted({r["model"] for r in main}):
        for task in g3.TASKS:
            sub = [r for r in main if r["model"] == model and r["task"] == task]
            if not sub:
                continue
            cell: dict[str, Any] = {}
            for r in sub:
                r["cap_hit"] = int(r["finish_reason"] == MATH_CAP_REASON)
                r["time_cut"] = int(r["finish_reason"] == "cut_at_time_budget")
                r["ended_eos"] = int(r["finish_reason"] == "stop")
            keys = (
                [
                    "correct",
                    "correct_anywhere",
                    "correct_g2b",
                    "completion_len",
                    "cap_hit",
                    "time_cut",
                    "has_answer",
                ]
                if task == "math"
                else ["judge_correct", "contains_answer", "says_idk", "completion_len", "cap_hit"]
            )
            for key in keys:
                m = margin if key in ("correct", "judge_correct", "contains_answer") else None
                cell[key] = paired_summary(sub, key, arms, reps, seed, m)
            pairs = [r for r in sub if "identical_to_fp32" in r]
            cell["vs_fp32_tokens"] = {}
            for arm in arms[1:]:
                ps = [r for r in pairs if r["arm"] == arm]
                firsts = [
                    r["first_diff_vs_fp32"] for r in ps if r["first_diff_vs_fp32"] is not None
                ]
                cell["vs_fp32_tokens"][arm] = {
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
            if task == "math":
                ended = {}
                for arm in arms:
                    ar = [r for r in sub if r["arm"] == arm]
                    eos = [r for r in ar if r["ended_eos"]]
                    ended[arm] = {
                        "requests": len(ar),
                        "ended_eos": len(eos),
                        "accuracy_among_eos": (sum(r["correct"] for r in eos) / len(eos))
                        if eos
                        else None,
                        "median_len": float(np.median([r["completion_len"] for r in ar])),
                        "p90_len": float(np.percentile([r["completion_len"] for r in ar], 90)),
                        "wrong_answer_given": sum(
                            1 for r in ar if r["has_answer"] and not r["correct"]
                        ),
                        "capped_after_thinking_closed": sum(
                            1 for r in ar if r["cap_hit"] and r["thinking_closed"]
                        ),
                        # Rollouts still running at 28K tokens, and the share that then ended
                        # on their own before the 32,768 cap.
                        "running_at_28k": sum(1 for r in ar if r["completion_len"] > TAIL_FROM),
                        "ended_after_28k": sum(
                            1 for r in ar if r["completion_len"] > TAIL_FROM and r["ended_eos"]
                        ),
                    }
                cell["by_arm"] = ended
                # Accuracy under a shorter output cap: correct and ended within L tokens (the
                # tokens before L do not depend on the cap, so this is what a cap at L gives).
                cell["by_cap"] = {}
                for cap in CAPS:
                    for r in sub:
                        r["correct_cap"] = int(bool(r["correct"]) and r["completion_len"] <= cap)
                    cell["by_cap"][str(cap)] = paired_summary(
                        sub, "correct_cap", arms, reps, seed, None
                    )
                # By seed (submission order: seed 42 first; descriptive).
                cell["seed_heterogeneity"] = seed_heterogeneity(sub, "correct", reps, seed)
                cell["by_seed"] = {
                    str(s): paired_summary(
                        [r for r in sub if r["seed"] == s], "correct", arms, reps, seed, None
                    )
                    for s in sorted({r["seed"] for r in sub})
                }
            results["cells"][f"{model}/{task}"] = cell
    math_models = sorted({r["model"] for r in main if r["task"] == "math"})
    if len(math_models) > 1:
        results["pooled_math"] = pooled_over_models(
            [r for r in main if r["task"] == "math"], "correct", math_models, reps, seed
        )
    results["throughput"] = [t for t in throughput if t["phase"] in ("main", "lme_extra")]
    for t in results["throughput"]:
        if t["task"] != "math":
            continue
        rs = [
            r
            for r in main
            if r["model"] == t["model"] and r["arm"] == t["arm"] and r["task"] == "math"
        ]
        solved = sum(r["correct"] for r in rs)
        t["solved"] = solved
        t["solved_per_engine_s"] = solved / t["wall_s"] if t["wall_s"] else None
        t["tokens_per_solved"] = t["output_tokens"] / solved if solved else None
    return results


def tables_md(results: dict[str, Any]) -> str:
    arms = list(g3.ARM_NAMES)
    lines = [
        "# g3-state-precision-accuracy-v1 tables (EXPLORATORY)",
        "",
        "Accuracy in percent; differences in points (arm minus fp32), with 95% "
        "question-cluster bootstrap intervals "
        f"({results['bootstrap']['reps']} draws, seed {results['bootstrap']['seed']}). "
        f"Equivalence reading: is the 90% (TOST) or 95% interval inside "
        f"+-{100 * results['equivalence_margin']:.0f} points.",
        "",
    ]
    lines += [
        "## Accuracy",
        "",
        "| Model | Task | Score | Questions | fp32 | fp16 | bf16 | fp16 - fp32 [95%] | 90% | "
        "bf16 - fp32 [95%] | 90% |",
        "|---|---|---|---:|---:|---:|---:|---|---|---|---|",
    ]
    for name, cell in results["cells"].items():
        model, task = name.split("/")
        scores = (
            ["correct", "correct_g2b"] if task == "math" else ["judge_correct", "contains_answer"]
        )
        for key in scores:
            c = cell.get(key) or {}
            if not c.get("n_questions"):
                continue
            row = [model, task, key, str(c["n_questions"])]
            row += [fmt_pct(c[a]["mean"]) for a in arms]
            for a in arms[1:]:
                d = c[f"{a}_minus_fp32"]
                row += [f"{100 * d['diff']:+.1f} {fmt_ci(d['ci95'])}", fmt_ci(d["ci90"])]
            lines.append("| " + " | ".join(row) + " |")
    primary = [(n, c) for n, c in results["cells"].items() if n.endswith("/math")]
    if primary:
        lines += [
            "",
            "## Primary math contrasts (checker): 95%, Bonferroni 98.75% (4 contrasts) and 90%",
            "",
            "| Model | Contrast | Difference | 95% | 98.75% | 90% |",
            "|---|---|---:|---|---|---|",
        ]
        for name, cell in primary:
            for a in arms[1:]:
                d = cell["correct"][f"{a}_minus_fp32"]
                lines.append(
                    f"| {name.split('/')[0]} | {a} - fp32 | {100 * d['diff']:+.1f} | "
                    f"{fmt_ci(d['ci95'])} | {fmt_ci(d['ci98_75'])} | {fmt_ci(d['ci90'])} |"
                )
        pooled = results.get("pooled_math")
        if pooled:
            for a in arms[1:]:
                d = pooled[f"{a}_minus_fp32"]
                lines.append(
                    f"| pooled over models | {a} - fp32 | {100 * d['diff']:+.1f} | "
                    f"{fmt_ci(d['ci95'])} | {fmt_ci(d['ci98_75'])} | |"
                )
        lines += [
            "",
            "## Seed-order heterogeneity (math, checker): (arm - fp32 at seed 42) minus the mean "
            "at seeds 43-44, paired by question",
            "",
            "| Model | Arm | Contrast | 95% |",
            "|---|---|---:|---|",
        ]
        for name, cell in primary:
            het = cell.get("seed_heterogeneity") or {}
            for a in arms[1:]:
                if a in het:
                    lines.append(
                        f"| {name.split('/')[0]} | {a} | {100 * het[a]['contrast']:+.1f} | "
                        f"{fmt_ci(het[a]['ci95'])} |"
                    )
    lines += [
        "",
        "## Length and truncation",
        "",
        "| Model | Task | Measure | fp32 | fp16 | bf16 | fp16 - fp32 [95%] | bf16 - fp32 [95%] |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for name, cell in results["cells"].items():
        model, task = name.split("/")
        for key, scale, unit in (
            ("completion_len", 1.0, "tokens"),
            ("cap_hit", 100.0, "%"),
            ("time_cut", 100.0, "%"),
            ("has_answer", 100.0, "%"),
            ("says_idk", 100.0, "%"),
        ):
            c = cell.get(key) or {}
            if not c.get("n_questions"):
                continue
            digits = 0 if unit == "tokens" else 1
            row = [model, task, f"{key} ({unit})"]
            row += [f"{scale * c[a]['mean']:.{digits}f}" for a in arms]
            for a in arms[1:]:
                d = c[f"{a}_minus_fp32"]
                row.append(f"{scale * d['diff']:+.{digits}f} {fmt_ci(d['ci95'], scale, digits)}")
            lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "## Token-level agreement with the fp32 arm (same request id and seed)",
        "",
        "| Model | Task | Arm | Pairs | Identical | First difference, median (p10, p90) |",
        "|---|---|---|---:|---:|---|",
    ]
    for name, cell in results["cells"].items():
        model, task = name.split("/")
        for arm, v in cell["vs_fp32_tokens"].items():
            fd = (
                "n/a"
                if v["first_diff_median"] is None
                else (
                    f"{v['first_diff_median']:.0f} ({v['first_diff_p10_p90'][0]:.0f}, "
                    f"{v['first_diff_p10_p90'][1]:.0f})"
                )
            )
            lines.append(f"| {model} | {task} | {arm} | {v['pairs']} | {v['identical']} | {fd} |")
    if any("by_arm" in c for c in results["cells"].values()):
        lines += [
            "",
            "## Math rollouts by arm",
            "",
            "| Model | Arm | Rollouts | Ended (EOS) | Accuracy among EOS | Wrong answer given "
            "| Median length | p90 length | Running at 28K: ended by the cap |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for name, cell in results["cells"].items():
            if "by_arm" not in cell:
                continue
            for arm, v in cell["by_arm"].items():
                tail = (
                    f"{v['ended_after_28k']} of {v['running_at_28k']} "
                    f"({fmt_pct(v['ended_after_28k'] / v['running_at_28k'], 0)}%)"
                    if v.get("running_at_28k")
                    else "n/a"
                )
                lines.append(
                    f"| {name.split('/')[0]} | {arm} | {v['requests']} | {v['ended_eos']} | "
                    f"{fmt_pct(v['accuracy_among_eos'])} | {v.get('wrong_answer_given', 'n/a')} | "
                    f"{v['median_len']:.0f} | {v['p90_len']:.0f} | {tail} |"
                )
    if any("by_cap" in c for c in results["cells"].values()):
        lines += [
            "",
            "## Math accuracy under a shorter output cap (correct and ended within L tokens)",
            "",
            "| Model | Cap L | fp32 | fp16 | bf16 | fp16 - fp32 [95%] | bf16 - fp32 [95%] |",
            "|---|---:|---:|---:|---:|---|---|",
        ]
        for name, cell in results["cells"].items():
            for cap, c in cell.get("by_cap", {}).items():
                row = [name.split("/")[0], cap] + [fmt_pct(c[a]["mean"]) for a in arms]
                for a in arms[1:]:
                    d = c[f"{a}_minus_fp32"]
                    row.append(f"{100 * d['diff']:+.1f} {fmt_ci(d['ci95'])}")
                lines.append("| " + " | ".join(row) + " |")
        lines += [
            "",
            "## Math accuracy by seed (seed 42 submitted first; descriptive)",
            "",
            "| Model | Seed | fp32 | fp16 | bf16 | fp16 - fp32 [95%] | bf16 - fp32 [95%] |",
            "|---|---:|---:|---:|---:|---|---|",
        ]
        for name, cell in results["cells"].items():
            for sd, c in cell.get("by_seed", {}).items():
                row = [name.split("/")[0], sd] + [fmt_pct(c[a]["mean"]) for a in arms]
                for a in arms[1:]:
                    d = c[f"{a}_minus_fp32"]
                    row.append(f"{100 * d['diff']:+.1f} {fmt_ci(d['ci95'])}")
                lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "## Throughput (one engine per model x arm x task)",
        "",
        "| Model | Task | Arm | Requests | Wall (s) | Output tok/s | Prompt tok/s | Mean running | "
        "Preemptions | Peak KV | Blocks x size |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for t in sorted(
        results["throughput"], key=lambda t: (t["model"], t["task"], arms.index(t["arm"]))
    ):
        lines.append(
            f"| {t['model']} | {t['task']} | {t['arm']} | {t['requests']} | {t['wall_s']:.0f} | "
            f"{t['output_tok_per_s']:.0f} | {t['prompt_tok_per_s']:.0f} | "
            f"{(t['mean_running'] or 0):.0f} | {t['preemptions']:.0f} | "
            f"{100 * (t['peak_kv_usage'] or 0):.0f}% | {t['num_gpu_blocks']} x {t['block_size']} |"
        )
    solved = [t for t in results["throughput"] if t.get("solved") is not None]
    if solved:
        lines += [
            "",
            "## Math: solved problems per engine-second (fixed request set)",
            "",
            "| Model | Arm | Solved (of requests) | Wall (s) | Solved per 1,000 s | Output tokens "
            "per solved |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for t in sorted(solved, key=lambda t: (t["model"], arms.index(t["arm"]))):
            lines.append(
                f"| {t['model']} | {t['arm']} | {t['solved']} ({t['requests']}) | "
                f"{t['wall_s']:.0f} | {1000 * t['solved_per_engine_s']:.1f} | "
                f"{t['tokens_per_solved']:.0f} |"
            )
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- commands


def write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    """Deterministic gzip (mtime 0, no file name), so the file reproduces byte for byte."""

    with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        for row in rows:
            gz.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def lme_questions(path: Path) -> dict[str, Any]:
    config = g3.load_config()
    return {
        str(r["question_id"]): {
            "question_type": r["question_type"],
            "question": r["question"],
            "answer": r["answer"],
        }
        for r in g3.load_lme(path, config)
    }


def cmd_score(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.workers]
    rows = score_workers(paths)
    if any(r["task"] == "lme" for r in rows):
        add_containment(rows, paths, lme_questions(Path(args.lme)))
    write_jsonl_gz(Path(args.output), rows)
    print(json.dumps({"rows": len(rows), "output": args.output}))
    return 0


def cmd_judge_input(args: argparse.Namespace) -> int:
    rows = read_jsonl_gz(Path(args.scored))
    questions = lme_questions(Path(args.lme))
    replies = []
    for p in args.workers:
        w = load_worker(Path(p))
        rec = w["records"]
        if rec["task"] != "lme" or rec["phase"] not in ("main", "lme_extra"):
            continue
        for r in rec["requests"]:
            replies.append(
                {
                    "question_id": r["question_id"],
                    "reply": g3.reply_text(w["texts"][r["request_id"]]),
                }
            )
    used = sorted({r["question_id"] for r in replies})
    items = g3.judge_items(
        {q: questions[q] for q in used}, replies, g3.load_config()["judge"]["idk_response"]
    )
    artifact = {
        "experiment_id": g3.EXPERIMENT_ID,
        "questions": {q: questions[q] for q in used},
        "items": items,
        "scored_rows": len(rows),
    }
    Path(args.output).write_text(json.dumps(artifact, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"items": len(items), "questions": len(used), "replies": len(replies)}))
    return 0


def judge_map(labels_path: Path, input_path: Path) -> tuple[dict[str, int], dict[str, Any]]:
    """(question_id, SHA-256 of the stripped reply) -> judge label, and the validation check."""

    labels = {r["index"]: r for r in json.loads(labels_path.read_text())["labels"]}
    artifact = json.loads(input_path.read_text())
    out: dict[str, int] = {}
    validation = {"items": 0, "agree": 0, "malformed": 0}
    for item in artifact["items"]:
        lab = labels[item["index"]]
        validation["malformed"] += int(not lab["well_formed"])
        if "expected" in item:
            validation["items"] += 1
            validation["agree"] += int(lab["label"] == item["expected"])
            continue
        key = item["question_id"] + ":" + hashlib.sha256(item["response"].encode()).hexdigest()
        out[key] = int(lab["label"])
    return out, validation


def cmd_analyze(args: argparse.Namespace) -> int:
    config = g3.load_config()
    rows = read_jsonl_gz(Path(args.scored))
    judge = None
    validation = None
    if args.judge_labels:
        judge, validation = judge_map(Path(args.judge_labels), Path(args.judge_input))
        for r in rows:
            if r["task"] == "lme":
                r["reply_key"] = f"{r['question_id']}:{r['reply_sha256']}"
    throughput = worker_summaries([Path(p) for p in args.summaries])
    a = config["analysis"]
    results = analyze(
        rows,
        judge,
        throughput,
        int(a["bootstrap_reps"]),
        int(a["bootstrap_seed"]),
        float(a["equivalence_margin"]),
    )
    results["judge_validation"] = validation
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    (out / "tables.md").write_text(tables_md(results))
    print(json.dumps({"cells": list(results["cells"]), "output": str(out)}))
    return 0


def longer_shorter(a_rows: list[dict[str, Any]], b_rows: list[dict[str, Any]]) -> dict[str, int]:
    """Pairs where a ran longer / shorter than b (a rollout cut at the cap counts as longer;
    both cut is a tie)."""

    longer = shorter = tie = 0
    for a, b in zip(a_rows, b_rows, strict=True):
        ca, cb = a["finish_reason"] != "stop", b["finish_reason"] != "stop"
        if ca and cb:
            tie += 1
        elif ca or (not cb and a["completion_len"] > b["completion_len"]):
            longer += 1
        elif cb or a["completion_len"] < b["completion_len"]:
            shorter += 1
        else:
            tie += 1
    return {"longer": longer, "shorter": shorter, "ties": tie}


def divergence(a: dict[str, np.ndarray], b: dict[str, np.ndarray], ids: list[str]) -> dict:
    firsts = [first_difference(a[i], b[i]) for i in ids]
    found = [f for f in firsts if f is not None]
    return {
        "pairs": len(ids),
        "identical": sum(1 for f in firsts if f is None),
        "first_diff_median": float(np.median(found)) if found else None,
        "first_diff_p10_p90": [float(np.percentile(found, 10)), float(np.percentile(found, 90))]
        if found
        else None,
    }


def cmd_extras(args: argparse.Namespace) -> int:
    """Host only (reads token ids): the pilot's fp32 rollouts as a partial A/A for the main fp32
    arm on the shared request seeds; the long-context A/A; and a repetition measure (distinct
    16-gram share of the last 8K tokens) for capped math rollouts. Text-free output."""

    config = g3.load_config()
    a = config["analysis"]
    reps, seed = int(a["bootstrap_reps"]), int(a["bootstrap_seed"])
    rows = read_jsonl_gz(Path(args.scored))
    by = {(r["phase"], r["model"], r["arm"], r["task"], r["request_id"]): r for r in rows}
    tokens: dict[tuple[str, str, str, str], dict[str, np.ndarray]] = {}
    for path in args.workers:
        w = load_worker(Path(path))
        rec = w["records"]
        tokens[(rec["phase"], rec["model_id"], rec["arm"], rec["task"])] = w["tokens"]
    out: dict[str, Any] = {"aa_math": {}, "aa_lme": {}, "repetition": {}}
    arms = list(g3.ARM_NAMES)
    for model in sorted({k[1] for k in tokens}):
        pilot = tokens.get(("pilot", model, "fp32", "math"))
        if pilot is not None and ("main", model, "fp32", "math") in tokens:
            main = {arm: tokens[("main", model, arm, "math")] for arm in arms}
            ids = sorted(set(pilot) & set(main["fp32"]))

            def get(
                phase: str, arm: str, ids: list[str] = ids, model: str = model
            ) -> list[dict[str, Any]]:
                return [by[(phase, model, arm, "math", i)] for i in ids]

            aa_rows = [dict(r, arm="pilot_fp32") for r in get("pilot", "fp32")]
            aa_rows += [dict(r, arm="main_fp32") for r in get("main", "fp32")]
            entry: dict[str, Any] = {
                "shared_requests": len(ids),
                "questions": len({by[("main", model, "fp32", "math", i)]["question_index"]
                                  for i in ids}),
                "seeds": sorted({by[("main", model, "fp32", "math", i)]["seed"] for i in ids}),
            }  # fmt: skip
            for key in ("correct", "completion_len"):
                ps = paired_summary(aa_rows, key, ["pilot_fp32", "main_fp32"], reps, seed, None)
                entry[f"main_fp32_minus_pilot_fp32_{key}"] = ps.pop("main_fp32_minus_fp32")
                entry[f"means_{key}"] = {k: v["mean"] for k, v in ps.items() if isinstance(v, dict)}
            entry["main_fp32_vs_pilot_fp32_lengths"] = longer_shorter(
                get("main", "fp32"), get("pilot", "fp32")
            )
            entry["main_fp32_vs_pilot_fp32_tokens"] = divergence(main["fp32"], pilot, ids)
            same = [dict(r, arm=arm) for arm in arms for r in get("main", arm)]
            for key in ("correct", "completion_len"):
                ps = paired_summary(same, key, arms, reps, seed, None)
                entry[f"main_arms_on_shared_{key}"] = ps
            for arm in arms[1:]:
                entry[f"main_{arm}_vs_main_fp32_tokens"] = divergence(main[arm], main["fp32"], ids)
                entry[f"main_{arm}_vs_main_fp32_lengths"] = longer_shorter(
                    get("main", arm), get("main", "fp32")
                )
            out["aa_math"][model] = entry
        lme_pilot = tokens.get(("pilot", model, "fp32", "lme"))
        lme_ref = tokens.get(("main", model, "fp32", "lme")) or tokens.get(
            ("lme_extra", model, "fp32", "lme")
        )
        if lme_pilot is not None and lme_ref is not None:
            ids = sorted(set(lme_pilot) & set(lme_ref))
            out["aa_lme"][model] = divergence(lme_pilot, lme_ref, ids)
        for arm in arms:
            key = ("main", model, arm, "math")
            if key not in tokens:
                continue
            capped, late = [], []
            for rid, ids_ in tokens[key].items():
                r = by[("main", model, arm, "math", rid)]
                share = distinct_ngram_share(ids_)
                if share is None:
                    continue
                if r["finish_reason"] == MATH_CAP_REASON:
                    capped.append(share)
                elif r["finish_reason"] == "stop" and r["completion_len"] > 24576:
                    late.append(share)
            out["repetition"][f"{model}/{arm}"] = {
                "capped": len(capped),
                "capped_median_distinct_16gram_share": float(np.median(capped)) if capped else None,
                "capped_below_0_5": sum(1 for x in capped if x < 0.5),
                "ended_past_24k": len(late),
                "ended_past_24k_median": float(np.median(late)) if late else None,
            }
    Path(args.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"models": list(out["aa_math"]), "output": args.output}))
    return 0


def cmd_pilot(args: argparse.Namespace) -> int:
    rows = [r for r in read_jsonl_gz(Path(args.scored)) if r["phase"] == "pilot"]
    throughput = [
        t for t in worker_summaries([Path(p) for p in args.summaries]) if t["phase"] == "pilot"
    ]
    report: dict[str, Any] = {"models": {}, "throughput": throughput}
    for model in sorted({r["model"] for r in rows}):
        m = [r for r in rows if r["model"] == model and r["task"] == "math"]
        l_rows = [r for r in rows if r["model"] == model and r["task"] == "lme"]
        var = per_question_variance(m, "correct")
        lens = [r["completion_len"] for r in m]
        entry: dict[str, Any] = {
            "math": {
                "rollouts": len(m),
                "accuracy": float(np.mean([r["correct"] for r in m])) if m else None,
                "accuracy_g2b": float(np.mean([r["correct_g2b"] for r in m])) if m else None,
                "cap_hit": float(np.mean([r["finish_reason"] == MATH_CAP_REASON for r in m])),
                "time_cut": float(np.mean([r["finish_reason"] == "cut_at_time_budget" for r in m])),
                "len_mean": float(np.mean(lens)),
                "len_median": float(np.median(lens)),
                "len_p90": float(np.percentile(lens, 90)),
                "tokens": int(sum(lens)),
                "variance": var,
                "half_width_134": {
                    k: half_width(var["mean_p_one_minus_p"], 134, k) for k in (2, 3, 4, 5, 6, 8)
                }
                if var["mean_p_one_minus_p"]
                else None,
            },
            "lme": {
                "requests": len(l_rows),
                "contains_answer": float(np.mean([r["contains_answer"] for r in l_rows]))
                if l_rows
                else None,
                "says_idk": float(np.mean([r["says_idk"] for r in l_rows])) if l_rows else None,
                "len_mean": float(np.mean([r["completion_len"] for r in l_rows]))
                if l_rows
                else None,
                "prompt_len_mean": float(np.mean([r["prompt_len"] for r in l_rows]))
                if l_rows
                else None,
                "cap_hit": float(np.mean([r["finish_reason"] == "length" for r in l_rows]))
                if l_rows
                else None,
            },
        }
        report["models"][model] = entry
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("score", allow_abbrev=False)
    s.add_argument("--workers", nargs="+", required=True)
    s.add_argument("--lme", default=None)
    s.add_argument("--output", required=True)
    j = sub.add_parser("judge-input", allow_abbrev=False)
    j.add_argument("--scored", required=True)
    j.add_argument("--workers", nargs="+", required=True)
    j.add_argument("--lme", required=True)
    j.add_argument("--output", required=True)
    a = sub.add_parser("analyze", allow_abbrev=False)
    a.add_argument("--scored", required=True)
    a.add_argument("--judge-labels", default=None)
    a.add_argument("--judge-input", default=None)
    a.add_argument("--summaries", nargs="+", required=True)
    a.add_argument("--output-dir", required=True)
    x = sub.add_parser("extras", allow_abbrev=False)
    x.add_argument("--scored", required=True)
    x.add_argument("--workers", nargs="+", required=True)
    x.add_argument("--output", required=True)
    p = sub.add_parser("pilot", allow_abbrev=False)
    p.add_argument("--scored", required=True)
    p.add_argument("--summaries", nargs="+", required=True)
    p.add_argument("--output", required=True)
    args = parser.parse_args()
    handlers = {
        "score": cmd_score,
        "judge-input": cmd_judge_input,
        "analyze": cmd_analyze,
        "pilot": cmd_pilot,
        "extras": cmd_extras,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
