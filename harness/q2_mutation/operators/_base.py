"""Operator protocol, label rules and deterministic mutant planning.

An operator turns (spec requirement or outside site, base snapshot, seed) into
a recipe of primitive edits plus an :class:`Expectation` (its purity
footprint) and a label with a witness. Labels come only from the spec: an
operator never reads checker code or checker verdicts.

Planning is deterministic: candidate sites for a (task, operator) cell are
ordered by a hash of (task, operator), at most three sites are kept, and they
are assigned seeds 42, 43, 44 in that order. Each seed also drives the
operator's own parameter choices through :func:`rng_for`.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from harness.q2_mutation.operators._purity import Expectation
from harness.q2_mutation.operators._spec import (
    Binding,
    allowed_mentions,
    bound_units,
    flagged_mentions,
    is_flagged,
    req_text,
    requirement_mentions,
    spec_mentions,
)
from harness.q2_mutation.schema import (
    LABELS,
    SCHEMA_VERSION,
    Requirement,
    RequirementSpec,
    make_mutant_id,
)

EQUIV, ALT, VIOLATION, EXTRA, AMBIGUOUS = LABELS
SEEDS = (42, 43, 44)
MAX_SITES_PER_CELL = 3
RECIPE_VERSION = 1
OFFICE_FAMILIES = ("xlsx", "docx", "pptx")


class OperatorError(ValueError):
    """An operator cannot build a recipe for the requested site."""


def derive_seed(*parts: object) -> int:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def rng_for(*parts: object) -> random.Random:
    return random.Random(derive_seed(*parts))


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class Site:
    unit: str
    req_id: str | None = None
    detail: tuple[tuple[str, Any], ...] = ()

    @property
    def info(self) -> dict:
        return dict(self.detail)

    def key(self) -> str:
        return canonical_json([self.unit, self.req_id, [list(kv) for kv in self.detail]])


def site(unit: str, req_id: str | None = None, **detail: Any) -> Site:
    return Site(unit, req_id, tuple(sorted(detail.items())))


@dataclass
class Context:
    """Everything an operator may read about one task: never checker code or verdicts."""

    task_id: str
    family: str
    spec: RequirementSpec
    base: dict
    delta: dict[str, set[str]]
    bindings: dict[str, Binding]
    input_sha256: str
    target_path_in_vm: str | None = None
    source_text: str | None = None

    @property
    def bound(self) -> set[str]:
        return bound_units(self.bindings)

    @staticmethod
    def touches(unit: str, others: set[str]) -> bool:
        return any(
            unit == o or unit.startswith(o + "/") or o.startswith(unit + "/") for o in others
        )

    def is_outside(self, unit: str) -> bool:
        """Not changed by the task and not read by any requirement observable."""
        return not self.touches(unit, set(self.delta)) and not self.touches(unit, self.bound)

    def requirement(self, req_id: str) -> Requirement:
        for req in self.spec.requirements:
            if req.req_id == req_id:
                return req
        raise OperatorError(f"no requirement {req_id}")


@dataclass
class Build:
    steps: list[dict]
    expectation: Expectation
    facts: dict = field(default_factory=dict)


@dataclass
class Judgement:
    label: str
    argument: str
    rule: str
    req_ids: tuple[str, ...] = ()


class Operator:
    """Base class; subclasses set the class variables and implement three methods."""

    name: ClassVar[str]
    family: ClassVar[str]
    label_class: ClassVar[str]
    target: ClassVar[str]  # "requirement" | "outside" | "document"
    check_kinds: ClassVar[tuple[str, ...]] = ()
    aspects: ClassVar[tuple[str, ...]] = ()
    provenance: ClassVar[str] = "principled"
    stratum: ClassVar[str] = "document_model"
    description: ClassVar[str] = ""

    def sites(
        self, ctx: Context, req: Requirement | None, binding: Binding | None
    ) -> list[Site]:
        raise NotImplementedError

    def build(self, ctx: Context, where: Site, rng: random.Random) -> Build:
        raise NotImplementedError

    def judge(self, ctx: Context, where: Site, built: Build) -> Judgement:
        raise NotImplementedError

    def finalize(self, ctx: Context, built: Build) -> Build:
        """Family-wide footprint adjustments (for example spreadsheet row heights)."""
        return built

    @classmethod
    def catalog_entry(cls) -> dict:
        return {
            "name": cls.name,
            "family": cls.family,
            "label_class": cls.label_class,
            "target": cls.target,
            "check_kinds": list(cls.check_kinds),
            "aspects": list(cls.aspects),
            "provenance": cls.provenance,
            "stratum": cls.stratum,
            "description": cls.description,
        }


# --------------------------------------------------------------------------- label rules


def _quote_hits(hits: list[tuple[str, list[str]]]) -> str:
    return "; ".join(
        f"{rid} mentions {', '.join(repr(h) for h in snippets)}" for rid, snippets in hits
    )


def _cite_allowed(allowed: list[tuple[int, str, list[str]]]) -> str:
    return "; ".join(f"allowed_variations[{i}] {text!r}" for i, text, _ in allowed)


def judge_equivalence(ctx: Context, aspects: tuple[str, ...], change: str) -> Judgement:
    """E rule: the change touches only aspects no requirement constrains."""
    hits = [h for aspect in aspects for h in spec_mentions(ctx.spec, aspect)]
    allowed = [a for aspect in aspects for a in allowed_mentions(ctx.spec, aspect)]
    flagged = sorted({f for aspect in aspects for f in flagged_mentions(ctx.spec, aspect)})
    every = tuple(r.req_id for r in ctx.spec.requirements)
    if flagged and not allowed:
        return Judgement(
            AMBIGUOUS,
            f"W-E-FLAGGED: {change}; the spec flags this aspect as ambiguous ({flagged}).",
            "W-E-FLAGGED",
            tuple(f for f in flagged if not f.startswith("allowed")),
        )
    if hits and not allowed:
        return Judgement(
            AMBIGUOUS,
            f"W-E-CONFLICT: {change}; but {_quote_hits(hits)}, so the spec may constrain it.",
            "W-E-CONFLICT",
            tuple(rid for rid, _ in hits),
        )
    if allowed:
        return Judgement(
            EQUIV,
            f"W-E-ALLOWED: {change}; the spec lists it as unconstrained "
            f"({_cite_allowed(allowed)}).",
            "W-E-ALLOWED",
            every,
        )
    return Judgement(
        EQUIV,
        f"W-E-SILENT: {change}; no requirement statement or observable mentions "
        f"{'/'.join(aspects)}, and the purity check confirms no content, format, layout or "
        "structure change, so every requirement observable is preserved.",
        "W-E-SILENT",
        every,
    )


def judge_alternative(
    ctx: Context,
    req: Requirement,
    mechanism_aspects: tuple[str, ...],
    change: str,
    pinned_patterns: tuple[str, ...] = (),
) -> Judgement:
    """A rule: the observable is preserved and the requirement does not pin the mechanism."""
    text = req_text(req)
    pinned = [h for aspect in mechanism_aspects for h in requirement_mentions(req, aspect)]
    explicit = sorted(
        {m.group(0) for p in pinned_patterns for m in re.finditer(p, text, re.IGNORECASE)}
    )
    allowed = [a for aspect in mechanism_aspects for a in allowed_mentions(ctx.spec, aspect)]
    if allowed:
        return Judgement(
            ALT,
            f"W-A-ALLOWED: {change}; {req.req_id}'s observable value is preserved and the spec "
            f"marks the mechanism as unconstrained ({_cite_allowed(allowed)}).",
            "W-A-ALLOWED",
            (req.req_id,),
        )
    if explicit and not is_flagged(req.statement):
        return Judgement(
            VIOLATION,
            f"W-A-PINNED: {change}; but {req.req_id} explicitly requires the replaced "
            f"mechanism ({explicit}).",
            "W-A-PINNED",
            (req.req_id,),
        )
    flagged = sorted({f for a in mechanism_aspects for f in flagged_mentions(ctx.spec, a)})
    if is_flagged(req.statement) or flagged:
        which = req.req_id if is_flagged(req.statement) else flagged
        return Judgement(
            AMBIGUOUS,
            f"W-A-FLAGGED: {change}; the spec flags {which} as ambiguous.",
            "W-A-FLAGGED",
            (req.req_id,),
        )
    if pinned:
        return Judgement(
            AMBIGUOUS,
            f"W-A-MENTIONED: {change}; {req.req_id} mentions {sorted(set(pinned))}, so whether "
            "the mechanism is part of the requirement is unclear.",
            "W-A-MENTIONED",
            (req.req_id,),
        )
    return Judgement(
        ALT,
        f"W-A-SILENT: {change}; {req.req_id} ({req.check_kind}) constrains the observable "
        f"{req.observable!r}, which the purity check shows is unchanged, and it does not "
        f"mention {'/'.join(mechanism_aspects) or 'the mechanism'}.",
        "W-A-SILENT",
        (req.req_id,),
    )


def judge_violation(
    req: Requirement,
    aspects: tuple[str, ...],
    change: str,
    binding: Binding | None,
    implied_by_kind: tuple[str, ...] = (),
) -> Judgement:
    """R rule: the requirement pins the attacked aspect and the mutant moves it off gold."""
    hits = [h for aspect in aspects for h in requirement_mentions(req, aspect)]
    by_kind = req.check_kind in implied_by_kind
    confidence = binding.confidence if binding else "none"
    method = binding.method if binding else "none"
    if is_flagged(req.statement):
        return Judgement(
            AMBIGUOUS,
            f"W-R-FLAGGED: {change}; the spec flags {req.req_id} itself as ambiguous.",
            "W-R-FLAGGED",
            (req.req_id,),
        )
    if (hits or by_kind) and confidence in {"high", "medium"}:
        reason = (
            f"it mentions {sorted(set(hits))}" if hits else f"its check_kind is {req.check_kind}"
        )
        return Judgement(
            VIOLATION,
            f"W-R-PINNED: {change}; {req.req_id} pins this ({reason}); the site is bound to "
            f"{req.req_id} by {method} ({confidence}); gold satisfies every requirement and "
            "the mutant moves the bound observable away from gold.",
            "W-R-PINNED",
            (req.req_id,),
        )
    if hits or by_kind:
        return Judgement(
            AMBIGUOUS,
            f"W-R-WEAK-BINDING: {change}; {req.req_id} constrains this aspect but the site is "
            f"bound only by {method} ({confidence}).",
            "W-R-WEAK-BINDING",
            (req.req_id,),
        )
    return Judgement(
        AMBIGUOUS,
        f"W-R-UNPINNED: {change}; {req.req_id} does not mention {'/'.join(aspects)}.",
        "W-R-UNPINNED",
        (req.req_id,),
    )


def judge_extra(ctx: Context, aspects: tuple[str, ...], change: str, harmful: bool) -> Judgement:
    """F rule (ABC-style): the site is outside every requirement and the task's own edits."""
    allowed = [a for aspect in aspects for a in allowed_mentions(ctx.spec, aspect)]
    flagged = sorted({f for aspect in aspects for f in flagged_mentions(ctx.spec, aspect)})
    if flagged and not allowed:
        return Judgement(
            AMBIGUOUS,
            f"W-F-FLAGGED: {change}; the spec flags this aspect as ambiguous ({flagged}).",
            "W-F-FLAGGED",
        )
    if allowed:
        return Judgement(
            AMBIGUOUS if harmful else EQUIV,
            f"W-F-ALLOWED: {change}; the spec lists this aspect as unconstrained "
            f"({_cite_allowed(allowed)}).",
            "W-F-ALLOWED",
        )
    if harmful:
        return Judgement(
            EXTRA,
            f"W-F-UNREQUESTED: {change}; the site is outside every requirement binding and "
            "outside the initial-to-gold delta, no requirement asks for it, and it changes "
            "or removes existing content.",
            "W-F-UNREQUESTED",
        )
    return Judgement(
        AMBIGUOUS,
        f"W-F-COSMETIC: {change}; unrequested but cosmetic, so a user might accept it.",
        "W-F-COSMETIC",
    )


