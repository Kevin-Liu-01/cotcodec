"""Batched indexer bank of the Q3 K1 successor screen (q3-k1-localization-screen-v2).

The v1 screen trains and evaluates every block-form indexer on its own: one
``BlockIndexer`` forward, one KL loss, one backward, one ``clip_grad_norm_``
and one ``torch.optim.Adam`` step per indexer, sequence and layer, with host
synchronisations in between. This module computes the same function for all
indexers of one layer at once. Nothing here changes what is computed; every
choice below is an engineering choice with an equivalence test against the v1
per-indexer path (``tests/test_sparse_indexer_bank.py``).

* ``LayerBank`` stacks the parameters of a layer's trainable indexers along a
  leading slot axis, grouped in *cells*: one (target, learning rate) and its
  seeds. Every slot is initialised by v1's ``BlockIndexer.initialised`` (so the
  initialisation is bit-identical and still depends on (seed, layer, target)
  only), every cell has its own ``torch.optim.Adam`` with ``foreach=False``
  (the single-tensor path v1 uses; Adam is elementwise, so a stacked step
  equals the per-indexer step bit for bit), and the gradient norm is clipped
  per slot over that slot's six parameter tensors, never across slots.
  Indexers that are not trained (the V1 extension's non-selected learning
  rates) are not in the bank at all, so no optimizer ever moves them.
* The KL loss is computed in fixed chunks of ``ROW_CHUNK`` (1,024) rows, the
  registered chunk of v1's target recomputation. A chunk ending at row ``e``
  uses keys ``[0, e)`` and blocks ``[0, e // 4)`` only: every dropped key is in
  the future of every row of the chunk and every dropped block is incomplete
  for every row, so the targets, the loss and its gradient are unchanged up to
  floating-point summation order. Rows without a complete block (``i < 3``) are
  sliced off, as v1's loss excludes them. Block keys are computed once per
  sequence; their gradient is accumulated over the chunks and then pushed
  through the key path once.
* The ``1 / sqrt(128)`` score scale is applied to the per-row head gates, not
  to the logits plane: ``sum_j w_ij ReLU(l_ij) / s = sum_j (w_ij / s) ReLU(l_ij)``
  for ``s > 0``. The target path is untouched (its scale stays the fp32
  multiplier after the bf16-valued product, as in v1).
* Evaluation selections use one ``torch.topk`` over a composite integer key
  (the score's order-preserving integer image, then the lower index first)
  instead of a stable sort per selector and layer; the selected sets, boundary
  tie counts, needle hits and selected-token counts equal v1's
  ``select_top_blocks``, ``boundary_ties``, ``block_selection_recall`` and
  ``union_topk_recall`` exactly, and ``U`` and ``U_k`` come from one top-k
  (the top 64 is a prefix of the same order).

Nothing here calls ``torch.compile`` or generates code at run time.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn.functional as F
from torch import Tensor

from harness import sparse_indexer_torch as sit
from harness.sparse_indexer_k1_runtime import (
    ADAM_BETAS,
    ADAM_EPS,
    GRAD_CLIP,
    TARGET_ROW_CHUNK,
    learning_rate,
)

ROW_CHUNK = TARGET_ROW_CHUNK  # registered: v1's 1,024-row target chunk, also the indexer chunk
PARAM_NAMES: tuple[str, ...] = ("wq", "wk", "gate_w", "gate_b", "q_norm", "k_norm")
CLIP_EPS = 1e-6  # torch.nn.utils.clip_grad_norm_: max_norm / (total_norm + 1e-6)
BLOCK_INDEX_BITS = 12  # composite selection key: up to 4,096 blocks (16K tokens)
TOKEN_INDEX_BITS = 14  # composite union key: up to 16,384 tokens
EVAL_LAYER_GROUP = 4  # layers per batched block-selection call (memory only; exact either way)

ChunkTargets = Callable[[int, int], Mapping[str, Tensor]]


class BankContractError(ValueError):
    """Raised when a bank input violates the registered K1 contract."""


# --------------------------------------------------------------------------- #
# Cells and keys
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Cell:
    """One (target, learning rate) group of seeds; trained by one Adam."""

    target: str
    lr_tag: str
    seeds: tuple[int, ...]

    @property
    def lr(self) -> float:
        return float(self.lr_tag)

    def indexer_keys(self) -> list[str]:
        return [f"{self.target}|{self.lr_tag}|{seed}" for seed in self.seeds]


def cells_of(keys: Sequence[str]) -> list[Cell]:
    """Group v1 indexer keys (``target|lr|seed``) into cells, keeping their order.

    The keys of one (target, learning rate) must be contiguous, so the bank's
    slot order equals the given key order.
    """

    cells: list[Cell] = []
    seen: set[tuple[str, str]] = set()
    for key in keys:
        parts = key.split("|")
        if len(parts) != 3:
            raise BankContractError(f"indexer key {key!r} is not target|lr|seed")
        target, lr_tag, seed = parts[0], parts[1], int(parts[2])
        if cells and (cells[-1].target, cells[-1].lr_tag) == (target, lr_tag):
            if seed in cells[-1].seeds:
                raise BankContractError(f"indexer key {key!r} is repeated")
            cells[-1] = Cell(target, lr_tag, (*cells[-1].seeds, seed))
            continue
        if (target, lr_tag) in seen:
            raise BankContractError("the keys of one (target, lr) cell must be contiguous")
        seen.add((target, lr_tag))
        cells.append(Cell(target, lr_tag, (seed,)))
    return cells


def target_runs(slot_targets: Sequence[str]) -> list[tuple[int, int, str]]:
    """Maximal runs ``(start, stop, target)`` of slots that share a target."""

    runs: list[tuple[int, int, str]] = []
    for index, target in enumerate(slot_targets):
        if runs and runs[-1][2] == target:
            runs[-1] = (runs[-1][0], index + 1, target)
        else:
            runs.append((index, index + 1, target))
    return runs


def slot_name(layer: int, key: str) -> str:
    return f"L{layer:02d}|{key}"


# --------------------------------------------------------------------------- #
# Stacked forward
# --------------------------------------------------------------------------- #


def _rms(x: Tensor, weight: Tensor, eps: float = sit.INDEXER_NORM_EPS) -> Tensor:
    # The expression of v1's sparse_indexer_torch._rms_norm, broadcast over slots.
    return x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + eps) * weight


def stacked_block_keys(params: Mapping[str, Tensor], hidden: Tensor,
                       spec: sit.IndexerSpec) -> Tensor:
    """``(N, nB, d)`` pooled, normalised, rotated keys of every slot (v1 ``block_keys``)."""

    if hidden.ndim != 2 or hidden.shape[1] != spec.d_model:
        raise BankContractError("hidden must be (T, d_model)")
    n_blocks = hidden.shape[0] // spec.block_size
    weight = params["wk"]
    x = hidden[: n_blocks * spec.block_size].to(weight.dtype)
    keys = torch.matmul(x, weight.transpose(1, 2))
    pooled = keys.reshape(weight.shape[0], n_blocks, spec.block_size, spec.dim).mean(dim=2)
    pooled = _rms(pooled, params["k_norm"][:, None, :])
    positions = torch.arange(n_blocks, device=hidden.device) * spec.block_size
    cos, sin = sit.rotary_cos_sin(positions, spec.rope_dims, spec.rope_theta, hidden.device,
                                  pooled.dtype)
    return sit.apply_rotary(pooled, cos, sin)


def stacked_scores(params: Mapping[str, Tensor], hidden_rows: Tensor, rows: Tensor,
                   keys: Tensor, spec: sit.IndexerSpec) -> Tensor:
    """Raw scores ``(N, R, nB)`` of every slot for ``rows`` against ``keys`` (unmasked).

    ``sum_j (w_ij / sqrt(d)) ReLU(q_i^j . kbar_b)``: v1's score with the scale
    moved from the logits plane to the gates.
    """

    weight = params["wq"]
    slots = weight.shape[0]
    x = hidden_rows.to(weight.dtype)
    n_rows = x.shape[0]
    q = torch.matmul(x, weight.transpose(1, 2)).reshape(slots, n_rows, spec.heads, spec.dim)
    q = _rms(q, params["q_norm"][:, None, None, :])
    cos, sin = sit.rotary_cos_sin(rows, spec.rope_dims, spec.rope_theta, x.device, x.dtype)
    q = sit.apply_rotary(q, cos[:, None, :], sin[:, None, :])
    gates = params["gate_b"][:, None, :] + torch.matmul(x, params["gate_w"].transpose(1, 2))
    gates = gates / math.sqrt(spec.dim)
    logits = torch.matmul(q.reshape(slots, n_rows * spec.heads, spec.dim), keys.transpose(1, 2))
    logits = logits.reshape(slots, n_rows, spec.heads, keys.shape[1])
    return torch.einsum("nrh,nrhb->nrb", gates, F.relu(logits))


def kl_slot_sums(scores: Tensor, valid: Tensor, targets: Mapping[str, Tensor],
                 runs: Sequence[tuple[int, int, str]]) -> Tensor:
    """Per slot: sum over rows and blocks of ``KL(target || softmax(scores))`` terms.

    The terms are v1's ``kl_block_loss`` terms; every row passed in must hold a
    complete block.
    """

    dtype = torch.promote_types(scores.dtype, torch.float32)
    masked = scores.to(dtype).masked_fill(~valid, float("-inf"))
    log_q = torch.log_softmax(masked, dim=-1).masked_fill(~valid, 0.0)
    sums = []
    for start, stop, target in runs:
        p = targets[target].to(dtype)
        terms = torch.xlogy(p, p) - p * log_q[start:stop]
        sums.append(terms.sum(dim=(1, 2)))
    return torch.cat(sums)


def causal_probs(query_rows: Tensor, key: Tensor, rows: Tensor, scaling: float) -> Tensor:
    """v1's ``head_probs_rows`` (same operations in the same order) without its
    host-synchronising range checks; ``rows`` must lie inside ``key``."""

    heads_q, n_rows, dim = query_rows.shape
    heads_kv, length, _ = key.shape
    groups = heads_q // heads_kv
    q = query_rows.float().reshape(heads_kv, groups * n_rows, dim)
    scores = torch.matmul(q, key.float().transpose(-1, -2)).reshape(heads_q, n_rows, length)
    scores = scores * float(scaling)
    future = torch.arange(length, device=key.device)[None, :] > rows[:, None]
    scores = scores.masked_fill(future[None], float("-inf"))
    return torch.softmax(scores, dim=-1)


def truncated_targets(q: Tensor, k: Tensor, scaling: float,
                      block_size: int = sit.BLOCK_SIZE) -> ChunkTargets:
    """Chunk target provider: hs and mp for rows ``[first, end)`` over keys ``[0, end)``.

    ``q`` is ``(Hq, T, d)`` and ``k`` ``(Hkv, T, d)`` of one sequence.
    """

    if q.ndim != 3 or k.ndim != 3 or q.shape[1] != k.shape[1]:
        raise BankContractError("q must be (Hq, T, d) and k (Hkv, T, d)")

    def provide(first: int, end: int) -> Mapping[str, Tensor]:
        rows = torch.arange(first, end, device=k.device)
        probs = causal_probs(q[:, first:end], k[:, :end], rows, scaling)
        return sit.block_targets(probs, rows, block_size=block_size)

    return provide


def chunk_bounds(length: int, row_chunk: int, block_size: int) -> list[tuple[int, int]]:
    """``(first, end)`` per row chunk; ``first`` skips rows with no complete block."""

    if row_chunk <= 0:
        raise BankContractError("row_chunk must be positive")
    out = []
    for start in range(0, length, row_chunk):
        end = min(start + row_chunk, length)
        first = max(start, block_size - 1)
        if first < end:
            out.append((first, end))
    return out


@torch.no_grad()
def sequence_kl(params: Mapping[str, Tensor], spec: sit.IndexerSpec,
                runs: Sequence[tuple[int, int, str]], hidden: Tensor,
                chunk_targets: ChunkTargets, *, row_chunk: int = ROW_CHUNK) -> Tensor:
    """Per-slot KL (v1 ``kl_block_loss``) of one sequence without gradients (stream-dev KL)."""

    length = hidden.shape[0]
    count = length - (spec.block_size - 1)
    if count <= 0:
        raise BankContractError("no row has a complete block")
    keys = stacked_block_keys(params, hidden, spec)
    totals = torch.zeros(keys.shape[0], dtype=torch.promote_types(keys.dtype, torch.float32),
                         device=hidden.device)
    for first, end in chunk_bounds(length, row_chunk, spec.block_size):
        targets = chunk_targets(first, end)
        valid = targets["valid"]
        rows = torch.arange(first, end, device=hidden.device)
        scores = stacked_scores(params, hidden[first:end], rows, keys[:, : valid.shape[1]], spec)
        totals += kl_slot_sums(scores, valid, targets, runs)
    return totals / count


# --------------------------------------------------------------------------- #
# The bank of one layer
# --------------------------------------------------------------------------- #


class LayerBank:
    """The trainable indexers of one layer: stacked cells, one Adam per cell."""

    def __init__(self, spec: sit.IndexerSpec, layer: int, keys: Sequence[str],
                 device: torch.device | str, *, dtype: torch.dtype = torch.float32) -> None:
        if not keys:
            raise BankContractError("a bank needs at least one indexer")
        self.spec = spec
        self.layer = int(layer)
        self.cells = cells_of(keys)
        self.keys = [key for cell in self.cells for key in cell.indexer_keys()]
        self.slot_targets = [cell.target for cell in self.cells for _ in cell.seeds]
        self.runs = target_runs(self.slot_targets)
        self.device = torch.device(device)
        self.leaves: list[dict[str, Tensor]] = []
        self.optimisers: list[torch.optim.Adam] = []
        for cell in self.cells:
            members = [dict(sit.BlockIndexer.initialised(spec, seed, self.layer,
                                                         cell.target).named_parameters())
                       for seed in cell.seeds]
            leaves = {name: torch.stack([m[name].detach() for m in members]).to(
                device=self.device, dtype=dtype).requires_grad_(True) for name in PARAM_NAMES}
            self.leaves.append(leaves)
            self.optimisers.append(torch.optim.Adam(
                [leaves[name] for name in PARAM_NAMES], lr=cell.lr, betas=ADAM_BETAS,
                eps=ADAM_EPS, weight_decay=0.0, foreach=False))

    @property
    def slots(self) -> int:
        return len(self.keys)

    # -- parameters ----------------------------------------------------------- #

    def working_params(self) -> dict[str, Tensor]:
        """Fresh leaf tensors ``(N, ...)`` holding every slot, for one training step."""

        with torch.no_grad():
            stacked = {name: torch.cat([leaves[name] for leaves in self.leaves])
                       for name in PARAM_NAMES}
        return {name: tensor.requires_grad_(True) for name, tensor in stacked.items()}

    def frozen_params(self) -> dict[str, Tensor]:
        with torch.no_grad():
            return {name: torch.cat([leaves[name] for leaves in self.leaves]).detach()
                    for name in PARAM_NAMES}

    def adopt_grads(self, params: Mapping[str, Tensor]) -> None:
        """Hand the accumulated stacked gradients to the cells' leaves."""

        offset = 0
        for cell, leaves in zip(self.cells, self.leaves, strict=True):
            width = len(cell.seeds)
            for name in PARAM_NAMES:
                grad = params[name].grad
                if grad is None:
                    raise BankContractError(f"no gradient reached {name}")
                leaves[name].grad = grad[offset : offset + width].detach()
            offset += width

    # -- training --------------------------------------------------------------- #

    def accumulate_sequence(self, params: Mapping[str, Tensor], hidden: Tensor,
                            chunk_targets: ChunkTargets, *, grad_scale: float,
                            row_chunk: int = ROW_CHUNK) -> Tensor:
        """Backward of ``grad_scale * KL`` of one sequence into ``params``; returns
        the per-slot KL (v1 ``kl_block_loss``), detached."""

        spec = self.spec
        length = hidden.shape[0]
        count = length - (spec.block_size - 1)
        if count <= 0:
            raise BankContractError("no row has a complete block")
        keys = stacked_block_keys(params, hidden, spec)
        keys_leaf = keys.detach().requires_grad_(True)
        totals = torch.zeros(self.slots, dtype=torch.promote_types(keys.dtype, torch.float32),
                             device=hidden.device)
        for first, end in chunk_bounds(length, row_chunk, spec.block_size):
            targets = chunk_targets(first, end)
            valid = targets["valid"]
            n_blocks = valid.shape[1]
            rows = torch.arange(first, end, device=hidden.device)
            scores = stacked_scores(params, hidden[first:end], rows, keys_leaf[:, :n_blocks],
                                    spec)
            sums = kl_slot_sums(scores, valid, targets, self.runs)
            (sums.sum() * (grad_scale / count)).backward()
            totals += sums.detach()
        if keys_leaf.grad is not None:
            keys.backward(keys_leaf.grad)
        return totals / count

    def sequence_kl(self, params: Mapping[str, Tensor], hidden: Tensor,
                    chunk_targets: ChunkTargets, *, row_chunk: int = ROW_CHUNK) -> Tensor:
        return sequence_kl(params, self.spec, self.runs, hidden, chunk_targets,
                           row_chunk=row_chunk)

    @torch.no_grad()
    def clip_(self) -> Tensor:
        """Clip every slot's gradient to norm ``GRAD_CLIP`` over its six tensors.

        Returns the per-slot total norms before clipping (v1 ``clip_grad_norm_``).
        """

        totals = []
        for leaves in self.leaves:
            grads = [leaves[name].grad for name in PARAM_NAMES]
            if any(grad is None for grad in grads):
                raise BankContractError("clip before every parameter has a gradient")
            norms = torch.stack([torch.linalg.vector_norm(grad.reshape(grad.shape[0], -1), 2,
                                                          dim=1) for grad in grads], dim=1)
            total = torch.linalg.vector_norm(norms, 2, dim=1)
            coef = torch.clamp(GRAD_CLIP / (total + CLIP_EPS), max=1.0)
            for grad in grads:
                grad.mul_(coef.reshape(-1, *([1] * (grad.ndim - 1))))
            totals.append(total)
        return torch.cat(totals)

    def step(self, step: int, warmup: int) -> None:
        """One Adam step per cell at v1's warm-up learning rate, then clear the grads."""

        for cell, optimiser in zip(self.cells, self.optimisers, strict=True):
            for group in optimiser.param_groups:
                group["lr"] = learning_rate(step, cell.lr, warmup)
            optimiser.step()
            optimiser.zero_grad(set_to_none=True)

    # -- state (v1 per-indexer names) --------------------------------------------- #

    def state_tensors(self) -> dict[str, Tensor]:
        """v1 ``IndexerBank.state_tensors`` names for every slot of this bank.

        Every tensor is its own copy: slices of a stacked tensor share storage,
        which safetensors refuses to write.
        """

        out: dict[str, Tensor] = {}
        for cell, leaves, optimiser in zip(self.cells, self.leaves, self.optimisers,
                                           strict=True):
            for slot, key in enumerate(cell.indexer_keys()):
                prefix = slot_name(self.layer, key)
                for name in PARAM_NAMES:
                    out[f"{prefix}|param|{name}"] = leaves[name][slot].detach().clone()
                for name in PARAM_NAMES:
                    state = optimiser.state.get(leaves[name])
                    if state:
                        out[f"{prefix}|exp_avg|{name}"] = state["exp_avg"][slot].clone()
                        out[f"{prefix}|exp_avg_sq|{name}"] = state["exp_avg_sq"][slot].clone()
                        out[f"{prefix}|step|{name}"] = torch.as_tensor(
                            state["step"]).reshape(1).clone()
        return out

    def load_state(self, tensors: Mapping[str, Tensor]) -> None:
        """Restore parameters and Adam moments written by ``state_tensors``."""

        for cell, leaves, optimiser in zip(self.cells, self.leaves, self.optimisers,
                                           strict=True):
            prefixes = [slot_name(self.layer, key) for key in cell.indexer_keys()]
            with torch.no_grad():
                for name in PARAM_NAMES:
                    stacked = torch.stack([tensors[f"{p}|param|{name}"] for p in prefixes])
                    leaves[name].copy_(stacked.to(leaves[name].device))
            for name in PARAM_NAMES:
                present = [f"{p}|exp_avg|{name}" in tensors for p in prefixes]
                if not any(present):
                    continue
                if not all(present):
                    raise BankContractError(f"cell {cell.target}|{cell.lr_tag}: Adam state "
                                            "exists for some seeds only")
                steps = [tensors[f"{p}|step|{name}"].reshape(()) for p in prefixes]
                if any(not torch.equal(steps[0], other) for other in steps[1:]):
                    raise BankContractError(f"cell {cell.target}|{cell.lr_tag}: seeds were "
                                            "stepped a different number of times")
                param = leaves[name]
                optimiser.state[param] = {
                    "step": steps[0].clone().float().cpu(),
                    "exp_avg": torch.stack([tensors[f"{p}|exp_avg|{name}"] for p in prefixes]
                                           ).to(param.device).clone(),
                    "exp_avg_sq": torch.stack([tensors[f"{p}|exp_avg_sq|{name}"]
                                               for p in prefixes]).to(param.device).clone(),
                }

    def param_digests(self) -> dict[str, str]:
        """v1 ``IndexerBank.param_digest``: per indexer, over its own parameters."""

        out = {}
        for cell, leaves in zip(self.cells, self.leaves, strict=True):
            for slot, key in enumerate(cell.indexer_keys()):
                out[slot_name(self.layer, key)] = sit.state_digest(
                    {name: leaves[name][slot] for name in PARAM_NAMES})
        return out


