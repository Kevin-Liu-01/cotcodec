"""Dense-only evaluation of the Q3 dense headroom pre-check (torch).

One evaluation unit is one (context, query) prompt. A single forward pass of
the frozen base captures, at every softmax-attention layer, the post-norm,
post-RoPE queries of the question rows and every key (K1 v1's
``CaptureSession``; on Qwen3.5-4B-Base only the eight full-attention layers
have attention to capture). Exact probabilities are recomputed in fp32 and the
registered selectors are read at the matched budget:

* ``T:hs``, ``T:mp``, ``T:hm``: dense block top-k of K1 v1's targets (lower
  block index first on ties, K1 v2's batched selection, equivalence-tested
  against v1);
* ``U``, ``Uk``: the union over heads of each head's top 4k and top k/4 tokens;
* ``rand``: the analytic expectation of a uniformly random choice of k
  complete blocks;
* ``LEX``: a literal selector that scores a block by how many of its context
  tokens are content tokens of the question, with exact expected recall under
  uniformly random tie-breaking (layer-independent);
* ``T:hs@fixed``, ``T:mp@fixed``, ``rand@fixed``: the K1 budget of 256 blocks
  whatever the context length (equal to the matched budget at 8,192 tokens);
* ``N:<target>:<sigma>:<seed>``: the block-score null, the target's natural-log
  block scores plus N(0, sigma^2) noise drawn from a generator seeded by
  SHA-256 of (seed, unit, layer), identical in law on every leg.

Multiple choice is K1 v1's acc_norm (sum of option token log-probabilities over
UTF-8 bytes) with the prompt's cache: cropped back for an attention-only model
(K1 v1's code), deep-copied per option for a hybrid model whose recurrent
state cannot be cropped. Nothing here calls ``torch.compile`` or writes code;
on Qwen3.5 the gated-delta layers run flash-linear-attention's Triton kernels
from the pinned image (library code, compiled by Triton at first use).
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from torch import Tensor

from harness import dense_headroom_stats as dhs
from harness import sparse_indexer_bank as skb
from harness import sparse_indexer_torch as sit
from harness.sparse_indexer_k1_runtime import _option_scores

LOG_FLOOR = 1e-30


class DenseEvalError(RuntimeError):
    """An evaluation unit broke an integrity rule (exit code 3)."""


def attention_layers(config: Any) -> list[int]:
    """Indices of the softmax-attention layers (all layers for a plain transformer)."""

    n_layers = int(config.num_hidden_layers)
    kinds = getattr(config, "layer_types", None)
    if not kinds:
        return list(range(n_layers))
    return [i for i, kind in enumerate(kinds[:n_layers]) if kind == "full_attention"]


def is_hybrid(config: Any) -> bool:
    kinds = getattr(config, "layer_types", None) or []
    return any(kind != "full_attention" for kind in kinds)


def scaling_of(config: Any) -> float:
    head_dim = getattr(config, "head_dim", None) or (
        config.hidden_size // config.num_attention_heads)
    return float(head_dim) ** -0.5


@dataclass
class UnitOutput:
    recall: np.ndarray  # (attention layers, selectors) float32, NaN without selection
    ties: np.ndarray  # (selectors,) int64
    max_selected: int
    k_blocks: int
    mc_scores: np.ndarray  # (4,) float32, NaN without multiple choice
    mc_correct: int


def expected_topk_hits(scores: Tensor, valid: Tensor, k_blocks: int, cover: Tensor,
                       tail: Tensor) -> tuple[Tensor, Tensor]:
    """Expected needle hits ``(R,)`` of the top-k blocks when ties at the k-th
    score are broken uniformly at random, and the rows where that tie mattered.

    ``scores`` ``(R, nB)``; ``cover`` ``(nB,)`` needle tokens per block; ``tail``
    ``(R,)`` needle tokens in each row's incomplete tail block.
    """

    masked = scores.float().masked_fill(~valid, float("-inf"))
    width = min(k_blocks, masked.shape[-1])
    kth = torch.topk(masked, width, dim=-1).values[..., -1:]
    finite_kth = torch.isfinite(kth)
    above = valid & ((masked > kth) | ~finite_kth)
    tie = valid & (masked == kth) & finite_kth
    n_above = above.sum(dim=-1)
    n_tie = tie.sum(dim=-1)
    slots = (k_blocks - n_above).clamp_min(0)
    fraction = torch.where(n_tie > 0, slots.double() / n_tie.clamp_min(1).double(),
                           torch.zeros_like(n_tie, dtype=torch.float64)).clamp(max=1.0)
    cover = cover.double()
    hits = ((above.double() * cover).sum(dim=-1) + fraction * (tie.double() * cover).sum(dim=-1)
            + tail.double())
    straddle = ((n_tie > slots) & (slots > 0)).sum()
    return hits, straddle


def null_noise(seed: int, unit_key: str, layer: int, shape: tuple[int, int],
               device: torch.device) -> Tensor:
    generator = torch.Generator(device=device)
    generator.manual_seed(sit.derive_seed("dense-headroom-null", seed, unit_key, layer))
    return torch.randn(shape, generator=generator, device=device, dtype=torch.float32)


def select_unit(cap: Any, rows: Tensor, q0: int, n0: int, n1: int, *,
                layers: Sequence[int], k_blocks: int, fixed_k_blocks: int, scaling: float,
                lex_blocks: Tensor, seeds: Sequence[int], unit_key: str,
                names: Sequence[str]) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    """``(layers, selectors)`` recall in percent, tie counts summed over layers,
    the most tokens any top-k selection kept, and whether every score was finite."""

    device = rows.device
    needle = n1 - n0
    finite = torch.ones((), dtype=torch.bool, device=device)
    rand = sit.random_block_recall(rows, n0, n1, k_blocks).double().mean() * 100.0
    rand_fixed = sit.random_block_recall(rows, n0, n1, fixed_k_blocks).double().mean() * 100.0
    sigmas = torch.as_tensor(dhs.SIGMAS, dtype=torch.float32, device=device)
    union_k = (dhd_tokens(k_blocks), max(1, dhd_tokens(k_blocks) // 16))
    tail = skb.tail_overlap(rows, n0, n1, sit.BLOCK_SIZE)
    layer_rows: list[Tensor] = []
    ties_total = torch.zeros(len(names), dtype=torch.int64, device=device)
    selected = torch.zeros((), dtype=torch.int64, device=device)
    for layer in layers:
        q = cap.query[layer][0]
        k = cap.key[layer][0]
        probs = skb.causal_probs(q, k, rows, scaling)
        finite = finite & torch.isfinite(probs).all()
        dense = sit.block_targets(probs, rows, include_hm=True)
        valid = dense["valid"]
        n_blocks = valid.shape[-1]
        cover = sit.needle_block_cover(n_blocks, n0, n1, sit.BLOCK_SIZE, device)
        planes = torch.stack([dense["hs"], dense["mp"], dense["hm"]]).float()
        main = skb.select_blocks(planes, valid, rows, n0, n1, k_blocks, min_row=q0)
        if fixed_k_blocks == k_blocks:
            fixed_hits, fixed_ties = main.hits[:2], main.ties[:2]
            fixed_max = main.selected_max[:2]
        else:
            fixed = skb.select_blocks(planes[:2], valid, rows, n0, n1, fixed_k_blocks,
                                      min_row=q0)
            fixed_hits, fixed_ties, fixed_max = fixed.hits, fixed.ties, fixed.selected_max
        big, small = skb.union_hits(probs, rows, union_k, n0, n1, min_row=q0)
        lex_plane = lex_blocks[:n_blocks].to(device)[None, :].expand(rows.numel(), -1)
        lex_hits, lex_straddle = expected_topk_hits(lex_plane, valid, k_blocks, cover, tail)
        logs = torch.log(planes[:2].clamp_min(LOG_FLOOR))  # (2, R, nB)
        noise = torch.stack([null_noise(seed, unit_key, layer, tuple(valid.shape), device)
                             for seed in seeds])  # (S, R, nB)
        null_planes = (logs[:, None, None] + sigmas[None, :, None, None, None]
                       * noise[None, None]).reshape(-1, *valid.shape)
        finite = finite & (torch.isfinite(null_planes) | ~valid).all()
        null = skb.select_blocks(null_planes, valid, rows, n0, n1, k_blocks, min_row=q0)
        row = torch.cat([
            skb.row_mean_percent(main.hits, needle),
            torch.stack([skb.row_mean_percent(big, needle), skb.row_mean_percent(small, needle),
                         rand, skb.row_mean_percent(lex_hits, needle)]),
            skb.row_mean_percent(fixed_hits, needle), rand_fixed.reshape(1),
            skb.row_mean_percent(null.hits, needle),
        ])
        if row.shape[0] != len(names):
            raise DenseEvalError("selector columns do not match the registered selectors")
        layer_rows.append(row)
        zero = torch.zeros((), dtype=torch.int64, device=device)
        ties_total = ties_total + torch.cat([
            main.ties, torch.stack([zero, zero, zero, lex_straddle.to(torch.int64)]),
            fixed_ties, zero.reshape(1), null.ties])
        selected = torch.maximum(selected, torch.cat([main.selected_max, fixed_max,
                                                      null.selected_max]).max())
        del probs, dense, planes, null_planes, noise
    return torch.stack(layer_rows), ties_total, selected, finite


def dhd_tokens(k_blocks: int) -> int:
    return k_blocks * sit.BLOCK_SIZE


def option_scores(model: Any, cache: Any, last_logits: Tensor, options: Sequence[np.ndarray],
                  option_bytes: Sequence[int], prefix: int, device: torch.device,
                  hybrid: bool) -> list[float]:
    """K1 v1's acc_norm option scores; a hybrid cache is copied, never cropped."""

    if not hybrid:
        return _option_scores(model, cache, last_logits, options, option_bytes, prefix, device)
    first = torch.log_softmax(last_logits.float(), dim=-1)
    scores = []
    for tokens, n_bytes in zip(options, option_bytes, strict=True):
        ids = torch.as_tensor(np.asarray(tokens, dtype=np.int64), device=device)[None]
        total = float(first[int(ids[0, 0])])
        if ids.shape[1] > 1:
            branch = copy.deepcopy(cache)
            out = model(input_ids=ids[:, :-1], past_key_values=branch, use_cache=True)
            logp = torch.log_softmax(out.logits[0].float(), dim=-1)
            total += float(logp.gather(1, ids[0, 1:, None]).sum())
            del branch, out
        scores.append(total / max(int(n_bytes), 1))
    return scores