# --------------------------------------------------------------------------- planning


@dataclass
class PlannedMutant:
    """A mutation record before its document exists: purity checks are still empty."""

    record: dict

    @property
    def mutant_id(self) -> str:
        return self.record["mutant_id"]


def candidate_sites(op: Operator, ctx: Context) -> list[Site]:
    found: list[Site] = []
    if op.target == "requirement":
        for req in ctx.spec.requirements:
            if req.check_kind in op.check_kinds:
                found.extend(op.sites(ctx, req, ctx.bindings.get(req.req_id)))
    else:
        found.extend(op.sites(ctx, None, None))
    # One site per (unit, detail): keep the requirement with the strongest binding
    # (then spec order), so the label cites the requirement that best reads the unit.
    rank = {"high": 0, "medium": 1, "low": 2, "none": 3}
    order = {r.req_id: i for i, r in enumerate(ctx.spec.requirements)}

    def strength(item: Site) -> tuple[int, int]:
        if item.req_id is None:
            return (0, 0)
        binding = ctx.bindings.get(item.req_id)
        return (rank[binding.confidence if binding else "none"], order.get(item.req_id, 0))

    best: dict[str, Site] = {}
    for item in found:
        key = canonical_json([item.unit, [list(kv) for kv in item.detail]])
        if key not in best or strength(item) < strength(best[key]):
            best[key] = item
    return list(best.values())


