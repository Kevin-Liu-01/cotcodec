"""Scheduling of reference items (decision D31): which consumer items share a
reference entry, where the reference items go in the run order, and what each
consumer waits for.

Pure Python (no torch). A driver passes its run-ordered ``WorkItem`` field
dicts through :func:`with_references`; it never changes which kernels, gates,
replicates or buckets are scored (the plan and its ``plan_sha256`` are
untouched), only adds reference items and execution facts to consumers. The
rule:

- a **group** is (problem, problem source, replicate, channel, the item
  options that change the entry); its consumers are the items of the gates in
  ``refstore.CONSUMERS[channel]``;
- a group gets one reference item when at least ``min_kernels`` distinct
  kernels consume it (default 2); a smaller group computes inline, since a
  reference item costs a process and a store write;
- the reference item is placed just before the group's first consumer, takes
  that consumer's concurrency units and exclusivity, and its compile-phase
  limit is the consumer's compile plus correctness limits (it never loads a
  candidate, so it never enters the ``correctness`` phase);
- every consumer gets ``requires`` (the runner starts it only when the
  reference item is no longer queued or running) and the store root in
  ``options.reference_store``. A consumer whose reference item failed, was cut
  or never ran finds no usable entry and computes inline.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from harness.q1.journal import item_key
from harness.q1.refstore import (
    CHANNEL_GATE,
    CHANNEL_OF,
    OPTION,
    REFERENCE_JOURNAL,
    reference_kernel_id,
)

#: Item options that change a channel's entry (and so split groups).
ENTRY_OPTIONS = ("manifest_path", "num_trials")
DEFAULT_MIN_KERNELS = 2


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def group_of(item: Mapping[str, Any]) -> tuple[Any, ...] | None:
    channel = CHANNEL_OF.get(item["gate"])
    if channel is None:
        return None
    options = dict(item.get("options") or {})
    relevant = {k: v for k, v in options.items() if k in ENTRY_OPTIONS}
    return (
        item["problem_id"],
        item.get("problem_source_path"),
        int(item["seed"]),
        channel,
        _canonical(relevant),
    )


def reference_timeouts(limits: Mapping[str, float] | None) -> dict[str, float] | None:
    if not limits:
        return None
    from harness.q1.runner import DEFAULT_TIMEOUTS

    merged = {**DEFAULT_TIMEOUTS, **dict(limits)}
    return {**merged, "compile": merged["compile"] + merged["correctness"]}


def reference_items_for(
    consumers: Iterable[Mapping[str, Any]],
    *,
    root: str,
    min_kernels: int = DEFAULT_MIN_KERNELS,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Reference items (in first-consumer order) and, per consumer item key, the
    reference item keys it requires."""
    groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
    for item in consumers:
        group = group_of(item)
        if group is not None:
            groups.setdefault(group, []).append(item)
    refs: list[dict[str, Any]] = []
    requires: dict[str, list[str]] = {}
    for (problem_id, source_path, seed, channel, relevant), members in groups.items():
        if len({m["kernel_id"] for m in members}) < min_kernels:
            continue
        first = members[0]
        gate = CHANNEL_GATE[channel]
        kernel_id = reference_kernel_id(problem_id)
        if source_path or relevant != "{}":
            # Another problem source (tests, shrunk problems) or entry options get
            # their own reference kernel id, so item keys never collide.
            suffix = hashlib.sha256(_canonical([source_path, relevant]).encode()).hexdigest()
            kernel_id += "." + suffix[:8]
        refs.append(
            {
                "kernel_id": kernel_id,
                "kernel_path": "",
                "problem_id": problem_id,
                "gate": gate,
                "seed": seed,
                "problem_source_path": source_path,
                "options": {**json.loads(relevant), OPTION: root},
                "exclusive": bool(first.get("exclusive", False)),
                "timeouts": reference_timeouts(first.get("timeouts")),
                "units": first.get("units"),
                "journal": REFERENCE_JOURNAL,
            }
        )
        key = item_key(kernel_id, gate, seed)
        for member in members:
            requires.setdefault(item_key(member["kernel_id"], member["gate"], seed), []).append(key)
    return refs, requires


def with_references(
    items: Sequence[Mapping[str, Any]],
    *,
    root: str,
    min_kernels: int = DEFAULT_MIN_KERNELS,
) -> list[dict[str, Any]]:
    """``items`` with reference items inserted before each group's first consumer,
    and consumers given ``requires`` and ``options.reference_store``."""
    refs, requires = reference_items_for(items, root=root, min_kernels=min_kernels)
    by_key = {item_key(r["kernel_id"], r["gate"], r["seed"]): r for r in refs}
    placed: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = item_key(item["kernel_id"], item["gate"], int(item["seed"]))
        needs = requires.get(key, [])
        for ref_key in needs:
            if ref_key not in placed:
                out.append(dict(by_key[ref_key]))
                placed.add(ref_key)
        if needs:
            item = {
                **item,
                "requires": sorted(set(item.get("requires") or []) | set(needs)),
                "options": {**dict(item.get("options") or {}), OPTION: root},
            }
        out.append(dict(item))
    return out


def summary(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts for a driver's record: reference items per channel, consumers served."""
    from collections import Counter

    refs = Counter(i["gate"] for i in items if i.get("journal") == REFERENCE_JOURNAL)
    served = sum(1 for i in items if i.get("requires"))
    return {"reference_items": dict(sorted(refs.items())), "consumers_with_store": served}


__all__ = [
    "DEFAULT_MIN_KERNELS",
    "ENTRY_OPTIONS",
    "group_of",
    "reference_items_for",
    "reference_timeouts",
    "summary",
    "with_references",
]
