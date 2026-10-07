"""D9 audit protocol: provider-distinct model raters, blind, design-weighted.

Decision D9 (program/decisions.md) replaces the two blind human raters with
two model raters from different providers under the same blind protocol, and
sets aside a stratified sample for a human spot check by Kevin. Every result
names them as model raters and states that the human check is pending.

This module fixes, before any rating exists:

* the raters (``RATERS``) and the prompt (``RATER_PROMPT_V1``);
* the audit sample: disjoint strata in priority order ``alt_solution`` (all
  should_pass_alt_solution mutants, cap 150), ``disagreement`` (label class
  and checker verdict disagree, cap 200) and ``agreement`` (100), each item
  carrying its inclusion probability; plus sham items (10 percent, half
  LibreOffice-saved gold, half do-nothing) whose answer is known;
* the blind packet: instruction, initial files and the candidate only.
  Never gold, checker verdict, operator, family or label;
* the human spot-check sample for Kevin;
* how two ratings combine and how label error is estimated: consensus, else
  Kevin's adjudication, else counted as a label error; Hajek weights; the K3
  bound is the larger of the task-cluster bootstrap limit and an exact bound
  at the Kish effective size, with a minimum audited size
  (``stats.label_error_bound``).

Model calls are not made here; a runner sends ``packet`` objects and stores
the answers as ``Rating`` rows.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from harness.q2_mutation.schema import SHOULD_FAIL_LABELS, SHOULD_PASS_LABELS
from harness.q2_mutation.stats import (
    K3_THRESHOLD,
    AuditItem,
    Interval,
    LabelErrorBound,
    audit_label_error,
    cohens_kappa,
    hajek_rate,
    label_error_bound,
)

RATERS: tuple[Mapping[str, str], ...] = (
    {"rater_id": "model-rater-anthropic", "registry_id": "claude-opus-5", "provider": "anthropic"},
    {"rater_id": "model-rater-openai", "registry_id": "gpt-5.6-sol", "provider": "openai"},
)
ANSWERS = ("accept", "reject", "unsure")
STRATA = ("alt_solution", "disagreement", "agreement")
CAPS = {"alt_solution": 150, "disagreement": 200, "agreement": 100}
SHAM_FRACTION = 0.10
FORBIDDEN_PACKET_KEYS = frozenset(
    {"gold", "verdict", "score", "operator", "family", "label", "witness", "recipe", "checker"}
)

RATER_PROMPT_V1 = """\
You are checking whether a computer-use task was completed. You will see:
1. the task instruction given to the user's assistant,
2. the files the user started with (structure and rendering),
3. the end-state file(s) the assistant produced (structure, rendering, and a
   structural difference against the starting files).

You are not shown any reference answer or any automatic grade.

Question: would the user who gave this instruction accept the end-state file(s)
as a correct and complete result? Judge only what the instruction asks for and
what a reasonable user would expect to stay unchanged. Differences the
instruction does not constrain (for example an equivalent formula, a different
but valid way to reach the same visible result) are acceptable.

