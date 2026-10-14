"""Shared helpers for g2b-state-dtype-v1 (experiments/g2/g2b-state-dtype-v1.yaml), EXPLORATORY.

Pure Python (no torch, no vLLM, no numpy at import) so that both images and the CPU analysis can
import it: config loading and validation, the rollout and saturation request plans, vLLM 0.31.0's
hybrid block accounting, packing for the varlen trainer path, the metrics snapshot parser and the
per-phase stats summary. The G2 pilot's helpers (prompts, receipts, deadline, checkpoint marker)
are reused from harness.g2_pilot.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import yaml

from harness import g2_pilot as g2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "g2" / "g2b-state-dtype-v1.yaml"
EXPERIMENT_ID = "g2b-state-dtype-v1"
#: vLLM's MambaDType values accepted for --mamba-ssm-cache-dtype (config/cache.py:61).
VLLM_MAMBA_DTYPES = ("auto", "float32", "float16", "bfloat16")
ARM_NAMES = ("fp32", "bf16")
DTYPE_BYTES = {"float32": 4, "bfloat16": 2, "float16": 2}
#: Block sizes are rounded up to this many tokens (inference-baseline-v1: 528 and 1,056 tokens
#: for a float32 state, 272 predicted for bf16).
BLOCK_ALIGN_TOKENS = 16
#: Metric names read from LLM.get_metrics() (vllm/v1/metrics/loggers.py:509, 519, 577, 677,
#: 686, 720). Counters may carry a "_total" suffix depending on the prometheus client.
METRIC_KEYS = {
    "vllm:num_requests_running": "running",
    "vllm:num_requests_waiting": "waiting",
    "vllm:kv_cache_usage_perc": "kv_usage",
    "vllm:num_preemptions": "preemptions",
    "vllm:generation_tokens": "generation_tokens",
    "vllm:prompt_tokens": "prompt_tokens",
}


class G2bConfigError(ValueError):
    """The g2b config or its inputs are invalid."""


# --------------------------------------------------------------------------- config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("experiment_id") != EXPERIMENT_ID:
        raise G2bConfigError("not the g2b-state-dtype-v1 config")
    if config.get("claim_level") != "exploratory":
        raise G2bConfigError("g2b-state-dtype-v1 is exploratory only")
    if config.get("seeds") != [42, 43, 44]:
        raise G2bConfigError("seeds must be [42, 43, 44]")
    arms = config.get("state_dtypes") or {}
    if tuple(arms) != ARM_NAMES:
        raise G2bConfigError(f"state_dtypes must name the arms {ARM_NAMES} in order")
    for arm, value in arms.items():
        if value not in VLLM_MAMBA_DTYPES:
            raise G2bConfigError(f"{arm}: {value!r} is not a vLLM MambaDType")
    if arms["fp32"] != "auto" or arms["bf16"] != "bfloat16":
        raise G2bConfigError("the arms are vLLM's default ('auto') and 'bfloat16'")
    for model_id, model in config["models"].items():
        if not set(model["arms"]) <= {"mismatch", "concurrency"}:
            raise G2bConfigError(f"{model_id}: unknown arm")
        for key in ("gen_seconds",):
            if model_id not in config["rollouts"][key]:
                raise G2bConfigError(f"{model_id}: rollouts.{key} missing")
        for key in ("requests_per_prompt", "output_tokens"):
            if model_id not in config["saturation"][key]:
                raise G2bConfigError(f"{model_id}: saturation.{key} missing")
    sampling = config["rollouts"]["sampling"]
    longest = config["engine"]["max_model_len"] - sampling["max_tokens"]
    if longest < 720:  # the longest rendered prompt (G2 pilot selftest: 720 tokens)
        raise G2bConfigError("max_model_len leaves no room for the longest prompt")
    if set(config["teacher_force"]["r2_seeds"]) - set(config["seeds"]):
        raise G2bConfigError("r2 seeds must be declared seeds")
    if set(config["teacher_force"]["r4_seeds"]) - set(config["seeds"]):
        raise G2bConfigError("r4 seeds must be declared seeds")
    analysis = config["analysis"]
    analysis["entropy_edges"] = g2.numeric_edges(analysis.get("entropy_edges"), "entropy_edges")
    return config


def mismatch_models(config: dict[str, Any]) -> list[str]:
    return [m for m, spec in config["models"].items() if "mismatch" in spec["arms"]]


def vllm_state_dtype(config: dict[str, Any], arm: str) -> str:
    if arm not in config["state_dtypes"]:
        raise G2bConfigError(f"unknown arm {arm!r}")
    return str(config["state_dtypes"][arm])


def arm_for_state_dtype(config: dict[str, Any], dtype: str) -> str:
    for arm, value in config["state_dtypes"].items():
        if value == dtype:
            return arm
    raise G2bConfigError(f"no arm uses state dtype {dtype!r}")


def engine_settings(config: dict[str, Any], model_id: str, prefill: bool = False) -> dict[str, Any]:
    settings = dict(config["engine"])
    settings.update(config.get("engine_overrides", {}).get(model_id, {}))
    if prefill:
        settings.update(config["prefill"]["engine_overrides"])
    return settings


def sequence_id(model_id: str, arm: str, prompt_index: int, seed: int) -> str:
    return f"{model_id}/{arm}/p{prompt_index:03d}/s{seed}"


def parse_sequence_id(value: str) -> dict[str, Any]:
    model_id, arm, prompt, seed = value.split("/")
    return {
        "model_id": model_id,
        "arm": arm,
        "prompt_index": int(prompt[1:]),
        "seed": int(seed[1:]),
    }


def rollout_requests(
    config: dict[str, Any], prompts: Sequence[dict[str, Any]], model_id: str, arm: str
) -> list[dict[str, Any]]:
    """Phase R requests in submission order (seed, then prompt): id, prompt index, seed, cap."""

    rollouts = config["rollouts"]
    moe = "mismatch" not in config["models"][model_id]["arms"]
    count = rollouts["moe_prompt_count"] if moe else rollouts["prompt_count"]
    seeds = rollouts["moe_seeds"] if moe else config["seeds"]
    cap = rollouts["moe_max_tokens"] if moe else rollouts["sampling"]["max_tokens"]
    subset = g2.prompt_subset(prompts, count)
    return [
        {
            "sequence_id": sequence_id(model_id, arm, row["prompt_index"], seed),
            "prompt_index": int(row["prompt_index"]),
            "seed": int(seed),
            "max_tokens": int(cap),
        }
        for seed in seeds
        for row in subset
    ]


def saturation_seed(seed: int, prompt_index: int, j: int) -> int:
    if not 0 <= j < 100 or not 0 <= prompt_index < 10_000:
        raise G2bConfigError("saturation request index out of range")
    return seed * 1_000_000 + prompt_index * 100 + j


def saturation_requests(
    config: dict[str, Any], prompts: Sequence[dict[str, Any]], model_id: str, seed: int
) -> list[dict[str, Any]]:
    """Phase S wave for one seed: every prompt x requests_per_prompt, fixed output length."""

    sat = config["saturation"]
    per = int(sat["requests_per_prompt"][model_id])
    out = int(sat["output_tokens"][model_id])
    return [
        {
            "request_id": f"S/{seed}/p{row['prompt_index']:03d}/{j}",
            "prompt_index": int(row["prompt_index"]),
            "seed": saturation_seed(seed, int(row["prompt_index"]), j),
            "output_tokens": out,
        }
        for row in prompts
        for j in range(per)
    ]


# --------------------------------------------------------------------------- block accounting


def gdn_page_bytes(config: dict[str, Any], state_dtype: str) -> int:
    """One sequence's GDN state for one layer: recurrent state plus bf16 convolution state."""

    geo = config["gdn_state"]
    recurrent = geo["num_v_heads"] * geo["head_k_dim"] * geo["head_v_dim"]
    conv = geo["conv_dim"] * geo["conv_width_minus_1"]
    return recurrent * DTYPE_BYTES[state_dtype] + conv * DTYPE_BYTES["bfloat16"]


