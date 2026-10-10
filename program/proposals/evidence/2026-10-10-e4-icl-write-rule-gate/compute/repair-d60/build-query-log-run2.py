#!/usr/bin/env python3
"""Assemble query-log-run2.json for the fresh E4 gauntlet run (D60) from the repair's raw query log.

Input: the repair owner's per-query JSONL (one record per counted retrieval call, written by the
query runner at the moment of the call) and the list of uncounted full-text reads. Output: the run-2
query log beside wave 1's query-log.json, which is left as it was.

Usage: python build-query-log-run2.py <log.jsonl> <out.json>
"""
import hashlib
import json
import sys

FLAWED = {"A01", "A02", "A03"}  # first ACL searches: the bib parser missed the abstract field (last field, no
                                # trailing comma), so these searched titles only; recorded, counted, and rerun as A04-A06

READS = [
    ("2212.10559", "Dai et al., Why Can GPT Learn In-Context? (ACL Findings 2023)", "Sec. 2.2 dual form, 3.1, 3.2, 4.1"),
    ("2311.07772", "Deutch et al., In-context Learning and Gradient Descent Revisited (NAACL 2024)", "abstract, 3.3, 4.1-4.5, 6"),
    ("2506.06266", "Eyuboglu et al., Cartridges (2025)", "abstract, 3.2, 4.2"),
    ("2602.16284", "Zweiger et al., Fast KV Compaction via Attention Matching (ICML 2026)", "abstract, 3.2-3.3, discussion"),
    ("2609.17346", "Rakotonirina et al., Where Should a Document Live (2026)", "abstract, 3, 4, Table 2, 5.1"),
    ("2404.11225", "Li et al., In-Context Learning State Vector with Inner and Momentum Optimization (2024)", "abstract, 1, outline"),
    ("2507.04221", "Lu et al., Context Tuning for In-Context Optimization (2025; ICML 2026)", "abstract, 1"),
    ("2507.16003", "Dherin et al., Learning without training: the implicit dynamics of in-context learning (2025)", "abstract, Theorem 2.3"),
    ("2310.19698", "Petrov et al., When Do Prompting and Prefix-Tuning Work? (ICLR 2024)", "abstract, Sec. 4 heading and statement"),
    ("2610.05885", "Villeneuve et al., The Optimization Landscape of Learning Compacted Context Models (2026)", "abstract, 1"),
]


def main() -> int:
    recs = [json.loads(line) for line in open(sys.argv[1])]
    for r in recs:
        if r["qid"] in FLAWED:
            r["flawed"] = "title-only search (parser bug: the abstract field was not read); counted; rerun with the fixed parser"
    by_tool = {}
    for r in recs:
        by_tool[r["tool"]] = by_tool.get(r["tool"], 0) + 1
    ids = [i for r in recs for i in r["returned_ids"]]
    out = {
        "run": "E4 gate fresh gauntlet run after the D60 repair (2026-10-10)",
        "declared_budget_queries": 80,
        "reserved_for_refuters": 30,
        "counted_by_repair_owner": len(recs),
        "counted_by_tool": by_tool,
        "remaining_after_repair": 80 - len(recs),
        "counting_rule": "every retrieval search is counted: orx discover (keyword, embedding, openalex), OpenReview API searches and ACL Anthology searches over the downloaded anthology+abstracts bib; full-text reads (orx paper --full) are not counted, as in wave 1",
        "coverage_notes": [
            "OpenReview: api2.openreview.net/notes/search (forum notes; includes ICLR 2027 submissions); the per-note endpoint returned a bot challenge, which was not bypassed, so OpenReview-only papers were read through the search API's abstracts",
            "ACL Anthology: aclanthology.org/anthology+abstracts.bib.gz (sha256 a5b75a3e..., 42.5 MB, fetched 2026-10-10; 131,473 entries, 82,295 with abstracts), searched with all-of regular expressions over title and abstract",
            "orx 0.2.2 (alphaXiv keyword and embedding, OpenAlex); the alphaXiv embedding index favours recent papers",
        ],
        "prisma": {"identified": len(ids), "unique": len(set(ids)),
                   "screened_by_title": len(set(ids)),
                   "abstracts_read": "OpenReview search abstracts for vdDNOvVZxW, x7actWdqhZ, JHUthhdVQu, KYVfZRpU3B; ACL abstracts for 2025.findings-acl.345; orx abstracts for every N-query hit list's top items",
                   "full_texts_read": len(READS), "included_as_direct_prior": 0},
        "full_text_reads_not_counted": [{"id": a, "title": b, "sections": c} for a, b, c in READS],
        "queries": recs,
    }
    text = json.dumps(out, indent=1, sort_keys=True)
    out["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
    print(len(recs), by_tool, len(ids), len(set(ids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
