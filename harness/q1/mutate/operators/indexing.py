"""Indexing family: axis, block-extent, stride and decode confusions.

CUDA's thread-index rules (``tidx2tidy``), warp-size and shared-memory tree
rules have no Triton counterpart (the language has no thread index, warp or
explicit shared memory); see the mapping table in ``rules.py``.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from harness.q1.mutate.operators._base import (
    BLOCK_PTR,
    LOAD,
    Candidate,
    Operator,
    ScopeContext,
    arg,
)
from harness.q1.mutate.source import parent


def _program_id_axis(ctx: ScopeContext, node: ast.AST, depth: int = 3) -> int | None:
    """Axis of the ``tl.program_id`` a program-index expression derives from.

    Matches ``tl.program_id(a)`` itself and names bound (once) to expressions
    containing it, such as ``pid_m = pid // num_pid_n`` in grouped matmuls.
    """
    if depth < 0:
        return None
    if isinstance(node, ast.Name):
        bound = ctx.binding(node.id)
        return _program_id_axis(ctx, bound, depth - 1) if bound is not None else None
    if isinstance(node, ast.Call) and ctx.name_of(node) == "tl.program_id":
        axis = ctx.const(arg(node, 0, "axis"))
        return int(axis) if axis is not None else None
    if isinstance(node, ast.BinOp):
        for side in (node.left, node.right):
            axis = _program_id_axis(ctx, side, depth - 1)
            if axis is not None:
                return axis
    return None


def _program_id_axis_swap(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls({"tl.program_id"}):
        axis_node = arg(call, 0, "axis")
        axis = ctx.const(axis_node)
        if axis_node is None or axis is None:
            continue
        new_axis = 1 if int(axis) == 0 else 0
        yield Candidate(call, (ctx.edit(axis_node, str(new_axis)),))


def _pid_block_products(ctx: ScopeContext) -> Iterator[tuple[ast.Name, int]]:
    """Yield (block-size Name, axis) for ``pid * BLOCK`` products."""
    for node in ctx.nodes:
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult)):
            continue
        for pid_side, block_side in ((node.left, node.right), (node.right, node.left)):
            axis = _program_id_axis(ctx, pid_side)
            if (
                axis is not None
                and isinstance(block_side, ast.Name)
                and block_side.id in ctx.constexpr_params
            ):
                yield block_side, axis


def _block_to_num_programs(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    if tl is None:
        return
    for name, axis in _pid_block_products(ctx):
        yield Candidate(name, (ctx.edit(name, f"{tl}.num_programs({axis})"),))


def _block_size_swap(ctx: ScopeContext) -> Iterator[Candidate]:
    blocks = [p for p in ctx.constexpr_params if "BLOCK" in p.upper()]
    for name, _axis in _pid_block_products(ctx):
        other = ctx.partner(blocks, name.id)
        if other is not None:
            yield Candidate(name, (ctx.edit(name, other),), detail=f"{name.id}->{other}")


def _is_block_pointer(ctx: ScopeContext, node: ast.AST) -> bool:
    resolved = ctx.resolve(node, depth=2)
    return isinstance(resolved, ast.Call) and ctx.name_of(resolved) in BLOCK_PTR


def _load_offset_off1(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls(LOAD):
        pointer = arg(call, 0, "pointer")
        if pointer is None or _is_block_pointer(ctx, pointer):
            continue
        yield Candidate(pointer, (ctx.edit(pointer, f"({ctx.wseg(pointer)} + 1)"),))


def _name_swap(pool_attr: str, context: str):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        pool = getattr(ctx, pool_attr)
        for node in ctx.nodes:
            if not (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)):
                continue
            if node.id not in pool:
                continue
            up = parent(node)
            if context == "mult" and not (
                isinstance(up, ast.BinOp) and isinstance(up.op, ast.Mult)
            ):
                continue
            if context == "decode" and not (
                isinstance(up, ast.BinOp)
                and isinstance(up.op, ast.Mod | ast.FloorDiv)
                and up.right is node
            ):
                continue
            other = ctx.partner(pool, node.id)
            if other is not None:
                yield Candidate(node, (ctx.edit(node, other),), detail=f"{node.id}->{other}")

    return finder


def _launch_stride_swap(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Subscript)):
            continue  # Triton launches look like kernel[grid](...)
        for value in [*node.args, *(kw.value for kw in node.keywords)]:
            for sub in ast.walk(value):
                if (
                    isinstance(sub, ast.Call)
                    and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == "stride"
                    and len(sub.args) == 1
                    and isinstance(sub.args[0], ast.Constant)
                    and isinstance(sub.args[0].value, int)
                    and not isinstance(sub.args[0].value, bool)
                    and sub.args[0].value >= 0
                ):
                    dim = sub.args[0].value
                    new_dim = 1 if dim == 0 else dim - 1
                    yield Candidate(sub, (ctx.edit(sub.args[0], str(new_dim)),))


OPERATORS = (
    Operator(
        "program-id-axis-swap",
        "indexing",
        "paper",
        "bidx2bidy",
        ("device",),
        "Wrong grid axis at one tl.program_id site (axis 0 <-> 1).",
        _program_id_axis_swap,
    ),
    Operator(
        "block-size-to-num-programs",
        "indexing",
        "paper",
        "bdim2gdim",
        ("device",),
        "In pid * BLOCK index math, the block extent becomes tl.num_programs(axis) "
        "(the Triton analogue of blockDim -> gridDim).",
        _block_to_num_programs,
    ),
    Operator(
        "block-size-swap",
        "indexing",
        "paper",
        "grid-x-use-block-y",
        ("device",),
        "In pid * BLOCK index math, the block extent is replaced by another BLOCK "
        "constexpr of the same kernel (the analogue of using blockDim.y for x).",
        _block_size_swap,
    ),
    Operator(
        "load-offset-off1",
        "indexing",
        "paper",
        "smem-index-off1",
        ("device",),
        "One tl.load reads one element past its intended address. The paper rule "
        "offsets a shared-memory partner index; Triton has no explicit shared memory, "
        "so the port offsets a global load pointer.",
        _load_offset_off1,
    ),
    Operator(
        "stride-param-swap",
        "indexing",
        "paper",
        "row-store-stride-k",
        ("device",),
        "One use of a stride argument is replaced by another stride argument.",
        _name_swap("stride_params", "any"),
        ports=("a-row-stride-n", "b-row-stride-k"),
    ),
    Operator(
        "dim-param-swap-index",
        "indexing",
        "paper",
        "row-store-stride-k",
        ("device",),
        "One dimension argument used as a multiplier in index math is replaced by "
        "another dimension argument (row * N -> row * K).",
        _name_swap("dim_params", "mult"),
        ports=("a-row-stride-n", "b-row-stride-k"),
    ),
    Operator(
        "dim-param-swap-decode",
        "indexing",
        "paper",
        "flatten-height-use-width",
        ("device",),
        "One dimension argument used to decode a flat index (% or //) is replaced "
        "by another dimension argument.",
        _name_swap("dim_params", "decode"),
        ports=("output-position-height-first",),
    ),
    Operator(
        "launch-stride-swap",
        "indexing",
        "paper",
        "row-store-stride-k",
        ("launch",),
        "One tensor.stride(d) argument of a kernel launch uses the neighbouring dimension.",
        _launch_stride_swap,
        ports=("a-row-stride-n", "b-row-stride-k"),
    ),
)