def resolved_state_dtype(config_value: str, checkpoint_dtype: str = "float32") -> str:
    """vLLM's resolution of mamba_ssm_cache_dtype for Qwen3.5 (models/config.py:829-832)."""

    return checkpoint_dtype if config_value == "auto" else config_value


def predicted_block_tokens(attn_bytes_per_token_layer: int, gdn_page: int) -> int:
    """Smallest aligned attention block whose page holds one layer's GDN state."""

    tokens = math.ceil(gdn_page / attn_bytes_per_token_layer)
    return int(math.ceil(tokens / BLOCK_ALIGN_TOKENS) * BLOCK_ALIGN_TOKENS)


def blocks_per_sequence(length: int, block_tokens: int, gdn_groups: int = 3) -> int:
    """Blocks one running sequence of ``length`` tokens holds: attention blocks for its tokens
    plus one block in each GDN group (inference-baseline-v1, hybrid block pool)."""

    if length <= 0 or block_tokens <= 0:
        raise ValueError("length and block size must be positive")
    return math.ceil(length / block_tokens) + gdn_groups


def max_sequences(num_blocks: int, length: int, block_tokens: int, gdn_groups: int = 3) -> int:
    """Most sequences of ``length`` tokens that fit at once (one block is vLLM's null block)."""

    usable = max(num_blocks - 1, 0)
    return usable // blocks_per_sequence(length, block_tokens, gdn_groups)