def evaluate_unit(model: Any, tokens: np.ndarray, q0: int, q1: int, n0: int, n1: int, *,
                  layers: Sequence[int], k_blocks: int, fixed_k_blocks: int, scaling: float,
                  do_select: bool, do_mc: bool, options: Sequence[np.ndarray] = (),
                  option_bytes: Sequence[int] = (), answer: int = -1,
                  lex_blocks: np.ndarray | None = None, seeds: Sequence[int] = (),
                  unit_key: str = "", names: Sequence[str] = (), hybrid: bool = False,
                  device: torch.device) -> UnitOutput:
    """One unit: one forward with capture (and the prompt cache when scored)."""

    from transformers import DynamicCache

    recall = np.full((len(layers), len(names)), np.nan, dtype=np.float32)
    ties = np.zeros(len(names), dtype=np.int64)
    max_selected = 0
    mc = np.full(4, np.nan, dtype=np.float32)
    correct = -1
    if do_select and not 0 < n0 < n1 <= q0:
        raise DenseEvalError("a selection unit needs a needle before the query")
    ids = torch.as_tensor(tokens.astype(np.int64), device=device)[None]
    rows = torch.arange(q0, q1, device=device)
    cache = DynamicCache(config=model.config) if do_mc else None
    capture_layers = list(layers) if do_select else []
    with sit.CaptureSession(model, capture_layers, query_rows=rows) as cap, torch.no_grad():
        out = model(input_ids=ids, use_cache=do_mc, past_key_values=cache, logits_to_keep=1)
        if do_select:
            if lex_blocks is None:
                raise DenseEvalError("a selection unit needs the literal selector's blocks")
            values, tie_counts, selected, finite = select_unit(
                cap, rows, q0, n0, n1, layers=layers, k_blocks=k_blocks,
                fixed_k_blocks=fixed_k_blocks, scaling=scaling,
                lex_blocks=torch.as_tensor(lex_blocks, dtype=torch.float32), seeds=seeds,
                unit_key=unit_key, names=names)
            host = torch.cat([values.flatten().double(), tie_counts.double(),
                              selected.double().reshape(1),
                              finite.double().reshape(1)]).cpu().numpy()
            if host[-1] != 1.0:
                raise DenseEvalError("non-finite score on a selection unit")
            n = len(layers) * len(names)
            recall[:] = host[:n].reshape(len(layers), len(names))
            ties[:] = host[n : n + len(names)]
            max_selected = int(host[-2])
        if do_mc:
            with cap.paused():
                mc[:] = option_scores(model, cache, out.logits[0, -1], options, option_bytes,
                                      ids.shape[1], device, hybrid)
                correct = int(answer)
    del cache
    return UnitOutput(recall, ties, max_selected, k_blocks if do_select else 0, mc, correct)


def unit_record(output: UnitOutput) -> Mapping[str, Any]:
    return {"recall": output.recall, "ties": output.ties, "max_selected": output.max_selected,
            "k_blocks": output.k_blocks, "mc_scores": output.mc_scores,
            "mc_correct": output.mc_correct}


__all__ = [
    "DenseEvalError",
    "UnitOutput",
    "attention_layers",
    "evaluate_unit",
    "expected_topk_hits",
    "is_hybrid",
    "null_noise",
    "option_scores",
    "scaling_of",
    "select_unit",
    "unit_record",
]
