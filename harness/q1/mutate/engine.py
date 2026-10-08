"""Site enumeration and CPU-side deduplication.

``enumerate_mutants`` applies every operator to every scope of one
``kernel.py`` and returns the syntactically valid, behaviourally plausible
mutants, one per (operator, site), in a deterministic order:

1. operators in registry order (schema family order);
2. within an operator, device scopes (jit functions in source order) and then
   the launch scope;
3. within a scope, candidates by (line, column, edit spans).

Each mutant is checked to parse, compared against the parent, and
deduplicated by the SHA-256 of its normalized AST (formatting, comments and
docstrings removed). This is the CPU analogue of trivial compiler equivalence;
the compiled-specialization hook in ``compiled.py`` removes the remaining
equivalent and duplicate mutants at the cubin level.
"""

from __future__ import annotations

import ast
import hashlib
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from harness.q1.mutate.operators import OPERATORS, Operator, ScopeContext
from harness.q1.mutate.source import KernelSource, SourceError, normalized_ast_hash

MUTANT_ID_MAX = 160


@dataclass(frozen=True)
class MutantCandidate:
    """A distinct mutant of one kernel source."""

    operator: str
    family: str
    rule_origin: str
    kbm_rule: str | None
    line: int
    col: int
    scope: str
    function: str | None
    source: str
    dedup_hash: str
    detail: str
    n_edits: int
    description: str

    @property
    def site(self) -> str:
        return f"kernel.py:{self.line}:{self.col}"

    @property
    def key(self) -> str:
        return f"{self.operator}@{self.line}:{self.col}"


@dataclass(frozen=True)
class Rejection:
    """A candidate that did not become a distinct mutant, and why."""

    operator: str
    line: int
    col: int
    reason: str  # "syntax" | "equivalent-to-parent" | "duplicate"
    duplicate_of: str | None = None


@dataclass
class Enumeration:
    parent_hash: str
    distinct: list[MutantCandidate] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        reasons = Counter(r.reason for r in self.rejected)
        return {
            "candidates": len(self.distinct) + len(self.rejected),
            "distinct": len(self.distinct),
            "syntax": reasons.get("syntax", 0),
            "equivalent_to_parent": reasons.get("equivalent-to-parent", 0),
            "duplicate": reasons.get("duplicate", 0),
            "by_family": dict(sorted(Counter(m.family for m in self.distinct).items())),
            "by_operator": dict(sorted(Counter(m.operator for m in self.distinct).items())),
        }


class OperatorFailure(RuntimeError):
    """An operator raised while enumerating sites (a mutator bug; fail closed)."""


def scope_contexts(src: KernelSource) -> list[ScopeContext]:
    contexts = [ScopeContext.device(src, fn) for fn in src.jit_functions()]
    contexts.append(ScopeContext.launch(src))
    return contexts


def enumerate_mutants(
    text: str, *, filename: str = "kernel.py", operators: Sequence[Operator] = OPERATORS
) -> Enumeration:
    """Enumerate distinct mutants of ``text`` (deterministic)."""
    src = KernelSource(text, filename)
    if not src.jit_functions():
        raise SourceError(f"{filename} defines no @triton.jit function")
    parent_hash = normalized_ast_hash(text)
    result = Enumeration(parent_hash=parent_hash)
    seen: dict[str, str] = {}
    contexts = scope_contexts(src)
    for op in operators:
        for ctx in contexts:
            try:
                found = op.candidates(ctx)
            except Exception as exc:  # noqa: BLE001 - re-raised with context
                where = ctx.function.name if ctx.function else "launch scope"
                raise OperatorFailure(f"operator {op.name} failed in {where}: {exc}") from exc
            ordered = sorted(
                found,
                key=lambda c: (src.site(c.anchor), tuple((e.start, e.end) for e in c.edits)),
            )
            for cand in ordered:
                line, col = src.site(cand.anchor)
                try:
                    mutated = src.apply(cand.edits)
                    ast.parse(mutated, filename)
                except (SourceError, SyntaxError):
                    result.rejected.append(Rejection(op.name, line, col, "syntax"))
                    continue
                digest = normalized_ast_hash(mutated)
                if digest == parent_hash:
                    result.rejected.append(Rejection(op.name, line, col, "equivalent-to-parent"))
                    continue
                if digest in seen:
                    result.rejected.append(
                        Rejection(op.name, line, col, "duplicate", duplicate_of=seen[digest])
                    )
                    continue
                candidate = MutantCandidate(
                    operator=op.name,
                    family=op.family,
                    rule_origin=op.origin,
                    kbm_rule=cand.kbm_rule or op.kbm_rule,
                    line=line,
                    col=col,
                    scope=ctx.scope,
                    function=ctx.function.name if ctx.function else None,
                    source=mutated,
                    dedup_hash=digest,
                    detail=cand.detail,
                    n_edits=len(cand.edits),
                    description=op.description,
                )
                seen[digest] = candidate.key
                result.distinct.append(candidate)
    return result


def mutant_id(substrate_id: str, candidate: MutantCandidate, taken: set[str]) -> str:
    """Directory-safe, stable id: ``<substrate>.<operator>.L<line>C<col>[-k]``."""
    base = f"{substrate_id}.{candidate.operator}.L{candidate.line}C{candidate.col}"
    if len(base) > MUTANT_ID_MAX - 4:
        digest = hashlib.sha256(base.encode()).hexdigest()[:16]
        base = f"{substrate_id[: MUTANT_ID_MAX - 4 - 18]}.{digest}"
    ident, k = base, 2
    while ident in taken:
        ident, k = f"{base}-{k}", k + 1
    taken.add(ident)
    return ident
