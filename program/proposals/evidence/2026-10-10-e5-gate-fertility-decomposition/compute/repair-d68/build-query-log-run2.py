#!/usr/bin/env python3
"""Build query-log-run2.json for the E5 fresh gauntlet run under D68 (the repair's retrieval).

Reads the repair owner's orx records from the session scratchpad (one JSON line per
`orx discover` call, written by the logging wrapper with the raw output's SHA-256) and the
full-text reads. Wave 1's log (`query-log.json`) is kept unedited. Counting rule, as in
wave 1: a successful `orx discover` call counts against the declared query budget; a call
that failed (HTTP 429 from OpenAlex) is logged and not counted; `orx paper --full` reads are
logged and not counted.

Usage (inside the session that ran the queries):
    python3 build-query-log-run2.py <scratchpad e5-repair-d68 dir> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

DECLARED = 80
RESERVED_FOR_REFUTERS = 30

PURPOSE = {
    "r01": "decay intervention x write interaction in delta-rule recurrent state (repair novelty: the factorial's components)",
    "r02": "the v2 mechanism paragraph in plain words (published after 2026-01-01)",
    "r03": "noising/denoising and pure indirect effect in recurrent or state-space models",
    "r04": "closest prior's title phrase, follow-ups after its first version (2026-09-27)",
    "r05": "runner-up prior's title phrase, follow-ups after its first version (2026-09-14)",
    "r06": "tokenization granularity, recurrent decay, subword fragmentation",
    "r07": "per-token forget gate vs extra writes under re-tokenization on frozen recurrent checkpoints (after 2026-06-01)",
    "r08": "OpenAlex: four-way mediation decomposition with interaction (venue context)",
    "r09": "token fertility, multilingual recurrent models, gates",
    "r10": "patching decay values between tokenizations in both directions (pure and total indirect effects)",
    "r11": "discretization-step or decay patching in factual recall",
    "r12": "forgetting-mass parity and gate normalisation per character (legacy D20 idea as a direct prior)",
    "r13": "decay versus interference by causal intervention on a frozen recurrent checkpoint (after 2026-03-01)",
    "r14": "OpenAlex retry: exposure-mediator interaction decomposition",
}

FULL_TEXT_READS = [
    ("2609.33093", "closest prior; Secs. 2.1-2.3, 4.2, 5, 6 and App. B re-read for the delta rows and the blind paragraph"),
    ("2609.16183", "runner-up; abstract, Axis 3 (decay), Secs. 5-6 re-read for the delta rows and the blind paragraph"),
    ("2606.27510", "patching NIE = PIE + INT (Prop. 3.1), Theorem 3.2; cited by wave 1's refuters, now credited"),
    ("1804.11188", "time-warping invariance and gates (Secs. 1, discrete-time translation); wave-1 row closed on abstract"),
    ("2004.12265", "causal mediation analysis with model components (natural direct and indirect effects); wave-1 row closed on abstract"),
    ("2404.03646", "activation patching in a selective state-space model (Sec. 2); wave-1 row closed on abstract"),
    ("2406.14528", "effective receptive field and decimation (abstract, Secs. 1 and 4); wave-1 row closed on abstract"),
    ("1609.07843", "WikiText-103 Table 1: train 28,475 articles, validation 60, test 60 (v2 draws passages from the train split)"),
]


CITATION_GRAPH = [
    ("works/doi:10.48550/arXiv.2609.33093", "OpenAlex W7214795438, cited_by_count 0 (too recent)"),
    ("works/doi:10.48550/arXiv.2609.16183", "OpenAlex W7213409806, cited_by_count 0"),
    ("works/doi:10.48550/arXiv.2606.27510", "OpenAlex W7166554991, cited_by_count 0"),
    ("works/doi:10.48550/arXiv.1804.11188 and works?filter=cites:W2786406400", "17 citing works in OpenAlex, all screened by title: none on tokenization granularity or per-token decay in language models"),
    ("works/doi:10.48550/arXiv.2111.00396", "OpenAlex W3209374680, cited_by_count 495"),
    ("works?filter=cites:W3209374680&search=tokenization / fertility / time warping", "94 / 0 / 2 citing works; the first 25 'tokenization' titles and both 'time warping' titles screened: none on decay versus tokenization granularity in recurrent language models"),
]


def main() -> int:
    d = Path(sys.argv[1])
    rows = [json.loads(line) for line in (d / "queries/log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    counted, failed = [], []
    for r in rows:
        r["purpose"] = PURPOSE.get(r["qid"], "")
        (counted if r["return_code"] == 0 and r["returned_ids"] else failed).append(r)
    reads = []
    for pid, why in FULL_TEXT_READS:
        p = d / "papers" / f"{pid}.txt"
        raw = p.read_bytes() if p.is_file() else b""
        reads.append({"id": pid, "command": f"orx paper {pid} --full", "purpose": why,
                      "raw_sha256": hashlib.sha256(raw).hexdigest() if raw else None, "raw_bytes": len(raw)})
    out = {
        "run": "E5 fresh gauntlet run under D68 (repair by the single owner)",
        "orx_version": "0.2.2 (reports itself outdated against 0.2.18)",
        "declared_queries": DECLARED, "reserved_for_refuters": RESERVED_FOR_REFUTERS,
        "counted_by_repair_owner": len(counted),
        "remaining_after_repair": DECLARED - len(counted),
        "counting_rule": "successful orx discover calls count; failed calls (OpenAlex HTTP 429) are logged and not counted; paper reads are not counted",
        "counted_queries": counted,
        "failed_not_counted": failed,
        "full_text_reads_not_counted": reads,
        "citation_graph_lookups_not_counted": [{"request": q, "result": r, "endpoint": "https://api.openalex.org/"} for q, r in CITATION_GRAPH],
        "screening": {"records_returned": sum(len(r["returned_ids"]) for r in counted),
                      "distinct_ids": len({i for r in counted for i in r["returned_ids"]}),
                      "screened_at_title_or_abstract": "all returned titles; abstracts of 2610.00232, 2610.05700, 2606.26560, 2605.13485, 2609.24797, 2608.30376, 2609.07681, 2609.06872, 2605.22791, 2609.36322, 2609.34049, 2610.11743",
                      "opened_in_full": [r["id"] for r in reads], "direct_priors": 0},
        "wave1_log": "query-log.json (120 counted by the wave-1 cells; the wave-1 record counts 135 with the refuters')",
    }
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(len(counted), "counted;", len(failed), "failed;", len(reads), "reads;", out["screening"]["distinct_ids"], "distinct ids")
    return 0


if __name__ == "__main__":
    sys.exit(main())