def initial_state(spec: sit.IndexerSpec, layer: int, keys: Sequence[str]) -> dict[str, Tensor]:
    """v1 parameter tensors (no optimizer state) of indexers that are never trained here."""

    out: dict[str, Tensor] = {}
    for key in keys:
        target, _, seed = key.split("|")
        indexer = sit.BlockIndexer.initialised(spec, int(seed), layer, target)
        for name, param in indexer.named_parameters():
            out[f"{slot_name(layer, key)}|param|{name}"] = param.detach()
    return out


def stack_from_state(tensors: Mapping[str, Tensor], layer: int, keys: Sequence[str],
                     device: torch.device | str,
                     dtype: torch.dtype = torch.float32) -> dict[str, Tensor]:
    """Stacked parameters ``(N, ...)`` of ``keys`` from v1-named state tensors."""

    out = {}
    for name in PARAM_NAMES:
        try:
            parts = [tensors[f"{slot_name(layer, key)}|param|{name}"] for key in keys]
        except KeyError as exc:
            raise BankContractError(f"layer {layer}: missing indexer state {exc}") from exc
        out[name] = torch.stack(parts).to(device=device, dtype=dtype)
    return out


# --------------------------------------------------------------------------- #
# Evaluation: exact batched selection and recall
# --------------------------------------------------------------------------- #


