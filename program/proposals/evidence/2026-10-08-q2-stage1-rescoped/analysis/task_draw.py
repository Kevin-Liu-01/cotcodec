"""Seeded task draw for q2-stage1-rescoped-v1 (draft): base set and extension order.

Pool: the 120-task confirm split of program/evidence/q2-mutation/splits.json (seed 42) minus the
four K1 raw-gold failures. Base: plain largest-remainder apportionment over domains (ties by domain
name), then within each domain the first n_d ids of sorted(ids) shuffled by
random.Random(f"q2-stage1a:base:42:{domain}"). Extension: the remaining ids, sorted, shuffled by
random.Random("q2-stage1a:ext:42"), cut into blocks of 8. Usage: python task_draw.py <repo_root> [K]
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

REPO = Path(sys.argv[1])
K = int(sys.argv[2]) if len(sys.argv) > 2 else 32
K1_RAW_GOLD_FAILURES = ("0a0faba3", "15aece23", "ac1b39ff", "ed43c15f")
splits = json.loads((REPO / "program/evidence/q2-mutation/splits.json").read_text())
pool = sorted(t for t in splits["confirm"] if t[:8] not in K1_RAW_GOLD_FAILURES)
domain = {
    t: json.loads((REPO / f"program/evidence/q2-mutation/sanitized-tasks/{t}.json").read_text())[
        "domain"
    ]
    for t in pool
}
counts = Counter(domain.values())


def apportion(k: int) -> dict[str, int]:
    quota = {d: k * n / len(pool) for d, n in counts.items()}
    seats = {d: math.floor(q) for d, q in quota.items()}
    for d in sorted(quota, key=lambda d: (-(quota[d] - seats[d]), d))[: k - sum(seats.values())]:
        seats[d] += 1
    if min(seats.values()) < 1:
        raise SystemExit(f"K={k} leaves a domain empty")
    return dict(sorted(seats.items()))


seats = apportion(K)
base = []
for d in sorted(seats):
    ids = sorted(t for t in pool if domain[t] == d)
    random.Random(f"q2-stage1a:base:42:{d}").shuffle(ids)
    base += ids[: seats[d]]
rest = sorted(set(pool) - set(base))
random.Random("q2-stage1a:ext:42").shuffle(rest)
blocks = [rest[i : i + 8] for i in range(0, len(rest), 8)]
out = {
    "K_base": K,
    "pool_size": len(pool),
    "pool_domains": dict(sorted(counts.items())),
    "seats": seats,
    "base": sorted(base),
    "extension_blocks": blocks,
    "splits_sha256": hashlib.sha256(
        (REPO / "program/evidence/q2-mutation/splits.json").read_bytes()
    ).hexdigest(),
}
print(json.dumps(out, indent=1))
