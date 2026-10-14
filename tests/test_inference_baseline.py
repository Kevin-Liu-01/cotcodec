"""CPU tests for the exploratory inference baseline driver (no vLLM, no GPU)."""

# The engine-log fixture quotes vLLM 0.31.0 log lines verbatim.
# ruff: noqa: E501

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from scripts import analyze_inference_baseline as an
from scripts import run_inference_baseline as ib

ENGINE_LOG = """\
(APIServer pid=133) INFO 10-07 15:07:42 [model.py:699] Resolved architecture: Qwen3_5ForConditionalGeneration
(EngineCore pid=481) INFO 10-07 15:08:06 [cuda.py:526] Using FLASH_ATTN attention backend out of potential backends: ['FLASH_ATTN']
(EngineCore pid=481) INFO 10-07 15:08:11 [model_runner.py:407] Model loading took 17.66 GiB memory and 8.714965 seconds
(EngineCore pid=481) INFO 10-07 15:08:35 [monitor.py:53] torch.compile took 17.87 s in total
(EngineCore pid=481) INFO 10-07 15:08:54 [model_runner.py:1087] Graph capturing finished in 9 secs, took 0.65 GiB
(EngineCore pid=481) INFO 10-07 15:08:54 [gpu_worker.py:692] Available KV cache memory: 51.24 GiB
(EngineCore pid=481) INFO 10-07 15:08:54 [kv_cache_utils.py:2464] GPU KV cache size: 1,634,030 tokens, Maximum concurrency for 131,072 tokens per request: 12.47x
(EngineCore pid=481) INFO 10-07 15:09:05 [gpu_worker.py:955] Free memory on device (78.68/79.19 GiB) on startup. Desired GPU memory utilization is (0.9, 71.27 GiB). Actual usage is 18.25 GiB for consumed memory (weights + non-torch), 1.79 GiB for peak activation, and 0.43 GiB for CUDAGraph memory. Replace
(EngineCore pid=481) INFO 10-07 15:09:07 [core.py:373] init engine (profile, create kv cache, warmup model) took 55.67 s (compilation: 17.87 s)
"""

METRICS = """\
# HELP vllm:kv_cache_usage_perc KV-cache usage.
# TYPE vllm:kv_cache_usage_perc gauge
vllm:kv_cache_usage_perc{engine="0",model_name="ib"} 0.25
vllm:num_requests_running{engine="0",model_name="ib"} 7.0
vllm:prefix_cache_queries_total{engine="0",model_name="ib"} 1000.0
vllm:prefix_cache_hits_total{engine="0",model_name="ib"} 10.0
vllm:cache_config_info{block_size="16",cache_dtype="auto",num_gpu_blocks="102127"} 1.0
vllm:unrelated_total{engine="0"} 5.0
"""


@pytest.fixture(scope="module")
def config() -> dict:
    return ib.load_config()


def test_every_job_resolves_within_limits(config: dict) -> None:
    gpu_minutes = 0
    for job in config["jobs"]:
        plan = ib.resolve_plan(config, job)
        assert plan["claim_level"] == "exploratory"
        assert plan["primary_model"] in plan["models"]
        for engine in plan["engines"]:
            assert engine["tp"] <= plan["gpus"]
            for cell in engine["cells"]:
                assert cell["input_len"] + cell["output_len"] <= engine["max_model_len"]
        gpu_minutes += plan["gpus"]
    assert set(config["jobs"]) == {"a", "b", "c", "d", "e", "f", "g", "h"}


def test_serve_argv_carries_engine_flags(config: dict) -> None:
    plan = ib.resolve_plan(config, "b")
    by_id = {engine["id"]: engine for engine in plan["engines"]}
    base = by_id["qwen3.5-9b-tp1"]["serve_argv"]
    assert base[:3] == ["vllm", "serve", "/model-cache/cotcodec-models/qwen3.5-9b"]
    assert "--enable-prefix-caching" in base
    assert base[base.index("--kv-cache-dtype") + 1] == "auto"
    assert base[base.index("--limit-mm-per-prompt") + 1] == '{"image":0,"video":0}'
    assert "--no-enable-prefix-caching" in by_id["qwen3.5-9b-tp1-nopc"]["serve_argv"]
    fp8 = by_id["qwen3.5-9b-tp1-kvfp8"]["serve_argv"]
    assert fp8[fp8.index("--kv-cache-dtype") + 1] == "fp8"
    assert "--trust-remote-code" not in " ".join(base)