def _ordered_int(values: Tensor) -> Tensor:
    """Order-preserving int64 image of float32 values (-0.0 is canonicalised to +0.0)."""

    canonical = values.float() + 0.0
    bits = canonical.contiguous().view(torch.int32).to(torch.int64)
    return torch.where(bits < 0, bits ^ 0x7FFFFFFF, bits)


def tail_overlap(rows: Tensor, needle_start: int, needle_end: int,
                 block_size: int = sit.BLOCK_SIZE) -> Tensor:
    """Needle tokens in each row's incomplete tail block (v1 ``_tail_overlap``)."""

    tail_start = ((rows + 1) // block_size) * block_size
    lo = torch.clamp(tail_start, min=needle_start)
    hi = torch.clamp(rows + 1, max=needle_end)
    return torch.clamp(hi - lo, min=0)


@dataclass(frozen=True)
class BlockSelection:
    hits: Tensor  # (..., R) needle tokens selected (chosen blocks plus the tail block)
    ties: Tensor  # (...) rows whose k-th and (k+1)-th valid scores tie
    selected_max: Tensor  # (...) most tokens selected on any row


def _needle_precedes(rows: Tensor, needle_end: int, min_row: int | None) -> None:
    first = int(rows.min()) if min_row is None else int(min_row)
    if first < needle_end:
        raise BankContractError("every needle token must precede every query row")


def select_blocks(scores: Tensor, valid: Tensor, rows: Tensor, needle_start: int,
                  needle_end: int, k_blocks: int = sit.BLOCK_BUDGET,
                  block_size: int = sit.BLOCK_SIZE, *,
                  min_row: int | None = None) -> BlockSelection:
    """Top-``k_blocks`` complete blocks of ``scores`` ``(..., R, nB)``, ties to the lower block.

    Equals v1's ``select_top_blocks`` + ``block_selection_recall`` (hits),
    ``boundary_ties`` and the selected-token count, for every leading index.
    ``min_row`` (the first query row, when the caller knows it) spares a host
    synchronisation in the needle-before-query check.
    """

    if k_blocks <= 0:
        raise BankContractError("k_blocks must be positive")
    n_blocks = scores.shape[-1]
    if n_blocks >= 1 << BLOCK_INDEX_BITS:
        raise BankContractError("too many blocks for the composite selection key")
    if not 0 <= needle_start < needle_end:
        raise BankContractError("needle span must be non-empty and non-negative")
    _needle_precedes(rows, needle_end, min_row)
    masked = scores.float().masked_fill(~valid, float("-inf")) + 0.0
    index = torch.arange(n_blocks, device=scores.device)
    key = (_ordered_int(masked) << BLOCK_INDEX_BITS) | ((1 << BLOCK_INDEX_BITS) - 1 - index)
    if n_blocks > k_blocks:
        top = torch.topk(key, k_blocks + 1, dim=-1, sorted=True)
        chosen = (key >= top.values[..., k_blocks - 1 : k_blocks]) & valid
        kth = masked.gather(-1, top.indices[..., k_blocks - 1 : k_blocks]).squeeze(-1)
        nxt = masked.gather(-1, top.indices[..., k_blocks : k_blocks + 1]).squeeze(-1)
        ties = ((kth == nxt) & torch.isfinite(nxt)).sum(dim=-1)
    else:
        chosen = valid.expand_as(masked)
        ties = torch.zeros(masked.shape[:-2], dtype=torch.int64, device=scores.device)
    cover = sit.needle_block_cover(n_blocks, needle_start, needle_end, block_size,
                                   scores.device)
    tail = tail_overlap(rows, needle_start, needle_end, block_size)
    hits = (chosen.to(cover.dtype) * cover).sum(dim=-1) + tail
    selected = chosen.sum(dim=-1) * block_size + (rows + 1) % block_size
    return BlockSelection(hits=hits, ties=ties, selected_max=selected.amax(dim=-1))


def union_hits(probs: Tensor, rows: Tensor, k_values: Sequence[int], needle_start: int,
               needle_end: int, *, min_row: int | None = None) -> list[Tensor]:
    """Needle hits ``(R,)`` of the union over heads of each head's causal top-k tokens,
    for every ``k`` in ``k_values``, from one top-k (v1 ``union_topk_recall`` x |N|)."""

    heads, n_rows, length = probs.shape
    if length >= 1 << TOKEN_INDEX_BITS:
        raise BankContractError("too many tokens for the composite union key")
    if not 0 <= needle_start < needle_end:
        raise BankContractError("needle span must be non-empty and non-negative")
    _needle_precedes(rows, needle_end, min_row)
    future = torch.arange(length, device=probs.device)[None, :] > rows[:, None]
    index = torch.arange(length, device=probs.device)
    key = (_ordered_int(probs) << TOKEN_INDEX_BITS) | ((1 << TOKEN_INDEX_BITS) - 1 - index)
    key = key.masked_fill(future[None], -1)
    top = torch.topk(key, min(max(k_values), length), dim=-1, sorted=True).values
    visible = ~future[:, needle_start:needle_end]
    out = []
    for k in k_values:
        width = min(k, length)
        threshold = top[..., width - 1 : width]
        chosen = (key[..., needle_start:needle_end] >= threshold) & visible[None]
        out.append(chosen.any(dim=0).sum(dim=-1))
    return out


def row_mean_percent(hits: Tensor, needle_tokens: int) -> Tensor:
    """Mean over the last (row) axis of v1's per-row recall ``hits / |N|``, in percent.

    The per-row values are v1's fp32 values; the mean is taken in float64.
    """

    per_row = hits.float() / float(needle_tokens)
    return per_row.double().mean(dim=-1) * 100.0


def finite_or_raise(values: Tensor, valid: Tensor | None, what: str) -> None:
    """Integrity: no non-finite value on a selection prompt (V3)."""

    checked = values if valid is None else values.masked_select(valid.expand_as(values))
    if not bool(torch.isfinite(checked).all()):
        raise BankContractError(f"non-finite {what} on a selection prompt")


# --------------------------------------------------------------------------- #
# Equivalence with the v1 per-indexer path
# --------------------------------------------------------------------------- #


def _rel(a: Tensor, b: Tensor) -> float:
    a64, b64 = a.detach().double(), b.detach().double()
    scale = float(b64.abs().max()) if b64.numel() else 0.0
    return float((a64 - b64).abs().max()) / scale if scale > 0 else float((a64 - b64).abs().max())


def _rel_fro(a: Tensor, b: Tensor) -> float:
    a64, b64 = a.detach().double(), b.detach().double()
    scale = float(torch.linalg.vector_norm(b64))
    diff = float(torch.linalg.vector_norm(a64 - b64))
    return diff / scale if scale > 0 else diff


def compare_with_v1(spec: sit.IndexerSpec, layer: int, keys: Sequence[str], hidden: Tensor,
                    sequence_targets: Mapping[str, Tensor], *, device: torch.device | str,
                    dtype: torch.dtype, row_chunk: int = ROW_CHUNK, warmup: int = 20,
                    sequences: int = 1) -> dict[str, Any]:
    """Run v1's per-indexer path and the bank on the same inputs for one step.

    ``sequence_targets`` holds v1's full-length ``hs``, ``mp`` and ``valid``
    ``(T, nB)`` for ``hidden`` (``T x d``); both paths read the same targets
    (the bank its chunk slices), so the comparison isolates the indexer path.
    The batch repeats ``hidden`` ``sequences`` times, as v1 accumulates
    ``loss / batch`` per sequence. Returns the largest relative differences of
    the loss, every gradient tensor before clipping, the clip norm, and the
    parameters after one Adam step, plus a bitwise check of the Adam step on
    identical clipped gradients and states.
    """

    device = torch.device(device)
    hidden = hidden.to(device=device, dtype=dtype)
    targets = {name: value.to(device) for name, value in sequence_targets.items()}
    length = hidden.shape[0]
    rows = torch.arange(length, device=device)
    n_blocks = targets["valid"].shape[1]
    for _, end in chunk_bounds(length, row_chunk, spec.block_size):
        tail = targets["valid"][:, end // spec.block_size :]
        if bool(tail[:end].any()):
            raise BankContractError("a dropped block is complete for a chunk row")
    reference: dict[str, Any] = {}
    for key in keys:
        target, lr_tag, seed = key.split("|")
        indexer = sit.BlockIndexer.initialised(spec, int(seed), layer, target).to(
            device=device, dtype=dtype)
        optimiser = torch.optim.Adam(indexer.parameters(), lr=float(lr_tag), betas=ADAM_BETAS,
                                     eps=ADAM_EPS, weight_decay=0.0, foreach=False)
        losses = []
        for _ in range(sequences):
            scores, valid = indexer(hidden, rows)
            loss, _ = sit.kl_block_loss(targets[target], scores, valid)
            (loss / sequences).backward()
            losses.append(loss.detach())
        grads = {name: p.grad.detach().clone() for name, p in indexer.named_parameters()}
        norm = torch.nn.utils.clip_grad_norm_(indexer.parameters(), GRAD_CLIP, foreach=False)
        clipped = {name: p.grad.detach().clone() for name, p in indexer.named_parameters()}
        for group in optimiser.param_groups:
            group["lr"] = learning_rate(0, float(lr_tag), warmup)
        optimiser.step()
        reference[key] = {"loss": torch.stack(losses).sum() / sequences, "grads": grads,
                          "norm": norm.detach(), "clipped": clipped,
                          "params": {n: p.detach().clone() for n, p in indexer.named_parameters()},
                          "state": {n: {k: (v.clone() if torch.is_tensor(v) else v)
                                        for k, v in optimiser.state[p].items()}
                                    for n, p in indexer.named_parameters()}}

    def provide(first: int, end: int) -> Mapping[str, Tensor]:
        width = end // spec.block_size
        return {name: targets[name][first:end, :width] for name in ("hs", "mp", "valid")}

    bank = LayerBank(spec, layer, keys, device, dtype=dtype)
    params = bank.working_params()
    totals = None
    for _ in range(sequences):
        kl = bank.accumulate_sequence(params, hidden, provide, grad_scale=1.0 / sequences,
                                      row_chunk=row_chunk)
        totals = kl if totals is None else totals + kl
    assert totals is not None
    bank_losses = totals / sequences
    bank.adopt_grads(params)
    bank_grads = {name: torch.cat([leaves[name].grad for leaves in bank.leaves]).clone()
                  for name in PARAM_NAMES}
    bank_norms = bank.clip_()
    # The Adam check: hand the bank v1's clipped gradients and compare the step bitwise.
    adam_bank = LayerBank(spec, layer, keys, device, dtype=dtype)
    for cell, leaves in zip(adam_bank.cells, adam_bank.leaves, strict=True):
        for name in PARAM_NAMES:
            leaves[name].grad = torch.stack([reference[key]["clipped"][name]
                                             for key in cell.indexer_keys()])
    adam_bank.step(0, warmup)
    bank.step(0, warmup)
    report: dict[str, Any] = {"slots": len(keys), "n_blocks": n_blocks,
                              "row_chunk": row_chunk, "dtype": str(dtype),
                              "device": str(device)}
    loss_rel, norm_rel = 0.0, 0.0
    grad_rel: dict[str, float] = dict.fromkeys(PARAM_NAMES, 0.0)
    param_rel: dict[str, float] = dict.fromkeys(PARAM_NAMES, 0.0)
    adam_bitwise = True
    for slot, key in enumerate(bank.keys):
        ref = reference[key]
        loss_rel = max(loss_rel, _rel(bank_losses[slot], ref["loss"]))
        norm_rel = max(norm_rel, _rel(bank_norms[slot], ref["norm"]))
        for name in PARAM_NAMES:
            grad_rel[name] = max(grad_rel[name], _rel_fro(bank_grads[name][slot],
                                                          ref["grads"][name]))
        cell_index = next(i for i, c in enumerate(bank.cells) if key in c.indexer_keys())
        cell_slot = bank.cells[cell_index].indexer_keys().index(key)
        for name in PARAM_NAMES:
            after = bank.leaves[cell_index][name][cell_slot]
            param_rel[name] = max(param_rel[name], _rel_fro(after, ref["params"][name]))
            adam_after = adam_bank.leaves[cell_index][name][cell_slot]
            state = adam_bank.optimisers[cell_index].state[adam_bank.leaves[cell_index][name]]
            adam_bitwise &= torch.equal(adam_after.detach(), ref["params"][name])
            adam_bitwise &= torch.equal(state["exp_avg"][cell_slot],
                                        ref["state"][name]["exp_avg"])
            adam_bitwise &= torch.equal(state["exp_avg_sq"][cell_slot],
                                        ref["state"][name]["exp_avg_sq"])
            adam_bitwise &= torch.equal(state["step"], ref["state"][name]["step"])
    report.update({"loss_max_rel": loss_rel, "clip_norm_max_rel": norm_rel,
                   "grad_max_rel_fro": grad_rel, "param_after_step_max_rel_fro": param_rel,
                   "adam_step_bitwise": bool(adam_bitwise)})
    return report


__all__ = [
    "BLOCK_INDEX_BITS",
    "EVAL_LAYER_GROUP",
    "PARAM_NAMES",
    "ROW_CHUNK",
    "TOKEN_INDEX_BITS",
    "BankContractError",
    "BlockSelection",
    "Cell",
    "LayerBank",
    "causal_probs",
    "cells_of",
    "chunk_bounds",
    "compare_with_v1",
    "finite_or_raise",
    "initial_state",
    "kl_slot_sums",
    "row_mean_percent",
    "select_blocks",
    "sequence_kl",
    "slot_name",
    "stack_from_state",
    "stacked_block_keys",
    "stacked_scores",
    "tail_overlap",
    "target_runs",
    "truncated_targets",
    "union_hits",
]
