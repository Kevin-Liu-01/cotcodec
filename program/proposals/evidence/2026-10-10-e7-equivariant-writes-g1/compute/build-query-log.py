#!/usr/bin/env python3
"""Build query-log.json for the E7 G1 gauntlet from the discovery cells' raw outputs.

Reads the session scratchpad (frontier cell e7-frontier/, kill-shot cell
e7kill/, cross-domain cell e7xd/, asset cell e7-asset/, synthesis e7-synth/),
records every retrieval call with its returned ids and the SHA-256 of the raw
output file, and counts orx discover queries against the declared budget of
150. Reproducible only inside the session that produced the scratchpad; the
log records every raw file's digest.

Usage: build-query-log.py <scratchpad-dir> <output.json>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

KILL_QUERIES = [
    ("orx discover keyword", "cross-lingual alignment recurrent state Gated DeltaNet"),
    ("orx discover keyword", "translation contrastive loss linear attention state"),
    ("orx discover keyword", "Balancing Memory Pathways hybrid"),
    ("orx discover keyword", "What Attention Recalls and Recurrence Controls"),
    ("orx discover keyword", "How Linear Attention Remembers"),
    ("orx discover keyword", "Multilinguality in Hybrid Attention"),
    ("orx discover embedding", "Train a hybrid language model with an auxiliary loss that makes the recurrent state update written for a sentence match the update written for its translation, to improve cross-lingual recall when attention cannot reach the fact"),
    ("orx discover embedding", "Small hybrid model with sliding window attention and linear recurrent layers trained from scratch evaluated on cross-lingual associative recall beyond the attention window"),
    ("orx discover openalex", "cross-lingual associative recall state space model"),
    ("orx discover keyword", "short window attention enables long-term memorization"),
    ("orx discover keyword", "multilingual associative recall MQAR"),
    ("orx discover keyword", "cross-lingual needle in a haystack"),
    ("orx discover embedding", "Pretraining small multilingual language models from scratch with parallel bitext data: when does cross-lingual transfer and alignment emerge as a function of model size and training tokens"),
    ("orx discover keyword", "sliding window size hybrid linear attention recurrent memory underused training window"),
    ("orx discover embedding --published-after 2026-09-01", "Auxiliary semantic alignment objective on the recurrent state of linear attention or state space models across translations"),
    ("orx discover keyword", "Mamba multilingual cross-lingual transfer state space"),
    ("orx discover openalex", "cross-lingual in-context retrieval parallel data pretraining small language models"),
    ("orx discover keyword --published-after 2026-06-01", "language-agnostic recurrent state contrastive translation pairs"),
    ("orx discover embedding", "Contrastive cross-lingual alignment applied to the hidden state of a Mamba or state space model during pretraining with parallel data"),
    ("orx discover keyword --published-after 2026-01-01", "cross-lingual recall linear attention hybrid"),
    ("orx discover openalex", "translation invariant memory state recurrent network contrastive alignment"),
    ("orx discover keyword", "sliding window attention receptive field grows with layers multi-hop beyond window"),
    ("orx discover embedding", "In-context cross-lingual key-value retrieval where facts are stated in one language and queried in another, evaluated in small language models trained from scratch"),
]

SYNTH_QUERIES = [
    ("s01", "orx discover keyword --published-after 2026-01-01", "receptive field stacked sliding window attention layers hybrid recurrent state recall evaluation distance"),
    ("s02", "orx discover embedding", "placing a fact farther back than the combined reach of all sliding-window attention layers so that only the recurrent state can carry it, to test state-carried recall in a hybrid model"),
    ("s03", "orx discover keyword --published-after 2026-01-01", "associative recall binding versus copying a distractor value chance level in-context values"),
    ("s04", "orx discover keyword --published-after 2026-09-15", "translation pair recurrent state write cross-lingual Gated DeltaNet sliding window"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids_from_raw(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find("[")
    if start < 0:
        return []
    try:
        return [str(rec.get("id") or rec.get("doi") or "") for rec in json.loads(text[start:])]
    except json.JSONDecodeError:
        return []


def main() -> int:
    sp, out = Path(sys.argv[1]), Path(sys.argv[2])
    entries = []
    # Frontier cell: the cell's own final log plus raw discover outputs q01..q46.
    fr = json.loads((sp / "e7-frontier/queries_final.json").read_text())
    raw = sorted((sp / "e7-frontier").glob("q*.raw"))
    n_disc = 0
    for q in fr:
        counted = q["tool"].startswith("orx discover")
        rec = {"cell": "frontier", "tool": q["tool"], "query": q["query"], "returned_ids": q["returned_ids"], "counted": counted}
        if counted:
            rec["raw_output"] = f"e7-frontier/{raw[n_disc].name}"
            rec["raw_sha256"] = sha(raw[n_disc])
            n_disc += 1
        entries.append(rec)
    # Kill-shot cell: raw outputs q01..q23 with the cell's query strings.
    for i, (tool, query) in enumerate(KILL_QUERIES, start=1):
        path = sp / f"e7kill/q{i:02d}.txt"
        entries.append({"cell": "kill-shot", "tool": tool, "query": query, "returned_ids": ids_from_raw(path),
                        "raw_output": f"e7kill/{path.name}", "raw_sha256": sha(path), "counted": True})
    for name in sorted(p.name for p in (sp / "e7kill").glob("p_*.txt")):
        entries.append({"cell": "kill-shot", "tool": "orx paper --full", "query": name[2:-4], "counted": False,
                        "raw_output": f"e7kill/{name}", "raw_sha256": sha(sp / "e7kill" / name)})
    entries.append({"cell": "kill-shot", "tool": "OpenReview api2 notes/search", "query": "cross-lingual recurrent state alignment; multilingual linear attention recurrent state hybrid; translation equivariant state writes", "counted": False,
                    "note": "three searches; outputs not saved to files; returned ids recorded in the cell report"})
    entries.append({"cell": "kill-shot", "tool": "WebSearch (ACL Anthology)", "query": "site:aclanthology.org cross-lingual alignment state space model Mamba recurrent hidden state translation", "counted": False})
    # Cross-domain cell.
    xd = json.loads((sp / "e7xd/queries.json").read_text())
    xraw = sorted((sp / "e7xd").glob("q*.out"))
    n = 0
    for q in xd:
        counted = q["tool"].startswith("orx discover")
        rec = {"cell": "cross-domain", "tool": q["tool"], "query": q["query"], "returned_ids": q["returned_ids"], "counted": counted}
        if counted:
            rec["raw_output"] = f"e7xd/{xraw[n].name}"
            rec["raw_sha256"] = sha(xraw[n])
            n += 1
        elif q["tool"].startswith("orx paper"):
            p = sp / f"e7xd/p_{q['query']}.txt"
            if p.is_file():
                rec["raw_output"] = f"e7xd/{p.name}"
                rec["raw_sha256"] = sha(p)
        entries.append(rec)
    # Asset cell.
    entries.append({"cell": "asset", "tool": "orx paper --full", "query": "2610.06750", "counted": False,
                    "raw_output": "e7-asset/2610.06750.txt", "raw_sha256": sha(sp / "e7-asset/2610.06750.txt")})
    # Synthesis.
    for name, tool, query in SYNTH_QUERIES:
        path = sp / f"e7-synth/{name}.raw"
        entries.append({"cell": "synthesis", "tool": tool, "query": query, "returned_ids": ids_from_raw(path),
                        "raw_output": f"e7-synth/{path.name}", "raw_sha256": sha(path), "counted": True})
    for pid in ("2609.30634", "2610.00232"):
        path = sp / f"e7-synth/p_{pid}.txt"
        entries.append({"cell": "synthesis", "tool": "orx paper (abstract)", "query": pid, "counted": False,
                        "raw_output": f"e7-synth/{path.name}", "raw_sha256": sha(path)})
    entries.append({"cell": "synthesis", "tool": "Hugging Face dataset API and raw README", "query": "openlanguagedata/flores_plus; jhu-clsp/paradocs; airesearch/scb_mt_enth_2020; HuggingFaceFW/fineweb; HuggingFaceFW/fineweb-2", "counted": False,
                    "note": "licence, gating and revision reads (auxiliary)"})
    entries.append({"cell": "synthesis", "tool": "GitHub raw and REST API", "query": "MicrosoftTranslator/NTREX README.md, LICENSE.md, LANGUAGES.tsv, commits/main", "counted": False,
                    "note": "licence (CC BY-SA 4.0), language codes deu/zho-CN/tha, head 468c6b69 (auxiliary)"})
    counted = [e for e in entries if e.get("counted")]
    by_cell: dict[str, int] = {}
    for e in counted:
        by_cell[e["cell"]] = by_cell.get(e["cell"], 0) + 1
    log = {
        "schema": "e7-g1 query log v1",
        "source_cutoff": "2026-10-10",
        "counting_rule": "orx discover queries count against the declared 150 (as in the C3 and E4 gauntlets); OpenReview, web, GitHub, Hugging Face and curl calls and paper reads are logged and not counted",
        "queries_against_budget": len(counted),
        "queries_by_cell": by_cell,
        "remaining_queries": 150 - len(counted),
        "refuter_reserve": 30,
        "uncounted_calls": sum(1 for e in entries if not e.get("counted")),
        "entries": entries,
    }
    out.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(len(counted), by_cell, 150 - len(counted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
