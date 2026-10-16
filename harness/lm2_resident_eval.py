"""LM2 (D129, EXPLORATORY): resident models for a 128 GB machine on verifiable tasks.

Pure logic shared by the in-container driver (``scripts/run_lm2_eval.py``), the CPU scorer
(``scripts/lm2_score.py``), the code sandbox grader (``scripts/lm2_code_grader.py``) and the
analysis (``scripts/analyze_lm2.py``):

- the plan (``experiments/lm2/lm2-resident-eval-v1.json``): arms, tasks, sampling, digests;
- the item order: within each task, items sorted by the SHA-256 of their id and permuted with
  ``numpy``-free ``random.Random(42)``; tasks interleaved one item at a time; the seeds of an item
  adjacent. Every prefix of the order is a balanced design, so a budget cut is a prefix cut;
- prompts, request payloads and per-request seeds;
- answer extraction and scoring (math through G3's checker v2, ``math_equiv``; code through the
  sandbox's verdicts; multiple choice by the last ``Answer: X`` line);
- paired item-level comparisons with question-cluster bootstrap intervals.

No model output text leaves the host: the scorer writes text-free grade rows.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from harness.g3_state_precision import evaluate, last_boxed, math_equiv, normalize_math

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = PROJECT_ROOT / "experiments" / "lm2" / "lm2-resident-eval-v1.json"
EXPERIMENT_ID = "lm2-resident-eval-v1"
TASKS = ("math", "code", "knowledge")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ARM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

MATH_SUFFIX = "Please reason step by step, and put your final answer within \\boxed{}."
# LiveCodeBench's generic chat prompt (lcb_runner/prompts/code_generation.py), with its system
# message placed first in the single user turn so every template receives the same messages.
LCB_SYSTEM = (
    "You are an expert Python programmer. You will be given a question (problem specification) "
    "and will generate a correct Python program that matches the specification and passes all "
    "tests."
)
LCB_WITH_STARTER = (
    "You will use the following starter code to write the solution to the problem and enclose "
    "your code within delimiters."
)
LCB_WITHOUT_STARTER = (
    "Read the inputs from stdin solve the problem and write the answer to stdout (do not "
    "directly test on the sample inputs). Enclose your code within delimiters as follows. "
    "Ensure that when the python program runs, it reads the inputs, runs the algorithm and "
    "writes output to STDOUT."
)
MC_LETTERS = "ABCDEFGHIJ"
MC_HEADER = (
    "Answer the following multiple choice question. There is only one correct answer. The last "
    "line of your response should be in the format 'Answer: $LETTER' (without quotes), where "
    "LETTER is one of {letters}."
)
MC_ANSWER_RE = re.compile(r"Answer\s*[:：]\s*\**\s*\(?([A-J])\)?\b")

# Sampler fields llama-server would otherwise default (temperature 0.8, top-k 40, min-p 0.05,
# ...); every request sets all of them.
SAMPLER_KEYS = ("temperature", "top_p", "top_k", "min_p")
NEUTRAL_SAMPLERS = {
    "repeat_penalty": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "dry_multiplier": 0.0,
    "xtc_probability": 0.0,
    "typical_p": 1.0,
    "top_n_sigma": -1.0,
    "mirostat": 0,
}


class LM2Error(ValueError):
    """The plan, an input file or an argument violates the contract."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))[:16]


# --- Plan ----------------------------------------------------------------------------------


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LM2Error(message)


