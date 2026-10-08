"""Operator framework: scope analysis, constant resolution and edit helpers.

An operator is a deterministic function from one scope (a ``@triton.jit``
function body, or the launch code) to candidate edits. Each candidate changes
one site; a few paper rules need paired edits (``acc-fp16`` rewrites the
accumulator declaration and its updates), which a candidate expresses as
several :class:`~harness.q1.mutate.source.TextEdit` objects anchored at one
site.
"""

from __future__ import annotations

import ast
import math
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field

from harness.q1.mutate.source import KernelSource, TextEdit, iter_scope, parent, wrap

FAMILIES = ("arithmetic", "indexing", "semantic", "boundary", "synchronization", "precision")
ORIGINS = ("paper", "triton-only")
SCOPES = ("device", "launch")

# Canonical callee names (see KernelSource.dotted).
MAXIMUM = frozenset({"tl.maximum", "triton_helpers.maximum", "libdevice.fmax"})
MINIMUM = frozenset({"tl.minimum", "triton_helpers.minimum", "libdevice.fmin"})
REDUCE_MAX = frozenset({"tl.max", "triton_helpers.max2"})
REDUCE_MIN = frozenset({"tl.min", "triton_helpers.min2"})
REDUCE_SUM = frozenset({"tl.sum", "triton_helpers.sum2"})
ABS = frozenset({"tl.abs", "tl.math.abs", "libdevice.fabs", "libdevice.abs"})
EXP = frozenset({"tl.exp", "tl.exp2", "tl.math.exp", "tl.math.exp2", "libdevice.exp"})
SQRT = frozenset({"tl.sqrt", "tl.sqrt_rn", "tl.math.sqrt", "libdevice.sqrt"})
RSQRT = frozenset({"tl.rsqrt", "tl.math.rsqrt", "libdevice.rsqrt"})
ERF = frozenset({"tl.erf", "tl.math.erf", "libdevice.erf"})
LOAD = frozenset({"tl.load"})
STORE = frozenset({"tl.store"})
ATOMICS = frozenset(
    {
        "tl.atomic_add",
        "tl.atomic_max",
        "tl.atomic_min",
        "tl.atomic_xchg",
        "tl.atomic_and",
        "tl.atomic_or",
        "tl.atomic_xor",
    }
)
RANGE = frozenset({"range", "tl.range", "tl.static_range"})
CDIV = frozenset({"tl.cdiv", "triton.cdiv"})
BLOCK_PTR = frozenset({"tl.make_block_ptr", "tl.advance"})


@dataclass(frozen=True)
class Candidate:
    """One mutation: edits anchored at ``anchor`` (the reported site)."""

    anchor: ast.AST
    edits: tuple[TextEdit, ...]
    kbm_rule: str | None = None
    detail: str = ""


