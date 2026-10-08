"""Static reading of a KernelBench problem's ``get_inputs`` (no torch, no execution).

The hack controls need each problem's native input shapes (the KBV H.1
shortcut guards on the exact test shape) and whether the official inputs are
non-negative (``torch.rand``). Calling ``get_inputs()`` would allocate up to
17 GB, so the module-level constants and the generator calls are evaluated
statically instead. Anything that is not a plain literal expression fails
closed.
"""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass

_GENERATORS = {"torch.rand": "rand", "torch.randn": "randn", "torch.randint": "randint"}
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
}


class NativeInputError(ValueError):
    """``get_inputs`` cannot be read statically."""


@dataclass(frozen=True)
class InputSpec:
    generator: str  # rand | randn | randint | other
    shape: tuple[int, ...] | None
    transformed: bool  # the generator result is further transformed

    @property
    def nonnegative_uniform(self) -> bool:
        return self.generator == "rand" and not self.transformed


def _dotted(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return ".".join([node.id, *reversed(parts)])


def _evaluate(node: ast.AST, env: dict[str, object]) -> object:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float | str):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise NativeInputError(f"unknown name {node.id}")
        return env[node.id]
    if isinstance(node, ast.Tuple | ast.List):
        out: list[object] = []
        for element in node.elts:
            if isinstance(element, ast.Starred):
                out.extend(_as_tuple(_evaluate(element.value, env)))
            else:
                out.append(_evaluate(element, env))
        return tuple(out)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_number(_evaluate(node.operand, env))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _evaluate(node.left, env), _evaluate(node.right, env)
        if isinstance(left, tuple) and isinstance(right, tuple) and isinstance(node.op, ast.Add):
            return left + right
        return _BINOPS[type(node.op)](_number(left), _number(right))
    raise NativeInputError(f"not a literal expression: {ast.dump(node)[:80]}")


def _number(value: object) -> int | float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise NativeInputError(f"expected a number, got {value!r}")
    return value


def _as_tuple(value: object) -> tuple:
    if not isinstance(value, tuple):
        raise NativeInputError(f"expected a tuple, got {value!r}")
    return value


def _module_env(tree: ast.Module) -> dict[str, object]:
    env: dict[str, object] = {}
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        try:
            value = _evaluate(stmt.value, env)
        except NativeInputError:
            continue
        for target in stmt.targets:  # also chained: height = width = 256
            if isinstance(target, ast.Name):
                env[target.id] = value
    return env


def _shape(call: ast.Call, generator: str, env: dict[str, object]) -> tuple[int, ...]:
    if generator == "randint":
        size = call.args[2] if len(call.args) > 2 else None
        for kw in call.keywords:
            if kw.arg == "size":
                size = kw.value
        if size is None:
            raise NativeInputError("torch.randint without a size")
        dims: list[object] = list(_as_tuple(_evaluate(size, env)))
    elif len(call.args) == 1 and not isinstance(call.args[0], ast.Starred):
        value = _evaluate(call.args[0], env)
        dims = list(value) if isinstance(value, tuple) else [value]
    else:
        dims = list(_as_tuple(_evaluate(ast.Tuple(elts=call.args, ctx=ast.Load()), env)))
    if not all(isinstance(d, int) and not isinstance(d, bool) and d > 0 for d in dims):
        raise NativeInputError(f"non-integer shape {dims!r}")
    return tuple(int(d) for d in dims)  # type: ignore[arg-type]


def _spec(node: ast.AST, env: dict[str, object]) -> InputSpec:
    generators = [
        n for n in ast.walk(node) if isinstance(n, ast.Call) and _dotted(n.func) in _GENERATORS
    ]
    if len(generators) != 1:
        return InputSpec("other", None, True)
    call = generators[0]
    generator = _GENERATORS[_dotted(call.func) or ""]
    transformed = node is not call or any(kw.arg in {"dtype", "device"} for kw in call.keywords)
    return InputSpec(generator, _shape(call, generator, env), transformed)


def native_inputs(problem_source: str) -> list[InputSpec]:
    """Input specs of ``get_inputs()``'s returned list, in order."""
    tree = ast.parse(problem_source)
    env = _module_env(tree)
    function = next(
        (s for s in tree.body if isinstance(s, ast.FunctionDef) and s.name == "get_inputs"), None
    )
    if function is None:
        raise NativeInputError("problem has no get_inputs")
    local: dict[str, ast.AST] = {}
    returned: list[ast.AST] | None = None
    for stmt in function.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name):
                local[target.id] = stmt.value
        elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.List | ast.Tuple):
            returned = list(stmt.value.elts)
    if returned is None:
        raise NativeInputError("get_inputs does not return a literal list")
    specs = []
    for element in returned:
        expr = local.get(element.id, element) if isinstance(element, ast.Name) else element
        specs.append(_spec(expr, env))
    return specs
