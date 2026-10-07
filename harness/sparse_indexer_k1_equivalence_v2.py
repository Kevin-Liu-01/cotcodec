"""Device equivalence check of the K1 successor's bank against v1's per-indexer path.

The CPU tests (``tests/test_sparse_indexer_bank.py``) and the v2 doctor prove
the bank equal to v1's per-indexer code in float64. On an H100 the indexer runs
in fp32 with TF32 matmuls (registered design decision 25), where two
implementations of the same function differ by accumulation order and by TF32
input rounding flips. ``device_check`` measures those differences on the real
teacher's activations at the registered shapes and gates them against
registered tolerances; the throughput probe runs it before any timing, and
``tests/test_sparse_indexer_bank_gpu.py`` runs it inside the image when a GPU
is visible.

Gates (``TOLERANCES``):

* loss, clip norm and gradients of the 18 registered indexers of one layer,
  against v1's per-indexer forward, ``kl_block_loss`` and ``clip_grad_norm_``
  on the same targets (the parameters after one Adam step are reported);
* the Adam step on identical clipped gradients and states (bitwise is
  reported; the gate allows float32 rounding);
* changing one indexer leaves every other indexer's KL and gradients bit-identical;
* chunked targets against v1's ``sequence_targets`` (and no mass in a dropped block);
* block selection and the U/U_k union on the device against v1's functions on
  the CPU (the registered tie rule), exactly;
* one evaluation unit against v1's evaluation loop: the dense selectors, U,
  U_k and the random baseline within 1e-3 recall points (the indexer columns
  are reported).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
import torch

from harness import sparse_indexer_bank as skb
from harness import sparse_indexer_k1_runtime as rt
from harness import sparse_indexer_torch as sit

TOLERANCES: dict[str, float] = {
    "loss_max_rel": 1e-3,
    "clip_norm_max_rel": 1e-2,
    "grad_max_rel_fro": 1e-2,
    "adam_step_max_rel": 1e-6,
    "targets_max_rel": 1e-4,
    "dense_recall_points": 1e-3,
}
# The parameters after one Adam step are reported, not gated, on the device:
# Adam's first step is about lr x sign(gradient), so a TF32 rounding difference
# in a near-zero gradient element flips that element's whole update, and the
# gate W_w starts at zero, so its post-step value is that update alone. The step
# itself is gated on identical inputs ("adam_step_max_rel") and the gradients
# are gated ("grad_max_rel_fro"); in float64 the post-step parameters are gated
# at 1e-11 (tests/test_sparse_indexer_bank.py, the v2 doctor).
CHECK_LAYER = 15  # a layer of the binding shard (layers 15-21)


def registered_keys(seeds: tuple[int, ...] = (42, 43, 44)) -> list[str]:
    return [rt.indexer_key(t, lr, s) for t in sit.TRAINED_TARGETS for lr in rt.LEARNING_RATES
            for s in seeds]


def _max_rel(a: torch.Tensor, b: torch.Tensor) -> float:
    a64, b64 = a.detach().double().cpu(), b.detach().double().cpu()
    scale = float(b64.abs().max()) if b64.numel() else 0.0
    diff = float((a64 - b64).abs().max()) if b64.numel() else 0.0
    return diff / scale if scale > 0 else diff


def adam_check(spec: sit.IndexerSpec, layer: int, keys: list[str],
               device: torch.device) -> dict[str, Any]:
    """Stacked Adam against per-indexer Adam on identical random gradients, 3 steps."""

    generator = torch.Generator().manual_seed(7)
    bank = skb.LayerBank(spec, layer, keys, device)
    reference = {}
    for key in keys:
        target, lr_tag, seed = key.split("|")
        indexer = sit.BlockIndexer.initialised(spec, int(seed), layer, target).to(device)
        reference[key] = (indexer, torch.optim.Adam(indexer.parameters(), lr=float(lr_tag),
                                                    betas=rt.ADAM_BETAS, eps=rt.ADAM_EPS,
                                                    weight_decay=0.0, foreach=False))
    worst, bitwise = 0.0, True
    for step in range(3):
        grads = {key: {name: (torch.randn(p.shape, generator=generator) * 10.0 ** (step - 1)
                              ).to(device) for name, p in reference[key][0].named_parameters()}
                 for key in keys}
        for key in keys:
            indexer, optimiser = reference[key]
            for name, param in indexer.named_parameters():
                param.grad = grads[key][name].clone()
            for group in optimiser.param_groups:
                group["lr"] = rt.learning_rate(step, float(key.split("|")[1]), 20)
            optimiser.step()
        for cell, leaves in zip(bank.cells, bank.leaves, strict=True):
            for name in skb.PARAM_NAMES:
                leaves[name].grad = torch.stack([grads[key][name] for key in cell.indexer_keys()])
        bank.step(step, 20)
        for cell, leaves in zip(bank.cells, bank.leaves, strict=True):
            for slot, key in enumerate(cell.indexer_keys()):
                params = dict(reference[key][0].named_parameters())
                for name in skb.PARAM_NAMES:
                    mine, theirs = leaves[name][slot].detach(), params[name].detach()
                    bitwise &= bool(torch.equal(mine, theirs))
                    worst = max(worst, _max_rel(mine, theirs))
    return {"adam_step_max_rel": worst, "adam_step_bitwise": bitwise}


def independence_check(spec: sit.IndexerSpec, layer: int, keys: list[str], hidden: torch.Tensor,
                       provide: Callable[[int, int], Mapping[str, torch.Tensor]]
                       ) -> dict[str, Any]:
    def run(perturb: bool) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        bank = skb.LayerBank(spec, layer, keys, hidden.device)
        params = bank.working_params()
        if perturb:
            with torch.no_grad():
                params["wq"][4] += 0.05
                params["gate_b"][4] -= 0.5
        kl = bank.accumulate_sequence(params, hidden, provide, grad_scale=1.0)
        return kl, {name: params[name].grad for name in skb.PARAM_NAMES}

    base_kl, base = run(False)
    moved_kl, moved = run(True)
    others = [i for i in range(len(keys)) if i != 4]
    return {"other_losses_bitwise": bool(torch.equal(base_kl[others], moved_kl[others])),
            "perturbed_loss_moves": bool(base_kl[4] != moved_kl[4]),
            "other_gradients_bitwise": all(bool(torch.equal(base[n][others], moved[n][others]))
                                           for n in skb.PARAM_NAMES)}


def selection_check(device: torch.device) -> dict[str, Any]:
    """Device selection against v1's functions run on the CPU (the registered rule)."""

    mismatches = []
    for trial, k in enumerate([256, 255, 300, 1]):
        generator = torch.Generator().manual_seed(300 + trial)
        n_rows, n_blocks = 34, 2056
        rows = torch.arange(n_blocks * 4 - n_rows, n_blocks * 4)
        valid = sit.complete_block_mask(rows, n_blocks)
        raw = torch.randn(4, n_rows, n_blocks, generator=generator)
        raw[0] = (raw[0] * 4).round() / 4
        raw[1] = torch.where(raw[1] > 0, torch.zeros_like(raw[1]), -torch.zeros_like(raw[1]))
        raw[2] = torch.relu(raw[2]) * torch.sign(torch.randn(n_rows, n_blocks,
                                                             generator=generator))
        result = skb.select_blocks(raw[None].to(device), valid.to(device), rows.to(device),
                                   4000, 4150, k)
        for s in range(raw.shape[0]):
            chosen = sit.select_top_blocks(raw[s], valid, k)
            hits = (sit.block_selection_recall(chosen, rows, 4000, 4150) * 150).round().long()
            if not (torch.equal(result.hits[0, s].cpu(), hits)
                    and int(result.ties[0, s]) == sit.boundary_ties(raw[s], valid, k)):
                mismatches.append(f"blocks k={k} selector {s}")
        logits = torch.randn(16, n_rows, n_blocks * 4, generator=generator) * 8.0
        future = torch.arange(n_blocks * 4)[None, :] > rows[:, None]
        probs = torch.softmax(logits.masked_fill(future[None], float("-inf")), dim=-1)
        big, small = skb.union_hits(probs.to(device), rows.to(device), (1024, 64), 4000, 4150)
        for value, width in ((big, 1024), (small, 64)):
            reference = (sit.union_topk_recall(probs, rows, width, 4000, 4150) * 150
                         ).round().long()
            if not torch.equal(value.cpu(), reference):
                mismatches.append(f"union k={width}")
    return {"selection_exact": not mismatches, "selection_mismatches": mismatches}