def validate_plan(plan: Any) -> dict[str, Any]:
    _require(isinstance(plan, dict) and plan.get("schema_version") == 1, "plan schema_version 1")
    _require(plan.get("experiment") == EXPERIMENT_ID, f"plan experiment must be {EXPERIMENT_ID}")
    _require(plan.get("status") == "EXPLORATORY", "plan status must be EXPLORATORY")
    seeds = plan.get("seeds")
    _require(
        isinstance(seeds, list)
        and len(seeds) == len(set(seeds)) >= 1
        and all(isinstance(s, int) and not isinstance(s, bool) for s in seeds),
        "plan seeds must be distinct integers",
    )
    datasets = plan.get("datasets")
    _require(isinstance(datasets, dict) and isinstance(datasets.get("root"), str), "datasets")
    tasks = plan.get("tasks")
    _require(isinstance(tasks, dict) and tasks, "plan tasks")
    for task, spec in tasks.items():
        _require(task in TASKS, f"unknown task {task}")
        _require(isinstance(spec, dict), f"task {task} must be a mapping")
        entry = datasets.get(task)
        _require(
            isinstance(entry, dict)
            and isinstance(entry.get("file"), str)
            and SHA_RE.fullmatch(str(entry.get("sha256", ""))) is not None,
            f"datasets.{task} needs file and sha256",
        )
        cap = spec.get("max_tokens")
        _require(isinstance(cap, int) and 256 <= cap <= 131072, f"task {task} max_tokens")
        _require(isinstance(spec.get("sources"), list) and spec["sources"], f"{task} sources")
    order = plan.get("order", {})
    _require(order.get("interleave") and set(order["interleave"]) <= set(tasks), "order")
    arms = plan.get("arms")
    _require(isinstance(arms, dict) and arms, "plan arms")
    for arm_id, arm in arms.items():
        _require(ARM_RE.fullmatch(arm_id) is not None, f"unsafe arm id {arm_id}")
        for key in ("model_id", "gguf", "receipt_sha256", "artifact_root_sha256"):
            _require(isinstance(arm.get(key), str) and arm[key], f"arm {arm_id}: {key}")
        for key in ("receipt_sha256", "artifact_root_sha256"):
            _require(SHA_RE.fullmatch(arm[key]) is not None, f"arm {arm_id}: {key} not hex")
        sampling = arm.get("sampling")
        _require(
            isinstance(sampling, dict) and set(SAMPLER_KEYS) <= set(sampling),
            f"arm {arm_id}: sampling must set {SAMPLER_KEYS}",
        )
        _require(isinstance(arm.get("slots"), int) and 1 <= arm["slots"] <= 128, "slots")
        caps = {
            task: arm.get("max_tokens", {}).get(task, spec["max_tokens"])
            for task, spec in tasks.items()
        }
        _require(
            isinstance(arm.get("ctx_per_slot"), int)
            and arm["ctx_per_slot"] >= max(caps.values()) + 1024,
            f"arm {arm_id}: ctx_per_slot must exceed every max_tokens by at least 1,024",
        )
        _require(isinstance(arm.get("gpus"), int) and 1 <= arm["gpus"] <= 7, "gpus")
        args = arm.get("server_args", [])
        _require(isinstance(args, list) and all(isinstance(a, str) for a in args), "server_args")
        template = arm.get("chat_template_file")
        if template is not None:
            _require(
                SHA_RE.fullmatch(str(arm.get("chat_template_sha256", ""))) is not None,
                f"arm {arm_id}: a chat_template_file needs chat_template_sha256",
            )
    reference = plan.get("reference_arm")
    _require(reference in arms, "reference_arm must be an arm")
    return plan


def load_plan(path: Path = PLAN_PATH, expected_sha256: str | None = None) -> dict[str, Any]:
    raw = path.read_bytes()
    if expected_sha256 is not None and sha256_bytes(raw) != expected_sha256:
        raise LM2Error("plan SHA-256 differs from the expected digest")
    return validate_plan(json.loads(raw))


# --- Items and order -----------------------------------------------------------------------


def load_items(path: Path, expected_sha256: str | None = None) -> list[dict[str, Any]]:
    if expected_sha256 is not None and sha256_file(path) != expected_sha256:
        raise LM2Error(f"{path.name}: SHA-256 differs from the plan")
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def select_items(task: str, spec: dict[str, Any], items: Iterable[dict[str, Any]]) -> list[dict]:
    """The task's eligible items, by the plan's rule (sources and an optional date window)."""

    sources = set(spec["sources"])
    chosen = [item for item in items if item.get("source") in sources]
    numeric_only = set(spec.get("numeric_reference_only_sources", []))
    if numeric_only:
        chosen = [
            item
            for item in chosen
            if item["source"] not in numeric_only
            or evaluate(normalize_math(item["answer"])) is not None
        ]
    if task == "code":
        lo, hi = spec.get("contest_date_from"), spec.get("contest_date_to")
        if lo:
            chosen = [item for item in chosen if item["contest_date"] >= lo]
        if hi:
            chosen = [item for item in chosen if item["contest_date"] < hi]
    if task == "knowledge" and spec.get("subset_size"):
        ranked = sorted(chosen, key=lambda item: sha256_bytes(item["id"].encode()))
        chosen = ranked[: int(spec["subset_size"])]
    ids = [item["id"] for item in chosen]
    if len(ids) != len(set(ids)):
        raise LM2Error(f"{task}: duplicate item ids")
    return chosen


def permuted(items: Sequence[dict[str, Any]], rng_seed: int) -> list[dict[str, Any]]:
    ranked = sorted(items, key=lambda item: sha256_bytes(item["id"].encode()))
    rng = random.Random(rng_seed)
    rng.shuffle(ranked)
    return ranked


