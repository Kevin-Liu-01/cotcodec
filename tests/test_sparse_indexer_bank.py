"""CPU equivalence of the K1 successor's batched bank with the v1 per-indexer path.

Every test runs the v1 code (``harness/sparse_indexer_torch.py`` and
``harness/sparse_indexer_k1_runtime.py``, unchanged) next to the bank on the
same inputs: forward, KL, gradients, per-indexer clipping and the Adam step in
float64, the chunked targets, and the exact selection rules.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from harness import sparse_indexer_bank as bank_mod  # noqa: E402
from harness import sparse_indexer_k1_runtime as rt  # noqa: E402
from harness import sparse_indexer_torch as sit  # noqa: E402

SMALL = sit.IndexerSpec(d_model=32, heads=2, dim=16, rope_dims=16)
KEYS18 = [rt.indexer_key(t, lr, s) for t in ("hs", "mp") for lr in rt.LEARNING_RATES
          for s in (42, 43, 44)]


def random_targets(length: int, heads: int = 3, seed: int = 0,
                   dtype: torch.dtype = torch.float64) -> dict:
    """v1 block targets of random causal probabilities (float64, zero-heavy rows)."""

    generator = torch.Generator().manual_seed(seed)
    logits = torch.randn(heads, length, length, generator=generator, dtype=dtype) * 3.0
    future = torch.arange(length)[None, :] > torch.arange(length)[:, None]
    probs = torch.softmax(logits.masked_fill(future[None], float("-inf")), dim=-1)
    return sit.block_targets(probs, torch.arange(length))


def test_bank_initialisation_is_v1_bit_for_bit() -> None:
    bank = bank_mod.LayerBank(SMALL, 5, KEYS18, "cpu")
    assert bank.keys == KEYS18 and [c.lr_tag for c in bank.cells] == ["3e-4", "1e-3", "3e-3"] * 2
    for cell, leaves in zip(bank.cells, bank.leaves, strict=True):
        for slot, seed in enumerate(cell.seeds):
            reference = dict(sit.BlockIndexer.initialised(SMALL, seed, 5, cell.target)
                             .named_parameters())
            for name in bank_mod.PARAM_NAMES:
                assert torch.equal(leaves[name][slot].detach(), reference[name].detach())
    # Learning rates share an initialisation; targets do not (registered pairing).
    assert torch.equal(bank.leaves[0]["wq"][0], bank.leaves[1]["wq"][0])
    assert not torch.equal(bank.leaves[0]["wq"][0], bank.leaves[3]["wq"][0])


@pytest.mark.parametrize(("spec", "length", "chunk", "sequences"), [
    (SMALL, 67, 16, 1),
    (SMALL, 67, 1024, 2),
    (sit.IndexerSpec(), 41, 16, 1),
])
def test_forward_gradients_clip_and_adam_match_v1_in_float64(spec, length, chunk,
                                                             sequences) -> None:
    generator = torch.Generator().manual_seed(11)
    hidden = torch.randn(length, spec.d_model, generator=generator, dtype=torch.float64)
    report = bank_mod.compare_with_v1(spec, 3, KEYS18, hidden, random_targets(length),
                                      device="cpu", dtype=torch.float64, row_chunk=chunk,
                                      sequences=sequences)
    assert report["loss_max_rel"] < 1e-12, report
    assert report["clip_norm_max_rel"] < 1e-12, report
    assert max(report["grad_max_rel_fro"].values()) < 1e-11, report
    assert max(report["param_after_step_max_rel_fro"].values()) < 1e-11, report
    assert report["adam_step_bitwise"] is True


def test_clipping_is_per_indexer_and_actually_clips() -> None:
    bank = bank_mod.LayerBank(SMALL, 0, KEYS18[:6], "cpu", dtype=torch.float64)
    scales = [0.01, 5.0, 300.0]
    for cell, leaves in zip(bank.cells, bank.leaves, strict=True):
        for name in bank_mod.PARAM_NAMES:
            grad = torch.ones_like(leaves[name])
            for slot in range(len(cell.seeds)):
                grad[slot] *= scales[slot]
            leaves[name].grad = grad
    norms = bank.clip_()
    total = sum(leaves.numel() // 3 for leaves in bank.leaves[0].values()) ** 0.5
    assert torch.allclose(norms, torch.tensor(scales * 2, dtype=torch.float64) * total)
    for leaves in bank.leaves:
        flat = torch.cat([leaves[n].grad.reshape(3, -1) for n in bank_mod.PARAM_NAMES], dim=1)
        after = torch.linalg.vector_norm(flat, dim=1)
        assert after[0] == pytest.approx(0.01 * total)  # below the clip: untouched
        assert after[1] == pytest.approx(1.0, rel=1e-6) and after[2] == pytest.approx(1.0,
                                                                                      rel=1e-6)


def test_slots_never_couple() -> None:
    # Changing one indexer's parameters or target leaves every other indexer's
    # loss and gradient bit-identical (no shared norm, state or reduction).
    length = 37
    generator = torch.Generator().manual_seed(3)
    hidden = torch.randn(length, SMALL.d_model, generator=generator, dtype=torch.float64)
    targets = random_targets(length)

    def provide(first: int, end: int) -> dict:
        return {k: targets[k][first:end, : end // 4] for k in ("hs", "mp", "valid")}

    def run(perturb: bool) -> tuple:
        bank = bank_mod.LayerBank(SMALL, 1, KEYS18, "cpu", dtype=torch.float64)
        params = bank.working_params()
        if perturb:
            with torch.no_grad():
                params["wq"][4] += 0.5
                params["gate_b"][4] -= 2.0
        kl = bank.accumulate_sequence(params, hidden, provide, grad_scale=1.0, row_chunk=8)
        return kl, {name: params[name].grad.clone() for name in bank_mod.PARAM_NAMES}

    base_kl, base = run(False)
    moved_kl, moved = run(True)
    others = [i for i in range(18) if i != 4]
    assert torch.equal(base_kl[others], moved_kl[others]) and base_kl[4] != moved_kl[4]
    for name in bank_mod.PARAM_NAMES:
        assert torch.equal(base[name][others], moved[name][others]), name


def test_multi_step_training_tracks_the_v1_bank_in_float64() -> None:
    # Three steps of v1's IndexerBank loop (per-indexer forward, loss / batch,
    # clip, Adam with warm-up) against the bank, with v1's chunked targets.
    length, steps, batch = 29, 3, 2
    generator = torch.Generator().manual_seed(5)
    hiddens = torch.randn(steps, batch, length, SMALL.d_model, generator=generator,
                          dtype=torch.float64)
    targets = [[random_targets(length, seed=10 * s + b) for b in range(batch)]
               for s in range(steps)]
    v1 = rt.IndexerBank.__new__(rt.IndexerBank)  # v1's bank, built in float64
    v1.spec, v1.layers, v1.keys, v1.device = SMALL, [2], KEYS18, torch.device("cpu")
    v1.indexers, v1.optimisers = {}, {}
    for key in KEYS18:
        target, lr_s, seed_s = key.split("|")
        indexer = sit.BlockIndexer.initialised(SMALL, int(seed_s), 2, target).double()
        v1.indexers[(2, key)] = indexer
        v1.optimisers[(2, key)] = torch.optim.Adam(indexer.parameters(), lr=float(lr_s),
                                                   betas=rt.ADAM_BETAS, eps=rt.ADAM_EPS,
                                                   weight_decay=0.0, foreach=False)
    bank = bank_mod.LayerBank(SMALL, 2, KEYS18, "cpu", dtype=torch.float64)
    rows = torch.arange(length)
    for step in range(steps):
        for key in KEYS18:
            indexer = v1.indexers[(2, key)]
            for b in range(batch):
                scores, valid = indexer(hiddens[step, b], rows)
                loss, _ = sit.kl_block_loss(targets[step][b][key.split("|")[0]], scores, valid)
                (loss / batch).backward()
            torch.nn.utils.clip_grad_norm_(indexer.parameters(), rt.GRAD_CLIP, foreach=False)
            optimiser = v1.optimisers[(2, key)]
            for group in optimiser.param_groups:
                group["lr"] = rt.learning_rate(step, v1.lr_of(key), 2)
            optimiser.step()
            optimiser.zero_grad(set_to_none=True)
        params = bank.working_params()
        for b in range(batch):
            target = targets[step][b]
            bank.accumulate_sequence(
                params, hiddens[step, b],
                lambda first, end, t=target: {k: t[k][first:end, : end // 4]
                                              for k in ("hs", "mp", "valid")},
                grad_scale=1.0 / batch, row_chunk=8)
        bank.adopt_grads(params)
        bank.clip_()
        bank.step(step, 2)
    reference = v1.state_tensors()
    mine = bank.state_tensors()
    assert set(mine) == set(reference)
    worst = max(float((mine[n].double() - reference[n].double()).abs().max()
                      / max(float(reference[n].double().abs().max()), 1e-300))
                for n in reference if "|step|" not in n)
    assert worst < 1e-9
    assert all(torch.equal(mine[n], reference[n]) for n in reference if "|step|" in n)


def test_state_round_trip_is_bitwise_and_uses_v1_names() -> None:
    bank = bank_mod.LayerBank(SMALL, 7, KEYS18, "cpu")
    params = bank.working_params()
    hidden = torch.randn(21, SMALL.d_model)
    targets = random_targets(21, dtype=torch.float32)
    bank.accumulate_sequence(params, hidden, lambda f, e: {k: targets[k][f:e, : e // 4]
                                                          for k in ("hs", "mp", "valid")},
                             grad_scale=1.0)
    bank.adopt_grads(params)
    bank.clip_()
    bank.step(0, 20)
    state = {name: tensor.clone() for name, tensor in bank.state_tensors().items()}
    assert "L07|hs|3e-4|42|exp_avg_sq|wq" in state and "L07|mp|3e-3|44|step|k_norm" in state
    fresh = bank_mod.LayerBank(SMALL, 7, KEYS18, "cpu")
    fresh.load_state(state)
    again = fresh.state_tensors()
    assert all(torch.equal(again[name], state[name]) for name in state)
    assert fresh.param_digests() == bank.param_digests()
    # A step count that differs between seeds of one cell is refused.
    state["L07|hs|3e-4|43|step|wq"] = state["L07|hs|3e-4|43|step|wq"] + 1
    with pytest.raises(bank_mod.BankContractError, match="different number of times"):
        fresh.load_state(state)


def test_truncated_chunk_targets_equal_v1_sequence_targets() -> None:
    generator = torch.Generator().manual_seed(9)
    length, chunk = 70, 16
    q = torch.randn(4, length, 8, generator=generator).bfloat16()
    k = torch.randn(2, length, 8, generator=generator).bfloat16()
    full = rt.sequence_targets(q, k, 0.35, chunk=chunk)
    provide = bank_mod.truncated_targets(q, k, 0.35)
    for first, end in bank_mod.chunk_bounds(length, chunk, 4):
        part = provide(first, end)
        width = end // 4
        assert torch.equal(part["valid"], full["valid"][first:end, :width])
        assert not bool(full["valid"][first:end, width:].any())
        assert float(full["hs"][first:end, width:].abs().sum()) == 0.0
        assert float(full["mp"][first:end, width:].abs().sum()) == 0.0
        for name in ("hs", "mp"):
            assert torch.allclose(part[name], full[name][first:end, :width], rtol=2e-6,
                                  atol=1e-9), name
    rows = torch.arange(5, 30)
    assert torch.equal(bank_mod.causal_probs(q[:, 5:30], k, rows, 0.35),
                       sit.head_probs_rows(q[:, 5:30], k, rows, 0.35))
    assert bank_mod.chunk_bounds(70, 16, 4)[0] == (3, 16)


def _v1_block(scores, valid, rows, n0, n1, k):
    chosen = sit.select_top_blocks(scores, valid, k)
    hits = sit.block_selection_recall(chosen, rows, n0, n1) * (n1 - n0)
    selected = (chosen >= 0).sum(dim=-1) * 4 + (rows + 1) % 4
    return hits.round().long(), sit.boundary_ties(scores, valid, k), int(selected.max())


@pytest.mark.parametrize("trial", range(6))
def test_block_selection_equals_v1_with_ties_and_signed_zeros(trial) -> None:
    generator = torch.Generator().manual_seed(100 + trial)
    n_rows, n_blocks, k = 9, 40, [5, 12, 39, 40, 64, 1][trial]
    rows = torch.arange(n_blocks * 4 - n_rows, n_blocks * 4) - (trial % 3) * 7
    valid = sit.complete_block_mask(rows, n_blocks)
    stack = []
    for s in range(5):
        raw = torch.randn(n_rows, n_blocks, generator=generator)
        if s == 0:
            raw = (raw * 2).round() / 2  # many exact ties
        if s == 1:
            raw = torch.where(raw > 0, torch.zeros_like(raw), -torch.zeros_like(raw))
        if s == 2:
            raw = torch.relu(raw) * torch.sign(torch.randn(n_rows, n_blocks,
                                                           generator=generator))
        stack.append(raw)
    scores = torch.stack(stack)
    n0, n1 = 37, 61
    result = bank_mod.select_blocks(scores[None], valid, rows, n0, n1, k)
    for s in range(scores.shape[0]):
        hits, ties, selected = _v1_block(scores[s], valid, rows, n0, n1, k)
        assert torch.equal(result.hits[0, s], hits), s
        assert int(result.ties[0, s]) == ties, s
        assert int(result.selected_max[0, s]) == selected, s


@pytest.mark.parametrize("trial", range(4))
def test_union_hits_equal_v1_union_topk_recall(trial) -> None:
    generator = torch.Generator().manual_seed(200 + trial)
    heads, length = 4, 90
    rows = torch.arange(length - 7, length) - trial * 10
    logits = torch.randn(heads, rows.numel(), length, generator=generator) * 6.0
    if trial % 2:
        logits = (logits * 0.5).round() * 40.0  # underflowing, exactly tied probabilities
    future = torch.arange(length)[None, :] > rows[:, None]
    probs = torch.softmax(logits.masked_fill(future[None], float("-inf")), dim=-1)
    n0, n1 = 3, 40
    big, small = bank_mod.union_hits(probs, rows, (16, 3), n0, n1)
    for value, k in ((big, 16), (small, 3)):
        reference = sit.union_topk_recall(probs, rows, k, n0, n1) * (n1 - n0)
        assert torch.equal(value, reference.round().long()), k
    huge, = bank_mod.union_hits(probs, rows, (500,), n0, n1)
    reference = sit.union_topk_recall(probs, rows, 500, n0, n1) * (n1 - n0)
    assert torch.equal(huge, reference.round().long())
    with pytest.raises(bank_mod.BankContractError, match="precede"):
        bank_mod.union_hits(probs, rows, (16,), n0, int(rows.min()) + 1)
    with pytest.raises(bank_mod.BankContractError, match="precede"):
        bank_mod.select_blocks(torch.zeros(rows.numel(), 30), torch.ones(rows.numel(), 30,
                                                                         dtype=torch.bool),
                               rows, n0, n1, 4, min_row=n1 - 1)


def test_row_means_use_v1_per_row_values() -> None:
    hits = torch.tensor([[3, 0, 7], [1, 1, 1]])
    expected = (hits.float() / 7.0).double().mean(dim=-1) * 100.0
    assert torch.equal(bank_mod.row_mean_percent(hits, 7), expected)
    rows = torch.arange(10, 30)
    assert torch.equal(bank_mod.tail_overlap(rows, 5, 28),
                       sit._tail_overlap(rows, 5, 28, 4))


def test_cells_require_contiguous_keys() -> None:
    cells = bank_mod.cells_of(["hs|1e-3|42", "hs|1e-3|43", "mp|3e-3|42"])
    assert [(c.target, c.lr_tag, c.seeds) for c in cells] == [("hs", "1e-3", (42, 43)),
                                                              ("mp", "3e-3", (42,))]
    with pytest.raises(bank_mod.BankContractError, match="contiguous"):
        bank_mod.cells_of(["hs|1e-3|42", "mp|1e-3|42", "hs|1e-3|43"])
    with pytest.raises(bank_mod.BankContractError, match="repeated"):
        bank_mod.cells_of(["hs|1e-3|42", "hs|1e-3|42"])


def test_stream_dev_kl_sums_in_float64_exactly_as_v1() -> None:
    # Review finding: v2 summed the 64 per-sequence float32 losses in float32 on the
    # device; v1 adds float(loss) in Python floats. Widening before the sum gives
    # v1's float64 sums and means bit for bit, so a 1 percent LR tie cannot flip.
    from harness import sparse_indexer_k1_runtime_v2 as rt2

    generator = torch.Generator().manual_seed(11)
    sequences = [torch.tensor([1.0, 3.0, 0.5], dtype=torch.float32)]
    sequences += [(torch.rand(3, generator=generator) * 1e-7).to(torch.float32)
                  for _ in range(63)]
    sums: dict = {7: None}
    for values in sequences:
        rt2.add_sequence_kl(sums, {7: values})
    v1 = [0.0, 0.0, 0.0]
    for values in sequences:
        for index, loss in enumerate(values):
            v1[index] += float(loss)
    means = rt2.mean_sequence_kl(sums[7], len(sequences))
    assert means == [value / len(sequences) for value in v1]  # exactly, not approximately
    narrow = torch.stack(sequences).cumsum(0, dtype=torch.float32)[-1]  # the old fp32 sum
    assert [float(v) for v in narrow / len(sequences)] != means
    assert rt2.mean_sequence_kl(None, 4) == []
