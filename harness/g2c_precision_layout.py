"""Shared helpers for g2c-precision-layout-v1 (experiments/g2/g2c-precision-layout-v1.yaml).

EXPLORATORY. Two new vLLM 0.31.0 GDN-state arms on top of G2b (g2b-state-dtype-v1), whose fp32
and bf16 arms are reused from their committed, hash-bound outputs:

* ``fp16``: ``mamba_ssm_cache_dtype=float16`` at vLLM's own block size (272 tokens, as bf16).
* ``bf16_b528``: ``mamba_ssm_cache_dtype=bfloat16`` with ``block_size=528``, the fp32 arm's block.

Everything else (prompts, engine, sampling, budgets, prefill engine, r4 subset, analysis
settings) is G2b's config, loaded through ``harness.g2b_state_dtype.load_config`` and pinned by
its SHA-256. Pure Python (no torch, vLLM or numpy at import).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

from harness import g2_pilot as g2
from harness import g2b_state_dtype as gb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "experiments" / "g2" / "g2c-precision-layout-v1.yaml"
EXPERIMENT_ID = "g2c-precision-layout-v1"
#: The arms this experiment runs, in run order.
ARM_NAMES = ("fp16", "bf16_b528")
#: G2b's arms, reused (not rerun).
REFERENCE_ARMS = gb.ARM_NAMES
#: Every arm in analysis order: G2b's two, then this experiment's two.
ALL_ARMS = REFERENCE_ARMS + ARM_NAMES
#: Each arm's state dtype and block layout, for tables (the G2b arms' resolved values).
ARM_LABELS = {
    "fp32": "fp32 state, 528-token blocks (G2b)",
    "bf16": "bf16 state, 272-token blocks (G2b)",
    "fp16": "fp16 state, 272-token blocks",
    "bf16_b528": "bf16 state, 528-token blocks (forced)",
}
#: vLLM 0.31.0's FLASH_ATTN backend advertises MultipleOf(16) kernel blocks
#: (v1/attention/backends/flash_attn.py:355-363).
KERNEL_BLOCK_MULTIPLE = 16
TF_PATHS = ("r1", "r4")


class G2cConfigError(ValueError):
    """The g2c config or its inputs are invalid."""


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("experiment_id") != EXPERIMENT_ID:
        raise G2cConfigError("not the g2c-precision-layout-v1 config")
    if raw.get("claim_level") != "exploratory":
        raise G2cConfigError("g2c-precision-layout-v1 is exploratory only")
    if raw.get("seeds") != [42, 43, 44]:
        raise G2cConfigError("seeds must be [42, 43, 44]")
    base_spec = raw["base_config"]
    base_path = PROJECT_ROOT / base_spec["file"]
    if g2.sha256_file(base_path) != base_spec["sha256"]:
        raise G2cConfigError("G2b base config digest differs from base_config.sha256")
    base = gb.load_config(base_path)
    if base["seeds"] != raw["seeds"]:
        raise G2cConfigError("seeds must equal G2b's")
    models = list(raw["models"])
    if not models or not set(models) <= set(gb.mismatch_models(base)):
        raise G2cConfigError("models must be G2b mismatch models")
    arms = raw.get("arms") or {}
    if tuple(arms) != ARM_NAMES:
        raise G2cConfigError(f"arms must be {ARM_NAMES} in order")
    for name, arm in arms.items():
        dtype = arm.get("mamba_ssm_cache_dtype")
        if dtype not in gb.VLLM_MAMBA_DTYPES or dtype == "auto":
            raise G2cConfigError(f"{name}: an explicit vLLM MambaDType is required")
        block = arm.get("block_size")
        if block is not None and (
            not isinstance(block, int) or block <= 0 or block % KERNEL_BLOCK_MULTIPLE
        ):
            raise G2cConfigError(f"{name}: block_size must be a positive multiple of 16")
    if arms["fp16"] != {"mamba_ssm_cache_dtype": "float16", "block_size": None}:
        raise G2cConfigError("fp16 is float16 at vLLM's own block size")
    if arms["bf16_b528"]["mamba_ssm_cache_dtype"] != "bfloat16":
        raise G2cConfigError("bf16_b528 is a bfloat16 state")
    for model_id in models:
        if raw["fp32_block_tokens"].get(model_id) != arms["bf16_b528"]["block_size"]:
            raise G2cConfigError(f"{model_id}: bf16_b528's block must equal G2b's fp32 block")
    if set(raw["saturation_seeds"]) - set(raw["seeds"]):
        raise G2cConfigError("saturation seeds must be declared seeds")
    if tuple(raw["teacher_force"]["paths"]) != TF_PATHS:
        raise G2cConfigError(f"teacher-force paths must be {TF_PATHS}")
    config: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "claim_level": "exploratory",
        "seeds": list(raw["seeds"]),
        "base_experiment_id": base["experiment_id"],
        "base_config": dict(base_spec),
        "prompts": base["prompts"],
        "models": {m: base["models"][m] for m in models},
        "engine": base["engine"],
        "engine_overrides": {
            m: v for m, v in base.get("engine_overrides", {}).items() if m in models
        },
        "rollouts": base["rollouts"],
        "saturation": dict(base["saturation"], seeds=list(raw["saturation_seeds"])),
        "prefill": base["prefill"],
        "teacher_force": {
            "paths": list(TF_PATHS),
            "lm_head_chunk": base["teacher_force"]["lm_head_chunk"],
            "r4_seeds": base["teacher_force"]["r4_seeds"],
            "r4_prompts": base["teacher_force"]["r4_prompts"],
        },
        "analysis": base["analysis"],
        "gdn_state": base["gdn_state"],
        "arms": {name: dict(arm) for name, arm in arms.items()},
        "fp32_block_tokens": dict(raw["fp32_block_tokens"]),
        "probe": dict(raw["probe"]),
        "reference": raw["reference"],
        "budget": raw["budget"],
    }
    return config


def arm_state_dtype(config: dict[str, Any], arm: str) -> str:
    if arm not in config["arms"]:
        raise G2cConfigError(f"unknown arm {arm!r}")
    return str(config["arms"][arm]["mamba_ssm_cache_dtype"])


def arm_block_size(config: dict[str, Any], arm: str) -> int | None:
    if arm not in config["arms"]:
        raise G2cConfigError(f"unknown arm {arm!r}")
    block = config["arms"][arm]["block_size"]
    return None if block is None else int(block)


def rollout_requests(
    config: dict[str, Any], prompts: list[dict[str, Any]], model_id: str, arm: str
) -> list[dict[str, Any]]:
    """Phase R requests: G2b's plan (24 prompts x seeds 42-44, 32K cap) under this arm's id."""

    if arm not in ARM_NAMES:
        raise G2cConfigError(f"unknown arm {arm!r}")
    return gb.rollout_requests(config, prompts, model_id, arm)


def r4_prompt_indices(config: dict[str, Any], prompts: list[dict[str, Any]]) -> set[int]:
    subset = g2.prompt_subset(prompts, config["rollouts"]["prompt_count"])
    return {int(r["prompt_index"]) for r in subset[: config["teacher_force"]["r4_prompts"]]}


def tf_members(
    config: dict[str, Any], prompts: list[dict[str, Any]], sequences: list[dict[str, Any]]
) -> dict[str, list[int]]:
    """Indices of the sequences each teacher-forcing path scores: r1 all, r4 G2b's subset."""

    r4_prompts = r4_prompt_indices(config, prompts)
    r4_seeds = set(config["teacher_force"]["r4_seeds"])
    return {
        "r1": list(range(len(sequences))),
        "r4": [
            i
            for i, s in enumerate(sequences)
            if s["seed"] in r4_seeds and s["prompt_index"] in r4_prompts
        ],
    }


