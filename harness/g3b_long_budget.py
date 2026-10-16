"""Shared helpers for g3b-long-budget-v1 (experiments/g3/g3b-long-budget-v1.yaml), EXPLORATORY.

G3b reruns G3's Qwen3.5-4B math arm (``harness.g3_state_precision``) with a float32 and a
bfloat16 GDN state on the 51 questions that had a capped rollout in G3, at the model card's
81,920-token budget and with no preemption. Pure Python (no torch, vLLM or numpy at import), so
the vLLM image, the CPU selftest and the host analysis all import it:

* config loading and validation, the pinned question list and its derivation from G3's
  committed per-request data, and each phase's plan;
* the requests (G3's order, seed then question, and G3's request seeds);
* the engine settings, and the check that every running sequence fits the block pool at
  max_model_len (so the scheduler never preempts);
* scoring a rollout as if it had been capped at L generated tokens.

The prompts, the checker (v2) and the sampling are G3's, imported from
``harness.g3_state_precision``.
"""

from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
from typing import Any

import yaml

from harness import g3_state_precision as g3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "g3" / "g3b-long-budget-v1.yaml"
EXPERIMENT_ID = "g3b-long-budget-v1"
MODEL_ID = "qwen3.5-4b"
ARM_DTYPES = {"fp32": "auto", "bf16": "bfloat16", "fp32_aa": "auto"}
REFERENCE_ARM = "fp32"
PHASES = ("pilot", "main", "aa")
TASK = "math"
MODEL_ROOT = g3.MODEL_ROOT
G3_CAP = 32768
#: The worker's finish reason for a rollout still running when the job's time budget ended.
TIME_CUT = "cut_at_time_budget"


class G3bConfigError(ValueError):
    """The g3b config or its inputs are invalid."""


def indices_digest(indices: list[int]) -> str:
    """SHA-256 of the indices, one per line, ascending, each line ending in a newline."""

    return g3.sha256_bytes("".join(f"{int(q)}\n" for q in indices).encode("utf-8"))


def capped_questions(rows: list[dict[str, Any]], model: str = MODEL_ID) -> list[int]:
    """G3's questions with at least one rollout that reached its cap (finish_reason "length"), in
    any arm and seed of the model's main math run."""

    return sorted(
        {
            int(r["question_index"])
            for r in rows
            if r["phase"] == "main"
            and r["model"] == model
            and r["task"] == "math"
            and r["finish_reason"] == "length"
        }
    )


def read_g3_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# --------------------------------------------------------------------------- config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("experiment_id") != EXPERIMENT_ID:
        raise G3bConfigError("not the g3b-long-budget-v1 config")
    if config.get("claim_level") != "exploratory":
        raise G3bConfigError("g3b is exploratory only")
    if config.get("seeds") != [42, 43, 44]:
        raise G3bConfigError("seeds must be [42, 43, 44] (G3's request seeds)")
    if list(config.get("models") or {}) != [MODEL_ID]:
        raise G3bConfigError("g3b runs Qwen3.5-4B only")
    if dict(config.get("arms") or {}) != ARM_DTYPES or tuple(config["arms"]) != tuple(ARM_DTYPES):
        raise G3bConfigError(f"arms must be {ARM_DTYPES} in order")
    if set(config["tasks"]) != {TASK}:
        raise G3bConfigError("g3b runs the math task only")
    q = config["questions"]
    indices = [int(i) for i in q["indices"]]
    count = int(config["tasks"][TASK]["prompts"]["count"])
    if indices != sorted(set(indices)) or not all(0 <= i < count for i in indices):
        raise G3bConfigError("question indices must be distinct, ascending and in range")
    if indices_digest(indices) != q["indices_sha256"]:
        raise G3bConfigError("question indices differ from their pinned digest")
    spec = config["tasks"][TASK]
    sampling = spec["sampling"]
    if sampling["max_tokens"] >= spec["max_model_len"]:
        raise G3bConfigError("max_tokens must leave room for the prompt")
    for key in ("temperature", "top_p", "top_k", "min_p", "presence_penalty"):
        if key not in sampling:
            raise G3bConfigError(f"sampling.{key} missing")
    caps = [int(c) for c in spec.get("rescore_caps") or []]
    if G3_CAP not in caps or any(not 0 < c < int(sampling["max_tokens"]) for c in caps):
        raise G3bConfigError("rescore_caps must include G3's 32,768 and stay below max_tokens")
    e = config["engine"]
    if e.get("enable_prefix_caching"):
        raise G3bConfigError("prefix caching stays off, as in G3")
    if int(e["max_num_seqs"]) < 1 or int(e["gdn_groups"]) < 1:
        raise G3bConfigError("max_num_seqs and gdn_groups must be positive")
    for phase in PHASES:
        if phase in config:
            phase_plan(config, phase)
    return config


