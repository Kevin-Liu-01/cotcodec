"""KernelBench@423217d9 problem access, constant analysis and shape overrides.

Problems are vendored verbatim under ``third_party/kernelbench/problems`` and
pinned by the SHA-256 table in ``data/kernelbench_423217d9_problems.json``.
Every load verifies the file hash, so a drifted problem fails closed.

Shape variation (gate c2/c3 and audit A3) never edits a problem by hand. A
problem's module-level integer constants are classified by static scope
analysis (``symtable``):

- *init-bound*: reached, directly or through other constants, from
  ``get_init_inputs`` (changing it would change the weights);
- *model-bound*: read as a global from inside ``class Model``;
- *free roots*: literal-valued integer constants reached from ``get_inputs``
  that are neither init- nor model-bound.

An override rewrites only the value span of a free root's assignment, so the
rest of the file stays byte-identical and derived constants (``input_shape =
(num_classes,)``) are recomputed by the problem's own code.

This module imports torch lazily; the static analysis runs without it.
"""

from __future__ import annotations

import ast
import json
import re
import symtable
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from harness.q1.schema import (
    KERNELBENCH_PROBLEMS_REVISION,
    SchemaError,
    parse_problem_id,
    problem_relpath,
    sha256_bytes,
)

Q1_ROOT = Path(__file__).resolve().parent
PROBLEMS_ROOT = Q1_ROOT / "third_party" / "kernelbench" / "problems"
PROBLEM_HASHES_PATH = Q1_ROOT / "data" / "kernelbench_423217d9_problems.json"

_CONSTANT_ZERO = "constant-zero output (KernelBench-Verified App. I)"
#: Problems excluded from the Q1 Stage 0 corpus before any data, with reasons.
EXCLUDED_PROBLEMS: dict[str, str] = {
    "L2/23_Conv3d_GroupNorm_Mean": _CONSTANT_ZERO,
    "L2/80_Gemm_Max_Subtract_GELU": _CONSTANT_ZERO,
    "L2/83_Conv3d_GroupNorm_Min_Clamp_Dropout": _CONSTANT_ZERO,
    "L2/66_Matmul_Dropout_Softmax": "training-mode Dropout makes the reference random",
}

_MATMUL_NAME_RE = re.compile(
    r"(?i)(matmul|matrix_multiplication|matrix_vector_multiplication|tensor_matrix_multiplication)"
)


class ProblemError(ValueError):
    """Raised when a problem cannot be loaded, analysed or overridden."""


# --- Loading -------------------------------------------------------------------


@lru_cache(maxsize=1)
def problem_hashes() -> dict[str, str]:
    data = json.loads(PROBLEM_HASHES_PATH.read_text(encoding="utf-8"))
    if data.get("kernelbench_revision") != KERNELBENCH_PROBLEMS_REVISION:
        raise ProblemError("problem hash table is not for the pinned KernelBench revision")
    return dict(data["sha256"])


def problem_path(problem_id: str) -> Path:
    return PROBLEMS_ROOT / problem_relpath(problem_id)


def list_problem_ids(
    levels: Iterable[int] = (1, 2), *, include_excluded: bool = False
) -> list[str]:
    """All vendored problem ids at the given levels, in (level, number) order."""
    ids = []
    for problem_id in problem_hashes():
        level, number, _ = parse_problem_id(problem_id)
        if level in set(levels) and (include_excluded or problem_id not in EXCLUDED_PROBLEMS):
            ids.append((level, number, problem_id))
    return [problem_id for _, _, problem_id in sorted(ids)]


def load_problem_source(problem_id: str, *, verify: bool = True) -> str:
    """Return the problem file text after checking its pinned SHA-256."""
    try:
        parse_problem_id(problem_id)
    except SchemaError as exc:
        raise ProblemError(str(exc)) from exc
    path = problem_path(problem_id)
    if not path.is_file():
        raise ProblemError(f"{problem_id}: {path.name} is not vendored")
    data = path.read_bytes()
    if verify:
        expected = problem_hashes().get(problem_id)
        if expected is None:
            raise ProblemError(f"{problem_id}: no pinned hash")
        if sha256_bytes(data) != expected:
            raise ProblemError(f"{problem_id}: file hash differs from the pinned table")
    return data.decode("utf-8")


def is_matmul_problem(problem_id: str) -> bool:
    level, _, name = parse_problem_id(problem_id)
    return level == 1 and bool(_MATMUL_NAME_RE.search(name)) and "scalar" not in name.lower()


# --- Static analysis -------------------------------------------------------------