def device_check(teacher: Any, device: torch.device, *, profile: rt.Profile,
                 length: int = 8192, seed: int = 42, layer: int = CHECK_LAYER,
                 unit_rows: int = 34, unit_context: int = 8192) -> dict[str, Any]:
    """All registered device gates on one synthetic sequence through the real teacher."""

    from harness import sparse_indexer_k1_runtime_v2 as rt2

    started = time.perf_counter()
    sit.set_determinism(allow_tf32=True)
    config = teacher.config
    n_layers = int(config.num_hidden_layers)
    layer = min(layer, n_layers - 1)
    scaling = rt2.teacher_scaling(config)
    spec = sit.IndexerSpec(d_model=int(config.hidden_size))
    rng = np.random.default_rng(seed)
    tokens = rng.integers(0, min(int(config.vocab_size), sit.SINK_TOKEN_ID), size=length)
    tokens[0] = sit.SINK_TOKEN_ID if int(config.vocab_size) > sit.SINK_TOKEN_ID else 1
    ids = torch.as_tensor(tokens, dtype=torch.long, device=device)[None]
    with sit.CaptureSession(teacher, [layer]) as cap, torch.no_grad():
        teacher.model(input_ids=ids, use_cache=False)
        q, k, hidden = cap.query[layer][0], cap.key[layer][0], cap.hidden[layer][0]
    keys = registered_keys()
    full = rt.sequence_targets(q, k, scaling)
    report: dict[str, Any] = {"layer": layer, "length": length, "slots": len(keys),
                              "device": str(device), "tolerances": TOLERANCES}
    path = skb.compare_with_v1(spec, layer, keys, hidden, full, device=device,
                               dtype=torch.float32)
    report["indexer_path"] = path
    provide = skb.truncated_targets(q, k, scaling)
    worst, dropped = 0.0, 0.0
    for first, end in skb.chunk_bounds(length, skb.ROW_CHUNK, spec.block_size):
        part = provide(first, end)
        width = end // spec.block_size
        for name in ("hs", "mp"):
            worst = max(worst, _max_rel(part[name], full[name][first:end, :width]))
            dropped = max(dropped, float(full[name][first:end, width:].abs().sum()))
    report["targets"] = {"targets_max_rel": worst, "dropped_block_mass": dropped}
    report["adam"] = adam_check(spec, layer, keys, device)
    report["independence"] = independence_check(spec, layer, keys, hidden, provide)
    report["selection"] = selection_check(device)
    report["eval_unit"] = eval_unit_check(teacher, device, spec, scaling, rng, unit_rows,
                                          profile=profile, context=unit_context)
    gates = {
        "loss": path["loss_max_rel"] <= TOLERANCES["loss_max_rel"],
        "clip_norm": path["clip_norm_max_rel"] <= TOLERANCES["clip_norm_max_rel"],
        "gradients": max(path["grad_max_rel_fro"].values()) <= TOLERANCES["grad_max_rel_fro"],
        "adam_step": report["adam"]["adam_step_max_rel"] <= TOLERANCES["adam_step_max_rel"],
        "targets": worst <= TOLERANCES["targets_max_rel"] and dropped == 0.0,
        "independence": all(report["independence"].values()),
        "selection": report["selection"]["selection_exact"],
        "eval_unit_dense": report["eval_unit"]["dense_max_abs_points"]
        <= TOLERANCES["dense_recall_points"],
    }
    report["gates"] = gates
    report["passed"] = all(gates.values())
    report["seconds"] = time.perf_counter() - started
    return report


