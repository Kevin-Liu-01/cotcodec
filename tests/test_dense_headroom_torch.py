"""Torch pieces of the dense headroom pre-check (skip without the architecture extra)."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from harness import dense_headroom_torch as dht  # noqa: E402
from scripts import run_dense_headroom_precheck_doctor as doctor  # noqa: E402


def test_expected_topk_hits_matches_enumeration() -> None:
    rng = np.random.default_rng(5)
    for _ in range(50):
        n_blocks, k = int(rng.integers(4, 9)), int(rng.integers(1, 6))
        scores = torch.as_tensor(rng.integers(0, 3, size=(1, n_blocks)).astype(np.float32))
        valid = torch.as_tensor(rng.random((1, n_blocks)) < 0.85)
        cover = torch.as_tensor(rng.integers(0, 5, size=n_blocks))
        hits, _ = dht.expected_topk_hits(scores, valid, k, cover, torch.zeros(1))
        ids = [b for b in range(n_blocks) if bool(valid[0, b])]
        if len(ids) <= k:
            expected = sum(int(cover[b]) for b in ids)
        else:
            outcomes = []
            values = sorted((float(scores[0, b]) for b in ids), reverse=True)
            kth = values[k - 1]
            above = [b for b in ids if float(scores[0, b]) > kth]
            tie = [b for b in ids if float(scores[0, b]) == kth]
            for combo in itertools.combinations(tie, k - len(above)):
                outcomes.append(sum(int(cover[b]) for b in above + list(combo)))
            expected = float(np.mean(outcomes))
        assert float(hits[0]) == pytest.approx(expected)


def test_layer_kinds() -> None:
    from transformers import Qwen3_5TextConfig, Qwen3Config

    hybrid = Qwen3_5TextConfig(num_hidden_layers=4, layer_types=[
        "linear_attention", "full_attention", "linear_attention", "full_attention"])
    assert dht.attention_layers(hybrid) == [1, 3] and dht.is_hybrid(hybrid)
    plain = Qwen3Config(num_hidden_layers=3)
    assert dht.attention_layers(plain) == [0, 1, 2]
    assert not dht.is_hybrid(plain)


def test_selectors_match_k1_v1(tmp_path) -> None:
    result = doctor.case_selectors(tmp_path)
    assert result["status"] == "PASS", result["failures"]


def test_cached_option_scores_equal_a_full_forward(tmp_path) -> None:
    result = doctor.case_multiple_choice(tmp_path)
    assert result["status"] == "PASS", result["failures"]