def request_order(
    per_task: dict[str, list[dict[str, Any]]],
    interleave: Sequence[str],
    seeds: Sequence[int],
    rng_seed: int,
    caps: dict[str, int] | None = None,
) -> list[tuple[str, dict[str, Any], int, int]]:
    """(task, item, rank, seed) in run order: item-major, tasks alternating, seeds adjacent.

    ``caps`` keeps only the first N items of a task's permutation (a prefix cut).
    """

    queues = {task: permuted(per_task[task], rng_seed) for task in interleave}
    if caps:
        for task, cap in caps.items():
            if task in queues:
                queues[task] = queues[task][:cap]
    order: list[tuple[str, dict[str, Any], int, int]] = []
    rank = 0
    while any(rank < len(queues[task]) for task in interleave):
        for task in interleave:
            if rank < len(queues[task]):
                item = queues[task][rank]
                for seed in seeds:
                    order.append((task, item, rank, seed))
        rank += 1
    return order


def request_key(arm: str, task: str, item_id: str, seed: int) -> str:
    return f"{arm}|{task}|{item_id}|{seed}"


def request_seed(seed: int, item_id: str) -> int:
    """The sampler seed of (seed, item): the same for every arm."""

    return int(sha256_bytes(f"lm2:{seed}:{item_id}".encode())[:8], 16) & 0x7FFFFFFF


# --- Prompts and payloads --------------------------------------------------------------------


def math_prompt(item: dict[str, Any]) -> str:
    return f"{item['problem']}\n\n{MATH_SUFFIX}"


def code_prompt(item: dict[str, Any]) -> str:
    text = f"{LCB_SYSTEM}\n\n### Question:\n{item['question_content']}\n\n"
    starter = item.get("starter_code") or ""
    if starter:
        text += f"### Format: {LCB_WITH_STARTER}\n```python\n{starter}\n```\n\n"
    else:
        text += f"### Format: {LCB_WITHOUT_STARTER}\n```python\n# YOUR CODE HERE\n```\n\n"
    text += "### Answer: (use the provided format with backticks)\n\n"
    return text


def knowledge_prompt(item: dict[str, Any]) -> str:
    options = item["options"]
    letters = MC_LETTERS[: len(options)]
    lines = [MC_HEADER.format(letters=letters), "", item["question"], ""]
    lines += [f"{letter}) {option}" for letter, option in zip(letters, options, strict=False)]
    return "\n".join(lines)


PROMPTS = {"math": math_prompt, "code": code_prompt, "knowledge": knowledge_prompt}


def max_tokens(plan: dict[str, Any], arm_id: str, task: str) -> int:
    arm = plan["arms"][arm_id]
    return int(arm.get("max_tokens", {}).get(task, plan["tasks"][task]["max_tokens"]))


def chat_payload(
    plan: dict[str, Any], arm_id: str, task: str, item: dict[str, Any], seed: int
) -> dict[str, Any]:
    arm = plan["arms"][arm_id]
    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": PROMPTS[task](item)}],
        "max_tokens": max_tokens(plan, arm_id, task),
        "seed": request_seed(seed, item["id"]),
        "cache_prompt": False,
        "n_probs": 0,
        **NEUTRAL_SAMPLERS,
        **{key: arm["sampling"][key] for key in SAMPLER_KEYS},
    }
    if arm.get("chat_template_kwargs"):
        payload["chat_template_kwargs"] = dict(arm["chat_template_kwargs"])
    if arm.get("reasoning_effort"):
        payload["reasoning_effort"] = arm["reasoning_effort"]
    return payload


# --- Extraction and scoring ----------------------------------------------------------------


def extract_code(content: str) -> str:
    """LiveCodeBench's extraction: the text between the last two lines containing ```."""

    lines = content.split("\n")
    fences = [index for index, line in enumerate(lines) if "```" in line]
    if len(fences) < 2:
        return ""
    return "\n".join(lines[fences[-2] + 1 : fences[-1]])


def math_answer(content: str | None) -> str | None:
    return last_boxed(content) if content else None


def score_math(content: str | None, reference: str) -> dict[str, Any]:
    answer = math_answer(content)
    return {"has_answer": answer is not None, "correct": bool(math_equiv(answer, reference))}


def mc_answer(content: str | None) -> str | None:
    if not content:
        return None
    found = MC_ANSWER_RE.findall(content)
    return found[-1] if found else None


def score_knowledge(content: str | None, letter: str) -> dict[str, Any]:
    answer = mc_answer(content)
    return {"has_answer": answer is not None, "correct": answer == letter}


# --- Code verdict comparison (used inside the sandbox grader, trusted side) ------------------