Answer with exactly one of: accept, reject, unsure. Then give one sentence of
reasons naming the specific cell, paragraph, slide object or setting involved.
"""


@dataclass(frozen=True)
class Candidate:
    """One scored mutant, as the audit sampler sees it (harness side)."""

    mutant_id: str
    task_id: str
    label: str
    verdict: str


@dataclass(frozen=True)
class Sampled:
    mutant_id: str
    task_id: str
    stratum: str
    inclusion_probability: float
    sham: str | None = None  # "gold" | "do_nothing" for sham items


def stratum_of(candidate: Candidate) -> str | None:
    """Disjoint audit stratum; None for errors and ambiguous labels."""
    if candidate.verdict == "error" or candidate.label == "ambiguous":
        return None
    if candidate.label == "should_pass_alt_solution":
        return "alt_solution"
    passes = candidate.verdict == "pass"
    if (candidate.label in SHOULD_PASS_LABELS and not passes) or (
        candidate.label in SHOULD_FAIL_LABELS and passes
    ):
        return "disagreement"
    return "agreement"


def draw_audit_sample(
    candidates: Sequence[Candidate],
    *,
    seed: int = 42,
    caps: Mapping[str, int] = CAPS,
    sham_tasks: Sequence[str] = (),
) -> list[Sampled]:
    """Stratified sample with known inclusion probabilities, plus sham items."""
    by_stratum: dict[str, list[Candidate]] = {name: [] for name in STRATA}
    for candidate in sorted(candidates, key=lambda c: c.mutant_id):
        name = stratum_of(candidate)
        if name is not None:
            by_stratum[name].append(candidate)
    rng = random.Random(seed)
    sample: list[Sampled] = []
    for name in STRATA:
        pool = by_stratum[name]
        cap = caps[name]
        chosen = pool if len(pool) <= cap else rng.sample(pool, cap)
        probability = 1.0 if len(pool) <= cap else cap / len(pool)
        sample += [
            Sampled(c.mutant_id, c.task_id, name, probability)
            for c in sorted(chosen, key=lambda c: c.mutant_id)
        ]
    n_sham = math.ceil(SHAM_FRACTION * len(sample))
    tasks = sorted(set(sham_tasks) or {item.task_id for item in sample})
    for index in range(min(n_sham, 2 * len(tasks))):
        task = tasks[(index // 2) % len(tasks)] if len(tasks) else ""
        kind = "gold" if index % 2 == 0 else "do_nothing"
        sample.append(Sampled(f"{task}__sham_{kind}", task, "sham", 1.0, sham=kind))
    return sample


def opaque_item_id(mutant_id: str, seed: int) -> str:
    return hashlib.sha256(f"q2-audit:{seed}:{mutant_id}".encode()).hexdigest()[:16]


def make_packet(
    sampled: Sampled,
    *,
    instruction: str,
    initial_files: Sequence[Mapping[str, str]],
    candidate_artifacts: Mapping[str, Any],
    seed: int,
) -> dict[str, Any]:
    """The only content a rater sees for one item."""
    packet = {
        "item_id": opaque_item_id(sampled.mutant_id, seed),
        "prompt_version": "RATER_PROMPT_V1",
        "instruction": instruction,
        "initial_files": [dict(item) for item in initial_files],
        "candidate": dict(candidate_artifacts),
    }
    leaked = _leaked_keys(packet)
    if leaked:
        raise ValueError(f"packet leaks checker or operator information: {leaked}")
    return packet


def _leaked_keys(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            if str(key).lower() in FORBIDDEN_PACKET_KEYS:
                hits.append(f"{path}.{key}")
            hits += _leaked_keys(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            hits += _leaked_keys(value, f"{path}[{index}]")
    return hits


def rater_order(item_ids: Sequence[str], rater_id: str, seed: int = 42) -> list[str]:
    """Each rater sees the items in its own seeded random order."""
    order = sorted(item_ids)
    random.Random(f"{seed}:{rater_id}").shuffle(order)
    return order


def human_spot_check(sample: Sequence[Sampled], *, seed: int = 42) -> list[Sampled]:
    """Kevin's stratified spot check: max(5, 10%) per stratum plus 5 shams."""
    rng = random.Random(f"{seed}:human")
    chosen: list[Sampled] = []
    for name in (*STRATA, "sham"):
        pool = sorted((item for item in sample if item.stratum == name), key=lambda s: s.mutant_id)
        k = 5 if name == "sham" else max(5, math.ceil(0.10 * len(pool)))
        chosen += pool if len(pool) <= k else rng.sample(pool, k)
    return chosen


def consensus(first: str, second: str) -> str:
    """Two model ratings -> accept / reject / unresolved."""
    for answer in (first, second):
        if answer not in ANSWERS:
            raise ValueError(f"unknown answer {answer!r}")
    if first == second and first in ("accept", "reject"):
        return first
    return "unresolved"


def label_is_wrong(label: str, decision: str) -> bool | None:
    """Whether the audit contradicts the a-priori label; None if unresolved."""
    if decision == "unresolved":
        return None
    if label in SHOULD_PASS_LABELS:
        return decision == "reject"
    if label in SHOULD_FAIL_LABELS:
        return decision == "accept"
    raise ValueError(f"label {label!r} is not auditable")


@dataclass(frozen=True)
class AuditSummary:
    """Audit result. ``label_error`` and ``k3`` are the K3/K4 statistics.

    An item is resolved by rater consensus, else by Kevin's adjudication; an
    item still unresolved counts as a label error (the spec author and one
    rater share a provider, so dropping the other rater's dissents would bias
    label error down). ``label_error_resolved_only`` (unresolved items
    dropped) is a sensitivity estimate, and ``per_rater`` shows each rater's
    disagreement with the labels on its own.
    """

    kappa: float
    n_items: int
    n_unresolved: int
    n_adjudicated: int
    sham_accuracy: Mapping[str, float]
    label_error: Mapping[str, Interval]
    k3: Mapping[str, LabelErrorBound]
    k3_fires: Mapping[str, bool]
    kappa_fires: bool
    label_error_resolved_only: Mapping[str, Interval]
    label_error_unresolved_as_wrong: Mapping[str, float]
    per_rater: Mapping[str, Mapping[str, Mapping[str, float]]]


