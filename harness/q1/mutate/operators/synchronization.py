"""Synchronization family, reduced to what Triton exposes.

Triton inserts its own barriers, so the CUDA ``__syncthreads``/``__syncwarp``
and named-barrier rules have no direct analogue. What remains is the explicit
``tl.debug_barrier`` and the atomics used for cross-program (split-K style)
reductions.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from harness.q1.mutate.operators._base import (
    Candidate,
    Operator,
    ScopeContext,
    arg,
    is_expression_statement,
)


def _debug_barrier_remove(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls({"tl.debug_barrier"}):
        if is_expression_statement(call):
            statement = call._q1_parent  # type: ignore[attr-defined]
            yield Candidate(call, (ctx.edit(statement, "pass"),))


def _atomic_parts(ctx: ScopeContext, call: ast.Call):
    pointer, value, mask = arg(call, 0, "pointer"), arg(call, 1, "val"), arg(call, 2, "mask")
    if pointer is None or value is None:
        return None
    return pointer, value, mask


def _atomic_add_to_store(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    if tl is None:
        return
    for call in ctx.calls({"tl.atomic_add"}):
        if not is_expression_statement(call) or (parts := _atomic_parts(ctx, call)) is None:
            continue
        pointer, value, mask = parts
        mask_text = f", mask={ctx.seg(mask)}" if mask is not None else ""
        text = f"{tl}.store({ctx.seg(pointer)}, {ctx.seg(value)}{mask_text})"
        yield Candidate(call, (ctx.edit(call, text),))


def _atomic_rmw_split(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    if tl is None:
        return
    for call in ctx.calls({"tl.atomic_add"}):
        if not is_expression_statement(call) or (parts := _atomic_parts(ctx, call)) is None:
            continue
        pointer, value, mask = parts
        mask_text = f", mask={ctx.seg(mask)}" if mask is not None else ""
        old = f"{tl}.load({ctx.seg(pointer)}{mask_text})"
        text = f"{tl}.store({ctx.seg(pointer)}, {old} + {ctx.wseg(value)}{mask_text})"
        yield Candidate(call, (ctx.edit(call, text),))


OPERATORS = (
    Operator(
        "debug-barrier-remove",
        "synchronization",
        "paper",
        "sync-remove",
        ("device",),
        "An explicit tl.debug_barrier() is removed.",
        _debug_barrier_remove,
    ),
    Operator(
        "atomic-add-to-store",
        "synchronization",
        "triton-only",
        None,
        ("device",),
        "A cross-program tl.atomic_add becomes a plain tl.store: concurrent partial "
        "results overwrite each other (lost updates in split-K style reductions).",
        _atomic_add_to_store,
    ),
    Operator(
        "atomic-rmw-split",
        "synchronization",
        "triton-only",
        None,
        ("device",),
        "A tl.atomic_add becomes a non-atomic load-add-store: a race that is visible "
        "only under contention.",
        _atomic_rmw_split,
    ),
)
