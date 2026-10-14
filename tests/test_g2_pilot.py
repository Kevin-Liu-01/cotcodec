"""Tests for the G2 exploratory pilot (config, plan, parsers, packing and statistics)."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness import g2_pilot as g2  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


rollouts = _load("run_g2_rollouts")
teacher = _load("run_g2_teacher_force")
analysis = _load("analyze_g2_pilot")


def test_config_and_prompts() -> None:
    config = g2.load_config()
    prompts = g2.load_prompts(config)
    assert len(prompts) == 64
    assert all(row["level"] == 5 for row in prompts)
    plan = g2.rollout_plan(config, prompts)
    counts = {m: sum(1 for r in plan if r["model_id"] == m) for m in config["models"]}
    assert counts == {"qwen3.5-4b": 192, "qwen3-8b": 64}
    assert len({r["sequence_id"] for r in plan}) == len(plan)
    assert config["teacher_force"]["fp32_seeds"] == [42]


def test_rollout_plan_engine_kwargs() -> None:
    plan = rollouts.build_plan(g2.load_config())
    kwargs = plan["models"]["qwen3.5-4b"]["engine_kwargs"]
    assert kwargs["trust_remote_code"] is False
    assert kwargs["enable_prefix_caching"] is False
    assert kwargs["logprobs_mode"] == "raw_logprobs"
    assert kwargs["limit_mm_per_prompt"] == {"image": 0, "video": 0}
    assert "limit_mm_per_prompt" not in plan["models"]["qwen3-8b"]["engine_kwargs"]


class _Lp:
    def __init__(self, value: float) -> None:
        self.logprob = value


def test_logprob_parsers() -> None:
    tokens = [5, 7]
    assert rollouts.sampled_logprobs(tokens, [{5: _Lp(-0.5)}, {7: _Lp(-1.0), 2: _Lp(-0.1)}]) == [
        -0.5,
        -1.0,
    ]
    with pytest.raises(ValueError):
        rollouts.sampled_logprobs(tokens, [{5: _Lp(-0.5)}])
    prompt = [None, {1: _Lp(-3.0)}, {5: _Lp(-0.25)}, {7: _Lp(-0.75)}]
    assert rollouts.prefill_logprobs(2, tokens, prompt) == [-0.25, -0.75]
    with pytest.raises(ValueError):
        rollouts.prefill_logprobs(3, tokens, prompt)


def test_k3_and_slope() -> None:
    assert g2.k3(0.0) == 0.0
    assert math.isclose(g2.k3(0.1), math.expm1(0.1) - 0.1)
    rng = np.random.default_rng(0)
    x = rng.uniform(0, 16, 5000)
    y = 0.01 + 0.002 * x + rng.normal(0, 0.001, 5000)
    seq = rng.integers(0, 50, 5000)
    stats = analysis.seq_stats(seq, x, y, 50)
    slope, lo, hi = analysis.bootstrap_slope(stats, 300, 42)
    assert math.isclose(slope, np.polyfit(x, y, 1)[0], rel_tol=1e-9)
    assert lo < 0.002 < hi
    again = analysis.bootstrap_slope(stats, 300, 42)
    assert again == (slope, lo, hi)
    fe = analysis.within_bin_slope(seq, np.zeros(5000, dtype=int), x, y, 50, 300, 42)
    assert math.isclose(fe[0], slope, rel_tol=1e-9)


def test_within_bin_slope_removes_group_confound() -> None:
    rng = np.random.default_rng(1)
    groups = rng.integers(0, 2, 4000)
    x = rng.uniform(0, 10, 4000) + 5 * groups  # later positions sit in group 1
    y = 0.5 * groups + rng.normal(0, 0.01, 4000)  # y depends on the group only
    seq = rng.integers(0, 40, 4000)
    pooled = analysis.ols_slope(analysis.seq_stats(seq, x, y, 40).sum(0))
    within = analysis.within_bin_slope(seq, groups, x, y, 40, 200, 42)[0]
    assert pooled > 0.02
    assert abs(within) < 0.002


def _fake_jobs(tmp: Path) -> tuple[Path, Path]:
    roll = tmp / "roll"
    tf = tmp / "tf"
    (roll / "qwen3.5-4b").mkdir(parents=True)
    tf.mkdir()
    rng = np.random.default_rng(3)
    lengths = [300, 1500, 2500]
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    total = int(offsets[-1])
    tokens = rng.integers(0, 1000, total).astype(np.int32)
    r1 = -rng.exponential(1.0, total).astype(np.float32)
    dec = r1 + rng.normal(0, 0.01, total).astype(np.float32)
    np.savez_compressed(
        roll / "qwen3.5-4b" / "tokens.npz",
        offsets=offsets,
        prompt_len=np.asarray([100, 120, 90], dtype=np.int32),
        token_ids=tokens,
        logp_decode=dec,
        logp_prefill=r1 + 0.001,
    )
    ids = ["qwen3.5-4b/p000/s42", "qwen3.5-4b/p001/s42", "qwen3.5-4b/p000/s43"]
    (roll / "qwen3.5-4b" / "sequences.json").write_text(json.dumps({"sequence_order": ids}))
    r4 = r1 + 0.002
    np.savez_compressed(
        tf / "tf-qwen3.5-4b.npz",
        offsets=offsets,
        prompt_len=np.asarray([100, 120, 90], dtype=np.int32),
        token_ids=tokens,
        logp_r1_fla_chunk_bf16=r1,
        ent_r1_fla_chunk_bf16=rng.uniform(0, 3, total).astype(np.float32),
        logp_r3_fla_recurrent_bf16=r1 - 0.003,
        ent_r3_fla_recurrent_bf16=rng.uniform(0, 3, total).astype(np.float32),
        logp_r4_torch_fp32=np.where(np.arange(total) < offsets[2], r4, np.nan).astype(np.float32),
        ent_r4_torch_fp32=rng.uniform(0, 3, total).astype(np.float32),
    )
    seqs = [
        {"sequence_id": ids[0], "prompt_index": 0, "seed": 42},
        {"sequence_id": ids[1], "prompt_index": 1, "seed": 42},
        {"sequence_id": ids[2], "prompt_index": 0, "seed": 43},
    ]
    (tf / "tf-qwen3.5-4b-sequences.json").write_text(json.dumps(seqs))
    return roll, tf


def test_pack_and_analyze(tmp_path: Path) -> None:
    roll, tf = _fake_jobs(tmp_path)
    packed = analysis.pack_model(roll, tf, "qwen3.5-4b")
    assert packed is not None
    assert packed["position"][0] == 100
    assert packed["position"][300] == 120
    r3 = analysis.path_logp(packed, "r3")
    assert np.allclose(r3 - packed["logp_r1"], -0.003, atol=1e-5)
    settings = dict(g2.load_config()["analysis"], bootstrap_reps=50)
    result = analysis.analyze({"qwen3.5-4b": packed}, settings)
    blocks = result["models"]["qwen3.5-4b"]["subsets"]["seed_42"]
    assert math.isclose(blocks["r1_vs_r4"]["mean_abs"], 0.002, rel_tol=1e-2)
    assert "r1_vs_r4" not in result["models"]["qwen3.5-4b"]["subsets"]["seed_43"]
    assert blocks["dec_vs_r1"]["k3"] > 0
    assert math.isclose(blocks["dec_vs_r3"]["mean_abs"], blocks["dec_vs_r1"]["mean_abs"], rel_tol=0.5)
    assert "## qwen3.5-4b" in analysis.markdown_tables(result)
    assert analysis.contrast_table(result, "qwen3.5-4b", "qwen3-8b") == ""
    both = analysis.analyze({"qwen3.5-4b": packed, "qwen3-8b": packed}, settings)
    assert "| 0 |" in analysis.contrast_table(both, "qwen3.5-4b", "qwen3-8b")


def test_pack_refuses_token_mismatch(tmp_path: Path) -> None:
    roll, tf = _fake_jobs(tmp_path)
    data = dict(np.load(tf / "tf-qwen3.5-4b.npz"))
    data["token_ids"] = data["token_ids"].copy()
    data["token_ids"][5] += 1
    np.savez_compressed(tf / "tf-qwen3.5-4b.npz", **data)
    with pytest.raises(ValueError):
        analysis.pack_model(roll, tf, "qwen3.5-4b")


def test_teacher_force_paths_named() -> None:
    config = g2.load_config()
    for model in config["models"].values():
        assert set(model["tf_paths"]) <= set(teacher.PATHS)
    assert teacher.GDN_IMPL["r3_fla_recurrent_bf16"] == "fla_fused_recurrent"


def test_entry_points_avoid_archived_names() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import submit_docker_research_job as submitter

    for name in ("run_g2_rollouts", "run_g2_teacher_force", "analyze_g2_pilot"):
        assert submitter.archived_memory_reference(f"scripts/{name}.py") is None


def test_merge_tf_inputs() -> None:
    a = {"experiment_id": "g2-pilot-v1", "git_sha": "a" * 40, "sequences": [{"sequence_id": "x"}]}
    b = {"experiment_id": "g2-pilot-v1", "git_sha": "b" * 40, "sequences": [{"sequence_id": "y"}]}
    merged = rollouts.merge_tf_inputs([a, b], "g2-pilot-v1")
    assert [s["sequence_id"] for s in merged["sequences"]] == ["x", "y"]
    assert [s["git_sha"] for s in merged["sources"]] == ["a" * 40, "b" * 40]
    with pytest.raises(g2.G2ConfigError):
        rollouts.merge_tf_inputs([a, a], "g2-pilot-v1")
    with pytest.raises(g2.G2ConfigError):
        rollouts.merge_tf_inputs([dict(a, experiment_id="other")], "g2-pilot-v1")


def test_delta_logprobs_and_prompt_subset() -> None:
    values, missing = rollouts.delta_logprobs([5, 7], [{5: _Lp(-0.5)}, {7: _Lp(-1.0)}])
    assert values == [-0.5, -1.0] and missing == 0
    values, missing = rollouts.delta_logprobs([5, 7], [{5: _Lp(-0.5)}])
    assert missing == 2 and all(math.isnan(v) for v in values)
    assert rollouts.delta_logprobs([], None) == ([], 0)
    prompts = g2.load_prompts(g2.load_config())
    subset = g2.prompt_subset(prompts, 24)
    assert len(subset) == 24
    assert [r["prompt_index"] for r in subset] == sorted(r["prompt_index"] for r in subset)
    assert subset == g2.prompt_subset(prompts, 24)
    assert g2.prompt_subset(prompts, 64) == prompts
