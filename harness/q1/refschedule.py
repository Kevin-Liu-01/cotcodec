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
- a group whose estimated entry (``entry_bytes_estimate``: stored outputs per
  draw from the memory table, fp64 for the audit oracle) exceeds
  ``entry_cap_bytes`` (``ENTRY_CAP_BYTES``) gets no reference item: its
  consumers compute inline (D31 review, finding 5);
- the reference item is placed just before the group's first consumer, takes
  that consumer's concurrency units, memory estimate and exclusivity, and its
  compile-phase limit is the consumer's compile plus correctness limits (it
  never loads a candidate, so it never enters the ``correctness`` phase); with
  ``store_cap_bytes`` it carries the store's disk cap (``refstore.CAP_OPTION``);
- every consumer gets ``requires`` (the runner starts it only when the
  reference item is no longer queued or running) and the store root in
  ``options.reference_store``. A consumer whose reference item failed, was cut
  or never ran finds no usable entry and computes inline.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from harness.q1.journal import item_key
from harness.q1.refstore import (
    CAP_OPTION,
    CHANNEL_GATE,
    CHANNEL_OF,
    OPTION,
    REFERENCE_JOURNAL,
    reference_kernel_id,
)

#: Item options that change a channel's entry (and so split groups).
ENTRY_OPTIONS = ("manifest_path", "num_trials")
DEFAULT_MIN_KERNELS = 2
#: Registered cap on one entry's estimated tensors (section 18.9); larger groups
#: compute inline.
ENTRY_CAP_BYTES = 50_000_000_000
#: Draws per channel that do not depend on the problem (A1: five native draws; A2:
#: seven distributions; A5: one draw with seven reference calls).
A1_DRAWS, A2_DRAWS, A5_CALLS = 5, 7, 7
_DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def _shape_manifest() -> dict[str, Any]:
    return json.loads((_DATA / "shape_manifest.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _kbv_configs() -> dict[str, Any]:
    return json.loads((_DATA / "kbv_hidden_configs.json").read_text(encoding="utf-8"))


def entry_bytes_estimate(problem_id: str, channel: str) -> int | None:
    """Upper estimate of an entry's stored tensors from the memory table (``None``:
    the problem is not in it). gate (c): one fp32 output per configuration (c1's
    KBV configurations, two draws per c2 and c3 configuration), at the largest
    output of any configuration; A1 and A2: an fp64 oracle output per draw at
    native shapes; A3: one per A3 configuration at the largest output; A5: seven
    fp32 outputs at native shapes."""
    from harness.q1 import memory

    entry = memory.table()["problems"].get(problem_id)
    if entry is None:
        return None
    native = int(entry["native"]["output_bytes"] or entry["native"]["input_bytes"])
    largest = int(entry["all_configs"]["output_bytes"] or entry["all_configs"]["input_bytes"])
    shapes = _shape_manifest()["problems"].get(problem_id, {})
    if channel == "c":
        c1 = len(_kbv_configs()["problems"].get(problem_id, {}).get("configs", [1, 2, 3, 4]))
        draws = c1 + 2 * (len(shapes.get("c2", [])) + len(shapes.get("c3", [])))
        return draws * largest
    if channel == "A1":
        return A1_DRAWS * 2 * native
    if channel == "A2":
        return A2_DRAWS * 2 * native
    if channel == "A3":
        return len(shapes.get("A3", [])) * 2 * largest
    if channel == "A5":
        return A5_CALLS * native
    raise ValueError(f"unknown channel {channel}")


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
    entry_cap_bytes: int | None = ENTRY_CAP_BYTES,
    store_cap_bytes: int | None = None,
    over_cap: list[dict[str, Any]] | None = None,
    estimates: dict[str, int | None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Reference items (in first-consumer order) and, per consumer item key, the
    reference item keys it requires. Groups over ``entry_cap_bytes`` are listed in
    ``over_cap`` (when given) and get no reference item; ``estimates`` (when given)
    receives each reference item's entry estimate by item key."""
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
        estimate = entry_bytes_estimate(problem_id, channel) if not source_path else None
        if entry_cap_bytes is not None and estimate is not None and estimate > entry_cap_bytes:
            if over_cap is not None:
                over_cap.append(
                    {"problem_id": problem_id, "seed": seed, "channel": channel, "bytes": estimate}
                )
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
                "options": {
                    **json.loads(relevant),
                    OPTION: root,
                    **({CAP_OPTION: int(store_cap_bytes)} if store_cap_bytes else {}),
                },
                "exclusive": bool(first.get("exclusive", False)),
                "timeouts": reference_timeouts(first.get("timeouts")),
                "units": first.get("units"),
                "memory_bytes": first.get("memory_bytes"),
                "journal": REFERENCE_JOURNAL,
            }
        )
        key = item_key(kernel_id, gate, seed)
        if estimates is not None:
            estimates[key] = estimate
        for member in members:
            requires.setdefault(item_key(member["kernel_id"], member["gate"], seed), []).append(key)
    return refs, requires


def with_references(
    items: Sequence[Mapping[str, Any]],
    *,
    root: str,
    min_kernels: int = DEFAULT_MIN_KERNELS,
    entry_cap_bytes: int | None = ENTRY_CAP_BYTES,
    store_cap_bytes: int | None = None,
    over_cap: list[dict[str, Any]] | None = None,
    estimates: dict[str, int | None] | None = None,
) -> list[dict[str, Any]]:
    """``items`` with reference items inserted before each group's first consumer,
    and consumers given ``requires`` and ``options.reference_store`` (see
    :func:`reference_items_for` for ``over_cap`` and ``estimates``)."""
    refs, requires = reference_items_for(
        items,
        root=root,
        min_kernels=min_kernels,
        entry_cap_bytes=entry_cap_bytes,
        store_cap_bytes=store_cap_bytes,
        over_cap=over_cap,
        estimates=estimates,
    )
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


def footprint(items: Sequence[Mapping[str, Any]], estimates: Mapping[str, int | None]) -> dict:
    """Estimated disk footprint of a job's store: the sum over its entries, and the
    largest live total if each entry's tensors are deleted once its last consumer
    has run (consumers run in queue order after their reference item)."""
    last_use: dict[str, int] = {}
    position = {}
    for index, item in enumerate(items):
        key = item_key(item["kernel_id"], item["gate"], int(item["seed"]))
        position[key] = index
        for ref in item.get("requires") or []:
            last_use[ref] = index
    live = peak = 0
    events: list[tuple[int, int]] = []
    for key, size in estimates.items():
        if size is None or key not in position:
            continue
        events.append((position[key], int(size)))
        events.append((last_use.get(key, position[key]) + 1, -int(size)))
    for _, delta in sorted(events, key=lambda e: (e[0], e[1])):
        live += delta
        peak = max(peak, live)
    total = sum(int(v) for v in estimates.values() if v is not None)
    return {"entries_bytes_estimate": total, "peak_live_bytes_estimate": peak}


def summary(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts for a driver's record: reference items per channel, consumers served."""
    from collections import Counter

    refs = Counter(i["gate"] for i in items if i.get("journal") == REFERENCE_JOURNAL)
    served = sum(1 for i in items if i.get("requires"))
    return {"reference_items": dict(sorted(refs.items())), "consumers_with_store": served}


__all__ = [
    "DEFAULT_MIN_KERNELS",
    "ENTRY_CAP_BYTES",
    "ENTRY_OPTIONS",
    "entry_bytes_estimate",
    "footprint",
    "group_of",
    "reference_items_for",
    "reference_timeouts",
    "summary",
    "with_references",
]