def g3_view(config: dict[str, Any]) -> dict[str, Any]:
    """The pieces of the config in the shape G3's helpers read (prompts, suffix, sampling)."""

    return {"tasks": {TASK: config["tasks"][TASK]}}


def phase_plan(config: dict[str, Any], phase: str) -> dict[str, Any]:
    """Arms, question indices, seeds and the generation budget of one phase, validated. Every
    phase uses the pinned questions unless it names a subset of them (``questions``)."""

    if phase not in PHASES or phase not in config:
        raise G3bConfigError(f"no {phase!r} phase in the config")
    spec = config[phase]
    arms = list(spec["arms"])
    if not arms or not set(arms) <= set(ARM_DTYPES) or len(set(arms)) != len(arms):
        raise G3bConfigError(f"{phase}: unknown or repeated arm")
    pinned = [int(i) for i in config["questions"]["indices"]]
    questions = [int(i) for i in spec.get("questions", pinned)]
    if not questions or not set(questions) <= set(pinned) or questions != sorted(set(questions)):
        raise G3bConfigError(f"{phase}: questions must be an ascending subset of the pinned list")
    seeds = [int(s) for s in spec["seeds"]]
    if not seeds or not set(seeds) <= set(config["seeds"]) or seeds != sorted(set(seeds)):
        raise G3bConfigError(f"{phase}: seeds must be an ascending subset of the declared seeds")
    if phase == "main" and (
        arms != ["fp32", "bf16"] or questions != pinned or seeds != config["seeds"]
    ):
        raise G3bConfigError("main runs fp32 and bf16 on every pinned question and seed")
    if phase == "aa" and arms != ["fp32_aa"]:
        raise G3bConfigError("aa runs the second fp32 engine only")
    gen = float(spec["gen_seconds"])
    if gen <= 0:
        raise G3bConfigError(f"{phase}: gen_seconds must be positive")
    return {
        "phase": phase,
        "arms": arms,
        "math_questions": questions,
        "math_seeds": seeds,
        "math_gen_seconds": gen,
    }


