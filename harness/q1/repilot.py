"""Q1 Stage 0 re-pilot (decision D31): the reference store's cost, paired with the inline path.

Pure Python (no torch). D31 admits Stage 0 only if, after the engineering pass
that computes references once per problem and draw (``refstore``), the high
projection of ``q1-stage0-trim/2`` fits 8 GPU-h, and it sets that projection by
a re-pilot of at most 0.5 GPU-h on S1-cal and other non-evaluation kernels only
(D28: no further exposure of evaluation units). This module is that re-pilot's
registered rule ``q1-repilot/1``, written before its job runs:

- **Problems.** S1 calibration-half problems (``substrates/split.py``, seed 42)
  with no S2 substrate (so no evaluation unit of any tier lives on them), not
  excluded, in the Stage 0 planning corpus's admitted S1-cal set, with native
  inputs below the trimming rule's small class (0.6 GB, where every in-scope
  evaluation substrate lies: 0.008-0.537 GB). Five strata follow the in-scope
  evaluation set (45 level-2 and 24 level-1 substrates; the level-1 ones are
  mostly matrix products): level 1 below 0.6 GB (2 problems), and level 2 in
  ``[0, 0.05)`` (2), ``[0.05, 0.2)`` (1), ``[0.2, 0.4)`` (2) and ``[0.4, 0.6)``
  GB (1). In each stratum candidates are ordered by
  ``sha256("q1-repilot/1/" + problem_id)`` and the first that build (mock-H100
  codegen and conversion on the CPU) are taken; a candidate that does not build
  is replaced by the next and listed. (A CPU trial build of an earlier draft of
  this rule, size bins without levels, picked eight level-2 problems; no GPU
  item had run. The level strata were added before any GPU job.)
- **Kernels.** Per problem: the S1-cal substrate, its reference-identity
  control and one mutant (the first of the parent's CPU-distinct pool by
  ``sha256("q1-repilot/1/mutant/" + mutant_id)``; no compile filter, since S1-cal
  specializations were never recorded, so a mutant that fails to compile on the
  GPU is reported, and both arms of it are cheap alike).
- **Arms.** Every kernel gets all 15 scoring items twice at replicate 42: the
  inline path (no store) and the store path (``refschedule``: one reference
  item per problem and channel, consumers read its entry). The store twin's
  kernel id is the kernel id plus ``.store``. Twins are adjacent in the queue,
  so they run under the same contention; reference items go just before their
  group's first consumer. Execution is Stage 0's (``trim.TRIM_RULE``): 12 units
  per GPU, one unit per item below 0.6 GB, size-scaled watchdog limits.
- **Order.** Problems by stratum (as listed), then by their order key; a time
  box therefore cuts the largest level-2 problems first and every completed
  problem has both arms.

The paired per-gate ratio (store over inline) and the reference items' cost,
both as functions of native input size, feed the Stage 0 projection
(``cost_card.project_trimmed(store=...)``); the twins' rows are compared for a
GPU check of the equivalence the CPU tests prove.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from harness.q1 import pilot, trim

RULE = "q1-repilot/1"
#: Strata: (name, KernelBench level, native input bytes [low, high), problems).
STRATA: tuple[tuple[str, int, int, int, int], ...] = (
    ("L1-below-0.6GB", 1, 0, 600_000_000, 2),
    ("L2-0-0.05GB", 2, 0, 50_000_000, 2),
    ("L2-0.05-0.2GB", 2, 50_000_000, 200_000_000, 1),
    ("L2-0.2-0.4GB", 2, 200_000_000, 400_000_000, 2),
    ("L2-0.4-0.6GB", 2, 400_000_000, 600_000_000, 1),
)
STORE_SUFFIX = ".store"
REPLICATE = 42
SCORING_GATES = trim.SCORING_GATES


def order_key(problem_id: str) -> str:
    return hashlib.sha256(f"{RULE}/{problem_id}".encode()).hexdigest()


def mutant_key(mutant_id: str) -> str:
    return hashlib.sha256(f"{RULE}/mutant/{mutant_id}".encode()).hexdigest()


def candidates(
    calibration_problems: Iterable[str],
    *,
    s2_problems: Iterable[str],
    eligible: Iterable[str],
    excluded: Iterable[str] = (),
    size_of: Any = pilot.native_input_bytes,
) -> dict[str, list[str]]:
    """Per stratum, the eligible problems in rule order."""
    from harness.q1.schema import parse_problem_id

    ok = set(eligible) - set(excluded) - set(s2_problems)
    out: dict[str, list[str]] = {}
    for name, level, low, high, _count in STRATA:
        members = {
            p
            for p in calibration_problems
            if p in ok and parse_problem_id(p)[0] == level and low <= (size_of(p) or 0) < high
        }
        out[name] = sorted(members, key=order_key)
    return out


def pick(
    ordered: Mapping[str, Sequence[str]],
    builds: Any,
    counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """The first ``counts[stratum]`` problems per stratum (default: the rule's) for
    which ``builds(problem_id)`` is true; the others tried are listed as replaced."""
    wanted = dict(counts) if counts is not None else {s[0]: s[4] for s in STRATA}
    chosen: list[str] = []
    record = []
    for name, members in ordered.items():
        taken, replaced = [], []
        for problem_id in members:
            if len(taken) == wanted[name]:
                break
            (taken if builds(problem_id) else replaced).append(problem_id)
        chosen += taken
        record.append({"stratum": name, "chosen": taken, "replaced_not_built": replaced})
    return {"rule": RULE, "problems": chosen, "strata": record}


def first_mutant(mutant_ids: Iterable[str]) -> str | None:
    ordered = sorted(mutant_ids, key=mutant_key)
    return ordered[0] if ordered else None


def twin(kernel_id: str) -> str:
    return kernel_id + STORE_SUFFIX


def arm_of(kernel_id: str) -> tuple[str, str]:
    """(kernel id without the arm suffix, ``inline`` or ``store``)."""
    if kernel_id.endswith(STORE_SUFFIX):
        return kernel_id[: -len(STORE_SUFFIX)], "store"
    return kernel_id, "inline"


def items(
    kernels: Sequence[Mapping[str, Any]], *, store_root: str, journal: str
) -> list[dict[str, Any]]:
    """Run-ordered ``WorkItem`` field dicts for both arms (see the module docstring).

    ``kernels``: dicts with ``kernel_id``, ``kernel_path`` and ``problem_id``, in
    problem order."""
    from harness.q1 import refschedule

    rule = trim.TRIM_RULE
    capacity = int(rule["slot_capacity"])
    inline: list[dict[str, Any]] = []
    store: list[dict[str, Any]] = []
    for kernel in kernels:
        problem_id = kernel["problem_id"]
        units = trim.concurrency_units(problem_id, rule)
        limits = pilot.watchdog_limits(problem_id)
        for gate in SCORING_GATES:
            base = {
                "kernel_path": kernel["kernel_path"],
                "problem_id": problem_id,
                "gate": gate,
                "seed": REPLICATE,
                "problem_source_path": None,
                "options": {},
                "exclusive": units >= capacity,
                "timeouts": dict(limits),
                "units": units,
                "requires": [],
                "journal": None,
            }
            inline.append({**base, "kernel_id": kernel["kernel_id"]})
            store.append({**base, "kernel_id": twin(kernel["kernel_id"])})
    scheduled = refschedule.with_references(store, root=store_root)
    twins = {(i["kernel_id"], i["gate"]): i for i in inline}
    out: list[dict[str, Any]] = []
    for entry in scheduled:
        if entry.get("journal"):
            out.append({**entry, "journal": journal})
            continue
        base_id, _ = arm_of(entry["kernel_id"])
        out.append(twins[(base_id, entry["gate"])])
        out.append(entry)
    return out


#: Row fields that measure time or name the run or process (twins differ in them).
VOLATILE_TOP = ("gpu_seconds", "wall_seconds", "run_id", "kernel_id", "code_sha256")
VOLATILE_DETAILS = (
    "item_wall_seconds",
    "item_started_at",
    "item_ended_at",
    "item_key",
    "slot",
    "log_tail",
)
_TEMPFILE = re.compile(r"/tmp/tmp[A-Za-z0-9_]+\.py")
_ADDRESS = re.compile(r" at 0x[0-9a-f]+")


def normalized_row(row: Mapping[str, Any]) -> str:
    """A verdict row without its timing, run, process and arm identity (twins compare)."""
    body = {k: v for k, v in row.items() if k not in VOLATILE_TOP}
    body["details"] = {k: v for k, v in row["details"].items() if k not in VOLATILE_DETAILS}
    text = json.dumps(body, sort_keys=True)
    return _ADDRESS.sub(" at <address>", _TEMPFILE.sub("<tempfile>", text))


def compare_twins(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Inline versus store rows of the same kernel, gate, config and policy."""
    sides: dict[tuple[str, str, str, str, int], dict[str, list[Mapping[str, Any]]]] = {}
    for row in rows:
        base, arm = arm_of(row["kernel_id"])
        key = (base, row["gate"], row["config_id"], row["tf32_policy"], int(row.get("seed", 42)))
        sides.setdefault(key, {"inline": [], "store": []})[arm].append(row)
    both = {k: v for k, v in sides.items() if v["inline"] and v["store"]}
    identical = verdict_equal = 0
    differing: list[dict[str, Any]] = []
    for key, side in sorted(both.items()):
        left = sorted(normalized_row(r) for r in side["inline"])
        right = sorted(normalized_row(r) for r in side["store"])
        verdicts = sorted(r["verdict"] for r in side["inline"]) == sorted(
            r["verdict"] for r in side["store"]
        )
        identical += left == right
        verdict_equal += verdicts
        if left != right:
            fields = sorted(
                {
                    k
                    for a, b in zip(left, right, strict=False)
                    for k in _diff_paths(json.loads(a), json.loads(b))
                }
            )
            differing.append({"key": list(key), "verdicts_equal": verdicts, "fields": fields[:20]})
    return {
        "rows_compared": len(both),
        "rows_identical": identical,
        "verdicts_identical": verdict_equal,
        "only_one_arm": len(sides) - len(both),
        "differing": differing,
    }


def _diff_paths(a: Any, b: Any, prefix: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [
            path
            for key in sorted(set(a) | set(b))
            for path in _diff_paths(a.get(key), b.get(key), f"{prefix}.{key}")
        ]
    return [] if a == b else [prefix]


__all__ = [
    "REPLICATE",
    "RULE",
    "SCORING_GATES",
    "STORE_SUFFIX",
    "STRATA",
    "arm_of",
    "candidates",
    "compare_twins",
    "normalized_row",
    "first_mutant",
    "items",
    "mutant_key",
    "order_key",
    "pick",
    "twin",
]
