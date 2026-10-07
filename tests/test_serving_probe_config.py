from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from harness.serving_probe.config import (
    ProbeConfigError,
    bind_seeds,
    check_pins,
    load_config,
    parse_weight_pins,
    render_engine_flags,
    validate_config,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT_ROOT / "experiments" / "serving" / "serving-throughput-probe-v1.yaml"
PIN = "a" * 64 + ":" + "b" * 64


def _raw() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _validate(raw: dict):
    return validate_config(raw, path=CONFIG, sha256="0" * 64)


def test_live_contract_loads_and_pins_every_identity() -> None:
    config = load_config(CONFIG)
    assert config.experiment_id == "serving-throughput-probe-v1"
    assert config.primary_seeds == (42, 43, 44)
    assert config.preregistration == "program/preregistrations/serving-throughput-probe-v1.md"
    variants = config.section("vllm")["image_variants"]
    assert variants["cu129"]["base_image"].endswith(
        "b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f"
    )
    assert variants["cu129"]["env"]["VLLM_ENABLE_CUDA_COMPATIBILITY"] == "0"
    assert variants["cu130"]["env"]["VLLM_ENABLE_CUDA_COMPATIBILITY"] == "1"
    assert set(config.jobs) == {"a", "b", "c"}
    assert config.jobs["a"].allocation_minutes == 40
    assert config.jobs["b"].allocation_minutes == 20
    assert config.jobs["c"].allocation_minutes == 30


def test_job_structure_matches_the_preregistered_order() -> None:
    config = load_config(CONFIG)
    job_a = config.job("a")
    real, control = job_a.phases
    assert [p.point_id for p in real.points] == [
        "a-smoke",
        "a1a",
        "r1",
        "r3",
        "r4",
        "a1b",
        "r2",
        "a1c",
        "f1",
        "a2",
        "d8",
        "a6",
    ]
    assert control.engine.load_format == "dummy" and control.engine.model == "qwen3.5-9b"
    assert control.reserve_minutes == 9
    assert [p.point_id for p in control.points] == ["x1-smoke", "x1-a1", "x1-r1"]
    assert job_a.pinned_models() == []
    assert config.job("b").pinned_models() == ["qwen3-8b"]
    assert config.job("c").pinned_models() == ["qwen3.5-27b-fp8", "qwen3.5-35b-a3b-fp8"]
    assert config.job("b").mode == "offline"
    a1_seeds = [config.points[name].seed for name in ("a1a", "a1b", "a1c")]
    b1_seeds = [config.points[name].seed for name in ("b1a", "b1b", "b1c")]
    assert a1_seeds == b1_seeds == list(config.primary_seeds)


def test_controls_reuse_the_compared_points_exactly() -> None:
    config = load_config(CONFIG)
    points = config.points
    for control, reference in (("x1-a1", "a1a"), ("x1-r1", "r1"), ("f1", "a1a")):
        assert points[control].get("control_of") == reference
        assert points[control].seed == points[reference].seed
        diff = {
            key
            for key in set(points[control].params) | set(points[reference].params)
            if points[control].get(key) != points[reference].get(key)
        }
        assert diff <= {"control_of", "image_kind"}
    assert points["f1"]["image_kind"] == "png-rendered"
    assert points["a1a"]["image_kind"] == "jpeg-random"


def test_server_argv_has_no_speculative_decoding_and_prefix_caching_on() -> None:
    config = load_config(CONFIG)
    argv = config.engines["a-real"].server_argv(
        "/model-cache/cotcodec-models/qwen3.5-9b", host="127.0.0.1", port=8000, served_name="m"
    )
    joined = " ".join(argv)
    assert "--enable-prefix-caching" in argv
    assert "--gpu-memory-utilization 0.9" in joined
    assert "--max-model-len 65536" in joined
    assert "--load-format auto" in joined
    assert "speculative" not in joined and "mtp" not in joined.lower()
    assert '{"image":{"count":20,"height":1080,"width":1920},"video":0}' in argv
    dummy = config.engines["a-dummy"].server_argv("/m", host="h", port=1, served_name="m")
    assert dummy[dummy.index("--load-format") + 1] == "dummy"
    assert config.engines["b-offline"].offline_kwargs()["load_format"] == "dummy"
    assert config.engines["b-offline"].offline_kwargs()["max_model_len"] == 32768


def test_render_engine_flags_booleans_and_order() -> None:
    assert render_engine_flags({"enable_prefix_caching": False, "seed": 1}) == [
        "--seed",
        "1",
        "--no-enable-prefix-caching",
    ]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda raw: raw["engines"]["a-real"]["flags"].__setitem__("speculative_config", {}),
            "banned",
        ),
        (
            lambda raw: raw["engines"]["b-offline"]["flags"].__setitem__("kv_cache_dtype", "fp8"),
            "not admitted",
        ),
        (
            lambda raw: raw["engines"]["a-real"]["flags"].__setitem__(
                "enable_prefix_caching", False
            ),
            "prefix caching",
        ),
        (
            lambda raw: raw["engines"]["a-real"]["flags"].__setitem__(
                "gpu_memory_utilization", 0.99
            ),
            "gpu_memory_utilization",
        ),
        (lambda raw: raw["engines"]["b-offline"].__setitem__("load_format", "auto"), "real-weight"),
        (
            lambda raw: raw["engines"]["a-dummy"].__setitem__("model", "qwen3-0.6b-base"),
            "admission token",
        ),
        (lambda raw: raw["jobs"]["a"]["phases"][0]["points"].append("a1a"), "scheduled twice"),
        (
            lambda raw: raw["jobs"]["a"]["phases"][0]["points"].remove("a-smoke"),
            "start with its smoke",
        ),
        (
            lambda raw: raw["jobs"]["b"]["phases"][0]["points"].append("a1a"),
            "cannot run on offline",
        ),
        (lambda raw: raw.__setitem__("primary_seeds", [42, 42, 43]), "primary_seeds"),
        (lambda raw: raw["points"]["r1"].__setitem__("harness", "h3"), "harness"),
        (lambda raw: raw["points"]["a1a"].__setitem__("image_kind", "webp"), "image_kind"),
        (
            lambda raw: raw["jobs"]["a"]["phases"][1].__setitem__("reserve_minutes", 40),
            "reserves exceed",
        ),
        (
            lambda raw: raw["vllm"]["image_variants"]["cu129"].__setitem__(
                "base_image", "vllm/vllm-openai:latest"
            ),
            "digest",
        ),
    ],
)
def test_contract_tampering_fails_closed(mutate, message: str) -> None:
    raw = copy.deepcopy(_raw())
    for engine in raw["engines"].values():
        engine["flags"] = copy.deepcopy(engine["flags"])
    mutate(raw)
    with pytest.raises(ProbeConfigError, match=message):
        _validate(raw)