def test_tp_engines_and_tp1_context_limit(config: dict) -> None:
    assert ib.resolve_plan(config, "f")["engines"][0]["tp"] == 4
    e = {engine["id"]: engine for engine in ib.resolve_plan(config, "e")["engines"]}
    assert e["qwen3-32b-tp1"]["max_model_len"] == 16384
    assert not any(c["shape"] == "in32k" for c in e["qwen3-32b-tp1"]["cells"])
    assert any(c["shape"] == "in32k" for c in e["qwen3-32b-tp1-kvfp8"]["cells"])


def test_bench_argv_skips_ready_check_and_forces_lengths(config: dict, tmp_path: Path) -> None:
    plan = ib.resolve_plan(config, "a")
    engine = plan["engines"][1]
    cells = {cell["cell_id"]: cell for cell in engine["cells"]}
    argv = ib.bench_serve_argv(
        engine, cells["in8k-c32"], seed=42, result_dir=tmp_path, result_filename="x.json", label="l"
    )
    assert argv[argv.index("--ready-check-timeout-sec") + 1] == "0"
    assert "--ignore-eos" in argv
    assert argv[argv.index("--random-input-len") + 1] == "8192"
    assert argv[argv.index("--num-prompts") + 1] == "64"
    assert argv[argv.index("--max-concurrency") + 1] == "32"
    prefix = ib.bench_serve_argv(
        engine,
        cells["prefix-c8"],
        seed=42,
        result_dir=tmp_path,
        result_filename="y.json",
        label="l",
    )
    assert prefix[prefix.index("--dataset-name") + 1] == "prefix_repetition"
    assert prefix[prefix.index("--prefix-repetition-prefix-len") + 1] == "4096"


def test_offline_cells_scale(config: dict) -> None:
    moe = ib.resolve_plan(config, "c")["engines"][0]
    counts = {cell["shape"]: cell["num_prompts"] for cell in moe["offline_cells"]}
    assert counts == {"chat": 256, "in8k": 32, "decode": 64}
    argv = ib.offline_argv(moe, moe["offline_cells"][0], 42)
    assert argv[argv.index("--tensor-parallel-size") + 1] == "2"


def test_parse_engine_log() -> None:
    parsed = ib.parse_engine_log(ENGINE_LOG)
    assert parsed["weights_gib_per_rank"] == [17.66]
    assert parsed["kv_cache_gib_per_rank"] == [51.24]
    assert parsed["kv_cache_tokens"] == 1634030
    assert parsed["max_concurrency_at_len"] == {"len": 131072, "x": 12.47}
    assert parsed["actual_usage_gib_per_rank"][0]["peak_activation"] == 1.79
    assert parsed["init_engine_s"] == 55.67
    assert parsed["compilation_s"] == 17.87
    assert parsed["attention_backends"] == ["FLASH_ATTN"]
    assert parsed["architecture"] == "Qwen3_5ForConditionalGeneration"


def test_parse_prometheus_and_summary() -> None:
    values, cache = ib.parse_prometheus(METRICS)
    assert values["vllm:kv_cache_usage_perc"] == 0.25
    assert "vllm:unrelated_total" not in values
    assert cache["num_gpu_blocks"] == "102127"
    rows = [
        {"t": 1.0, "vllm:kv_cache_usage_perc": 0.1},
        {"t": 2.0, "vllm:kv_cache_usage_perc": 0.3},
    ]
    before = {"vllm:prefix_cache_queries_total": 100.0, "vllm:prefix_cache_hits_total": 0.0}
    after = {"vllm:prefix_cache_queries_total": 300.0, "vllm:prefix_cache_hits_total": 50.0}
    summary = ib.summarize_metrics(rows, before, after)
    assert summary["peak_kv_cache_usage_perc"] == 0.3
    assert summary["prefix_cache_hit_rate"] == 0.25