@dataclass(frozen=True)
class Constant:
    """A module-level constant, or one integer element ``name[i]`` of a literal tuple."""

    name: str
    value: Any
    dep_order: tuple[str, ...]  # constants the value reads, in source order
    lineno: int
    value_start: int  # character offset of the value expression in the source
    value_end: int

    @property
    def deps(self) -> frozenset[str]:
        return frozenset(self.dep_order)

    @property
    def is_int_root(self) -> bool:
        return (
            isinstance(self.value, int)
            and not isinstance(self.value, bool)
            and not self.dep_order
            and self.value > 0
        )


@dataclass(frozen=True)
class ProblemAnalysis:
    problem_id: str
    constants: dict[str, Constant]
    input_roots: tuple[str, ...]
    init_bound: frozenset[str]
    model_bound: frozenset[str]
    free_roots: tuple[str, ...]
    leading: str | None
    inner: str | None
    is_matmul: bool
    notes: tuple[str, ...] = field(default=())

    def native_values(self) -> dict[str, int]:
        return {name: int(self.constants[name].value) for name in self.free_roots}


_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
}


def _eval_const(node: ast.AST, env: Mapping[str, Any]) -> Any:
    """Evaluate a literal-ish constant expression; raise ValueError otherwise."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float | bool | str):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env and env[node.id] is not None:
            return env[node.id]
        raise ValueError(node.id)
    if isinstance(node, ast.Tuple | ast.List):
        values = [_eval_const(item, env) for item in node.elts]
        return tuple(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_const(node.operand, env)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval_const(node.left, env), _eval_const(node.right, env))
    if isinstance(node, ast.Starred):
        raise ValueError("starred")
    raise ValueError(type(node).__name__)


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _names_in_order(node: ast.AST) -> list[str]:
    names = sorted(
        (n.lineno, n.col_offset, n.id) for n in ast.walk(node) if isinstance(n, ast.Name)
    )
    return [name for _, _, name in names]


def _literal_int_elements(node: ast.AST) -> list[int] | None:
    """Values of a tuple whose elements are name-free integer expressions."""
    if not isinstance(node, ast.Tuple) or not node.elts:
        return None
    values = []
    for item in node.elts:
        if _names_in_order(item):
            return None
        try:
            value = _eval_const(item, {})
        except (ValueError, ZeroDivisionError, TypeError):
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            return None
        values.append(value)
    return values


def _module_constants(source: str, tree: ast.Module) -> dict[str, Constant]:
    offsets = _line_offsets(source)

    def span(node: ast.AST) -> tuple[int, int]:
        start = offsets[node.lineno - 1] + node.col_offset
        end = offsets[node.end_lineno - 1] + node.end_col_offset
        return start, end

    constants: dict[str, Constant] = {}
    env: dict[str, Any] = {}
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            value = _eval_const(node.value, env)
        except (ValueError, ZeroDivisionError, TypeError):
            value = None
        deps: list[str] = []
        for name in _names_in_order(node.value):
            if name in constants and name not in deps:
                deps.append(name)
        element_values = _literal_int_elements(node.value)
        if element_values is not None:
            # ``input_shape = (32768,)``: each element is its own overridable constant.
            for index, (item, item_value) in enumerate(
                zip(node.value.elts, element_values, strict=True)
            ):
                element = f"{target.id}[{index}]"
                start, end = span(item)
                constants[element] = Constant(element, item_value, (), node.lineno, start, end)
                deps.append(element)
        start, end = span(node.value)
        constants[target.id] = Constant(target.id, value, tuple(deps), node.lineno, start, end)
        env[target.id] = value
    return constants


def _global_refs(table: symtable.SymbolTable) -> set[str]:
    refs: set[str] = set()
    for symbol in table.get_symbols():
        if symbol.is_referenced() and (symbol.is_global() or symbol.is_free()):
            refs.add(symbol.get_name())
    for child in table.get_children():
        refs |= _global_refs(child)
    return refs


def _closure(names: Iterable[str], constants: Mapping[str, Constant]) -> set[str]:
    seen: set[str] = set()
    stack = [name for name in names if name in constants]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        stack.extend(dep for dep in constants[name].deps if dep not in seen)
    return seen


def analyze_problem(problem_id: str, source: str | None = None) -> ProblemAnalysis:
    """Classify a problem's module constants (see module docstring)."""
    if source is None:
        source = load_problem_source(problem_id)
    tree = ast.parse(source)
    constants = _module_constants(source, tree)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"get_inputs", "get_init_inputs"}
    }
    if set(functions) != {"get_inputs", "get_init_inputs"}:
        raise ProblemError(f"{problem_id}: get_inputs and get_init_inputs are required")
    table = symtable.symtable(source, problem_id, "exec")
    scopes = {child.get_name(): child for child in table.get_children()}
    if "Model" not in scopes:
        raise ProblemError(f"{problem_id}: class Model is missing")
    model_refs = _global_refs(scopes["Model"])
    init_refs = _global_refs(scopes["get_init_inputs"])
    input_refs = _global_refs(scopes["get_inputs"])
    init_bound = frozenset(_closure(init_refs, constants))
    model_bound = frozenset(_closure(model_refs, constants))
    loads = sorted(
        (node.lineno, node.col_offset, node.id)
        for node in ast.walk(functions["get_inputs"])
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in input_refs
    )
    ordered: list[str] = []

    def expand(name: str, guard: frozenset[str]) -> None:
        if name not in constants or name in guard:
            return
        if not constants[name].dep_order:
            if name not in ordered:
                ordered.append(name)
            return
        for dep in constants[name].dep_order:
            expand(dep, guard | {name})

    for _, _, name in loads:
        expand(name, frozenset())
    input_roots = tuple(ordered)
    notes: list[str] = []
    free: list[str] = []
    for name in input_roots:
        constant = constants[name]
        if not constant.is_int_root:
            notes.append(f"{name}: not a positive literal integer, kept fixed")
            continue
        if name in init_bound:
            continue
        if name in model_bound:
            notes.append(f"{name}: read by class Model, kept fixed")
            continue
        free.append(name)
    return ProblemAnalysis(
        problem_id=problem_id,
        constants=constants,
        input_roots=input_roots,
        init_bound=init_bound,
        model_bound=model_bound,
        free_roots=tuple(free),
        leading=free[0] if free else None,
        inner=free[-1] if free else None,
        is_matmul=is_matmul_problem(problem_id),
        notes=tuple(notes),
    )


