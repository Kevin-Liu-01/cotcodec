#!/usr/bin/env python3
"""Assemble query-log-run2.json for C5's fresh gauntlet run after the D68 repair.

Input: the repair owner's per-query JSONL (one record per counted retrieval call, written by the
query runner at the moment of the call, with the raw output's SHA-256; raw outputs stay in the
session scratchpad, as in wave 1). Output: the run-2 query log beside wave 1's query-log.json, which
is left as it was. Counting rule (wave 1's, kept): every retrieval search counts, including backend
rejections (OpenAlex HTTP 429); orx paper reads and PDF reads do not.

Usage: python build-query-log-run2.py <queries-run2.jsonl> <out.json>
"""

import hashlib
import json
import sys

READS = [
    ("2510.25602", "Chen et al., INT v.s. FP: A Comprehensive Study of Fine-Grained Low-bit Quantization Formats (arXiv v1)",
     "orx paper --full; Sec. 4.1 assumptions, Eq. 12-14, Theorems 1-2 and their interpretations, Fig. 3, Table 2, Sec. 5.1-5.3",
     "5c3301eeaec20457dee1f98b7fc82a359da27661d22d886400b88f7bf435509d"),
    ("2302.08007", "Rouhani et al., With Shared Microexponents, A Little Shifting Goes a Long Way (ISCA 2023)",
     "orx paper --full; Sec. IV-A (QSNR and the Pearson correlation with LM training loss), Fig. 7 (FP4 E2M1/E1M2/E3M0, scaled INT4)",
     "ab339035f8a74aed82f6d47f5c0dd9b111ceb8a47a43fb4fd84ec596555be0e3"),
    ("DOI 10.1109/ARITH64983.2025.00011", "Yang et al., An Empirical Study of Microscaling Formats for Low-Precision LLM Training (ARITH 2025)",
     "open copy https://par.nsf.gov/servlets/purl/10628832 (HTTP 200, application/pdf, 2,352,338 B), pdftotext; read in full: Sec. III design factors, "
     "Figs. 4-13, Insights 1-6; training runs E2M1 (E3M0 for gradients) under E8M0 only; INT4 only in R-MSE tensor analysis",
     "d1d5b8e32b0b5ccac3c0a1aa385caf4c82c8150b733d02ccf0644ef005295ded"),
]


def main() -> int:
    recs = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8")]
    by_tool, rejected = {}, 0
    for r in recs:
        by_tool[r["tool"]] = by_tool.get(r["tool"], 0) + 1
        rejected += bool(r.get("backend_error"))
    ids = [i for r in recs for i in r["returned_ids"]]
    out = {
        "run": "C5 fresh gauntlet run after the D68 repair (2026-10-10); repair owner's retrieval only",
        "declared_budget_queries": 80,
        "reserved_for_refuters": 30,
        "counted_by_repair_owner": len(recs),
        "rejected_by_backend": rejected,
        "counted_by_tool": by_tool,
        "remaining_after_repair": 80 - len(recs),
        "counting_rule": "every retrieval search counts, including backend rejections (OpenAlex HTTP 429): orx discover keyword, embedding and openalex, and OpenReview api2 notes/search; orx paper --full reads and the NSF PAR PDF read do not count, as in wave 1",
        "coverage_notes": [
            "orx 0.2.2 (alphaXiv keyword and embedding; OpenAlex returned HTTP 429 on both attempts, R2-07 and R2-15, so the OpenAlex leg is again degraded)",
            "OpenReview api2.openreview.net/notes/search (forum notes, content all; includes ICLR 2027 submissions and ICML 2026 camera-ready records); per-note pages and PDFs not fetched (browser challenge in wave 1), so OpenReview-only items are abstract-level",
            "not searched: patents, Chinese-language venues, X, Reddit, Hacker News, vendor blogs; the citation graph of 2510.25602 not expanded (OpenAlex rate-limited)",
        ],
        "prisma": {
            "identified": len(ids),
            "unique": len(set(ids)),
            "screened_by_title": len(set(ids)),
            "abstracts_read": "orx abstracts of 2607.04422, 2608.01847, 2606.13370, 2609.37693, 2605.12464, 2609.37416, 2603.08741, 2609.29397; OpenReview search abstracts of eEicXkAWDk, 6xNJZSLSjl, CzwnhuTaBw, 1GIYHWO9S5, yLILdp4xpf",
            "full_texts_read": len(READS),
            "included_as_direct_prior": 0,
        },
        "findings": [
            "No paper found trains E2M1 and INT4 under both power-of-two and non-power-of-two block scales.",
            "ARITH 2025 is not on arXiv (R2-03 title search returns other work); its open copy on NSF PAR was read in full.",
            "2510.25602 appears on OpenReview twice: an ICLR 2026 withdrawn submission (gMUZ8GKRFf) and an ICML 2026 regular paper (1GIYHWO9S5) whose abstract states that MXINT4 is superior to MXFP4, while arXiv v1 (read in full) finds MXINT4 behind MXFP4 without rotation; the camera-ready full text was not read (abstract-level discrepancy).",
            "New relevant item: OpenReview eEicXkAWDk (ICLR 2027 submission, abstract only): in a small model nearly all of one FP4 recipe's gap to BF16 comes from forward-pass rounding; cited for the attribution endpoint.",
        ],
        "full_text_reads_not_counted": [{"id": a, "title": b, "sections": c, "text_sha256": d} for a, b, c, d in READS],
        "queries": recs,
    }
    text = json.dumps(out, indent=1, sort_keys=True)
    out["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(len(recs), by_tool, rejected, len(ids), len(set(ids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
