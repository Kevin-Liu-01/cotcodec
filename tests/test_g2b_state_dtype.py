"""Tests for g2b-state-dtype-v1 (EXPLORATORY): config, plans, block accounting, packing, metrics
parsing, the join and the mismatch statistics. CPU only; no torch or vLLM needed."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness import g2_pilot as g2  # noqa: E402
from harness import g2b_state_dtype as gb  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


rollouts = _load("run_g2b_rollouts")
teacher = _load("run_g2b_teacher_force")
analysis = _load("analyze_g2b_state_dtype")


def test_config_arms_and_edges() -> None:
    config = gb.load_config()
    assert config["state_dtypes"] == {"fp32": "auto", "bf16": "bfloat16"}
    assert all(isinstance(e, float) for e in config["analysis"]["entropy_edges"])
    assert config["analysis"]["entropy_edges"][-1] == 1.0e9
    assert gb.mismatch_models(config) == ["qwen3.5-4b", "qwen3.5-9b"]
    assert set(config["state_dtypes"].values()) <= set(gb.VLLM_MAMBA_DTYPES)


def test_request_plans() -> None:
    config = gb.load_config()
    prompts = g2.load_prompts(config)
    r = gb.rollout_requests(config, prompts, "qwen3.5-4b", "bf16")
    assert len(r) == 72 and len({x["sequence_id"] for x in r}) == 72
    assert {x["seed"] for x in r} == {42, 43, 44}
    assert {x["max_tokens"] for x in r} == {32768}
    # The 24 prompts are the G2 pilot's (g2.prompt_subset with the same count).
    pilot = {row["prompt_index"] for row in g2.prompt_subset(prompts, 24)}
    assert {x["prompt_index"] for x in r} == pilot
    moe = gb.rollout_requests(config, prompts, "qwen3.6-35b-a3b", "fp32")
    assert len(moe) == 64 and {x["seed"] for x in moe} == {42} and moe[0]["max_tokens"] == 16384
    wave = gb.saturation_requests(config, prompts, "qwen3.5-9b", 43)
    assert len(wave) == 512 and len({w["seed"] for w in wave}) == 512
    assert {w["output_tokens"] for w in wave} == {2048}
    assert len(gb.saturation_requests(config, prompts, "qwen3.6-35b-a3b", 42)) == 128
    seeds = {gb.saturation_seed(s, p, j) for s in (42, 43, 44) for p in range(64) for j in range(8)}
    assert len(seeds) == 3 * 64 * 8
    with pytest.raises(gb.G2bConfigError):
        gb.saturation_seed(42, 1, 100)
    parsed = gb.parse_sequence_id(r[5]["sequence_id"])
    assert parsed["arm"] == "bf16" and parsed["seed"] == r[5]["seed"]


def test_engine_kwargs() -> None:
    config = gb.load_config()
    kw = rollouts.engine_kwargs(config, "qwen3.5-9b", Path("/m"), "bfloat16")
    assert kw["mamba_ssm_cache_dtype"] == "bfloat16"
    assert kw["disable_log_stats"] is False and kw["trust_remote_code"] is False
    assert kw["gpu_memory_utilization"] == 0.90 and kw["max_num_seqs"] == 512
    assert kw["max_model_len"] >= 32768 + 720
    pre = rollouts.engine_kwargs(config, "qwen3.5-9b", Path("/m"), "auto", prefill=True)
    assert pre["gpu_memory_utilization"] == 0.80 and pre["max_num_batched_tokens"] == 4096
    assert pre["mamba_ssm_cache_dtype"] == "auto"
    moe = rollouts.engine_kwargs(config, "qwen3.6-35b-a3b", Path("/m"), "auto")
    assert moe["max_num_seqs"] == 128
    with pytest.raises(gb.G2bConfigError):
        rollouts.engine_kwargs(config, "qwen3.5-9b", Path("/m"), "fp8")
    plan = rollouts.build_plan(config)
    assert plan["models"]["qwen3.5-4b"]["arms"]["fp32"]["rollout_requests"] == 72


def test_block_accounting_reproduces_inference_baseline() -> None:
    config = gb.load_config()
    fp32 = gb.gdn_page_bytes(config, "float32")
    bf16 = gb.gdn_page_bytes(config, "bfloat16")
    assert fp32 == 2_146_304  # inference-baseline-v1, hybrid block pool section
    assert bf16 == 1_097_728
    assert fp32 * 24 / 2**20 == pytest.approx(49.125)
    assert fp32 * 30 / 2**20 == pytest.approx(61.40625)
    assert gb.predicted_block_tokens(4096, fp32) == 528
    assert gb.predicted_block_tokens(2048, fp32) == 1056
    assert gb.predicted_block_tokens(4096, bf16) == 272
    assert gb.predicted_block_tokens(2048, bf16) == 544
    # 9B, 3,171 blocks: chat 634, long output 264, 32k 48 (baseline table); MoE TP 1: 51.
    assert gb.max_sequences(3171, 768, 528) == 634
    assert gb.max_sequences(3171, 4608, 528) == 264
    assert gb.max_sequences(3171, 32256, 528) == 48
    assert gb.max_sequences(207, 768, 1056) == 51
    assert gb.resolved_state_dtype("auto") == "float32"
    assert gb.resolved_state_dtype("bfloat16") == "bfloat16"


def test_greedy_packs() -> None:
    assert gb.greedy_packs([10, 20, 30, 50], 60) == [[0, 1, 2], [3]]
    assert gb.greedy_packs([70, 5], 60) == [[0], [1]]
    assert gb.cu_seqlens([3, 4]) == [0, 3, 7]


def test_metrics_parser_and_summary() -> None:
    metrics = [
        SimpleNamespace(name="vllm:num_requests_running", labels={}, value=12.0),
        SimpleNamespace(name="vllm:num_preemptions_total", labels={}, value=4),
        SimpleNamespace(name="vllm:kv_cache_usage_perc", labels={}, value=0.75),
        SimpleNamespace(name="vllm:unrelated", labels={}, value=1.0),
        SimpleNamespace(name="vllm:cache_config_info", labels={"block_size": "272"}, value=1.0),
    ]
    assert gb.parse_metrics(metrics) == {"running": 12.0, "preemptions": 4.0, "kv_usage": 0.75}
    assert gb.cache_config_info(metrics) == {"block_size": "272"}
    steps = [(0.1, 3, 3), (0.2, 5, 5)]
    samples = [
        {"t": 0, "running": 0, "preemptions": 1.0},
        {"t": 0.2, "running": 5, "preemptions": 3.0},
    ]
    s = gb.summarize_phase(steps, samples, 5, 5, 8, 0.25)
    assert s["peak_running"] == 5 and s["preemptions_delta"] == 2.0 and s["output_tok_per_s"] == 32
    sp = gb.spread([10.0, 11.0, 12.0])
    assert sp["mean"] == 11.0 and sp["range_over_mean"] == pytest.approx(2 / 11)


def test_merge_inputs() -> None:
    a = {
        "experiment_id": gb.EXPERIMENT_ID,
        "sequences": [{"sequence_id": "m/fp32/p000/s42", "model_id": "m"}],
    }
    b = {
        "experiment_id": gb.EXPERIMENT_ID,
        "sequences": [{"sequence_id": "m/bf16/p000/s42", "model_id": "m"}],
    }
    merged = rollouts.merge_inputs([a, b], gb.EXPERIMENT_ID)
    assert len(merged["sequences"]) == 2
    with pytest.raises(gb.G2bConfigError):
        rollouts.merge_inputs([a, a], gb.EXPERIMENT_ID)
    with pytest.raises(gb.G2bConfigError):
        rollouts.merge_inputs([a, {"experiment_id": "other", "sequences": []}], gb.EXPERIMENT_ID)


def test_teacher_force_members() -> None:
    config = gb.load_config()
    seqs = [{"seed": s, "prompt_index": p} for s in (42, 43) for p in (0, 1, 2, 5)]
    members = teacher.path_members(config, seqs)
    assert members["r1"] == list(range(8))
    assert members["r2"] == [0, 1, 2, 3]
    r4 = teacher.r4_prompt_indices(config)
    assert len(r4) == 16
    assert members["r4"] == [
        i for i, s in enumerate(seqs) if s["seed"] == 42 and s["prompt_index"] in r4
    ]
    assert teacher.segments([0, 3, 7]) == [(0, 3), (3, 7)]


def test_common_prefix() -> None:
    assert analysis.common_prefix(np.asarray([1, 2, 3]), np.asarray([1, 2, 4, 5])) == 2
    assert analysis.common_prefix(np.asarray([1, 2]), np.asarray([1, 2, 3])) == 2
    assert analysis.common_prefix(np.asarray([]), np.asarray([1])) == 0


def _synthetic_jobs(tmp: Path, bf16_scale: float, trend: float) -> tuple[Path, ...]:
    """Two arms' rollout dirs, a prefill dir and a teacher-forcing dir for 4 prompts x 2 seeds.
    The bf16 arm's decode mismatch is ``bf16_scale`` times the fp32 arm's and grows by
    ``trend`` per 1,000 positions."""

    rng = np.random.default_rng(42)
    model = "qwen3.5-4b"
    order, seqs_by_arm = [], {"fp32": [], "bf16": []}
    for arm in ("fp32", "bf16"):
        for seed in (42, 43):
            for prompt in (0, 1, 2, 5):
                n = int(rng.integers(1500, 3000))
                ids = rng.integers(0, 1000, n)
                if (
                    arm == "bf16"
                ):  # share a prefix with the fp32 rollout of the same prompt and seed
                    twin = next(s for s in seqs_by_arm["fp32"] if s["key"] == (prompt, seed))
                    ids[:50] = twin["ids"][:50]
                    ids[50] = (twin["ids"][50] + 1) % 1000
                sid = gb.sequence_id(model, arm, prompt, seed)
                r1 = -np.abs(rng.normal(0, 1, n))
                pos = 100 + np.arange(n)
                noise = np.abs(rng.normal(0, 0.01, n)) * (bf16_scale if arm == "bf16" else 1.0)
                if arm == "bf16":
                    noise = noise + trend * pos / 1000.0
                seqs_by_arm[arm].append(
                    {
                        "sid": sid,
                        "key": (prompt, seed),
                        "ids": ids,
                        "r1": r1,
                        "dec": r1 + noise * rng.choice([-1, 1], n),
                        "prompt": prompt,
                        "seed": seed,
                    }
                )
                order.append((arm, len(seqs_by_arm[arm]) - 1))
    dirs = []
    for arm in ("fp32", "bf16"):
        d = tmp / f"{model}-{arm}"
        d.mkdir()
        seqs = seqs_by_arm[arm]
        offsets = np.concatenate([[0], np.cumsum([len(s["ids"]) for s in seqs])])
        np.savez(
            d / "tokens.npz",
            offsets=offsets,
            prompt_len=np.full(len(seqs), 100, np.int32),
            token_ids=np.concatenate([s["ids"] for s in seqs]).astype(np.int32),
            logp_decode=np.concatenate([s["dec"] for s in seqs]).astype(np.float32),
        )
        (d / "sequences.json").write_text(
            json.dumps(
                {
                    "arm": arm,
                    "sequence_order": [s["sid"] for s in seqs],
                    "sequences": [{"sequence_id": s["sid"], "finish_reason": "stop"} for s in seqs],
                }
            )
        )
        dirs.append(d)
    merged = [seqs_by_arm[a][i] for a, i in order]
    offsets = np.concatenate([[0], np.cumsum([len(s["ids"]) for s in merged])])
    tf = tmp / "tf"
    tf.mkdir()
    r1 = np.concatenate([s["r1"] for s in merged])
    np.savez(
        tf / f"tf-{model}.npz",
        offsets=offsets,
        prompt_len=np.full(len(merged), 100, np.int32),
        token_ids=np.concatenate([s["ids"] for s in merged]).astype(np.int32),
        logp_r1=r1.astype(np.float32),
        ent_r1=rng.uniform(0, 3, len(r1)).astype(np.float32),
        logp_r2=(r1 + rng.normal(0, 0.002, len(r1))).astype(np.float32),
        pack_id=np.arange(len(merged), dtype=np.int32) // 2,
        pack_slot=np.arange(len(merged), dtype=np.int32) % 2,
    )
    (tf / f"tf-{model}-sequences.json").write_text(
        json.dumps(
            [
                {"sequence_id": s["sid"], "arm": a, "prompt_index": s["prompt"], "seed": s["seed"]}
                for (a, _), s in zip(order, merged, strict=True)
            ]
        )
    )
    pre = tmp / "pre"
    pre.mkdir()
    for arm in ("fp32", "bf16"):
        np.savez(
            pre / f"prefill-{arm}.npz",
            offsets=offsets,
            logp_prefill=(r1 + rng.normal(0, 0.003, len(r1))).astype(np.float32),
        )
        (pre / f"prefill-{arm}.json").write_text(
            json.dumps({"sequence_order": [s["sid"] for s in merged]})
        )
    return dirs[0], dirs[1], pre, tf


def test_pack_and_analyze_detect_injected_effects(tmp_path: Path) -> None:
    fp32_dir, bf16_dir, pre, tf = _synthetic_jobs(tmp_path, bf16_scale=2.0, trend=0.004)
    packed = analysis.pack_model("qwen3.5-4b", [fp32_dir, bf16_dir], pre, tf)
    assert packed["arm"].tolist() == [0] * 8 + [1] * 8
    assert set(packed["common_prefix"][packed["arm"] == 1].tolist()) == {50}
    assert np.isfinite(packed["d_pair"].astype(float)).sum() == 8 * 50
    config = gb.load_config()
    settings = dict(config["analysis"]) | {"bootstrap_reps": 300}
    result = analysis.analyze_model(packed, settings)
    c = result["contrasts"]["dec_vs_r1"]
    assert c["mean_abs"]["ratio"] > 2.0
    assert c["mean_abs"]["ratio_ci95"][0] > 1.5
    assert c["slope_within_sequences_per_1k"]["diff"] == pytest.approx(0.004, rel=0.1)
    assert c["slope_within_sequences_per_1k"]["diff_ci95"][0] > 0
    assert result["subsets"]["both/all"]["pre32_vs_pre16"]["tokens"] == int(packed["offsets"][-1])
    assert result["shared_prefix"]["median"] == 50
    assert [r["slot"] for r in result["packed_by_slot"]] == [0, 1]
    text = analysis.markdown({"mismatch": {"qwen3.5-4b": result}})
    assert "arm contrasts" in text


def test_pack_refuses_token_mismatch(tmp_path: Path) -> None:
    fp32_dir, bf16_dir, pre, tf = _synthetic_jobs(tmp_path, bf16_scale=1.0, trend=0.0)
    data = dict(np.load(tf / "tf-qwen3.5-4b.npz"))
    data["token_ids"] = data["token_ids"].copy()
    data["token_ids"][3] += 1
    np.savez(tf / "tf-qwen3.5-4b.npz", **data)
    with pytest.raises(ValueError, match="tokens differ"):
        analysis.pack_model("qwen3.5-4b", [fp32_dir, bf16_dir], pre, tf)


def test_parse_log(tmp_path: Path) -> None:
    log = tmp_path / "w.log"
    log.write_text(
        "INFO 10-15 [kv_cache_utils.py:1] GPU KV cache size: 1,505,903 tokens\n"
        "INFO 10-15 [kv_cache_utils.py:2] Maximum concurrency for 33,536 tokens per request: 44.91x\n"  # noqa: E501
        "INFO 10-15 [interface.py:3] Setting attention block size to 272 tokens to ensure ...\n"
        "INFO 10-15 [qwen_gdn_linear_attn.py:4] GDN decode kernel: cuda\n"
    )
    facts = analysis.parse_log(log)
    assert facts["kv_cache_tokens"] == 1505903
    assert facts["max_concurrency"] == [33536, 44.91]
    assert facts["attention_block_tokens"] == 272 and facts["gdn_decode_kernel"] == "cuda"


def test_entry_points_avoid_archived_names() -> None:
    for name in ("run_g2b_rollouts", "run_g2b_teacher_force", "analyze_g2b_state_dtype"):
        assert "mem" not in name and "letta" not in name