def eval_unit_check(teacher: Any, device: torch.device, spec: sit.IndexerSpec, scaling: float,
                    rng: np.random.Generator, unit_rows: int, *, profile: rt.Profile,
                    context: int) -> dict[str, Any]:
    """One synthetic selection unit: v2 ``evaluate_unit`` against v1's evaluation loop."""

    from harness import sparse_indexer_k1_runtime_v2 as rt2

    config = teacher.config
    n_layers = int(config.num_hidden_layers)
    seeds = [42, 43, 44]
    keys = [f"{t}|1e-3|{s}" for t in sit.TRAINED_TARGETS for s in seeds]
    params = {layer: skb.stack_from_state(skb.initial_state(spec, layer, keys), layer, keys,
                                          device) for layer in range(n_layers)}
    vocab = min(int(config.vocab_size), sit.SINK_TOKEN_ID)
    tokens = rng.integers(0, vocab, size=context + unit_rows + 3)
    q0, q1 = context + 2, context + 2 + unit_rows
    n0, n1 = context // 2, context // 2 + max(4, context // 50)
    output = rt2.evaluate_unit(teacher, tokens, q0, q1, n0, n1, do_select=True, do_mc=False,
                               eval_params=params, n_selectors=12, profile=profile,
                               scaling=scaling, ispec=spec, device=device)
    names = rt.selector_names(seeds)
    reference = np.full((n_layers, len(names)), np.nan, dtype=np.float32)
    ids = torch.as_tensor(tokens.astype(np.int64), device=device)[None]
    rows = torch.arange(q0, q1, device=device)
    with sit.CaptureSession(teacher, range(n_layers), query_rows=rows) as cap, torch.no_grad():
        teacher(input_ids=ids, use_cache=False, logits_to_keep=1)
        for layer in range(n_layers):
            q, k, hidden = cap.query[layer][0], cap.key[layer][0], cap.hidden[layer][0]
            probs = sit.head_probs_rows(q, k, rows, scaling)
            dense = sit.block_targets(probs, rows, include_hm=True)
            for col, name in enumerate(names):
                if name.startswith("T:"):
                    chosen = sit.select_top_blocks(dense[name[2:]], dense["valid"],
                                                   profile.k_blocks)
                    values = sit.block_selection_recall(chosen, rows, n0, n1)
                elif name.startswith("I:"):
                    _, target, seed = name.split(":")
                    indexer = sit.BlockIndexer.initialised(spec, int(seed), layer,
                                                           target).to(device)
                    score, valid = indexer(hidden, rows)
                    chosen = sit.select_top_blocks(score, valid, profile.k_blocks)
                    values = sit.block_selection_recall(chosen, rows, n0, n1)
                elif name == "U":
                    values = sit.union_topk_recall(probs, rows, profile.union_k, n0, n1)
                elif name == "Uk":
                    values = sit.union_topk_recall(probs, rows, profile.union_budget_k, n0, n1)
                else:
                    values = sit.random_block_recall(rows, n0, n1, profile.k_blocks)
                reference[layer, col] = float(values.mean()) * 100.0
    dense_cols = list(range(6))
    return {"dense_max_abs_points": float(np.abs(output.recall[:, dense_cols]
                                                 - reference[:, dense_cols]).max()),
            "indexer_max_abs_points": float(np.abs(output.recall[:, 6:]
                                                   - reference[:, 6:]).max()),
            "rows": unit_rows}


__all__ = ["CHECK_LAYER", "TOLERANCES", "adam_check", "device_check", "eval_unit_check",
           "independence_check", "registered_keys", "selection_check"]