def plan_operator(
    op: Operator, ctx: Context, seeds: tuple[int, ...] = SEEDS, catalog_version: str = ""
) -> tuple[list[PlannedMutant], list[dict]]:
    """Plan up to three mutants for one (task, operator) cell.

    Returns the planned records (schema ``MutationResult`` without purity checks)
    and skip records explaining every candidate site that produced no mutant.
    """
    if op.family != ctx.family:
        return [], []
    sites = sorted(candidate_sites(op, ctx), key=lambda s: s.key())
    rng_for(ctx.task_id, op.name, "site-order").shuffle(sites)
    planned: list[PlannedMutant] = []
    skipped: list[dict] = []
    seen_steps: set[str] = set()
    pending = list(seeds[:MAX_SITES_PER_CELL])
    for where in sites:
        if not pending:
            break
        seed = pending[0]
        try:
            built = op.finalize(ctx, op.build(ctx, where, rng_for(ctx.task_id, op.name, seed)))
        except OperatorError as exc:
            skipped.append({"operator": op.name, "unit": where.unit, "reason": str(exc)})
            continue
        steps_key = canonical_json(built.steps)
        if steps_key in seen_steps:
            skipped.append({"operator": op.name, "unit": where.unit, "reason": "duplicate"})
            continue
        seen_steps.add(steps_key)
        pending.pop(0)
        judgement = op.judge(ctx, where, built)
        if judgement.label not in LABELS:
            raise OperatorError(f"{op.name} produced unknown label {judgement.label}")
        req_ids = judgement.req_ids or ((where.req_id,) if where.req_id else ())
        if judgement.label == VIOLATION and not req_ids:
            raise OperatorError(f"{op.name}: a violation label needs a requirement")
        recipe = {
            "recipe_version": RECIPE_VERSION,
            "catalog_version": catalog_version,
            "seed": seed,
            "input_sha256": ctx.input_sha256,
            "save": "gui_dispatch_save" if op.family in OFFICE_FAMILIES else "python_write",
            "params": {
                "site": {"unit": where.unit, "req_id": where.req_id, "detail": where.info},
                "binding": ctx.bindings[where.req_id].as_dict() if where.req_id else None,
                "steps": built.steps,
                "expectation": built.expectation.as_dict(),
                "facts": built.facts,
            },
        }
        record = {
            "mutant_id": make_mutant_id(ctx.task_id, op.name, recipe),
            "task_id": ctx.task_id,
            "operator": op.name,
            "family": op.family,
            "label": judgement.label,
            "witness": {"req_ids": list(req_ids), "argument": judgement.argument},
            "purity_checks": [],
            "recipe": recipe,
            "stratum": op.stratum,
            "schema_version": SCHEMA_VERSION,
        }
        if ctx.target_path_in_vm:
            record["target_path_in_vm"] = ctx.target_path_in_vm
        planned.append(PlannedMutant(record))
    return planned, skipped