# --------------------------------------------------------------------------- packing


def greedy_packs(lengths: Sequence[int], budget: int) -> list[list[int]]:
    """Indices grouped into packs of at most ``budget`` tokens, first fit in index order; a
    sequence longer than the budget is a pack of its own."""

    if budget <= 0:
        raise ValueError("budget must be positive")
    packs: list[list[int]] = []
    current: list[int] = []
    used = 0
    for index, length in enumerate(lengths):
        if current and used + length > budget:
            packs.append(current)
            current, used = [], 0
        current.append(index)
        used += int(length)
    if current:
        packs.append(current)
    return packs


def cu_seqlens(lengths: Iterable[int]) -> list[int]:
    out = [0]
    for length in lengths:
        out.append(out[-1] + int(length))
    return out


# --------------------------------------------------------------------------- metrics and stats


def parse_metrics(metrics: Iterable[Any]) -> dict[str, float]:
    """Gauge and counter values of interest from LLM.get_metrics() (one engine)."""

    out: dict[str, float] = {}
    for metric in metrics:
        name = str(getattr(metric, "name", ""))
        base = name[: -len("_total")] if name.endswith("_total") else name
        key = METRIC_KEYS.get(base)
        if key is None or not hasattr(metric, "value"):
            continue
        out[key] = out.get(key, 0.0) + float(metric.value)
    return out


def cache_config_info(metrics: Iterable[Any]) -> dict[str, str] | None:
    for metric in metrics:
        if str(getattr(metric, "name", "")).startswith("vllm:cache_config_info"):
            return dict(getattr(metric, "labels", {}) or {})
    return None


def summarize_phase(
    steps: Sequence[Sequence[float]],
    samples: Sequence[dict[str, float]],
    requests: int,
    finished: int,
    output_tokens: int,
    wall_s: float,
) -> dict[str, Any]:
    """One phase's throughput and concurrency summary.

    ``steps``: (t, outputs this step, new tokens this step) per engine step; ``samples``: metric
    snapshots with ``t`` and the METRIC_KEYS values. Counters are reported as the change over
    the phase; the output count per step is the number of requests that produced a token.
    """

    out: dict[str, Any] = {
        "requests": requests,
        "finished": finished,
        "output_tokens": output_tokens,
        "wall_s": round(wall_s, 3),
        "output_tok_per_s": output_tokens / wall_s if wall_s > 0 else float("nan"),
        "steps": len(steps),
        "peak_outputs_per_step": max((int(s[1]) for s in steps), default=0),
    }
    if steps:
        out["mean_outputs_per_step"] = sum(s[1] for s in steps) / len(steps)
    if samples:
        first, last = samples[0], samples[-1]
        for key in ("running", "waiting", "kv_usage"):
            values = [s[key] for s in samples if key in s]
            if values:
                out[f"peak_{key}"] = max(values)
                out[f"mean_{key}"] = sum(values) / len(values)
        for key in ("preemptions", "generation_tokens", "prompt_tokens"):
            if key in first and key in last:
                out[f"{key}_delta"] = last[key] - first[key]
        out["metric_samples"] = len(samples)
    return out


def spread(values: Sequence[float]) -> dict[str, float]:
    """Mean, min, max and (max - min) / mean of repeat values."""

    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not vals:
        return {"n": 0}
    mean = sum(vals) / len(vals)
    return {
        "n": len(vals),
        "mean": mean,
        "min": min(vals),
        "max": max(vals),
        "range_over_mean": (max(vals) - min(vals)) / mean if mean else float("nan"),
    }
