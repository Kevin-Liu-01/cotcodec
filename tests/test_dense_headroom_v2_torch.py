"""v2's evaluation equals v1's bit for bit (skip without the architecture extra)."""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from harness import dense_headroom_data as dhd  # noqa: E402

dhd.block_gpu_only_kernels()

from harness import dense_headroom_torch_v2 as dht2  # noqa: E402
from scripts import run_dense_headroom_precheck_doctor as d1  # noqa: E402
from scripts import run_dense_headroom_precheck_v2_doctor as d2  # noqa: E402


def test_every_unit_field_equals_v1_bit_for_bit(tmp_path: Path) -> None:
    result = d2.case_equivalence(tmp_path)
    assert result["status"] == "PASS", result["failures"]
    assert result["units_compared"] == 12


def test_clone_cache_copies_every_tensor_and_shares_none(tmp_path: Path) -> None:
    from transformers import DynamicCache

    from harness import sparse_indexer_torch as sit

    model = sit.load_teacher(d1.make_tiny_hybrid(tmp_path / "hybrid"), "cpu")
    cache = DynamicCache(config=model.config)
    with torch.no_grad():
        model(input_ids=torch.arange(3, 40)[None], use_cache=True, past_key_values=cache)
    twin = dht2.clone_cache(cache)
    deep = copy.deepcopy(cache)

    def tensors(obj, prefix=""):
        out = {}
        for name, value in vars(obj).items():
            if isinstance(value, torch.Tensor):
                out[prefix + name] = value
            elif isinstance(value, dict):
                for key, item in value.items():
                    if isinstance(item, torch.Tensor):
                        out[f"{prefix}{name}[{key}]"] = item
        return out

    assert len(twin.layers) == len(cache.layers)
    for index, (a, b, c) in enumerate(zip(cache.layers, twin.layers, deep.layers, strict=True)):
        assert type(a) is type(b) and a is not b
        ta, tb, tc = tensors(a), tensors(b), tensors(c)
        assert set(ta) == set(tb) == set(tc) and ta, index
        for key in ta:
            assert torch.equal(ta[key], tb[key]) and torch.equal(tb[key], tc[key])
            assert ta[key].data_ptr() != tb[key].data_ptr()
            assert ta[key].stride() == tb[key].stride()
            assert getattr(ta[key], "__dict__", {}) == getattr(tb[key], "__dict__", {})
        for name, value in vars(a).items():
            if isinstance(value, dict):
                assert vars(b)[name] is not value and vars(b)[name].keys() == value.keys()


def test_the_timer_records_components_without_changing_values(tmp_path: Path) -> None:
    from harness import dense_headroom_stats as dhs
    from harness import sparse_indexer_torch as sit

    model = sit.load_teacher(d1.make_tiny_hybrid(tmp_path / "hybrid"), "cpu")
    torch.use_deterministic_algorithms(True, warn_only=True)
    try:
        rng = np.random.default_rng(3)
        tokens = rng.integers(3, d1.HYBRID_VOCAB - 1, size=120).astype(np.uint32)
        names = dhs.selector_names([42, 43, 44])
        kwargs = dict(layers=[1, 3], k_blocks=4, fixed_k_blocks=4,
                      scaling=dht2.scaling_of(model.config), do_select=True, do_mc=True,
                      options=[np.asarray([5, 6, 7], dtype=np.uint32)] * 4,
                      option_bytes=[3, 3, 3, 3], answer=0,
                      lex_blocks=np.zeros(30, dtype=np.float32), seeds=[42, 43, 44],
                      unit_key="c0-q0", names=names, hybrid=True, device=torch.device("cpu"))
        timer = dht2.UnitTimer(torch.device("cpu"))
        timed = dht2.evaluate_unit(model, tokens, 100, 110, 20, 40, timer=timer, **kwargs)
        plain = dht2.evaluate_unit(model, tokens, 100, 110, 20, 40, **kwargs)
    finally:
        torch.use_deterministic_algorithms(False)
    assert not d2._unit_fields_equal(timed, plain)
    parts = timer.as_dict()
    assert {"inputs", "prefill_forward", "select", "mc_cache_copy",
            "mc_option_forward"} <= set(parts)