# --------------------------------------------------------------------------- block accounting


def attention_page_bytes_per_token(num_kv_heads: int, head_dim: int, dtype_bytes: int = 2) -> int:
    """One token's K and V in one full-attention layer."""

    return 2 * num_kv_heads * head_dim * dtype_bytes


def resolved_block_tokens(
    gdn_page: int, attn_per_token: int, user_block: int | None, kernel_multiple: int = 16
) -> int:
    """vLLM 0.31.0's hybrid block size without prefix caching (platforms/interface.py
    _align_hybrid_block_size, lines 951-993): alignment = max(kernel multiple, user block or
    the backend default 16); the smallest aligned block whose attention page holds the GDN
    page; a smaller user block is raised to it, a larger one kept."""

    alignment = max(kernel_multiple, user_block or kernel_multiple)
    needed = alignment * math.ceil(gdn_page / (alignment * attn_per_token))
    current = user_block or kernel_multiple
    return needed if current < needed else current


def mamba_padding_pct(gdn_page: int, attn_per_token: int, block_tokens: int) -> float:
    """How much vLLM pads the GDN page up to the attention page (interface.py:998-1018)."""

    page = block_tokens * attn_per_token
    if page < gdn_page:
        raise G2cConfigError("attention page smaller than the GDN page (vLLM asserts this)")
    return 100.0 * (page - gdn_page) / gdn_page
