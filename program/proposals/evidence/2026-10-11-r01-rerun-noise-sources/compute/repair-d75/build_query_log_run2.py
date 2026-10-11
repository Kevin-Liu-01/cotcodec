#!/usr/bin/env python3
"""Query log of the D75 repair run (fresh gauntlet run 2 of R01): every counted retrieval query
with its returned ids and raw-output digest, plus the uncounted reads and fetches.

Input: the repair owner's wrapper log (``q.sh`` appends one JSON line per ``orx discover`` call
with the query, mode, arguments, UTC time, exit code, raw-output SHA-256 and returned ids), the
full-text and report reads, and the fetch attempts for the closest prior's full text. Raw outputs
stay in the session scratchpad (they hold abstracts); the repository receives ids and digests.

Usage: python3 build_query_log_run2.py --log <q/log.jsonl> --reads <reads.out> --out query-log-run2.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BUDGET = 80
RESERVE = 30


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--reads", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    queries = [json.loads(x) for x in args.log.read_text().splitlines() if x.strip()]
    reads = []
    for line in args.reads.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 4:
            reads.append(
                {
                    "id": parts[0],
                    "kind": parts[1],
                    "rc": parts[2].split("=")[1],
                    "bytes": int(line.split("bytes=")[1].split()[0]),
                    "utc": line.split("utc=")[1].strip(),
                }
            )
    ids = [i for q in queries for i in q["returned_ids"]]
    unique = sorted(set(ids))
    out = {
        "schema": "r01-query-log-run2-v1",
        "run": "R01 fresh gauntlet run under D75 (repair by the single owner)",
        "counting_rule": (
            "every retrieval search that reached a backend counts (orx discover keyword, embedding, openalex; "
            "OpenReview or ACL Anthology searches; arXiv title searches), the program convention of S2 run 2, "
            "S2 v3 and R01 wave 1's recorder; full-text reads, report reads and page fetches are recorded, not counted"
        ),
        "declared_queries": BUDGET,
        "refuter_reserve": RESERVE,
        "counted": {"orx_discover": len(queries), "other_searches": 0, "total": len(queries)},
        "remaining_after_repair": BUDGET - len(queries),
        "reserve_intact": BUDGET - len(queries) >= RESERVE,
        "queries": [
            {
                k: q[k]
                for k in (
                    "id",
                    "mode",
                    "query",
                    "extra",
                    "utc",
                    "exit",
                    "raw_sha256",
                    "n",
                    "returned_ids",
                )
            }
            for q in queries
        ],
        "reads_not_counted": reads,
        "fetch_attempts_not_counted": [
            {
                "what": "cELldjX2oq full text, https://openreview.net/pdf?id=cELldjX2oq, through the H100 host relay (curl, read-only ssh)",
                "result": "HTTP 403, OpenReview browser-challenge HTML (12,707 bytes); not bypassed",
                "utc": "2026-10-11T12:15Z",
            },
            {
                "what": "cELldjX2oq through the OpenReview API, https://api2.openreview.net/attachment?id=cELldjX2oq&name=pdf and /notes?id=",
                "result": "HTTP 403 ChallengeRequiredError; not bypassed",
                "utc": "2026-10-11T12:16Z",
            },
        ],
        "prisma": {
            "identified": len(ids),
            "unique": len(unique),
            "screened_by_title": len(unique),
            "read_beyond_title": len(reads),
            "read_full_text": [r["id"] for r in reads if r["kind"] == "full"],
            "read_report": [r["id"] for r in reads if r["kind"] == "report"],
            "direct_priors": 0,
        },
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(
        json.dumps(
            {k: out[k] for k in ("counted", "remaining_after_repair", "reserve_intact", "prisma")}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
