#!/usr/bin/env python3
"""Build query-log.json for the E3 Stage-0 gauntlet from the discovery cells' raw outputs.

Reads the four cells' raw orx outputs in the session scratchpad (frontier,
kill-shot, cross-domain, asset), parses every `orx discover` call into
{cell, call, strategy, query, returned_ids, raw_file, raw_sha256}, and adds the
uncounted searches (OpenReview API, web search, metadata APIs) and paper reads
the cells reported. Counting rule (as in the C3 and E4 gauntlets): every
`orx discover` call counts against the declared query budget, including calls
that failed; OpenReview, web and metadata API calls and paper reads are logged
but not counted. The synthesis owner made no counted query.

The cross-domain cell saved results without the query string; those strings
are taken from the cell's structured report (in call order) and checked
against the first returned id of each raw file.

Usage: build_query_log.py <scratchpad-dir> <out.json>
Reproduces the log only inside the session that owns the scratchpad; every
raw file's SHA-256 is recorded so the log can be checked against it.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

XD_QUERIES = [
    ("keyword", "unbalanced optimal transport word alignment null alignment"),
    ("keyword", "Victor-Purpura spike train distance"),
    ("openalex", "spike time tiling coefficient firing rate independent correlation"),
    ("openalex", "gamma inter-annotator agreement unitizing alignment chance shuffling"),
    ("keyword", "boundary edit distance text segmentation evaluation boundary similarity"),
    ("openalex", "R-value phoneme segmentation over-segmentation evaluation"),
    ("keyword --prioritize historical", "Unbalanced Optimal Transport for Unbalanced Word Alignment"),
    ("openalex", "event coincidence analysis statistical interrelationships event time series"),
    ("keyword --prioritize historical", "affiliation metrics time series anomaly detection precision recall"),
    ("openalex", "regioneR permutation test genomic region sets overlap association"),
    ("embedding", "chance-corrected agreement between two sets of boundary positions under a null model that preserves boundary rate and spacing"),
    ("keyword --prioritize historical", "morphological segmentation evaluation boundary precision recall morpheme"),
    ("keyword --prioritize historical", "word alignment gold test set English Korean annotated alignments"),
    ("keyword --prioritize historical", "label projection word alignment span projection cross-lingual named entity"),
    ("keyword --prioritize historical", "Sinkhorn divergences for unbalanced optimal transport"),
    ("keyword --prioritize historical", "translation invariant Sinkhorn 1-D Frank-Wolfe unbalanced"),
    ("openalex", "Measuring word alignment quality for statistical machine translation"),
    ("openalex", "noise ceiling representational similarity analysis toolbox"),
    ("embedding", "measure whether a tokenizer or segmenter places boundaries at corresponding positions in translations of the same sentence"),
    ("keyword --prioritize historical", "R-value over-segmentation boundary F1 tolerance window phoneme segmentation"),
    ("openalex", "WindowDiff Pk text segmentation evaluation metric critique"),
    ("openalex", "Krippendorff reliability of unitizing continuum alpha"),
    ("keyword --prioritize historical", "Korean jamo decomposition morpheme boundary inside syllable tokenization"),
    ("keyword --prioritize historical", "XL-WA multilingual word alignment benchmark gold"),
    ("openalex", "Nature and precision of temporal coding in visual cortex: a metric-space analysis"),
    ("openalex", "Conditional modeling and the jitter method of spike resampling"),
    ("openalex", "On the reliability of unitizing continuous data Krippendorff"),
]

ASSET_QUERIES = {
    "orx-a1.json": ("keyword", "released byte-level language model checkpoints learned boundary predictor dynamic chunking multilingual"),
    "orx-a2.json": ("embedding", "multilingual byte-level LM with learned dynamic chunking boundaries and released weights evaluated on Chinese Korean Polish"),
    "orx-a3.json": ("keyword", "OmniAlign word alignment"),
    "orx-a4.json": ("keyword", "CTFAlign MDPAlign"),
    "orx-a5.json": ("keyword", "FLORES+ word alignment gold English Chinese Korean"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_ids(text: str) -> tuple[list[str], str]:
    i = text.find("[")
    if i < 0:
        if "429" in text:
            return [], "FAILED: OpenAlex 429 Too Many Requests"
        return [], "FAILED: no JSON array"
    try:
        data, _end = json.JSONDecoder().raw_decode(text[i:])  # raw files may end with an 'rc=0' line
    except json.JSONDecodeError:
        return [], "unparseable output"
    return [str(rec.get("id") or rec.get("doi") or "") for rec in data], "ok"


def frontier(root: Path) -> list[dict]:
    cell = root / "e3-frontier"
    structured = json.loads((cell / "queries.json").read_text())
    rows = []
    discover = [q for q in structured if q["tool"].startswith("orx discover")]
    raw_names = ["q01b.raw"] + [f"q{n:02d}.raw" for n in range(2, 62)]
    # q01 was run twice (q01.txt parsed, q01b.raw raw); both calls count
    q01 = cell / "q01.txt"
    rows.append({"cell": "frontier", "call": "q01", "strategy": discover[0]["tool"].removeprefix("orx discover "),
                 "query": discover[0]["query"], "returned_ids": discover[0]["returned_ids"],
                 "raw_file": "e3-frontier/q01.txt", "raw_sha256": sha(q01), "counted": True,
                 "note": "first run of q01; identical results to q01b"})
    for q, name in zip(discover, raw_names):
        raw = cell / name
        ids, status = parse_ids(raw.read_text(errors="replace")) if raw.exists() else ([], "raw missing")
        rows.append({"cell": "frontier", "call": name.removesuffix(".raw"), "strategy": q["tool"].removeprefix("orx discover "),
                     "query": q["query"], "returned_ids": q["returned_ids"], "raw_file": f"e3-frontier/{name}",
                     "raw_sha256": sha(raw) if raw.exists() else None, "parse_status": status,
                     "raw_ids_match_structured": (ids[: len(q["returned_ids"])] == q["returned_ids"]) if ids else None,
                     "counted": True})
    for q in structured:
        if not q["tool"].startswith("orx discover"):
            rows.append({"cell": "frontier", "strategy": q["tool"], "query": q["query"],
                         "returned_ids": q["returned_ids"], "counted": False})
    return rows


def killshot(root: Path) -> list[dict]:
    cell = root / "e3-killshot"
    rows = []
    for n in range(1, 25):
        cmd = (cell / f"q{n:02d}.cmd").read_text().strip()
        strategy, query = cmd.split(" ", 1)
        txt = cell / f"q{n:02d}.txt"
        ids, status = parse_ids(txt.read_text(errors="replace"))
        rows.append({"cell": "kill-shot", "call": f"q{n:02d}", "strategy": strategy, "query": query,
                     "returned_ids": ids, "raw_file": f"e3-killshot/q{n:02d}.txt", "raw_sha256": sha(txt),
                     "parse_status": status, "counted": True})
    for q in ("byte-level boundaries parallel", "dynamic chunking multilingual",
              "tokenizer-free cross-lingual boundary", "H-Net multilingual"):
        rows.append({"cell": "kill-shot", "strategy": "openreview api2 notes/search", "query": q,
                     "returned_ids": "see cell report (titles mostly unreadable)", "counted": False})
    return rows


def crossdomain(root: Path) -> list[dict]:
    cell = root / "e3-xdomain"
    rows = []
    for n, (strategy, query) in enumerate(XD_QUERIES, start=1):
        txt = cell / f"q{n:02d}.txt"
        ids, status = parse_ids(txt.read_text(errors="replace"))
        rows.append({"cell": "cross-domain", "call": f"q{n:02d}", "strategy": strategy, "query": query,
                     "returned_ids": ids, "raw_file": f"e3-xdomain/q{n:02d}.txt", "raw_sha256": sha(txt),
                     "parse_status": status, "counted": True,
                     "query_string_source": "cell structured report (raw file holds results only)"})
    for q in ("Fournier 2013 Evaluating Text Segmentation using Boundary Edit Distance ACL Anthology",
              "Rasanen Laine Altosaar 2009 R-value improved speech segmentation quality measure",
              "gold standard word alignment dataset English-Korean English-Polish English-Chinese",
              "XL-WA gold evaluation benchmark word alignment 14 language pairs",
              "FLORES-200 word alignment gold annotation human-annotated alignments"):
        rows.append({"cell": "cross-domain", "strategy": "WebSearch", "query": q, "counted": False})
    rows.append({"cell": "cross-domain", "strategy": "WebFetch + pdftotext", "query": "https://ceur-ws.org/Vol-3596/paper32.pdf", "counted": False})
    rows.append({"cell": "cross-domain", "strategy": "gh api", "query": "repos/SapienzaNLP/XL-WA (licence, contents, README)", "counted": False})
    return rows


def asset(root: Path) -> list[dict]:
    cell = root / "e3-asset"
    rows = []
    for name, (strategy, query) in ASSET_QUERIES.items():
        raw = cell / name
        ids, status = parse_ids(raw.read_text(errors="replace"))
        rows.append({"cell": "asset", "call": name.removesuffix(".json"), "strategy": strategy, "query": query,
                     "returned_ids": ids, "raw_file": f"e3-asset/{name}", "raw_sha256": sha(raw),
                     "parse_status": status, "counted": True})
    rows.append({"cell": "asset", "strategy": "Hugging Face and GitHub APIs (read-only)",
                 "query": "cartesia-ai hnet_* model repos, allenai Bolmo/Bwen/Blama, facebook BLT, openlanguagedata/flores_plus, WPS-Qingqiu/OmniAlign, ZurichNLP/CTFAlign, goombalab/hnet, allenai/bolmo-core",
                 "counted": False})
    return rows


PAPER_READS = {
    "frontier": ["2601.22805", "2507.07955", "2407.08818", "2609.06381", "2608.27658", "2608.03599", "2512.15586",
                 "2502.06468", "2507.07824", "2610.01921", "2610.05978", "2610.11790", "2605.30080", "2508.05628",
                 "2605.28128", "2609.00463 (report)", "2609.12303 (report)", "2602.13940 (report)", "2510.06128 (report)",
                 "2607.16117 (report)", "2603.03583 (report)", "2602.01007 (report)", "10.1038/s41586-026-11111-4 (HTML)"],
    "kill-shot": ["2407.08818", "2609.06381", "2608.27658", "2608.03599", "2512.15586", "2507.07955", "2608.18474",
                  "2608.21023", "2610.05978", "2608.17325", "2609.00463", "2610.01984", "2605.30080", "2507.07824",
                  "2510.06128", "2605.28128", "2502.06468", "1810.01480", "2606.23566", "2608.15454", "2603.29026",
                  "10.1038/s41586-026-11111-4 (metadata)"],
    "cross-domain": ["2306.04116", "2412.16063", "2605.28128", "2512.17083", "1910.12958", "2201.00730", "2608.18474",
                     "2502.06468", "2206.13167 (report)", "2109.05257 (report)", "1508.03534 (report)", "1708.07508 (report)",
                     "6 OpenAlex metadata records"],
    "asset": ["2608.18474", "2608.21023", "2610.05978", "2609.00463", "2608.15454", "2605.30080", "2507.12720",
              "2508.05628", "2407.08818", "2507.07955"],
    "synthesis_rereads": ["2502.06468 (Secs. 3.2, 5, 6)", "2601.22805 (Secs. 3.4, 3.5)",
                          "2507.07955 (Sec. 2.2 routing, Eq. 4; Sec. 3 Fig. 4 bullets; Chinese setup)",
                          "2512.15586 (Sec. 3.1.1; Stage 1 accuracy; end-to-end note)", "2610.01921 (abstract, Sec. 1)"],
}


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    rows = frontier(root) + killshot(root) + crossdomain(root) + asset(root)
    counted = [r for r in rows if r.get("counted")]
    by_cell: dict[str, int] = {}
    for r in counted:
        by_cell[r["cell"]] = by_cell.get(r["cell"], 0) + 1
    failed = [f'{r["cell"]}:{r.get("call")}' for r in counted if str(r.get("parse_status", "")).startswith("FAILED")]
    log = {
        "schema": "e3-stage0 gauntlet query log v1",
        "built_on": "2026-10-10",
        "counting_rule": "every orx discover call counts (failed calls included); OpenReview, web and metadata API calls and paper reads are logged, not counted",
        "queries_against_budget": len(counted),
        "declared_query_budget": 150,
        "refuter_reserve": 30,
        "remaining_after_cells": 150 - len(counted),
        "counted_by_cell": by_cell,
        "synthesis_counted_queries": 0,
        "failed_counted_calls": failed,
        "uncounted_calls": len(rows) - len(counted),
        "paper_reads": PAPER_READS,
        "rows": rows,
    }
    out.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(len(counted), by_cell, failed, len(rows) - len(counted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
