"""Dense-only evaluation of q3-dense-headroom-precheck-v2 (torch).

v1's evaluation (``harness/dense_headroom_torch.py``, imported unchanged) with
three changes that do not change any computed quantity:

* The selectors are v1's ``select_unit`` itself, called with the literal
  selector's block scores already on the device (v1 moved them inside the
  layer loop; the values and the dtype are the same).
* A hybrid model's prompt cache is copied per option by ``clone_cache``: the
  same tensors cloned (values, strides, Python attributes) into new layer
  objects, in place of ``copy.deepcopy`` of the whole cache object graph. The
  forward that follows reads the same values.
* An option's first-token index is read from its host token array, not from
  the device (v1 synchronised on ``int(ids[0, 0])``); it is the same index.

``evaluate_unit`` takes an optional ``UnitTimer``: the development timing job
passes one, which synchronises the device at component boundaries and records
wall and process CPU time per component. The lanes pass none, so no
synchronisation is added. Bit-for-bit equality with v1 on every selector,
statistic and receipt field is tested on tiny models
(``tests/test_dense_headroom_v2_torch.py``, the doctor's ``equivalence`` case).
"""

from __future__ import annotations

import copy
import time
from collections.abc import Sequence
from typing import Any

import numpy as np
import torch
from torch import Tensor

from harness import dense_headroom_torch as v1
from harness import sparse_indexer_torch as sit
from harness.sparse_indexer_k1_runtime import _option_scores

UnitOutput = v1.UnitOutput
DenseEvalError = v1.DenseEvalError
attention_layers = v1.attention_layers
is_hybrid = v1.is_hybrid
scaling_of = v1.scaling_of
unit_record = v1.unit_record


class UnitTimer:
    """Wall and process CPU seconds per component of a unit (timing job only).

    ``mark(name)`` closes the component that ran since the previous mark,
    after synchronising the device so that queued GPU work is charged to the
    component that queued it.
    """

    def __init__(self, device: torch.device) -> None:
        self.device = device
        self.parts: dict[str, list[float]] = {}
        self._wall = 0.0
        self._cpu = 0.0
        self.start()

    def _sync(self) -> None:
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)

    def start(self) -> None:
        self._sync()
        self._wall = time.perf_counter()
        self._cpu = time.process_time()

    def mark(self, name: str) -> None:
        self._sync()
        wall, cpu = time.perf_counter(), time.process_time()
        entry = self.parts.setdefault(name, [0.0, 0.0])
        entry[0] += wall - self._wall
        entry[1] += cpu - self._cpu
        self._wall, self._cpu = wall, cpu

    def as_dict(self) -> dict[str, dict[str, float]]:
        return {name: {"wall_s": wall, "cpu_s": cpu} for name, (wall, cpu)
                in sorted(self.parts.items())}


def _clone_value(value: Any) -> Any:
    if isinstance(value, Tensor):
        twin = torch.empty_strided(value.size(), value.stride(), dtype=value.dtype,
                                   device=value.device)
        twin.copy_(value)
        if getattr(value, "__dict__", None):
            twin.__dict__.update(copy.copy(value.__dict__))
        return twin
    if isinstance(value, dict):
        return {key: _clone_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_value(item) for item in value)
    return value


def _clone_layer(layer: Any) -> Any:
    twin = copy.copy(layer)
    for name, value in vars(layer).items():
        object.__setattr__(twin, name, _clone_value(value))
    return twin


def clone_cache(cache: Any) -> Any:
    """A copy of a ``transformers`` cache for one option's forward: every tensor
    a new tensor with the same values, sizes, strides and Python attributes,
    every layer and bookkeeping container a new object, the rest shared."""

    twin = copy.copy(cache)
    for name, value in vars(cache).items():
        if name == "layers":
            object.__setattr__(twin, name, [_clone_layer(layer) for layer in value])
        else:
            object.__setattr__(twin, name, _clone_value(value))
    return twin


def option_scores(model: Any, cache: Any, last_logits: Tensor, options: Sequence[np.ndarray],
                  option_bytes: Sequence[int], prefix: int, device: torch.device,
                  hybrid: bool, timer: UnitTimer | None = None) -> list[float]:
    """K1 v1's acc_norm option scores; a hybrid cache is cloned per option, never cropped."""

    if not hybrid:
        scores = _option_scores(model, cache, last_logits, options, option_bytes, prefix, device)
        if timer is not None:
            timer.mark("mc_options")
        return scores
    first = torch.log_softmax(last_logits.float(), dim=-1)
    scores = []
    for tokens, n_bytes in zip(options, option_bytes, strict=True):
        host = np.asarray(tokens, dtype=np.int64)
        ids = torch.as_tensor(host, device=device)[None]
        total = float(first[int(host[0])])
        if ids.shape[1] > 1:
            branch = clone_cache(cache)
            if timer is not None:
                timer.mark("mc_cache_copy")
            out = model(input_ids=ids[:, :-1], past_key_values=branch, use_cache=True)
            logp = torch.log_softmax(out.logits[0].float(), dim=-1)
            total += float(logp.gather(1, ids[0, 1:, None]).sum())
            del branch, out
            if timer is not None:
                timer.mark("mc_option_forward")
        scores.append(total / max(int(n_bytes), 1))
    return scores


def evaluate_unit(model: Any, tokens: np.ndarray, q0: int, q1: int, n0: int, n1: int, *,
                  layers: Sequence[int], k_blocks: int, fixed_k_blocks: int, scaling: float,
                  do_select: bool, do_mc: bool, options: Sequence[np.ndarray] = (),
                  option_bytes: Sequence[int] = (), answer: int = -1,
                  lex_blocks: np.ndarray | None = None, seeds: Sequence[int] = (),
                  unit_key: str = "", names: Sequence[str] = (), hybrid: bool = False,
                  device: torch.device, timer: UnitTimer | None = None) -> v1.UnitOutput:
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
    if timer is not None:
        timer.mark("inputs")
    with sit.CaptureSession(model, capture_layers, query_rows=rows) as cap, torch.no_grad():
        out = model(input_ids=ids, use_cache=do_mc, past_key_values=cache, logits_to_keep=1)
        if timer is not None:
            timer.mark("prefill_forward")
        if do_select:
            if lex_blocks is None:
                raise DenseEvalError("a selection unit needs the literal selector's blocks")
            lex = torch.as_tensor(lex_blocks, dtype=torch.float32).to(device)
            values, tie_counts, selected, finite = v1.select_unit(
                cap, rows, q0, n0, n1, layers=layers, k_blocks=k_blocks,
                fixed_k_blocks=fixed_k_blocks, scaling=scaling, lex_blocks=lex, seeds=seeds,
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
            if timer is not None:
                timer.mark("select")
        if do_mc:
            with cap.paused():
                mc[:] = option_scores(model, cache, out.logits[0, -1], options, option_bytes,
                                      ids.shape[1], device, hybrid, timer)
                correct = int(answer)
    del cache
    return v1.UnitOutput(recall, ties, max_selected, k_blocks if do_select else 0, mc, correct)


__all__ = [
    "DenseEvalError",
    "UnitOutput",
    "UnitTimer",
    "attention_layers",
    "clone_cache",
    "evaluate_unit",
    "is_hybrid",
    "option_scores",
    "scaling_of",
    "unit_record",
]