@dataclass
class ScopeContext:
    """Analysis of one scope, shared by every operator."""

    src: KernelSource
    scope: str
    function: ast.FunctionDef | None
    nodes: list[ast.AST]
    params: list[str] = field(default_factory=list)
    constexpr_params: list[str] = field(default_factory=list)
    pointer_params: set[str] = field(default_factory=set)
    stride_params: list[str] = field(default_factory=list)
    dim_params: list[str] = field(default_factory=list)
    bindings: dict[str, list[ast.AST]] = field(default_factory=dict)

    @classmethod
    def device(cls, src: KernelSource, fn: ast.FunctionDef) -> ScopeContext:
        nodes = list(iter_scope(fn.body))
        args = [*fn.args.posonlyargs, *fn.args.args]
        params = [a.arg for a in args]
        constexpr = [
            a.arg
            for a in args
            if a.annotation is not None
            and (src.dotted(a.annotation) in {"tl.constexpr", "constexpr"})
        ]
        ctx = cls(src, "device", fn, nodes, params=params, constexpr_params=constexpr)
        ctx._analyse()
        return ctx

    @classmethod
    def launch(cls, src: KernelSource) -> ScopeContext:
        return cls(src, "launch", None, list(iter_scope(src.launch_statements())))

    # --- analysis ----------------------------------------------------------

    def _analyse(self) -> None:
        rebound: set[str] = set(self.params)
        for node in self.nodes:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.bindings.setdefault(target.id, []).append(node.value)
                    else:
                        rebound.update(_names_in(target))
            elif isinstance(node, ast.AugAssign | ast.AnnAssign | ast.For):
                target = getattr(node, "target", None)
                if target is not None:
                    rebound.update(_names_in(target))
        for name in rebound:
            self.bindings.setdefault(name, []).append(ast.Constant(value=None))

        pointer_roots: set[str] = set()
        for node in self.nodes:
            name = self.src.call_name(node)
            if name in LOAD | STORE | ATOMICS:
                root = self.pointer_root(arg(node, 0, "pointer"))
            elif name == "tl.make_block_ptr":
                root = self.pointer_root(arg(node, 0, "base"))
            else:
                continue
            if root is not None:
                pointer_roots.add(root)
        non_const = [p for p in self.params if p not in self.constexpr_params]
        self.pointer_params = {
            p for p in non_const if p in pointer_roots or p.lower().endswith("ptr")
        }
        self.stride_params = [p for p in non_const if "stride" in p.lower()]
        used_as_dim: set[str] = set()
        for node in self.nodes:
            if isinstance(node, ast.Compare):
                for operand in (node.left, *node.comparators):
                    used_as_dim.update(_names_in(operand))
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod | ast.FloorDiv):
                used_as_dim.update(_names_in(node.right))
            elif self.src.call_name(node) in CDIV | RANGE:
                for a in node.args:
                    used_as_dim.update(_names_in(a))
        self.dim_params = [
            p
            for p in non_const
            if p in used_as_dim and p not in self.pointer_params and p not in self.stride_params
        ]

    # --- queries -----------------------------------------------------------

    def pointer_root(self, node: ast.AST | None, depth: int = 4) -> str | None:
        """The parameter at the root of a pointer expression (leftmost Add operand)."""
        while node is not None and depth >= 0:
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add | ast.Sub):
                node = node.left
            elif isinstance(node, ast.Subscript):
                node = node.value
            elif isinstance(node, ast.Name):
                if node.id in self.params:
                    return node.id
                values = self.bindings.get(node.id, [])
                node = values[0] if values else None
                depth -= 1
            elif isinstance(node, ast.Call) and self.src.call_name(node) in BLOCK_PTR:
                node = node.args[0] if node.args else None
            else:
                return None
        return None

    def binding(self, name: str) -> ast.AST | None:
        """The value of ``name`` if it is assigned exactly once in scope."""
        values = self.bindings.get(name, [])
        return values[0] if len(values) == 1 else None

    def resolve(self, node: ast.AST, depth: int = 4) -> ast.AST:
        """Follow single-assignment Name bindings."""
        while depth and isinstance(node, ast.Name):
            bound = self.binding(node.id)
            if bound is None:
                break
            node, depth = bound, depth - 1
        return node

    def const(self, node: ast.AST | None, depth: int = 4) -> float | None:
        """Numeric value of a constant expression, or ``None``."""
        if node is None or depth < 0:
            return None
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool) or not isinstance(value, int | float):
                return None
            return float(value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
            inner = self.const(node.operand, depth - 1)
            if inner is None:
                return None
            return -inner if isinstance(node.op, ast.USub) else inner
        if isinstance(node, ast.Name):
            bound = self.binding(node.id)
            return self.const(bound, depth - 1) if bound is not None else None
        if isinstance(node, ast.Attribute) and self.src.dotted(node) in {"math.inf", "np.inf"}:
            return math.inf
        if isinstance(node, ast.Call):
            name = self.src.call_name(node)
            if name == "float" and len(node.args) == 1:
                literal = node.args[0]
                if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                    try:
                        return float(literal.value)
                    except ValueError:
                        return None
            if name == "tl.full":
                return self.const(arg(node, 1, "value"), depth - 1)
        return None

    def is_const(self, node: ast.AST | None, value: float) -> bool:
        found = self.const(node)
        return found is not None and found == value

    def calls(self, names: Iterable[str]) -> Iterator[ast.Call]:
        wanted = frozenset(names)
        for node in self.nodes:
            if isinstance(node, ast.Call) and self.src.call_name(node) in wanted:
                yield node

    def name_of(self, call: ast.Call) -> str | None:
        return self.src.call_name(call)

    def tl(self) -> str | None:
        return self.src.module_alias("tl")

    def seg(self, node: ast.AST) -> str:
        return self.src.segment(node)

    def wseg(self, node: ast.AST) -> str:
        return wrap(self.seg(node), node)

    def edit(self, node: ast.AST, text: str) -> TextEdit:
        return self.src.replace(node, text)

    def partner(self, pool: list[str], name: str) -> str | None:
        """Next name after ``name`` in ``pool`` (cyclic), or ``None``."""
        if name not in pool or len(pool) < 2:
            return None
        return pool[(pool.index(name) + 1) % len(pool)]


Finder = Callable[[ScopeContext], Iterable[Candidate]]


@dataclass(frozen=True)
class Operator:
    """A mutation operator: metadata plus a site finder."""

    name: str
    family: str
    origin: str
    kbm_rule: str | None
    scopes: tuple[str, ...]
    description: str
    finder: Finder
    ports: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(f"{self.name}: unknown family {self.family}")
        if self.origin not in ORIGINS:
            raise ValueError(f"{self.name}: unknown origin {self.origin}")
        if self.origin == "paper" and not (self.kbm_rule or self.ports):
            raise ValueError(f"{self.name}: a paper rule must name its KernelBench-M rule")
        if self.origin == "triton-only" and (self.kbm_rule or self.ports):
            raise ValueError(f"{self.name}: a Triton-only extension has no KernelBench-M rule")
        if not set(self.scopes) <= set(SCOPES) or not self.scopes:
            raise ValueError(f"{self.name}: bad scopes {self.scopes}")

    def candidates(self, ctx: ScopeContext) -> list[Candidate]:
        if ctx.scope not in self.scopes:
            return []
        return list(self.finder(ctx))

    def table_row(self) -> dict[str, object]:
        return {
            "operator": self.name,
            "family": self.family,
            "rule_origin": self.origin,
            "kernelbench_m_rule": self.kbm_rule,
            "also_ports": list(self.ports),
            "scopes": list(self.scopes),
            "description": self.description,
        }


# --- generic helpers ---------------------------------------------------------


def arg(call: ast.Call, index: int | None, keyword: str | None) -> ast.AST | None:
    """Positional argument ``index`` or keyword ``keyword`` of ``call``."""
    if index is not None and len(call.args) > index:
        candidate = call.args[index]
        if not isinstance(candidate, ast.Starred):
            return candidate
    if keyword is not None:
        for kw in call.keywords:
            if kw.arg == keyword:
                return kw.value
    return None


def kwarg(call: ast.Call, keyword: str) -> ast.keyword | None:
    for kw in call.keywords:
        if kw.arg == keyword:
            return kw
    return None


def rebuild_call(
    ctx: ScopeContext,
    call: ast.Call,
    *,
    drop_positional: Iterable[int] = (),
    drop_keywords: Iterable[str] = (),
    set_keywords: dict[str, str] | None = None,
    func_text: str | None = None,
    replace_positional: dict[int, str] | None = None,
) -> str:
    """Re-render ``call`` from source segments with the requested changes."""
    drop_pos = set(drop_positional)
    drop_kw = set(drop_keywords)
    replace_pos = replace_positional or {}
    pieces = []
    for index, value in enumerate(call.args):
        if index in drop_pos:
            continue
        pieces.append(replace_pos.get(index, ctx.seg(value)))
    pending = dict(set_keywords or {})
    for kw in call.keywords:
        if kw.arg is not None and kw.arg in drop_kw:
            continue
        if kw.arg is not None and kw.arg in pending:
            pieces.append(f"{kw.arg}={pending.pop(kw.arg)}")
        elif kw.arg is None:
            pieces.append(f"**{ctx.seg(kw.value)}")
        else:
            pieces.append(f"{kw.arg}={ctx.seg(kw.value)}")
    pieces.extend(f"{key}={value}" for key, value in pending.items())
    head = func_text if func_text is not None else ctx.seg(call.func)
    return f"{head}({', '.join(pieces)})"


def swap_attr(ctx: ScopeContext, call: ast.Call, new_attr: str) -> str | None:
    """Text of ``call``'s callee with its final attribute replaced."""
    if not isinstance(call.func, ast.Attribute):
        return None
    return f"{ctx.seg(call.func.value)}.{new_attr}"


def _names_in(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def names_in(node: ast.AST) -> set[str]:
    return _names_in(node)


def inside_call(ctx: ScopeContext, node: ast.AST, names: frozenset[str]) -> ast.Call | None:
    """Nearest enclosing call (within scope) whose callee is in ``names``."""
    current = parent(node)
    while current is not None:
        if isinstance(current, ast.Call) and ctx.src.call_name(current) in names:
            return current
        if isinstance(current, ast.stmt):
            return None
        current = parent(current)
    return None


def compare_of(ctx: ScopeContext, cond: ast.AST) -> ast.Compare | None:
    """``cond`` itself or the Compare a single-assignment Name is bound to."""
    resolved = ctx.resolve(cond, depth=1) if isinstance(cond, ast.Name) else cond
    return resolved if isinstance(resolved, ast.Compare) else None


def same_name(a: ast.AST | None, b: ast.AST | None) -> bool:
    return isinstance(a, ast.Name) and isinstance(b, ast.Name) and a.id == b.id


def positive_branch_compare(
    ctx: ScopeContext, where: ast.Call
) -> tuple[ast.Compare, ast.AST, ast.AST, ast.AST] | None:
    """Match ``tl.where(x > 0, x, other)``; return (compare, zero node, x, other)."""
    cond, true_val, false_val = (arg(where, i, None) for i in range(3))
    if cond is None or true_val is None or false_val is None:
        return None
    compare = compare_of(ctx, cond)
    if compare is None or len(compare.ops) != 1:
        return None
    op, left, right = compare.ops[0], compare.left, compare.comparators[0]
    if isinstance(op, ast.Gt) and same_name(left, true_val) and ctx.is_const(right, 0.0):
        return compare, right, true_val, false_val
    if isinstance(op, ast.Lt) and same_name(right, true_val) and ctx.is_const(left, 0.0):
        return compare, left, true_val, false_val
    return None


def statement_of(node: ast.AST) -> ast.stmt | None:
    current: ast.AST | None = node
    while current is not None and not isinstance(current, ast.stmt):
        current = parent(current)
    return current


def is_expression_statement(call: ast.Call) -> bool:
    return isinstance(parent(call), ast.Expr)


def float_repr(value: float) -> str:
    """Shortest literal for ``value`` rounded to 12 significant digits."""
    text = repr(float(f"{float(value):.12g}"))
    return text if ("e" in text or "." in text or "inf" in text) else text + ".0"
