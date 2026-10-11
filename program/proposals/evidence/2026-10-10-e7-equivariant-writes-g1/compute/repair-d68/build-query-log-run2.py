#!/usr/bin/env python3
"""Assemble query-log-run2.json for the fresh E7 gauntlet run (D68) from the repair owner's raw query log.

Input: the per-query JSONL written by the repair's query runner at the moment of each call (one record per
counted retrieval call: orx discover keyword, embedding and openalex; OpenReview API searches; ACL Anthology
searches over the cached anthology+abstracts bibliography; OpenAlex citing-works lookups). Output: the run-2
query log beside wave 1's query-log.json, which is left as it was. Full-text reads (orx paper --full) and the
OpenAlex id resolutions are listed but not counted, as in wave 1.

Usage: python build-query-log-run2.py <log.jsonl> <out.json>
"""
import hashlib
import json
import sys

READS = [
    ("2402.19427", "De et al., Griffin: Mixing Gated Linear Recurrences with Local Attention (2024)", "Sec. 6.2 and Fig. 6 (phonebook lookup up to the 1,024 local window, degrading beyond it; 7B, 300B tokens); App. E"),
    ("2408.10151", "Hengle et al., Multilingual Needle in a Haystack (MLNeedle; NAACL 2025)", "abstract, Sec. 2 (MLQA needles, monolingual and cross-lingual), Sec. 3 (four dense instruction LLMs: Llama2-7B-Chat, Llama3-8B-Instruct, Mistral-7B-Instruct-v0.2, Aya-23-8B)"),
    ("2503.01996", "Kim et al., One ruler to measure them all (OneRuler, 2025)", "abstract, Sec. 1-2 (26 languages, NIAH variants, cross-lingual instructions and context; Qwen 2.5, Llama 3.1/3.3, o3-mini-high, Gemini 1.5 Flash), Sec. 4 cross-lingual setting"),
    ("2609.33093", "How Linear Attention Remembers (2026)", "Sec. 2.3 (pretrained GLA/GDN 340M, GDN 1.3B, near-matched hybrid; four-choice recall), Sec. 3.1 (fact-time write block of the selected head: recall -36 to -79 pp), Sec. 4.1 (hybrid state carries under 1%), App. F.2 (prose-retrieval competence check, 56.3% at 512 filler, two fixed query paraphrases)"),
    ("2509.24552", "Short window attention enables long-term memorization (SWAX, ICLR 2026)", "Sec. 3 (receptive field O(lw)), Sec. 4.1 (1.4B/7B, 150B tokens, 16K sequences, RoPE SWA), Sec. 4.2 (pure SWA receptive field 128 x 24 = 3,072), Sec. 4.3 and Figs. 5-6 (windows 128-2,048; training-time against test-time window; train 512 / test 512 average NIAH 0.33)"),
    ("2610.06750", "Balancing Memory Pathways (2026; ICLR 2027 submission)", "Sec. 4.1 (recurrent-only: attention masked across the segment boundary; attention-only: state reset at the boundary), Sec. 4.2 setup (Qwen3.5-4B, Nemotron-H-4B-Instruct; 8.2k examples, average context 84k), Sec. 5.1-5.2"),
    ("2504.10906", "Gao et al., Understanding LLMs' Cross-Lingual Context Retrieval (2025)", "abstract (40+ dense LLMs, 12 languages, xMRC; post-training forms cross-lingual context retrieval)"),
]
UNCOUNTED_LOOKUPS = [
    "OpenAlex id resolution by DOI (api.openalex.org/works/doi:10.48550/arXiv.<id>) for 2509.24552 (W4415336939, cited_by_count 0), 2609.33093 (W7214795438, 0), 2402.19427 (W6891815739, 8), 2610.06750 (W7220745173, 0), 2408.10151 (W4402502700, 0), 2503.01996 (W4415337897, 0); used only to address the citing-works queries F01 and F02",
]


def main() -> int:
    recs = [json.loads(line) for line in open(sys.argv[1])]
    by_tool = {}
    for r in recs:
        key = r["tool"] + (":" + r["mode"] if r["tool"] == "orx" else "")
        by_tool[key] = by_tool.get(key, 0) + 1
    ids = [i for r in recs for i in r["returned_ids"]]
    http429 = [r["qid"] for r in recs if r.get("http_429")]
    out = {
        "run": "E7 G1 floor gate, fresh gauntlet run after the D68 repair (2026-10-10)",
        "declared_budget_queries": 80,
        "reserved_for_refuters": 30,
        "counted_by_repair_owner": len(recs),
        "counted_by_tool": by_tool,
        "remaining_after_repair": 80 - len(recs),
        "http_429_counted": http429,
        "counting_rule": ("every retrieval search that reached a backend is counted, including OpenAlex HTTP 429 replies (wave 1's rule): "
                          "orx discover (keyword, embedding, openalex), OpenReview API searches, ACL Anthology searches over the cached "
                          "bibliography, OpenAlex citing-works lookups; full-text reads and id resolutions are listed, not counted"),
        "coverage_notes": [
            "orx 0.2.2 (alphaXiv keyword and embedding, OpenAlex); the build reports itself outdated against 0.2.18; OpenAlex returned HTTP 429 on 4 of 5 orx openalex calls",
            "OpenReview: api2.openreview.net/notes/search (forum notes, includes ICLR 2027 submissions); per-note pages are behind a browser challenge, not bypassed, so OpenReview-only items are abstract-only",
            "ACL Anthology: the parsed title-and-abstract cache of aclanthology.org/anthology+abstracts.bib.gz (sha256 a5b75a3e..., fetched 2026-10-10 by the E4 D60 repair, 131,473 entries) was reused; no new download",
            "citation graph: OpenAlex citing-works for Griffin (8 citing works indexed) and SWAX (0 indexed); OpenAlex indexes almost no citations to 2026 arXiv preprints, so the alphaXiv full-text BM25 search on each prior's title phrase (K04-K07, K13-K15) is the citation proxy; Semantic Scholar unreachable from the Mac and the host relay not used",
        ],
        "prisma": {"identified": len(ids), "unique": len(set(ids)), "screened_by_title": len(set(ids)),
                   "abstracts_read": "orx abstracts for the top hits of every keyword and embedding query; OpenReview abstracts for UUldzWxIL4, usnA2Fiw5e, Itap0vC8Xl, HdZogiR5K1, 5MKfXl078n; ACL abstracts for 2024.wmt-1.111 and 2026.eacl-long.290",
                   "full_texts_read": len(READS), "included_as_direct_prior": 0},
        "full_text_reads_not_counted": [{"id": a, "title": b, "sections": c} for a, b, c in READS],
        "uncounted_lookups": UNCOUNTED_LOOKUPS,
        "queries": recs,
    }
    text = json.dumps(out, indent=1, sort_keys=True)
    out["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
    open(sys.argv[2], "a").write("\n")
    print(len(recs), by_tool, len(ids), len(set(ids)), http429)
    return 0


if __name__ == "__main__":
    sys.exit(main())
