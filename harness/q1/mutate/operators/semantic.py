"""Semantic family: accumulation, extremum, tie-breaking, clamp and activation faults."""

from __future__ import annotations

import ast
import math
from collections.abc import Iterator

from harness.q1.mutate.operators._base import (
    ABS,
    MAXIMUM,
    MINIMUM,
    REDUCE_MAX,
    REDUCE_MIN,
    Candidate,
    Operator,
    ScopeContext,
    arg,
    kwarg,
    positive_branch_compare,
    rebuild_call,
    same_name,
    swap_attr,
)

_MAX_TO_MIN = {"maximum": "minimum", "fmax": "fmin", "max": "min", "max2": "min2"}
_MIN_TO_MAX = {value: key for key, value in _MAX_TO_MIN.items()}


def _dot_acc(ctx: ScopeContext, node: ast.AST) -> tuple[ast.Name, ast.Call] | None:
    """Match ``acc = tl.dot(a, b, acc)``; return (target, dot call)."""
    if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
        return None
    target, value = node.targets[0], node.value
    if not (isinstance(target, ast.Name) and isinstance(value, ast.Call)):
        return None
    if ctx.name_of(value) != "tl.dot":
        return None
    acc = arg(value, 2, "acc")
    return (target, value) if same_name(acc, target) else None


