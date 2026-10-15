"""Tests for g2c-precision-layout-v1 (EXPLORATORY): config inheritance from G2b, the arms' engine
settings, vLLM 0.31.0's hybrid block rule, teacher-forcing membership, the join and the
four-arm statistics. CPU only; no torch or vLLM needed."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness import g2_pilot as g2  # noqa: E402
from harness import g2b_state_dtype as gb  # noqa: E402
from harness import g2c_precision_layout as gc  # noqa: E402

MODEL = "qwen3.5-4b"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


rollouts = _load("run_g2c_rollouts")
teacher = _load("run_g2c_teacher_force")
analysis = _load("analyze_g2c_precision_layout")
g2b_teacher = _load("run_g2b_teacher_force")


def test_config_inherits_g2b() -> None:
    config = gc.load_config()
    base = gb.load_config()
    assert config["seeds"] == base["seeds"] == [42, 43, 44]
    assert list(config["models"]) == ["qwen3.5-4b", "qwen3.5-9b"]
    for key in ("prompts", "engine", "rollouts", "prefill", "analysis", "gdn_state"):
        assert config[key] == base[key]
    assert config["saturation"]["seeds"] == [42]
    assert config["saturation"]["output_tokens"] == base["saturation"]["output_tokens"]
    assert config["teacher_force"]["r4_prompts"] == 16 and config["teacher_force"]["r4_seeds"] == [
        42
    ]
    assert config["arms"] == {
        "fp16": {"mamba_ssm_cache_dtype": "float16", "block_size": None},
        "bf16_b528": {"mamba_ssm_cache_dtype": "bfloat16", "block_size": 528},
    }
    assert gc.ALL_ARMS == ("fp32", "bf16", "fp16", "bf16_b528")


def _tampered(tmp_path: Path, edit) -> Path:
    raw = yaml.safe_load(gc.CONFIG_PATH.read_text(encoding="utf-8"))
    edit(raw)
    path = tmp_path / "g2c.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "edit",
    [
        lambda r: r["base_config"].update(sha256="0" * 64),
        lambda r: r["arms"]["bf16_b528"].update(block_size=544),
        lambda r: r["arms"]["bf16_b528"].update(block_size=520),
        lambda r: r["arms"]["fp16"].update(mamba_ssm_cache_dtype="auto"),
        lambda r: r["arms"]["fp16"].update(block_size=272),
        lambda r: r.update(seeds=[42, 43]),
        lambda r: r.update(models=["qwen3.6-35b-a3b"]),
        lambda r: r["teacher_force"].update(paths=["r1", "r2", "r4"]),
        lambda r: r.update(claim_level="confirmatory"),
    ],
)
def test_config_refuses_tampering(tmp_path: Path, edit) -> None:
    with pytest.raises(gc.G2cConfigError):
        gc.load_config(_tampered(tmp_path, edit))


def test_rollout_plan_matches_g2b() -> None:
    config = gc.load_config()
    base = gb.load_config()
    prompts = g2.load_prompts(config)
    ours = gc.rollout_requests(config, prompts, MODEL, "fp16")
    theirs = gb.rollout_requests(base, prompts, MODEL, "fp32")
    assert len(ours) == 72
    strip = [{k: v for k, v in r.items() if k != "sequence_id"} for r in ours]
    assert strip == [{k: v for k, v in r.items() if k != "sequence_id"} for r in theirs]
    assert gb.parse_sequence_id(ours[0]["sequence_id"])["arm"] == "fp16"
    with pytest.raises(gc.G2cConfigError):
        gc.rollout_requests(config, prompts, MODEL, "fp32")


def test_engine_kwargs_per_arm() -> None:
    config = gc.load_config()
    fp16 = rollouts.engine_kwargs(config, MODEL, Path("/m"), "fp16")
    assert fp16["mamba_ssm_cache_dtype"] == "float16" and "block_size" not in fp16
    forced = rollouts.engine_kwargs(config, MODEL, Path("/m"), "bf16_b528")
    assert forced["mamba_ssm_cache_dtype"] == "bfloat16" and forced["block_size"] == 528
    pre = rollouts.engine_kwargs(config, MODEL, Path("/m"), "bf16_b528", prefill=True)
    assert pre["block_size"] == 528 and pre["max_num_batched_tokens"] == 4096
    assert pre["gpu_memory_utilization"] == 0.80
    # Everything else equals G2b's engines.
    g2b_rollouts = _load("run_g2b_rollouts")
    g2b = g2b_rollouts.engine_kwargs(gb.load_config(), MODEL, Path("/m"), "bfloat16")
    assert {k: v for k, v in forced.items() if k != "block_size"} == g2b
    probe = rollouts.probe_kwargs(config, MODEL, Path("/m"))
    assert probe["block_size"] == 272 and probe["mamba_ssm_cache_dtype"] == "auto"
    assert probe["load_format"] == "dummy" and probe["enforce_eager"] is True
    plan = rollouts.build_plan(config)
    assert plan["models"][MODEL]["arms"]["bf16_b528"]["rollout_requests"] == 72
    assert plan["models"][MODEL]["arms"]["fp16"]["saturation_requests_per_wave"] == {42: 512}


def test_block_rule_reproduces_g2b_and_predicts_the_arms() -> None:
    config = gc.load_config()
    attn = gc.attention_page_bytes_per_token(4, 256)
    assert attn == 4096
    fp32 = gb.gdn_page_bytes(config, "float32")
    half = gb.gdn_page_bytes(config, "bfloat16")
    assert gb.gdn_page_bytes(config, "float16") == half
    # G2b's engines: 528 and 272 tokens, padding 0.76% and 1.49% (worker logs).
    assert gc.resolved_block_tokens(fp32, attn, None) == 528
    assert gc.resolved_block_tokens(half, attn, None) == 272
    assert round(gc.mamba_padding_pct(fp32, attn, 528), 2) == 0.76
    assert round(gc.mamba_padding_pct(half, attn, 272), 2) == 1.49
    # The arms: bf16 at a user block of 528 is kept and padded about 97%.
    assert gc.resolved_block_tokens(half, attn, 528) == 528
    assert round(gc.mamba_padding_pct(half, attn, 528), 2) == 97.01
    # fp32 at a user block of 272 is raised to 544 (alignment max(16, 272)).
    assert gc.resolved_block_tokens(fp32, attn, 272) == 544
    assert gc.resolved_block_tokens(fp32, attn, 1024) == 1024
    with pytest.raises(gc.G2cConfigError):
        gc.mamba_padding_pct(fp32, attn, 272)
    # bf16 at 528 has the same page bytes per block as fp32 at 528: the same block pool.
    assert 528 * attn == gc.resolved_block_tokens(fp32, attn, None) * attn


def test_teacher_force_members_equal_g2b_subset() -> None:
    config = gc.load_config()
    prompts = g2.load_prompts(config)
    subset = sorted(r["prompt_index"] for r in g2.prompt_subset(prompts, 24))
    seqs = [
        {"seed": s, "prompt_index": p, "arm": a} for a in gc.ARM_NAMES for s in (42, 43, 44)
        for p in subset
    ]  # fmt: skip
    members = gc.tf_members(config, prompts, seqs)
    assert members["r1"] == list(range(144)) and len(members["r4"]) == 32
    assert gc.r4_prompt_indices(config, prompts) == g2b_teacher.r4_prompt_indices(gb.load_config())


def test_teacher_force_input_checks() -> None:
    seq = {
        "sequence_id": f"{MODEL}/fp16/p000/s42",
        "model_id": MODEL,
        "arm": "fp16",
        "prompt_index": 0,
        "seed": 42,
        "prompt_ids": [1],
        "completion_ids": [2],
    }
    ok = {"experiment_id": gc.EXPERIMENT_ID, "sequences": [seq]}
    assert teacher.check_input(ok, MODEL) == [seq]
    for bad in (
        {"experiment_id": "g2b-state-dtype-v1", "sequences": [seq]},
        {"experiment_id": gc.EXPERIMENT_ID, "sequences": [seq, seq]},
        {"experiment_id": gc.EXPERIMENT_ID, "sequences": [dict(seq, arm="bf16")]},
        {"experiment_id": gc.EXPERIMENT_ID, "sequences": [dict(seq, completion_ids=[])]},
    ):
        with pytest.raises(gc.G2cConfigError):
            teacher.check_input(bad, MODEL)


# --------------------------------------------------------------------------- synthetic data

PROMPTS = (0, 1, 2, 5, 7, 9)
SEEDS = (42, 43)


def _arm_seqs(rng: np.random.Generator, scale: float, trend: float) -> list[dict]:
    seqs = []
    for seed in SEEDS:
        for prompt in PROMPTS:
            n = 1500 + (prompt * 397 + seed * 113) % 1500  # equal lengths in every arm
            pos = 100 + np.arange(n)
            noise = np.abs(rng.normal(0, 0.01, n)) * scale + trend * pos / 1000.0
            seqs.append(
                {
                    "prompt": prompt,
                    "seed": seed,
                    "ids": rng.integers(0, 1000, n),
                    "r1": -np.abs(rng.normal(0, 1, n)),
                    "d": noise * rng.choice([-1, 1], n),
                }
            )
    return seqs


def _per_token(arms: list[list[dict]], rng: np.random.Generator, g2b: bool) -> dict:
    """A per-token file in G2b's (d_pre32/d_pre16) or this experiment's (d_pre) encoding."""

    seqs = [(a, s) for a, arm in enumerate(arms) for s in arm]
    lengths = [len(s["ids"]) for _, s in seqs]
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    total = int(offsets[-1])
    d_dec = np.concatenate([s["d"] for _, s in seqs])
    raw = {
        "offsets": offsets,
        "prompt_len": np.full(len(seqs), 100, np.int32),
        "arm": np.asarray([a for a, _ in seqs], np.int8),
        "seed": np.asarray([s["seed"] for _, s in seqs], np.int16),
        "prompt_index": np.asarray([s["prompt"] for _, s in seqs], np.int16),
        "finished": np.ones(len(seqs), np.int8),
        "ent_r1": rng.uniform(0, 3, total).astype(np.float16),
        "d_dec": d_dec.astype(np.float16),
        "d_r4": rng.normal(0, 0.008, total).astype(np.float16),
    }
    pre = rng.normal(0, 0.008, total).astype(np.float16)
    if g2b:
        raw["d_pre32"], raw["d_pre16"] = pre, pre
    else:
        raw["d_pre"] = pre
    raw["position"] = analysis.ab.token_positions(offsets, raw["prompt_len"])
    return raw


def test_four_arm_contrasts_recover_injected_effects(tmp_path: Path) -> None:
    rng = np.random.default_rng(42)
    fp32 = _arm_seqs(rng, 1.0, 0.0)
    bf16 = _arm_seqs(rng, 1.0, 0.006)
    fp16 = _arm_seqs(rng, 1.0, 0.0)  # fp32-like
    b528 = _arm_seqs(rng, 1.0, 0.006)  # bf16-like
    data = analysis.combine(
        _per_token([fp32, bf16], rng, g2b=True), _per_token([fp16, b528], rng, g2b=False)
    )
    assert sorted(set(data["arm"].tolist())) == [0, 1, 2, 3]
    config = gc.load_config()
    settings = dict(config["analysis"]) | {"bootstrap_reps": 300}
    result = analysis.analyze_model(data, settings)
    con = result["contrasts"]["dec_vs_r1"]
    assert con["prompts"] == len(PROMPTS)
    pairs = con["pairs"]
    assert pairs["bf16_vs_fp32"]["mean_abs"]["ratio"] > 1.5
    assert pairs["bf16_vs_fp32"]["mean_abs"]["ratio_ci95"][0] > 1.3
    assert pairs["fp16_vs_fp32"]["mean_abs"]["ratio"] == pytest.approx(1, abs=0.05)
    assert pairs["fp16_excess_fraction"]["mean_abs"]["value"] == pytest.approx(0, abs=0.1)
    assert pairs["bf16_b528_excess_fraction"]["mean_abs"]["value"] == pytest.approx(1, abs=0.1)
    slope = pairs["bf16_b528_vs_fp32"]["slope_within_sequences_per_1k"]
    assert slope["diff"] == pytest.approx(0.006, rel=0.15) and slope["diff_ci95"][0] > 0
    assert con["arms"]["fp16"]["share_outside_band"]["value"] >= 0
    rows = result["position_ratios"]["dec_vs_r1"]
    assert rows[-1]["bf16_over_fp32"] > rows[0]["bf16_over_fp32"]
    assert set(result["subsets"]) >= {"fp16/all", "bf16_b528/seed_43"}
    assert result["arms"]["bf16_b528"]["sequences"] == len(PROMPTS) * len(SEEDS)
    text = analysis.markdown({"mismatch": {MODEL: result}})
    assert "Excess fraction" in text and "bf16_b528" in text
    figure = tmp_path / "figure.png"
    analysis.plot({"mismatch": {MODEL: result}}, figure)
    assert figure.stat().st_size > 10_000


def test_combine_uses_each_g2b_arms_own_prefill() -> None:
    rng = np.random.default_rng(1)
    g2b = _per_token([_arm_seqs(rng, 1, 0), _arm_seqs(rng, 1, 0)], rng, g2b=True)
    g2b["d_pre16"] = (g2b["d_pre32"].astype(float) + 1.0).astype(np.float16)
    g2c = _per_token([_arm_seqs(rng, 1, 0), _arm_seqs(rng, 1, 0)], rng, g2b=False)
    data = analysis.combine(g2b, g2c)
    bf16 = data["arm_token"] == 1
    fp32 = data["arm_token"] == 0
    n_g2b = int(g2b["offsets"][-1])
    assert np.allclose(data["d_pre"][:n_g2b][fp32[:n_g2b]], g2b["d_pre32"][fp32[:n_g2b]])
    assert np.allclose(data["d_pre"][:n_g2b][bf16[:n_g2b]], g2b["d_pre16"][bf16[:n_g2b]])
    assert np.allclose(data["d_pre"][n_g2b:], g2c["d_pre"].astype(float))


def _write_jobs(tmp: Path, rng: np.random.Generator) -> tuple[Path, Path]:
    """A rollout job dir (both arms, prefill) and a teacher-forcing dir."""

    job = tmp / "job"
    tf = tmp / "tf"
    job.mkdir()
    tf.mkdir()
    merged = []
    for arm in gc.ARM_NAMES:
        worker = job / f"{MODEL}-{arm}"
        worker.mkdir()
        seqs = _arm_seqs(rng, 1.0, 0.0)[:4]
        for s in seqs:
            s["sid"] = gb.sequence_id(MODEL, arm, s["prompt"], s["seed"])
            s["arm"] = arm
        offsets = np.concatenate([[0], np.cumsum([len(s["ids"]) for s in seqs])])
        np.savez(
            worker / "tokens.npz",
            offsets=offsets,
            prompt_len=np.full(len(seqs), 100, np.int32),
            token_ids=np.concatenate([s["ids"] for s in seqs]).astype(np.int32),
            logp_decode=np.concatenate([s["r1"] + s["d"] for s in seqs]).astype(np.float32),
        )
        (worker / "sequences.json").write_text(
            json.dumps(
                {
                    "arm": arm,
                    "sequence_order": [s["sid"] for s in seqs],
                    "sequences": [
                        {"sequence_id": s["sid"], "finish_reason": "stop", "nonfinite_logprobs": 0}
                        for s in seqs
                    ],
                }
            )
        )
        # The prefill records its own order (reversed here) and offsets.
        rev = seqs[::-1]
        poff = np.concatenate([[0], np.cumsum([len(s["ids"]) for s in rev])])
        np.savez(
            job / f"prefill-{arm}.npz",
            offsets=poff,
            logp_prefill=np.concatenate([s["r1"] + 0.001 for s in rev]).astype(np.float32),
        )
        (job / f"prefill-{arm}.json").write_text(
            json.dumps({"sequence_order": [s["sid"] for s in rev]})
        )
        merged += seqs
    offsets = np.concatenate([[0], np.cumsum([len(s["ids"]) for s in merged])])
    r1 = np.concatenate([s["r1"] for s in merged])
    np.savez(
        tf / f"tf-{MODEL}.npz",
        offsets=offsets,
        prompt_len=np.full(len(merged), 100, np.int32),
        token_ids=np.concatenate([s["ids"] for s in merged]).astype(np.int32),
        logp_r1=r1.astype(np.float32),
        ent_r1=rng.uniform(0, 3, len(r1)).astype(np.float32),
        logp_r4=(r1 + 0.002).astype(np.float32),
        ent_r4=rng.uniform(0, 3, len(r1)).astype(np.float32),
    )
    (tf / f"tf-{MODEL}-sequences.json").write_text(
        json.dumps(
            [
                {
                    "sequence_id": s["sid"],
                    "arm": s["arm"],
                    "prompt_index": s["prompt"],
                    "seed": s["seed"],
                }
                for s in merged
            ]  # fmt: skip
        )
    )
    return job, tf


def test_pack_joins_by_sequence_id(tmp_path: Path) -> None:
    job, tf = _write_jobs(tmp_path, np.random.default_rng(3))
    packed = analysis.pack_model(MODEL, job, tf)
    assert packed["arm"].tolist() == [0] * 4 + [1] * 4
    assert np.allclose(packed["d_pre"].astype(float), 0.001, atol=1e-3)
    assert np.allclose(packed["d_r4"].astype(float), 0.002, atol=1e-3)
    assert np.abs(packed["d_dec"].astype(float)).mean() > 0.001
    data = dict(np.load(tf / f"tf-{MODEL}.npz"))
    data["token_ids"][5] += 1
    np.savez(tf / f"tf-{MODEL}.npz", **data)
    with pytest.raises(ValueError, match="tokens differ"):
        analysis.pack_model(MODEL, job, tf)


def test_termination_pairs_each_arm_with_both_references() -> None:
    def rec(p, s, n, f):
        return {"prompt_index": p, "seed": s, "completion_len": n, "finish_reason": f,
                "boxed_matches_reference": f == "stop", "tail_compress_ratio": 0.4}  # fmt: skip

    records = {
        "fp32": [rec(0, 42, 100, "stop"), rec(1, 42, 900, "stop"), rec(2, 42, 500, "length")],
        "bf16": [rec(0, 42, 400, "stop"), rec(1, 42, 300, "stop"),
                 rec(2, 42, 450, "cut_at_time_budget")],
        "fp16": [rec(0, 42, 100, "stop"), rec(1, 42, 950, "stop"), rec(2, 42, 600, "stop")],
    }  # fmt: skip
    t = analysis.termination(records)
    assert t["arms"]["bf16"]["cut_at_time_budget"] == 1 and t["arms"]["fp32"]["hit_cap"] == 1
    assert t["arms"]["fp16"]["ended_before"]["4096"] == 3
    p = t["paired"]["fp16_vs_fp32"]
    assert p["arm_ran_longer"] == 1 and p["ref_ran_longer"] == 1 and p["neither"] == 1
    assert t["paired"]["bf16_vs_fp32"]["arm_ran_longer"] == 1
    assert "bf16_b528_vs_fp32" not in t["paired"]


def test_committed_g2b_seed42_subsets_reproduce_g2b(tmp_path: Path) -> None:
    """G2b's committed seed-42 per-token subsets, read through this experiment's combine and
    statistics, give G2b's committed seed-42 dec-vs-r1 means."""

    ref = ROOT / "program" / "evidence" / "2026-10-15" / "g2b-state-dtype"
    committed = json.loads((ref / "analysis" / "analysis.json").read_text(encoding="utf-8"))
    _, raw = analysis.ab.load_per_token(ref / "data" / f"per-token-{MODEL}-seed42.npz")
    empty = {k: v[:0] if k != "offsets" else v[:1] for k, v in raw.items()}
    data = analysis.combine(raw, empty | {"d_pre": raw["d_pre32"][:0]})
    config = gc.load_config()
    settings = dict(config["analysis"]) | {"bootstrap_reps": 50}
    for code, arm in enumerate(("fp32", "bf16")):
        mask = data["arm_token"] == code
        block = analysis.ap.comparison_block(data, "dec", "r1", mask, settings)
        theirs = committed["mismatch"][MODEL]["subsets"][f"{arm}/seed_42"]["dec_vs_r1"]
        assert block["tokens"] == theirs["tokens"]
        assert block["mean_abs"] == pytest.approx(theirs["mean_abs"], rel=1e-9)
        assert block["k3"] == pytest.approx(theirs["k3"], rel=1e-9)


def test_report_survives_arms_without_shared_prompts(tmp_path: Path) -> None:
    """Smoke-sized new arms on prompts G2b never ran: no contrasts, but tables and figure."""

    rng = np.random.default_rng(5)
    g2b = _per_token([_arm_seqs(rng, 1, 0), _arm_seqs(rng, 1, 0.004)], rng, g2b=True)
    g2c = _per_token([_arm_seqs(rng, 1, 0), _arm_seqs(rng, 1, 0)], rng, g2b=False)
    g2c["prompt_index"] = (g2c["prompt_index"] + 30).astype(np.int16)
    data = analysis.combine(g2b, g2c)
    settings = dict(gc.load_config()["analysis"]) | {"bootstrap_reps": 50}
    result = analysis.analyze_model(data, settings)
    assert "arms" not in result["contrasts"]["dec_vs_r1"]
    assert "fp16 state" in analysis.markdown({"mismatch": {MODEL: result}})
    analysis.plot({"mismatch": {MODEL: result}}, tmp_path / "f.png")
