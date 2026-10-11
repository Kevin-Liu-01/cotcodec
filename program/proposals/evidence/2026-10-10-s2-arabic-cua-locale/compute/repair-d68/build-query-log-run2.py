#!/usr/bin/env python3
"""Build query-log-run2.json for the S2 D68 repair from the session's query runner log.

Every counted retrieval search of this run (orx discover keyword/embedding/openalex, ACL
Anthology searches over the bibliography with abstracts, OpenReview API searches) is copied
with its exact query, returned ids and the SHA-256 of its raw output. Full-text reads and
source-code fetches are listed and not counted, as in wave 1 and in the E4 repair.

Usage: python build-query-log-run2.py <runner_dir> <out.json>
(<runner_dir> holds q/log.jsonl and q/<qid>.txt; it is the session scratchpad and is not
committed, so this builder reproduces the log only inside that session.)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    rd, out = Path(sys.argv[1]), Path(sys.argv[2])
    rows = [json.loads(l) for l in (rd / "q" / "log.jsonl").read_text().splitlines() if l.strip()]
    for r in rows:
        raw = (rd / "q" / f"{r['qid']}.txt").read_text()
        assert hashlib.sha256(raw.encode()).hexdigest() == r["raw_sha256"], r["qid"]
    by_tool = {}
    for r in rows:
        key = r["tool"] if r["tool"] != "orx" else f"orx {r['mode']}"
        by_tool[key] = by_tool.get(key, 0) + 1
    ids = [i for r in rows for i in r["returned_ids"]]
    log = {
        "schema": "s2-repair-d68-query-log-v1",
        "run": "S2 gauntlet, fresh run under D68 (repair by the single owner)",
        "declared_budget_queries": 80,
        "refuter_reserve": 30,
        "counting_rule": "every retrieval search is counted: orx discover (keyword, embedding, openalex), ACL Anthology searches over the bibliography with abstracts, OpenReview API searches; full-text reads (orx paper) and source-code or standards fetches are not counted, as in wave 1 and the E4 repair",
        "counted_by_repair_owner": len(rows),
        "counted_by_tool": by_tool,
        "remaining_after_repair": 80 - len(rows),
        "reserve_intact": 80 - len(rows) >= 30,
        "coverage_notes": [
            "orx 0.2.2 (alphaXiv keyword and embedding, OpenAlex); the build reports itself outdated against 0.2.18; alphaXiv's embedding index favours recent papers",
            "ACL Anthology: the parsed title+abstract cache of aclanthology.org/anthology+abstracts.bib.gz (sha256 a5b75a3e7645ef5c25dfbd390e2c28f6a209e3eb67153b27232a7d7ce0125eea, 131,473 entries, fetched 2026-10-10 by the E4 repair and reused read-only; no new download)",
            "OpenReview: api2.openreview.net/notes/search over forum notes (titles only in the log); per-note pages return a browser challenge and were not opened",
            "Chinese-language coverage: one Chinese-language embedding query on alphaXiv (R2-q12); no Chinese-language venue (CNKI, Wanfang) was searched",
            "not searched in this run: Semantic Scholar (the host relay was not used: the host is reserved for the reviewer's lane job), patents beyond wave 1's IBM family, X, Reddit, Hacker News, Google Scholar",
        ],
        "queries": rows,
        "full_text_reads_not_counted": [
            {"id": "2601.21961", "how": "orx paper --full", "sections": "abstract, Sec. 3.1 and Table 1 (8 variant families, 48 variants), Sec. 4 findings", "finding": "VAF varies background, text colour, font family, font size, position (banner/header/sidebar), card size, clarity and order of a target item on web pages; no language, script, text-direction or layout-mirroring variant"},
            {"id": "2604.17849", "how": "orx paper (alphaXiv report)", "sections": "report sections 1-3", "finding": "repeated-execution reliability of computer-use agents; decomposes unreliability into execution stochasticity, task ambiguity and planning variability; no locale factor"},
        ],
        "source_fetches_not_counted": "13 primary-source files for the per-application switches and the isolation construction (snapshots/raw.githubusercontent.com_*, www.unicode.org_reports_tr9_, www.w3.org_TR_css-writing-modes-3_), with matched line numbers; listed in compute/repair-d68/mechanism-sources-index.json",
        "prisma": {
            "identified": len(ids),
            "unique": len(set(ids)),
            "screened_by_title": len(set(ids)),
            "abstracts_or_reports_read": ["2601.21961", "2604.17849", "macOSWorld OpenReview YJxGJP8feU (title only)", "MPR-GUI ACL 2026.acl-long.1375 (title; read in full in wave 1)"],
            "full_texts_read": 1,
            "included_as_direct_prior": 0,
            "added_to_the_ledger": ["2601.21961 (VAF, controlled visual-attribute variants for web agents)", "2604.17849 (reliability of computer-use agents)"],
        },
    }
    out.write_text(json.dumps(log, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    print(len(rows), by_tool, len(ids), len(set(ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