KAPPA_MIN = 0.6


def summarize(
    sample: Sequence[Sampled],
    labels: Mapping[str, str],
    ratings: Mapping[str, tuple[str, str]],
    *,
    adjudicated: Mapping[str, str] | None = None,
    n_boot: int = 10_000,
    seed: int = 42,
) -> AuditSummary:
    """Combine two raters' answers into kappa, sham accuracy and label error.

    ``adjudicated`` maps an item whose raters did not agree to Kevin's answer
    (accept or reject).
    """
    adjudicated = adjudicated or {}
    real = [s for s in sample if s.sham is None and s.mutant_id in ratings]
    shams = [s for s in sample if s.sham is not None and s.mutant_id in ratings]
    kappa = cohens_kappa(
        [ratings[s.mutant_id][0] for s in real], [ratings[s.mutant_id][1] for s in real]
    )
    expected = {"gold": "accept", "do_nothing": "reject"}
    sham_accuracy = {}
    for index, rater in enumerate(RATERS):
        if shams:
            hits = sum(ratings[s.mutant_id][index] == expected[str(s.sham)] for s in shams)
            sham_accuracy[rater["rater_id"]] = hits / len(shams)
    primary: dict[str, list[AuditItem]] = {}
    resolved_only: dict[str, list[AuditItem]] = {}
    pessimistic: dict[str, list[AuditItem]] = {}
    per_rater_items: dict[str, dict[str, list[AuditItem]]] = {}
    per_rater_unsure: dict[str, dict[str, list[AuditItem]]] = {}
    unresolved = 0
    n_adjudicated = 0

    def item(source: Sampled, wrong: bool) -> AuditItem:
        return AuditItem(
            source.mutant_id, source.task_id, source.stratum, source.inclusion_probability, wrong
        )

    for source in real:
        label = labels[source.mutant_id]
        group = "should_pass" if label in SHOULD_PASS_LABELS else "should_fail"
        decision = consensus(*ratings[source.mutant_id])
        wrong = label_is_wrong(label, decision)
        if wrong is None:
            unresolved += 1
        pessimistic.setdefault(group, []).append(item(source, True if wrong is None else wrong))
        if wrong is not None:
            resolved_only.setdefault(group, []).append(item(source, wrong))
        else:
            answer = adjudicated.get(source.mutant_id)
            if answer is not None:
                if answer not in ("accept", "reject"):
                    raise ValueError(f"adjudication {answer!r} is not accept or reject")
                n_adjudicated += 1
                wrong = label_is_wrong(label, answer)
        primary.setdefault(group, []).append(item(source, True if wrong is None else wrong))
        for index, rater in enumerate(RATERS):
            answer = ratings[source.mutant_id][index]
            rid = rater["rater_id"]
            single = label_is_wrong(label, answer if answer != "unsure" else "unresolved")
            per_rater_items.setdefault(rid, {}).setdefault(group, []).append(
                item(source, bool(single))
            )
            per_rater_unsure.setdefault(rid, {}).setdefault(group, []).append(
                item(source, answer == "unsure")
            )

    k3 = {
        group: label_error_bound(items, n_boot=n_boot, seed=seed)
        for group, items in primary.items()
    }
    return AuditSummary(
        kappa=kappa,
        n_items=len(real),
        n_unresolved=unresolved,
        n_adjudicated=n_adjudicated,
        sham_accuracy=sham_accuracy,
        label_error={
            group: audit_label_error(items, n_boot=n_boot, seed=seed)
            for group, items in primary.items()
        },
        k3=k3,
        k3_fires={
            group: (not bound.sufficient) or bound.upper > K3_THRESHOLD
            for group, bound in k3.items()
        },
        kappa_fires=kappa < KAPPA_MIN,
        label_error_resolved_only={
            group: audit_label_error(items, n_boot=n_boot, seed=seed)
            for group, items in resolved_only.items()
        },
        label_error_unresolved_as_wrong={
            group: hajek_rate(items) for group, items in pessimistic.items()
        },
        per_rater={
            rid: {
                group: {
                    "contradicts_label": hajek_rate(items),
                    "unsure": hajek_rate(per_rater_unsure[rid][group]),
                }
                for group, items in groups.items()
            }
            for rid, groups in per_rater_items.items()
        },
    )
