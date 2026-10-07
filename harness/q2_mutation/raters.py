"""D9/D23 audit protocol: two model raters, blind, design-weighted.

Decision D9 (program/decisions.md) replaces the two blind human raters with
two model raters under the same blind protocol, and sets aside a stratified
sample for a human spot check by Kevin. Decision D23 fixes the lineup: a
Claude model through the Anthropic API and a self-hosted open-weight
vision-language model (Qwen3.5-9B, a different developer and training
lineage). The spec author is also a Claude model, so the open-weight rater is
the independent one: each rater's answers are reported separately, and an
item on which the raters do not agree is adjudicated by Kevin (blind, same
packet) or counted as a label error, never dropped. Every result names them as
model raters and states that the human check is pending.

This module fixes, before any rating exists:

* the raters (``RATERS``) and the prompt (``RATER_PROMPT_V1``);
* the candidate pool (``audit_candidates``): mutants evaluable under the
  primary venv outside probe-touched cells, the population P2-P5 are computed
  on;
* the audit sample: disjoint strata in priority order ``alt_solution`` (all
  should_pass_alt_solution mutants, cap 150), ``disagreement`` (label class
  and checker verdict disagree, cap 200) and ``agreement`` (100), each item
  carrying its inclusion probability; plus sham items (10 percent, half
  LibreOffice-saved gold, half do-nothing, at most two per task) whose answer
  is known, and every P1 gold fixed-point flip (``p1_flip``);
* the answer rule (``parse_first_token``): the first word of the reply, and
  ``unsure`` for a refusal, an empty or unparseable reply, a timeout or a
  request the provider rejected (``answer_for``);
* the blind packet: instruction, initial files and the candidate only.
  Never gold, checker verdict, operator, family or label;
* the human spot-check sample for Kevin;
* how two ratings combine and how label error is estimated: consensus, else
  Kevin's adjudication, else counted as a label error; Hajek weights; the K3
  bound is the larger of the task-cluster bootstrap limit and an exact bound
  at the Kish effective size, with a minimum audited size
  (``stats.label_error_bound``).

K3 and K4 are computed on the two label classes that enter the primary metrics
without an audit gate: ``should_pass_equiv`` (P2, P5) and
``should_fail_violation`` (P3, P5). Alternative-solution and extra-change
mutants enter P2 and P4 only through the audit's own decision, so their
acceptance and rejection rates are reported under S6 (``by_label_class``) and
never fire K3.

Model calls are made by ``rater_runner``; this module only defines the sample,
the packet, the answer rule and the summary.
"""

from __future__ import annotations

import hashlib
import math
import random
import re
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

# Decision D23. The Anthropic model id is the one the API names (recorded by
# ``rater_runner models`` and in every response); the open-weight model is
# pinned by its Hugging Face revision and the receipt the lane verifies.
RATERS: tuple[Mapping[str, str], ...] = (
    {
        "rater_id": "model-rater-anthropic",
        "provider": "anthropic",
        "registry_id": "claude-opus-5-5",
        "role": "same provider as the spec author",
    },
    {
        "rater_id": "model-rater-open-weight",
        "provider": "qwen-open-weight-self-hosted",
        "registry_id": "qwen3.5-9b",
        "repo_id": "Qwen/Qwen3.5-9B",
        "revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
        "receipt_sha256": "0a9e052d561b017c505adf5a1c6fcdc048522660a0db134486b84edbf3de5cb3",
        "role": "independent",
    },
)
RATER_IDS = tuple(r["rater_id"] for r in RATERS)
ANSWERS = ("accept", "reject", "unsure")
STRATA = ("alt_solution", "disagreement", "agreement")
EXTRA_STRATA = ("sham", "p1_flip")
CAPS = {"alt_solution": 150, "disagreement": 200, "agreement": 100}
SHAM_FRACTION = 0.10
# Label classes whose label error is K3/K4: the classes that enter P2-P5
# without an audit gate.
K3_GROUPS = ("should_pass_equiv", "should_fail_violation")
# Label classes whose entry into a metric is decided by the audit itself.
GATED_LABELS = {"should_pass_alt_solution": "accept", "should_fail_extra_change": "reject"}
LABEL_CLASSES = (
    "should_pass_equiv",
    "should_pass_alt_solution",
    "should_fail_violation",
    "should_fail_extra_change",
)
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


