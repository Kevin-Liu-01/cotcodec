"""Row comparison helpers for the reference-store equivalence tests (not collected).

Pure Python: the verdict rows of an inline run and a store run are compared
without timing and run-identity fields and without process-specific text.
"""

from __future__ import annotations

import json
import re

#: Row fields that measure time or name the run; everything else must match.
VOLATILE_TOP = ("gpu_seconds", "wall_seconds", "run_id")
VOLATILE_DETAILS = (
    "item_wall_seconds",
    "item_started_at",
    "item_ended_at",
    "slot",
    "log_tail",
)


#: Process-specific text gate (b1) records in its launch captures: KernelBench's
#: loader imports each candidate from a fresh temporary file, and a grid callable is
#: printed with its address. Neither depends on the store (b1 reads no reference).
TEMPFILE = re.compile(r"/tmp/tmp[A-Za-z0-9_]+\.py")
ADDRESS = re.compile(r" at 0x[0-9a-f]+")


#: Detail lists that hold a set (the static checker builds them from Python sets,
#: whose order follows the process's string hash seed): compared sorted.
SET_DETAILS = ("static_warnings", "static_errors")


def normalized(row: dict) -> str:
    row = {k: v for k, v in row.items() if k not in VOLATILE_TOP}
    row["details"] = {k: v for k, v in row["details"].items() if k not in VOLATILE_DETAILS}
    for key in SET_DETAILS:
        if isinstance(row["details"].get(key), list):
            row["details"][key] = sorted(row["details"][key], key=str)
    text = TEMPFILE.sub("<tempfile>", json.dumps(row, sort_keys=True))
    return ADDRESS.sub(" at <address>", text)


def fails_dual_poison(rows: list[dict]) -> set[str]:
    """Kernels whose output changes when fresh allocations are filled with 0x00 instead
    of 0xFF (A4's dual-poison check): they read bytes they never wrote, or are not
    deterministic at all.

    A kernel that reads unwritten bytes gets gate and A1-A3 rows that depend on what
    the allocator hands back, which is harness history (other allocations in the
    process, concurrency): pilot jobs 518 and 548 already gave such a kernel different
    verdicts on identical items. The store changes that history, so such rows are
    outside the equivalence claim. A4 rejects these kernels either way, so every audit
    tier is the same."""
    out = set()
    for row in rows:
        if row["gate"] != "A4" or row["config_id"] != "in-process":
            continue
        subchecks = row["details"].get("subchecks", {})
        if any(
            not s.get("dual_poison_factory", {}).get("passed", True) for s in subchecks.values()
        ):
            out.add(row["kernel_id"])
    return out


def row_index(rows: list[dict]) -> dict[tuple[str, str, str, str], list[str]]:
    out: dict[tuple[str, str, str, str], list[str]] = {}
    for row in rows:
        key = (row["kernel_id"], row["gate"], row["config_id"], row["tf32_policy"])
        out.setdefault(key, []).append(normalized(row))
    return {k: sorted(v) for k, v in out.items()}


def _paths(a: object, b: object, prefix: str = "") -> list[str]:
    """Paths at which two JSON values differ (for readable failure messages)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return [
            p for k in sorted(set(a) | set(b)) for p in _paths(a.get(k), b.get(k), f"{prefix}.{k}")
        ]
    return [] if a == b else [f"{prefix}: {str(a)[:120]} != {str(b)[:120]}"]


def differences(inline: list[dict], stored: list[dict]) -> list[dict]:
    left, right = row_index(inline), row_index(stored)
    out = []
    for key in sorted(set(left) | set(right)):
        if left.get(key) != right.get(key):
            a, b = left.get(key) or [], right.get(key) or []
            paths = (
                _paths(json.loads(a[0]), json.loads(b[0])) if len(a) == len(b) == 1 else ["count"]
            )
            out.append({"key": key, "inline": a, "store": b, "paths": paths})
    return out


def describe(diff: list[dict]) -> str:
    return "\n".join(f"{d['key']}: {d['paths'][:4]}" for d in diff[:12])
