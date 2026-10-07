"""Boundary family: guards, masks, ceil division, loop bounds and dimension swaps.

In Triton, bounds guards are mostly load/store masks rather than ``if``
statements, so the CUDA guard rules port to mask edits. Many KernelBench-M
"drop the last element/row/tap/tile" rules are distinct CUDA spellings of one
Triton mutation (mask bound minus one, or loop bound minus one step); they are
recorded as ``ports`` of the operator that subsumes them.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from harness.q1.mutate.operators._base import (
    ATOMICS,
    CDIV,
    LOAD,
    RANGE,
    STORE,
    Candidate,
    Operator,
    ScopeContext,
    arg,
    kwarg,
    rebuild_call,
)
from harness.q1.mutate.operators.semantic import _inf_literal
from harness.q1.mutate.source import parent

_SYMBOL = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
_LOW_PRECEDENCE = (ast.Compare, ast.BoolOp, ast.IfExp, ast.Lambda, ast.NamedExpr)


def _operand(ctx: ScopeContext, node: ast.AST) -> str:
    text = ctx.seg(node)
    return f"({text})" if isinstance(node, _LOW_PRECEDENCE) else text


def _render_compare(ctx: ScopeContext, node: ast.Compare, ops: list[ast.cmpop]) -> str:
    parts = [_operand(ctx, node.left)]
    for op, comparator in zip(ops, node.comparators, strict=True):
        symbol = _SYMBOL.get(type(op))
        if symbol is None:
            raise ValueError("unsupported comparison operator")
        parts.append(f"{symbol} {_operand(ctx, comparator)}")
    return "(" + " ".join(parts) + ")"


def _ror(op_from: type[ast.cmpop], op_to: type[ast.cmpop]):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        for node in ctx.nodes:
            if not isinstance(node, ast.Compare):
                continue
            if any(type(op) not in _SYMBOL for op in node.ops):
                continue
            for index, op in enumerate(node.ops):
                if not isinstance(op, op_from):
                    continue
                ops = list(node.ops)
                ops[index] = op_to()
                text = _render_compare(ctx, node, ops)
                yield Candidate(node.comparators[index], (ctx.edit(node, text),))

    return finder


def _ceil2floor(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if isinstance(node, ast.Call) and ctx.name_of(node) in CDIV and len(node.args) == 2:
            a, b = node.args
            text = f"({ctx.wseg(a)} // {ctx.wseg(b)})"
            yield Candidate(node, (ctx.edit(node, text),), kbm_rule="ceil2floor")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            numerator, divisor = node.left, node.right
            # (a + b - 1) // b
            if (
                isinstance(numerator, ast.BinOp)
                and isinstance(numerator.op, ast.Sub)
                and ctx.is_const(numerator.right, 1.0)
                and isinstance(numerator.left, ast.BinOp)
                and isinstance(numerator.left.op, ast.Add)
                and ctx.seg(numerator.left.right) == ctx.seg(divisor)
            ):
                base = numerator.left.left
                text = f"({ctx.wseg(base)} // {ctx.wseg(divisor)})"
                yield Candidate(node, (ctx.edit(node, text),), kbm_rule="ceil2floor")
            # (a + 255) // 256
            elif (
                isinstance(numerator, ast.BinOp)
                and isinstance(numerator.op, ast.Add)
                and isinstance(numerator.right, ast.Constant)
                and isinstance(divisor, ast.Constant)
                and isinstance(numerator.right.value, int)
                and isinstance(divisor.value, int)
                and numerator.right.value == divisor.value - 1
            ):
                text = f"({ctx.wseg(numerator.left)} // {ctx.seg(divisor)})"
                yield Candidate(node, (ctx.edit(node, text),), kbm_rule="ceil2floor-lit")


def _guarded_calls(ctx: ScopeContext) -> Iterator[tuple[ast.Call, list[int], list[str]]]:
    """Yield (call, positional indices, keywords) that carry a guard."""
    for call in ctx.calls(LOAD | STORE | ATOMICS):
        name = ctx.name_of(call)
        if name in LOAD:
            positional, keywords = [1, 2], ["mask", "other", "boundary_check", "padding_option"]
        elif name in STORE:
            positional, keywords = [2], ["mask", "boundary_check"]
        else:
            positional, keywords = [2], ["mask"]
        present_pos = [i for i in positional if len(call.args) > i]
        present_kw = [k for k in keywords if kwarg(call, k) is not None]
        guard_present = (
            (positional[0] in present_pos)
            or kwarg(call, "mask") is not None
            or kwarg(call, "boundary_check") is not None
        )
        if guard_present:
            yield call, present_pos, present_kw


def _mask_drop(ctx: ScopeContext) -> Iterator[Candidate]:
    for call, positions, keywords in _guarded_calls(ctx):
        text = rebuild_call(ctx, call, drop_positional=positions, drop_keywords=keywords)
        yield Candidate(call, (ctx.edit(call, text),))


def _return_guard_drop(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if (
            isinstance(node, ast.If)
            and not node.orelse
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Return)
            and node.body[0].value is None
        ):
            yield Candidate(node, (ctx.edit(node, "pass"),))


def _where_guard_drop(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls({"tl.where"}):
        cond, value, fallback = (arg(call, i, None) for i in range(3))
        if cond is None or value is None or fallback is None:
            continue
        if ctx.is_const(fallback, 0.0) and ctx.const(value) is None:
            yield Candidate(call, (ctx.edit(call, ctx.wseg(value)),))


def _range_parts(ctx: ScopeContext, loop: ast.For):
    call = loop.iter
    if not (isinstance(call, ast.Call) and ctx.name_of(call) in RANGE):
        return None
    args = call.args
    if not args or any(isinstance(a, ast.Starred) for a in args):
        return None
    if len(args) == 1:
        return call, None, args[0], arg(call, None, "step")
    step = args[2] if len(args) > 2 else arg(call, None, "step")
    return call, args[0], args[1], step


def _loop_bound_minus1(ctx: ScopeContext) -> Iterator[Candidate]:
    for loop in ctx.nodes:
        if not isinstance(loop, ast.For) or (parts := _range_parts(ctx, loop)) is None:
            continue
        _call, _start, stop, step = parts
        step_text = ctx.wseg(step) if step is not None else "1"
        yield Candidate(stop, (ctx.edit(stop, f"({ctx.wseg(stop)} - {step_text})"),))


def _loop_start_1(ctx: ScopeContext) -> Iterator[Candidate]:
    for loop in ctx.nodes:
        if not isinstance(loop, ast.For) or (parts := _range_parts(ctx, loop)) is None:
            continue
        _call, start, stop, step = parts
        step_text = ctx.wseg(step) if step is not None else "1"
        if start is None:
            yield Candidate(stop, (ctx.edit(stop, f"{step_text}, {ctx.seg(stop)}"),))
        else:
            yield Candidate(start, (ctx.edit(start, f"({ctx.wseg(start)} + {step_text})"),))


def _loop_step_double(ctx: ScopeContext) -> Iterator[Candidate]:
    for loop in ctx.nodes:
        if not isinstance(loop, ast.For) or (parts := _range_parts(ctx, loop)) is None:
            continue
        step = parts[3]
        if step is not None:
            yield Candidate(step, (ctx.edit(step, f"(2 * {ctx.wseg(step)})"),))


def _mask_bound(delta: str):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        for node in ctx.nodes:
            if not isinstance(node, ast.Compare):
                continue
            for op, comparator in zip(node.ops, node.comparators, strict=True):
                if isinstance(op, ast.Lt) and ctx.const(comparator) is None:
                    text = f"({ctx.wseg(comparator)} {delta})"
                    yield Candidate(comparator, (ctx.edit(comparator, text),))

    return finder


def _bound_dim_swap(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if not isinstance(node, ast.Compare):
            continue
        for comparator in node.comparators:
            for sub in ast.walk(comparator):
                if isinstance(sub, ast.Name) and sub.id in ctx.dim_params:
                    other = ctx.partner(ctx.dim_params, sub.id)
                    if other is not None:
                        yield Candidate(sub, (ctx.edit(sub, other),), detail=f"{sub.id}->{other}")


def _sentinel_min(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if _inf_literal(ctx, node, 1.0) and not isinstance(parent(node), ast.UnaryOp):
            yield Candidate(node, (ctx.edit(node, "0.0"),))


OPERATORS = (
    Operator(
        "ceil2floor",
        "boundary",
        "paper",
        "ceil2floor",
        ("device", "launch"),
        "Ceil division becomes floor division (tl.cdiv/triton.cdiv, (a+b-1)//b, "
        "(a+255)//256): the tail block or tail iteration is never processed.",
        _ceil2floor,
        ports=("ceil2floor-lit",),
    ),
    Operator(
        "lt2le",
        "boundary",
        "paper",
        "lt2le",
        ("device",),
        "ROR: one < becomes <= (off-by-one overrun).",
        _ror(ast.Lt, ast.LtE),
        ports=(
            "output-elements-one-extra-lane",
            "line-count-one-extra-lane",
            "flat-n-one-extra-lane",
        ),
    ),
    Operator(
        "le2lt",
        "boundary",
        "paper",
        "le2lt",
        ("device",),
        "ROR: one <= becomes < (off-by-one underrun).",
        _ror(ast.LtE, ast.Lt),
    ),
    Operator(
        "gt2ge",
        "boundary",
        "paper",
        "gt2ge",
        ("device",),
        "ROR: one > becomes >=.",
        _ror(ast.Gt, ast.GtE),
    ),
    Operator(
        "ge2gt",
        "boundary",
        "paper",
        "ge2gt",
        ("device",),
        "ROR: one >= becomes > (one out-of-range lane slips through).",
        _ror(ast.GtE, ast.Gt),
    ),
    Operator(
        "lt2gt",
        "boundary",
        "paper",
        "lt2gt",
        ("device",),
        "ROR: one < becomes > (inverted guard).",
        _ror(ast.Lt, ast.Gt),
    ),
    Operator(
        "mask-drop",
        "boundary",
        "paper",
        "guard-drop-if",
        ("device",),
        "One tl.load/tl.store/atomic loses its mask (and fill value) or boundary_check: "
        "the Triton spelling of deleting a bounds guard.",
        _mask_drop,
    ),
    Operator(
        "return-guard-drop",
        "boundary",
        "paper",
        "return-guard-drop",
        ("device",),
        "An early-return bounds guard (if cond: return) is removed.",
        _return_guard_drop,
    ),
    Operator(
        "where-guard-drop",
        "boundary",
        "paper",
        "guard-drop-ternary",
        ("device",),
        "tl.where(cond, x, 0) -> x: an edge guard becomes an unconditional value.",
        _where_guard_drop,
    ),
    Operator(
        "loop-bound-minus1",
        "boundary",
        "paper",
        "loop-bound-minus1",
        ("device",),
        "A range/tl.range loop drops its last iteration (stop -> stop - step).",
        _loop_bound_minus1,
        ports=(
            "last-row-reduction-skip",
            "last-row-reduction-skip-start1",
            "tile-last-iteration-skip",
            "literal-loop-last-skip",
            "strided-tail-drop",
            "arg-reduction-last-row-drop",
            "min-reduction-last-row-drop",
            "cumsum-last-output-drop",
            "pool2d-last-tap-drop",
        ),
    ),
    Operator(
        "loop-start-1",
        "boundary",
        "paper",
        "loop-start-1",
        ("device",),
        "A range/tl.range loop skips its first iteration (start -> start + step).",
        _loop_start_1,
        ports=("argmax-seed-from-second",),
    ),
    Operator(
        "loop-step-double",
        "boundary",
        "paper",
        "grid-stride-step-double",
        ("device",),
        "A stepped loop doubles its step and skips every other chunk (the persistent "
        "or grid-stride loop analogue).",
        _loop_step_double,
    ),
    Operator(
        "mask-bound-minus1",
        "boundary",
        "paper",
        "elementwise-guard-minus1",
        ("device",),
        "In one x < bound comparison the bound becomes bound - 1: the last element of "
        "a masked range or reduction is dropped.",
        _mask_bound("- 1"),
        ports=(
            "tail-guard-tighten",
            "matmul-a-last-k-drop",
            "matmul-a-transposed-last-k-drop",
            "matmul-b-last-k-drop",
            "groupnorm-sum-tail-scalar-drop",
            "groupnorm-sqdev-tail-scalar-drop",
        ),
    ),
    Operator(
        "mask-bound-plus1",
        "boundary",
        "paper",
        "elementwise-guard-plus1",
        ("device",),
        "In one x < bound comparison the bound becomes bound + 1: one lane past the end.",
        _mask_bound("+ 1"),
    ),
    Operator(
        "bound-dim-swap",
        "boundary",
        "paper",
        "matrix-row-bound-use-n",
        ("device",),
        "A dimension argument inside a bounds comparison is replaced by another "
        "dimension argument (row < M -> row < N).",
        _bound_dim_swap,
        ports=("matrix-col-bound-use-m", "height-bound-use-width", "width-bound-use-height"),
    ),
    Operator(
        "sentinel-zero-min",
        "boundary",
        "paper",
        "reduce-seed-first-element-min",
        ("device",),
        "A literal +inf (min-reduction seed or fill) becomes 0.0: wrong only when every "
        "value is positive.",
        _sentinel_min,
    ),
)