def audit_candidates(
    outcomes: Sequence[Mapping[str, Any]], primary: str = "lock"
) -> list[Candidate]:
    """The audit's candidate pool: evaluable mutants outside probe-touched cells.

    This is the population P2-P5 are computed on (``campaign.build_report``):
    status ``evaluable`` under the primary venv (which already excludes
    ambiguous labels, errors, nondeterministic scorings, null_not_pass and the
    infrastructure exclusions) and ``probe_touched`` false (a probe cell or a
    probe-informed operator).
    """
    return [
        Candidate(
            str(r["mutant_id"]), str(r["task_id"]), str(r["label"]), str(r[f"{primary}_verdict"])
        )
        for r in outcomes
        if r.get(f"{primary}_status") == "evaluable" and not r.get("probe_touched")
    ]


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


def sham_id(task_id: str, kind: str) -> str:
    return f"{task_id}__sham_{kind}"


def p1_flip_id(task_id: str) -> str:
    return f"{task_id}__p1_flip"


def draw_audit_sample(
    candidates: Sequence[Candidate],
    *,
    seed: int = 42,
    caps: Mapping[str, int] = CAPS,
    sham_tasks: Sequence[str] = (),
    p1_flip_tasks: Sequence[str] = (),
) -> list[Sampled]:
    """Stratified sample with known inclusion probabilities, plus shams and P1 flips."""
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
        task = tasks[(index // 2) % len(tasks)]
        kind = "gold" if index % 2 == 0 else "do_nothing"
        sample.append(Sampled(sham_id(task, kind), task, "sham", 1.0, sham=kind))
    for task in sorted(set(p1_flip_tasks)):
        sample.append(Sampled(p1_flip_id(task), task, "p1_flip", 1.0))
    return sample


def opaque_item_id(mutant_id: str, seed: int) -> str:
    return hashlib.sha256(f"q2-audit:{seed}:{mutant_id}".encode()).hexdigest()[:16]


def make_packet(
    sampled: Sampled,
    *,
    instruction: str,
    initial_files: Sequence[Mapping[str, Any]],
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


# --- answers ------------------------------------------------------------------

# Characters a reply may open with before its first word (markdown emphasis,
# quotes, list markers, brackets); everything else must be the answer word.
_LEADING = re.compile(r"^[\s*_`\"'#>(\[\-:.]*")
_FIRST_WORD = re.compile(r"[A-Za-z]+")
# Call outcomes that never carry an answer; each maps to ``unsure``.
NON_ANSWER_OUTCOMES = (
    "refusal",
    "empty",
    "unparseable",
    "timeout",
    "transport_exhausted",
    "request_rejected",
    "unrated",
)


def parse_first_token(text: str | None) -> tuple[str, str]:
    """(answer, parse status) under the registered first-token rule.

    The answer is the first word of the reply (letters only, case-folded)
    after leading whitespace, markdown emphasis, quotes, list markers and
    brackets. It counts only if it is ``accept``, ``reject`` or ``unsure``;
    otherwise the reply is ``unparseable`` and the answer is ``unsure``. An
    empty reply is ``empty`` and ``unsure``. Nothing later in the reply is
    read.
    """
    if text is None or not text.strip():
        return "unsure", "empty"
    match = _FIRST_WORD.match(_LEADING.sub("", text, count=1))
    if match is None:
        return "unsure", "unparseable"
    word = match.group(0).lower()
    if word in ANSWERS:
        return word, "ok"
    return "unsure", "unparseable"


def answer_for(outcome: str, text: str | None) -> tuple[str, str]:
    """(answer, status) for one call: ``ok`` replies are parsed, the rest are ``unsure``."""
    if outcome == "ok":
        return parse_first_token(text)
    if outcome not in NON_ANSWER_OUTCOMES:
        raise ValueError(f"unknown call outcome {outcome!r}")
    return "unsure", outcome


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


def final_decision(ratings: tuple[str, str], adjudicated: str | None) -> str:
    """Consensus, else Kevin's blind adjudication, else ``unresolved``."""
    decision = consensus(*ratings)
    if decision != "unresolved" or adjudicated is None:
        return decision
    if adjudicated not in ("accept", "reject"):
        raise ValueError(f"adjudication {adjudicated!r} is not accept or reject")
    return adjudicated


@dataclass(frozen=True)
class AuditSummary:
    """Audit result. ``label_error`` and ``k3`` are the K3/K4 statistics.

    Groups are the label classes in ``K3_GROUPS``. An item is resolved by rater
    consensus, else by Kevin's adjudication; an item still unresolved counts
    as a label error (the spec author and one rater share a provider, so
    dropping the other rater's dissents would bias label error down).
    ``label_error_resolved_only`` (unresolved items dropped) is a sensitivity
    estimate, ``per_rater`` shows each rater's disagreement with the labels on
    its own, and ``by_label_class`` is S6 for every label class, including the
    audit-gated alternative-solution and extra-change classes. ``decisions``
    holds the final decision of every real item (mutant id or P1 flip id);
    the analysis uses it to gate P2 (alternative solutions) and P4.
    """

    kappa: float | None
    kappa_fires: bool
    n_items: int
    n_unresolved: int
    n_adjudicated: int
    sham_accuracy: Mapping[str, float]
    label_error: Mapping[str, Interval]
    k3: Mapping[str, LabelErrorBound | None]
    k3_fires: Mapping[str, bool]
    k4_fires: bool
    label_error_resolved_only: Mapping[str, Interval]
    label_error_unresolved_as_wrong: Mapping[str, float]
    per_rater: Mapping[str, Mapping[str, Mapping[str, float]]]
    by_label_class: Mapping[str, Mapping[str, Any]]
    p1_flips: Mapping[str, str]
    decisions: Mapping[str, str]


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
    """Combine two raters' answers into kappa, sham accuracy, S6 and label error.

    ``ratings`` maps an item (mutant id, sham id or P1 flip id) to the two
    raters' answers in ``RATERS`` order; an item a rater never answered is
    ``unsure`` for that rater (``answer_for('unrated', None)``) and must be
    passed as such. ``adjudicated`` maps an item whose raters did not agree to
    Kevin's answer (accept or reject).
    """
    adjudicated = adjudicated or {}
    real = [s for s in sample if s.sham is None and s.mutant_id in ratings]
    shams = [s for s in sample if s.sham is not None and s.mutant_id in ratings]
    kappa = (
        cohens_kappa(
            [ratings[s.mutant_id][0] for s in real], [ratings[s.mutant_id][1] for s in real]
        )
        if real
        else None
    )
    expected = {"gold": "accept", "do_nothing": "reject"}
    sham_accuracy = {}
    for index, rater in enumerate(RATERS):
        if shams:
            hits = sum(ratings[s.mutant_id][index] == expected[str(s.sham)] for s in shams)
            sham_accuracy[rater["rater_id"]] = hits / len(shams)
    primary: dict[str, list[AuditItem]] = {group: [] for group in K3_GROUPS}
    resolved_only: dict[str, list[AuditItem]] = {}
    pessimistic: dict[str, list[AuditItem]] = {}
    per_rater_items: dict[str, dict[str, list[AuditItem]]] = {}
    per_rater_unsure: dict[str, dict[str, list[AuditItem]]] = {}
    classes: dict[str, list[tuple[Sampled, str]]] = {name: [] for name in LABEL_CLASSES}
    decisions: dict[str, str] = {}
    p1_flips: dict[str, str] = {}
    unresolved = 0
    n_adjudicated = 0

    def item(source: Sampled, wrong: bool) -> AuditItem:
        return AuditItem(
            source.mutant_id, source.task_id, source.stratum, source.inclusion_probability, wrong
        )

    for source in real:
        pair = ratings[source.mutant_id]
        decision = final_decision(pair, adjudicated.get(source.mutant_id))
        if consensus(*pair) == "unresolved":
            unresolved += 1
            if decision != "unresolved":
                n_adjudicated += 1
        decisions[source.mutant_id] = decision
        if source.stratum == "p1_flip":
            p1_flips[source.mutant_id] = decision
            continue
        label = labels[source.mutant_id]
        classes[label].append((source, decision))
        if label not in K3_GROUPS:
            continue
        consensus_wrong = label_is_wrong(label, consensus(*pair))
        pessimistic.setdefault(label, []).append(
            item(source, True if consensus_wrong is None else consensus_wrong)
        )
        if consensus_wrong is not None:
            resolved_only.setdefault(label, []).append(item(source, consensus_wrong))
        wrong = label_is_wrong(label, decision)
        primary[label].append(item(source, True if wrong is None else wrong))
        for index, rater in enumerate(RATERS):
            answer = pair[index]
            rid = rater["rater_id"]
            single = label_is_wrong(label, answer if answer != "unsure" else "unresolved")
            per_rater_items.setdefault(rid, {}).setdefault(label, []).append(
                item(source, bool(single))
            )
            per_rater_unsure.setdefault(rid, {}).setdefault(label, []).append(
                item(source, answer == "unsure")
            )

    k3: dict[str, LabelErrorBound | None] = {}
    for group in K3_GROUPS:
        items = primary[group]
        k3[group] = label_error_bound(items, n_boot=n_boot, seed=seed) if items else None
    kappa_fires = kappa is None or kappa < KAPPA_MIN
    k3_fires = {
        group: kappa_fires or bound is None or (not bound.sufficient) or bound.upper > K3_THRESHOLD
        for group, bound in k3.items()
    }
    label_error = {
        group: audit_label_error(items, n_boot=n_boot, seed=seed)
        for group, items in primary.items()
        if items
    }
    k4_fires = all(
        group in label_error and label_error[group].estimate > K3_THRESHOLD for group in K3_GROUPS
    )
    return AuditSummary(
        kappa=kappa,
        kappa_fires=kappa_fires,
        n_items=len(real),
        n_unresolved=unresolved,
        n_adjudicated=n_adjudicated,
        sham_accuracy=sham_accuracy,
        label_error=label_error,
        k3=k3,
        k3_fires=k3_fires,
        k4_fires=k4_fires,
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
        by_label_class={name: _class_summary(name, rows) for name, rows in classes.items()},
        p1_flips=p1_flips,
        decisions=decisions,
    )


def _class_summary(label: str, rows: Sequence[tuple[Sampled, str]]) -> dict[str, Any]:
    """S6 for one label class: decisions and the Hajek share agreeing with the label."""
    counts = {
        name: sum(1 for _, d in rows if d == name) for name in ("accept", "reject", "unresolved")
    }
    out: dict[str, Any] = {"n": len(rows), **counts}
    if not rows:
        return out
    weights = [1.0 / s.inclusion_probability for s, _ in rows]
    total = sum(weights)
    pairs = list(zip(weights, rows, strict=True))
    agree = sum(w for w, (_, d) in pairs if label_is_wrong(label, d) is False)
    open_ = sum(w for w, (_, d) in pairs if d == "unresolved")
    out["agrees_with_label"] = agree / total
    out["unresolved_share"] = open_ / total
    if label in GATED_LABELS:
        gate = GATED_LABELS[label]
        out["gate"] = gate
        out["gate_share"] = sum(w for w, (_, d) in pairs if d == gate) / total
    return out
