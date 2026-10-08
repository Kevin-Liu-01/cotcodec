"""A2: held-out value distributions for the independent audit.

Each distribution replaces every floating tensor returned by the problem's
``get_inputs()`` (same shapes and dtypes); integer and bool tensors and
non-tensor values are left unchanged. The draws are seeded per distribution
(``channel_seed(4042, replicate, index)``) and, like gate (c), every draw
passes a validity gate before it counts (see ``audit/run.py``).

| name | values |
|---|---|
| ``randn`` | standard normal |
| ``uniform8`` | U[-8, 8] |
| ``samesign100`` | U[0, 1) x 100 (all positive) |
| ``spiky`` | U[0, 1); 0.1% of entries (at least one) and the last element along |
| | every axis multiplied by 1000 |
| ``ties`` | U[-4, 4] rounded to multiples of 1/8 (many exact ties) |
| ``allneg`` | every entry in [-1, -0.001] (all-negative rows) |
| ``constrows`` | each row along the last axis is one normal value repeated |
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import torch

A2_BASE = 4042


def _randn(t: torch.Tensor) -> torch.Tensor:
    return torch.randn(t.shape, dtype=t.dtype)


def _uniform8(t: torch.Tensor) -> torch.Tensor:
    return torch.rand(t.shape, dtype=t.dtype) * 16.0 - 8.0


def _samesign100(t: torch.Tensor) -> torch.Tensor:
    return torch.rand(t.shape, dtype=t.dtype) * 100.0


def _spiky(t: torch.Tensor) -> torch.Tensor:
    out = torch.rand(t.shape, dtype=t.dtype)
    if out.numel() == 0:
        return out
    flat = out.view(-1)
    count = max(1, out.numel() // 1000)
    positions = torch.randperm(out.numel())[:count]
    flat[positions] *= 1000.0
    for axis in range(out.dim()):
        index = [0] * out.dim()
        index[axis] = out.shape[axis] - 1
        out[tuple(index)] *= 1000.0
    flat[-1] *= 1000.0
    return out


def _ties(t: torch.Tensor) -> torch.Tensor:
    return torch.round((torch.rand(t.shape, dtype=t.dtype) * 8.0 - 4.0) * 8.0) / 8.0


def _allneg(t: torch.Tensor) -> torch.Tensor:
    return -(torch.rand(t.shape, dtype=t.dtype) * 0.999 + 0.001)


def _constrows(t: torch.Tensor) -> torch.Tensor:
    if t.dim() == 0:
        return torch.randn((), dtype=t.dtype)
    rows = torch.randn((*t.shape[:-1], 1), dtype=t.dtype)
    return rows.expand(t.shape).contiguous()


DISTRIBUTIONS: dict[str, Callable[[torch.Tensor], torch.Tensor]] = {
    "randn": _randn,
    "uniform8": _uniform8,
    "samesign100": _samesign100,
    "spiky": _spiky,
    "ties": _ties,
    "allneg": _allneg,
    "constrows": _constrows,
}


def apply_distribution(inputs: Sequence[Any], name: str) -> list[Any]:
    """Replace floating tensors with draws from ``name`` (call after seeding)."""
    fn = DISTRIBUTIONS[name]
    return [fn(x) if isinstance(x, torch.Tensor) and x.is_floating_point() else x for x in inputs]