def test_safetensors_breakdown(tmp_path: Path) -> None:
    header = {
        "model.embed_tokens.weight": {"dtype": "BF16", "shape": [4, 2], "data_offsets": [0, 16]},
        "model.layers.0.mlp.experts.3.up_proj.weight": {
            "dtype": "BF16", "shape": [2, 2], "data_offsets": [16, 24],
        },
        "model.layers.0.mlp.shared_expert.up_proj.weight": {
            "dtype": "BF16", "shape": [2, 2], "data_offsets": [24, 32],
        },
        "model.visual.blocks.0.weight": {"dtype": "BF16", "shape": [2], "data_offsets": [32, 36]},
        "__metadata__": {"format": "pt"},
    }  # fmt: skip
    blob = json.dumps(header).encode()
    (tmp_path / "model.safetensors").write_bytes(struct.pack("<Q", len(blob)) + blob + b"\0" * 36)
    out = ib.safetensors_breakdown(tmp_path)
    assert out["bytes_by_category"] == {
        "embed_tokens": 16,
        "routed_experts": 8,
        "shared_expert": 8,
        "vision": 4,
    }
    assert (
        ib.tensor_category("model.layers.3.linear_attn.in_proj_qkvz.weight") == "linear_attention"
    )
    assert ib.tensor_category("model.layers.3.mlp.gate.weight") == "router"
    assert ib.tensor_category("lm_head.weight") == "lm_head"


def test_unknown_job_is_refused(config: dict) -> None:
    with pytest.raises(ib.PlanError):
        ib.resolve_plan(config, "z")


def test_gdn_state_bytes_match_vllm_page_padding() -> None:
    """Qwen3.5-9B geometry: the fp32 SSM state reproduces vLLM's logged 528-token block and 0.76%."""
    text = {
        "num_hidden_layers": 32, "full_attention_interval": 4, "hidden_size": 4096,
        "num_attention_heads": 16, "num_key_value_heads": 4, "head_dim": 256,
        "linear_num_key_heads": 16, "linear_num_value_heads": 32, "linear_key_head_dim": 128,
        "linear_value_head_dim": 128, "linear_conv_kernel_dim": 4, "mamba_ssm_dtype": "float32",
    }  # fmt: skip
    geo = an.geometry({"config": {"text_config": text}})
    per_layer = 32 * 128 * 128 * 4 + (2 * 16 * 128 + 32 * 128) * 3 * 2
    assert per_layer == 2_146_304
    assert geo["linear_attention_layers"] == 24
    assert geo["state_ssm_dtype"] == "float32"
    assert geo["state_bytes_per_seq"] == 24 * per_layer
    attn_page = 528 * 2 * 4 * 256 * 2  # block size x K and V x KV heads x head dim x bf16
    assert round(100 * (attn_page - per_layer) / per_layer, 2) == 0.76
    bf16 = an.geometry({"config": {"text_config": {**text, "mamba_ssm_dtype": "bfloat16"}}})
    assert bf16["state_bytes_per_seq"] == 24 * 1_097_728
    moved = an.decode_bytes_per_step(geo, batch=2.0, context=0.0, kv_dtype="auto")
    assert moved["state"] == 2 * 2 * 24 * per_layer  # batch x read and write x state
    # The engine's recorded mamba_ssm_cache_dtype wins over the checkpoint; "auto" means bf16.
    bare = {k: v for k, v in text.items() if k != "mamba_ssm_dtype"}
    assert an.geometry({"config": bare}, "float32")["state_bytes_per_seq"] == 24 * per_layer
    assert an.geometry({"config": {"text_config": text}}, "auto")["state_ssm_dtype"] == "bfloat16"
    assert an.geometry({"config": bare})["state_ssm_dtype"] == "bfloat16"
