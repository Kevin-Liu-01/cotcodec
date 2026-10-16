#!/usr/bin/env python3
"""LM2 scoring on the host CPU: model responses in, text-free grade rows out.

Steps (each a subcommand; the model text never leaves the host):

- ``prepare``: read every ``responses-*.jsonl`` under the given run directories, keep one ``ok``
  row per key (the earliest), take the final answer (the content after the reasoning), score math
  (G3 checker v2) and multiple choice, and write:
  - ``grades-pre.jsonl``: text-free rows (key, arm, task, item, seed, finish reason, token counts,
    answer flags, correctness; code rows have ``correct: null`` until their verdict is merged);
  - ``code-input.jsonl`` (host only, holds program text): the extracted program and the tests of
    every code row, the sandbox grader's input.
- ``finalize``: merge the sandbox's text-free verdicts into the code rows and write
  ``grades.jsonl``.

A reasoning arm's answer counts only if its reasoning closed: llama-server separated it into
``reasoning_content``, or the content holds a ``</think>`` (the text after the last one is the
final answer). A thinking arm that was cut while reasoning has no answer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.lm2_resident_eval import (  # noqa: E402
    extract_code,
    load_items,
    load_plan,
    math_answer,
    mc_answer,
    score_knowledge,
    score_math,
)

THINK_END = "</think>"
HARMONY_FINAL = "<|channel|>final<|message|>"


def final_text(row: dict[str, Any], thinking: bool) -> tuple[str | None, str]:
    """(final answer text or None, how it was found)."""

    content = row.get("content") or ""
    reasoning = row.get("reasoning_content") or ""
    if not thinking:
        return content, "content"
    if reasoning:
        if not content.strip():
            return None, "reasoning_only"
        return content, "separated"
    if THINK_END in content:
        return content.rsplit(THINK_END, 1)[1], "think_tag"
    if HARMONY_FINAL in content:
        return content.rsplit(HARMONY_FINAL, 1)[1], "harmony_tag"
    return None, "unclosed"


def load_responses(run_dirs: list[Path]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for directory in run_dirs:
        for path in sorted(directory.rglob("responses-*.jsonl")):
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if row.get("status") != "ok":
                        continue
                    key = row["key"]
                    if key not in rows or row.get("started_at", "") < rows[key].get(
                        "started_at", ""
                    ):
                        rows[key] = row
    return rows


def prepare(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    data = args.data
    items: dict[str, dict[str, Any]] = {}
    for task in plan["tasks"]:
        entry = plan["datasets"][task]
        for item in load_items(data / entry["file"], entry["sha256"]):
            items[item["id"]] = item
    responses = load_responses(args.runs)
    args.out.mkdir(parents=True, exist_ok=True)
    n_code = 0
    with (
        (args.out / "grades-pre.jsonl").open("w", encoding="utf-8") as grades,
        (args.out / "code-input.jsonl").open("w", encoding="utf-8") as code_in,
    ):
        for key in sorted(responses):
            row = responses[key]
            arm = plan["arms"][row["arm"]]
            item = items[row["item_id"]]
            text, how = final_text(row, bool(arm.get("thinking")))
            tokens = int(row.get("completion_tokens") or 0)
            # "Answered within the budget": a response longer than the cap, or one stopped by an
            # output cap equal to it, did not finish within the budget.
            over_cap = args.analysis_cap is not None and (
                tokens > args.analysis_cap
                or (tokens >= args.analysis_cap and row.get("finish_reason") == "length")
            )
            if over_cap:
                # The analysis cap (8,192): a response longer than the cap is scored as cut there.
                # Its text within the first 8,192 tokens is not recovered, so it counts as having no
                # answer (conservative for that arm).
                text, how = None, "over_analysis_cap"
            grade: dict[str, Any] = {
                "key": key,
                "arm": row["arm"],
                "task": row["task"],
                "item_id": row["item_id"],
                "source": item.get("source"),
                "seed": row["seed"],
                "rank": row.get("rank"),
                "job_id": row.get("job_id"),
                "finish_reason": "length" if over_cap else row.get("finish_reason"),
                "finish_reason_raw": row.get("finish_reason"),
                "max_tokens": row.get("max_tokens") or 16384,
                "over_analysis_cap": over_cap,
                "completion_tokens": row.get("completion_tokens"),
                "prompt_tokens": row.get("prompt_tokens"),
                "wall_s": row.get("wall_s"),
                "reasoning_chars": len(row.get("reasoning_content") or ""),
                "content_chars": len(row.get("content") or ""),
                "final_found": how,
                "has_final": text is not None,
            }
            if row["task"] == "math":
                scored = score_math(text, item["answer"])
                answer = math_answer(text)
                grade.update(scored, answer_chars=len(answer) if answer is not None else None)
            elif row["task"] == "knowledge":
                grade.update(score_knowledge(text, item["answer_letter"]))
                grade["answer_letter_given"] = mc_answer(text)
            else:
                program = extract_code(text or "")
                grade.update(has_answer=bool(program.strip()), correct=None)
                grade["code_chars"] = len(program)
                code_in.write(
                    json.dumps(
                        {
                            "key": key,
                            "item_id": row["item_id"],
                            "testtype": item["testtype"],
                            "func_name": item.get("func_name"),
                            "code": program,
                            "tests": [
                                {"input": t["input"], "output": t["output"]} for t in item["tests"]
                            ],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                n_code += 1
            grades.write(json.dumps(grade, sort_keys=True) + "\n")
    print(json.dumps({"responses": len(responses), "code_rows": n_code}))
    return 0


def censor(args: argparse.Namespace) -> int:
    """Rows for requests that were still running when a job's budget ended.

    In continuous batching every running request gains one token per decode step. When all the
    holes of a top-up job start together, each one still running at the end has generated at least
    ``--min-tokens`` (from the job's metrics) without stopping. If that is at or above the
    analysis cap, the request did not finish within the budget, which is its outcome under the
    cap (``correct: false``, ``censored: true``). Keys come from the plan's order and caps minus
    the keys any of ``--runs`` completed.
    """

    from harness.lm2_resident_eval import request_key, request_order, select_items

    plan = load_plan(args.plan)
    if args.min_tokens < args.analysis_cap:
        raise SystemExit("censored requests must have passed the analysis cap")
    items = {}
    for task in plan["order"]["interleave"]:
        entry = plan["datasets"][task]
        rows = load_items(args.data / entry["file"], entry["sha256"])
        items[task] = select_items(task, plan["tasks"][task], rows)
    caps = dict(spec.split("=") for spec in args.cap)
    order = request_order(
        items,
        plan["order"]["interleave"],
        plan["seeds"],
        plan["order"]["rng_seed"],
        {k: int(v) for k, v in caps.items()},
    )
    done = load_responses(args.runs)
    out = []
    for task, item, rank, seed in order:
        key = request_key(args.arm, task, item["id"], seed)
        if key in done:
            continue
        out.append(
            {
                "key": key,
                "arm": args.arm,
                "task": task,
                "item_id": item["id"],
                "source": item.get("source"),
                "seed": seed,
                "rank": rank,
                "job_id": args.job,
                "finish_reason": "length",
                "finish_reason_raw": None,
                "completion_tokens": args.min_tokens,
                "censored": True,
                "over_analysis_cap": True,
                "has_final": False,
                "has_answer": False,
                "correct": False,
                "final_found": "unfinished_at_abort",
                "max_tokens": args.max_tokens,
            }
        )
    with args.out.open("w", encoding="utf-8") as handle:
        for row in out:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"censored_rows": len(out)}))
    return 0


def finalize(args: argparse.Namespace) -> int:
    verdicts: dict[str, dict[str, Any]] = {}
    for path in args.verdicts:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                verdicts[row["key"]] = row
    missing = 0
    out_rows = []
    for line in args.pre.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        grade = json.loads(line)
        if grade["task"] == "code":
            verdict = verdicts.get(grade["key"])
            if verdict is None:
                missing += 1
                continue
            grade["correct"] = bool(verdict["passed"])
            grade["code_failure"] = verdict.get("failure")
            grade["tests"] = verdict.get("tests")
            grade["passed_tests"] = verdict.get("passed_tests")
            grade["grade_s"] = verdict.get("elapsed_s")
        out_rows.append(grade)
    keys = {g["key"] for g in out_rows}
    for path in args.censored:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["key"] not in keys:
                    out_rows.append(row)
                    keys.add(row["key"])
    with args.out.open("w", encoding="utf-8") as handle:
        for grade in out_rows:
            handle.write(json.dumps(grade, sort_keys=True) + "\n")
    print(json.dumps({"rows": len(out_rows), "code_without_verdict": missing}))
    return 0 if missing == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument(
        "--plan", type=Path, default=PROJECT_ROOT / "experiments/lm2/lm2-resident-eval-v1.json"
    )
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--runs", type=Path, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--analysis-cap", type=int, default=5120)
    f = sub.add_parser("finalize")
    f.add_argument("--pre", type=Path, required=True)
    f.add_argument("--verdicts", type=Path, nargs="+", required=True)
    f.add_argument("--out", type=Path, required=True)
    f.add_argument("--censored", type=Path, nargs="*", default=[])
    c = sub.add_parser("censor")
    c.add_argument(
        "--plan", type=Path, default=PROJECT_ROOT / "experiments/lm2/lm2-resident-eval-v1.json"
    )
    c.add_argument("--data", type=Path, required=True)
    c.add_argument("--runs", type=Path, nargs="+", required=True)
    c.add_argument("--arm", required=True)
    c.add_argument("--job", required=True)
    c.add_argument("--cap", action="append", required=True)
    c.add_argument("--min-tokens", type=int, required=True)
    c.add_argument("--max-tokens", type=int, required=True)
    c.add_argument("--analysis-cap", type=int, default=5120)
    c.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "censor":
        return censor(args)
    return prepare(args) if args.command == "prepare" else finalize(args)


if __name__ == "__main__":
    sys.exit(main())