def _acc_overwrite(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            text = f"{ctx.seg(node.target)} = {ctx.seg(node.value)}"
            yield Candidate(node, (ctx.edit(node, text),))
        elif (match := _dot_acc(ctx, node)) is not None:
            _, call = match
            text = rebuild_call(ctx, call, drop_positional=(2,), drop_keywords=("acc",))
            yield Candidate(call, (ctx.edit(call, text),))


def _acc_minus(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            text = f"{ctx.seg(node.target)} -= {ctx.seg(node.value)}"
            yield Candidate(node, (ctx.edit(node, text),))
        elif (match := _dot_acc(ctx, node)) is not None:
            target, call = match
            dot = rebuild_call(ctx, call, drop_positional=(2,), drop_keywords=("acc",))
            yield Candidate(call, (ctx.edit(call, f"({target.id} - {dot})"),))


def _swap_extremum(names: frozenset[str], mapping: dict[str, str]):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        for call in ctx.calls(names):
            if not isinstance(call.func, ast.Attribute) or call.func.attr not in mapping:
                continue
            func = swap_attr(ctx, call, mapping[call.func.attr])
            yield Candidate(call, (ctx.edit(call.func, func),))

    return finder


def _is_inf_atom(ctx: ScopeContext, node: ast.AST) -> bool:
    """``float("inf")``, ``float("-inf")``, ``math.inf`` or ``np.inf`` (not tl.full)."""
    if isinstance(node, ast.Call):
        return ctx.name_of(node) == "float"
    return isinstance(node, ast.Attribute) and ctx.src.dotted(node) in {"math.inf", "np.inf"}


def _inf_literal(ctx: ScopeContext, node: ast.AST, sign: float) -> bool:
    """True for a literal +/-inf expression, optionally negated (never a Name)."""
    atom = node.operand if isinstance(node, ast.UnaryOp) else node
    if not _is_inf_atom(ctx, atom):
        return False
    value = ctx.const(node, depth=2)
    return value is not None and math.isinf(value) and math.copysign(1.0, value) == sign


def _sentinel(sign: float):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        from harness.q1.mutate.source import parent

        for node in ctx.nodes:
            if not _inf_literal(ctx, node, sign):
                continue
            up = parent(node)
            if isinstance(up, ast.UnaryOp):
                continue  # the enclosing negation is the site
            yield Candidate(node, (ctx.edit(node, "0.0"),))

    return finder


def _const0to1(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    for node in ctx.nodes:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, float) and value.value == 0:
            yield Candidate(value, (ctx.edit(value, "1.0"),))
            continue
        if not isinstance(value, ast.Call):
            continue
        name = ctx.name_of(value)
        if name == "tl.zeros" and tl is not None:
            shape = arg(value, 0, "shape")
            dtype = arg(value, 1, "dtype")
            if shape is None:
                continue
            dtype_text = ctx.seg(dtype) if dtype is not None else f"{tl}.float32"
            text = f"{tl}.full({ctx.seg(shape)}, 1.0, {dtype_text})"
            yield Candidate(value, (ctx.edit(value, text),))
        elif name == "tl.full":
            fill = arg(value, 1, "value")
            if fill is not None and ctx.is_const(fill, 0.0) and not isinstance(fill, ast.Name):
                literal = "1.0" if isinstance(getattr(fill, "value", None), float) else "1"
                yield Candidate(fill, (ctx.edit(fill, literal),))


def _tie_last(names: frozenset[str], reduce_names: frozenset[str]):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        for call in ctx.calls(names):
            existing = kwarg(call, "tie_break_left")
            if existing is not None and ctx.const(existing.value) == 0.0:
                continue
            text = rebuild_call(ctx, call, set_keywords={"tie_break_left": "False"})
            yield Candidate(call, (ctx.edit(call, text),))
        for call in ctx.calls(reduce_names):
            indices = kwarg(call, "return_indices")
            if indices is None or not (
                isinstance(indices.value, ast.Constant) and indices.value.value is True
            ):
                continue
            text = rebuild_call(ctx, call, set_keywords={"return_indices_tie_break_left": "False"})
            yield Candidate(call, (ctx.edit(call, text),))

    return finder


def _nan_propagation_drop(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls(MAXIMUM | MINIMUM):
        policy = kwarg(call, "propagate_nan")
        if policy is None or "ALL" not in ctx.seg(policy.value):
            continue
        text = rebuild_call(ctx, call, drop_keywords=("propagate_nan",))
        yield Candidate(call, (ctx.edit(call, text),))


def _tie_order(names: frozenset[str], symbol: str):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        tl = ctx.tl()
        if tl is None:
            return
        for node in ctx.nodes:
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            target, call = node.targets[0], node.value
            if not (isinstance(call, ast.Call) and ctx.name_of(call) in names):
                continue
            if len(call.args) != 2 or call.keywords:
                continue
            first, second = call.args
            if same_name(first, target):
                other = second
            elif same_name(second, target):
                other = first
            else:
                continue
            new = ctx.wseg(other)
            text = f"{tl}.where({new} {symbol} {target.id}, {new}, {target.id})"
            yield Candidate(call, (ctx.edit(call, text),))

    return finder


def _where_threshold(new_threshold: str, require_nonzero_other: bool):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        for call in ctx.calls({"tl.where"}):
            match = positive_branch_compare(ctx, call)
            if match is None:
                continue
            _compare, zero, _x, other = match
            if require_nonzero_other and ctx.is_const(other, 0.0):
                continue
            yield Candidate(zero, (ctx.edit(zero, new_threshold),))

    return finder


def _remove_extremum_with(names: frozenset[str], value: float, position: str, simple: bool):
    """MAXIMUM/MINIMUM(x, c) -> x, with the constant at ``position``."""

    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        for call in ctx.calls(names):
            if len(call.args) != 2 or call.keywords:
                continue
            first, second = call.args
            pairs = {"second": [(first, second)], "first": [(second, first)]}
            pairs["either"] = pairs["second"] + pairs["first"]
            for kept, const_node in pairs[position]:
                if not ctx.is_const(const_node, value):
                    continue
                if ctx.const(kept) is not None:
                    continue
                if simple and _is_extremum(ctx, kept, MAXIMUM):
                    continue
                yield Candidate(call, (ctx.edit(call, ctx.wseg(kept)),))
                break

    return finder


def _is_extremum(ctx: ScopeContext, node: ast.AST, names: frozenset[str]) -> bool:
    resolved = ctx.resolve(node, depth=1)
    return isinstance(resolved, ast.Call) and ctx.name_of(resolved) in names


def _relu_where_remove(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls({"tl.where"}):
        match = positive_branch_compare(ctx, call)
        if match is None:
            continue
        _compare, _zero, x, other = match
        if ctx.is_const(other, 0.0):
            yield Candidate(call, (ctx.edit(call, ctx.wseg(x)),))


def _clamp_nested_drop_upper(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    for call in ctx.calls(MINIMUM):
        if len(call.args) != 2 or call.keywords:
            continue
        first, second = call.args
        for inner, bound in ((first, second), (second, first)):
            if ctx.is_const(bound, 1.0) and _is_extremum(ctx, inner, MAXIMUM):
                yield Candidate(call, (ctx.edit(call, ctx.wseg(inner)),))
                break
    if tl is None:
        return
    for call in ctx.calls({"tl.clamp"}):
        x, low, high = arg(call, 0, "x"), arg(call, 1, "min"), arg(call, 2, "max")
        if x is not None and low is not None and ctx.is_const(high, 1.0):
            text = f"{tl}.maximum({ctx.seg(x)}, {ctx.seg(low)})"
            yield Candidate(call, (ctx.edit(call, text),))


def _abs_remove(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls(ABS):
        if len(call.args) == 1 and not call.keywords:
            yield Candidate(call, (ctx.edit(call, ctx.wseg(call.args[0])),))


OPERATORS = (
    Operator(
        "acc-overwrite",
        "semantic",
        "paper",
        "acc-overwrite",
        ("device",),
        "Accumulation becomes overwrite: acc += x -> acc = x, and tl.dot(a, b, acc) "
        "drops its accumulator.",
        _acc_overwrite,
    ),
    Operator(
        "acc-minus",
        "semantic",
        "paper",
        "acc-minus",
        ("device",),
        "Accumulation becomes subtraction: acc += x -> acc -= x, and "
        "acc = tl.dot(a, b, acc) -> acc - tl.dot(a, b).",
        _acc_minus,
    ),
    Operator(
        "max2min",
        "semantic",
        "paper",
        "fmax2fmin",
        ("device",),
        "One elementwise or reduction maximum becomes the matching minimum.",
        _swap_extremum(MAXIMUM | REDUCE_MAX, _MAX_TO_MIN),
    ),
    Operator(
        "min2max",
        "semantic",
        "paper",
        "fmin2fmax",
        ("device",),
        "One elementwise or reduction minimum becomes the matching maximum.",
        _swap_extremum(MINIMUM | REDUCE_MIN, _MIN_TO_MAX),
    ),
    Operator(
        "sentinel-zero",
        "semantic",
        "paper",
        "sentinel-zero",
        ("device",),
        "A literal -inf (reduction sentinel, masked-load fill) becomes 0.0: wrong only "
        "when every value is negative.",
        _sentinel(-1.0),
        ports=("reduce-seed-first-element",),
    ),
    Operator(
        "const0to1",
        "semantic",
        "paper",
        "const0to1",
        ("device",),
        "An initialiser 0 becomes 1: x = 0.0, tl.zeros(...) and tl.full(..., 0, ...).",
        _const0to1,
    ),
    Operator(
        "argmax-tie-last",
        "semantic",
        "paper",
        "argmax-tie-last",
        ("device",),
        "tl.argmax (or tl.max with return_indices) keeps the last maximum instead of "
        "the first: visible only on duplicate values.",
        _tie_last(frozenset({"tl.argmax"}), frozenset({"tl.max"})),
        ports=("argmax-tie-nan-form",),
    ),
    Operator(
        "argmin-tie-last",
        "semantic",
        "paper",
        "argmin-tie-last",
        ("device",),
        "tl.argmin (or tl.min with return_indices) keeps the last minimum.",
        _tie_last(frozenset({"tl.argmin"}), frozenset({"tl.min"})),
    ),
    Operator(
        "nan-propagation-drop",
        "semantic",
        "paper",
        "argmax-nan-policy-drop",
        ("device",),
        "propagate_nan=ALL is dropped from tl.maximum/tl.minimum: differs only on NaN.",
        _nan_propagation_drop,
    ),
    Operator(
        "reduce-max-tie-order",
        "semantic",
        "paper",
        "reduce-fmax-tie-order",
        ("device",),
        "m = maximum(m, x) becomes tl.where(x > m, x, m): NaN handling differs.",
        _tie_order(MAXIMUM, ">"),
    ),
    Operator(
        "reduce-min-tie-order",
        "semantic",
        "paper",
        "reduce-fmin-tie-order",
        ("device",),
        "m = minimum(m, x) becomes tl.where(x < m, x, m): NaN handling differs.",
        _tie_order(MINIMUM, "<"),
    ),
    Operator(
        "relu-threshold-shift",
        "semantic",
        "paper",
        "relu-threshold-shift",
        ("device",),
        "tl.where(x > 0, x, y) cutoff moves to 1e-6: only tiny positives differ.",
        _where_threshold("1e-06", require_nonzero_other=False),
    ),
    Operator(
        "positive-cutoff-nudge",
        "semantic",
        "paper",
        "elu-positive-cutoff-nudge",
        ("device",),
        "tl.where(x > 0, x, f(x)) with f(x) != 0 (ELU/SELU) cutoff moves to -1e-6.",
        _where_threshold("-1e-06", require_nonzero_other=True),
        ports=("selu-positive-cutoff-nudge",),
    ),
    Operator(
        "relu-max-zero-remove",
        "semantic",
        "paper",
        "relu-fmax-zero-remove",
        ("device",),
        "maximum(x, 0) -> x: ReLU removed, wrong only for negative inputs.",
        _remove_extremum_with(MAXIMUM, 0.0, "second", simple=False),
    ),
    Operator(
        "relu-max-zero-first-remove",
        "semantic",
        "paper",
        "relu-fmax-zero-first-remove",
        ("device",),
        "maximum(0, x) -> x: commuted ReLU removed.",
        _remove_extremum_with(MAXIMUM, 0.0, "first", simple=False),
    ),
    Operator(
        "relu-where-remove",
        "semantic",
        "triton-only",
        None,
        ("device",),
        "tl.where(x > 0, x, 0) -> x: the Triton tl.where spelling of ReLU removed.",
        _relu_where_remove,
    ),
    Operator(
        "clamp-upper-unit-remove",
        "semantic",
        "paper",
        "upper-unit-clamp-remove",
        ("device",),
        "minimum(x, 1) -> x for a simple x: upper saturation removed.",
        _remove_extremum_with(MINIMUM, 1.0, "second", simple=True),
    ),
    Operator(
        "clamp-upper-unit-first-remove",
        "semantic",
        "paper",
        "upper-unit-clamp-first-remove",
        ("device",),
        "minimum(1, x) -> x for a simple x: commuted upper saturation removed.",
        _remove_extremum_with(MINIMUM, 1.0, "first", simple=True),
    ),
    Operator(
        "clamp-lower-negunit-remove",
        "semantic",
        "paper",
        "lower-negunit-clamp-remove",
        ("device",),
        "maximum(x, -1) -> x (either argument order): lower saturation removed.",
        _remove_extremum_with(MAXIMUM, -1.0, "either", simple=False),
    ),
    Operator(
        "clamp-nested-drop-upper",
        "semantic",
        "paper",
        "nested-unit-clamp-drop-upper",
        ("device",),
        "minimum(maximum(x, lo), 1) -> maximum(x, lo); tl.clamp(x, lo, 1) -> tl.maximum(x, lo).",
        _clamp_nested_drop_upper,
    ),
    Operator(
        "abs-remove",
        "semantic",
        "paper",
        "fabs-simple-remove",
        ("device",),
        "abs(x) -> x: identity on non-negative inputs.",
        _abs_remove,
        ports=("softsign-positive-fabs-elide",),
    ),
)