def test_seed_binding_is_exact() -> None:
    config = load_config(CONFIG)
    assert bind_seeds(config, [42, 43, 44]) == (42, 43, 44)
    for wrong in ([42, 43], [44, 43, 42], [42, 43, 44, 45]):
        with pytest.raises(ProbeConfigError, match="differ"):
            bind_seeds(config, wrong)


def test_weight_pins_parse_and_must_cover_the_job() -> None:
    config = load_config(CONFIG)
    pins = parse_weight_pins([f"qwen3-8b={PIN}"])
    assert pins == {"qwen3-8b": ("a" * 64, "b" * 64)}
    check_pins(config.job("b"), pins)
    with pytest.raises(ProbeConfigError, match="needs weight pins"):
        check_pins(config.job("c"), pins)
    with pytest.raises(ProbeConfigError, match="needs weight pins"):
        check_pins(config.job("a"), pins)
    for bad in ("qwen3-8b", "qwen3-8b=abc:def", f"Qwen/Qwen3-8B={PIN}"):
        with pytest.raises(ProbeConfigError, match="weight pin"):
            parse_weight_pins([bad])
    with pytest.raises(ProbeConfigError, match="repeated"):
        parse_weight_pins([f"qwen3-8b={PIN}", f"qwen3-8b={PIN}"])
