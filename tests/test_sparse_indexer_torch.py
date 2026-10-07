from __future__ import annotations

import math

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from harness import sparse_indexer_torch as sit  # noqa: E402
from scripts import run_sparse_indexer_k1_doctor as doctor  # noqa: E402


def test_capture_equals_eager_including_kv_cache(tmp_path) -> None:
    result = doctor.case_capture_vs_eager(tmp_path)
    assert all(result["gates"].values()), result


def test_targets_equal_numpy_reference() -> None:
    result = doctor.case_targets_vs_numpy()
    assert all(result["gates"].values()), result


def test_selection_union_and_random_equal_brute_force() -> None:
    result = doctor.case_selection_brute_force()
    assert all(result["gates"].values()), result


def test_indexer_gradient_matches_finite_differences() -> None:
    result = doctor.case_gradient_check()
    assert all(result["gates"].values()), result


def test_mp_is_qsa_eq17_not_a_head_max() -> None:
    probs = torch.zeros(2, 8, 8, dtype=torch.float64)
    rows = torch.arange(8)
    for i in range(8):
        probs[0, i, : i + 1] = 1.0 / (i + 1)
        probs[1, i, i] = 1.0
    row7 = sit.block_targets(probs, rows, include_hm=True)
    head_sum = probs[:, 7].sum(0) / 2.0
    expected_mp = head_sum.reshape(2, 4).amax(-1)
    expected_mp = expected_mp / expected_mp.sum()
    assert torch.allclose(row7["mp"][7], expected_mp)
    expected_hm = probs[:, 7].amax(0).reshape(2, 4).sum(-1)
    assert torch.allclose(row7["hm"][7], expected_hm / expected_hm.sum())


def test_complete_blocks_and_tail_recall() -> None:
    rows = torch.tensor([2, 3, 9])
    mask = sit.complete_block_mask(rows, 3)
    assert mask.tolist() == [[False, False, False], [True, False, False], [True, True, False]]
    chosen = torch.tensor([[0, 1, -1]])
    recall = sit.block_selection_recall(chosen, torch.tensor([13]), 2, 6)
    assert float(recall[0]) == pytest.approx(1.0)
    with pytest.raises(sit.TorchContractError):
        sit.block_selection_recall(chosen, torch.tensor([4]), 2, 6)


def test_select_pads_and_counts_boundary_ties() -> None:
    scores = torch.tensor([[1.0, 1.0, 1.0, 0.5]])
    valid = torch.tensor([[True, True, True, False]])
    assert sit.select_top_blocks(scores, valid, 5).tolist() == [[0, 1, 2, -1, -1]]
    assert sit.boundary_ties(scores, valid, 2) == 1
    assert sit.boundary_ties(torch.tensor([[3.0, 2.0, 1.0]]), torch.ones(1, 3, dtype=bool), 2) == 0


def test_kl_loss_is_zero_at_the_target_and_positive_elsewhere() -> None:
    target = torch.tensor([[0.5, 0.5, 0.0]], dtype=torch.float64)
    valid = torch.tensor([[True, True, False]])
    exact = torch.log(torch.tensor([[0.5, 0.5, 1.0]], dtype=torch.float64))
    loss, rows = sit.kl_block_loss(target, exact.masked_fill(~valid, float("-inf")), valid)
    assert rows == 1 and float(loss) == pytest.approx(0.0, abs=1e-12)
    worse, _ = sit.kl_block_loss(target, torch.tensor([[2.0, 0.0, float("-inf")]],
                                                      dtype=torch.float64), valid)
    assert float(worse) > 0


def test_ratio_retention_and_param_count() -> None:
    assert sit.ratio_retention(50.0, 90.0, 10.0) == pytest.approx(0.5)
    assert math.isnan(sit.ratio_retention(50.0, 10.0, 10.0))
    assert sit.indexer_parameter_count() == 659_716


def test_init_is_paired_across_learning_rates_and_distinct_across_targets() -> None:
    spec = sit.IndexerSpec(d_model=16, heads=2, dim=8, rope_dims=8)
    a = sit.BlockIndexer.initialised(spec, 42, 3, "hs")
    b = sit.BlockIndexer.initialised(spec, 42, 3, "hs")
    c = sit.BlockIndexer.initialised(spec, 42, 3, "mp")
    assert torch.equal(a.wq, b.wq) and not torch.equal(a.wq, c.wq)
    assert torch.equal(a.gate_w, torch.zeros_like(a.gate_w))
    assert torch.equal(a.gate_b, torch.ones_like(a.gate_b))


def test_indexer_scores_are_block_causal() -> None:
    spec = sit.IndexerSpec(d_model=16, heads=2, dim=8, rope_dims=8)
    indexer = sit.BlockIndexer.initialised(spec, 1, 0, "hs")
    hidden = torch.randn(20, 16)
    scores, valid = indexer(hidden, torch.arange(20))
    assert torch.isinf(scores[~valid]).all() and torch.isfinite(scores[valid]).all()
    assert valid[7].tolist()[:3] == [True, True, False]


def test_registered_layer_shards_and_seed_derivation() -> None:
    shards = sit.balanced_layer_shards(28, 4)
    assert [s[0] for s in shards] == [0, 8, 15, 22] and sum(len(s) for s in shards) == 28
    assert sit.derive_seed("a", 1) == sit.derive_seed("a", 1) != sit.derive_seed("a", 2)


def test_head_probs_rows_rejects_bad_shapes() -> None:
    with pytest.raises(sit.TorchContractError):
        sit.head_probs_rows(torch.zeros(3, 2, 4), torch.zeros(2, 5, 4), torch.arange(2), 0.5)
    probs = sit.head_probs_rows(torch.randn(4, 2, 8), torch.randn(2, 5, 8),
                                torch.tensor([1, 4]), 0.3)
    assert torch.allclose(probs.sum(-1), torch.ones(4, 2))
    assert float(probs[:, 0, 2:].abs().max()) == 0.0


def test_state_digest_is_bitwise() -> None:
    tensor = torch.tensor([1.0, 2.0])
    assert sit.state_digest({"a": tensor}) == sit.state_digest({"a": tensor.clone()})
    assert sit.state_digest({"a": tensor}) != sit.state_digest({"a": tensor + 1e-7})
    _ = np