def math_requests(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """G3's submission order (seed, then question) and request seeds, for the plan's subset."""

    return [
        {
            "request_id": f"m/q{q:03d}/s{seed}",
            "question_index": q,
            "seed": seed,
            "request_seed": g3.request_seed(seed, q),
        }
        for seed in plan["math_seeds"]
        for q in plan["math_questions"]
    ]


def engine_kwargs(config: dict[str, Any], model_dir: Path, arm: str) -> dict[str, Any]:
    """G3's rollout engine with this arm's state dtype and G3b's max_model_len and
    max_num_seqs."""

    if arm not in ARM_DTYPES:
        raise G3bConfigError(f"unknown arm {arm!r}")
    e = config["engine"]
    return {
        "model": str(model_dir),
        "tokenizer": str(model_dir),
        "trust_remote_code": False,
        "dtype": e["dtype"],
        "seed": int(e["seed"]),
        "max_model_len": int(config["tasks"][TASK]["max_model_len"]),
        "gpu_memory_utilization": float(e["gpu_memory_utilization"]),
        "max_num_seqs": int(e["max_num_seqs"]),
        "max_num_batched_tokens": int(e["max_num_batched_tokens"]),
        "enable_prefix_caching": bool(e["enable_prefix_caching"]),
        "logprobs_mode": e["logprobs_mode"],
        "limit_mm_per_prompt": dict(e["limit_mm_per_prompt"]),
        "disable_log_stats": bool(e["disable_log_stats"]),
        "mamba_ssm_cache_dtype": config["arms"][arm],
    }


def sampling_kwargs(config: dict[str, Any], seed: int, stop_id: int) -> dict[str, Any]:
    return g3.sampling_kwargs(g3_view(config), TASK, seed, stop_id)


# --------------------------------------------------------------------------- the fit check


def blocks_per_sequence(length: int, block_tokens: int, gdn_groups: int) -> int:
    """Blocks one running sequence of ``length`` tokens holds in vLLM's hybrid pool: attention
    blocks for its tokens plus one block in each GDN group (mamba_cache_mode "none")."""

    if length <= 0 or block_tokens <= 0 or gdn_groups < 0:
        raise ValueError("length, block size and groups must be positive")
    return math.ceil(length / block_tokens) + gdn_groups


def fit_report(
    num_gpu_blocks: int,
    block_size: int,
    max_model_len: int,
    max_num_seqs: int,
    gdn_groups: int,
    vllm_max_concurrency: float | None = None,
) -> dict[str, Any]:
    """Whether ``max_num_seqs`` sequences of ``max_model_len`` tokens fit the pool at once (one
    block is vLLM's null block), so that no request is ever preempted. vLLM's own figure
    (``kv_cache_max_concurrency``: blocks over blocks per sequence, null block included) is
    recorded and must agree with the same formula."""

    per_seq = blocks_per_sequence(max_model_len, block_size, gdn_groups)
    fits = (max(num_gpu_blocks - 1, 0)) // per_seq
    report: dict[str, Any] = {
        "num_gpu_blocks": int(num_gpu_blocks),
        "block_size": int(block_size),
        "max_model_len": int(max_model_len),
        "gdn_groups": int(gdn_groups),
        "blocks_per_sequence": per_seq,
        "max_sequences_that_fit": int(fits),
        "max_num_seqs": int(max_num_seqs),
        "blocks_needed": per_seq * int(max_num_seqs),
        "ok": int(max_num_seqs) <= fits,
    }
    if vllm_max_concurrency is not None:
        ours = num_gpu_blocks / per_seq
        report["vllm_kv_cache_max_concurrency"] = float(vllm_max_concurrency)
        report["formula_concurrency"] = ours
        report["vllm_agrees"] = math.isclose(ours, float(vllm_max_concurrency), rel_tol=1e-6)
        report["ok"] = report["ok"] and report["vllm_agrees"]
    return report


# --------------------------------------------------------------------------- scoring


def score_text(text: str, reference: str) -> dict[str, Any]:
    """G3's checker v2 on one completion (the last boxed answer after the last ``</think>``)."""

    ans = g3.final_answer(text)
    return {
        "thinking_closed": ans["thinking_closed"],
        "has_answer": ans["answer"] is not None,
        "correct": int(g3.math_equiv(ans["answer"], reference)),
    }


def score_at_cap(
    completion_len: int,
    finish_reason: str,
    full: dict[str, Any],
    truncated: dict[str, Any] | None,
    cap: int,
) -> dict[str, Any]:
    """A rollout as a run capped at ``cap`` generated tokens would have scored it: unchanged if it
    ended within the cap, else its first ``cap`` tokens (``truncated``, scored from the text the
    worker decoded) with the cap reached. The tokens before the cap do not depend on the cap.
    A rollout cut by the job's time budget before it reached the cap has no outcome at the cap
    (every field None): it would have gone on."""

    if completion_len < cap and finish_reason == TIME_CUT:
        return {"correct": None, "has_answer": None, "cap_hit": None, "ended": None, "len": None}
    if completion_len <= cap:
        return {
            "correct": int(full["correct"]),
            "has_answer": bool(full["has_answer"]),
            "cap_hit": int(finish_reason == "length" and completion_len == cap),
            "ended": int(finish_reason == "stop"),
            "len": int(completion_len),
        }
    if truncated is None:
        raise G3bConfigError("a rollout longer than the cap needs its truncated text")
    return {
        "correct": int(truncated["correct"]),
        "has_answer": bool(truncated["has_answer"]),
        "cap_hit": 1,
        "ended": 0,
        "len": int(cap),
    }