def override_constants(source: str, analysis: ProblemAnalysis, overrides: Mapping[str, int]) -> str:
    """Rewrite the value span of each overridden free root; everything else is untouched."""
    for name, value in overrides.items():
        if name not in analysis.free_roots:
            raise ProblemError(f"{analysis.problem_id}: {name} is not a free root")
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ProblemError(f"{analysis.problem_id}: {name} must be a positive integer")
    edits = sorted(
        (
            (analysis.constants[name].value_start, analysis.constants[name].value_end, str(value))
            for name, value in overrides.items()
        ),
        reverse=True,
    )
    for start, end, text in edits:
        source = source[:start] + text + source[end:]
    return source


# --- Execution helpers (torch required) --------------------------------------------


def exec_problem(source: str, filename: str = "<kernelbench-problem>") -> dict[str, Any]:
    """Execute problem source the way KernelBench does (``exec`` into a dict)."""
    context: dict[str, Any] = {"__name__": "kernelbench_problem"}
    exec(compile(source, filename, "exec"), context)  # noqa: S102 - pinned, hashed problem files
    for name in ("Model", "get_inputs", "get_init_inputs"):
        if name not in context:
            raise ProblemError(f"problem defines no {name}")
    return context


def meta_input_summary(source: str) -> dict[str, Any]:
    """Shapes, dtypes and total bytes of ``get_inputs()`` evaluated on the meta device."""
    import torch

    context = exec_problem(source)
    with torch.device("meta"):
        inputs = context["get_inputs"]()
    shapes: list[list[int] | None] = []
    dtypes: list[str] = []
    total = 0
    for item in inputs:
        if isinstance(item, torch.Tensor):
            shapes.append(list(item.shape))
            dtypes.append(str(item.dtype).replace("torch.", ""))
            total += item.numel() * item.element_size()
        else:
            shapes.append(None)
            dtypes.append(type(item).__name__)
    return {"input_shapes": shapes, "input_dtypes": dtypes, "input_bytes": int(total)}


def init_inputs_value(source: str) -> list[Any]:
    """``get_init_inputs()`` as plain Python values, for invariance checks."""
    context = exec_problem(source)
    values = context["get_init_inputs"]()
    return [repr(value) for value in values]


__all__ = [
    "EXCLUDED_PROBLEMS",
    "PROBLEMS_ROOT",
    "Constant",
    "ProblemAnalysis",
    "ProblemError",
    "analyze_problem",
    "exec_problem",
    "init_inputs_value",
    "is_matmul_problem",
    "list_problem_ids",
    "load_problem_source",
    "meta_input_summary",
    "override_constants",
    "problem_hashes",
    "problem_path",
]