def _decimal_tokens(tokens: list[str]) -> list[Any] | None:
    from decimal import Decimal, InvalidOperation

    out = []
    for token in tokens:
        try:
            out.append(Decimal(token))
        except (InvalidOperation, ValueError):
            return None
    return out


def stdio_match(output: str, expected: str) -> bool:
    """LiveCodeBench-style stdout comparison: stripped lines, then tokens, then exact decimals."""

    got = [line.strip() for line in output.strip().split("\n")]
    want = [line.strip() for line in expected.strip().split("\n")]
    if got == want:
        return True
    if len(got) != len(want):
        return False
    for a, b in zip(got, want, strict=True):
        if a == b:
            continue
        ta, tb = a.split(), b.split()
        if ta == tb:
            continue
        da, db = _decimal_tokens(ta), _decimal_tokens(tb)
        if da is None or db is None or da != db:
            return False
    return True


def _listify(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_listify(v) for v in value]
    if isinstance(value, list):
        return [_listify(v) for v in value]
    return value


def functional_match(result_json: str, expected: str) -> bool:
    """LiveCodeBench-style call-based comparison of a JSON result against the expected JSON."""

    try:
        got = _listify(json.loads(result_json))
        want = _listify(json.loads(expected))
    except (json.JSONDecodeError, TypeError):
        return False
    if got == want:
        return True
    if isinstance(got, list) and len(got) == 1 and got[0] == want:
        return True
    if isinstance(got, float) and isinstance(want, (int, float)):
        return math.isclose(got, want, rel_tol=1e-9, abs_tol=1e-9)
    return False


# --- Analysis ------------------------------------------------------------------------------


def item_means(rows: Iterable[dict[str, Any]], seeds: set[int] | None = None) -> dict[str, float]:
    """Per item, the mean of ``correct`` over its seeds (optionally only the given seeds)."""

    sums: dict[str, list[float]] = {}
    for row in rows:
        if seeds is not None and row["seed"] not in seeds:
            continue
        sums.setdefault(row["item_id"], []).append(1.0 if row["correct"] else 0.0)
    return {item: sum(v) / len(v) for item, v in sums.items()}


def paired_rows(
    rows_a: Sequence[dict[str, Any]], rows_b: Sequence[dict[str, Any]]
) -> tuple[list[float], list[float]]:
    """Per-item accuracies of two arms over the (item, seed) keys both have."""

    keys_a = {(r["item_id"], r["seed"]): r for r in rows_a}
    keys_b = {(r["item_id"], r["seed"]): r for r in rows_b}
    common = sorted(set(keys_a) & set(keys_b))
    by_item: dict[str, list[tuple[float, float]]] = {}
    for key in common:
        by_item.setdefault(key[0], []).append(
            (float(bool(keys_a[key]["correct"])), float(bool(keys_b[key]["correct"])))
        )
    items = sorted(by_item)
    a = [sum(p[0] for p in by_item[i]) / len(by_item[i]) for i in items]
    b = [sum(p[1] for p in by_item[i]) / len(by_item[i]) for i in items]
    return a, b


def cluster_bootstrap_diff(
    a: Sequence[float], b: Sequence[float], draws: int = 10_000, seed: int = 42
) -> dict[str, Any]:
    """Mean of a - b over items (percentage points) with a percentile bootstrap over items."""

    n = len(a)
    if n == 0 or n != len(b):
        return {"n_items": n, "diff": None, "ci95": None}
    diffs = [x - y for x, y in zip(a, b, strict=True)]
    point = 100.0 * sum(diffs) / n
    rng = random.Random(seed)
    stats = []
    for _ in range(draws):
        total = 0.0
        for _ in range(n):
            total += diffs[rng.randrange(n)]
        stats.append(100.0 * total / n)
    stats.sort()
    lo = stats[int(0.025 * draws)]
    hi = stats[min(draws - 1, int(math.ceil(0.975 * draws)) - 1)]
    discordant = sum(1 for d in diffs if d != 0)
    return {
        "n_items": n,
        "diff": round(point, 2),
        "ci95": [round(lo, 2), round(hi, 2)],
        "a_mean": round(100.0 * sum(a) / n, 2),
        "b_mean": round(100.0 * sum(b) / n, 2),
        "items_discordant": discordant,
        "items_a_better": sum(1 for d in diffs if d > 0),
        "items_b_better": sum(1 for d in diffs if d < 0),
    }


def bootstrap_mean(values: Sequence[float], draws: int = 10_000, seed: int = 42) -> list[float]:
    n = len(values)
    if n == 0:
        return []
    rng = random.Random(seed)
    stats = sorted(
        100.0 * sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws)
    )
    return [round(stats[int(0.025 * draws)], 2), round(stats[int(0.975 * draws) - 1], 2)]
