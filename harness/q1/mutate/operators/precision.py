"""Precision family: low-precision accumulation and stores, fast math, removed
stabilisers, perturbed approximation constants and TF32 in tl.dot."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from harness.q1.mutate.operators._base import (
    ERF,
    EXP,
    REDUCE_MAX,
    REDUCE_SUM,
    RSQRT,
    SQRT,
    STORE,
    Candidate,
    Operator,
    ScopeContext,
    arg,
    float_repr,
    inside_call,
    kwarg,
    names_in,
    rebuild_call,
    same_name,
    statement_of,
)

# Approximation and model constants that KernelBench-M perturbs in its CUDA
# substrates, with the paper rule that perturbs them. Values are mathematical
# constants (GELU, SELU, hard-sigmoid, softplus); matching is by value.
_NAMED_CONSTANTS: tuple[tuple[float, str, str], ...] = (
    (0.044715, "gelu-tanh-const-perturb", "gelu-tanh-const-perturb"),
    (0.7978845608028654, "gelu-sqrt2pi-perturb", "gelu-sqrt2pi-perturb"),
    (0.7071067811865476, "invsqrt2-perturb", "invsqrt2-perturb"),
    (1.6732632423543772, "selu-alpha-perturb", "selu-alpha-small-perturb"),
    (1.0507009873554805, "selu-scale-perturb", "selu-scale-small-perturb"),
    (0.16666666666666666, "hardsigmoid-six-denom-perturb", "hardsigmoid-six-denom-perturb"),
    (6.0, "hardsigmoid-six-denom-perturb", "hardsigmoid-six-denom-perturb"),
    (3.0, "hardsigmoid-slope-perturb", "hardsigmoid-half-ulpish-perturb"),
    (0.5, "hardsigmoid-slope-perturb", "hardsigmoid-half-ulpish-perturb"),
    (20.0, "softplus-cutoff-tiny-shift", "softplus-cutoff-tiny-shift"),
)


def _named_constant(value: float) -> tuple[str, str] | None:
    for constant, large_rule, small_rule in _NAMED_CONSTANTS:
        if abs(value - constant) <= 1e-6 * abs(constant):
            return large_rule, small_rule
    return None


def _accumulators(ctx: ScopeContext) -> Iterator[tuple[ast.Name, ast.Call, ast.AST]]:
    """Yield (target, init call, dtype node) for fp32 accumulators updated in a loop."""
    updated: dict[str, list[ast.AST]] = {}
    for node in ctx.nodes:
        if (
            isinstance(node, ast.AugAssign)
            and isinstance(node.op, ast.Add)
            and isinstance(node.target, ast.Name)
        ):
            updated.setdefault(node.target.id, []).append(node)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
            if (
                isinstance(target, ast.Name)
                and isinstance(value, ast.Call)
                and ctx.name_of(value) == "tl.dot"
                and same_name(arg(value, 2, "acc"), target)
            ):
                updated.setdefault(target.id, []).append(node)
    for node in ctx.nodes:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target, value = node.targets[0], node.value
        if not (isinstance(target, ast.Name) and isinstance(value, ast.Call)):
            continue
        if target.id not in updated:
            continue
        name = ctx.name_of(value)
        dtype = (
            arg(value, 1, "dtype")
            if name == "tl.zeros"
            else arg(value, 2, "dtype")
            if name == "tl.full"
            else None
        )
        if dtype is not None and ctx.src.dotted(dtype) == "tl.float32":
            yield target, value, dtype


def _acc_fp16(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    if tl is None:
        return
    half = f"{tl}.float16"
    for target, _init, dtype in _accumulators(ctx):
        edits = [ctx.edit(dtype, half)]
        for node in ctx.nodes:
            if (
                isinstance(node, ast.AugAssign)
                and isinstance(node.op, ast.Add)
                and same_name(node.target, target)
            ):
                edits.append(ctx.edit(node.value, f"({ctx.seg(node.value)}).to({half})"))
            elif (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and same_name(node.targets[0], target)
                and isinstance(node.value, ast.Call)
                and ctx.name_of(node.value) == "tl.dot"
            ):
                call = node.value
                edits.append(
                    ctx.edit(call, rebuild_call(ctx, call, set_keywords={"out_dtype": half}))
                )
        yield Candidate(target, tuple(edits), detail=f"accumulator {target.id}")


def _store_value_wrap(template: str, skip_marker: str | None):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        tl = ctx.tl()
        if tl is None:
            return
        for call in ctx.calls(STORE):
            value = arg(call, 1, "value")
            if value is None:
                continue
            if skip_marker and skip_marker.format(tl=tl) in ctx.seg(value):
                continue
            text = template.format(value=ctx.wseg(value), tl=tl)
            yield Candidate(value, (ctx.edit(value, text),))

    return finder


def _exp_fast(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    if tl is None:
        return
    for call in ctx.calls({"libdevice.exp"}):
        if len(call.args) == 1 and not call.keywords:
            yield Candidate(call, (ctx.edit(call.func, f"{tl}.exp"),))


def _is_sum_like(ctx: ScopeContext, node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and any(k in node.id.lower() for k in ("sum", "denom")):
        return True
    resolved = ctx.resolve(node, depth=1)
    while isinstance(resolved, ast.Subscript):
        resolved = resolved.value
    return isinstance(resolved, ast.Call) and ctx.name_of(resolved) in REDUCE_SUM


def _div_fast(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    if tl is None:
        return
    for node in ctx.nodes:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if _is_sum_like(ctx, node.right):
                text = f"{tl}.fdiv({ctx.seg(node.left)}, {ctx.seg(node.right)})"
                yield Candidate(node, (ctx.edit(node, text),))
        elif (
            isinstance(node, ast.Call)
            and ctx.name_of(node) in {"tl.div_rn", "libdevice.div_rn"}
            and len(node.args) == 2
            and not node.keywords
        ):
            a, b = node.args
            text = f"{tl}.fdiv({ctx.seg(a)}, {ctx.seg(b)})"
            yield Candidate(node, (ctx.edit(node, text),))


def _constant_perturb(relative: float, small: bool):
    def finder(ctx: ScopeContext) -> Iterator[Candidate]:
        for node in ctx.nodes:
            if not (isinstance(node, ast.Constant) and isinstance(node.value, float)):
                continue
            rules = _named_constant(node.value)
            if rules is None:
                continue
            new = float_repr(node.value * (1.0 + relative))
            yield Candidate(node, (ctx.edit(node, new),), kbm_rule=rules[1 if small else 0])

    return finder


def _is_epsilon(ctx: ScopeContext, node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return "eps" in node.id.lower()
    value = ctx.const(node) if isinstance(node, ast.Constant) else None
    return value is not None and 0.0 < abs(value) <= 1e-4


def _epsilon_sites(ctx: ScopeContext) -> Iterator[tuple[ast.BinOp, ast.AST, ast.AST, str | None]]:
    for node in ctx.nodes:
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
            continue
        for eps, kept in ((node.right, node.left), (node.left, node.right)):
            if _is_epsilon(ctx, eps) and not _is_epsilon(ctx, kept):
                if inside_call(ctx, node, RSQRT) is not None:
                    rule = "rsqrt-epsilon-remove"
                elif inside_call(ctx, node, SQRT) is not None:
                    rule = "sqrt-epsilon-remove"
                elif isinstance(eps, ast.Constant):
                    rule = "literal-epsilon-remove"
                else:
                    rule = None
                yield node, eps, kept, rule
                break


def _epsilon_remove(ctx: ScopeContext) -> Iterator[Candidate]:
    for node, _eps, kept, rule in _epsilon_sites(ctx):
        yield Candidate(node, (ctx.edit(node, ctx.wseg(kept)),), kbm_rule=rule)


def _epsilon_halve(ctx: ScopeContext) -> Iterator[Candidate]:
    for _node, eps, _kept, _rule in _epsilon_sites(ctx):
        yield Candidate(eps, (ctx.edit(eps, f"({ctx.wseg(eps)} * 0.5)"),))


def _is_max_like(ctx: ScopeContext, node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and "max" in node.id.lower():
        return True
    resolved = ctx.resolve(node, depth=1)
    while isinstance(resolved, ast.Subscript):
        resolved = resolved.value
    return isinstance(resolved, ast.Call) and ctx.name_of(resolved) in REDUCE_MAX


def _flows_into_exp(ctx: ScopeContext, node: ast.BinOp) -> bool:
    if inside_call(ctx, node, EXP) is not None:
        return True
    statement = statement_of(node)
    if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1):
        return False
    target = statement.targets[0]
    if not isinstance(target, ast.Name):
        return False
    return any(target.id in names_in(a) for call in ctx.calls(EXP) for a in call.args)


def _max_subtraction_remove(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Sub)
            and _is_max_like(ctx, node.right)
            and _flows_into_exp(ctx, node)
        ):
            yield Candidate(node, (ctx.edit(node, ctx.wseg(node.left)),))


def _variance_unbiased(ctx: ScopeContext) -> Iterator[Candidate]:
    for node in ctx.nodes:
        if (
            isinstance(node, ast.AugAssign)
            and isinstance(node.op, ast.Div)
            and isinstance(node.target, ast.Name)
            and "var" in node.target.id.lower()
        ):
            yield Candidate(node.value, (ctx.edit(node.value, f"({ctx.wseg(node.value)} - 1)"),))
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and "var" in node.targets[0].id.lower()
            and isinstance(node.value, ast.BinOp)
            and isinstance(node.value.op, ast.Div)
        ):
            divisor = node.value.right
            yield Candidate(divisor, (ctx.edit(divisor, f"({ctx.wseg(divisor)} - 1)"),))


def _erf_to_tanh(ctx: ScopeContext) -> Iterator[Candidate]:
    tl = ctx.tl()
    if tl is None:
        return
    for call in ctx.calls(ERF):
        if len(call.args) != 1 or call.keywords:
            continue
        z = ctx.wseg(call.args[0])
        # erf(z) ~= tanh(2/sqrt(pi) * (z + 0.08943 z^3)), the GELU tanh form in
        # terms of z = x / sqrt(2); tanh(u) is written as 2 / (1 + exp(-2u)) - 1.
        inner = f"1.1283791670955126 * ({z} + 0.08943 * {z} * {z} * {z})"
        text = f"(2.0 / (1.0 + {tl}.exp(-2.0 * ({inner}))) - 1.0)"
        yield Candidate(call, (ctx.edit(call, text),))


def _dot_tf32(ctx: ScopeContext) -> Iterator[Candidate]:
    for call in ctx.calls({"tl.dot"}):
        precision = kwarg(call, "input_precision")
        if (
            precision is not None
            and isinstance(precision.value, ast.Constant)
            and precision.value.value in ("ieee", "tf32x3")
        ):
            yield Candidate(call, (ctx.edit(precision.value, '"tf32"'),))
        allow = kwarg(call, "allow_tf32")
        if (
            allow is not None
            and isinstance(allow.value, ast.Constant)
            and allow.value.value is False
        ):
            yield Candidate(call, (ctx.edit(allow.value, "True"),))


def _cutoff_shift(ctx: ScopeContext) -> Iterator[Candidate]:
    from harness.q1.mutate.operators._base import compare_of

    for call in ctx.calls({"tl.where"}):
        cond = arg(call, 0, "condition")
        compare = compare_of(ctx, cond) if cond is not None else None
        if compare is None or len(compare.ops) != 1:
            continue
        if not isinstance(compare.ops[0], ast.Gt | ast.GtE | ast.Lt | ast.LtE):
            continue
        for side in (compare.left, compare.comparators[0]):
            value = ctx.const(side)
            if value is not None and abs(value) >= 10.0:
                yield Candidate(side, (ctx.edit(side, float_repr(value * 0.4)),))


def _clamp_bound_perturb(ctx: ScopeContext) -> Iterator[Candidate]:
    from harness.q1.mutate.operators._base import MINIMUM

    for call in ctx.calls(MINIMUM):
        if len(call.args) != 2 or call.keywords:
            continue
        for bound, other in ((call.args[1], call.args[0]), (call.args[0], call.args[1])):
            if ctx.is_const(bound, 1.0) and ctx.const(other) is None:
                yield Candidate(bound, (ctx.edit(bound, "0.999"),))
                break
    for call in ctx.calls({"tl.clamp"}):
        high = arg(call, 2, "max")
        if high is not None and ctx.is_const(high, 1.0):
            yield Candidate(high, (ctx.edit(high, "0.999"),))


OPERATORS = (
    Operator(
        "acc-fp16",
        "precision",
        "paper",
        "acc-fp16",
        ("device",),
        "An fp32 accumulator is declared fp16; its += updates (and tl.dot out_dtype) "
        "are rewritten to keep the loop-carried type consistent.",
        _acc_fp16,
    ),
    Operator(
        "store-fp16",
        "precision",
        "paper",
        "store-fp16",
        ("device",),
        "One stored value round-trips through fp16 (tl.store casts back to the "
        "pointer's element type).",
        _store_value_wrap("{value}.to({tl}.float16)", "{tl}.float16"),
    ),
    Operator(
        "exp-fast",
        "precision",
        "paper",
        "expf-fast",
        ("device",),
        "Precise libdevice.exp becomes tl.exp (the approximate ex2-based lowering).",
        _exp_fast,
    ),
    Operator(
        "div-fast",
        "precision",
        "paper",
        "fdividef-fast",
        ("device",),
        "IEEE division by a sum or denominator (or div_rn) becomes approximate tl.fdiv.",
        _div_fast,
    ),
    Operator(
        "named-constant-perturb",
        "precision",
        "paper",
        "gelu-tanh-const-perturb",
        ("device",),
        "A known approximation constant (GELU, SELU, hard-sigmoid, softplus cutoff) is "
        "perturbed by a relative 1e-3.",
        _constant_perturb(1e-3, small=False),
        ports=(
            "gelu-sqrt2pi-perturb",
            "invsqrt2-perturb",
            "selu-alpha-perturb",
            "selu-scale-perturb",
            "hardsigmoid-six-denom-perturb",
            "hardsigmoid-slope-perturb",
            "softplus-cutoff-tiny-shift",
        ),
    ),
    Operator(
        "named-constant-small-perturb",
        "precision",
        "paper",
        "selu-alpha-small-perturb",
        ("device",),
        "A known approximation constant is perturbed by a relative 1e-4 (below the "
        "official tolerance).",
        _constant_perturb(1e-4, small=True),
        ports=("selu-scale-small-perturb", "hardsigmoid-half-ulpish-perturb"),
    ),
    Operator(
        "epsilon-remove",
        "precision",
        "paper",
        "rsqrt-epsilon-remove",
        ("device",),
        "A variance or literal epsilon stabiliser is removed (x + eps -> x).",
        _epsilon_remove,
        ports=("sqrt-epsilon-remove", "literal-epsilon-remove"),
    ),
    Operator(
        "epsilon-halve",
        "precision",
        "paper",
        "groupnorm-epsilon-halved",
        ("device",),
        "A variance or literal epsilon is halved.",
        _epsilon_halve,
        ports=("batchnorm-epsilon-small-bias",),
    ),
    Operator(
        "softmax-max-subtraction-remove",
        "precision",
        "paper",
        "softmax-max-subtraction-remove",
        ("device",),
        "The max subtraction feeding an exp is removed: overflow at large magnitude.",
        _max_subtraction_remove,
        ports=("softmax-max-subtraction-fast-remove",),
    ),
    Operator(
        "variance-unbiased-count",
        "precision",
        "paper",
        "variance-unbiased-count",
        ("device",),
        "A population variance divides by N - 1 instead of N.",
        _variance_unbiased,
    ),
    Operator(
        "store-scale-nudge",
        "precision",
        "paper",
        "matmul-acc-store-fma-nudge",
        ("device",),
        "One stored value is scaled by 0.9999 (the paper nudges the matmul "
        "accumulator store; the port applies at every tl.store).",
        _store_value_wrap("{value} * 0.9999", None),
    ),
    Operator(
        "erf-to-tanh-approx",
        "precision",
        "paper",
        "erf-to-tanh-approx",
        ("device",),
        "An exact erf is replaced by the tanh approximation used by tanh-GELU.",
        _erf_to_tanh,
    ),
    Operator(
        "cutoff-shift",
        "precision",
        "paper",
        "softplus-cutoff-shift",
        ("device",),
        "A large piecewise cutoff in a tl.where condition (softplus 20) moves to 0.4x "
        "its value (the paper moves 20 to 8).",
        _cutoff_shift,
    ),
    Operator(
        "clamp-bound-perturb",
        "precision",
        "paper",
        "clamp-bound-perturb",
        ("device",),
        "A unit saturation bound (minimum(x, 1.0) or tl.clamp(..., 1.0)) becomes 0.999.",
        _clamp_bound_perturb,
    ),
    Operator(
        "dot-tf32",
        "precision",
        "triton-only",
        None,
        ("device",),
        "tl.dot input_precision ieee/tf32x3 -> tf32, or allow_tf32=False -> True.",
        _dot_tf32,
    ),
)
