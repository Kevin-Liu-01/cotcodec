"""Source model for the Triton mutator: parsing, scopes, spans and name resolution.

A mutation is a set of non-overlapping text edits on the original ``kernel.py``
source. Edits replace the exact source span of one AST node, so everything the
mutation does not touch (comments, formatting, other functions) stays byte for
byte identical to the parent. Python reports column offsets in UTF-8 bytes; the
span arithmetic here converts them to character offsets.

Two scopes exist:

- **device**: the bodies of ``@triton.jit`` functions (decorators excluded);
- **launch**: every other statement of the module (``ModelNew``, launchers,
  grid lambdas), excluding imports and the jit functions themselves.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

# Canonical prefixes for module aliases. Inductor output imports
# ``triton_helpers`` and ``libdevice`` from torch; hand-written kernels import
# ``triton.language as tl`` and libdevice from ``triton.language.extra``.
_MODULE_CANON = {
    "triton.language": "tl",
    "triton.language.math": "tl.math",
    "triton.language.extra.libdevice": "libdevice",
    "triton.language.extra.cuda.libdevice": "libdevice",
    "torch._inductor.runtime.triton_helpers": "triton_helpers",
    "torch._inductor.runtime.triton_helpers.libdevice": "libdevice",
    "torch._inductor.runtime.triton_helpers.math": "tl.math",
    "triton": "triton",
    "math": "math",
}


class SourceError(ValueError):
    """Raised when a kernel source cannot be parsed or an edit is malformed."""


@dataclass(frozen=True, order=True)
class TextEdit:
    """Replace ``text[start:end]`` (character offsets) with ``replacement``."""

    start: int
    end: int
    replacement: str


def is_jit_decorator(node: ast.expr) -> bool:
    """True for ``@triton.jit``, ``@jit`` and ``@triton.jit(...)``."""
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        return target.attr == "jit" and isinstance(target.value, ast.Name)
    return isinstance(target, ast.Name) and target.id == "jit"


def normalized_ast_dump(tree: ast.AST) -> str:
    """Formatting- and comment-free dump with docstrings removed."""
    tree = _strip_docstrings(ast.parse(ast.unparse(tree)))
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def normalized_ast_hash(text: str) -> str:
    """SHA-256 of the normalized AST of ``text`` (the CPU-side dedup key)."""
    return hashlib.sha256(normalized_ast_dump(ast.parse(text)).encode()).hexdigest()


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    return tree


@dataclass
class KernelSource:
    """A parsed ``kernel.py`` with span helpers and alias resolution."""

    text: str
    filename: str = "kernel.py"
    tree: ast.Module = field(init=False)
    aliases: dict[str, str] = field(init=False)
    _line_starts: list[int] = field(init=False, repr=False)
    _lines: list[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            self.tree = ast.parse(self.text, self.filename)
        except SyntaxError as exc:
            raise SourceError(f"{self.filename} does not parse: {exc}") from exc
        self._lines = self.text.splitlines(keepends=True)
        starts, offset = [], 0
        for line in self._lines:
            starts.append(offset)
            offset += len(line)
        starts.append(offset)
        self._line_starts = starts
        self.aliases = self._collect_aliases()
        _attach_parents(self.tree)

    # --- spans -------------------------------------------------------------

    def offset(self, lineno: int, col_byte: int) -> int:
        """Character offset of a (1-based line, UTF-8 byte column) position."""
        if lineno - 1 >= len(self._lines):
            return self._line_starts[-1]
        line = self._lines[lineno - 1]
        prefix = line.encode("utf-8")[:col_byte].decode("utf-8", errors="strict")
        return self._line_starts[lineno - 1] + len(prefix)

    def span(self, node: ast.AST) -> tuple[int, int]:
        if getattr(node, "end_lineno", None) is None:
            raise SourceError(f"node {type(node).__name__} has no source position")
        return (
            self.offset(node.lineno, node.col_offset),
            self.offset(node.end_lineno, node.end_col_offset),
        )

    def segment(self, node: ast.AST) -> str:
        start, end = self.span(node)
        return self.text[start:end]

    def site(self, node: ast.AST) -> tuple[int, int]:
        """(1-based line, 0-based character column) of ``node``."""
        start, _ = self.span(node)
        line = node.lineno
        return line, start - self._line_starts[line - 1]

    def apply(self, edits: Sequence[TextEdit]) -> str:
        """Return the source with ``edits`` applied; edits must not overlap."""
        ordered = sorted(edits)
        for left, right in zip(ordered, ordered[1:], strict=False):
            if right.start < left.end:
                raise SourceError("overlapping edits")
        out, cursor = [], 0
        for edit in ordered:
            if not 0 <= edit.start <= edit.end <= len(self.text):
                raise SourceError("edit outside the source")
            out.append(self.text[cursor : edit.start])
            out.append(edit.replacement)
            cursor = edit.end
        out.append(self.text[cursor:])
        return "".join(out)

    def replace(self, node: ast.AST, replacement: str) -> TextEdit:
        start, end = self.span(node)
        return TextEdit(start, end, replacement)

    # --- scopes ------------------------------------------------------------

    def jit_functions(self) -> list[ast.FunctionDef]:
        found = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and any(
                is_jit_decorator(dec) for dec in node.decorator_list
            ):
                found.append(node)
        return sorted(found, key=lambda fn: (fn.lineno, fn.col_offset))

    def launch_statements(self) -> list[ast.stmt]:
        """Top-level statements outside jit functions and imports."""
        jit = set(map(id, self.jit_functions()))
        return [
            stmt
            for stmt in self.tree.body
            if id(stmt) not in jit and not isinstance(stmt, ast.Import | ast.ImportFrom)
        ]

    # --- names -------------------------------------------------------------

    def _collect_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {"tl": "tl", "triton": "triton", "libdevice": "libdevice"}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    canon = _MODULE_CANON.get(alias.name)
                    if canon:
                        aliases[alias.asname or alias.name.split(".")[0]] = (
                            canon if alias.asname else alias.name.split(".")[0]
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    full = f"{node.module}.{alias.name}"
                    canon = _MODULE_CANON.get(full)
                    if canon:
                        aliases[alias.asname or alias.name] = canon
        return aliases

    def dotted(self, node: ast.AST) -> str | None:
        """Canonical dotted name of a Name/Attribute chain, e.g. ``tl.maximum``."""
        parts: list[str] = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        head = self.aliases.get(node.id, node.id)
        name = ".".join([head, *reversed(parts)])
        if name.startswith("triton.language."):
            name = "tl." + name[len("triton.language.") :]
        if name.startswith("tl.extra.cuda.libdevice.") or name.startswith("tl.extra.libdevice."):
            name = "libdevice." + name.rsplit(".", 1)[1]
        return name

    def call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            return self.dotted(node.func)
        return None

    def module_alias(self, canon: str) -> str | None:
        """Local name bound to canonical module ``canon`` (e.g. ``tl``)."""
        for local, value in sorted(self.aliases.items()):
            if value == canon and _name_is_bound(self.tree, local):
                return local
        return None


def _name_is_bound(tree: ast.Module, name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                if bound == name:
                    return True
    return False


def _attach_parents(tree: ast.AST) -> None:
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child._q1_parent = parent  # type: ignore[attr-defined]


def parent(node: ast.AST) -> ast.AST | None:
    return getattr(node, "_q1_parent", None)


def iter_scope(nodes: Sequence[ast.AST]) -> Iterator[ast.AST]:
    """Pre-order traversal in source order, skipping decorators and nested jit fns."""
    stack = list(reversed(nodes))
    while stack:
        node = stack.pop()
        yield node
        children = []
        for name, value in ast.iter_fields(node):
            if name == "decorator_list":
                continue
            if isinstance(value, list):
                children.extend(v for v in value if isinstance(v, ast.AST))
            elif isinstance(value, ast.AST):
                children.append(value)
        for child in reversed(children):
            if isinstance(child, ast.FunctionDef) and any(
                is_jit_decorator(dec) for dec in child.decorator_list
            ):
                continue
            stack.append(child)


ATOMIC_TYPES = (ast.Name, ast.Attribute, ast.Call, ast.Subscript)


def wrap(text: str, node: ast.AST | None = None) -> str:
    """Parenthesise ``text`` unless ``node`` is an atom; safe in any expression slot."""
    if isinstance(node, ATOMIC_TYPES):
        return text
    if isinstance(node, ast.Constant) and not text.lstrip().startswith("-"):
        return text
    return f"({text})"
