#!/usr/bin/env python3
"""Build query-log.json for the E5 gauntlet from the discovery cells' raw orx outputs.

The frontier and kill-shot cells saved each `orx discover` output as q<N>.txt without the
query text; their structured results listed the queries in the same order. The query
strings below are transcribed from those structured results (the computed task text of
workflow gauntlet-e5-wave1), and the returned ids are parsed from the raw files, whose
SHA-256 are recorded. The cross-domain cell saved queries.json with query text and ids;
the asset cell saved one file with a header per query. Runs only inside the session that
holds the scratchpad; the log records every raw file's digest so it can be checked.

Usage: python build-query-log.py <scratchpad-dir> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

FRONTIER = [
    ("keyword", "How Linear Attention Remembers", None),
    ("keyword", "Multilinguality in Hybrid Attention", None),
    ("keyword", "SpectralShift Gated DeltaNet spectral reparameterization", None),
    ("keyword", "token fertility recurrent state decay", None),
    ("keyword", "memory load interference elapsed context linear attention recall", None),
    ("embedding", "Does exact-match recall in attention-free gated delta-rule language models (RWKV-7, Gated DeltaNet) drop when the same content is split into more tokens, and is the drop caused by per-token state decay or by interference from extra writes?", None),
    ("keyword", "non-canonical tokenization recurrent", None),
    ("keyword", "tokenization granularity state space model recall", None),
    ("keyword", "multilingual RWKV tokenizer fertility", None),
    ("keyword", "decay rescale inference length extrapolation Mamba", None),
    ("embedding", "tokenizer fertility disparity across languages penalizes recurrent linear-attention and state-space language models with fixed-size memory more than transformers", None),
    ("embedding", "splitting words into more subword tokens (character-level re-segmentation) of the same text and measuring in-context recall in Mamba or linear RNN language models", None),
    ("openalex", "token fertility multilingual recurrent state space model memory", None),
    ("openalex", "gated linear recurrence forget gate time warping invariance", None),
    ("keyword", "Broken tokens non-canonical tokenizations", None),
    ("keyword", "character-level tokenization Mamba recall", None),
    ("keyword", "training-free decay scaling context extension linear attention", None),
    ("embedding", "training-free inference-time rescaling of forget-gate decay in a pretrained linear-attention or state-space language model to lengthen memory, e.g. scaling the discretization step or log decay by a constant", None),
    ("embedding", "multilingual evaluation of attention-free recurrent language models such as RWKV, Mamba and Gated DeltaNet across languages with different tokenizer lengths", None),
    ("keyword", "RWKV-7 decay associative recall", None),
    ("keyword", "time warping invariance gated recurrent", None),
    ("keyword", "state capacity forget gate state collapse", None),
    ("keyword", "MambaExtend training-free long context extension Mamba", None),
    ("keyword", "Stuffed Mamba state collapse state capacity", None),
    ("keyword", "recency over-smoothing state space models bottlenecks", None),
    ("embedding", "under per-token forget gates the same information spread over more tokens is forgotten faster; recurrent memory retention depends on token count rather than content length", None),
    ("keyword", "multilingual needle in a haystack recurrent linear attention fertility", "--published-after 2026-06-01"),
    ("keyword", "byte-level Mamba recall tokens per word", None),
    ("keyword", "Gated DeltaNet multilingual", "--published-after 2026-05-01"),
    ("embedding", "decomposing recall loss in linear attention language models into state decay versus write interference using causal interventions on gate values", "--published-after 2026-06-01"),
    ("openalex", "MambaExtend training-free long context extension Mamba", None),
    ("openalex", "Stuffed Mamba state collapse state capacity RNN long-context", None),
    ("openalex", "language model tokenizers introduce unfairness between languages", None),
    ("embedding", "how effective are recurrent state space models for machine translation and multilingual long sequences compared with transformers", None),
    ("embedding", "when the same text is tokenized into more pieces, does the effective memory horizon of a recurrent language model scale with characters or with tokens", None),
    ("keyword", "byte-level recurrent decay timescale tokenization granularity", None),
    ("keyword", "proactive interference working memory language models", None),
    ("keyword", "tokenizer fertility long context", "--published-after 2026-09-01"),
    ("embedding", "token inflation in low-resource languages harms long-context recall of linear recurrent or hybrid language models; per-language analysis of gates or decay", "--published-after 2026-09-20"),
    ("keyword", "re-segmentation English synthetic fertility", None),
    ("keyword", "A Systematic Analysis of Hybrid Linear Attention", None),
    ("keyword", "training-free length extrapolation Gated DeltaNet decay gate scaling", "--published-after 2026-01-01"),
    ("keyword", "forget gate scaling inference RWKV length extrapolation", None),
    ("keyword", "semantic clock gate parity", None),
    ("keyword", "forgetting mass per language gate statistics parallel text", None),
    ("embedding", "halving the decay rate of a frozen recurrent language model as an intervention to test whether recall loss on longer token sequences is caused by forgetting rather than interference", None),
    ("keyword", "information density per token recurrent memory capacity languages", None),
]

KILL = [
    ("keyword", "memory load elapsed context linear attention recall decay interference", None),
    ("keyword", "How Linear Attention Remembers", None),
    ("keyword", "Multilinguality in Hybrid Attention LLMs", None),
    ("keyword", "SpectralShift Gated DeltaNet spectral reparameterization context window", None),
    ("embedding", "Does recall from the recurrent state of linear attention or state space language models drop when the same content is split into more tokens, and is the drop caused by per-token decay of the state or by interference from additional writes?", None),
    ("openalex", "decay versus interference recurrent state language model recall tokenization", None),
    ("keyword", "tokenization fertility state space model recurrent memory multilingual", None),
    ("keyword", "non-canonical tokenization character-level segmentation robustness language model", None),
    ("embedding", "Effect of tokenization granularity, subword versus character splitting of the same text, on recall and long-context performance of Mamba, RWKV and linear attention models", None),
    ("keyword", "RWKV-7 decay rescale context extension training-free", None),
    ("embedding", "token inflation in high-fertility languages hurts recurrent or linear attention models more than transformers, needle in a haystack across languages", None),
    ("keyword", "1.3B-100B-GatedDeltaNet-pure", None),
    ("keyword", "time warping invariance gates recurrent networks fertility tokenizer", None),
    ("openalex", "tokenization granularity recurrent state space model memory", None),
    ("keyword", "Mamba Modulation length generalization training-free scaling transition", None),
    ("keyword", "Stuffed Mamba state collapse state capacity forgetting", None),
    ("keyword", "RWKV multilingual long context needle tokenizer", None),
    ("embedding", "Splitting words into more subword tokens without changing content to measure how token count affects memory and retrieval in language models", None),
    ("keyword", "Broken Tokens non-canonical tokenizations", None),
    ("keyword", "decay interference forgetting linear recurrent associative recall distractors delta rule", "--published-after 2025-06-01"),
    ("openalex", "non-canonical tokenization robustness language models", None),
    ("embedding", "Gated DeltaNet and RWKV-7 forget gate decay rescaling at inference changes recall over distance; per-token decay versus write interference in pretrained recurrent language models", "--published-after 2025-06-01"),
    ("keyword", "Echo KV-cache-free associative recall", None),
    ("keyword", "fertility RWKV Mamba recurrent tokenizer token count recall degradation languages", "--published-after 2026-01-01"),
]

ASSET_UNSAVED = [  # listed in the asset cell's result; raw output not saved
    ("keyword", "systematic analysis hybrid linear attention 1.3B 100B pure ratio",
     ["2610.05842", "2608.12149", "2607.21553", "2507.06457", "2610.08527", "2605.22791"]),
]

UNCOUNTED = [
    {"cell": "frontier", "tool": "OpenReview API notes/search (type=terms)", "count": 7,
     "query": "tokenization recurrent state decay; fertility linear attention; multilingual state space model tokenization; gated DeltaNet forget gate decay recall; tokenizer fertility recurrent; multilingual linear attention; forget gate decay recall interference",
     "returned_ids": ["uo5OpAXPn0", "9LUInzhKZc", "xNfvKKom80", "q2Lnyegkr8", "dhagW3WAHa"], "note": "most forum titles hidden or HTTP 403"},
    {"cell": "frontier", "tool": "WebSearch", "count": 3,
     "query": "openreview tokenizer fertility recurrent SSM; aclanthology tokenization length multilingual Mamba RWKV; Gated DeltaNet OR RWKV-7 tokenization fertility decay recall 2026",
     "returned_ids": ["2401.13660", "2609.07681", "2025.loresmt-1.11", "2024.wmt-1.111", "2024.emnlp-main.100", "2025.acl-long.564", "2609.16183", "2509.22630", "2608.22354", "2604.07658"]},
    {"cell": "frontier", "tool": "WebSearch + WebFetch/pdftotext", "count": 1,
     "query": "MambaExtend ICLR 2025 proceedings", "returned_ids": ["ICLR 2025 f1922bd718528ac3eab114eabbbfa7a0"]},
    {"cell": "frontier", "tool": "curl export.arxiv.org/abs + HF API (version histories and subject metadata)", "count": 0,
     "query": "version checks for 14 arXiv ids; HF metadata, config and tokenizer for both subjects", "returned_ids": []},
    {"cell": "kill-shot", "tool": "WebSearch", "count": 3,
     "query": "site:aclanthology.org non-canonical tokenization recurrent SSM; openreview tokenizer fertility linear attention 2026; same content more tokens recurrent decay interference GDN RWKV-7",
     "returned_ids": ["2024.emnlp-main.100", "2401.13660", "2503.18970", "2412.14847", "2608.26449", "2510.09947", "2025.coling-main.660", "2605.13521", "2506.11305", "2503.14456", "2607.07953", "2605.22791", "2609.00103"]},
    {"cell": "kill-shot", "tool": "read-only ssh (squeue; cached model cards, receipts and tokenizer files)", "count": 0,
     "query": "host read-only checks", "returned_ids": []},
    {"cell": "cross-domain", "tool": "OpenReview api2 notes/search", "count": 2,
     "query": "decay interference linear attention recurrent state; tokenization fertility recurrent state memory",
     "returned_ids": ["dJgAbV5lNz", "5KBYAraeHy", "uo5OpAXPn0", "9a4dEL5xo8", "f7bdAVAC2e", "b3lZofUyGC", "I0TJxzJdty", "whXh2YxMbt", "lYWcLB1rAh", "S3ukuEfenO", "MBL4vJm6lt", "QphCVdMCyG", "7tNeBpmmO7", "WaV17GnVpt", "w3FemalIoe", "lzak3g6k9v", "4x2xpfKKK1", "zMOuykBYE2", "qY9ivoN3Rw", "pieKK31nBb"]},
    {"cell": "cross-domain", "tool": "WebFetch ACL Anthology", "count": 2,
     "query": "https://aclanthology.org/2023.acl-long.284/; https://aclanthology.org/2021.acl-long.243/", "returned_ids": ["2023.acl-long.284", "2021.acl-long.243"]},
    {"cell": "asset", "tool": "HF API, raw config.json and safetensors header range reads; read-only ssh (squeue, receipts, cache listing)", "count": 0,
     "query": "subject metadata and loader compatibility", "returned_ids": []},
    {"cell": "synthesis", "tool": "HF API (model metadata, config.json, file tree) and arXiv abstract pages (snapshots)", "count": 0,
     "query": "m-a-p/1.3B-100B-GatedDeltaNet-pure, linear-moe-hub/Gated-Deltanet-1.3B, fla-hub/rwkv7-1.5B-world, Salesforce/wikitext; abstracts of the cited arXiv ids", "returned_ids": []},
]

FAILURES = [
    {"cell": "asset", "tool": "orx discover openalex", "query": "A Systematic Analysis of Hybrid Linear Attention", "error": "HTTP 429 Too Many Requests (twice)"},
    {"cell": "cross-domain", "tool": "OpenReview note fetch", "query": "Beyond Fertility; The Token Tax", "error": "browser challenge, not bypassed"},
]

PAPER_READS = {
    "frontier": {"full": ["2609.33093", "2609.35378", "2609.14320", "2609.16183", "2506.19004", "2410.07145", "2507.06457", "MambaExtend (ICLR 2025 PDF, pdftotext)"],
                 "report": ["2607.26831", "2609.04434", "2610.12144", "2609.36194", "2603.10771", "2606.15521", "2609.09157", "2610.10114", "2609.32102", "2609.07681", "2609.23366", "2608.26319", "2609.12960", "2605.06946", "2604.07658", "2505.07793", "2608.10296", "2609.30634", "2610.00232", "2608.13668", "2610.06750", "2604.27263", "2604.02474", "2407.05489"]},
    "kill-shot": {"full": ["2609.33093", "2609.35378", "2609.14320", "2507.06457", "2506.19004", "2607.26831", "2603.10771", "2606.15521", "2609.16183", "2509.19633", "2606.06203", "2609.30634"]},
    "cross-domain": {"full": ["2607.26831", "2506.19004", "2609.33093", "2510.05381"],
                     "report": ["2608.30376", "2609.39800", "2502.17433", "2008.07669", "2604.02474", "2609.04434", "2510.09947"],
                     "openalex_metadata": ["10.3758/pbr.15.5.875", "10.1111/j.1467-985x.2012.01032.x", "10.3758/s13421-011-0158-0", "10.1126/sciadv.aaw2594", "10.3758/s13421-011-0094-z", "10.1073/pnas.0804451105", "10.1080/17470218.2014.914546", "10.20982/tqmp.16.2.r001", "10.3758/pbr.15.1.230", "10.1037/bul0000153"]},
    "asset": {"full": ["2507.06457", "2609.33093"]},
    "synthesis": {"reread": ["2609.33093 Secs. 2.2-2.3 and 4.2, App. A (from the frontier cell's full text)"],
                  "abstract_only_additions": ["2004.12265 (causal mediation analysis in NLP)", "2404.03646 (factual recall in Mamba)", "1804.11188 (gates and time warping)", "1609.07843 (WikiText-103)", "2412.06464 (Gated DeltaNet)", "2503.14456 (RWKV-7)", "2305.15425 (tokenizer unfairness)"]},
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids_from(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    i = text.find("[")
    try:
        return [r.get("id") for r in json.loads(text[i:])]
    except (json.JSONDecodeError, ValueError):
        return re.findall(r'"id":\s*"([^"]+)"', text)


def main() -> int:
    scratch, out = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for cell, spec, folder, pat in (("frontier", FRONTIER, "e5-frontier", "q{:02d}.txt"),
                                    ("kill-shot", KILL, "e5-kill", "q{}.txt")):
        for i, (mode, query, bound) in enumerate(spec, 1):
            raw = scratch / folder / pat.format(i)
            rows.append({"cell": cell, "n": i, "tool": f"orx discover {mode}" + (f" ({bound})" if bound else ""),
                         "query": query, "counted": True, "returned_ids": ids_from(raw),
                         "raw_file": f"{folder}/{raw.name}", "raw_sha256": sha(raw)})
    xq = json.loads((scratch / "e5-xdomain/queries.json").read_text(encoding="utf-8"))
    n = 0
    for q in xq:
        if q["tool"].startswith("orx discover"):
            n += 1
            raw = scratch / "e5-xdomain" / f"q{n:02d}.txt"
            raw_ids = ids_from(raw)
            rows.append({"cell": "cross-domain", "n": n, "tool": q["tool"], "query": q["query"], "counted": True,
                         "returned_ids": raw_ids, "cell_listed_ids": q["returned_ids"],
                         "raw_file": f"e5-xdomain/{raw.name}", "raw_sha256": sha(raw),
                         "ids_match_cell_list": raw_ids[:len(q["returned_ids"])] == q["returned_ids"]})
    asset_raw = scratch / "e5-asset/orx-asset-queries.txt"
    text = asset_raw.read_text(encoding="utf-8")
    parts = re.split(r"^### ", text, flags=re.M)[1:]
    n = 0
    for part in parts:
        head, body = part.split("\n", 1)
        mode, query = head.split(" ", 1)
        if "failed" in body[:400] and "[" not in body[:400]:
            continue
        n += 1
        ids = re.findall(r'"id":\s*"([^"]+)"', body)
        rows.append({"cell": "asset", "n": n, "tool": f"orx discover {mode}", "query": query, "counted": True,
                     "returned_ids": ids, "raw_file": "e5-asset/orx-asset-queries.txt (section)",
                     "raw_sha256": sha(asset_raw)})
    for mode, query, ids in ASSET_UNSAVED:
        n += 1
        rows.append({"cell": "asset", "n": n, "tool": f"orx discover {mode}", "query": query, "counted": True,
                     "returned_ids": ids, "raw_file": None, "raw_sha256": None,
                     "note": "raw output not saved; ids from the cell's structured result"})
    counted = sum(1 for r in rows if r["counted"])
    by_cell = {}
    for r in rows:
        by_cell[r["cell"]] = by_cell.get(r["cell"], 0) + 1
    log = {
        "schema": "e5 gauntlet query log v1",
        "built_from": "discovery cells of workflow gauntlet-e5-wave1 (frontier, kill-shot, cross-domain, asset); synthesis ran 0 counted queries",
        "queries_against_budget": counted,
        "queries_by_cell": by_cell,
        "declared_query_budget": 150,
        "refuter_reserve": 30,
        "remaining_after_synthesis": 150 - counted,
        "counted_queries": rows,
        "uncounted_searches": UNCOUNTED,
        "failures": FAILURES,
        "paper_reads": PAPER_READS,
        "cell_verdicts": {
            "frontier": "NARROWED: residual is same-content English re-segmentation x decay intervention x load on attention-free pretrained checkpoints; Boesch and Wee (2609.16183) and MambaExtend added as missed priors",
            "kill-shot": "NARROWED, not OCCUPIED; the (f, r) design as written is close to uninformative (predictable from 2609.33093, dead fund branch, decay share not identified by r = 2, re-segmentation confounded)",
            "cross-domain": "STILL_OPEN for the question, but the (f, r) design cannot separate decay from interference; ranked repairs led by a per-word decay clamp (exact mediator manipulation)",
            "asset": "first step central about 1.2 GPU-h, high about 3.5 GPU-h; GDN-pure has no licence and is not on the host; RWKV-7 receipt present; no episode inputs exist",
        },
    }
    out.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(counted, by_cell)
    mism = [(r["cell"], r["n"]) for r in rows if r.get("ids_match_cell_list") is False]
    print("cross-domain rows whose raw ids differ from the cell list:", mism)
    return 0


if __name__ == "__main__":
    sys.exit(main())
