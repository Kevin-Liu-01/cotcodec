"""Arithmetic family: classical AOR/UOI replacements (paper rules)."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from harness.q1.mutate.operators._base import (
    STORE,
    Candidate,
    Operator,
    ScopeContext,
    arg,
)


def _binop_swap(op_type: type[ast.operator], symbol: str):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        for node in ctx.nodes:
            if isinstance(node, ast.BinOp) and isinstance(node.op, op_type):
                text = f"{ctx.wseg(node.left)} {symbol} {ctx.wseg(node.right)}"
                yield Candidate(node, (ctx.edit(node, f"({text})"),))

    return finder


def _negate_store(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls(STORE):
        value = arg(call, 1, "value")
        if value is None:
            continue
        yield Candidate(value, (ctx.edit(value, f"(-{ctx.wseg(value)})"),))


OPERATORS = (
    Operator(
        "plus2minus",
        "arithmetic",
        "paper",
        "plus2minus",
        ("device",),
        "AOR: one binary + in device code becomes -.",
        _binop_swap(ast.Add, "-"),
    ),
    Operator(
        "minus2plus",
        "arithmetic",
        "paper",
        "minus2plus",
        ("device",),
        "AOR: one binary - in device code becomes +.",
        _binop_swap(ast.Sub, "+"),
    ),
    Operator(
        "mul2div",
        "arithmetic",
        "paper",
        "mul2div",
        ("device",),
        "AOR: one binary * becomes / (ill-typed integer sites fail the compile filter).",
        _binop_swap(ast.Mult, "/"),
    ),
    Operator(
        "mul2plus",
        "arithmetic",
        "paper",
        "mul2plus",
        ("device",),
        "AOR: one binary * becomes +.",
        _binop_swap(ast.Mult, "+"),
    ),
    Operator(
        "negate-store",
        "arithmetic",
        "paper",
        "negate-store",
        ("device",),
        "UOI: the value written by one tl.store is negated. The paper rule negates a "
        "stored exp() expression; Triton stores are explicit, so the port negates the "
        "stored value at each tl.store site.",
        _negate_store,
    ),
)
