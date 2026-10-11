#!/usr/bin/env python3
"""Assemble query-log-run2.json for the fresh E3 gauntlet run (D68) from the repair's raw query log.

Input: the repair owner's per-query JSONL (one record per counted orx discover call, written by the
query runner at the moment of the call, with the raw output's SHA-256; the raw outputs stay in the
session scratchpad) plus the uncounted paper reads and metadata lookups listed below. Output: the
run-2 query log beside wave 1's query-log.json, which is left as it was.

Usage: python build_query_log_run2.py <log.jsonl> <out.json>
"""
import hashlib
import json
import sys

READS = [
    ("2608.18474", "OmniAlign (Yang et al., 2026)", "orx paper --full: Secs. 2-3, Tables 3, 4, 6, 8"),
    ("2407.12881", "BinaryAlign (Latouche et al., ACL 2024)", "orx paper --full: Secs. 4.1-4.3, Tables 1, 2, 4, 7, Appendix A.2"),
    ("2601.22805", "SOMBRERO (Neitemeier et al., 2026)", "orx paper --full: Secs. 3.4, 3.5"),
    ("2502.06468", "Token alignability (Hammerl et al., NAACL 2025)", "orx paper --full: Secs. 3.2, 4, 5"),
    ("2608.18062", "TokEval (Meister, COLM 2026)", "orx paper report: abstract, Sec. 3"),
]
METADATA = [
    "OpenAlex works by DOI: 10.1177/001316446002000104 (Cohen 1960), 10.1093/oxfordjournals.aje.a112510 (Rogan and Gladen 1978), 10.3115/1118693.1118732 (Fox 2002), 10.3115/1220175.1220298 (Wellington et al. 2006), 10.3115/1609067.1609128 (Ma and Way 2009), 10.3115/1599081.1599209 (Xu et al. 2008)",
    "GitHub API and raw files: goombalab/hnet at 3673fe12 (pyproject.toml, hnet/modules/dc.py, hnet/models/hnet.py, hnet/modules/mha.py, hnet/models/mixer_seq.py, generate.py); state-spaces/mamba at a6a1dae and main (mamba_ssm/__init__.py, utils/generation.py, setup.py, commit date); huggingface/transformers v5.15.0 and v4.57.1 (generation/__init__.py, setup.py); Dao-AILab/flash-attention release v2.8.0.post2 assets; Dao-AILab/causal-conv1d commit e940ead; MilkDargon/OmniAlign, sufenlp/AccAlign, neulab/awesome-align, SapienzaNLP/XL-WA, ubisoft/ubisoft-laforge-binaryalign (repository metadata, tree, README, licence, requirements, LFS pointer)",
    "Hugging Face API: WPS-Qingqiu/OmniAlign (config.json, modeling.py imports), spacy/en_core_web_sm, spacy/zh_core_web_sm; GitHub release explosion/spacy-models zh_core_web_sm-3.8.0",
    "TsinghuaAligner page: HTTP 502 (2026-10-10)",
]


def main() -> int:
    recs = [json.loads(line) for line in open(sys.argv[1])]
    by_tool = {}
    for r in recs:
        by_tool[r["tool"]] = by_tool.get(r["tool"], 0) + 1
    ids = [i for r in recs for i in r["returned_ids"]]
    out = {
        "run": "E3 Stage-0 probe fresh gauntlet run after the D68 repair (2026-10-10)",
        "declared_budget_queries": 80,
        "reserved_for_refuters": 30,
        "counted_by_repair_owner": len(recs),
        "counted_by_tool": by_tool,
        "remaining_after_repair": 80 - len(recs),
        "counting_rule": "every orx discover call is counted (keyword, embedding, openalex), including empty or failed ones; paper reads (orx paper) and metadata reads (OpenAlex by DOI, GitHub, Hugging Face, raw files) are not counted, as in wave 1",
        "coverage_notes": [
            "orx 0.2.2 (alphaXiv keyword and embedding, OpenAlex); the alphaXiv keyword search with --published-after favours recent unrelated items (R06)",
            "OpenAlex through orx returns no forward-citation lists; forward citations of 2502.06468 and 2601.22805 were approximated by title (R17, R18) and embedding (R07) searches",
            "Semantic Scholar and the arXiv API were not used (unreachable from the Mac; the host is reserved for the reviewer lane job)",
        ],
        "prisma": {"identified": len(ids), "unique": len(set(ids)), "screened_by_title": len(set(ids)),
                   "full_texts_or_reports_read": len(READS), "included_as_direct_prior": 0},
        "paper_reads_not_counted": [{"id": a, "title": b, "sections": c} for a, b, c in READS],
        "metadata_reads_not_counted": METADATA,
        "queries": recs,
    }
    text = json.dumps(out, indent=1, sort_keys=True)
    out["payload_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
    print(len(recs), by_tool, len(ids), len(set(ids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
