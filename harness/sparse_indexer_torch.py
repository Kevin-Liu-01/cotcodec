"""Torch objects for the Q3 K1 localization screen (block-form sparse indexers).

This module turns the NumPy Phase-0 definitions of
``harness/translation_supervised_indexer.py`` into the torch objects the K1
screen runs on a frozen Qwen3 checkpoint:

* ``CaptureSession``: a registered attention implementation that hands the
  post-norm, post-RoPE query and key tensors of the SDPA path to the caller,
  plus pre-hooks that capture each layer's attention input. Exact attention
  probabilities are then recomputed offline per row chunk, so an 8K sequence
  never materialises the eager ``(heads, T, T)`` tensor for every layer.
* ``block_targets``: the two registered distillation targets over complete
  blocks of ``BLOCK_SIZE`` tokens. ``hs`` is head-sum, L1, sum within the
  block, renormalised over complete blocks. ``mp`` is QSA Eq. 17: head-sum, L1,
  max within the block, L1 over complete blocks. ``hm`` (sum within the block
  of the per-token head-max) is a descriptive dense selector only and is never
  trained.
* ``BlockIndexer``: QSA Eq. 12-16 (per-head RMS-normalised queries, one
  average-pooled and RMS-normalised key per block, rotary position on the query
  at ``i`` and the key at ``r * b``, block-causal ReLU scores) with the DSA
  per-head gate ``w = b + x W`` (``b = 1``, ``W = 0`` at init, so the gate equals
  QSA's unweighted head sum at initialisation).
* ``kl_block_loss``, ``select_top_blocks`` (stable lower-index tie-break), the
  needle-recall functions for indexer, target, union references and the
  analytic random baseline, and ``ratio_retention`` for the scale-free
  co-statistic ``xi_rel``.

Nothing here calls ``torch.compile`` or generates code at run time.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch import Tensor, nn

BLOCK_SIZE = 4
INDEXER_HEADS = 4
INDEXER_DIM = 128
# Registered choice (preregistration, Design decisions): QSA applies rotary
# position to the indexer "matching the rotary dimension used in the core
# attention module". Qwen3-0.6B-Base rotates all 128 head dimensions, so the
# K1 indexer rotates all 128 of its dimensions at the base's theta.
INDEXER_ROPE_DIMS = 128
INDEXER_ROPE_THETA = 1_000_000.0
INDEXER_NORM_EPS = 1e-6
TOKEN_BUDGET = 1024
BLOCK_BUDGET = TOKEN_BUDGET // BLOCK_SIZE
UNION_K_PER_HEAD = 1024
UNION_BUDGET_MATCHED_K = 64
SINK_TOKEN_ID = 151643
TRAINED_TARGETS: tuple[str, ...] = ("hs", "mp")
DENSE_SELECTORS: tuple[str, ...] = ("hs", "mp", "hm")
CAPTURE_IMPLEMENTATION = "cotcodec_capture"
_TINY = 1e-30


class TorchContractError(ValueError):
    """Raised when a torch-side input violates the registered K1 contract."""


# --------------------------------------------------------------------------- #
# Determinism and seeds
# --------------------------------------------------------------------------- #


def set_determinism(allow_tf32: bool = True) -> None:
    """Deterministic kernels everywhere; TF32 matmuls keep bf16 products exact.

    bf16 values carry 8 significant bits and TF32 inputs carry 11, so a TF32
    matmul of bf16-valued fp32 tensors forms every product exactly and
    accumulates in fp32. It equals an fp32 matmul up to summation order.
    """

    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = allow_tf32
    torch.backends.cudnn.allow_tf32 = allow_tf32


def derive_seed(*parts: object) -> int:
    """A 63-bit seed from a stable SHA-256 of the parts (never Python's hash())."""

    payload = "|".join(str(part) for part in parts).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & ((1 << 63) - 1)


# --------------------------------------------------------------------------- #
# Teacher capture
# --------------------------------------------------------------------------- #

_ACTIVE_SESSION: CaptureSession | None = None
_REGISTERED = False


def _capture_attention(module: nn.Module, query: Tensor, key: Tensor, value: Tensor,
                       attention_mask: Tensor | None, **kwargs: Any) -> tuple[Tensor, Any]:
    from transformers.integrations.sdpa_attention import sdpa_attention_forward

    session = _ACTIVE_SESSION
    if session is not None:
        session._observe(module, query, key, value)
    output, weights = sdpa_attention_forward(module, query, key, value, attention_mask, **kwargs)
    if session is not None:
        session._observe_output(module, output)
    return output, weights


def register_capture_implementation() -> None:
    """Register the capture attention and its mask builder under one name.

    The mask registration matters: an unregistered implementation name gets
    ``attention_mask=None``, which is wrong for KV-cache continuation.
    """

    global _REGISTERED
    if _REGISTERED:
        return
    from transformers import AttentionInterface
    from transformers.masking_utils import AttentionMaskInterface, sdpa_mask

    AttentionInterface.register(CAPTURE_IMPLEMENTATION, _capture_attention)
    AttentionMaskInterface.register(CAPTURE_IMPLEMENTATION, sdpa_mask)
    _REGISTERED = True


class CaptureSession:
    """Capture post-RoPE queries/keys and attention inputs of selected layers.

    ``query_rows`` (absolute positions) keeps only those query rows; ``None``
    keeps every row. ``keep_values`` additionally keeps values and the SDPA
    output rows, which the smoke check uses to verify that recomputed
    probabilities reproduce the attention output the model produced.
    """

    def __init__(
        self,
        model: nn.Module,
        layers: Iterable[int],
        *,
        query_rows: Tensor | None = None,
        keep_values: bool = False,
    ) -> None:
        self.model = model
        self.layers = frozenset(int(layer) for layer in layers)
        self.query_rows = query_rows
        self.keep_values = keep_values
        self.recording = True
        self.query: dict[int, Tensor] = {}
        self.key: dict[int, Tensor] = {}
        self.value: dict[int, Tensor] = {}
        self.output: dict[int, Tensor] = {}
        self.hidden: dict[int, Tensor] = {}
        self._hooks: list[Any] = []

    def __enter__(self) -> CaptureSession:
        global _ACTIVE_SESSION
        if _ACTIVE_SESSION is not None:
            raise TorchContractError("a capture session is already active")
        register_capture_implementation()
        decoder = _decoder(self.model)
        for layer in sorted(self.layers):
            attention = decoder.layers[layer].self_attn
            self._hooks.append(
                attention.register_forward_pre_hook(self._make_hidden_hook(layer), with_kwargs=True)
            )
        _ACTIVE_SESSION = self
        return self

    def __exit__(self, *exc: object) -> None:
        global _ACTIVE_SESSION
        for hook in self._hooks:
            hook.remove()
        self._hooks.clear()
        _ACTIVE_SESSION = None

    @contextmanager
    def paused(self) -> Iterator[None]:
        previous = self.recording
        self.recording = False
        try:
            yield
        finally:
            self.recording = previous

    def clear(self) -> None:
        for store in (self.query, self.key, self.value, self.output, self.hidden):
            store.clear()

    def _make_hidden_hook(self, layer: int):
        def hook(module: nn.Module, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
            if not self.recording:
                return
            hidden = kwargs.get("hidden_states", args[0] if args else None)
            if hidden is None:
                raise TorchContractError("attention pre-hook saw no hidden_states")
            self.hidden[layer] = hidden.detach()

        return hook

    def _observe(self, module: nn.Module, query: Tensor, key: Tensor, value: Tensor) -> None:
        layer = int(module.layer_idx)
        if not self.recording or layer not in self.layers:
            return
        query = query.detach()
        if self.query_rows is not None:
            query = query.index_select(2, self.query_rows.to(query.device))
        self.query[layer] = query
        self.key[layer] = key.detach()
        if self.keep_values:
            self.value[layer] = value.detach()

    def _observe_output(self, module: nn.Module, output: Tensor) -> None:
        layer = int(module.layer_idx)
        if not self.recording or not self.keep_values or layer not in self.layers:
            return
        # sdpa_attention_forward returns (batch, T, heads, head_dim).
        output = output.detach()
        if self.query_rows is not None:
            output = output.index_select(1, self.query_rows.to(output.device))
        self.output[layer] = output


def _decoder(model: nn.Module) -> nn.Module:
    decoder = getattr(model, "model", model)
    if not hasattr(decoder, "layers"):
        raise TorchContractError("model has no decoder layers")
    return decoder


def load_teacher(
    model_dir: str | Path,
    device: str | torch.device,
    *,
    dtype: torch.dtype = torch.bfloat16,
    max_layer: int | None = None,
    attn_implementation: str = CAPTURE_IMPLEMENTATION,
) -> nn.Module:
    """Load the frozen teacher; optionally run the decoder only through ``max_layer``."""

    from transformers import AutoModelForCausalLM

    if attn_implementation == CAPTURE_IMPLEMENTATION:
        register_capture_implementation()
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        dtype=dtype,
        attn_implementation=attn_implementation,
        local_files_only=True,
    )
    model.requires_grad_(False)
    model.eval()
    if max_layer is not None:
        total = int(model.config.num_hidden_layers)
        if not 0 <= max_layer < total:
            raise TorchContractError("max_layer is outside the decoder")
        model.config.num_hidden_layers = max_layer + 1
    return model.to(device)


def head_probs_rows(query_rows: Tensor, key: Tensor, rows: Tensor, scaling: float) -> Tensor:
    """Exact causal softmax probabilities ``(Hq, R, T)`` in fp32 for absolute ``rows``.

    ``query_rows`` is ``(Hq, R, d)`` (post-norm, post-RoPE) and ``key`` is
    ``(Hkv, T, d)``. Query head ``h`` reads key head ``h // (Hq / Hkv)``, which
    is the grouping of ``transformers``' ``repeat_kv``.
    """

    if query_rows.ndim != 3 or key.ndim != 3:
        raise TorchContractError("query_rows must be (Hq, R, d) and key (Hkv, T, d)")
    heads_q, n_rows, dim = query_rows.shape
    heads_kv, length, key_dim = key.shape
    if key_dim != dim or heads_q % heads_kv:
        raise TorchContractError("query/key head shapes are incompatible")
    rows = rows.to(device=key.device, dtype=torch.long)
    if rows.shape != (n_rows,):
        raise TorchContractError("rows must label every query row")
    if n_rows and (int(rows.min()) < 0 or int(rows.max()) >= length):
        raise TorchContractError("query rows must lie inside the key sequence")
    groups = heads_q // heads_kv
    q = query_rows.float().reshape(heads_kv, groups * n_rows, dim)
    scores = torch.matmul(q, key.float().transpose(-1, -2)).reshape(heads_q, n_rows, length)
    scores = scores * float(scaling)
    future = torch.arange(length, device=key.device)[None, :] > rows[:, None]
    scores = scores.masked_fill(future[None], float("-inf"))
    return torch.softmax(scores, dim=-1)


# --------------------------------------------------------------------------- #
# Block targets
# --------------------------------------------------------------------------- #


def complete_block_mask(rows: Tensor, n_blocks: int, block_size: int = BLOCK_SIZE) -> Tensor:
    """``(R, nB)``: block ``b`` is complete for row ``i`` when ``r * b + r - 1 <= i``."""

    blocks = torch.arange(n_blocks, device=rows.device)
    return (blocks[None, :] * block_size + block_size - 1) <= rows[:, None]


def _renormalise(values: Tensor, valid: Tensor) -> tuple[Tensor, Tensor]:
    masked = torch.where(valid, values, torch.zeros_like(values))
    total = masked.sum(dim=-1, keepdim=True)
    ok = total.squeeze(-1) > 0
    return torch.where(total > 0, masked / total.clamp_min(_TINY), torch.zeros_like(masked)), ok


def block_targets(
    probs: Tensor,
    rows: Tensor,
    *,
    block_size: int = BLOCK_SIZE,
    include_hm: bool = False,
) -> dict[str, Tensor]:
    """Registered block targets from per-head probabilities ``(H, R, T)``.

    Returns ``hs``, ``mp`` (and ``hm`` when asked) as ``(R, nB)`` row
    distributions over complete blocks, plus ``valid`` (complete-block mask)
    and ``row_ok`` (rows with at least one complete block, i.e. ``i >= r - 1``).
    """

    if probs.ndim != 3:
        raise TorchContractError("probs must be (heads, rows, T)")
    _, n_rows, length = probs.shape
    n_blocks = length // block_size
    if n_blocks < 1:
        raise TorchContractError("sequence is shorter than one block")
    rows = rows.to(device=probs.device, dtype=torch.long)
    head_sum = probs.sum(dim=0)
    head_sum = head_sum / head_sum.sum(dim=-1, keepdim=True).clamp_min(_TINY)
    blocks = head_sum[:, : n_blocks * block_size].reshape(n_rows, n_blocks, block_size)
    valid = complete_block_mask(rows, n_blocks, block_size)
    hs, row_ok = _renormalise(blocks.sum(dim=-1), valid)
    mp, _ = _renormalise(blocks.amax(dim=-1), valid)
    out = {"hs": hs, "mp": mp, "valid": valid, "row_ok": row_ok}
    if include_hm:
        head_max = probs.amax(dim=0)[:, : n_blocks * block_size]
        hm, _ = _renormalise(head_max.reshape(n_rows, n_blocks, block_size).sum(dim=-1), valid)
        out["hm"] = hm
    return out


# --------------------------------------------------------------------------- #
# Indexer
# --------------------------------------------------------------------------- #


def rotary_cos_sin(
    positions: Tensor, rope_dims: int, theta: float, device: torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> tuple[Tensor, Tensor]:
    """``rotate_half`` convention (as in Qwen3); angles formed in float64."""

    if rope_dims % 2 or rope_dims <= 0:
        raise TorchContractError("rope_dims must be a positive even number")
    device = device or positions.device
    exponent = torch.arange(0, rope_dims, 2, dtype=torch.float64, device=device) / rope_dims
    inv_freq = 1.0 / (theta**exponent)
    angles = positions.to(device=device, dtype=torch.float64)[:, None] * inv_freq[None, :]
    emb = torch.cat([angles, angles], dim=-1)
    return emb.cos().to(dtype), emb.sin().to(dtype)


def apply_rotary(x: Tensor, cos: Tensor, sin: Tensor) -> Tensor:
    """Rotate the first ``cos.shape[-1]`` dims of ``x`` (positions on dim -2)."""

    rope_dims = cos.shape[-1]
    rotated, passthrough = x[..., :rope_dims], x[..., rope_dims:]
    half = rope_dims // 2
    turned = torch.cat([-rotated[..., half:], rotated[..., :half]], dim=-1)
    out = rotated * cos + turned * sin
    return torch.cat([out, passthrough], dim=-1) if passthrough.shape[-1] else out


def _rms_norm(x: Tensor, weight: Tensor, eps: float = INDEXER_NORM_EPS) -> Tensor:
    return x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + eps) * weight


@dataclass(frozen=True, slots=True)
class IndexerSpec:
    d_model: int = 1024
    heads: int = INDEXER_HEADS
    dim: int = INDEXER_DIM
    rope_dims: int = INDEXER_ROPE_DIMS
    rope_theta: float = INDEXER_ROPE_THETA
    block_size: int = BLOCK_SIZE

    def __post_init__(self) -> None:
        if self.rope_dims > self.dim or self.rope_dims % 2:
            raise TorchContractError("rope_dims must be even and at most the indexer dim")
        for name in ("d_model", "heads", "dim", "block_size"):
            if getattr(self, name) <= 0:
                raise TorchContractError(f"{name} must be positive")


class BlockIndexer(nn.Module):
    """Block-form indexer: QSA Eq. 12-16 plus the DSA per-head gate.

    ``I_{i,b} = sum_j w_{i,j} ReLU(<q_i^j, kbar_b>) / sqrt(d)`` on complete
    blocks ``b`` (``r b + r - 1 <= i``), where ``q_i^j = RoPE_i(RMSNorm(W_Q^j x_i))``,
    ``kbar_b = RoPE_{r b}(RMSNorm(mean_{s in b} W_K x_s))`` and
    ``w_{i,j} = b_j + x_i W_w[:, j]``. The ``1/sqrt(d)`` factor is a fixed
    reparametrisation (ReLU is positively homogeneous), not a new function class.
    """

    def __init__(self, spec: IndexerSpec, generator: torch.Generator | None = None) -> None:
        super().__init__()
        self.spec = spec
        std = 1.0 / math.sqrt(spec.d_model)
        wq = torch.randn(spec.heads * spec.dim, spec.d_model, generator=generator) * std
        wk = torch.randn(spec.dim, spec.d_model, generator=generator) * std
        self.wq = nn.Parameter(wq)
        self.wk = nn.Parameter(wk)
        self.gate_w = nn.Parameter(torch.zeros(spec.heads, spec.d_model))
        self.gate_b = nn.Parameter(torch.ones(spec.heads))
        self.q_norm = nn.Parameter(torch.ones(spec.dim))
        self.k_norm = nn.Parameter(torch.ones(spec.dim))

    @classmethod
    def initialised(cls, spec: IndexerSpec, seed: int, layer: int, target: str) -> BlockIndexer:
        """Init depends on (seed, layer, target) only, so the LR sweep is paired."""

        generator = torch.Generator(device="cpu").manual_seed(
            derive_seed("k1-indexer-init", seed, layer, target)
        )
        return cls(spec, generator)

    def block_keys(self, hidden: Tensor) -> Tensor:
        """``(nB, d)`` pooled, normalised, rotated keys for the complete blocks of ``hidden``."""

        spec = self.spec
        length = hidden.shape[0]
        n_blocks = length // spec.block_size
        dtype = self.wk.dtype
        keys = hidden[: n_blocks * spec.block_size].to(dtype) @ self.wk.T
        pooled = keys.reshape(n_blocks, spec.block_size, spec.dim).mean(dim=1)
        pooled = _rms_norm(pooled, self.k_norm)
        positions = torch.arange(n_blocks, device=hidden.device) * spec.block_size
        cos, sin = rotary_cos_sin(positions, spec.rope_dims, spec.rope_theta, hidden.device,
                                  dtype)
        return apply_rotary(pooled, cos, sin)

    def queries(self, hidden_rows: Tensor, rows: Tensor) -> tuple[Tensor, Tensor]:
        spec = self.spec
        x = hidden_rows.to(self.wq.dtype)
        q = (x @ self.wq.T).reshape(-1, spec.heads, spec.dim).transpose(0, 1)
        q = _rms_norm(q, self.q_norm)
        cos, sin = rotary_cos_sin(rows, spec.rope_dims, spec.rope_theta, hidden_rows.device,
                                  x.dtype)
        q = apply_rotary(q, cos[None], sin[None])
        gates = self.gate_b[None, :] + x @ self.gate_w.T
        return q, gates

    def forward(self, hidden: Tensor, rows: Tensor) -> tuple[Tensor, Tensor]:
        """Scores ``(R, nB)`` (``-inf`` on incomplete blocks) and the validity mask."""

        if hidden.ndim != 2 or hidden.shape[1] != self.spec.d_model:
            raise TorchContractError("hidden must be (T, d_model)")
        rows = rows.to(device=hidden.device, dtype=torch.long)
        keys = self.block_keys(hidden)
        q, gates = self.queries(hidden.index_select(0, rows), rows)
        logits = torch.matmul(q, keys.T) / math.sqrt(self.spec.dim)
        scores = torch.einsum("rh,hrb->rb", gates, F.relu(logits))
        valid = complete_block_mask(rows, keys.shape[0], self.spec.block_size)
        return scores.masked_fill(~valid, float("-inf")), valid


def indexer_parameter_count(spec: IndexerSpec | None = None) -> int:
    return sum(p.numel() for p in BlockIndexer(spec or IndexerSpec()).parameters())


def kl_block_loss(target: Tensor, scores: Tensor, valid: Tensor) -> tuple[Tensor, int]:
    """Mean over rows with a complete block of ``KL(target || softmax(scores))``."""

    if target.shape != scores.shape or valid.shape != scores.shape:
        raise TorchContractError("target, scores and valid must share (R, nB)")
    rows_ok = valid.any(dim=-1)
    count = int(rows_ok.sum())
    if count == 0:
        raise TorchContractError("no row has a complete block")
    dtype = torch.promote_types(scores.dtype, torch.float32)
    p = target[rows_ok].to(dtype)
    mask = valid[rows_ok]
    log_q = torch.log_softmax(scores[rows_ok].to(dtype), dim=-1).masked_fill(~mask, 0.0)
    terms = torch.xlogy(p, p) - p * log_q
    return terms.sum() / count, count


# --------------------------------------------------------------------------- #
# Selection, recall and references
# --------------------------------------------------------------------------- #


def select_top_blocks(scores: Tensor, valid: Tensor, k_blocks: int = BLOCK_BUDGET) -> Tensor:
    """``(R, k)`` block ids by descending score, lower index first on ties; ``-1`` pads."""

    if k_blocks <= 0:
        raise TorchContractError("k_blocks must be positive")
    masked = scores.float().masked_fill(~valid, float("-inf"))
    order = torch.sort(masked, dim=-1, descending=True, stable=True).indices
    width = min(k_blocks, order.shape[-1])
    chosen = order[:, :width]
    available = valid.sum(dim=-1, keepdim=True)
    rank = torch.arange(width, device=scores.device)[None, :]
    chosen = torch.where(rank < available, chosen, torch.full_like(chosen, -1))
    if width < k_blocks:
        pad = torch.full((chosen.shape[0], k_blocks - width), -1, dtype=chosen.dtype,
                         device=chosen.device)
        chosen = torch.cat([chosen, pad], dim=-1)
    return chosen


def boundary_ties(scores: Tensor, valid: Tensor, k_blocks: int = BLOCK_BUDGET) -> int:
    """Rows whose k-th and (k+1)-th valid scores tie, so the tie-break decided selection."""

    masked = scores.float().masked_fill(~valid, float("-inf"))
    ordered = torch.sort(masked, dim=-1, descending=True).values
    if ordered.shape[-1] <= k_blocks:
        return 0
    kth, nxt = ordered[:, k_blocks - 1], ordered[:, k_blocks]
    return int(((kth == nxt) & torch.isfinite(nxt)).sum())


def needle_block_cover(
    n_blocks: int, needle_start: int, needle_end: int, block_size: int = BLOCK_SIZE,
    device: torch.device | str = "cpu",
) -> Tensor:
    """Needle tokens inside each block (``needle_end`` exclusive)."""

    if not 0 <= needle_start < needle_end:
        raise TorchContractError("needle span must be non-empty and non-negative")
    starts = torch.arange(n_blocks, device=device) * block_size
    lo = torch.clamp(starts, min=needle_start)
    hi = torch.clamp(starts + block_size, max=needle_end)
    return torch.clamp(hi - lo, min=0)


def _tail_overlap(rows: Tensor, needle_start: int, needle_end: int, block_size: int) -> Tensor:
    tail_start = ((rows + 1) // block_size) * block_size
    lo = torch.clamp(tail_start, min=needle_start)
    hi = torch.clamp(rows + 1, max=needle_end)
    return torch.clamp(hi - lo, min=0)


def block_selection_recall(
    chosen: Tensor, rows: Tensor, needle_start: int, needle_end: int,
    block_size: int = BLOCK_SIZE,
) -> Tensor:
    """Per-row ``|S_i ∩ N| / |N|`` where ``S_i`` = chosen blocks plus the tail block."""

    rows = rows.to(device=chosen.device, dtype=torch.long)
    if int(rows.min()) < needle_end:
        raise TorchContractError("every needle token must precede every query row")
    n_blocks = max(int(chosen.max()) + 1 if chosen.numel() else 1, 1)
    cover = needle_block_cover(n_blocks, needle_start, needle_end, block_size, chosen.device)
    gathered = torch.where(chosen >= 0, cover[chosen.clamp_min(0)], torch.zeros_like(chosen))
    hits = gathered.sum(dim=-1) + _tail_overlap(rows, needle_start, needle_end, block_size)
    return hits.float() / float(needle_end - needle_start)


def union_topk_recall(
    probs: Tensor, rows: Tensor, k_per_head: int, needle_start: int, needle_end: int
) -> Tensor:
    """Needle recall of the union over heads of each head's own causal top-k tokens."""

    heads, n_rows, length = probs.shape
    rows = rows.to(device=probs.device, dtype=torch.long)
    if int(rows.min()) < needle_end:
        raise TorchContractError("every needle token must precede every query row")
    future = torch.arange(length, device=probs.device)[None, :] > rows[:, None]
    masked = probs.float().masked_fill(future[None], -1.0)
    width = min(k_per_head, length)
    top = torch.sort(masked, dim=-1, descending=True, stable=True).indices[..., :width]
    visible = (rows + 1)[None, :, None]
    rank = torch.arange(width, device=probs.device)[None, None, :]
    in_needle = (top >= needle_start) & (top < needle_end) & (rank < visible)
    sentinel = torch.full_like(top, length)
    positions = torch.where(in_needle, top, sentinel).permute(1, 0, 2).reshape(n_rows, -1)
    ordered = torch.sort(positions, dim=-1).values
    first = (ordered[:, :1] < length).long().squeeze(-1)
    distinct = ((ordered[:, 1:] != ordered[:, :-1]) & (ordered[:, 1:] < length)).sum(dim=-1)
    return (first + distinct).float() / float(needle_end - needle_start)


def random_block_recall(
    rows: Tensor, needle_start: int, needle_end: int, k_blocks: int = BLOCK_BUDGET,
    block_size: int = BLOCK_SIZE,
) -> Tensor:
    """Analytic expected recall of a uniformly random choice of ``k`` complete blocks."""

    rows = rows.to(dtype=torch.long)
    n_complete = (rows + 1) // block_size
    covered_blocks = torch.clamp(n_complete * block_size, max=needle_end) - needle_start
    in_complete = torch.clamp(covered_blocks, min=0).float()
    fraction = torch.clamp(k_blocks / n_complete.float().clamp_min(1.0), max=1.0)
    tail = _tail_overlap(rows, needle_start, needle_end, block_size).float()
    return (in_complete * fraction + tail) / float(needle_end - needle_start)


def ratio_retention(indexer: float, target: float, random: float, floor: float = 1e-9) -> float:
    """``G = (R_ind - R_rand) / (R_T - R_rand)``; NaN when the target has no headroom."""

    for value in (indexer, target, random):
        if not math.isfinite(value):
            raise TorchContractError("recalls must be finite")
    headroom = target - random
    if headroom <= floor:
        return float("nan")
    return (indexer - random) / headroom


# --------------------------------------------------------------------------- #
# Small helpers used by the entry point and the doctor
# --------------------------------------------------------------------------- #


def state_digest(tensors: dict[str, Tensor]) -> str:
    """SHA-256 over sorted names, dtypes, shapes and raw bytes (bitwise identity)."""

    digest = hashlib.sha256()
    for name in sorted(tensors):
        tensor = tensors[name].detach().contiguous().cpu()
        digest.update(name.encode())
        digest.update(str(tensor.dtype).encode())
        digest.update(str(tuple(tensor.shape)).encode())
        digest.update(tensor.view(torch.uint8).numpy().tobytes() if tensor.numel() else b"")
    return digest.hexdigest()


def balanced_layer_shards(n_layers: int, n_workers: int) -> list[list[int]]:
    """Contiguous layer shards balancing ``sum over owned layers of (prefix forward + training)``.

    A worker owning layers ``[a, b]`` runs the teacher through layer ``b`` and
    trains ``b - a + 1`` layers. With equal per-layer training cost ``c`` and
    forward cost 1 per layer, the cost is ``(b + 1) + c (b - a + 1)``. Training
    dominates (``c`` about 3), which gives the registered 0.6B split
    [0-7], [8-14], [15-21], [22-27].
    """

    if n_workers <= 0 or n_layers < n_workers:
        raise TorchContractError("need at least one layer per worker")
    if (n_layers, n_workers) == (28, 4):
        return [list(range(0, 8)), list(range(8, 15)), list(range(15, 22)), list(range(22, 28))]
    bounds = [round(n_layers * w / n_workers) for w in range(n_workers + 1)]
    return [list(range(bounds[w], bounds[w + 1])) for w in range(n_workers)]


def as_long(values: Sequence[int] | Tensor, device: torch.device | str = "cpu") -> Tensor:
    return torch.as_tensor(values, dtype=torch.long, device=device)


__all__ = [
    "BLOCK_BUDGET",
    "BLOCK_SIZE",
    "CAPTURE_IMPLEMENTATION",
    "DENSE_SELECTORS",
    "INDEXER_DIM",
    "INDEXER_HEADS",
    "INDEXER_ROPE_DIMS",
    "INDEXER_ROPE_THETA",
    "SINK_TOKEN_ID",
    "TOKEN_BUDGET",
    "TRAINED_TARGETS",
    "UNION_BUDGET_MATCHED_K",
    "UNION_K_PER_HEAD",
    "BlockIndexer",
    "CaptureSession",
    "IndexerSpec",
    "TorchContractError",
    "apply_rotary",
    "as_long",
    "balanced_layer_shards",
    "block_selection_recall",
    "block_targets",
    "boundary_ties",
    "complete_block_mask",
    "derive_seed",
    "head_probs_rows",
    "indexer_parameter_count",
    "kl_block_loss",
    "load_teacher",
    "needle_block_cover",
    "random_block_recall",
    "ratio_retention",
    "register_capture_implementation",
    "rotary_cos_sin",
    "select_top_blocks",
    "set_determinism",
    "state_digest",
    "union_topk_recall",
]
